"""Test coordinator for orchestrating the testing workflow."""

from typing import Optional, Callable
import logging
from threading import Lock

from .patterns.models import (
    Harness, WirePattern, TestPoint, TestState, PointStatus
)
from ..hal.led_matrix import LEDMatrixBase
from ..hal.switch import SwitchHandlerBase
from ..hal.buzzer import BuzzerDriverBase

logger = logging.getLogger(__name__)


class TestCoordinator:
    """
    Orchestrates the harness testing workflow.

    Responsibilities:
    - Manage test state machine
    - Coordinate GUI updates with LED matrix
    - Handle switch events and verify connections
    - Trigger audio feedback
    - Support flexible order testing (user can select any point)
    """

    # Color constants (24-bit RGB)
    COLOR_PENDING = 0xFFFF00   # Yellow
    COLOR_ACTIVE = 0x0000FF    # Blue
    COLOR_VERIFIED = 0x00FF00  # Green
    COLOR_ERROR = 0xFF0000     # Red
    COLOR_OFF = 0x000000       # Off

    def __init__(
        self,
        led_matrix: LEDMatrixBase,
        switch: SwitchHandlerBase,
        buzzer: BuzzerDriverBase
    ):
        """
        Initialize the test coordinator.

        Args:
            led_matrix: LED matrix driver instance
            switch: Switch handler instance
            buzzer: Buzzer driver instance
        """
        self._led_matrix = led_matrix
        self._switch = switch
        self._buzzer = buzzer

        self._state = TestState.IDLE
        self._current_harness: Optional[Harness] = None
        self._current_pattern: Optional[WirePattern] = None
        self._active_point: Optional[TestPoint] = None

        # Thread safety lock
        self._lock = Lock()

        # Callbacks for GUI updates
        self._on_state_change: Optional[Callable[[TestState], None]] = None
        self._on_point_update: Optional[Callable[[int, int, PointStatus], None]] = None
        self._on_progress_update: Optional[Callable[[int, int], None]] = None
        self._on_active_point_change: Optional[Callable[[Optional[TestPoint]], None]] = None
        self._on_test_complete: Optional[Callable[[], None]] = None

        # Setup switch callback
        self._switch.set_callback(self._on_switch_pressed)

    def set_callbacks(
        self,
        on_state_change: Optional[Callable[[TestState], None]] = None,
        on_point_update: Optional[Callable[[int, int, PointStatus], None]] = None,
        on_progress_update: Optional[Callable[[int, int], None]] = None,
        on_active_point_change: Optional[Callable[[Optional[TestPoint]], None]] = None,
        on_test_complete: Optional[Callable[[], None]] = None
    ) -> None:
        """Set callbacks for UI updates."""
        self._on_state_change = on_state_change
        self._on_point_update = on_point_update
        self._on_progress_update = on_progress_update
        self._on_active_point_change = on_active_point_change
        self._on_test_complete = on_test_complete

    def set_harness(self, harness: Harness) -> None:
        """
        Set the current harness.

        Args:
            harness: Harness to use for testing
        """
        with self._lock:
            self._current_harness = harness
            self._current_pattern = None
            self._active_point = None
            self._set_state(TestState.HARNESS_SELECTED)
            logger.info(f"Harness set: {harness.name}")

    def set_wire_type(self, wire_type: str) -> None:
        """
        Set the wire type pattern to test.

        Args:
            wire_type: Wire type name
        """
        with self._lock:
            if not self._current_harness:
                logger.warning("Cannot set wire type: no harness loaded")
                return

            pattern = self._current_harness.get_pattern(wire_type)
            if not pattern:
                logger.warning(f"Wire type not found: {wire_type}")
                return

            self._current_pattern = pattern
            self._active_point = None
            self._set_state(TestState.PATTERN_LOADED)
            self._update_led_display()
            self._notify_progress()
            logger.info(f"Wire type set: {wire_type} ({pattern.total_points} points)")

    def start_test(self) -> None:
        """Start the test sequence."""
        with self._lock:
            if not self._current_pattern:
                logger.warning("Cannot start test: no pattern loaded")
                return

            if self._state in (TestState.TESTING, TestState.POINT_ACTIVE):
                logger.warning("Test already in progress")
                return

            self._switch.start_monitoring()
            self._set_state(TestState.TESTING)

            # Auto-select first pending point if none active
            pending = self._current_pattern.get_pending_points()
            if pending and not self._active_point:
                self._select_point(pending[0])

            logger.info("Test started")

    def stop_test(self) -> None:
        """Stop the current test."""
        with self._lock:
            self._switch.stop_monitoring()

            if self._active_point:
                # Revert active point to pending if not verified
                if self._active_point.status == PointStatus.ACTIVE:
                    self._active_point.status = PointStatus.PENDING
                    self._update_point_on_led(self._active_point)
                    self._notify_point_update(self._active_point)

            self._active_point = None
            self._set_state(TestState.PATTERN_LOADED)
            self._update_led_display()
            logger.info("Test stopped")

    def reset_pattern(self) -> None:
        """Reset the current pattern (all points to pending)."""
        with self._lock:
            if self._current_pattern:
                self._current_pattern.reset_all()
                self._active_point = None
                self._update_led_display()
                self._notify_progress()
                self._set_state(TestState.PATTERN_LOADED)
                logger.info("Pattern reset")

    def select_point(self, x: int, y: int) -> bool:
        """
        Select a point for testing (flexible order).

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if point was selected, False otherwise
        """
        with self._lock:
            if not self._current_pattern:
                return False

            if self._state not in (TestState.TESTING, TestState.POINT_ACTIVE):
                return False

            point = self._current_pattern.get_point_at(x, y)
            if not point:
                return False

            if point.is_verified:
                logger.debug(f"Point ({x}, {y}) already verified")
                return False

            self._select_point(point)
            return True

    def _select_point(self, point: TestPoint) -> None:
        """Internal method to select a point."""
        # Deselect previous active point
        if self._active_point and self._active_point != point:
            if self._active_point.status == PointStatus.ACTIVE:
                self._active_point.status = PointStatus.PENDING
                self._update_point_on_led(self._active_point)
                self._notify_point_update(self._active_point)

        # Set new active point
        self._active_point = point
        point.set_active()
        self._update_point_on_led(point)
        self._notify_point_update(point)
        self._set_state(TestState.POINT_ACTIVE)

        if self._on_active_point_change:
            self._on_active_point_change(point)

        logger.debug(f"Point selected: ({point.x}, {point.y}) - {point.description}")

    def _on_switch_pressed(self) -> None:
        """Handle switch press event (called from switch handler thread)."""
        with self._lock:
            if self._state != TestState.POINT_ACTIVE:
                logger.debug("Switch pressed but no active point")
                return

            if not self._active_point:
                return

            # Verify the active point
            self._verify_point(self._active_point)

    def _verify_point(self, point: TestPoint) -> None:
        """Verify a test point."""
        point.verify()
        self._update_point_on_led(point)
        self._notify_point_update(point)
        self._buzzer.beep_success()

        logger.info(f"Point verified: ({point.x}, {point.y}) - {point.description}")

        # Update progress
        self._notify_progress()

        # Check if pattern complete
        if self._current_pattern and self._current_pattern.is_complete:
            self._complete_test()
        else:
            # Auto-advance to next pending point
            self._advance_to_next_point()

    def _advance_to_next_point(self) -> None:
        """Advance to the next pending point."""
        if not self._current_pattern:
            return

        pending = self._current_pattern.get_pending_points()
        if pending:
            # Select next point (by sequence order)
            self._select_point(pending[0])
        else:
            self._active_point = None
            self._set_state(TestState.TESTING)
            if self._on_active_point_change:
                self._on_active_point_change(None)

    def _complete_test(self) -> None:
        """Handle test completion."""
        self._switch.stop_monitoring()
        self._active_point = None
        self._set_state(TestState.COMPLETE)

        # Play completion tone
        self._buzzer.beep_custom(1500, 100)
        self._buzzer.beep_custom(2000, 100)
        self._buzzer.beep_custom(2500, 200)

        logger.info("Test complete!")

        if self._on_test_complete:
            self._on_test_complete()

        if self._on_active_point_change:
            self._on_active_point_change(None)

    def _update_led_display(self) -> None:
        """Update the entire LED matrix display."""
        self._led_matrix.clear()

        if self._current_pattern:
            for point in self._current_pattern.points:
                self._update_point_on_led(point)

        self._led_matrix.show()

    def _update_point_on_led(self, point: TestPoint) -> None:
        """Update a single point on the LED matrix."""
        color_map = {
            PointStatus.PENDING: self.COLOR_PENDING,
            PointStatus.ACTIVE: self.COLOR_ACTIVE,
            PointStatus.VERIFIED: self.COLOR_VERIFIED,
            PointStatus.ERROR: self.COLOR_ERROR,
        }
        color = color_map.get(point.status, self.COLOR_OFF)
        self._led_matrix.set_pixel(point.x, point.y, color)
        self._led_matrix.show()

    def _set_state(self, state: TestState) -> None:
        """Set the current state and notify listeners."""
        self._state = state
        if self._on_state_change:
            self._on_state_change(state)

    def _notify_point_update(self, point: TestPoint) -> None:
        """Notify listeners of a point status change."""
        if self._on_point_update:
            self._on_point_update(point.x, point.y, point.status)

    def _notify_progress(self) -> None:
        """Notify listeners of progress update."""
        if self._current_pattern and self._on_progress_update:
            self._on_progress_update(
                self._current_pattern.verified_count,
                self._current_pattern.total_points
            )

    def simulate_switch_press(self) -> None:
        """Simulate a switch press (for testing/GUI)."""
        self._on_switch_pressed()

    @property
    def state(self) -> TestState:
        """Get current test state."""
        return self._state

    @property
    def active_point(self) -> Optional[TestPoint]:
        """Get currently active point."""
        return self._active_point

    @property
    def current_pattern(self) -> Optional[WirePattern]:
        """Get current pattern."""
        return self._current_pattern

    def cleanup(self) -> None:
        """Clean up resources."""
        self._switch.stop_monitoring()
        self._led_matrix.clear()
        self._led_matrix.show()

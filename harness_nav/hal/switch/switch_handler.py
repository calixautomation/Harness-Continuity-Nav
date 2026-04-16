"""Switch handler with debouncing for limit switch input."""

from abc import ABC, abstractmethod
from typing import Callable, Optional
import threading
import time
import logging

logger = logging.getLogger(__name__)


class SwitchHandlerBase(ABC):
    """Abstract base class for switch handlers."""

    @abstractmethod
    def start_monitoring(self) -> None:
        """Start monitoring the switch for presses."""
        pass

    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stop monitoring the switch."""
        pass

    @abstractmethod
    def is_pressed(self) -> bool:
        """Check if switch is currently pressed."""
        pass

    @abstractmethod
    def set_callback(self, callback: Callable[[], None]) -> None:
        """Set callback to be called when switch is pressed."""
        pass


class DualSwitchHandlerBase(ABC):
    """Abstract base class for dual switch handlers (limit switch + metal plate)."""

    @abstractmethod
    def start_monitoring(self) -> None:
        """Start monitoring both switches."""
        pass

    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stop monitoring both switches."""
        pass

    @abstractmethod
    def set_lock_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for limit switch (wire lock) events."""
        pass

    @abstractmethod
    def set_verify_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for metal plate (verify) events."""
        pass


class MockSwitchHandler(SwitchHandlerBase):
    """Mock switch handler for development and testing."""

    def __init__(self, gpio_pin: str = "", debounce_ms: int = 50):
        self._gpio_pin = gpio_pin
        self._debounce_ms = debounce_ms
        self._callback: Optional[Callable[[], None]] = None
        self._pressed = False
        self._monitoring = False
        logger.info(f"MockSwitchHandler created for pin {gpio_pin}")

    def start_monitoring(self) -> None:
        """Start monitoring (no-op for mock)."""
        self._monitoring = True
        logger.info("MockSwitchHandler: monitoring started")

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._monitoring = False
        logger.info("MockSwitchHandler: monitoring stopped")

    def is_pressed(self) -> bool:
        """Check if switch is currently pressed."""
        return self._pressed

    def set_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for switch press events."""
        self._callback = callback

    def simulate_press(self) -> None:
        """Simulate a switch press (for testing/GUI interaction)."""
        if self._monitoring and self._callback:
            logger.debug("MockSwitchHandler: simulating press")
            self._pressed = True
            self._callback()
            self._pressed = False


class SwitchHandler(SwitchHandlerBase):
    """
    Real switch handler for BeagleBone Black GPIO.

    Uses Adafruit_BBIO for GPIO access with software debouncing.
    Falls back to MockSwitchHandler on non-BeagleBone systems.
    """

    def __init__(self, gpio_pin: str, debounce_ms: int = 50):
        self._gpio_pin = gpio_pin
        self._debounce_ms = debounce_ms
        self._callback: Optional[Callable[[], None]] = None
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_press_time = 0.0
        self._use_mock = False
        self._mock: Optional[MockSwitchHandler] = None
        self._gpio = None

        try:
            import Adafruit_BBIO.GPIO as GPIO
            self._gpio = GPIO
            self._setup_gpio()
            logger.info(f"SwitchHandler initialized on pin {gpio_pin}")
        except ImportError:
            logger.warning("Adafruit_BBIO not available, using mock")
            self._use_mock = True
            self._mock = MockSwitchHandler(gpio_pin, debounce_ms)

    def _setup_gpio(self) -> None:
        """Setup GPIO pin for input with pull-up."""
        if self._gpio:
            self._gpio.setup(self._gpio_pin, self._gpio.IN, pull_up_down=self._gpio.PUD_UP)

    def start_monitoring(self) -> None:
        """Start monitoring the switch in a background thread."""
        if self._use_mock and self._mock:
            self._mock.start_monitoring()
            return

        if self._monitoring:
            return

        self._monitoring = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("SwitchHandler: monitoring started")

    def stop_monitoring(self) -> None:
        """Stop monitoring the switch."""
        if self._use_mock and self._mock:
            self._mock.stop_monitoring()
            return

        self._monitoring = False
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            self._monitor_thread = None
        logger.info("SwitchHandler: monitoring stopped")

    def _monitor_loop(self) -> None:
        """Background thread loop for monitoring switch state."""
        last_state = True  # Pull-up means HIGH when not pressed
        debounce_time = self._debounce_ms / 1000.0

        while not self._stop_event.is_set():
            if self._gpio:
                current_state = self._gpio.input(self._gpio_pin)

                # Detect falling edge (button press with pull-up)
                if last_state and not current_state:
                    current_time = time.time()
                    if current_time - self._last_press_time > debounce_time:
                        self._last_press_time = current_time
                        if self._callback:
                            logger.debug("Switch pressed (debounced)")
                            self._callback()

                last_state = current_state

            time.sleep(0.01)  # 10ms polling interval

    def is_pressed(self) -> bool:
        """Check if switch is currently pressed."""
        if self._use_mock and self._mock:
            return self._mock.is_pressed()

        if self._gpio:
            # Pull-up: LOW = pressed
            return not self._gpio.input(self._gpio_pin)
        return False

    def set_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for switch press events."""
        if self._use_mock and self._mock:
            self._mock.set_callback(callback)
            return
        self._callback = callback

    def simulate_press(self) -> None:
        """Simulate a switch press (for testing or remote triggering)."""
        if self._use_mock and self._mock:
            self._mock.simulate_press()
        elif self._callback:
            self._callback()

    def cleanup(self) -> None:
        """Clean up GPIO resources."""
        self.stop_monitoring()
        if self._gpio:
            self._gpio.cleanup(self._gpio_pin)


class MockDualSwitchHandler(DualSwitchHandlerBase):
    """
    Mock dual switch handler for development and testing.

    Simulates:
    - Limit switch: Triggered when wire is locked in slot
    - Metal plate: Triggered when wire touches plate (verify connectivity)
    """

    def __init__(
        self,
        limit_switch_pin: str = "",
        metal_plate_pin: str = "",
        debounce_ms: int = 50
    ):
        self._limit_switch_pin = limit_switch_pin
        self._metal_plate_pin = metal_plate_pin
        self._debounce_ms = debounce_ms
        self._lock_callback: Optional[Callable[[], None]] = None
        self._verify_callback: Optional[Callable[[], None]] = None
        self._monitoring = False
        logger.info(f"MockDualSwitchHandler created (limit: {limit_switch_pin}, plate: {metal_plate_pin})")

    def start_monitoring(self) -> None:
        """Start monitoring (no-op for mock)."""
        self._monitoring = True
        logger.info("MockDualSwitchHandler: monitoring started")

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._monitoring = False
        logger.info("MockDualSwitchHandler: monitoring stopped")

    def set_lock_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for limit switch (wire lock) events."""
        self._lock_callback = callback

    def set_verify_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for metal plate (verify) events."""
        self._verify_callback = callback

    def simulate_lock(self) -> None:
        """Simulate limit switch press (wire locked in slot)."""
        if self._monitoring and self._lock_callback:
            logger.debug("MockDualSwitchHandler: simulating lock")
            self._lock_callback()

    def simulate_verify(self) -> None:
        """Simulate metal plate touch (verify connectivity)."""
        if self._monitoring and self._verify_callback:
            logger.debug("MockDualSwitchHandler: simulating verify")
            self._verify_callback()

    def simulate_lock_press(self) -> None:
        """Backward-compatible alias for simulating a lock press."""
        self.simulate_lock()

    def simulate_verify_press(self) -> None:
        """Backward-compatible alias for simulating a verify press."""
        self.simulate_verify()


class DualSwitchHandler(DualSwitchHandlerBase):
    """
    Real dual switch handler for BeagleBone Black GPIO.

    Monitors two inputs:
    - Limit switch: Detects when wire is locked in slot
    - Metal plate: Detects when wire touches plate (verify connectivity)

    Falls back to MockDualSwitchHandler on non-BeagleBone systems.
    """

    def __init__(
        self,
        limit_switch_pin: str,
        metal_plate_pin: str,
        debounce_ms: int = 50
    ):
        self._limit_switch_pin = limit_switch_pin
        self._metal_plate_pin = metal_plate_pin
        self._debounce_ms = debounce_ms
        self._lock_callback: Optional[Callable[[], None]] = None
        self._verify_callback: Optional[Callable[[], None]] = None
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_lock_time = 0.0
        self._last_verify_time = 0.0
        self._use_mock = False
        self._mock: Optional[MockDualSwitchHandler] = None
        self._gpio = None

        try:
            import Adafruit_BBIO.GPIO as GPIO
            self._gpio = GPIO
            self._setup_gpio()
            logger.info(f"DualSwitchHandler initialized (limit: {limit_switch_pin}, plate: {metal_plate_pin})")
        except ImportError:
            logger.warning("Adafruit_BBIO not available, using mock")
            self._use_mock = True
            self._mock = MockDualSwitchHandler(limit_switch_pin, metal_plate_pin, debounce_ms)

    def _setup_gpio(self) -> None:
        """Setup GPIO pins for input with pull-up."""
        if self._gpio:
            self._gpio.setup(self._limit_switch_pin, self._gpio.IN, pull_up_down=self._gpio.PUD_UP)
            self._gpio.setup(self._metal_plate_pin, self._gpio.IN, pull_up_down=self._gpio.PUD_UP)

    def start_monitoring(self) -> None:
        """Start monitoring both switches in a background thread."""
        if self._use_mock and self._mock:
            self._mock.start_monitoring()
            return

        if self._monitoring:
            return

        self._monitoring = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("DualSwitchHandler: monitoring started")

    def stop_monitoring(self) -> None:
        """Stop monitoring both switches."""
        if self._use_mock and self._mock:
            self._mock.stop_monitoring()
            return

        self._monitoring = False
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            self._monitor_thread = None
        logger.info("DualSwitchHandler: monitoring stopped")

    def _monitor_loop(self) -> None:
        """Background thread loop for monitoring both switch states."""
        last_lock_state = True  # Pull-up means HIGH when not pressed
        last_verify_state = True
        debounce_time = self._debounce_ms / 1000.0

        while not self._stop_event.is_set():
            if self._gpio:
                # Check limit switch (wire lock)
                current_lock_state = self._gpio.input(self._limit_switch_pin)
                if last_lock_state and not current_lock_state:
                    current_time = time.time()
                    if current_time - self._last_lock_time > debounce_time:
                        self._last_lock_time = current_time
                        if self._lock_callback:
                            logger.debug("Limit switch pressed (wire locked)")
                            self._lock_callback()
                last_lock_state = current_lock_state

                # Check metal plate (verify)
                current_verify_state = self._gpio.input(self._metal_plate_pin)
                if last_verify_state and not current_verify_state:
                    current_time = time.time()
                    if current_time - self._last_verify_time > debounce_time:
                        self._last_verify_time = current_time
                        if self._verify_callback:
                            logger.debug("Metal plate touched (verify)")
                            self._verify_callback()
                last_verify_state = current_verify_state

            time.sleep(0.01)  # 10ms polling interval

    def set_lock_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for limit switch (wire lock) events."""
        if self._use_mock and self._mock:
            self._mock.set_lock_callback(callback)
            return
        self._lock_callback = callback

    def set_verify_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for metal plate (verify) events."""
        if self._use_mock and self._mock:
            self._mock.set_verify_callback(callback)
            return
        self._verify_callback = callback

    def simulate_lock(self) -> None:
        """Simulate limit switch press (for testing)."""
        if self._use_mock and self._mock:
            self._mock.simulate_lock()
        elif self._lock_callback:
            self._lock_callback()

    def simulate_verify(self) -> None:
        """Simulate metal plate touch (for testing)."""
        if self._use_mock and self._mock:
            self._mock.simulate_verify()
        elif self._verify_callback:
            self._verify_callback()

    def simulate_lock_press(self) -> None:
        """Backward-compatible alias for simulating a lock press."""
        self.simulate_lock()

    def simulate_verify_press(self) -> None:
        """Backward-compatible alias for simulating a verify press."""
        self.simulate_verify()

    def cleanup(self) -> None:
        """Clean up GPIO resources."""
        self.stop_monitoring()
        if self._gpio:
            self._gpio.cleanup(self._limit_switch_pin)
            self._gpio.cleanup(self._metal_plate_pin)

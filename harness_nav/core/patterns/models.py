"""Data models for LED patterns and test states."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Set, Optional


class TestState(Enum):
    """States for the test state machine."""
    IDLE = auto()              # No pattern selected
    PATTERN_LOADED = auto()    # Pattern selected, ready to test
    TESTING = auto()           # Test in progress
    COMPLETE = auto()          # All LEDs verified
    ERROR = auto()             # Wrong connection detected


class LEDStatus(Enum):
    """Status of an individual LED."""
    OFF = auto()       # Not part of current pattern
    PENDING = auto()   # Needs to be tested
    ACTIVE = auto()    # Currently selected for testing (blinking)
    LOCKED = auto()    # Wire locked in slot (limit switch pressed)
    VERIFIED = auto()  # Successfully verified (circuit complete)
    ERROR = auto()     # Wrong connection


@dataclass
class Pattern:
    """
    Represents a test pattern with specific LED positions.

    LED numbering: 1-64 for 8x8 grid
    Layout:
        1  2  3  4  5  6  7  8
        9  10 11 12 13 14 15 16
        17 18 19 20 21 22 23 24
        25 26 27 28 29 30 31 32
        33 34 35 36 37 38 39 40
        41 42 43 44 45 46 47 48
        49 50 51 52 53 54 55 56
        57 58 59 60 61 62 63 64
    """
    id: str
    name: str
    description: str
    leds: List[int]  # LED numbers (1-64) that must be tested

    # Runtime state (not initialized in __init__)
    _verified_leds: Set[int] = field(default_factory=set, repr=False)
    _locked_leds: Set[int] = field(default_factory=set, repr=False)  # Wire locked but not verified
    _active_led: int = field(default=0, repr=False)

    def __post_init__(self):
        """Validate LED numbers."""
        for led in self.leds:
            if not (1 <= led <= 64):
                raise ValueError(f"LED number {led} out of range [1, 64]")
        self._verified_leds = set()
        self._locked_leds = set()
        self._active_led = 0

    @staticmethod
    def led_to_xy(led_num: int) -> tuple:
        """Convert LED number (1-64) to (x, y) coordinates (0-7, 0-7)."""
        if not (1 <= led_num <= 64):
            raise ValueError(f"LED number {led_num} out of range [1, 64]")
        led_index = led_num - 1
        x = led_index % 8
        y = led_index // 8
        return (x, y)

    @staticmethod
    def xy_to_led(x: int, y: int) -> int:
        """Convert (x, y) coordinates (0-7, 0-7) to LED number (1-64)."""
        if not (0 <= x < 8 and 0 <= y < 8):
            raise ValueError(f"Coordinates ({x}, {y}) out of range")
        return y * 8 + x + 1

    def get_led_status(self, led_num: int) -> LEDStatus:
        """Get the status of a specific LED."""
        if led_num not in self.leds:
            return LEDStatus.OFF
        if led_num in self._verified_leds:
            return LEDStatus.VERIFIED
        if led_num in self._locked_leds:
            return LEDStatus.LOCKED
        if led_num == self._active_led:
            return LEDStatus.ACTIVE
        return LEDStatus.PENDING

    def get_pending_leds(self) -> List[int]:
        """Get list of LEDs not yet verified."""
        return [led for led in self.leds if led not in self._verified_leds]

    def select_led(self, led_num: int) -> bool:
        """
        Select an LED for testing.
        Returns True if selection valid, False otherwise.
        """
        if led_num not in self.leds:
            return False
        if led_num in self._verified_leds:
            return False  # Already verified
        self._active_led = led_num
        return True

    def lock_active_led(self) -> bool:
        """
        Lock the currently active LED (wire inserted and locked).
        Returns True if locked, False if no active LED or already locked.
        """
        if self._active_led == 0:
            return False
        if self._active_led not in self.leds:
            return False
        if self._active_led in self._locked_leds:
            return False  # Already locked
        self._locked_leds.add(self._active_led)
        return True

    def verify_active_led(self) -> bool:
        """
        Verify the currently active LED (circuit complete).
        Returns True if verified, False if no active LED or not locked.
        """
        if self._active_led == 0:
            return False
        if self._active_led not in self.leds:
            return False
        if self._active_led not in self._locked_leds:
            return False  # Must be locked first
        self._verified_leds.add(self._active_led)
        self._locked_leds.discard(self._active_led)
        self._active_led = 0
        return True

    def is_active_led_locked(self) -> bool:
        """Check if the active LED is in locked state."""
        return self._active_led in self._locked_leds

    def check_connection(self, connected_led: int) -> bool:
        """
        Check if the connected LED matches the expected active LED.
        Returns True if correct, False if wrong connection (ERROR).
        """
        return connected_led == self._active_led

    @property
    def active_led(self) -> int:
        """Get currently active LED number (0 if none)."""
        return self._active_led

    @property
    def verified_leds(self) -> Set[int]:
        """Get set of verified LED numbers."""
        return self._verified_leds.copy()

    @property
    def is_complete(self) -> bool:
        """Check if all LEDs have been verified."""
        return len(self._verified_leds) == len(self.leds)

    @property
    def progress(self) -> tuple:
        """Get progress as (verified_count, total_count)."""
        return (len(self._verified_leds), len(self.leds))

    @property
    def progress_percent(self) -> float:
        """Get progress as percentage."""
        if len(self.leds) == 0:
            return 100.0
        return (len(self._verified_leds) / len(self.leds)) * 100

    def reset(self) -> None:
        """Reset all verification state."""
        self._verified_leds.clear()
        self._locked_leds.clear()
        self._active_led = 0

    def auto_select_next(self) -> Optional[int]:
        """Auto-select next pending LED. Returns LED number or None."""
        pending = self.get_pending_leds()
        if pending:
            self._active_led = pending[0]
            return self._active_led
        return None

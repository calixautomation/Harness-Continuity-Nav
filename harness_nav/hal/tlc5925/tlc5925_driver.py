"""
TLC5925 16-channel constant-current LED sink driver.

Hardware: Raspberry Pi 4B, GPIO bitbang (SPI peripheral left pins at 0V on this board).
Wiring:
    SDI  → BCM 10  (physical pin 19)
    CLK  → BCM 11  (physical pin 23)
    LE   → BCM 23  (physical pin 16)
    OE   → GND     (always enabled)
    REXT → 1kΩ → GND  (~22mA per channel)
    VDD  → external 5V (RPi 5V pin browns out under load)

Bit order: LSB first — bit 0 drives OUT0 (LED channel 1), bit 15 drives OUT15 (LED channel 16).

LED status → physical output mapping:
    ACTIVE   → blink in sync with GUI 500ms timer
    LOCKED   → solid ON  (wire locked, awaiting verification)
    VERIFIED → solid ON  (test passed)
    PENDING / OFF / ERROR → OFF
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict

from ...core.patterns.models import LEDStatus

logger = logging.getLogger(__name__)

# Only LED numbers 1–16 have physical channels (OUT0–OUT15).
_MAX_CHANNEL = 16


class TLC5925DriverBase(ABC):
    """Abstract base for TLC5925 driver implementations."""

    @abstractmethod
    def on_led_status_change(self, led_num: int, status: LEDStatus) -> None:
        """
        Update a single LED channel's status.

        led_num 1–16 maps to OUT0–OUT15. Numbers outside that range are ignored.
        Called by GridWidget whenever a GUI LED changes state.
        """

    @abstractmethod
    def on_blink_tick(self, blink_on: bool) -> None:
        """
        Synchronised blink tick from the GUI 500ms timer.

        blink_on=True  → ACTIVE LEDs should be lit.
        blink_on=False → ACTIVE LEDs should be dark.
        """

    @abstractmethod
    def sync(self, pattern, blink_on: bool) -> None:
        """
        Push the full 16-channel state derived from pattern + blink phase.

        pattern: Pattern object (or None to turn everything off).
        blink_on: current blink phase from the GUI 500ms timer.

        This is the preferred entry point — it derives the hardware word
        directly from the authoritative Pattern state on every call, so
        there is no accumulated internal state that can become stale.
        """

    @abstractmethod
    def all_off(self) -> None:
        """Turn all 16 channels off immediately and clear internal state."""

    @abstractmethod
    def cleanup(self) -> None:
        """Turn all LEDs off and release GPIO resources."""


class TLC5925Driver(TLC5925DriverBase):
    """
    Real TLC5925 driver using GPIO bitbang on Raspberry Pi 4B.

    Falls back to no-op logging when RPi.GPIO is unavailable so the same
    class can be imported on a development machine without crashing.
    """

    def __init__(self, sdi: int = 10, clk: int = 11, le: int = 23):
        """
        Args:
            sdi: BCM pin number for serial data in  (default GPIO10, physical pin 19)
            clk: BCM pin number for clock           (default GPIO11, physical pin 23)
            le:  BCM pin number for latch enable    (default GPIO23, physical pin 16)
        """
        self._sdi = sdi
        self._clk = clk
        self._le = le

        # Per-channel status tracking — only channels 1–16 stored.
        self._statuses: Dict[int, LEDStatus] = {}

        # Current blink phase (mirrors GridWidget._blink_state).
        self._blink_on: bool = True

        self._gpio = None
        self._init_gpio()

    # ------------------------------------------------------------------
    # GPIO setup
    # ------------------------------------------------------------------

    def _init_gpio(self) -> None:
        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
            if GPIO.getmode() is None:
                GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self._sdi, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self._clk, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self._le,  GPIO.OUT, initial=GPIO.LOW)
            logger.info(
                "TLC5925 GPIO initialised — SDI=%d CLK=%d LE=%d",
                self._sdi, self._clk, self._le
            )
            self._startup_test()
        except Exception as e:
            logger.warning("TLC5925 GPIO init failed (%s) — running in no-op mode", e)
            self._gpio = None

    def _startup_test(self) -> None:
        """
        Startup hardware test — runs before the Qt event loop so any failure
        is visible before the window opens.

        Sequence:
          1. All 16 channels ON → OFF  (confirms full-bus shift works)
          2. Chase ch0→ch15 at 60ms each  (confirms single-channel patterns work)
        """
        logger.info("TLC5925 startup test — all channels ON/OFF")
        self._shift_and_latch(0xFFFF)
        time.sleep(0.3)
        self._shift_and_latch(0x0000)
        time.sleep(0.1)

        logger.info("TLC5925 startup test — per-channel chase ch0→ch15")
        for i in range(16):
            self._shift_and_latch(1 << i)
            time.sleep(0.06)
        self._shift_and_latch(0x0000)
        logger.info("TLC5925 startup test complete")

    # ------------------------------------------------------------------
    # Low-level bitbang protocol
    # ------------------------------------------------------------------

    def _shift_and_latch(self, pattern: int) -> None:
        """
        Clock 16 bits LSB-first into the shift register then pulse LE to latch.

        Timing: ~2 µs per edge → ~250 kHz effective clock rate.
        Confirmed working on this board; SPI peripheral leaves GPIO10/11 at 0V.
        """
        if self._gpio is None:
            return

        GPIO = self._gpio
        GPIO.output(self._clk, GPIO.LOW)

        for i in range(16):
            GPIO.output(self._sdi, (pattern >> i) & 1)
            time.sleep(0.000002)          # setup time
            GPIO.output(self._clk, GPIO.HIGH)
            time.sleep(0.000002)          # hold time
            GPIO.output(self._clk, GPIO.LOW)
            time.sleep(0.000002)

        GPIO.output(self._sdi, GPIO.LOW)
        GPIO.output(self._le, GPIO.HIGH)  # rising edge latches shift → output reg
        time.sleep(0.00001)
        GPIO.output(self._le, GPIO.LOW)

    # ------------------------------------------------------------------
    # Pattern computation
    # ------------------------------------------------------------------

    def _build_pattern(self, blink_on: bool) -> int:
        """Return the 16-bit word to send based on current statuses and blink phase."""
        pattern = 0
        for led_num, status in self._statuses.items():
            channel = led_num - 1  # LED 1 → bit 0, LED 16 → bit 15
            if status == LEDStatus.ACTIVE:
                if blink_on:
                    pattern |= (1 << channel)
            elif status in (LEDStatus.LOCKED, LEDStatus.VERIFIED):
                pattern |= (1 << channel)
            # PENDING / OFF / ERROR → bit stays 0
        return pattern

    def _push(self) -> None:
        """Recompute pattern from current state and send to hardware."""
        pattern = self._build_pattern(self._blink_on)
        logger.debug("TLC5925 push 0x%04X (blink=%s)", pattern, self._blink_on)
        self._shift_and_latch(pattern)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def sync(self, pattern, blink_on: bool) -> None:
        hw = 0
        if pattern is not None:
            for led_num in range(1, _MAX_CHANNEL + 1):
                status = pattern.get_led_status(led_num)
                # Reversed mapping: LED 1 → bit 15 (OUT15), LED 16 → bit 0 (OUT0)
                bit = _MAX_CHANNEL - led_num
                if status == LEDStatus.ACTIVE:
                    if blink_on:
                        hw |= (1 << bit)
                elif status in (LEDStatus.LOCKED, LEDStatus.VERIFIED):
                    hw |= (1 << bit)
        logger.debug("TLC5925 sync 0x%04X (blink=%s)", hw, blink_on)
        self._shift_and_latch(hw)

    def on_led_status_change(self, led_num: int, status: LEDStatus) -> None:
        if not (1 <= led_num <= _MAX_CHANNEL):
            return
        self._statuses[led_num] = status
        logger.info("TLC5925 ch%d → %s", led_num, status.name)
        self._push()

    def on_blink_tick(self, blink_on: bool) -> None:
        self._blink_on = blink_on
        self._push()

    def all_off(self) -> None:
        self._statuses.clear()
        self._shift_and_latch(0x0000)

    def cleanup(self) -> None:
        self.all_off()
        if self._gpio is not None:
            self._gpio.cleanup()
            logger.info("TLC5925 GPIO cleaned up")


class MockTLC5925Driver(TLC5925DriverBase):
    """
    Mock TLC5925 driver for desktop development and CI — no GPIO required.

    Logs all state changes at DEBUG level so behaviour can be verified
    without hardware.
    """

    def __init__(self):
        self._statuses: Dict[int, LEDStatus] = {}
        self._blink_on: bool = True

    def sync(self, pattern, blink_on: bool) -> None:
        if pattern is None:
            logger.debug("MockTLC5925: sync — all off")
            return
        active = [n for n in range(1, _MAX_CHANNEL + 1)
                  if pattern.get_led_status(n) == LEDStatus.ACTIVE]
        solid = [n for n in range(1, _MAX_CHANNEL + 1)
                 if pattern.get_led_status(n) in (LEDStatus.LOCKED, LEDStatus.VERIFIED)]
        logger.debug("MockTLC5925: sync blink=%s active=%s solid=%s", blink_on, active, solid)

    def on_led_status_change(self, led_num: int, status: LEDStatus) -> None:
        if not (1 <= led_num <= _MAX_CHANNEL):
            return
        self._statuses[led_num] = status
        logger.debug("MockTLC5925: ch%d → %s", led_num, status.name)

    def on_blink_tick(self, blink_on: bool) -> None:
        self._blink_on = blink_on
        active = [n for n, s in self._statuses.items() if s == LEDStatus.ACTIVE]
        if active:
            logger.debug(
                "MockTLC5925: blink %s — active channels %s",
                "ON" if blink_on else "OFF", active
            )

    def all_off(self) -> None:
        self._statuses.clear()
        logger.debug("MockTLC5925: all channels OFF")

    def cleanup(self) -> None:
        self.all_off()
        logger.debug("MockTLC5925: cleanup complete")

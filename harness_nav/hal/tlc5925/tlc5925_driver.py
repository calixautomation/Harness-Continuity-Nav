"""TLC5925 x4 (64-channel) driver for the TLC carrier board.

Pins (BCM): SDI=10 (pin 19), CLK=11 (pin 23), LE=25 (pin 22), /OE=7 (pin 26).
GUI LED n == J2 pin n. Carrier routing: OUT0-7 straight, OUT8-15 reversed:
    J2 pin = 16*chip + (out+1 if out < 8 else 24-out)
First bit shifted ends in U4/OUT15; last bit ends in U1/OUT0.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Iterable, List, Optional

from ...core.patterns.models import LEDStatus

logger = logging.getLogger(__name__)

_NUM_CHIPS = 4
_MAX_CHANNEL = 16 * _NUM_CHIPS          # 64


def carrier_j2_pin(chip: int, out: int) -> int:
    return 16 * chip + (out + 1 if out < 8 else 24 - out)


# J2 pin -> position in the 64-bit shift stream (0 = first bit clocked)
_SHIFT_POS: Dict[int, int] = {
    carrier_j2_pin(c, o): (_NUM_CHIPS - 1 - c) * 16 + (15 - o)
    for c in range(_NUM_CHIPS) for o in range(16)
}


def leds_to_bits(leds_on: Iterable[int]) -> List[int]:
    bits = [0] * _MAX_CHANNEL
    for n in leds_on:
        if 1 <= n <= _MAX_CHANNEL:
            bits[_SHIFT_POS[n]] = 1
    return bits


def _lit_leds(pattern, blink_on: bool) -> List[int]:
    if pattern is None:
        return []
    lit = []
    for n in range(1, _MAX_CHANNEL + 1):
        s = pattern.get_led_status(n)
        if s == LEDStatus.ACTIVE:
            if blink_on:
                lit.append(n)
        elif s in (LEDStatus.LOCKED, LEDStatus.VERIFIED):
            lit.append(n)
    return lit


class TLC5925DriverBase(ABC):
    @abstractmethod
    def on_led_status_change(self, led_num: int, status: LEDStatus) -> None: ...
    @abstractmethod
    def on_blink_tick(self, blink_on: bool) -> None: ...
    @abstractmethod
    def sync(self, pattern, blink_on: bool) -> None: ...
    @abstractmethod
    def all_off(self) -> None: ...
    @abstractmethod
    def cleanup(self) -> None: ...


class TLC5925Driver(TLC5925DriverBase):
    def __init__(self, sdi: int = 10, clk: int = 11, le: int = 25, oe: Optional[int] = 7,
                 startup_test: bool = True):
        self._sdi, self._clk, self._le, self._oe = sdi, clk, le, oe
        self._statuses: Dict[int, LEDStatus] = {}
        self._blink_on = True
        self._gpio = None
        self._closed = False
        self._init_gpio(startup_test)

    def _init_gpio(self, startup_test: bool) -> None:
        try:
            import RPi.GPIO as GPIO
        except Exception as e:
            logger.error("RPi.GPIO not importable (%s) - LEDs DISABLED. "
                         "sudo apt install python3-rpi.gpio", e)
            return
        try:
            self._gpio = GPIO
            if GPIO.getmode() is None:
                GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self._sdi, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self._clk, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self._le, GPIO.OUT, initial=GPIO.LOW)
            if self._oe is not None:
                GPIO.setup(self._oe, GPIO.OUT, initial=GPIO.HIGH)  # outputs off while clearing
            self._shift_and_latch(leds_to_bits([]))
            if self._oe is not None:
                GPIO.output(self._oe, GPIO.LOW)                     # enable outputs
            logger.info("TLC5925 x4 ready - SDI=%d CLK=%d LE=%d OE=%s",
                        self._sdi, self._clk, self._le, self._oe)
            if startup_test:
                self._startup_test()
        except Exception as e:
            logger.error("TLC5925 GPIO init failed (%s) - LEDs DISABLED", e)
            self._gpio = None

    def _startup_test(self) -> None:
        self._shift_and_latch(leds_to_bits(range(1, _MAX_CHANNEL + 1)))
        time.sleep(0.3)
        self._shift_and_latch(leds_to_bits([]))
        time.sleep(0.1)
        for n in range(1, _MAX_CHANNEL + 1):
            self._shift_and_latch(leds_to_bits([n]))
            time.sleep(0.025)
        self._shift_and_latch(leds_to_bits([]))
        logger.info("TLC5925 startup test complete")

    def _shift_and_latch(self, bits: List[int]) -> None:
        if self._gpio is None:
            return
        out, sdi, clk = self._gpio.output, self._sdi, self._clk
        out(clk, 0)
        for b in bits:
            out(sdi, b)
            out(clk, 1)
            out(clk, 0)
        out(sdi, 0)
        out(self._le, 1)
        out(self._le, 0)

    def sync(self, pattern, blink_on: bool) -> None:
        self._shift_and_latch(leds_to_bits(_lit_leds(pattern, blink_on)))

    def on_led_status_change(self, led_num: int, status: LEDStatus) -> None:
        if 1 <= led_num <= _MAX_CHANNEL:
            self._statuses[led_num] = status
            self._push()

    def on_blink_tick(self, blink_on: bool) -> None:
        self._blink_on = blink_on
        self._push()

    def _push(self) -> None:
        lit = [n for n, s in self._statuses.items()
               if (s == LEDStatus.ACTIVE and self._blink_on)
               or s in (LEDStatus.LOCKED, LEDStatus.VERIFIED)]
        self._shift_and_latch(leds_to_bits(lit))

    def all_off(self) -> None:
        self._statuses.clear()
        self._shift_and_latch(leds_to_bits([]))

    def cleanup(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.all_off()
        except Exception as e:
            logger.warning("all_off during cleanup failed: %s", e)
        if self._gpio is not None:
            self._gpio.cleanup()
            self._gpio = None


class MockTLC5925Driver(TLC5925DriverBase):
    def __init__(self, *args, **kwargs):
        self._statuses: Dict[int, LEDStatus] = {}
        self._blink_on = True

    def sync(self, pattern, blink_on: bool) -> None:
        logger.debug("MockTLC5925 lit=%s", _lit_leds(pattern, blink_on))

    def on_led_status_change(self, led_num: int, status: LEDStatus) -> None:
        if 1 <= led_num <= _MAX_CHANNEL:
            self._statuses[led_num] = status

    def on_blink_tick(self, blink_on: bool) -> None:
        self._blink_on = blink_on

    def all_off(self) -> None:
        self._statuses.clear()

    def cleanup(self) -> None:
        self.all_off()
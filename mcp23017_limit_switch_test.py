#!/usr/bin/env python3
"""Standalone MCP23017 LED sequence tester driven by a limit switch.

Behavior:
- Initializes MCP23017 (all 16 pins as outputs).
- Turns on a preset set of LEDs at startup.
- Blinks the current LED in a preset sequence.
- Each press on limit switch (default BCM GPIO14) advances to next sequence LED.

This is intentionally independent from the GUI so hardware behavior can be tested
in isolation on Raspberry Pi.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from typing import Iterable, List, Set

LOG = logging.getLogger("mcp23017_limit_switch_test")


class MCP23017Driver:
    """Minimal MCP23017 output driver (16 output pins)."""

    IODIRA = 0x00
    IODIRB = 0x01
    GPIOA = 0x12
    GPIOB = 0x13

    def __init__(self, bus_id: int, address: int, active_high: bool = True):
        self.bus_id = bus_id
        self.address = address
        self.active_high = active_high
        self._bus = None
        self._last_mask = None

    def start(self) -> None:
        from smbus2 import SMBus

        self._bus = SMBus(self.bus_id)
        self._bus.write_byte_data(self.address, self.IODIRA, 0x00)
        self._bus.write_byte_data(self.address, self.IODIRB, 0x00)
        self.write_mask(0x0000)

    def stop(self) -> None:
        if self._bus is None:
            return
        try:
            self.write_mask(0x0000)
            self._bus.close()
        finally:
            self._bus = None
            self._last_mask = None

    def write_mask(self, mask: int) -> None:
        if self._bus is None:
            return
        mask &= 0xFFFF
        if mask == self._last_mask:
            return

        value = mask if self.active_high else (~mask) & 0xFFFF
        low = value & 0xFF
        high = (value >> 8) & 0xFF

        self._bus.write_byte_data(self.address, self.GPIOA, low)
        self._bus.write_byte_data(self.address, self.GPIOB, high)
        self._last_mask = mask


class LimitSwitchPoller:
    """Debounced poller for a momentary limit switch on Raspberry Pi GPIO."""

    def __init__(self, gpio_pin: int, debounce_ms: int, poll_ms: int, active_low: bool = True):
        self._gpio_pin = gpio_pin
        self._debounce_s = max(1, debounce_ms) / 1000.0
        self._poll_s = max(1, poll_ms) / 1000.0
        self._active_low = active_low

        self._gpio = None
        self._raw_pressed = False
        self._stable_pressed = False
        self._last_raw_change = time.monotonic()

    def start(self) -> None:
        import RPi.GPIO as GPIO

        self._gpio = GPIO
        self._gpio.setwarnings(False)
        self._gpio.setmode(self._gpio.BCM)
        self._gpio.setup(self._gpio_pin, self._gpio.IN, pull_up_down=self._gpio.PUD_UP)

        self._raw_pressed = self.read_pressed()
        self._stable_pressed = self._raw_pressed
        self._last_raw_change = time.monotonic()

    def stop(self) -> None:
        if self._gpio is not None:
            self._gpio.cleanup(self._gpio_pin)
            self._gpio = None

    def read_pressed(self) -> bool:
        if self._gpio is None:
            return False
        raw = self._gpio.input(self._gpio_pin)
        if self._active_low:
            return raw == self._gpio.LOW
        return raw == self._gpio.HIGH

    def poll_pressed_event(self) -> bool:
        """Return True once per confirmed press edge."""
        now = time.monotonic()
        current = self.read_pressed()

        if current != self._raw_pressed:
            self._raw_pressed = current
            self._last_raw_change = now
            return False

        if current != self._stable_pressed and (now - self._last_raw_change) >= self._debounce_s:
            self._stable_pressed = current
            return self._stable_pressed

        return False

    @property
    def poll_interval_s(self) -> float:
        return self._poll_s


def _parse_led_list(raw: str) -> List[int]:
    raw = (raw or "").strip()
    if not raw:
        return []

    result: List[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        value = int(item)
        if not (0 <= value <= 15):
            raise ValueError(f"LED index {value} out of range [0..15]")
        result.append(value)
    return result


def _mask_from_pins(pins: Iterable[int]) -> int:
    mask = 0
    for pin in pins:
        mask |= 1 << pin
    return mask


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP23017 LED + limit switch standalone tester")
    parser.add_argument("--mcp-address", type=lambda v: int(v, 0), default=0x20, help="MCP23017 I2C address")
    parser.add_argument("--i2c-bus", type=int, default=1, help="I2C bus number")
    parser.add_argument("--active-low-outputs", action="store_true", help="Treat MCP outputs as active-LOW")

    parser.add_argument("--limit-switch-gpio", type=int, default=14, help="BCM GPIO pin for limit switch")
    parser.add_argument("--limit-switch-active-high", action="store_true", help="Treat press as GPIO HIGH")
    parser.add_argument("--debounce-ms", type=int, default=50, help="Switch debounce in ms")
    parser.add_argument("--poll-ms", type=int, default=5, help="Switch polling interval in ms")

    parser.add_argument(
        "--sequence",
        type=str,
        default="0,1,2,3,4,5,6,7",
        help="Comma-separated LED indices [0..15] advanced by each switch press",
    )
    parser.add_argument(
        "--initial-on",
        type=str,
        default="8,9",
        help="Comma-separated LED indices [0..15] that stay ON from startup",
    )
    parser.add_argument("--blink-ms", type=int, default=350, help="Blink interval for active LED")
    parser.add_argument("--loop", action="store_true", help="Loop back to sequence start after last LED")

    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    args = parse_args()

    try:
        sequence = _parse_led_list(args.sequence)
        initial_on = set(_parse_led_list(args.initial_on))
    except ValueError as exc:
        LOG.error("Invalid LED list: %s", exc)
        return 2

    if not sequence:
        LOG.error("Sequence is empty. Provide at least one LED index via --sequence")
        return 2

    mcp = MCP23017Driver(
        bus_id=args.i2c_bus,
        address=args.mcp_address,
        active_high=not args.active_low_outputs,
    )
    switch = LimitSwitchPoller(
        gpio_pin=args.limit_switch_gpio,
        debounce_ms=args.debounce_ms,
        poll_ms=args.poll_ms,
        active_low=not args.limit_switch_active_high,
    )

    running = True

    def _handle_stop(_sig, _frame) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    try:
        mcp.start()
        switch.start()
    except Exception as exc:
        LOG.exception("Hardware init failed: %s", exc)
        try:
            switch.stop()
        finally:
            mcp.stop()
        return 1

    LOG.info("MCP23017 ready: bus=%d address=0x%02X", args.i2c_bus, args.mcp_address)
    LOG.info(
        "Limit switch on BCM GPIO %d (%s)",
        args.limit_switch_gpio,
        "active LOW" if not args.limit_switch_active_high else "active HIGH",
    )
    LOG.info("Sequence=%s InitialON=%s", sequence, sorted(initial_on))

    seq_index = 0
    blink_on = True
    last_blink = time.monotonic()
    blink_interval = max(50, args.blink_ms) / 1000.0

    def _render() -> None:
        active_led = sequence[seq_index] if sequence else None
        steady: Set[int] = set(initial_on)

        # Keep active LED dedicated to blink state; remove from steady set if present.
        if active_led is not None and active_led in steady:
            steady.discard(active_led)

        lit = set(steady)
        if active_led is not None and blink_on:
            lit.add(active_led)

        mcp.write_mask(_mask_from_pins(lit))

    _render()

    try:
        while running:
            now = time.monotonic()

            if now - last_blink >= blink_interval:
                blink_on = not blink_on
                last_blink = now
                _render()

            if switch.poll_pressed_event():
                if seq_index < len(sequence) - 1:
                    seq_index += 1
                    blink_on = True
                    LOG.info("Switch press: advanced to sequence index %d (LED %d)", seq_index, sequence[seq_index])
                elif args.loop:
                    seq_index = 0
                    blink_on = True
                    LOG.info("Switch press: looped to sequence index 0 (LED %d)", sequence[seq_index])
                else:
                    LOG.info("Switch press: end of sequence reached (staying on LED %d)", sequence[seq_index])
                _render()

            time.sleep(switch.poll_interval_s)
    except Exception:
        LOG.exception("Unhandled runtime error")
        return 1
    finally:
        switch.stop()
        mcp.stop()
        LOG.info("Stopped and cleared MCP23017 outputs")

    return 0


if __name__ == "__main__":
    sys.exit(main())

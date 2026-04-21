#!/usr/bin/env python3
"""Standalone test for two I2C demux boards (TCA9548A) and LED expanders.

Use this script on Raspberry Pi to validate that both I2C demux boards are working,
channels are selectable, and LEDs connected through MCP23017 expanders respond.

Default test flow:
1. Select each demux board (0x70, 0x71)
2. Select each channel (0-7)
3. Probe configured MCP23017 address(es)
4. Run a short walking-LED pattern on each discovered MCP23017
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from typing import Iterable, List

LOG = logging.getLogger("two_i2c_demux_led_test")


@dataclass(frozen=True)
class DemuxTarget:
    demux_address: int
    channel: int


class TCA9548A:
    """Minimal TCA9548A demux/mux controller."""

    def __init__(self, bus, address: int):
        self._bus = bus
        self.address = address

    def select_channel(self, channel: int) -> None:
        if not (0 <= channel <= 7):
            raise ValueError(f"Invalid channel {channel}; must be 0..7")
        self._bus.write_byte(self.address, 1 << channel)

    def disable_all(self) -> None:
        self._bus.write_byte(self.address, 0x00)


class MCP23017:
    """Minimal MCP23017 output writer."""

    IODIRA = 0x00
    IODIRB = 0x01
    GPIOA = 0x12
    GPIOB = 0x13

    def __init__(self, bus, address: int, active_high: bool = True):
        self._bus = bus
        self.address = address
        self.active_high = active_high
        self._last_mask = None

    def initialize_outputs(self) -> None:
        self._bus.write_byte_data(self.address, self.IODIRA, 0x00)
        self._bus.write_byte_data(self.address, self.IODIRB, 0x00)
        self.write_mask(0x0000)

    def write_mask(self, mask: int) -> None:
        mask &= 0xFFFF
        if mask == self._last_mask:
            return

        value = mask if self.active_high else (~mask) & 0xFFFF
        low = value & 0xFF
        high = (value >> 8) & 0xFF

        self._bus.write_byte_data(self.address, self.GPIOA, low)
        self._bus.write_byte_data(self.address, self.GPIOB, high)
        self._last_mask = mask


def _parse_int_list(raw: str) -> List[int]:
    values: List[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        values.append(int(part, 0))
    return values


def _iter_targets(demux_addresses: Iterable[int], channels: Iterable[int]) -> List[DemuxTarget]:
    targets: List[DemuxTarget] = []
    for demux in demux_addresses:
        for channel in channels:
            targets.append(DemuxTarget(demux_address=demux, channel=channel))
    return targets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test two TCA9548A demux boards and MCP23017 LED outputs")
    parser.add_argument("--i2c-bus", type=int, default=1, help="I2C bus number (default: 1)")
    parser.add_argument(
        "--demux-addresses",
        type=str,
        default="0x70,0x71",
        help="Comma-separated demux addresses (default: 0x70,0x71)",
    )
    parser.add_argument(
        "--channels",
        type=str,
        default="0,1,2,3,4,5,6,7",
        help="Comma-separated channel list per demux (default: 0..7)",
    )
    parser.add_argument(
        "--mcp-addresses",
        type=str,
        default="0x20",
        help="Comma-separated MCP23017 addresses to test on each selected channel",
    )
    parser.add_argument(
        "--active-low-outputs",
        action="store_true",
        help="Treat MCP23017 outputs as active-LOW",
    )
    parser.add_argument(
        "--step-delay-ms",
        type=int,
        default=120,
        help="Delay between walking LED steps (default: 120ms)",
    )
    parser.add_argument(
        "--passes",
        type=int,
        default=1,
        help="How many full passes to run across all demux/channel/address combinations",
    )
    parser.add_argument(
        "--hold-final-ms",
        type=int,
        default=300,
        help="How long to hold all-on at end of each device test",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    args = parse_args()

    demux_addresses = _parse_int_list(args.demux_addresses)
    channels = _parse_int_list(args.channels)
    mcp_addresses = _parse_int_list(args.mcp_addresses)

    if not demux_addresses:
        LOG.error("No demux addresses provided")
        return 2
    if not channels:
        LOG.error("No channels provided")
        return 2
    if not mcp_addresses:
        LOG.error("No MCP23017 addresses provided")
        return 2
    if any(ch < 0 or ch > 7 for ch in channels):
        LOG.error("Channels must be in range 0..7")
        return 2

    step_delay_s = max(10, args.step_delay_ms) / 1000.0
    hold_final_s = max(0, args.hold_final_ms) / 1000.0

    try:
        from smbus2 import SMBus
    except ImportError:
        LOG.error("smbus2 is required. Install with: pip install smbus2")
        return 2

    targets = _iter_targets(demux_addresses, channels)
    LOG.info("Starting test with demux=%s channels=%s mcp=%s", demux_addresses, channels, mcp_addresses)

    with SMBus(args.i2c_bus) as bus:
        muxes = {addr: TCA9548A(bus, addr) for addr in demux_addresses}

        try:
            for test_pass in range(max(1, args.passes)):
                LOG.info("Pass %d/%d", test_pass + 1, max(1, args.passes))

                for target in targets:
                    mux = muxes[target.demux_address]
                    try:
                        mux.select_channel(target.channel)
                    except Exception as exc:
                        LOG.warning(
                            "Failed to select demux 0x%02X channel %d: %s",
                            target.demux_address,
                            target.channel,
                            exc,
                        )
                        continue

                    LOG.info("Testing demux=0x%02X channel=%d", target.demux_address, target.channel)

                    for mcp_addr in mcp_addresses:
                        dev = MCP23017(bus, mcp_addr, active_high=not args.active_low_outputs)
                        try:
                            dev.initialize_outputs()
                        except Exception as exc:
                            LOG.warning(
                                "No MCP23017 at demux=0x%02X channel=%d addr=0x%02X (%s)",
                                target.demux_address,
                                target.channel,
                                mcp_addr,
                                exc,
                            )
                            continue

                        LOG.info(
                            "Found MCP23017 at demux=0x%02X channel=%d addr=0x%02X",
                            target.demux_address,
                            target.channel,
                            mcp_addr,
                        )

                        for bit in range(16):
                            dev.write_mask(1 << bit)
                            time.sleep(step_delay_s)

                        dev.write_mask(0xFFFF)
                        time.sleep(hold_final_s)
                        dev.write_mask(0x0000)

        finally:
            for mux in muxes.values():
                try:
                    mux.disable_all()
                except Exception:
                    LOG.debug("Failed to clear demux 0x%02X", mux.address, exc_info=True)

    LOG.info("Test complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())

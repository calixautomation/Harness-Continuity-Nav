#!/usr/bin/env python3
"""
Interactive test script for debugging individual components.

Tests the HAL components (LED matrix, switch, buzzer) and pattern loader
using the 8x8 LED grid configuration.

Run from project root:
    python harness_nav/scripts/test/test_components.py
"""

import sys
import time
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from harness_nav.hal.led_matrix import LEDMatrix, MockLEDMatrix
from harness_nav.hal.switch import SwitchHandler, MockSwitchHandler, DualSwitchHandler, MockDualSwitchHandler
from harness_nav.hal.buzzer import BuzzerDriver, MockBuzzerDriver
from harness_nav.core.patterns import PatternLoader, Pattern


def run_led_matrix():
    """Test LED matrix initialization and basic operations."""
    print("\n=== Testing LED Matrix (8x8) ===")

    # Use mock for testing on PC
    matrix = MockLEDMatrix()
    matrix.init(8, 8, "P8_11")

    # Set some pixels
    print("Setting corner pixels...")
    matrix.set_pixel(0, 0, 0xFF0000)   # Red at top-left
    matrix.set_pixel(7, 0, 0x00FF00)   # Green at top-right
    matrix.set_pixel(0, 7, 0x0000FF)   # Blue at bottom-left
    matrix.set_pixel(7, 7, 0xFFFF00)   # Yellow at bottom-right
    matrix.show()

    print(f"  Pixel (0,0): {hex(matrix.get_pixel(0, 0))} (should be 0xff0000 - Red)")
    print(f"  Pixel (7,0): {hex(matrix.get_pixel(7, 0))} (should be 0xff00 - Green)")
    print(f"  Pixel (0,7): {hex(matrix.get_pixel(0, 7))} (should be 0xff - Blue)")
    print(f"  Pixel (7,7): {hex(matrix.get_pixel(7, 7))} (should be 0xffff00 - Yellow)")

    # Test brightness
    print("\nTesting brightness control...")
    matrix.set_brightness(128)
    print(f"  Brightness set to 128")

    # Clear
    matrix.clear()
    matrix.show()
    print("  Matrix cleared")

    print("LED Matrix test complete!")
    return True


def run_single_switch():
    """Test single switch handler."""
    print("\n=== Testing Single Switch Handler ===")

    switch = MockSwitchHandler("P9_12", debounce_ms=50)

    press_count = [0]

    def on_press():
        press_count[0] += 1
        print(f"  Switch pressed! Count: {press_count[0]}")

    switch.set_callback(on_press)
    switch.start_monitoring()

    print("Simulating 3 switch presses...")
    for i in range(3):
        switch.simulate_press()
        time.sleep(0.1)

    switch.stop_monitoring()
    print(f"Total presses detected: {press_count[0]}")

    success = press_count[0] == 3
    print(f"Single switch test {'PASSED' if success else 'FAILED'}!")
    return success


def run_dual_switch():
    """Test dual switch handler (limit switch + metal plate)."""
    print("\n=== Testing Dual Switch Handler ===")

    switch = MockDualSwitchHandler("P9_12", "P9_14", debounce_ms=50)

    lock_count = [0]
    verify_count = [0]

    def on_lock():
        lock_count[0] += 1
        print(f"  Limit switch triggered! (wire locked) Count: {lock_count[0]}")

    def on_verify():
        verify_count[0] += 1
        print(f"  Metal plate touched! (verified) Count: {verify_count[0]}")

    switch.set_lock_callback(on_lock)
    switch.set_verify_callback(on_verify)
    switch.start_monitoring()

    print("Simulating workflow: lock -> verify -> lock -> verify...")

    switch.simulate_lock_press()
    time.sleep(0.1)
    switch.simulate_verify_press()
    time.sleep(0.1)
    switch.simulate_lock_press()
    time.sleep(0.1)
    switch.simulate_verify_press()
    time.sleep(0.1)

    switch.stop_monitoring()

    print(f"Lock events: {lock_count[0]}, Verify events: {verify_count[0]}")

    success = lock_count[0] == 2 and verify_count[0] == 2
    print(f"Dual switch test {'PASSED' if success else 'FAILED'}!")
    return success


def run_buzzer():
    """Test buzzer driver with lock/verify tones."""
    print("\n=== Testing Buzzer Driver ===")

    buzzer = MockBuzzerDriver("P9_16")

    print("Playing lock tone (1500Hz, 100ms)...")
    buzzer.beep_lock()
    time.sleep(0.2)

    print("Playing verify tone (2500Hz, 200ms)...")
    buzzer.beep_verify()
    time.sleep(0.3)

    print("Playing error tone (500Hz, 500ms)...")
    buzzer.beep_error()
    time.sleep(0.6)

    print("Playing custom beep (1000Hz, 150ms)...")
    buzzer.beep_custom(1000, 150)
    time.sleep(0.2)

    print("Buzzer test complete!")
    return True


def run_pattern_loader():
    """Test pattern loading from JSON."""
    print("\n=== Testing Pattern Loader ===")

    patterns_file = PROJECT_ROOT / "harness_nav" / "data" / "patterns.json"
    print(f"Loading patterns from: {patterns_file}")

    if not patterns_file.exists():
        print(f"  ERROR: Patterns file not found!")
        return False

    loader = PatternLoader(str(patterns_file))
    patterns = loader.load()

    print(f"Found {len(patterns)} patterns:")

    for pattern in patterns:
        print(f"\n  Pattern: {pattern.name}")
        print(f"    ID: {pattern.id}")
        print(f"    Description: {pattern.description}")
        print(f"    LEDs: {pattern.leds}")
        print(f"    Total points: {len(pattern.leds)}")

    if patterns:
        # Test pattern operations
        print("\n  Testing pattern operations...")
        test_pattern = patterns[0]
        test_pattern.reset()

        # Select first LED
        if test_pattern.leds:
            first_led = test_pattern.leds[0]
            test_pattern.select_led(first_led)
            print(f"    Selected LED {first_led}: active_led = {test_pattern.active_led}")

            # Lock it
            test_pattern.lock_active_led()
            print(f"    Locked LED {first_led}: is_locked = {test_pattern.is_active_led_locked()}")

            # Verify it
            test_pattern.verify_active_led()
            verified, total = test_pattern.progress
            print(f"    Verified LED {first_led}: progress = {verified}/{total}")

    print("\nPattern loader test complete!")
    return True


def run_pattern_model():
    """Test Pattern model directly."""
    print("\n=== Testing Pattern Model ===")

    # Create a test pattern
    pattern = Pattern(
        id="test_pattern",
        name="Test Pattern",
        description="Testing pattern operations",
        leds=[1, 5, 10, 15, 64]
    )

    print(f"Created pattern: {pattern.name}")
    print(f"  LEDs: {pattern.leds}")

    # Test LED to XY conversion
    print("\n  LED to (x, y) conversion:")
    for led in pattern.leds:
        x, y = pattern.led_to_xy(led)
        back = pattern.xy_to_led(x, y)
        print(f"    LED {led:2d} -> ({x}, {y}) -> LED {back}")

    # Test workflow
    print("\n  Testing workflow:")
    pattern.reset()

    # Auto-select first
    next_led = pattern.auto_select_next()
    print(f"    Auto-selected: LED {next_led}")

    # Lock
    pattern.lock_active_led()
    print(f"    Locked: {pattern.is_active_led_locked()}")

    # Verify
    pattern.verify_active_led()
    print(f"    Verified: progress = {pattern.progress}")

    # Auto-select next
    next_led = pattern.auto_select_next()
    print(f"    Auto-selected next: LED {next_led}")

    # Complete all
    print("\n  Completing all LEDs...")
    while not pattern.is_complete:
        pattern.lock_active_led()
        pattern.verify_active_led()
        pattern.auto_select_next()

    print(f"    Pattern complete: {pattern.is_complete}")
    print(f"    Final progress: {pattern.progress}")

    print("\nPattern model test complete!")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("LED Pattern Tester - Component Tests (8x8 Grid)")
    print("=" * 60)

    tests = [
        ("LED Matrix", run_led_matrix),
        ("Single Switch", run_single_switch),
        ("Dual Switch", run_dual_switch),
        ("Buzzer", run_buzzer),
        ("Pattern Loader", run_pattern_loader),
        ("Pattern Model", run_pattern_model),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\nERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {name:20s} [{status}]")
        if success:
            passed += 1
        else:
            failed += 1

    print("-" * 60)
    print(f"  Total: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

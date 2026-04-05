"""Tests for Hardware Abstraction Layer modules (8x8 grid)."""

import pytest
from unittest.mock import MagicMock

from harness_nav.hal.led_matrix import MockLEDMatrix
from harness_nav.hal.switch import MockSwitchHandler, MockDualSwitchHandler
from harness_nav.hal.buzzer import MockBuzzerDriver


class TestMockLEDMatrix:
    """Test cases for MockLEDMatrix class (8x8 grid)."""

    def test_init_and_dimensions(self):
        """Test initialization and dimensions."""
        matrix = MockLEDMatrix()
        matrix.init(8, 8, "P8_11")

        assert matrix.width == 8
        assert matrix.height == 8

    def test_set_pixel(self):
        """Test setting individual pixels."""
        matrix = MockLEDMatrix()
        matrix.init(8, 8, "P8_11")

        matrix.set_pixel(0, 0, 0xFF0000)
        assert matrix.get_pixel(0, 0) == 0xFF0000

        matrix.set_pixel(7, 7, 0x00FF00)
        assert matrix.get_pixel(7, 7) == 0x00FF00

    def test_set_pattern(self):
        """Test setting multiple pixels at once."""
        matrix = MockLEDMatrix()
        matrix.init(8, 8, "P8_11")

        points = [(0, 0), (3, 3), (7, 7)]
        matrix.set_pattern(points, 0x0000FF)

        for x, y in points:
            assert matrix.get_pixel(x, y) == 0x0000FF

    def test_clear(self):
        """Test clearing the matrix."""
        matrix = MockLEDMatrix()
        matrix.init(8, 8, "P8_11")

        matrix.set_pixel(3, 3, 0xFF0000)
        matrix.clear()

        assert matrix.get_pixel(3, 3) == 0

    def test_show_callback(self):
        """Test show callback mechanism."""
        matrix = MockLEDMatrix()
        matrix.init(8, 8, "P8_11")

        callback = MagicMock()
        matrix.set_show_callback(callback)

        matrix.set_pixel(3, 3, 0xFF0000)
        matrix.show()

        callback.assert_called_once()

    def test_out_of_bounds(self):
        """Test out of bounds pixel access."""
        matrix = MockLEDMatrix()
        matrix.init(8, 8, "P8_11")

        # Should not raise, but should be ignored
        matrix.set_pixel(100, 100, 0xFF0000)
        assert matrix.get_pixel(100, 100) == 0

    def test_brightness(self):
        """Test brightness control."""
        matrix = MockLEDMatrix()
        matrix.init(8, 8, "P8_11")

        matrix.set_brightness(128)
        # Should not raise


class TestMockSwitchHandler:
    """Test cases for MockSwitchHandler class."""

    def test_monitoring(self):
        """Test start/stop monitoring."""
        switch = MockSwitchHandler("P9_12", debounce_ms=50)

        switch.start_monitoring()
        assert switch._monitoring

        switch.stop_monitoring()
        assert not switch._monitoring

    def test_simulate_press(self):
        """Test simulating a switch press."""
        switch = MockSwitchHandler("P9_12")
        callback = MagicMock()
        switch.set_callback(callback)
        switch.start_monitoring()

        switch.simulate_press()

        callback.assert_called_once()

    def test_simulate_press_not_monitoring(self):
        """Test that simulate_press does nothing when not monitoring."""
        switch = MockSwitchHandler("P9_12")
        callback = MagicMock()
        switch.set_callback(callback)

        switch.simulate_press()

        callback.assert_not_called()


class TestMockDualSwitchHandler:
    """Test cases for MockDualSwitchHandler class (two-stage verification)."""

    def test_monitoring(self):
        """Test start/stop monitoring."""
        switch = MockDualSwitchHandler("P9_12", "P9_14", debounce_ms=50)

        switch.start_monitoring()
        assert switch._monitoring

        switch.stop_monitoring()
        assert not switch._monitoring

    def test_lock_callback(self):
        """Test limit switch (lock) callback."""
        switch = MockDualSwitchHandler("P9_12", "P9_14")
        lock_callback = MagicMock()
        switch.set_lock_callback(lock_callback)
        switch.start_monitoring()

        switch.simulate_lock_press()

        lock_callback.assert_called_once()

    def test_verify_callback(self):
        """Test metal plate (verify) callback."""
        switch = MockDualSwitchHandler("P9_12", "P9_14")
        verify_callback = MagicMock()
        switch.set_verify_callback(verify_callback)
        switch.start_monitoring()

        switch.simulate_verify_press()

        verify_callback.assert_called_once()

    def test_both_callbacks(self):
        """Test both callbacks work independently."""
        switch = MockDualSwitchHandler("P9_12", "P9_14")
        lock_callback = MagicMock()
        verify_callback = MagicMock()
        switch.set_lock_callback(lock_callback)
        switch.set_verify_callback(verify_callback)
        switch.start_monitoring()

        switch.simulate_lock_press()
        switch.simulate_verify_press()
        switch.simulate_lock_press()

        assert lock_callback.call_count == 2
        assert verify_callback.call_count == 1


class TestMockBuzzerDriver:
    """Test cases for MockBuzzerDriver class (lock/verify tones)."""

    def test_beep_lock(self):
        """Test lock beep (1500Hz, 100ms)."""
        buzzer = MockBuzzerDriver(pwm_pin="P9_16")
        callback = MagicMock()
        buzzer.set_beep_callback(callback)

        buzzer.beep_lock()

        callback.assert_called_once()
        # Check it was called with lock parameters
        call_args = callback.call_args[0]
        assert call_args[0] == "lock"

    def test_beep_verify(self):
        """Test verify beep (2500Hz, 200ms)."""
        buzzer = MockBuzzerDriver(pwm_pin="P9_16")
        callback = MagicMock()
        buzzer.set_beep_callback(callback)

        buzzer.beep_verify()

        callback.assert_called_once()
        call_args = callback.call_args[0]
        assert call_args[0] == "verify"

    def test_beep_error(self):
        """Test error beep."""
        buzzer = MockBuzzerDriver(
            pwm_pin="P9_16",
            error_freq=500,
            error_duration=500
        )
        callback = MagicMock()
        buzzer.set_beep_callback(callback)

        buzzer.beep_error()

        callback.assert_called_once_with("error", 500, 500)

    def test_beep_custom(self):
        """Test custom beep."""
        buzzer = MockBuzzerDriver(pwm_pin="P9_16")
        callback = MagicMock()
        buzzer.set_beep_callback(callback)

        buzzer.beep_custom(1500, 300)

        callback.assert_called_once_with("custom", 1500, 300)

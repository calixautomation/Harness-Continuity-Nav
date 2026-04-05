"""Tests for pattern models and loader (8x8 JSON-based)."""

import pytest
import json
import tempfile
from pathlib import Path

from harness_nav.core.patterns.pattern_loader import PatternLoader
from harness_nav.core.patterns.models import Pattern, LEDStatus, TestState


class TestPattern:
    """Test cases for Pattern class (8x8 LED grid)."""

    def test_create_pattern(self):
        """Test creating a valid pattern."""
        pattern = Pattern(
            id="test_1",
            name="Test Pattern",
            description="A test pattern",
            leds=[1, 5, 10, 64]
        )

        assert pattern.id == "test_1"
        assert pattern.name == "Test Pattern"
        assert pattern.leds == [1, 5, 10, 64]
        assert len(pattern.leds) == 4

    def test_led_to_xy_conversion(self):
        """Test LED number to (x, y) coordinate conversion."""
        pattern = Pattern(id="test", name="Test", description="", leds=[1])

        # LED 1 is at (0, 0)
        assert pattern.led_to_xy(1) == (0, 0)

        # LED 8 is at (7, 0)
        assert pattern.led_to_xy(8) == (7, 0)

        # LED 9 is at (0, 1)
        assert pattern.led_to_xy(9) == (0, 1)

        # LED 64 is at (7, 7)
        assert pattern.led_to_xy(64) == (7, 7)

        # LED 37 is at (4, 4)
        assert pattern.led_to_xy(37) == (4, 4)

    def test_xy_to_led_conversion(self):
        """Test (x, y) coordinate to LED number conversion."""
        pattern = Pattern(id="test", name="Test", description="", leds=[1])

        assert pattern.xy_to_led(0, 0) == 1
        assert pattern.xy_to_led(7, 0) == 8
        assert pattern.xy_to_led(0, 1) == 9
        assert pattern.xy_to_led(7, 7) == 64

    def test_roundtrip_conversion(self):
        """Test LED -> (x,y) -> LED roundtrip."""
        pattern = Pattern(id="test", name="Test", description="", leds=[1])

        for led in range(1, 65):
            x, y = pattern.led_to_xy(led)
            back = pattern.xy_to_led(x, y)
            assert back == led, f"LED {led} -> ({x},{y}) -> {back}"

    def test_reset(self):
        """Test resetting pattern state."""
        pattern = Pattern(id="test", name="Test", description="", leds=[1, 2, 3])

        # Modify state
        pattern.select_led(1)
        pattern.lock_active_led()
        pattern.verify_active_led()

        # Reset
        pattern.reset()

        assert pattern.active_led == 0
        assert pattern.verified_count == 0
        assert len(pattern.verified_leds) == 0

    def test_select_led(self):
        """Test selecting an LED."""
        pattern = Pattern(id="test", name="Test", description="", leds=[1, 5, 10])

        # Select valid LED
        assert pattern.select_led(5) == True
        assert pattern.active_led == 5

        # Select LED not in pattern
        assert pattern.select_led(99) == False
        assert pattern.active_led == 5  # Unchanged

    def test_lock_active_led(self):
        """Test locking the active LED."""
        pattern = Pattern(id="test", name="Test", description="", leds=[1, 5, 10])

        # Can't lock without active LED
        assert pattern.lock_active_led() == False

        # Select and lock
        pattern.select_led(5)
        assert pattern.lock_active_led() == True
        assert pattern.is_active_led_locked() == True

        # Can't lock again
        assert pattern.lock_active_led() == False

    def test_verify_active_led(self):
        """Test verifying the active LED."""
        pattern = Pattern(id="test", name="Test", description="", leds=[1, 5, 10])

        # Select LED
        pattern.select_led(5)

        # Can't verify without locking first
        assert pattern.verify_active_led() == False

        # Lock then verify
        pattern.lock_active_led()
        assert pattern.verify_active_led() == True

        # LED should be verified
        assert 5 in pattern.verified_leds
        assert pattern.active_led == 0  # Cleared after verify

    def test_auto_select_next(self):
        """Test auto-selecting the next pending LED."""
        pattern = Pattern(id="test", name="Test", description="", leds=[1, 5, 10])

        # Auto-select first
        next_led = pattern.auto_select_next()
        assert next_led == 1
        assert pattern.active_led == 1

        # Verify and auto-select next
        pattern.lock_active_led()
        pattern.verify_active_led()
        next_led = pattern.auto_select_next()
        assert next_led == 5

    def test_progress(self):
        """Test progress tracking."""
        pattern = Pattern(id="test", name="Test", description="", leds=[1, 5, 10])

        assert pattern.progress == (0, 3)
        assert pattern.verified_count == 0

        # Verify one
        pattern.select_led(1)
        pattern.lock_active_led()
        pattern.verify_active_led()

        assert pattern.progress == (1, 3)
        assert pattern.verified_count == 1

    def test_is_complete(self):
        """Test completion detection."""
        pattern = Pattern(id="test", name="Test", description="", leds=[1, 5])

        assert pattern.is_complete == False

        # Verify all
        for led in pattern.leds:
            pattern.select_led(led)
            pattern.lock_active_led()
            pattern.verify_active_led()

        assert pattern.is_complete == True

    def test_get_led_status(self):
        """Test getting LED status."""
        pattern = Pattern(id="test", name="Test", description="", leds=[1, 5, 10])

        # LED not in pattern
        assert pattern.get_led_status(99) == LEDStatus.OFF

        # Pending LED
        assert pattern.get_led_status(5) == LEDStatus.PENDING

        # Active LED
        pattern.select_led(5)
        assert pattern.get_led_status(5) == LEDStatus.ACTIVE

        # Locked LED
        pattern.lock_active_led()
        assert pattern.get_led_status(5) == LEDStatus.LOCKED

        # Verified LED
        pattern.verify_active_led()
        assert pattern.get_led_status(5) == LEDStatus.VERIFIED


class TestPatternLoader:
    """Test cases for PatternLoader class (JSON-based)."""

    def test_load_valid_json(self, tmp_path):
        """Test loading a valid JSON file."""
        patterns_data = {
            "patterns": [
                {
                    "id": "test_1",
                    "name": "Test Pattern 1",
                    "description": "First test pattern",
                    "leds": [1, 2, 3, 4]
                },
                {
                    "id": "test_2",
                    "name": "Test Pattern 2",
                    "description": "Second test pattern",
                    "leds": [10, 20, 30]
                }
            ]
        }

        json_file = tmp_path / "patterns.json"
        json_file.write_text(json.dumps(patterns_data))

        loader = PatternLoader(str(json_file))
        patterns = loader.load()

        assert len(patterns) == 2
        assert patterns[0].id == "test_1"
        assert patterns[0].leds == [1, 2, 3, 4]
        assert patterns[1].id == "test_2"

    def test_load_missing_file(self, tmp_path):
        """Test loading a non-existent file raises error."""
        loader = PatternLoader(str(tmp_path / "nonexistent.json"))

        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_get_pattern_by_id(self, tmp_path):
        """Test getting a specific pattern by ID."""
        patterns_data = {
            "patterns": [
                {"id": "p1", "name": "Pattern 1", "description": "", "leds": [1]},
                {"id": "p2", "name": "Pattern 2", "description": "", "leds": [2]},
            ]
        }

        json_file = tmp_path / "patterns.json"
        json_file.write_text(json.dumps(patterns_data))

        loader = PatternLoader(str(json_file))
        loader.load()

        pattern = loader.get_pattern_by_id("p2")
        assert pattern is not None
        assert pattern.name == "Pattern 2"

        # Non-existent ID
        assert loader.get_pattern_by_id("nonexistent") is None

    def test_empty_patterns(self, tmp_path):
        """Test loading file with no patterns."""
        patterns_data = {"patterns": []}

        json_file = tmp_path / "patterns.json"
        json_file.write_text(json.dumps(patterns_data))

        loader = PatternLoader(str(json_file))
        patterns = loader.load()

        assert len(patterns) == 0


class TestLEDStatus:
    """Test cases for LEDStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert LEDStatus.OFF is not None
        assert LEDStatus.PENDING is not None
        assert LEDStatus.ACTIVE is not None
        assert LEDStatus.LOCKED is not None
        assert LEDStatus.VERIFIED is not None
        assert LEDStatus.ERROR is not None


class TestTestState:
    """Test cases for TestState enum."""

    def test_state_values(self):
        """Test all state values exist."""
        assert TestState.IDLE is not None
        assert TestState.PATTERN_LOADED is not None
        assert TestState.TESTING is not None
        assert TestState.COMPLETE is not None
        assert TestState.ERROR is not None

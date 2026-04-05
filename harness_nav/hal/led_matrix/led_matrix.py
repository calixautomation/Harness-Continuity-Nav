"""LED Matrix driver with mock implementation for development."""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class LEDMatrixBase(ABC):
    """Abstract base class for LED matrix drivers."""

    @abstractmethod
    def init(self, width: int, height: int, gpio_pin: str) -> None:
        """Initialize the LED matrix."""
        pass

    @abstractmethod
    def set_pixel(self, x: int, y: int, color: int) -> None:
        """Set a single pixel color. Color is 24-bit RGB (0xRRGGBB)."""
        pass

    @abstractmethod
    def set_pattern(self, points: List[Tuple[int, int]], color: int) -> None:
        """Set multiple pixels to the same color."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the entire matrix (all pixels off)."""
        pass

    @abstractmethod
    def show(self) -> None:
        """Push the buffer to the physical LEDs."""
        pass

    @abstractmethod
    def get_pixel(self, x: int, y: int) -> int:
        """Get the current color of a pixel."""
        pass

    @abstractmethod
    def set_brightness(self, brightness: int) -> None:
        """Set global brightness (0-255)."""
        pass


class MockLEDMatrix(LEDMatrixBase):
    """Mock LED matrix for development and testing on non-BeagleBone systems."""

    def __init__(self):
        self._width = 0
        self._height = 0
        self._buffer: List[List[int]] = []
        self._brightness = 255
        self._initialized = False
        self._show_callback: Optional[callable] = None

    def init(self, width: int, height: int, gpio_pin: str) -> None:
        """Initialize the mock LED matrix."""
        self._width = width
        self._height = height
        self._buffer = [[0 for _ in range(width)] for _ in range(height)]
        self._initialized = True
        logger.info(f"MockLEDMatrix initialized: {width}x{height} on pin {gpio_pin}")

    def set_pixel(self, x: int, y: int, color: int) -> None:
        """Set a single pixel color."""
        if not self._initialized:
            raise RuntimeError("LED matrix not initialized")
        if 0 <= x < self._width and 0 <= y < self._height:
            self._buffer[y][x] = color
        else:
            logger.warning(f"Pixel ({x}, {y}) out of bounds")

    def set_pattern(self, points: List[Tuple[int, int]], color: int) -> None:
        """Set multiple pixels to the same color."""
        for x, y in points:
            self.set_pixel(x, y, color)

    def clear(self) -> None:
        """Clear the entire matrix."""
        if not self._initialized:
            raise RuntimeError("LED matrix not initialized")
        for y in range(self._height):
            for x in range(self._width):
                self._buffer[y][x] = 0

    def show(self) -> None:
        """Push buffer to display (mock: triggers callback if set)."""
        if not self._initialized:
            raise RuntimeError("LED matrix not initialized")
        logger.debug("MockLEDMatrix: show() called")
        if self._show_callback:
            self._show_callback(self._buffer)

    def get_pixel(self, x: int, y: int) -> int:
        """Get the current color of a pixel."""
        if not self._initialized:
            raise RuntimeError("LED matrix not initialized")
        if 0 <= x < self._width and 0 <= y < self._height:
            return self._buffer[y][x]
        return 0

    def set_brightness(self, brightness: int) -> None:
        """Set global brightness (0-255)."""
        self._brightness = max(0, min(255, brightness))
        logger.info(f"MockLEDMatrix brightness set to {self._brightness}")

    def set_show_callback(self, callback: callable) -> None:
        """Set callback to be called on show() for GUI synchronization."""
        self._show_callback = callback

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def buffer(self) -> List[List[int]]:
        """Get the current buffer (for testing/debugging)."""
        return self._buffer

    def cleanup(self) -> None:
        """Clean up resources (no-op for mock)."""
        self.clear()
        logger.debug("MockLEDMatrix cleaned up")


class LEDMatrix(LEDMatrixBase):
    """
    Real LED matrix driver for BeagleBone Black with WS2812 LEDs.

    This implementation uses the BeagleBone PRU for precise timing.
    On non-BeagleBone systems, this will fall back to MockLEDMatrix.
    """

    def __init__(self):
        self._mock: Optional[MockLEDMatrix] = None
        self._width = 0
        self._height = 0
        self._gpio_pin = ""
        self._brightness = 255
        self._use_mock = False
        self._buffer: List[List[int]] = []

        # Panel layout configuration
        self._panel_width = 8
        self._panel_height = 8
        self._panels_x = 8
        self._panels_y = 8
        self._serpentine_panels = True
        self._serpentine_internal = True

        # Hardware library instances (set during init)
        self._neopixel = None
        self._ledscape = None
        self._use_neopixel = False
        self._use_ledscape = False

    def init(self, width: int, height: int, gpio_pin: str) -> None:
        """Initialize the LED matrix."""
        self._width = width
        self._height = height
        self._gpio_pin = gpio_pin
        self._buffer = [[0 for _ in range(width)] for _ in range(height)]

        try:
            # Try to import BeagleBone PRU library
            # This will fail on non-BeagleBone systems
            import Adafruit_BBIO.GPIO as GPIO  # noqa
            self._setup_pru()
            logger.info(f"LEDMatrix initialized with PRU: {width}x{height}")
        except ImportError:
            logger.warning("Adafruit_BBIO not available, using mock implementation")
            self._use_mock = True
            self._mock = MockLEDMatrix()
            self._mock.init(width, height, gpio_pin)

    def _setup_pru(self) -> None:
        """Setup PRU for WS2812 timing using rpi_ws281x compatible library."""
        try:
            # Option 1: Use Adafruit NeoPixel library (if available)
            from neopixel import NeoPixel
            import board

            # Map BeagleBone pin to board pin
            pin_map = {
                "P8_11": board.P8_11,
                "P9_22": board.P9_22,
            }
            pin = pin_map.get(self._gpio_pin)
            if pin:
                total_leds = self._width * self._height
                self._neopixel = NeoPixel(pin, total_leds, auto_write=False)
                self._use_neopixel = True
                logger.info("Using NeoPixel library for LED control")
                return
        except ImportError:
            pass

        try:
            # Option 2: Use LEDscape library (BeagleBone specific)
            # LEDscape uses PRU for precise timing
            import ledscape

            total_leds = self._width * self._height
            self._ledscape = ledscape.LEDscape(total_leds)
            self._use_ledscape = True
            logger.info("Using LEDscape library for LED control")
            return
        except ImportError:
            pass

        # If no library available, fall back to mock
        logger.warning("No LED library available, falling back to mock")
        self._use_mock = True
        self._mock = MockLEDMatrix()
        self._mock.init(self._width, self._height, self._gpio_pin)

    def _xy_to_led_index(self, x: int, y: int) -> int:
        """
        Convert (x, y) coordinates to physical LED index.

        Accounts for:
        - Tiled 8x8 panel arrangement
        - Serpentine wiring between panels
        - Serpentine LED order within panels
        """
        # Determine which panel this pixel belongs to
        panel_x = x // self._panel_width
        panel_y = y // self._panel_height

        # Position within the panel
        local_x = x % self._panel_width
        local_y = y % self._panel_height

        # Calculate panel index based on serpentine pattern
        if self._serpentine_panels and (panel_y % 2 == 1):
            # Odd rows go right to left
            panel_index = panel_y * self._panels_x + (self._panels_x - 1 - panel_x)
        else:
            # Even rows go left to right
            panel_index = panel_y * self._panels_x + panel_x

        # Calculate LED index within panel (also serpentine)
        if self._serpentine_internal and (local_y % 2 == 1):
            # Odd rows within panel go right to left
            local_index = local_y * self._panel_width + (self._panel_width - 1 - local_x)
        else:
            # Even rows within panel go left to right
            local_index = local_y * self._panel_width + local_x

        # Total index
        leds_per_panel = self._panel_width * self._panel_height
        return panel_index * leds_per_panel + local_index

    def set_pixel(self, x: int, y: int, color: int) -> None:
        """Set a single pixel color."""
        if self._use_mock and self._mock:
            self._mock.set_pixel(x, y, color)
            return

        if 0 <= x < self._width and 0 <= y < self._height:
            self._buffer[y][x] = color

    def set_pattern(self, points: List[Tuple[int, int]], color: int) -> None:
        """Set multiple pixels to the same color."""
        if self._use_mock and self._mock:
            self._mock.set_pattern(points, color)
            return

        for x, y in points:
            self.set_pixel(x, y, color)

    def clear(self) -> None:
        """Clear the entire matrix."""
        if self._use_mock and self._mock:
            self._mock.clear()
            return

        for y in range(self._height):
            for x in range(self._width):
                self._buffer[y][x] = 0

    def show(self) -> None:
        """Push buffer to physical LEDs."""
        if self._use_mock and self._mock:
            self._mock.show()
            return

        # Convert buffer to linear array with coordinate mapping
        led_data = []
        for y in range(self._height):
            for x in range(self._width):
                idx = self._xy_to_led_index(x, y)
                color = self._buffer[y][x]
                # Apply brightness
                r = ((color >> 16) & 0xFF) * self._brightness // 255
                g = ((color >> 8) & 0xFF) * self._brightness // 255
                b = (color & 0xFF) * self._brightness // 255
                led_data.append((idx, (r << 16) | (g << 8) | b))

        # Sort by LED index and send to PRU
        led_data.sort(key=lambda x: x[0])
        self._send_to_pru([color for _, color in led_data])

    def _send_to_pru(self, data: List[int]) -> None:
        """Send LED data to hardware using available library."""
        if self._use_neopixel and self._neopixel:
            # NeoPixel library expects (R, G, B) tuples
            for i, color in enumerate(data):
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF
                self._neopixel[i] = (r, g, b)
            self._neopixel.show()

        elif self._use_ledscape and self._ledscape:
            # LEDscape uses 32-bit colors directly
            self._ledscape.draw(data)
            self._ledscape.wait()

    def get_pixel(self, x: int, y: int) -> int:
        """Get the current color of a pixel."""
        if self._use_mock and self._mock:
            return self._mock.get_pixel(x, y)

        if 0 <= x < self._width and 0 <= y < self._height:
            return self._buffer[y][x]
        return 0

    def set_brightness(self, brightness: int) -> None:
        """Set global brightness (0-255)."""
        self._brightness = max(0, min(255, brightness))
        if self._use_mock and self._mock:
            self._mock.set_brightness(brightness)

    def set_show_callback(self, callback: callable) -> None:
        """Set callback for GUI synchronization (mock mode only)."""
        if self._mock:
            self._mock.set_show_callback(callback)

    def configure_panel_layout(
        self,
        panel_width: int = 8,
        panel_height: int = 8,
        panels_x: int = 8,
        panels_y: int = 8,
        serpentine_panels: bool = True,
        serpentine_internal: bool = True
    ) -> None:
        """Configure the physical panel layout for coordinate mapping."""
        self._panel_width = panel_width
        self._panel_height = panel_height
        self._panels_x = panels_x
        self._panels_y = panels_y
        self._serpentine_panels = serpentine_panels
        self._serpentine_internal = serpentine_internal

    def cleanup(self) -> None:
        """Clean up hardware resources."""
        self.clear()
        self.show()
        if self._neopixel:
            self._neopixel.deinit()
        if self._ledscape:
            self._ledscape.close()

"""Buzzer driver for audio feedback."""

from abc import ABC, abstractmethod
from typing import Optional
import threading
import time
import logging

logger = logging.getLogger(__name__)


class BuzzerDriverBase(ABC):
    """Abstract base class for buzzer drivers."""

    @abstractmethod
    def beep_lock(self) -> None:
        """Play lock tone (short beep when wire is locked in slot)."""
        pass

    @abstractmethod
    def beep_verify(self) -> None:
        """Play verify/success tone (when circuit complete)."""
        pass

    @abstractmethod
    def beep_error(self) -> None:
        """Play error tone (long low pitch)."""
        pass

    @abstractmethod
    def beep_custom(self, frequency: int, duration_ms: int) -> None:
        """Play custom tone."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop any playing tone."""
        pass

    # Alias for backward compatibility
    def beep_success(self) -> None:
        """Alias for beep_verify()."""
        self.beep_verify()


class MockBuzzerDriver(BuzzerDriverBase):
    """Mock buzzer driver for development and testing."""

    def __init__(
        self,
        pwm_pin: str = "",
        lock_freq: int = 1500,
        lock_duration: int = 100,
        verify_freq: int = 2500,
        verify_duration: int = 200,
        error_freq: int = 500,
        error_duration: int = 500
    ):
        self._pwm_pin = pwm_pin
        self._lock_freq = lock_freq
        self._lock_duration = lock_duration
        self._verify_freq = verify_freq
        self._verify_duration = verify_duration
        self._error_freq = error_freq
        self._error_duration = error_duration
        self._playing = False
        self._beep_callback: Optional[callable] = None
        logger.info(f"MockBuzzerDriver created for pin {pwm_pin}")

    def beep_lock(self) -> None:
        """Play lock tone (short beep when wire is locked)."""
        logger.info(f"MockBuzzer: LOCK beep ({self._lock_freq}Hz, {self._lock_duration}ms)")
        self._trigger_callback("lock", self._lock_freq, self._lock_duration)

    def beep_verify(self) -> None:
        """Play verify/success tone (circuit complete)."""
        logger.info(f"MockBuzzer: VERIFY beep ({self._verify_freq}Hz, {self._verify_duration}ms)")
        self._trigger_callback("verify", self._verify_freq, self._verify_duration)

    def beep_error(self) -> None:
        """Play error tone."""
        logger.info(f"MockBuzzer: ERROR beep ({self._error_freq}Hz, {self._error_duration}ms)")
        self._trigger_callback("error", self._error_freq, self._error_duration)

    def beep_custom(self, frequency: int, duration_ms: int) -> None:
        """Play custom tone."""
        logger.info(f"MockBuzzer: CUSTOM beep ({frequency}Hz, {duration_ms}ms)")
        self._trigger_callback("custom", frequency, duration_ms)

    def stop(self) -> None:
        """Stop any playing tone."""
        self._playing = False
        logger.debug("MockBuzzer: stopped")

    def _trigger_callback(self, tone_type: str, freq: int, duration: int) -> None:
        """Trigger callback if set (for GUI visualization)."""
        if self._beep_callback:
            self._beep_callback(tone_type, freq, duration)

    def set_beep_callback(self, callback: callable) -> None:
        """Set callback for beep events (for GUI feedback visualization)."""
        self._beep_callback = callback


class BuzzerDriver(BuzzerDriverBase):
    """
    Buzzer driver for Raspberry Pi using RPi.GPIO software PWM.

    GPIO18 (physical pin 12) supports hardware PWM on the Pi, but software
    PWM via RPi.GPIO is sufficient for short audio tones (1500–2500 Hz).
    Falls back to MockBuzzerDriver if RPi.GPIO is unavailable.
    """

    def __init__(
        self,
        pwm_pin: int,
        lock_freq: int = 1500,
        lock_duration: int = 100,
        verify_freq: int = 2500,
        verify_duration: int = 200,
        error_freq: int = 500,
        error_duration: int = 500
    ):
        self._pwm_pin = pwm_pin
        self._lock_freq = lock_freq
        self._lock_duration = lock_duration
        self._verify_freq = verify_freq
        self._verify_duration = verify_duration
        self._error_freq = error_freq
        self._error_duration = error_duration
        self._playing = False
        self._stop_event = threading.Event()
        self._play_thread: Optional[threading.Thread] = None
        self._use_mock = False
        self._mock: Optional[MockBuzzerDriver] = None
        self._pwm_instance = None
        self._gpio = None

        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
            if GPIO.getmode() is None:
                GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(pwm_pin, GPIO.OUT)
            # Create PWM instance at an arbitrary starting frequency; changed per tone.
            self._pwm_instance = GPIO.PWM(pwm_pin, 1000)
            logger.info("BuzzerDriver initialised on GPIO%d (RPi.GPIO software PWM)", pwm_pin)
        except Exception as e:
            logger.warning("RPi.GPIO PWM unavailable (%s) — buzzer using mock", e)
            self._use_mock = True
            self._mock = MockBuzzerDriver(
                pwm_pin, lock_freq, lock_duration, verify_freq, verify_duration,
                error_freq, error_duration
            )

    def beep_lock(self) -> None:
        if self._use_mock and self._mock:
            self._mock.beep_lock()
            return
        self.beep_custom(self._lock_freq, self._lock_duration)

    def beep_verify(self) -> None:
        if self._use_mock and self._mock:
            self._mock.beep_verify()
            return
        self.beep_custom(self._verify_freq, self._verify_duration)

    def beep_error(self) -> None:
        if self._use_mock and self._mock:
            self._mock.beep_error()
            return
        self.beep_custom(self._error_freq, self._error_duration)

    def beep_custom(self, frequency: int, duration_ms: int) -> None:
        """Play a tone at the given frequency for duration_ms milliseconds."""
        if self._use_mock and self._mock:
            self._mock.beep_custom(frequency, duration_ms)
            return

        self.stop()
        self._stop_event.clear()
        self._play_thread = threading.Thread(
            target=self._play_tone,
            args=(frequency, duration_ms),
            daemon=True,
            name="buzzer-tone"
        )
        self._play_thread.start()

    def _play_tone(self, frequency: int, duration_ms: int) -> None:
        """Run in background thread — starts PWM, waits, stops."""
        if not self._pwm_instance:
            return
        try:
            self._playing = True
            self._pwm_instance.ChangeFrequency(frequency)
            self._pwm_instance.start(50)  # 50% duty cycle

            deadline = time.monotonic() + duration_ms / 1000.0
            while time.monotonic() < deadline:
                if self._stop_event.is_set():
                    break
                time.sleep(0.01)

            self._pwm_instance.stop()
            self._playing = False
        except Exception as e:
            logger.error("Buzzer tone error: %s", e)
            self._playing = False

    def stop(self) -> None:
        if self._use_mock and self._mock:
            self._mock.stop()
            return

        self._stop_event.set()
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=0.5)

        if self._pwm_instance and self._playing:
            try:
                self._pwm_instance.stop()
            except Exception:
                pass
        self._playing = False

    def set_beep_callback(self, callback: callable) -> None:
        """Set callback for beep events (mock mode only)."""
        if self._mock:
            self._mock.set_beep_callback(callback)

    def cleanup(self) -> None:
        self.stop()
        if self._pwm_instance:
            try:
                self._pwm_instance.stop()
            except Exception:
                pass

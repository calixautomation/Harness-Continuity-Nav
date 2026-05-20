# Commit Changes Log

_Update this file before every commit. Add a new entry at the top under `## [Unreleased]` and move it to a dated section when committed._

---

## [Unreleased]

_No pending changes._

---

## 2026-05-21 — Hardware bring-up: RPi GPIO, TLC5925 driver, LED sync, thread safety

### Files changed
| File | Change |
|------|--------|
| `harness_nav/hal/tlc5925/tlc5925_driver.py` | **NEW** — TLC5925 16-channel bitbang driver |
| `harness_nav/hal/tlc5925/__init__.py` | **NEW** — package exports |
| `harness_nav/hal/switch/switch_handler.py` | Rewritten for RPi.GPIO (was Adafruit_BBIO) |
| `harness_nav/hal/buzzer/buzzer_driver.py` | Rewritten for RPi.GPIO PWM (was Adafruit_BBIO) |
| `harness_nav/scripts/run_hardware.py` | Added TLC5925 init, `_SwitchBridge` for thread safety |
| `harness_nav/gui/widgets/grid_widget.py` | Added `set_physical_sync_callback` |
| `harness_nav/gui/main_window.py` | `_stop_test()` now resets pattern + physical LEDs |

### Summary of changes

#### TLC5925 driver (`tlc5925_driver.py`)
- GPIO bitbang on BCM 10 (SDI), 11 (CLK), 23 (LE); OE tied to GND.
- Bit order: **reversed** — LED 1 maps to bit 15 (OUT15), LED 16 maps to bit 0 (OUT0).
  - Formula: `bit = _MAX_CHANNEL - led_num`
- `sync(pattern, blink_on)` — primary entry point; derives 16-bit word directly from
  the `Pattern` object on every call, no accumulated internal state.
- `_startup_test()` — flashes all 16 channels ON/OFF, then chases OUT0→OUT15 at 60 ms/step.
- Falls back to no-op logging if `RPi.GPIO` is unavailable (dev machine safe).
- `MockTLC5925Driver` — same interface, logs to DEBUG, no GPIO required.

#### Switch handler (`switch_handler.py`)
- Replaced `Adafruit_BBIO` with `RPi.GPIO` (BeagleBone library unavailable on Pi).
- `GPIO.getmode()` guard before `setmode` to avoid conflict with TLC5925 init.
- `cleanup()` calls `stop_monitoring()` only — does **not** call `GPIO.cleanup()` to
  avoid resetting TLC5925 pins.

#### Buzzer driver (`buzzer_driver.py`)
- Replaced `Adafruit_BBIO.PWM` with `RPi.GPIO.PWM` software PWM on GPIO 18.
- Background thread plays tone; `stop()` uses a `threading.Event` for clean interruption.
- Falls back to `MockBuzzerDriver` if `RPi.GPIO` is unavailable.

#### Thread-safety fix — `_SwitchBridge` (`run_hardware.py`)
- **Root cause of segfault**: GPIO polling thread called Qt GUI methods directly →
  QPainter crash / SIGSEGV on GPIO 27 pull.
- Fix: `_SwitchBridge(QObject)` with `lock_triggered` / `verify_triggered` `pyqtSignal`.
  GPIO thread only emits signals; `_do_lock()` / `_do_verify()` run in Qt main thread.

#### LED blink sync fix (`grid_widget.py`, `tlc5925_driver.py`, `run_hardware.py`)
- **Root cause**: old approach used two separate callbacks (`_blink_callback`,
  `_led_status_callback`) to maintain a `_statuses` dict in the driver. If either
  callback misfired the dict went stale → driver pushed wrong data.
- Fix: single `_physical_sync_callback(pattern, blink_on)` registered via
  `set_physical_sync_callback()`. Called from `_on_blink_timer`, `start_blinking`,
  `stop_blinking`, `refresh_display`, and `set_pattern`. Passes the authoritative
  `Pattern` object + blink phase; driver computes hardware word on the spot — no
  accumulated state possible.

#### Stop/switch bug fix (`main_window.py`)
- **Root cause**: `_stop_test()` left `Pattern._active_led` / `_locked_leds` dirty.
  TLC5925 carried over stale channel state into the next test.
- Fix: `_stop_test()` now calls `pattern.reset()` → `refresh_display()` → progress
  bar reset. Physical LEDs go dark immediately on Stop.

### Pin reference (BCM numbering)
| Signal | BCM | Physical pin |
|--------|-----|--------------|
| TLC5925 SDI | 10 | 19 |
| TLC5925 CLK | 11 | 23 |
| TLC5925 LE  | 23 | 16 |
| Limit switch | 17 | 11 |
| Metal plate  | 27 | 13 |
| Buzzer PWM   | 18 | 12 |

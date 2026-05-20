# Known Issues

_Track open bugs here. Move to "Resolved" with the fix date and commit when closed._

---

## Open

### Issue #1 — GUI hangs on keyboard interrupt (Ctrl+C)

**Severity**: Medium  
**Observed**: Application launched; Ctrl+C sent from terminal. GUI window freezes and does not close.

**Expected**: Window closes cleanly; GPIO resources released; process exits.

**Likely cause**:  
`signal.SIGINT` fires `_signal_handler` → calls `self.cleanup()` then `self.app.quit()`.  
`cleanup()` calls `self.tlc5925.cleanup()` (which calls `GPIO.cleanup()`) and
`self.switch.cleanup()` (which calls `stop_monitoring()` to join the daemon thread).
If the switch monitor thread is blocked on `GPIO.input()` or a sleep, `stop_monitoring()`
may block indefinitely before `app.quit()` is ever reached — leaving the Qt window alive.

**Investigation needed**:  
- Check whether `stop_monitoring()` sets a stop flag and joins with a timeout.  
- Check whether `GPIO.cleanup()` unblocks any pending `GPIO.input()` poll.  
- Consider calling `self.app.quit()` first (schedules event loop exit), then cleanup in
  a `QApplication.aboutToQuit` slot so the window closes immediately.

**Files to check**:  
- `harness_nav/scripts/run_hardware.py` — `_signal_handler`, `cleanup`  
- `harness_nav/hal/switch/switch_handler.py` — `stop_monitoring`

---

### Issue #2 — Cannot reset or start new test after successful completion

**Severity**: High  
**Observed**: All LEDs verified → success dialog appears → dialog dismissed.
Neither "Reset" nor selecting a new pattern from the combo box allows restarting.
Application must be relaunched.

**Expected**:  
- "Reset" re-initialises the same pattern and re-enables "Start Test".  
- Selecting a different pattern from the combo box enables "Start Test" for that pattern.

**Likely cause**:  
In `trigger_verify()` / `_on_verify_clicked()`, when `is_complete`:
```python
self._state = TestState.COMPLETE
self._start_btn.setEnabled(False)   # ← disabled here
```
`_on_reset_clicked()` only calls `auto_select_next()` when
`self._state == TestState.TESTING` — it does **not** re-enable `_start_btn` or
transition state back to `PATTERN_LOADED` when called from `COMPLETE` state.

`_on_pattern_selected()` does call `self._start_btn.setEnabled(True)`, so selecting a
**different** pattern should work — but in practice the combo box selection may not be
triggering the signal if the index hasn't changed (same pattern selected again).

**Fix plan**:  
1. In `_on_reset_clicked()`, handle `TestState.COMPLETE`:
   - Call `pattern.reset()` + `refresh_display()`.
   - Set `self._state = TestState.PATTERN_LOADED`.
   - Re-enable `_start_btn`.
   - Reset progress bar and labels.
2. In `_on_pattern_selected()`, always call `setEnabled(True)` on `_start_btn` when a
   valid pattern is selected (already done — verify it fires even when re-selecting the
   same index).

**Files to check**:  
- `harness_nav/gui/main_window.py` — `_on_reset_clicked`, `trigger_verify`,
  `_on_verify_clicked`, `_on_pattern_selected`

---

## Resolved

_No resolved issues yet._

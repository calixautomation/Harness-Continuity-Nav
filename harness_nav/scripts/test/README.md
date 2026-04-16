# Tests In This Folder

This folder contains automated pytest tests and one manual diagnostic script.

## What `pytest` runs

Today, `pytest` collects the automated test modules:

- `test_hal.py`
- `test_patterns.py`

These files use normal pytest conventions:

- file names start with `test_`
- test functions/methods start with `test_`
- tests use `assert` to verify behavior

Run them with:

```bash
pytest -v
```

## What `pytest` does not run

`test_components.py` is intentionally **not** part of the automated pytest suite.

It is a manual smoke-test / debugging script that:

- prints progress to the console
- sleeps to simulate hardware timing
- has its own `main()` runner
- uses `run_*` helpers instead of pytest `test_*` functions

Run it manually with:

```bash
python harness_nav/scripts/test/test_components.py
```


## How to add a new automated test

Use these rules:

1. Put the test in a `test_*.py` file.
2. Name each test `test_*`.
3. Use `assert`, not `return True` / `return False`.
4. Keep tests deterministic and non-interactive.
5. Prefer mocks/fakes over real hardware access.

Example:

```python
def test_select_led_marks_active():
    pattern = Pattern(id="p1", name="Demo", description="", leds=[1, 2])

    assert pattern.select_led(2) is True
    assert pattern.active_led == 2
```

## When to write a manual script instead

Use a manual script like `test_components.py` when you want:

- interactive debugging
- printed step-by-step output
- timing delays
- hardware bring-up checks
- a script that can be run directly by a developer

If you add another manual script, avoid pytest collection by not naming runnable helpers `test_*`.

## Naming gotcha

Pytest may try to collect classes whose names start with `Test`.

If a class is application code and not a test class, mark it with:

```python
__test__ = False
```

This only affects pytest discovery. It does not change normal runtime behavior.

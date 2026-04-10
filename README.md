# LED Pattern Tester

A GUI application for testing wire connectivity on an 8x8 LED matrix. Uses a two-stage verification process: lock the wire in the slot, then verify connectivity by touching a metal plate.

## Quick Start

```bash
# Install dependencies
pip install -r harness_nav/requirements.txt

# Run the GUI (Desktop mode with test buttons)
cd HarnessNav
python harness_nav/scripts/run_desktop.py
```

### Raspberry Pi Hardware Mirror

For Raspberry Pi deployments that drive external LEDs through MCP23017 expanders, run:

```bash
python raspberry_program.py --hardware-mode --switch-mode increment
```

The default expander map lives in [harness_nav/config/mcp23017_layout.json](harness_nav/config/mcp23017_layout.json). Add a new MCP23017 by adding another entry to that file with its I2C address and 16 output mappings.

If you only want to validate the switch/LED behavior without the GUI, use:

```bash
python mcp23017_limit_switch_test.py --limit-switch-gpio 14
```

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     LED Pattern Tester                       │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  Pattern:    │    1   2   3   4   5   6   7   8            │
│  [Dropdown]  │                                              │
│              │    9  10  11  12  13  14  15  16            │
│  [Start]     │                                              │
│  [Reset]     │   17  18  19  20  21  22  23  24            │
│              │                                              │
│  [1. Lock]   │   25  26  27  28  29  30  31  32            │
│  [2. Verify] │                                              │
│              │   33  34  35  36  37  38  39  40            │
│  Progress:   │                                              │
│  ████░░ 50%  │   41  42  43  44  45  46  47  48            │
│              │                                              │
│  Current:    │   49  50  51  52  53  54  55  56            │
│  LED 4       │                                              │
│              │   57  58  59  60  61  62  63  64            │
│              │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

### LED Colors

| Color | Meaning |
|-------|---------|
| Gray | Not part of pattern |
| Yellow | Needs to be tested |
| Cyan (blinking) | Currently active - waiting for wire |
| Orange | Wire locked in slot |
| Green | Verified/Passed |
| Red | Error/Wrong connection |

## Two-Stage Verification Workflow

```
1. Select Pattern    → LEDs in pattern turn YELLOW (pending)
2. Start Test        → First LED starts BLINKING (active)
3. Lock wire in slot → Limit switch triggers → LED turns ORANGE, beep (1500Hz)
4. Touch metal plate → Circuit completes → LED turns GREEN, beep (2500Hz)
5. Auto-advance      → Next LED starts blinking
6. Repeat            → Until all LEDs are GREEN
7. Complete          → Success message displayed
```

### Desktop Mode (Testing on PC)
- Use "1. Lock Wire" and "2. Verify Connection" buttons to simulate hardware
- Run with: `python harness_nav/scripts/run_desktop.py`

### Hardware Mode (BeagleBone Black)
- Buttons are hidden; uses actual GPIO inputs
- Limit switch detects wire locked in slot
- Metal plate touch completes circuit for verification
- Run with: `python harness_nav/scripts/run_hardware.py`

## Creating Patterns

Use the built-in Pattern Editor (click "New Pattern") or edit `harness_nav/data/patterns.json`:

```json
{
    "patterns": [
        {
            "id": "pattern_1",
            "name": "Pattern 1",
            "description": "LEDs 3, 4, 8",
            "leds": [3, 4, 8]
        },
        {
            "id": "corners",
            "name": "Corner LEDs",
            "description": "All four corners",
            "leds": [1, 8, 57, 64]
        }
    ]
}
```

### LED Numbering

```
 1   2   3   4   5   6   7   8
 9  10  11  12  13  14  15  16
17  18  19  20  21  22  23  24
25  26  27  28  29  30  31  32
33  34  35  36  37  38  39  40
41  42  43  44  45  46  47  48
49  50  51  52  53  54  55  56
57  58  59  60  61  62  63  64
```

### Modular MCP23017 Mapping

The Raspberry Pi hardware bridge treats the 64 GUI LEDs as logical LED numbers and maps them across one or more MCP23017 expanders.

Default layout:
- MCP23017 at `0x20` drives LEDs 1-16
- MCP23017 at `0x21` drives LEDs 17-32
- MCP23017 at `0x22` drives LEDs 33-48
- MCP23017 at `0x23` drives LEDs 49-64

To change the wiring, edit [harness_nav/config/mcp23017_layout.json](harness_nav/config/mcp23017_layout.json). Each expander entry contains:
- `address`: I2C address for the chip
- `active_high`: output polarity for that expander
- `outputs`: 16-element list mapping output bit 0-15 to logical LED numbers

This keeps the bridge modular so new expanders can be added without changing the rendering logic.

---

## Hardware Setup (BeagleBone Black)

### Required Components

| Component             | Description                               |
|-----------------------|-------------------------------------------|
| BeagleBone Black          | Main controller board                 |
| 7" Waveshare LCD      | Display for GUI (optional, can use HDMI)  |
| Limit Switch          | Detects when wire is locked in test slot  |
| Metal Plate           | Touch plate for connectivity verification |
| Piezo Buzzer          | Audio feedback (PWM driven)               |
| 8x8 WS2812 LED Matrix | Physical LED display (optional)           |

### Wiring Diagram

```
BeagleBone Black
       │
       ├── P9_12 (GPIO) ──────┬──── Limit Switch ──── GND
       │                      │
       │                   10kΩ pull-up to 3.3V
       │
       ├── P9_14 (GPIO) ──────┬──── Metal Plate ──── GND
       │                      │
       │                   10kΩ pull-up to 3.3V
       │
       ├── P9_16 (PWM) ───────┬──── Buzzer (+)
       │                      │
       │                  Buzzer (-) ──── GND
       │
       └── P8_11 (GPIO) ──────────── WS2812 Data In
                                     (with level shifter 3.3V→5V)
```

### Pin Connections

| Component | BeagleBone Pin | Notes |
|-----------|----------------|-------|
| Limit Switch | P9_12 (GPIO_60) | Pull-up to 3.3V, active LOW |
| Metal Plate | P9_14 (GPIO_50) | Pull-up to 3.3V, active LOW |
| Buzzer | P9_16 (EHRPWM1B) | PWM output for tone generation |
| LED Data | P8_11 (GPIO_45) | WS2812 data (needs 5V level shifter) |

### Circuit Notes

1. **Limit Switch**: Connect between P9_12 and GND. The switch should close (connect to GND) when wire is locked.

2. **Metal Plate**: Connect between P9_14 and GND. When wire touches the plate, it should connect P9_14 to GND through the wire path.

3. **Buzzer**: Use a passive piezo buzzer. Connect positive terminal to P9_16 and negative to GND.

4. **WS2812 LEDs**: These run on 5V but BeagleBone outputs 3.3V. Use a level shifter (like 74AHCT125) for the data line.

---

## Deploy to BeagleBone Black

### Option 1: Using Deployment Script (Windows)

```batch
cd HarnessNav\harness_nav\scripts
deploy_to_beaglebone.bat
```

Or specify IP address:
```batch
deploy_to_beaglebone.bat 192.168.7.2
```

### Option 2: Using Deployment Script (Linux/Mac)

```bash
cd HarnessNav/harness_nav/scripts
chmod +x deploy_to_beaglebone.sh
./deploy_to_beaglebone.sh
```

Or specify IP address:
```bash
./deploy_to_beaglebone.sh 192.168.7.2
```

### Option 3: Manual Deployment

```bash
# Copy files to BeagleBone
scp -r harness_nav debian@beaglebone.local:~/HarnessNav/

# SSH into BeagleBone
ssh debian@beaglebone.local

# Install dependencies
cd ~/HarnessNav
pip3 install -r harness_nav/requirements.txt

# Test run (hardware mode)
python3 harness_nav/scripts/run_hardware.py
```

### Enable Auto-Start on Boot

```bash
# SSH into BeagleBone
ssh debian@beaglebone.local

# Copy service file
sudo cp ~/HarnessNav/deploy/harness-nav.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable harness-nav
sudo systemctl start harness-nav

# Check status
sudo systemctl status harness-nav

# View logs
journalctl -u harness-nav -f
```

### Disable Auto-Start

```bash
sudo systemctl stop harness-nav
sudo systemctl disable harness-nav
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Escape | Exit application |
| Ctrl+Q | Exit application |
| F10 | Exit application (emergency) |

---

## Project Structure

```
HarnessNav/
├── README.md
├── PLAN.md                      # Project status and roadmap
├── deploy/
│   ├── harness-nav.service      # Systemd auto-start service
│   ├── install.sh               # Deployment installer
│   └── uninstall.sh             # Cleanup script
└── harness_nav/
    ├── requirements.txt
    ├── config/
    │   ├── settings.yaml        # Application settings
    │   ├── pins.yaml            # GPIO pin assignments
    │   └── led_layout.yaml      # LED panel configuration
    ├── data/
    │   └── patterns.json        # Test patterns
    ├── core/
    │   └── patterns/
    │       ├── models.py        # Data models
    │       └── pattern_loader.py
    ├── gui/
    │   ├── main_window.py       # Main application window
    │   ├── pattern_editor.py    # Pattern creation dialog
    │   └── widgets/
    │       └── grid_widget.py   # 8x8 LED grid with blinking
    ├── hal/
    │   ├── led_matrix/
    │   │   └── led_matrix.py    # LED matrix driver
    │   ├── switch/
    │   │   └── switch_handler.py # Dual switch handler
    │   └── buzzer/
    │       └── buzzer_driver.py  # PWM buzzer (lock/verify tones)
    └── scripts/
        ├── run_desktop.py        # PC testing mode
        ├── run_hardware.py       # BeagleBone hardware mode
        ├── deploy_to_beaglebone.sh
        └── deploy_to_beaglebone.bat
```

---

## Troubleshooting

### GUI won't start
```bash
pip install PyQt5 PyYAML
```

### No patterns in dropdown
Check that `harness_nav/data/patterns.json` exists and is valid JSON.

### Can't connect to BeagleBone
```bash
# Check if BeagleBone is reachable
ping beaglebone.local

# Try using IP address directly
ping 192.168.7.2   # USB connection
ping 192.168.1.x   # Network connection (check your router)
```

### GPIO not working on BeagleBone
```bash
# Install Adafruit library
pip3 install Adafruit-BBIO

# Check if running as correct user
# GPIO may need root or debian user in gpio group
sudo usermod -a -G gpio debian
```

### Buzzer not making sound
- Check PWM pin connection (P9_16)
- Verify buzzer polarity (+ to P9_16, - to GND)
- Test with: `python3 -c "from harness_nav.hal.buzzer import BuzzerDriver; b = BuzzerDriver('P9_16'); b.beep_verify()"`

### Application won't exit
- Press **Escape**, **Ctrl+Q**, or **F10**
- Or from SSH: `pkill -f run_hardware.py`

---

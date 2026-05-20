[![Python application](https://github.com/calixautomation/Harness-Continuity-Nav/actions/workflows/python-app.yml/badge.svg)](https://github.com/calixautomation/Harness-Continuity-Nav/actions/workflows/python-app.yml)

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

### Hardware Mode (Raspberry Pi)
- Buttons are hidden; uses SPI inputs
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

---

## Hardware Setup (Raspberry Pi)

### Required Components

| Component             | Description                               |
|-----------------------|-------------------------------------------|
| Raspberry Pi          | Main controller board                 |
| 10" Waveshare LCD     | Display for GUI (optional, can use HDMI)  |
| Limit Switch          | Detects when wire is locked in test slot  |
| Metal Plate           | Touch plate for connectivity verification |
| Piezo Buzzer          | Audio feedback (PWM driven)               |
| LEDs arranged in 8x8  | Physical LED display (optional)           |

### Wiring Diagram

```
Raspberry Pi 4B
       │
       ├── Pin 1 / 2 (3.3V / 5V) ──────── VCC (Pin 24 on TLC5925)
       │
       ├── Pin 6 / 9 (GND) ───────────── GND (Pin 12 on TLC5925)
       │
       ├── Pin 19 (GPIO 10 / MOSI) ───── SDI (Pin 23 on TLC5925)
       │
       ├── Pin 23 (GPIO 11 / SCLK) ───── CLK (Pin 22 on TLC5925)
       │
       ├── Pin 22 (GPIO 25) ──────────── LE (Pin 21 on TLC5925)
       │
       └── Pin 16 (GPIO 23) ──────────── \OE (Pin 10 on TLC5925, pulled LOW)
```

### Pin Connections

| Raspberry Pi Pin | TLC5925 Pin Name | TLC5925 Pin # | Notes                              |
|------------------|------------------|---------------|------------------------------------|
| Pin 1 / 2 (3.3V / 5V) | VCC              | Pin 24        | Logic power supply                |
| Pin 6 / 9 (GND)       | GND              | Pin 12        | Common ground                     |
| Pin 19 (GPIO 10 / MOSI)| SDI (Serial Data In) | Pin 23    | Data bus                          |
| Pin 23 (GPIO 11 / SCLK)| CLK (Clock)     | Pin 22        | Shift clock                       |
| Pin 22 (GPIO 25)       | LE (Latch Enable) | Pin 21      | Latches data into output          |
| Pin 16 (GPIO 23)       | \OE (Output Enable) | Pin 10   | Pull LOW (GND) to enable LED outputs |

### Circuit Notes

1. **Power Supply**: Connect the Raspberry Pi's 3.3V or 5V pin to the TLC5925's VCC (Pin 24). Ensure the voltage matches the logic level of the Raspberry Pi.

2. **Ground**: Connect the Raspberry Pi's GND pin to the TLC5925's GND (Pin 12).

3. **Serial Data Input (SDI)**: Connect GPIO 10 (MOSI, Pin 19) to the TLC5925's SDI (Pin 23).

4. **Clock (CLK)**: Connect GPIO 11 (SCLK, Pin 23) to the TLC5925's CLK (Pin 22).

5. **Latch Enable (LE)**: Connect GPIO 25 (Pin 22) to the TLC5925's LE (Pin 21). This pin latches the shifted data into the output.

6. **Output Enable (\OE)**: Connect GPIO 23 (Pin 16) to the TLC5925's \OE (Pin 10). Pull this pin LOW to enable the LED outputs.

---

## Deploy to Raspberry Pi 

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

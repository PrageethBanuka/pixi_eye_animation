# RoboEyes + Ultrasonic Interactive Animation (macOS)

This project renders expressive eyes with Pygame and reacts to distance readings from an Arduino Uno + HC‑SR04 ultrasonic sensor.

## What you get
- Desktop Pygame animation (blink, wink, laugh, moods)
- Arduino sketch that streams `DIST:<cm>` lines at ~20 Hz
- Python script maps distance zones to moods (Curious, Happy, Default, Tired)
- Simulation fallback if no Arduino is attached

## Hardware
- Arduino Uno (or compatible 5V board)
- HC‑SR04 ultrasonic distance sensor
- Jumper wires

### Wiring (Uno)
- HC‑SR04 VCC → 5V
- HC‑SR04 GND → GND
- HC‑SR04 TRIG → D9
- HC‑SR04 ECHO → D8

> Note: Uno is 5V logic so HC‑SR04 ECHO is fine directly. If you use a 3.3V board (like ESP32), add a voltage divider on ECHO.

## Upload Arduino
1. Open Arduino IDE
2. File → Open… `arduino/roboeyes_ultrasonic/roboeyes_ultrasonic.ino`
3. Select Board: Arduino Uno, correct Port
4. Upload

The sketch prints lines like `DIST:23.5` at 115200 baud.

## Python setup
Use the provided virtual environment or any Python 3.8+.

Install deps:

```bash
source myenv/bin/activate  # optional if using the provided venv
pip install -r requirements.txt
```

## Run the animation
1. Edit `animation.py` and set `SERIAL_PORT` to your Arduino device, e.g.:
   - macOS: `/dev/cu.usbmodemXXXX` or `/dev/cu.usbserial-XXXX`
2. Start:

```bash
python animation.py
```

- If the serial port is wrong or pyserial is missing, the script auto‑simulates distance so you can still test.

## Controls (keyboard)
- h → HAPPY
- d → DEFAULT
- a → ANGRY
- t → TIRED
- s → SCARY
- c → CURIOUS
- z → SAD
- f → FROZEN
- b → blink
- j → wink left
- k → wink right
- l → laugh
- SPACE → confuse

## Behavior map
- distance ≤ 15 cm → CURIOUS (+occasional wink)
- 15 < distance ≤ 35 cm → HAPPY
- 35 < distance ≤ 60 cm → DEFAULT
- distance > 60 cm → TIRED

Simple hysteresis (400 ms) reduces flicker at boundaries.

## Troubleshooting
- No motion / stuck on simulation: set a correct `SERIAL_PORT` in `animation.py` and ensure the Arduino IDE Serial Monitor is closed (only one app can open the port).
- Missing `serial` module: run `pip install pyserial` (already in requirements.txt).
- Window too large/small: adjust `WIDTH, HEIGHT` in `animation.py`.

## Direct SPI TFT (Raspberry Pi) – No fbcp Driver
If you have a 2.4" SPI ILI9341 display and a Raspberry Pi, you can drive it directly without compiling the fbcp mirror driver by using `tft_animation.py`.

### Extra Dependencies
Already added to `requirements.txt`:
`Pillow`, `adafruit-circuitpython-rgb-display`

Install on Pi:
```bash
sudo apt update
sudo apt install -y python3-pip python3-pil
pip install -r requirements.txt
```

### Enable SPI
```bash
sudo raspi-config   # Interface Options -> SPI -> Enable
sudo reboot
```

### Wiring (Default Used in Script)
| TFT Pin | Pi GPIO (BCM) | Header Pin |
|---------|---------------|------------|
| VCC     | 3V3           | 1 or 17    |
| GND     | GND           | 6          |
| CS      | GPIO8 (CE0)   | 24         |
| DC      | GPIO25        | 22         |
| RST     | GPIO24        | 18         |
| MOSI    | GPIO10        | 19         |
| MISO    | GPIO9         | 21 (optional) |
| SCK     | GPIO11        | 23         |
| LED     | 3V3 (or via transistor/PWM on GPIO18) |

### Run Direct Animation
```bash
python3 tft_animation.py
```
Cycles through moods every few seconds. Edit the `CYCLE` list or integrate sensors by calling `eyes.set_mood(<mood>)`.

### Performance Tips
- Lower target FPS (e.g. 25–30) for stability.
- Reduce SPI baudrate in `tft_animation.py` if artifacts appear (e.g. 24000000).
- Remove mood label drawing for a tiny speed boost.

### Integrating Sensors or Vision
Wrap sensor reading in a thread and set `eyes.set_mood()` based on conditions (distance, face detection, etc.). Keep rendering loop unchanged.

### Common Issues
| Symptom | Fix |
|---------|-----|
| Black screen | Check SPI enabled & wiring; confirm CS/DC/RST pins match script |
| Inverted colors / rotation | Adjust `rotation=` in display init (0, 90, 180, 270) |
| Flicker | Lower SPI baudrate or FPS |
| Slow | Ensure no desktop compositor overhead; run headless console |

## fbcp vs Direct SPI
- fbcp driver mirrors whole framebuffer (run existing `pygame` window unchanged).
- Direct SPI uses Pillow & pushes only your custom animation (lighter, simpler, no C build). Choose direct SPI if you only need the eyes.

## License
- `roboeyes_pygame.py` is a Pygame re‑implementation inspired by `mchobby/micropython-roboeyes` (GPL-3.0 reference). Other code in this repo is MIT unless noted.

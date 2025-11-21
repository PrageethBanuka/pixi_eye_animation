#!/usr/bin/env python3
"""Direct SPI TFT animation for 2.4" ILI9341 using CircuitPython RGB Display + Pillow.

Run on Raspberry Pi 4 (64-bit or 32-bit). No fbcp driver required.
Renders expressive 'RoboEyes' style cute eyes directly to the display.

Dependencies (see requirements.txt):
    Pillow
    adafruit-circuitpython-rgb-display

Enable SPI first: sudo raspi-config  -> Interface Options -> SPI -> Enable

Wiring (default pins used here):
    ILI9341   Raspberry Pi GPIO (BCM) / Header Pin
    VCC       3V3 (Pin 1 or 17)
    GND       GND (Pin 6 or 9 etc.)
    CS        CE0 (GPIO8, Pin 24)
    DC (D/C)  GPIO25 (Pin 22)
    RST       GPIO24 (Pin 18)
    MOSI      GPIO10 (Pin 19)
    MISO      GPIO9 (Pin 21)  (optional, not used for write-only)
    SCK       GPIO11 (Pin 23)
    LED       3V3 (or via transistor + GPIO18 PWM)

If your board differs, adjust the pin objects below accordingly.

Keyboard interaction is not included (headless). Modify mood cycle or integrate
external sensor threads (ultrasonic, vision) to set `eyes.set_mood(...)`.

Ctrl+C to exit.
"""
import time, math, random
from typing import Tuple

# CircuitPython display libs
import board
import digitalio
import busio
from PIL import Image, ImageDraw
import adafruit_rgb_display.ili9341 as ili9341

# Mood constants (align with earlier project)
DEFAULT, TIRED, ANGRY, HAPPY, FROZEN, SCARY, CURIOUS, SAD = 0,1,2,3,4,5,6,7

class CuteEyes:
    """Lightweight eye state manager for direct drawing.

    Handles blink timing, mood, and open factors for eyelids.
    """
    def __init__(self):
        self.mood = DEFAULT
        self.blinking = False
        self.last_blink_ts = 0.0
        self.next_blink_ts = time.time() + random.uniform(2.5, 4.5)
        self.blink_duration = 0.12  # seconds
        self.left_open = 1.0
        self.right_open = 1.0

    def set_mood(self, mood: int):
        self.mood = mood

    def trigger_blink(self):
        self.blinking = True
        self.last_blink_ts = time.time()

    def update(self):
        now = time.time()
        # Auto blink
        if not self.blinking and now >= self.next_blink_ts:
            self.trigger_blink()
            self.next_blink_ts = now + random.uniform(2.5, 4.5)
        if self.blinking:
            progress = (now - self.last_blink_ts) / self.blink_duration
            if progress >= 1.0:
                self.blinking = False
                self.left_open = 1.0
                self.right_open = 1.0
            else:
                phase = math.sin(progress * math.pi)  # smooth close/reopen
                openness = max(0.05, 1.0 - phase)
                self.left_open = openness
                self.right_open = openness

    def iris_color(self) -> Tuple[int,int,int]:
        # Pastel palette per mood
        return {
            HAPPY:   (255, 170, 205),
            CURIOUS: (150, 210, 255),
            TIRED:   (150, 160, 170),
            ANGRY:   (255, 110, 110),
            SCARY:   (140, 255, 170),
            FROZEN:  (185, 240, 255),
            SAD:     (145, 175, 235),
        }.get(self.mood, (165, 245, 230))

# --- Display setup ---
# SPI bus & pins (change if using different wiring)
spi = board.SPI()  # uses SCK/MOSI/MISO default
cs_pin = digitalio.DigitalInOut(board.CE0)    # Chip Select (GPIO8)
dc_pin = digitalio.DigitalInOut(board.D25)    # Data/Command (GPIO25)
rst_pin = digitalio.DigitalInOut(board.D24)   # Reset (GPIO24)
# Optional backlight (if transistor tied to GPIO18):
try:
    backlight = digitalio.DigitalInOut(board.D18)
    backlight.switch_to_output(value=True)  # ON
except Exception:
    backlight = None

# Create display (set baudrate for performance; 48MHz often OK on Pi4)
display = ili9341.ILI9341(spi, rotation=0, cs=cs_pin, dc=dc_pin, rst=rst_pin, baudrate=48000000)
WIDTH = display.width   # typically 240
HEIGHT = display.height # typically 320

# Off-screen buffer
image = Image.new("RGB", (WIDTH, HEIGHT))
draw = ImageDraw.Draw(image)

eyes = CuteEyes()

# Adjustable geometry
GAP = 18
EYE_W = 110
EYE_H = 110
IRIS_MARGIN_RATIO = 0.18

# Mood cycle demo (replace with sensor input or emotion classifier)
CYCLE = [
    (DEFAULT, 5.0),
    (CURIOUS, 5.0),
    (HAPPY, 5.0),
    (SAD, 5.0),
    (TIRED, 5.0),
    (ANGRY, 5.0),
]
cycle_index = 0
cycle_start = time.time()

BG_COLOR = (10,10,15)
SCLERA_COLOR = (250,248,245)
OUTLINE_COLOR = (70,70,80)
PUPIL_COLOR = (20,25,32)

def apply_mood_cycle():
    global cycle_index, cycle_start
    mood, duration = CYCLE[cycle_index]
    if time.time() - cycle_start >= duration:
        cycle_index = (cycle_index + 1) % len(CYCLE)
        cycle_start = time.time()
        mood, _ = CYCLE[cycle_index]
        eyes.set_mood(mood)

# Initial mood
eyes.set_mood(CYCLE[0][0])

def draw_eye(ex, top_y, w, h, open_factor, is_left):
    # Sclera
    draw.ellipse((ex, top_y, ex+w, top_y+h), fill=SCLERA_COLOR, outline=OUTLINE_COLOR)
    # Eyelid overlays based on mood
    if eyes.mood in (TIRED, SAD):
        lid_h = int(h * (0.55 if eyes.mood == TIRED else 0.35))
        draw.rectangle((ex, top_y, ex+w, top_y+lid_h), fill=BG_COLOR)
    elif eyes.mood == ANGRY:
        lid_h = int(h*0.5)
        if is_left:
            pts = [(ex, top_y),(ex+w, top_y),(ex, top_y+lid_h)]
        else:
            pts = [(ex, top_y),(ex+w, top_y),(ex+w, top_y+lid_h)]
        draw.polygon(pts, fill=BG_COLOR)
    elif eyes.mood == HAPPY:
        lid_h = int(h*0.45)
        draw.rectangle((ex, top_y+h-lid_h, ex+w, top_y+h), fill=BG_COLOR)

    # Iris
    iris_col = eyes.iris_color()
    margin = int(min(w, h)*IRIS_MARGIN_RATIO)
    iris_box = (ex+margin, top_y+margin, ex+w-margin, top_y+h-margin)
    draw.ellipse(iris_box, fill=iris_col)

    # Pupil scaling with mood & blink openness
    pupil_scale = 0.38
    if eyes.mood == CURIOUS: pupil_scale = 0.48
    if eyes.mood == ANGRY: pupil_scale = 0.30
    if eyes.mood == TIRED: pupil_scale = 0.32
    if eyes.mood == SAD: pupil_scale = 0.34

    iw = iris_box[2]-iris_box[0]
    ih = iris_box[3]-iris_box[1]
    pw = int(iw * pupil_scale)
    ph = int(ih * pupil_scale * open_factor)
    px = iris_box[0] + (iw-pw)//2
    py = iris_box[1] + (ih-ph)//2
    draw.ellipse((px,py,px+pw,py+ph), fill=PUPIL_COLOR)

    # Highlight (small white specular)
    hl_r = max(2, int(pw * 0.18))
    hl_x = px + int(pw*0.30)
    hl_y = py + int(ph*0.30)
    draw.ellipse((hl_x-hl_r, hl_y-hl_r, hl_x+hl_r, hl_y+hl_r), fill=(255,255,255))


def render_frame():
    draw.rectangle((0,0,WIDTH,HEIGHT), fill=BG_COLOR)
    # Compute positions
    x_center = WIDTH//2
    y_center = HEIGHT//2
    left_x = x_center - EYE_W - GAP//2
    right_x = x_center + GAP//2
    top_y = y_center - EYE_H//2
    draw_eye(left_x, top_y, EYE_W, EYE_H, eyes.left_open, True)
    draw_eye(right_x, top_y, EYE_W, EYE_H, eyes.right_open, False)

    # Optional mood label (tiny, minimal cost)
    label = {DEFAULT:"DEF", CURIOUS:"CUR", HAPPY:"HAP", SAD:"SAD", TIRED:"TRD", ANGRY:"ANG"}.get(eyes.mood, "M")
    # Use a simple pixel font by drawing rectangles (skip for performance if desired)
    # Here just a small colored dot indicating mood
    color_dot = eyes.iris_color()
    draw.rectangle((5,5,18,18), fill=color_dot)

    display.image(image)


def main_loop():
    target_fps = 30
    frame_interval = 1.0/target_fps
    try:
        while True:
            start = time.time()
            eyes.update()
            apply_mood_cycle()
            render_frame()
            elapsed = time.time() - start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main_loop()

import pygame, sys, threading, time, math
try:
    import serial  # pyserial
except ImportError:  # allow running without pyserial installed
    serial = None
from roboeyes_pygame import ANGRY, TIRED, SCARY, CURIOUS, SAD, FROZEN, RoboEyes, ON, DEFAULT, HAPPY

# --- Serial distance reader (Arduino) ---
# Opens the first Arduino UNO port & streams distance lines formatted as:
#   DIST:<number_in_cm>\n
# Thread updates shared variable current_distance_cm.
SERIAL_PORT = '/dev/cu.usbmodem1401'  # adjust to your Arduino device (e.g. /dev/cu.usbmodemXXXX)
BAUD_RATE = 115200
current_distance_cm = None
_stop_serial = False

def _serial_thread():
    """Background reader: updates current_distance_cm from Arduino or simulates.

    Keeps logic linear & low complexity: acquire port, loop reading, parse, fallback simulation.
    """
    global current_distance_cm, _stop_serial
    ser = None
    if serial is not None:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        except Exception:
            ser = None
    while not _stop_serial:
        if ser:
            if ser.in_waiting:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith('DIST:'):
                        val_str = line.split(':',1)[1]
                        try:
                            current_distance_cm = float(val_str)
                        except ValueError:
                            pass
                except Exception:
                    pass
        else:
            # simulate 5..60 cm oscillation using sine
            t = time.time()
            span = 55
            mid = 32
            simulated = mid + (span/2) * math.sin(t*0.5)
            current_distance_cm = max(5, min(60, simulated))
        time.sleep(0.02)

threading.Thread(target=_serial_thread, daemon=True).start()

pygame.init()
WIDTH, HEIGHT = 400, 200
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Create RoboEyes on the Pygame surface
robo = RoboEyes(screen, WIDTH, HEIGHT, frame_rate=60, bgcolor=(10,10,15), fgcolor=(131,238,255))
robo.set_auto_blinker(ON, 3, 2)
robo.set_idle_mode(ON, 2, 2)
# Example geometry and mood tweaks (optional)
robo.eyes_width(90, 90)
robo.eyes_height(80, 80)
robo.eyes_radius(15, 15)
robo.mood = DEFAULT

# Distance thresholds (cm)
NEAR_THRESHOLD = 15    # hand very close
MID_THRESHOLD = 35     # moderate proximity
FAR_THRESHOLD = 60     # far / idle

# Hysteresis state
last_zone = None
zone_cooldown_until = 0

running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_h:
                robo.mood = HAPPY
            if e.key == pygame.K_d:
                robo.mood = DEFAULT
            if e.key == pygame.K_a:
                robo.mood = ANGRY
            if e.key == pygame.K_t:
                robo.mood = TIRED
            if e.key == pygame.K_s:
                robo.mood = SCARY
            if e.key == pygame.K_c:
                robo.mood = CURIOUS
            if e.key == pygame.K_z:
                robo.mood = SAD
            if e.key == pygame.K_f:
                robo.mood = FROZEN
            if e.key == pygame.K_b:  # blink both
                robo.blink()
            if e.key == pygame.K_j:  # wink left
                robo.wink_left()
            if e.key == pygame.K_k:  # wink right
                robo.wink_right()
            if e.key == pygame.K_l:  # laugh animation
                robo.laugh()
            if e.key == pygame.K_SPACE:
                robo.confuse()

    # Serial-driven mood mapping
    now = pygame.time.get_ticks()
    dist = current_distance_cm
    if dist is not None:
        # Determine zone
        if dist <= NEAR_THRESHOLD:
            zone = 'near'
        elif dist <= MID_THRESHOLD:
            zone = 'mid'
        elif dist <= FAR_THRESHOLD:
            zone = 'far'
        else:
            zone = 'away'

        # cooldown to prevent rapid mood flicker
        if now < zone_cooldown_until:
            zone = last_zone if last_zone else zone
        elif zone != last_zone:
            zone_cooldown_until = now + 400
            last_zone = zone

        # Map zones to moods + micro animations
        if zone == 'near':
            # Very close: curious & occasional wink
            robo.mood = CURIOUS
            if (now // 1200) % 2 == 0:
                robo.wink_left()
                robo.confuse()
        elif zone == 'mid':
            # Mid: happy
            robo.mood = HAPPY
        elif zone == 'far':
            # Some distance: default
            robo.mood = DEFAULT
        else:
            # away: tired (low activity)
            robo.mood = TIRED

    # Update and draw
    robo.update()
    pygame.display.flip()
    clock.tick(60)

_stop_serial = True
pygame.quit()
sys.exit()
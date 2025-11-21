import pygame, sys
from roboeyes_pygame import ANGRY, TIRED, SCARY, CURIOUS, SAD,FROZEN, RoboEyes, ON, DEFAULT, HAPPY

pygame.init()
WIDTH, HEIGHT = 400, 200
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Create RoboEyes on the Pygame surface
robo = RoboEyes(screen, WIDTH, HEIGHT, frame_rate=60, bgcolor=(10,10,15), fgcolor=(131,238,255))
robo.set_auto_blinker(ON, 3, 2)
robo.set_idle_mode(ON, 2, 2)
# Example geometry and mood tweaks (optional)
robo.eyes_width(80, 80)
robo.eyes_height(80, 80)
robo.eyes_radius(15, 15)
robo.mood = DEFAULT
robo.set_cute(False)

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
            if e.key == pygame.K_u:  # toggle cute mode
                robo.set_cute(not getattr(robo, 'cute', False))
            if e.key == pygame.K_z:
                robo.mood = SAD
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

    # Update and draw
    robo.update()
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
"""Minimal Pygame simulation of the MicroPython RoboEyes library.

This is a lightweight re-implementation inspired by mchobby/micropython-roboeyes
so we can prototype animations on desktop with Pygame.
It DOES NOT copy the original source verbatim (GPL reference retained).

Original project (GPL-3.0): https://github.com/mchobby/micropython-roboeyes
FluxGarage Arduino origin: https://github.com/FluxGarage/RoboEyes

Core ideas implemented here:
- Two eyes (optionally cyclops) with width/height/radius/spacing
- Automatic blink & idle (random reposition)
- Moods: DEFAULT, TIRED, ANGRY, HAPPY, FROZEN, SCARY, CURIOUS (simplified drawing)
- Micro animations: confuse(), laugh(), wink(), blink()
- Sequences (very small subset) for timed steps

Desktop adaptation notes:
- Uses pygame.time.get_ticks() instead of time.ticks_ms()
- Frame limiting done via frame_interval derived from frame_rate
- Drawing primitives use pygame.draw (rounded rect & polygons)

Usage:
from roboeyes_pygame import *
robo = RoboEyes(screen, 400, 200, frame_rate=60)
while True:
    robo.update()
    pygame.display.flip()

"""
import pygame
import random
import math

# Constants (mirroring original API values)
DEFAULT = 0
TIRED = 1
ANGRY = 2
HAPPY = 3
FROZEN = 4
SCARY = 5
CURIOUS = 6
SAD = 7

ON = 1
OFF = 0

N, NE, E, SE, S, SW, W, NW = 1,2,3,4,5,6,7,8

class StepData:
    __slots__ = ["done","ms_timing","callback","owner_seq"]
    def __init__(self, owner_seq, ms_timing, callback):
        self.done = False
        self.ms_timing = ms_timing
        self.callback = callback
        self.owner_seq = owner_seq
    def update(self, ticks):
        if self.done: return
        if ticks - self.owner_seq._start < self.ms_timing: return
        self.callback(self.owner_seq.owner)
        self.done = True

class Sequence(list):
    def __init__(self, owner, name):
        super().__init__()
        self.owner = owner
        self.name = name
        self._start = None
    def step(self, ms_timing, callback):
        self.append(StepData(self, ms_timing, callback))
    def start(self):
        self._start = pygame.time.get_ticks()
    def reset(self):
        self._start = None
        for s in self: s.done = False
    @property
    def done(self):
        if self._start is None: return True
        return all(s.done for s in self)
    def update(self, ticks):
        if self._start is None: return
        for s in self:
            if not s.done: s.update(ticks)

class Sequences(list):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
    def add(self, name):
        seq = Sequence(self.owner, name)
        self.append(seq)
        return seq
    @property
    def done(self):
        return all(seq.done for seq in self)
    def update(self):
        ticks = pygame.time.get_ticks()
        for seq in self:
            seq.update(ticks)

class RoboEyes:
    def __init__(self, surface, width, height, frame_rate=30, bgcolor=(10,10,15), fgcolor=(0,255,255)):
        self.surface = surface
        self.screen_width = width
        self.screen_height = height
        self.bgcolor = bgcolor
        self.fgcolor = fgcolor

        # Sequences container
        self.sequences = Sequences(self)

        # Frame rate control
        self.set_framerate(frame_rate)
        self.fps_timer = 0

        # Geometry defaults
        self.space_between_default = 60
        self.space_between_current = self.space_between_default
        self.space_between_next = self.space_between_default

        self.eye_l_width_default = 80
        self.eye_l_height_default = 80
        self.eye_r_width_default = 80
        self.eye_r_height_default = 80
        self.eye_l_width_current = self.eye_l_width_default
        self.eye_l_height_current = self.eye_l_height_default
        self.eye_r_width_current = self.eye_r_width_default
        self.eye_r_height_current = self.eye_r_height_default
        self.eye_l_width_next = self.eye_l_width_current
        self.eye_l_height_next = self.eye_l_height_current
        self.eye_r_width_next = self.eye_r_width_current
        self.eye_r_height_next = self.eye_r_height_current
        self.eye_l_radius_default = 30
        self.eye_r_radius_default = 30
        self.eye_l_radius_current = self.eye_l_radius_default
        self.eye_r_radius_current = self.eye_r_radius_default
        self.eye_l_radius_next = self.eye_l_radius_default
        self.eye_r_radius_next = self.eye_r_radius_default

        # Position (centered)
        self.eye_l_y_default = (self.screen_height - self.eye_l_height_default)//2
        center_x = (self.screen_width - (self.eye_l_width_default + self.space_between_default + self.eye_r_width_default))//2
        self.eye_l_x = center_x
        self.eye_l_y = self.eye_l_y_default
        self.eye_r_x = self.eye_l_x + self.eye_l_width_default + self.space_between_default
        self.eye_r_y = self.eye_l_y
        self.eye_l_x_next = self.eye_l_x
        self.eye_l_y_next = self.eye_l_y
        self.eye_r_x_next = self.eye_r_x
        self.eye_r_y_next = self.eye_r_y

        # Modes / states
        self._mood = DEFAULT
        self.tired = False
        self.angry = False
        self.happy = False
        self._curious = False
        self._cyclops = False
        self.sad = False  # sad mood flag
        # Cute/kawaii rendering toggle & palette
        self.cute = False
        self.sclera_color = (250, 250, 255)
        self.pupil_color = (25, 30, 35)
        self.outline_color = (60, 65, 70)

        self.eye_l_open = True
        self.eye_r_open = True

        # Macro animations control
        self.autoblinker = False
        self.blink_interval = 1000
        self.blink_interval_variation = 2000
        self._next_blink = pygame.time.get_ticks() + self.blink_interval

        self.idle = False
        self.idle_interval = 1500
        self.idle_interval_variation = 1500
        self._next_idle = pygame.time.get_ticks() + self.idle_interval

        self._confused = False
        self._laugh = False
        self.confused_animation_timer = 0
        self.laugh_animation_timer = 0
        self.confused_duration = 500
        self.laugh_duration = 500
        self._wink_left = False
        self._wink_right = False
        self.wink_timer = 0
        self.wink_duration = 300

    # ---- Public API (subset) ----
    def set_framerate(self, fps):
        self.frame_interval = 1000//fps if fps>0 else 33

    def eyes_width(self, left_eye=None, right_eye=None):
        if left_eye is not None:
            self.eye_l_width_next = left_eye
            self.eye_l_width_default = left_eye
        if right_eye is not None:
            self.eye_r_width_next = right_eye
            self.eye_r_width_default = right_eye

    def eyes_height(self, left_eye=None, right_eye=None):
        if left_eye is not None:
            self.eye_l_height_next = left_eye
            self.eye_l_height_default = left_eye
        if right_eye is not None:
            self.eye_r_height_next = right_eye
            self.eye_r_height_default = right_eye

    def eyes_radius(self, left_eye=None, right_eye=None):
        if left_eye is not None:
            self.eye_l_radius_next = left_eye
            self.eye_l_radius_default = left_eye
        if right_eye is not None:
            self.eye_r_radius_next = right_eye
            self.eye_r_radius_default = right_eye

    def eyes_spacing(self, space):
        self.space_between_next = space
        self.space_between_default = space

    @property
    def mood(self):
        return self._mood
    @mood.setter
    def mood(self, value):
        self._mood = value
        self.tired = (value in (TIRED, SCARY))
        self.angry = (value == ANGRY)
        self.happy = (value == HAPPY)
        self._curious = (value == CURIOUS)
        self.sad = (value == SAD)
        # FROZEN currently handled visually by outline flicker in update()
        # SCARY reuses tired flag for eyelid lowering (already covered)
    def set_mood(self, value):
        self.mood = value

    @property
    def cyclops(self):
        return self._cyclops
    @cyclops.setter
    def cyclops(self, enabled):
        self._cyclops = enabled
    def set_cyclops(self, value):
        self.cyclops = value

    @property
    def curious(self):
        return self._curious
    @curious.setter
    def curious(self, enable):
        self._curious = enable
    def set_curious(self, value):
        self.curious = value

    def set_auto_blinker(self, active, interval=None, variation=None):
        self.autoblinker = bool(active)
        if interval is not None:
            self.blink_interval = int(interval*1000)
        if variation is not None:
            self.blink_interval_variation = int(variation*1000)
        self._next_blink = pygame.time.get_ticks() + self.blink_interval

    def set_idle_mode(self, active, interval=None, variation=None):
        self.idle = bool(active)
        if interval is not None:
            self.idle_interval = int(interval*1000)
        if variation is not None:
            self.idle_interval_variation = int(variation*1000)
        self._next_idle = pygame.time.get_ticks() + self.idle_interval

    # Cute mode controls
    def set_cute(self, enabled: bool):
        self.cute = bool(enabled)

    def set_eye_palette(self, sclera=None, pupil=None, outline=None):
        if sclera is not None:
            self.sclera_color = sclera
        if pupil is not None:
            self.pupil_color = pupil
        if outline is not None:
            self.outline_color = outline

    @property
    def position(self):
        # computed from left eye target
        return None
    @position.setter
    def position(self, direction):
        # Map directions to (x,y) for left eye center baseline
        max_x = self.screen_width - (self.eye_l_width_current + self.space_between_current + (0 if self._cyclops else self.eye_r_width_current))
        max_y = self.screen_height - self.eye_l_height_current
        if direction == N:
            self.eye_l_x_next = max_x//2; self.eye_l_y_next = 0
        elif direction == NE:
            self.eye_l_x_next = max_x; self.eye_l_y_next = 0
        elif direction == E:
            self.eye_l_x_next = max_x; self.eye_l_y_next = max_y//2
        elif direction == SE:
            self.eye_l_x_next = max_x; self.eye_l_y_next = max_y
        elif direction == S:
            self.eye_l_x_next = max_x//2; self.eye_l_y_next = max_y
        elif direction == SW:
            self.eye_l_x_next = 0; self.eye_l_y_next = max_y
        elif direction == W:
            self.eye_l_x_next = 0; self.eye_l_y_next = max_y//2
        elif direction == NW:
            self.eye_l_x_next = 0; self.eye_l_y_next = 0
        else: # center
            self.eye_l_x_next = max_x//2; self.eye_l_y_next = max_y//2

    def set_position(self, value):
        self.position = value

    # Basic animations
    def blink(self, left=None, right=None):
        if left is None and right is None:
            self.eye_l_height_next = 1
            self.eye_r_height_next = 1 if not self._cyclops else 0
            self.eye_l_open = False; self.eye_r_open = not self._cyclops
            self._schedule_open()
        else:
            if left:
                self.eye_l_height_next = 1; self.eye_l_open = False
            if right and not self._cyclops:
                self.eye_r_height_next = 1; self.eye_r_open = False
            # Coerce None to False for sequence scheduling
            self._schedule_open(left=bool(left), right=bool(right))

    def _schedule_open(self, left=True, right=True):
        # after short delay restore heights
        def reopen(robo):
            if left:
                robo.eye_l_height_next = robo.eye_l_height_default; robo.eye_l_open = True
            if right and not robo._cyclops:
                robo.eye_r_height_next = robo.eye_r_height_default; robo.eye_r_open = True
        seq = self.sequences.add("blink")
        seq.step(120, reopen)
        seq.start()

    def wink(self, left=None, right=None):
        if not (left or right):
            raise ValueError("wink requires left or right True")
        self._wink_left = bool(left)
        self._wink_right = bool(right)
        self.wink_timer = pygame.time.get_ticks()
        if left:
            self.eye_l_height_next = 1
            self.eye_l_open = False
        if right and not self._cyclops:
            self.eye_r_height_next = 1
            self.eye_r_open = False

    def wink_left(self):
        """Convenience helper: wink left eye only."""
        if self._cyclops:
            # fall back to blink if only one eye
            self.blink(left=True)
        else:
            self.wink(left=True, right=False)

    def wink_right(self):
        """Convenience helper: wink right eye only."""
        if self._cyclops:
            self.blink(right=True)
        else:
            self.wink(left=False, right=True)

    def confuse(self):
        self._confused = True
        self.confused_animation_timer = pygame.time.get_ticks()

    def laugh(self):
        self._laugh = True
        self.laugh_animation_timer = pygame.time.get_ticks()

    # --- Update loop ----
    def update(self):
        # sequences (timed steps)
        self.sequences.update()
        now = pygame.time.get_ticks()
        if now - self.fps_timer < self.frame_interval:
            return
        self.fps_timer = now

        # Auto blink
        if self.autoblinker and now >= self._next_blink:
            self.blink()
            jitter = random.randint(0, self.blink_interval_variation)
            self._next_blink = now + self.blink_interval + jitter

        # Idle reposition
        if self.idle and now >= self._next_idle:
            max_x = self.screen_width - (self.eye_l_width_current + self.space_between_current + (0 if self._cyclops else self.eye_r_width_current))
            max_y = self.screen_height - self.eye_l_height_current
            self.eye_l_x_next = random.randint(0, max_x)
            self.eye_l_y_next = random.randint(0, max_y)
            jitter = random.randint(0, self.idle_interval_variation)
            self._next_idle = now + self.idle_interval + jitter

        # Interpolate geometry
        def lerp(a,b):
            return (a + b)//2
        # Smooth interpolation of geometry & positioning
        self.eye_l_width_current = lerp(self.eye_l_width_current, self.eye_l_width_next)
        self.eye_r_width_current = lerp(self.eye_r_width_current, self.eye_r_width_next)
        self.eye_l_height_current = lerp(self.eye_l_height_current, self.eye_l_height_next)
        self.eye_r_height_current = lerp(self.eye_r_height_current, self.eye_r_height_next)
        self.eye_l_radius_current = lerp(self.eye_l_radius_current, self.eye_l_radius_next)
        self.eye_r_radius_current = lerp(self.eye_r_radius_current, self.eye_r_radius_next)
        self.space_between_current = lerp(self.space_between_current, self.space_between_next)
        self.eye_l_x = lerp(self.eye_l_x, self.eye_l_x_next)
        self.eye_l_y = lerp(self.eye_l_y, self.eye_l_y_next)
        self.eye_r_x_next = self.eye_l_x_next + self.eye_l_width_current + self.space_between_current
        self.eye_r_y_next = self.eye_l_y_next
        self.eye_r_x = lerp(self.eye_r_x, self.eye_r_x_next)
        self.eye_r_y = lerp(self.eye_r_y, self.eye_r_y_next)

        # Handle wink restore
        if (self._wink_left or self._wink_right) and (now - self.wink_timer) > self.wink_duration:
            if self._wink_left:
                self.eye_l_height_next = self.eye_l_height_default; self.eye_l_open = True
            if self._wink_right and not self._cyclops:
                self.eye_r_height_next = self.eye_r_height_default; self.eye_r_open = True
            self._wink_left = False; self._wink_right = False

        # Confuse jitter (horizontal)
        if self._confused:
            if now - self.confused_animation_timer < self.confused_duration:
                jitter = 20
                self.eye_l_x += (-jitter if (now//80)%2 else jitter)
                self.eye_r_x += (-jitter if (now//80)%2 else jitter)
            else:
                self._confused = False

        # Laugh jitter (vertical)
        if self._laugh:
            if now - self.laugh_animation_timer < self.laugh_duration:
                jitter = 15
                self.eye_l_y += (-jitter if (now//80)%2 else jitter)
                self.eye_r_y += (-jitter if (now//80)%2 else jitter)
            else:
                self._laugh = False

        # Curious enlarge outer edges
        l_extra = r_extra = 0
        if self._curious:
            if self.eye_l_x < self.screen_width*0.25:
                l_extra = 12
            if self.eye_r_x > self.screen_width*0.75:
                r_extra = 12

        # Clear
        self.surface.fill(self.bgcolor)

        # Draw eyes (rounded rect or cute ellipse)
        def draw_eye(x,y,w,h,r, extra_height, is_left=True):
            # Eyelid adjustments for moods
            tired_cut = int(h*0.5) if self.tired else 0
            angry_cut = int(h*0.5) if self.angry else 0
            happy_bump = int(h*0.5) if self.happy else 0
            sad_cut = int(h*0.4) if self.sad else 0
            current_h = max(1, h + extra_height)
            rect = pygame.Rect(x, y, w, current_h)
            if self.cute:
                # Mood→iris palette
                if self._mood == HAPPY:
                    iris = (255, 189, 210)
                elif self._mood == CURIOUS:
                    iris = (150, 210, 255)
                elif self._mood == TIRED:
                    iris = (170, 180, 190)
                elif self._mood == ANGRY:
                    iris = (255, 140, 140)
                elif self._mood == SCARY:
                    iris = (140, 255, 170)
                elif self._mood == FROZEN:
                    iris = (185, 240, 255)
                elif self._mood == SAD:
                    iris = (150, 185, 255)
                else:
                    iris = (165, 245, 230)
                pygame.draw.ellipse(self.surface, self.sclera_color, rect)
                pygame.draw.ellipse(self.surface, self.outline_color, rect, width=3)
                margin = int(min(w, current_h)*0.18)
                iris_rect = rect.inflate(-2*margin, -2*margin)
                pygame.draw.ellipse(self.surface, iris, iris_rect)
                pupil_margin = int(min(iris_rect.width, iris_rect.height)*0.35)
                pupil_rect = iris_rect.inflate(-2*pupil_margin, -2*pupil_margin)
                pygame.draw.ellipse(self.surface, self.pupil_color, pupil_rect)
                hl_r = max(2, int(min(pupil_rect.width, pupil_rect.height)*0.18))
                hl_x = pupil_rect.left + int(pupil_rect.width*0.28)
                hl_y = pupil_rect.top + int(pupil_rect.height*0.28)
                pygame.draw.circle(self.surface, (255,255,255), (hl_x, hl_y), hl_r)
            else:
                pygame.draw.rect(self.surface, self.fgcolor, rect, border_radius=min(r, w//2, current_h//2))
            # Tired: cover top part
            if tired_cut:
                lid = pygame.Rect(x, y, w, tired_cut)
                pygame.draw.rect(self.surface, self.bgcolor, lid)
            # Angry: triangles (simplified)
            if angry_cut:
                if is_left:
                    pts = [(x, y), (x+w, y), (x+w, y+angry_cut)]
                else:
                    pts = [(x, y), (x+w, y), (x, y+angry_cut)]
                pygame.draw.polygon(self.surface, self.bgcolor, pts)
            # Happy: bottom cover to curve
            if happy_bump:
                lid = pygame.Rect(x, y+current_h-happy_bump, w, happy_bump)
                pygame.draw.rect(self.surface, self.bgcolor, lid, border_radius=min(r, w//2))
            # Sad: drooping upper lid (softer than tired)
            if sad_cut and not tired_cut and not angry_cut:
                # Draw a semi-transparent overlay then mask rectangle for a soft droop look
                lid = pygame.Rect(x, y, w, sad_cut)
                pygame.draw.rect(self.surface, self.bgcolor, lid)
                # Add a small curved arc by overdrawing a fgcolor ellipse then trimming bottom with bg
                arc_h = min(sad_cut, int(h*0.25))
                if arc_h > 4:
                    ellipse_rect = pygame.Rect(x, y+sad_cut-arc_h*2, w, arc_h*2)
                    pygame.draw.ellipse(self.surface, self.bgcolor, ellipse_rect)

        if not self._cyclops:
            draw_eye(self.eye_l_x, self.eye_l_y, self.eye_l_width_current, self.eye_l_height_current, self.eye_l_radius_current, l_extra, True)
            draw_eye(self.eye_r_x, self.eye_r_y, self.eye_r_width_current, self.eye_r_height_current, self.eye_r_radius_current, r_extra, False)
        else:
            # Single centered eye
            draw_eye(self.eye_l_x, self.eye_l_y, self.eye_l_width_current, self.eye_l_height_current, self.eye_l_radius_current, l_extra, True)

        # Optional frozen/scary flicker outlines
        if self._mood in (FROZEN, SCARY):
            alpha = 60 if (now//150)%2==0 else 25
            overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            color = (*self.fgcolor, alpha)
            pygame.draw.rect(overlay, color, (0,0,self.screen_width,self.screen_height), width=4)
            self.surface.blit(overlay, (0,0))

        # Done drawing

__all__ = [
    'RoboEyes','DEFAULT','TIRED','ANGRY','HAPPY','FROZEN','SCARY','CURIOUS','SAD','ON','OFF',
    'N','NE','E','SE','S','SW','W','NW'
]

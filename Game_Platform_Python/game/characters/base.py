import pygame
import os

from game.config import PLAYER_SCALE, GRAVITY


class Character:
    """A minimal base Character class.

    This class is intentionally small: it provides a hitbox, basic
    animation holder and draw/move helpers. Extend it for real behaviors.
    """

    def __init__(self, x: int, y: int, sprite_path: str = None, scale: float = PLAYER_SCALE):
        self.rect = pygame.Rect(x, y, int(120 * scale), int(240 * scale))
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        # Skills attached to this character. Keys are skill ids, values are SkillBase instances.
        # Filled by factory when metadata specifies skills.
        self.skills = {}
        self.state = "idle"
        self.animations = {}
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 0.15
        # sprite_path is optional — load_frames should handle missing path
        self.sprite_path = sprite_path

    def load_frames(self, folder, size):
        frames = []
        if not folder:
            return frames
        if not os.path.isdir(folder):
            print(f"Character.load_frames: folder not found: {folder}")
            return frames
        for filename in sorted(os.listdir(folder)):
            if filename.endswith('.png'):
                img = pygame.image.load(os.path.join(folder, filename)).convert_alpha()
                img = pygame.transform.scale(img, size)
                frames.append((img, 0))
        return frames

    def draw(self, surface, camera_x=0, camera_y=0):
        if self.state not in self.animations or not self.animations[self.state]:
            return
        frame_surf, bottom_trim = self.animations[self.state][self.current_frame]
        if not self.facing_right:
            frame_surf = pygame.transform.flip(frame_surf, True, False)
        sprite_rect = frame_surf.get_rect(midbottom=(self.rect.centerx - camera_x,
                                                     self.rect.bottom - camera_y + bottom_trim))
        surface.blit(frame_surf, sprite_rect)

    # --- Minimal Player-like API so Character can be a safe fallback ---
    def handle_input(self):
        # Default fallback does not handle input; subclasses or Player handle it.
        return

    def use_skill(self, name, now_time):
        s = self.skills.get(name)
        if not s:
            return False
        # If skill object, call its use method
        if not isinstance(s, dict) and hasattr(s, 'use'):
            try:
                return s.use(now_time, self)
            except Exception:
                return False
        # Legacy dict behavior: emulate minimal dash
        if isinstance(s, dict) and name == 'dash':
            if now_time - s.get('last_used', -999.0) < s.get('cooldown', 0):
                return False
            s['last_used'] = now_time
            s['active'] = True
            self.skill_timers = self.__dict__.get('skill_timers', {})
            self.skill_timers['dash_time_left'] = s.get('duration', 0.18)
            mult = s.get('speed_multiplier', 2.0)
            # set a horizontal velocity to simulate dash
            if self.facing_right:
                self.vel_x = mult * 10
            else:
                self.vel_x = -mult * 10
            return True
        return False

    def update_skills(self, dt):
        # Call update on skill objects where available
        for name, s in list(self.skills.items()):
            if not isinstance(s, dict) and hasattr(s, 'update'):
                try:
                    s.update(dt, self)
                except Exception:
                    pass
            elif isinstance(s, dict) and name == 'dash':
                self.skill_timers = self.__dict__.get('skill_timers', {})
                if s.get('active'):
                    self.skill_timers['dash_time_left'] -= dt
                    if self.skill_timers['dash_time_left'] <= 0:
                        s['active'] = False
                        self.vel_x = 0

    def move(self, platforms):
        # Simple movement + gravity and collision resolution similar to Player.move
        if getattr(self, 'vel_x', 0) != 0:
            self.rect.x += int(self.vel_x)
            for _, plat in platforms:
                if self.rect.colliderect(plat):
                    if self.vel_x > 0:
                        self.rect.right = plat.left
                    elif self.vel_x < 0:
                        self.rect.left = plat.right
        self.vel_y += GRAVITY
        self.rect.y += int(self.vel_y)
        self.on_ground = False
        for _, plat in platforms:
            if self.rect.colliderect(plat):
                if self.vel_y > 0:
                    self.rect.bottom = plat.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = plat.bottom
                    self.vel_y = 0

    def update_animation(self):
        frames = self.animations.get(self.state, [])
        if not frames:
            return
        self.animation_timer += self.animation_speed
        if self.state == 'jump':
            if self.current_frame < len(frames) - 1:
                if self.animation_timer >= 1:
                    self.current_frame += 1
                    self.animation_timer = 0
            else:
                self.current_frame = len(frames) - 1
        else:
            if self.animation_timer >= 1:
                self.current_frame = (self.current_frame + 1) % len(frames)
                self.animation_timer = 0


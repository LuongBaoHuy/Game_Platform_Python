import pygame
import os
from game.config import PLAYER_SCALE, GRAVITY, JUMP_POWER, SPEED


class Player:
    def __init__(self, x, y):
        # Hitbox kích thước phóng to theo PLAYER_SCALE
        self.rect = pygame.Rect(x, y, int(120 * PLAYER_SCALE), int(240 * PLAYER_SCALE))
        self.vel_y = 0
        self.vel_x = 0
        self.on_ground = False
        self.facing_right = True

        # Load các animation
        sprite_size = (int(512 * PLAYER_SCALE), int(512 * PLAYER_SCALE))
        # NOTE: use proper Windows absolute paths (include backslash after drive)
        self.animations = {
            "idle": self.load_frames(r"D:\LapTrinh_Python\Python_Game\BlueWizard\2BlueWizardIdle", sprite_size),
            "walk": self.load_frames(r"D:\LapTrinh_Python\Python_Game\BlueWizard\2BlueWizardWalk", sprite_size),
            "jump": self.load_frames(r"D:\LapTrinh_Python\Python_Game\BlueWizard\2BlueWizardJump", sprite_size),
            # Dash animation (user-provided folder)
            "dash": self.load_frames(r"D:\LapTrinh_Python\Python_Game\BlueWizard\2BlueWizardJump\Dash2", sprite_size),
        }

        self.state = "idle"
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 0.15

        # Skills: dash implemented here
        # dash: short burst of horizontal speed with cooldown
        self.skills = {
            "dash": {"cooldown": 1.0, "last_used": -999.0, "duration": 0.18, "active": False, "speed_multiplier": 3.0}
        }
        self.skill_timers = {}

    def load_frames(self, folder, size):
        frames = []
        # If folder doesn't exist, return empty list and print helpful message
        if not os.path.isdir(folder):
            print(f"Player.load_frames: folder not found: {folder}")
            return frames
        for filename in sorted(os.listdir(folder)):
            if filename.endswith(".png"):
                img = pygame.image.load(os.path.join(folder, filename)).convert_alpha()
                img = pygame.transform.scale(img, size)
                # compute transparent rows at bottom so we can align visible pixels to hitbox
                h = img.get_height()
                bottom_trim = 0
                for y in range(h - 1, -1, -1):
                    row_has_pixel = False
                    for x in range(img.get_width()):
                        if img.get_at((x, y))[3] != 0:
                            row_has_pixel = True
                            break
                    if row_has_pixel:
                        bottom_trim = h - 1 - y
                        break
                frames.append((img, bottom_trim))
        return frames

    def handle_input(self):
        keys = pygame.key.get_pressed()
        moving = False
        # Nếu đang dash thì không override vel_x từ input
        if not self.skills["dash"]["active"]:
            self.vel_x = 0
            # Move left: Left arrow or A
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.vel_x = -SPEED
                self.facing_right = False
                moving = True
            # Move right: Right arrow or D
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.vel_x = SPEED
                self.facing_right = True
                moving = True

        # Dash key (K)
        if keys[pygame.K_k]:
            now = pygame.time.get_ticks() / 1000.0
            self.use_skill("dash", now)
        # Jump: Space or W
        if (keys[pygame.K_SPACE] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_POWER
            self.on_ground = False
            self.state = "jump"
            self.current_frame = 0

        # Không ghi đè state nếu đang dash, để dash animation có thể chạy
        if not self.skills["dash"]["active"]:
            if not self.on_ground:
                self.state = "jump"
            elif moving:
                self.state = "walk"
            else:
                self.state = "idle"

    def move(self, platforms):
        if self.vel_x != 0:
            self.rect.x += self.vel_x
            for _, plat in platforms:
                if self.rect.colliderect(plat):
                    if self.vel_x > 0:
                        self.rect.right = plat.left
                    elif self.vel_x < 0:
                        self.rect.left = plat.right
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y
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
        frames = self.animations[self.state]
        self.animation_timer += self.animation_speed
        if self.state == "jump":
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

    def use_skill(self, name, now_time):
        s = self.skills.get(name)
        if not s:
            return False
        if now_time - s["last_used"] < s["cooldown"]:
            return False
        s["last_used"] = now_time
        if name == "dash":
            s["active"] = True
            self.skill_timers["dash_time_left"] = s["duration"]
            mult = s.get("speed_multiplier", 2.0)
            self.vel_x = SPEED * mult if self.facing_right else -SPEED * mult
            # switch to dash animation
            self.state = "dash"
            self.current_frame = 0
        return True

    def update_skills(self, dt):
        # dt in seconds
        dash = self.skills.get("dash")
        if dash and dash["active"]:
            self.skill_timers["dash_time_left"] -= dt
            if self.skill_timers["dash_time_left"] <= 0:
                dash["active"] = False
                # stop dash horizontal velocity (input will set next frame)
                self.vel_x = 0
                # after dash, reset state so animation returns properly
                self.state = "idle"

    def draw(self, surface, camera_x, camera_y):
        frames = self.animations[self.state]
        frame_surf, bottom_trim = frames[self.current_frame]
        if not self.facing_right:
            frame_surf = pygame.transform.flip(frame_surf, True, False)
        sprite_rect = frame_surf.get_rect(midbottom=(self.rect.centerx - camera_x,
                                                     self.rect.bottom - camera_y + bottom_trim))
        surface.blit(frame_surf, sprite_rect)
        pygame.draw.rect(surface, (255, 0, 0),
                         (self.rect.x - camera_x, self.rect.y - camera_y,
                          self.rect.width, self.rect.height), 2)

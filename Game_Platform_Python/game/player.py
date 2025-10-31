import pygame
import os
from game.config import PLAYER_SCALE, GRAVITY, JUMP_POWER, SPEED

# Cố gắng import SkillBase để hỗ trợ hệ thống skill mới (data-driven).
try:
    from game.characters.skills import SkillBase
except Exception:
    SkillBase = None


class Player:
    def __init__(
        self,
        x,
        y,
        sprite_path: str = None,
        frames_map: dict = None,
        scale: float = None,
    ):
        """Player constructor.

        Parameters:
        - x, y: initial position
        - sprite_path: optional base folder for <state> subfolders (idle/walk/jump/dash)
        - frames_map: optional dict mapping state -> explicit folder path
        - scale: optional scale to override global PLAYER_SCALE
        """
        self.scale = scale if (scale is not None) else PLAYER_SCALE
        # Hitbox kích thước phóng to theo scale
        self.rect = pygame.Rect(x, y, int(120 * self.scale), int(240 * self.scale))
        self.vel_y = 0
        self.vel_x = 0
        self.on_ground = False
        self.facing_right = True

        # Prepare animations container. We'll load frames conditionally below.
        self.animations = {"idle": [], "walk": [], "jump": [], "dash": []}
        sprite_size = (int(512 * self.scale), int(512 * self.scale))

        # If frames_map or sprite_path provided, try to load frames accordingly.
        frames_map = frames_map or {}
        if frames_map:
            for state in ("idle", "walk", "jump", "dash"):
                folder = frames_map.get(state)
                if folder:
                    self.animations[state] = self.load_frames(folder, sprite_size)
        elif sprite_path:
            for state in ("idle", "walk", "jump", "dash"):
                candidate = os.path.join(sprite_path, state)
                self.animations[state] = self.load_frames(candidate, sprite_size)

        self.state = "idle"
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 0.15
        # Health and Mana
        self.max_hp = 100
        self.hp = self.max_hp
        self.max_mana = 100
        self.mana = self.max_mana
        self.mana_regen_rate = 20  # Mana points per second
        self.alive = True
        self.can_use_skills = True  # Flag to control skill usage

        # Skills: có thể là legacy dict (như trước) hoặc các instance SkillBase
        # Nếu factory gắn skill (SkillBase) thì self.skills sẽ chứa các instance
        # Ví dụ dạng legacy: self.skills = {"dash": {"cooldown":..., ...}}
        self.skills = {
            "dash": {
                "cooldown": 1.0,
                "last_used": -999.0,
                "duration": 0.18,
                "active": False,
                "speed_multiplier": 3.0,
            }
        }
        # skill_timers dùng cho legacy implementation; SkillBase subclasses có thể
        # quản lý timer riêng trong instance của chúng.
        self.skill_timers = {}
        # Charging state for hold-to-charge skill (L)
        self._is_charging = False
        self._charge_start = 0.0

        # Attach a default ChargeSkill instance if available
        try:
            from game.characters.skills import ChargeSkill

            # default frames_path points to repo-relative assets/skill-effect
            try:
                # Prefer the specific purple_skill folder and ensure large scale
                self.skills["charge"] = ChargeSkill(
                    frames_path=os.path.join("assets", "skill-effect", "purple_skill"),
                    base_speed=1200,
                    base_damage=30,
                    max_charge=3.0,
                    scale=10.0,
                )
            except Exception:
                # if instantiation fails, skip
                pass
        except Exception:
            pass

    def load_frames(self, folder, size):
        frames = []
        # If folder doesn't exist, return empty list
        if not os.path.isdir(folder):
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
        # Hỗ trợ cả 2 hệ thống skill:
        # - Nếu skill là object (SkillBase) dùng thuộc tính .active
        # - Nếu là dict legacy thì dùng key 'active'
        dash_obj = self.skills.get("dash")
        dash_active = False
        if isinstance(dash_obj, dict):
            dash_active = bool(dash_obj.get("active"))
        elif SkillBase is not None and hasattr(dash_obj, "active"):
            dash_active = bool(getattr(dash_obj, "active", False))

        if not dash_active:
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
            # Nếu skill là object: gọi phương thức use của nó
            dash = self.skills.get("dash")
            if (
                SkillBase is not None
                and not isinstance(dash, dict)
                and hasattr(dash, "use")
            ):
                # use(now, owner) -> skill có thể căn cứ owner.vel_x để áp lực
                try:
                    dash.use(now, self)
                except Exception:
                    pass
            else:
                # fallback sang legacy
                self.use_skill("dash", now)
        # Blast key (J) - chưởng ra
        if keys[pygame.K_j]:
            now = pygame.time.get_ticks() / 1000.0
            blast = self.skills.get("blast")
            if (
                SkillBase is not None
                and not isinstance(blast, dict)
                and hasattr(blast, "use")
            ):
                try:
                    blast.use(now, self)
                except Exception:
                    pass
            else:
                # If legacy dict provided, try use_skill fallback
                self.use_skill("blast", now)
        # Jump: Space or W
        if (keys[pygame.K_SPACE] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_POWER
            self.on_ground = False
            self.state = "jump"
            self.current_frame = 0

        # Use skill key (L) - press to use skill when mana is full
        if keys[pygame.K_l]:
            try:
                charge_skill = self.skills.get("charge")
                if self.can_use_skills and charge_skill is not None:
                    now = pygame.time.get_ticks() / 1000.0
                    if self.use_mana(self.max_mana):  # Use all mana for the skill
                        # Ensure a ChargeSkill instance exists (attach dynamically if factory didn't)
                        if charge_skill is None:
                            from game.characters.skills import ChargeSkill

                            # explicitly point to purple_skill frames and use large scale
                            inst = ChargeSkill(
                                frames_path=os.path.join(
                                    "assets", "skill-effect", "purple_skill"
                                ),
                                base_speed=1200,
                                base_damage=30,
                                max_charge=3.0,
                                scale=20.0,
                            )
                            self.skills["charge"] = inst
                            charge_skill = inst

                        # Fire skill immediately at full power
                        if (
                            SkillBase is not None
                            and not isinstance(charge_skill, dict)
                            and hasattr(charge_skill, "release")
                        ):
                            charge_skill.release(now, self, 3.0)  # Use max charge
            except Exception as e:
                print(f"Error using charge skill: {e}")

        # Không ghi đè state nếu đang dash, để dash animation có thể chạy
        # Dùng dash_active (đã tính toán ở trên) để tránh KeyError khi c.skills không có 'dash'
        # Recompute dash_active because use() above may have activated the skill
        dash_obj = self.skills.get("dash")
        dash_active = False
        if isinstance(dash_obj, dict):
            dash_active = bool(dash_obj.get("active"))
        elif SkillBase is not None and hasattr(dash_obj, "active"):
            dash_active = bool(getattr(dash_obj, "active", False))

        if not dash_active:
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

    def update_mana(self, dt):
        # Regenerate mana over time if not full
        if self.mana < self.max_mana:
            self.mana = min(self.max_mana, self.mana + self.mana_regen_rate * dt)
            # Only allow using skills when mana is full
            self.can_use_skills = False
        else:
            self.can_use_skills = True

    def use_mana(self, amount):
        # Only allow using skills when mana is 100%
        if self.mana >= self.max_mana and self.can_use_skills:
            self.mana = 0  # Use all mana
            self.can_use_skills = False  # Disable skills until mana is full again
            return True
        return False

    def update_animation(self):
        frames = self.animations.get(self.state, [])
        # If there are no frames for this state, keep current_frame at 0 and skip
        if not frames:
            self.current_frame = 0
            return

        # Ensure current_frame is within bounds
        self.current_frame = max(0, min(self.current_frame, len(frames) - 1))

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
                # advance and wrap
                self.current_frame = (self.current_frame + 1) % len(frames)
                self.animation_timer = 0

    def use_skill(self, name, now_time):
        # Legacy fallback: nếu skill là dict thì xử lý như cũ
        s = self.skills.get(name)
        if not s:
            return False
        if isinstance(s, dict):
            if now_time - s.get("last_used", -999.0) < s.get("cooldown", 0):
                return False
            s["last_used"] = now_time
            if name == "dash":
                s["active"] = True
                self.skill_timers["dash_time_left"] = s.get("duration", 0.18)
                mult = s.get("speed_multiplier", 2.0)
                self.vel_x = SPEED * mult if self.facing_right else -SPEED * mult
                # switch to dash animation
                self.state = "dash"
                self.current_frame = 0
            return True
        else:
            # Nếu là skill object (SkillBase), gọi phương thức use
            if hasattr(s, "use"):
                try:
                    return s.use(now_time, self)
                except Exception:
                    return False
            return False

    def take_damage(self, amount: int):
        try:
            self.hp -= int(amount)
        except Exception:
            self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def update_skills(self, dt):
        # dt in seconds
        # Hỗ trợ cả hệ thống mới (SkillBase instances) và legacy dict
        for name, s in list(self.skills.items()):
            # Nếu là object có update method -> dùng nó
            if not isinstance(s, dict) and hasattr(s, "update"):
                try:
                    s.update(dt, self)
                except Exception:
                    pass
                continue

            # Legacy xử lý cho dash
            if name == "dash" and isinstance(s, dict):
                if s.get("active"):
                    self.skill_timers["dash_time_left"] -= dt
                    if self.skill_timers["dash_time_left"] <= 0:
                        s["active"] = False
                        # stop dash horizontal velocity (input will set next frame)
                        self.vel_x = 0
                        # after dash, reset state so animation returns properly
                        self.state = "idle"

    def draw(self, surface, camera_x, camera_y):
        frames = self.animations.get(self.state, [])
        if not frames:
            return

        # Clamp current_frame to valid index
        if self.current_frame >= len(frames) or self.current_frame < 0:
            self.current_frame = self.current_frame % len(frames)

        frame_surf, bottom_trim = frames[self.current_frame]
        if not self.facing_right:
            frame_surf = pygame.transform.flip(frame_surf, True, False)
        sprite_rect = frame_surf.get_rect(
            midbottom=(
                self.rect.centerx - camera_x,
                self.rect.bottom - camera_y + bottom_trim,
            )
        )
        surface.blit(frame_surf, sprite_rect)
        pygame.draw.rect(
            surface,
            (255, 0, 0),
            (
                self.rect.x - camera_x,
                self.rect.y - camera_y,
                self.rect.width,
                self.rect.height,
            ),
            2,
        )

        # Draw any skill visuals (e.g. projectiles) if skill instances expose draw()
        for name, s in getattr(self, "skills", {}).items():
            if not isinstance(s, dict) and hasattr(s, "draw"):
                try:
                    s.draw(surface, camera_x, camera_y)
                except Exception:
                    pass

        # Draw a small charging indicator above the player if holding L
        try:
            if getattr(self, "_is_charging", False):
                cx = int(self.rect.centerx - camera_x)
                cy = int(self.rect.top - camera_y - 10)
                # small translucent circle
                surf = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(surf, (120, 200, 255, 160), (20, 20), 14)
                surface.blit(surf, (cx - 20, cy - 20))
        except Exception:
            pass

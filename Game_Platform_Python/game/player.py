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
        # Get reference to sound manager for sound effects
        from game.sound_manager import SoundManager

        self.sound_manager = SoundManager()

        # Track previous key states
        self._prev_key_states = {pygame.K_j: False}  # Track J key state

        self.scale = scale if (scale is not None) else PLAYER_SCALE
        # Hitbox kích thước phóng to theo scale
        self.rect = pygame.Rect(x, y, int(120 * self.scale), int(240 * self.scale))
        self.vel_y = 0
        self.vel_x = 0
        self.on_ground = False
        self.facing_right = True
        self.visible = True  # For teleport skill invisibility
        self.teleport_lock = 0.0  # Lock movement briefly after teleport
        self.physics_lock = 0.0  # Lock physics updates briefly after teleport
        
        # Double jump system
        self.max_jumps = 2  # Maximum number of jumps (1 ground + 1 air)
        self.jump_count = 0  # Current number of jumps used
        self.jump_key_pressed = False  # Track if jump key is currently pressed

        # Prepare animations container. We'll load frames conditionally below.
        self.animations = {"idle": [], "walk": [], "jump": [], "dash": [], "attack": []}
        sprite_size = (int(512 * self.scale), int(512 * self.scale))

        # If frames_map or sprite_path provided, try to load frames accordingly.
        frames_map = frames_map or {}
        if frames_map:
            for state in ("idle", "walk", "jump", "dash", "attack"):
                folder = frames_map.get(state)
                if folder:
                    self.animations[state] = self.load_frames(folder, None)
        elif sprite_path:
            for state in ("idle", "walk", "jump", "dash", "attack"):
                candidate = os.path.join(sprite_path, state)
                self.animations[state] = self.load_frames(candidate, None)

        self.state = "idle"
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 0.15
        # Attack animation tracking
        self.attack_active = False
        self.attack_timer = 0.0
        self.attack_duration = 0.5  # Attack animation duration in seconds
        # Health and Mana
        self.max_hp = 100
        self.hp = self.max_hp
        self.max_mana = 100
        self.mana = self.max_mana
        self.mana_regen_rate = 20  # Mana points per second
        self.alive = True
        self.can_use_skills = True  # Flag to control skill usage

        # Skill direction system
        self.shoot_direction = {"x": 0, "y": 0}  # Direction vector for skills

        # Skills: có thể là legacy dict (như trước) hoặc các instance SkillBase
        # Nếu factory gắn skill (SkillBase) thì self.skills sẽ chứa các instance
        # Ví dụ dạng legacy: self.skills = {"dash": {"cooldown":..., ...}}
        self.skills = {
            "dash": {
                "cooldown": 1.0,
                "last_used": -999.0,
                "duration": 0.8,
                "active": False,
                "speed_multiplier": 2.5,
            }
        }

        # Track jump and dash state for cloud skill
        self.has_jumped = False
        self.has_dashed = False
        # skill_timers dùng cho legacy implementation; SkillBase subclasses có thể
        # quản lý timer riêng trong instance của chúng.
        self.skill_timers = {}
        # Charging state for hold-to-charge skill (L)
        self._is_charging = False
        self._charge_start = 0.0

        # Attach a default ChargeSkill instance if available
        try:
            from game.characters.skills import ChargeSkill

            # Attach a default ChargeSkill instance if available
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

            # Add cloud skill
            try:
                from game.characters.skills import CloudSkill

                cloud_skill = CloudSkill()
                cloud_skill.set_owner(
                    self
                )  # This will set the owner and scale the cloud properly
                self.skills["cloud"] = cloud_skill
            except Exception as e:
                print(f"Error creating cloud skill: {e}")
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
                img = pygame.image.load(os.path.join(folder, filename))
                # Try convert_alpha, fallback to convert if display not set
                try:
                    img = img.convert_alpha()
                except pygame.error:
                    try:
                        img = img.convert()
                    except pygame.error:
                        pass  # Use original if conversion fails

                # Scale proportionally based on self.scale instead of fixed size
                original_w, original_h = img.get_size()
                new_w = int(original_w * self.scale)
                new_h = int(original_h * self.scale)
                img = pygame.transform.scale(img, (new_w, new_h))
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

        # Check if movement is locked (after teleport)
        if self.teleport_lock > 0:
            self.teleport_lock -= 1.0 / 60  # Reduce lock timer
            if self.teleport_lock <= 0:
                self.teleport_lock = 0
                # Reset velocity to ensure clean state
                self.vel_x = 0
                self.vel_y = 0
            return  # Skip all input while locked

        # Update shooting direction based on movement keys
        self.shoot_direction["x"] = 0
        self.shoot_direction["y"] = 0
        if keys[pygame.K_w]:  # Up
            self.shoot_direction["y"] = -1
        if keys[pygame.K_s]:  # Down
            self.shoot_direction["y"] = 1
        if keys[pygame.K_d]:  # Right
            self.shoot_direction["x"] = 1
            self.facing_right = True
        if keys[pygame.K_a]:  # Left
            self.shoot_direction["x"] = -1
            self.facing_right = False
        # Nếu đang dash thì không override vel_x từ input
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

        # Dash key (K) - dash skill
        if keys[pygame.K_k]:
            now = pygame.time.get_ticks() / 1000.0

            # Dash skill for both characters
            dash = self.skills.get("dash")
            if (
                SkillBase is not None
                and not isinstance(dash, dict)
                and hasattr(dash, "use")
            ):
                try:
                    if dash.use(now, self):
                        self.has_dashed = True  # Track that we've dashed
                except Exception:
                    pass
            else:
                # Legacy fallback
                if self.use_skill("dash", now):
                    self.has_dashed = True  # Track that we've dashed
                    self.sound_manager.play_sound("dash")

        # Cloud Skill (I key) - only when jumped and dashed
        if (
            keys[pygame.K_i]
            and not self.on_ground
            and self.has_jumped
            and self.has_dashed
        ):
            now = pygame.time.get_ticks() / 1000.0
            cloud = self.skills.get("cloud")
            if (
                SkillBase is not None
                and not isinstance(cloud, dict)
                and hasattr(cloud, "use")
            ):
                try:
                    if cloud.use(now, self):
                        # Reset jump and dash flags after using cloud skill
                        self.has_jumped = False
                        self.has_dashed = False
                except Exception as e:
                    print(f"Error using cloud skill: {e}")
        # Blast key (J) - chưởng ra
        j_key_pressed = keys[pygame.K_j]
        j_key_just_pressed = j_key_pressed and not self._prev_key_states[pygame.K_j]

        if j_key_pressed:  # Handle skill activation
            now = pygame.time.get_ticks() / 1000.0

            # Check for fire skill first (Fire Wizard)
            fire = self.skills.get("fire")
            if (
                SkillBase is not None
                and not isinstance(fire, dict)
                and hasattr(fire, "use")
            ):
                try:
                    if fire.use(now, self):
                        if j_key_just_pressed:
                            self.sound_manager.play_sound("attack")
                except Exception as e:
                    print(f"Error using fire skill: {e}")
            else:
                # If no fire skill, try blast skill (Blue Wizard)
                blast = self.skills.get("blast")
                if (
                    SkillBase is not None
                    and not isinstance(blast, dict)
                    and hasattr(blast, "use")
                ):
                    try:
                        if blast.use(now, self):
                            if j_key_just_pressed:
                                self.sound_manager.play_sound("attack")
                                self.trigger_attack_animation()  # Trigger attack animation
                    except Exception as e:
                        print(f"Error using blast skill: {e}")
                else:
                    # If legacy dict provided, try use_skill fallback
                    if self.use_skill("blast", now) and j_key_just_pressed:
                        self.sound_manager.play_sound("attack")
                        self.trigger_attack_animation()  # Trigger attack animation

        # Update previous key state
        self._prev_key_states[pygame.K_j] = j_key_pressed
        
        # Jump: Space only (with double jump support)
        jump_key_pressed = keys[pygame.K_SPACE]
        
        # Check if jump key was just pressed (not held)
        if jump_key_pressed and not self.jump_key_pressed:
            # Can jump if: on ground OR still have air jumps available
            if self.on_ground or self.jump_count < self.max_jumps:
                self.vel_y = JUMP_POWER
                self.jump_count += 1
                self.on_ground = False
                self.state = "jump"
                self.current_frame = 0
                self.has_jumped = True  # Track that we've jumped
                
                # Play different sound for double jump
                if self.jump_count == 1:
                    self.sound_manager.play_sound("jump")
                else:
                    self.sound_manager.play_sound("jump")  # Could use different sound for double jump
        
        # Update jump key state for next frame
        self.jump_key_pressed = jump_key_pressed

        # Ultimate skill key (L) - Fire Wizard: Fire Explosion, Blue Wizard: Charge Skill
        if keys[pygame.K_l]:
            try:
                now = pygame.time.get_ticks() / 1000.0
                if self.can_use_skills:  # Requires full mana

                    # Check for Fire Wizard's fire explosion skill first
                    fire_explosion = self.skills.get("fire_explosion")
                    if (
                        SkillBase is not None
                        and not isinstance(fire_explosion, dict)
                        and hasattr(fire_explosion, "use")
                    ):
                        if self.use_mana(self.max_mana):  # Use all mana for ultimate
                            if fire_explosion.use(now, self):
                                self.sound_manager.play_sound("explosion")
                                self.trigger_attack_animation()  # Trigger attack animation
                    else:
                        # Blue Wizard charge skill
                        charge_skill = self.skills.get("charge")
                        if charge_skill is not None:
                            if self.use_mana(
                                self.max_mana
                            ):  # Use all mana for the skill
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
                                    charge_skill.release(
                                        now, self, 3.0
                                    )  # Use max charge
                                    self.sound_manager.play_sound("charge_skill")
            except Exception as e:
                print(f"Error using ultimate skill: {e}")

        # Không ghi đè state nếu đang dash, để dash animation có thể chạy
        # Dùng dash_active (đã tính toán ở trên) để tránh KeyError khi c.skills không có 'dash'
        # Recompute skill active states because use() above may have activated them
        dash_obj = self.skills.get("dash")
        run_obj = self.skills.get("run")
        dash_active = False
        run_active = False

        if isinstance(dash_obj, dict):
            dash_active = bool(dash_obj.get("active"))
        elif SkillBase is not None and hasattr(dash_obj, "active"):
            dash_active = bool(getattr(dash_obj, "active", False))

        if isinstance(run_obj, dict):
            run_active = bool(run_obj.get("active"))
        elif SkillBase is not None and hasattr(run_obj, "active"):
            run_active = bool(getattr(run_obj, "active", False))

        # Set state based on current conditions (don't override attack animation)
        if not self.attack_active:  # Only change state if not attacking
            if run_active:
                self.state = "run"
            elif dash_active:
                self.state = "dash"
            elif not self.on_ground:
                self.state = "jump"
            elif moving:
                self.state = "walk"
            else:
                self.state = "idle"

    def move(self, platforms):
        # Update physics lock timer
        if self.physics_lock > 0:
            self.physics_lock -= 1.0 / 60  # Assuming 60 FPS
            if self.physics_lock <= 0:
                self.physics_lock = 0
            # Skip physics updates while locked to prevent teleport interference
            return

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
                    # Reset jump and dash flags when landing
                    self.has_jumped = False
                    self.has_dashed = False
                    # Reset jump count for double jump system
                    self.jump_count = 0
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

        # Handle attack animation (plays once then returns to idle)
        if self.state == "attack":
            if self.current_frame < len(frames) - 1:
                if self.animation_timer >= 1:
                    self.current_frame += 1
                    self.animation_timer = 0
            else:
                # Attack animation finished, return to idle
                self.attack_active = False
                self.state = "idle"
                self.current_frame = 0
        elif self.state == "jump":
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
            self.sound_manager.play_sound("game_over")
        self.sound_manager.play_sound("hurt")

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

    def trigger_attack_animation(self):
        """Trigger attack animation when using skills."""
        if self.animations.get("attack"):  # Only if attack frames are loaded
            self.attack_active = True
            self.attack_timer = 0.0
            self.state = "attack"
            self.current_frame = 0

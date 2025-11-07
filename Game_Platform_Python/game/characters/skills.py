"""Skills system.

Defines a small SkillBase contract and a sample DashSkill. Skills can be
registered into the skill registry so the factory can instantiate them by
id using character metadata.
"""

from typing import Dict, Any

from game.characters import registry
from game.config import SPEED


class SkillBase:
    """Minimal skill interface.

    Subclasses should override `use` and `update` as necessary.
    """

    def __init__(self, **params):
        self.params = params
        self.cooldown = params.get("cooldown", 0.0)
        self.last_used = -999.0
        self.active = False

    def can_use(self, now: float) -> bool:
        return (now - self.last_used) >= self.cooldown

    def use(self, now: float, owner) -> bool:
        """Activate the skill. Return True if used."""
        if not self.can_use(now):
            return False
        self.last_used = now
        self.active = True
        return True

    def update(self, dt: float, owner) -> None:
        """Update skill timers/effects. Override in subclasses."""
        pass


class DashSkill(SkillBase):
    def __init__(
        self,
        cooldown=1.0,
        duration=0.8,
        speed_multiplier=2.5,
        frames_path=None,
        **kwargs,
    ):
        super().__init__(
            cooldown=cooldown,
            duration=duration,
            speed_multiplier=speed_multiplier,
            **kwargs,
        )
        self.duration = duration
        self.speed_multiplier = speed_multiplier
        self.time_left = 0.0
        self.frames_path = frames_path
        self.effect_frames = []
        self.effect_frame_index = 0
        self.effect_timer = 0.0
        self.effect_speed = 0.1  # Time between frames
        self.effect_pos = (0, 0)

        # Load effect frames if path provided
        if frames_path:
            self.load_effect_frames()

    def load_effect_frames(self):
        """Load visual effect frames from the specified path."""
        import pygame
        import os

        if not self.frames_path:
            return

        try:
            # Convert relative path to absolute
            if not os.path.isabs(self.frames_path):
                repo_root = os.path.normpath(
                    os.path.join(os.path.dirname(os.path.dirname(__file__)), "..")
                )
                full_path = os.path.join(repo_root, self.frames_path)
            else:
                full_path = self.frames_path

            if os.path.exists(full_path):
                files = sorted([f for f in os.listdir(full_path) if f.endswith(".png")])
                for filename in files:
                    img_path = os.path.join(full_path, filename)
                    img = pygame.image.load(img_path)
                    try:
                        img = img.convert_alpha()
                    except pygame.error:
                        try:
                            img = img.convert()
                        except pygame.error:
                            pass
                    # Scale the effect
                    img = pygame.transform.scale(img, (128, 128))
                    self.effect_frames.append(img)
        except Exception as e:
            print(f"Failed to load dash effect frames: {e}")

    def use(self, now: float, owner) -> bool:
        if not super().use(now, owner):
            return False
        self.time_left = self.duration

        # Play dash sound
        if hasattr(owner, "sound_manager"):
            owner.sound_manager.play_sound("dash")

        # Reset effect animation
        self.effect_frame_index = 0
        self.effect_timer = 0.0
        self.effect_pos = (owner.rect.centerx, owner.rect.centery)

        # Apply a burst of horizontal speed. Caller should set vel_x before use.
        if owner.vel_x != 0:
            owner.vel_x = owner.vel_x * self.speed_multiplier
        else:
            # If owner was stationary, apply a dash in facing direction
            owner.vel_x = (
                SPEED * self.speed_multiplier
                if getattr(owner, "facing_right", True)
                else -SPEED * self.speed_multiplier
            )
        # Set owner state to dash so animation plays
        try:
            owner.state = "dash"
            owner.current_frame = 0
        except Exception:
            pass
        return True

    def update(self, dt: float, owner) -> None:
        if not self.active:
            return

        # Update effect animation
        if self.effect_frames:
            self.effect_timer += dt
            if self.effect_timer >= self.effect_speed:
                self.effect_frame_index = (self.effect_frame_index + 1) % len(
                    self.effect_frames
                )
                self.effect_timer = 0.0

        self.time_left -= dt
        if self.time_left <= 0:
            self.active = False
            # stop extra velocity; concrete owner logic should restore input-based velocity
            owner.vel_x = 0
            # restore state (basic heuristic)
            try:
                if not getattr(owner, "on_ground", True):
                    owner.state = "jump"
                elif getattr(owner, "vel_x", 0) != 0:
                    owner.state = "walk"
                else:
                    owner.state = "idle"
                owner.current_frame = 0
            except Exception:
                pass

    def draw(self, surface, camera_x=0, camera_y=0):
        """Draw dash visual effect."""
        if not self.active or not self.effect_frames:
            return

        if self.effect_frame_index < len(self.effect_frames):
            frame = self.effect_frames[self.effect_frame_index]
            # Draw effect at owner's position
            draw_x = self.effect_pos[0] - frame.get_width() // 2 - camera_x
            draw_y = self.effect_pos[1] - frame.get_height() // 2 - camera_y
            surface.blit(frame, (draw_x, draw_y))


# Register built-in skills
registry.register_skill("dash", DashSkill)

import os
import pygame

# Helper to find project root for default asset locations
_REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "..")
)


class Projectile:
    def __init__(
        self, x, y, vx, vy, frames, lifetime=1.5, damage=25, owner=None, scale=1.0
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.raw_frames = frames or []
        self.scale = float(scale) if scale is not None else 1.0
        # prepare scaled frames (surface, trim)
        self.frames = []
        for item in self.raw_frames:
            try:
                surf, trim = item
            except Exception:
                surf = item
                trim = 0
            if self.scale != 1.0 and surf is not None:
                w, h = surf.get_size()
                sw = max(1, int(w * self.scale))
                sh = max(1, int(h * self.scale))
                try:
                    scaled = pygame.transform.scale(surf, (sw, sh))
                except Exception:
                    scaled = surf
                self.frames.append((scaled, trim))
            else:
                self.frames.append((surf, trim))

        self.current = 0
        self.timer = 0.0
        self.frame_time = 0.06
        self.lifetime = lifetime
        self.age = 0.0
        # compute bounding rect from first frame if available
        if self.frames and self.frames[0][0] is not None:
            surf, _ = self.frames[0]
            self.rect = surf.get_rect(center=(int(self.x), int(self.y)))
        else:
            self.rect = pygame.Rect(
                int(self.x),
                int(self.y),
                max(8, int(8 * self.scale)),
                max(8, int(8 * self.scale)),
            )
        self.damage = damage
        self.owner = owner
        # for piercing projectiles we track which enemies we've already hit
        self.hit_targets = set()

    def update(self, dt):
        self.age += dt
        if self.age > self.lifetime:
            return False
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.timer += dt
        if self.timer >= self.frame_time and self.frames:
            self.current = (self.current + 1) % len(self.frames)
            self.timer = 0.0
        if self.frames:
            surf, trim = self.frames[self.current]
            self.rect = surf.get_rect(center=(int(self.x), int(self.y)))
        else:
            self.rect.topleft = (int(self.x), int(self.y))
        return True

    def draw(self, surface, camera_x=0, camera_y=0):
        if not self.frames:
            pygame.draw.circle(
                surface,
                (128, 0, 255),
                (int(self.x - camera_x), int(self.y - camera_y)),
                6,
            )
            return
        surf, trim = self.frames[self.current]
        dst = surf.get_rect(center=(int(self.x - camera_x), int(self.y - camera_y)))
        surface.blit(surf, dst)


class ProjectileSkill(SkillBase):
    """Skill that fires a projectile (purple blast).

    Params (via metadata):
      - frames_path: explicit path to folder with frames (optional)
      - speed: horizontal speed of projectile
      - lifetime: lifetime in seconds
      - cooldown
    """

    def __init__(
        self,
        frames_path=None,
        speed=3600,
        lifetime=1.2,
        cooldown=0.5,
        damage=25,
        **kwargs,
    ):
        super().__init__(cooldown=cooldown)

        # Cho phép tùy chỉnh scale từ metadata (mặc định 1.0)
        self.scale = float(kwargs.get("scale", 1.0))
        self.frames_path = frames_path
        self.speed = speed
        self.lifetime = lifetime
        self.projectiles = []
        self.damage = damage

        # load frames (try absolute or repo-relative)
        frames = []
        candidates = []
        if frames_path:
            candidates.append(frames_path)
            candidates.append(os.path.join(_REPO_ROOT, frames_path))
        # default path inside repo
        candidates.append(
            os.path.join(_REPO_ROOT, "assets", "skill-effect", "purple_skill")
        )

        for cand in candidates:
            cand = os.path.normpath(cand)
            if os.path.isdir(cand):
                for fn in sorted(os.listdir(cand)):
                    if fn.lower().endswith(".png"):
                        img = pygame.image.load(os.path.join(cand, fn))
                        # Try convert_alpha, fallback to convert if display not set
                        try:
                            img = img.convert_alpha()
                        except pygame.error:
                            try:
                                img = img.convert()
                            except pygame.error:
                                pass  # Use original if conversion fails
                        frames.append((img, 0))
                break

        self.frames = frames

    def use(self, now: float, owner) -> bool:
        if not super().use(now, owner):
            return False

        # Get shooting direction from owner
        dir_x = getattr(owner, "shoot_direction", {}).get("x", 0)
        dir_y = getattr(owner, "shoot_direction", {}).get("y", 0)

        # If no direction input, use facing direction
        if dir_x == 0 and dir_y == 0:
            dir_x = 1 if getattr(owner, "facing_right", True) else -1
            dir_y = 0

        # Normalize direction vector
        length = (dir_x * dir_x + dir_y * dir_y) ** 0.5
        if length > 0:
            dir_x = dir_x / length
            dir_y = dir_y / length

        # Calculate velocities
        vx = dir_x * self.speed
        vy = dir_y * self.speed

        # Spawn projectile from center of owner
        ox = owner.rect.centerx
        oy = owner.rect.centery

        # Adjust spawn position based on direction
        spawn_offset = owner.rect.width // 2 + 8
        spawn_x = ox + dir_x * spawn_offset
        spawn_y = oy + dir_y * spawn_offset

        proj = Projectile(
            spawn_x,
            spawn_y,
            vx,
            vy,
            self.frames,
            lifetime=self.lifetime,
            damage=self.damage,
            owner=owner,
            scale=self.scale,
        )
        self.projectiles.append(proj)
        self.active = True
        self.last_used = now
        return True

    def update(self, dt: float, owner) -> None:
        alive = []
        for p in self.projectiles:
            if p.update(dt):
                alive.append(p)
        self.projectiles = alive
        # keep active flag while any projectile exists
        if not self.projectiles:
            self.active = False

    def draw(self, surface, camera_x=0, camera_y=0):
        for p in self.projectiles:
            p.draw(surface, camera_x, camera_y)

    def handle_collisions(self, enemies: list):
        # Check projectiles against enemies; apply damage and remove projectile on hit
        alive = []
        for p in self.projectiles:
            hit = False
            for e in enemies:
                try:
                    if e.rect.colliderect(p.rect):
                        # apply damage
                        if hasattr(e, "take_damage"):
                            e.take_damage(p.damage)
                        hit = True
                        break
                except Exception:
                    continue
            if not hit:
                alive.append(p)
        self.projectiles = alive


registry.register_skill("blast", ProjectileSkill)


class ChargeSkill(SkillBase):
    """Chargeable shot: hold to increase damage and speed, release to fire.

    Usage:
      - begin(now, owner) -> start charging (checks cooldown)
      - release(now, owner, held_time) -> fire projectile with power based on held_time
    """

    def __init__(
        self,
        frames_path=None,
        base_speed=1200,
        base_damage=30,
        max_charge=3.0,
        lifetime=1.5,
        cooldown=0.2,
        **kwargs,
    ):
        super().__init__(cooldown=cooldown)
        # ChargeSkill visuals default to very large (20x). Can be overridden in metadata via 'scale'.
        self.scale = float(kwargs.get("scale", 20.0))
        # If no explicit frames_path provided, prefer the purple_skill subfolder
        if not frames_path:
            frames_path = os.path.join(
                _REPO_ROOT, "assets", "skill-effect", "purple_skill"
            )

    def __init__(
        self,
        frames_path=None,
        base_speed=1200,
        base_damage=30,
        max_charge=3.0,
        lifetime=1.5,
        cooldown=0.2,
        **kwargs,
    ):
        super().__init__(cooldown=cooldown)
        # ChargeSkill visuals default to very large (20x). Can be overridden in metadata via 'scale'.
        self.scale = float(kwargs.get("scale", 20.0))
        # If no explicit frames_path provided, prefer the purple_skill subfolder
        if not frames_path:
            frames_path = os.path.join(
                _REPO_ROOT, "assets", "skill-effect", "purple_skill"
            )

        self.frames_path = frames_path
        self.base_speed = base_speed
        self.base_damage = base_damage
        self.max_charge = float(max_charge)
        self.lifetime = lifetime
        self.projectiles = []
        self.charging = False
        self.charge_start = 0.0

        # load frames from candidates: explicit frames_path, repo-relative, default assets/skill-effect
        frames = []
        candidates = []
        if frames_path:
            candidates.append(frames_path)
            candidates.append(os.path.join(_REPO_ROOT, frames_path))
        # Prefer the purple_skill folder (contains PNG frames). Also try the generic skill-effect folder.

        candidates.append(
            os.path.join(_REPO_ROOT, "assets", "skill-effect", "purple_skill")
        )
        candidates.append(os.path.join(_REPO_ROOT, "assets", "skill-effect"))

        for cand in candidates:
            cand = os.path.normpath(cand)
            if os.path.isdir(cand):
                for fn in sorted(os.listdir(cand)):
                    if fn.lower().endswith(".png"):
                        try:
                            img = pygame.image.load(
                                os.path.join(cand, fn)
                            ).convert_alpha()

                        except Exception:
                            continue
                        frames.append((img, 0))
                break

        self.frames = frames

    def begin(self, now: float, owner) -> bool:
        if not self.can_use(now):
            return False
        self.charging = True
        self.charge_start = now
        return True

    def release(self, now: float, owner, held_time: float) -> bool:
        # clamp charge
        charge = max(0.0, min(self.max_charge, float(held_time)))
        mult = 1.0 + 2.0 * (charge / self.max_charge)  # 1.0 -> 3.0
        speed = float(self.base_speed) * mult
        damage = int(self.base_damage * mult)

        # Get shooting direction from owner
        dir_x = getattr(owner, "shoot_direction", {}).get("x", 0)
        dir_y = getattr(owner, "shoot_direction", {}).get("y", 0)

        # If no direction input, use facing direction
        if dir_x == 0 and dir_y == 0:
            dir_x = 1 if getattr(owner, "facing_right", True) else -1
            dir_y = 0

        # Normalize direction vector
        length = (dir_x * dir_x + dir_y * dir_y) ** 0.5
        if length > 0:
            dir_x = dir_x / length
            dir_y = dir_y / length

        # Calculate velocities
        vx = dir_x * speed
        vy = dir_y * speed

        # Spawn projectile from center of owner
        ox = owner.rect.centerx
        oy = owner.rect.centery

        # Adjust spawn position based on direction
        spawn_offset = owner.rect.width // 2 + 8
        spawn_x = ox + dir_x * spawn_offset
        spawn_y = oy + dir_y * spawn_offset

        proj = Projectile(
            spawn_x,
            spawn_y,
            vx,
            vy,
            self.frames,
            lifetime=self.lifetime,
            damage=damage,
            owner=owner,
            scale=self.scale,
        )

        self.projectiles.append(proj)
        self.active = True
        self.last_used = now
        self.charging = False
        return True

    def update(self, dt: float, owner) -> None:
        alive = []
        for p in self.projectiles:
            if p.update(dt):
                alive.append(p)
        self.projectiles = alive
        if not self.projectiles:
            self.active = False

    def draw(self, surface, camera_x=0, camera_y=0):
        for p in self.projectiles:
            p.draw(surface, camera_x, camera_y)

    def handle_collisions(self, enemies: list):
        # Piercing behavior: charged projectiles should pass through enemies.
        # Apply damage once per enemy per projectile by tracking hit targets
        for p in list(self.projectiles):
            for e in enemies:
                try:
                    if e.rect.colliderect(p.rect):
                        eid = id(e)
                        if eid in getattr(p, "hit_targets", set()):
                            # already damaged this enemy with this projectile
                            continue
                        if hasattr(e, "take_damage"):

                            e.take_damage(p.damage)
                        # record that this projectile has hit this enemy
                        try:
                            p.hit_targets.add(eid)
                        except Exception:
                            p.hit_targets = getattr(p, "hit_targets", set())

                            p.hit_targets.add(eid)
                except Exception:
                    continue


registry.register_skill("charge", ChargeSkill)


class CloudSkill(SkillBase):
    """Skill that allows player to hover in the air briefly."""

    def __init__(self, duration=1.0, cooldown=2.0, **kwargs):
        super().__init__(cooldown=cooldown)
        self.duration = duration
        self.hover_time = 0
        self.hovering = False
        self.frozen_pos = None  # Store position when skill activates
        # Load cloud effect
        try:
            cloud_path = os.path.join(_REPO_ROOT, "assets", "icon_skills", "cloud.png")
            self.cloud_image = pygame.image.load(cloud_path).convert_alpha()
            # Will scale the cloud image when owner is set
            self.cloud_image_original = self.cloud_image
        except Exception as e:
            print(f"Error loading cloud image: {e}")
            self.cloud_image = None
            self.cloud_image_original = None

    def set_owner(self, owner):
        """Update cloud size based on owner's dimensions"""
        self.owner = owner
        if self.cloud_image_original is not None and owner is not None:
            # Make cloud much larger - about 2x player width and 0.75x player height
            cloud_width = owner.rect.width * 2.0
            cloud_height = owner.rect.height * 0.75
            self.cloud_image = pygame.transform.scale(
                self.cloud_image_original, (int(cloud_width), int(cloud_height))
            )

    def can_use(self, now: float) -> bool:
        # Only allow use while in air and after dash
        if not super().can_use(now):
            return False
        return True

    def use(self, now: float, owner) -> bool:
        if not super().use(now, owner):
            return False

        # Store current position and start hovering
        self.frozen_pos = (owner.rect.x, owner.rect.y)
        self.hovering = True
        self.hover_time = self.duration
        # Reset all velocities
        owner.vel_x = 0
        owner.vel_y = 0
        self.active = True

        # Make sure we have the right cloud size
        if not hasattr(self, "owner"):
            self.set_owner(owner)
        return True

    def update(self, dt: float, owner) -> None:
        if not self.hovering:
            return

        self.hover_time -= dt
        if self.hover_time <= 0:
            self.hovering = False
            self.active = False
            self.frozen_pos = None
            return

        # Keep player completely still
        if self.frozen_pos is not None:
            owner.rect.x = self.frozen_pos[0]
            owner.rect.y = self.frozen_pos[1]
            owner.vel_x = 0
            owner.vel_y = 0

    def draw(self, surface, camera_x=0, camera_y=0):
        # Draw cloud effect under the player if hovering
        if self.hovering and hasattr(self, "owner") and self.cloud_image is not None:
            px = self.owner.rect.centerx - camera_x - self.cloud_image.get_width() // 2
            py = self.owner.rect.bottom - camera_y - 5  # Position closer to player
            surface.blit(self.cloud_image, (px, py))


registry.register_skill("cloud", CloudSkill)

registry.register_skill("charge", ChargeSkill)


class SlowSkill(SkillBase):
    """Slow projectile: gây hiệu ứng làm chậm player thay vì damage cao

    Khi projectile chạm player:
    - Gây ít damage (symbolic)
    - Áp dụng slow effect (giảm tốc độ di chuyển)
    - Duration dựa trên charge level
    """

    def __init__(
        self,
        frames_path=None,
        base_speed=400,
        base_damage=3,
        slow_percent=50,
        base_slow_duration=2.0,
        max_charge=2.0,
        lifetime=1.8,
        cooldown=3.5,
        **kwargs,
    ):
        super().__init__(cooldown=cooldown)
        self.scale = float(kwargs.get("scale", 2.5))

        # If no explicit frames_path provided, use purple_skill
        if not frames_path:
            frames_path = os.path.join(
                _REPO_ROOT, "assets", "skill-effect", "purple_skill"
            )
        self.frames_path = frames_path

        self.base_speed = base_speed
        self.base_damage = base_damage  # Damage rất thấp
        self.slow_percent = slow_percent  # Giảm bao nhiêu % tốc độ (50 = giảm 50%)
        self.base_slow_duration = base_slow_duration  # Slow kéo dài bao lâu
        self.max_charge = float(max_charge)
        self.lifetime = lifetime
        self.projectiles = []
        self.charging = False
        self.charge_start = 0.0

        # Load frames
        frames = []
        candidates = []
        if frames_path:
            candidates.append(frames_path)
            candidates.append(os.path.join(_REPO_ROOT, frames_path))
        candidates.append(
            os.path.join(_REPO_ROOT, "assets", "skill-effect", "purple_skill")
        )

        for cand in candidates:
            cand = os.path.normpath(cand)
            if os.path.isdir(cand):
                for fn in sorted(os.listdir(cand)):
                    if fn.lower().endswith(".png"):
                        try:
                            img = pygame.image.load(
                                os.path.join(cand, fn)
                            ).convert_alpha()
                        except Exception:
                            continue
                        frames.append((img, 0))
                break

        self.frames = frames

    def begin(self, now: float, owner) -> bool:
        if not self.can_use(now):
            return False
        self.charging = True
        self.charge_start = now
        return True

    def release(self, now: float, owner, held_time: float) -> bool:
        # clamp charge
        charge = max(0.0, min(self.max_charge, float(held_time)))
        mult = 1.0 + 1.0 * (
            charge / self.max_charge
        )  # 1.0 -> 2.0 (ít hơn charge skill)
        speed = float(self.base_speed) * mult
        damage = int(self.base_damage)  # Damage không tăng theo charge
        slow_duration = self.base_slow_duration * mult  # Duration tăng theo charge

        dir_x = 1 if getattr(owner, "facing_right", True) else -1
        vx = dir_x * speed
        vy = 0
        ox = owner.rect.centerx
        oy = owner.rect.centery
        spawn_x = ox + dir_x * (owner.rect.width // 2 + 8)
        spawn_y = oy

        # Tạo projectile với metadata về slow effect
        proj = Projectile(
            spawn_x,
            spawn_y,
            vx,
            vy,
            self.frames,
            lifetime=self.lifetime,
            damage=damage,
            owner=owner,
            scale=self.scale,
        )
        # Thêm thông tin slow vào projectile
        proj.slow_percent = self.slow_percent
        proj.slow_duration = slow_duration
        proj.is_slow_projectile = True

        self.projectiles.append(proj)
        self.active = True
        self.last_used = now
        self.charging = False
        return True

    def update(self, dt: float, owner) -> None:
        alive = []
        for p in self.projectiles:
            if p.update(dt):
                alive.append(p)
        self.projectiles = alive
        if not self.projectiles:
            self.active = False

    def draw(self, surface, camera_x=0, camera_y=0):
        for p in self.projectiles:
            p.draw(surface, camera_x, camera_y)


class FireSkill(SkillBase):
    """Fire skill that shoots fire projectiles."""

    def __init__(
        self,
        cooldown=1.0,
        damage=40,
        speed=1200,  # Increased speed for faster projectiles
        lifetime=2.0,
        frames_path="assets/skill-effect/fire",
        **kwargs,
    ):
        super().__init__(cooldown=cooldown, **kwargs)
        self.damage = damage
        self.speed = speed
        self.lifetime = lifetime
        self.frames_path = frames_path
        self.projectiles = []  # Store active fire projectiles
        self.frames = []  # Frames for projectiles

        # Load fire effect frames
        self.load_fire_frames()

    def load_fire_frames(self):
        """Load fire effect animation frames for projectiles."""
        try:
            import pygame
            import os

            base_path = self.frames_path
            if os.path.exists(base_path):
                # Get all png files and sort them
                files = [f for f in os.listdir(base_path) if f.endswith(".png")]
                files.sort()

                for file in files:
                    file_path = os.path.join(base_path, file)
                    try:
                        frame = pygame.image.load(file_path).convert_alpha()
                        # Scale fire effect - larger size
                        scaled_frame = pygame.transform.scale(
                            frame,
                            (
                                int(frame.get_width() * 1.2),
                                int(frame.get_height() * 1.2),
                            ),
                        )
                        # Store as (frame, bottom_trim) tuple like other skills
                        self.frames.append((scaled_frame, 0))
                    except Exception as e:
                        print(f"Error loading fire frame {file}: {e}")

                print(f"Loaded {len(self.frames)} fire projectile frames")
            else:
                print(f"Fire effect path not found: {base_path}")
        except Exception as e:
            print(f"Error loading fire effect frames: {e}")

    def use(self, now: float, owner) -> bool:
        print(
            f"FireSkill.use() - now: {now}, last_used: {self.last_used}, cooldown: {self.cooldown}"
        )
        print(
            f"Can use: {self.can_use(now)}, time since last use: {now - self.last_used}"
        )
        if not super().use(now, owner):
            print("FireSkill cooldown not ready!")
            return False
        print(f"FireSkill cooldown passed! Proceeding with projectile creation...")

        # Get shooting direction from owner
        dir_x = getattr(owner, "shoot_direction", {}).get("x", 0)
        dir_y = getattr(owner, "shoot_direction", {}).get("y", 0)

        # If no direction input, use facing direction
        if dir_x == 0 and dir_y == 0:
            dir_x = 1 if getattr(owner, "facing_right", True) else -1
            dir_y = 0

        # Normalize direction vector
        length = (dir_x * dir_x + dir_y * dir_y) ** 0.5
        if length > 0:
            dir_x = dir_x / length
            dir_y = dir_y / length

        # Calculate velocities
        vx = dir_x * self.speed
        vy = dir_y * self.speed

        # Spawn projectile from center of owner
        ox = owner.rect.centerx
        oy = owner.rect.centery

        # Adjust spawn position based on direction
        spawn_offset = owner.rect.width // 2 + 8
        spawn_x = ox + dir_x * spawn_offset
        spawn_y = oy + dir_y * spawn_offset

        # Create fire projectile
        print(
            f"Creating fire projectile at ({spawn_x}, {spawn_y}) with speed ({vx}, {vy})"
        )  # Debug
        if self.frames:
            proj = Projectile(
                spawn_x,
                spawn_y,
                vx,
                vy,
                self.frames,
                lifetime=self.lifetime,
                damage=self.damage,
                owner=owner,
                scale=1.5,  # Larger projectile scale
            )
            self.projectiles.append(proj)
            print(
                f"Fire projectile created! Total projectiles: {len(self.projectiles)}"
            )  # Debug
        else:
            print("No frames loaded for fire skill!")  # Debug

        # Play sound if available
        if hasattr(owner, "sound_manager") and owner.sound_manager:
            try:
                owner.sound_manager.play_sound("fire")
            except:
                pass

        return True

    def update(self, dt: float, owner) -> None:
        # Update all fire projectiles
        projectiles_to_remove = []

        for i, proj in enumerate(self.projectiles):
            proj.update(dt)

            # Remove expired projectiles or projectiles that moved off screen
            if (
                proj.lifetime <= 0
                or proj.x < -100
                or proj.x > 4000
                or proj.y < -100
                or proj.y > 1000
            ):
                projectiles_to_remove.append(i)

        # Remove expired projectiles (reverse order to maintain indices)
        for i in reversed(projectiles_to_remove):
            self.projectiles.pop(i)

        # Debug: print number of active projectiles
        if len(self.projectiles) > 0:
            print(f"Active fire projectiles: {len(self.projectiles)}")

    def draw(self, screen, camera_x, camera_y):
        """Draw active fire projectiles."""
        for proj in self.projectiles:
            proj.draw(screen, camera_x, camera_y)


registry.register_skill("slow", SlowSkill)
registry.register_skill("fire", FireSkill)


class FireExplosionSkill(SkillBase):
    """Fire Explosion skill - creates a large fire explosion around the player."""

    def __init__(
        self,
        cooldown=5.0,
        damage=80,
        explosion_radius=200,
        duration=1.0,
        frames_path="assets/skill-effect/fire_ult",
        **kwargs,
    ):
        super().__init__(cooldown=cooldown, **kwargs)
        self.damage = damage
        self.explosion_radius = explosion_radius
        self.duration = duration
        self.frames_path = frames_path
        self.explosion_active = False
        self.explosion_timer = 0.0
        self.explosion_center = (0, 0)
        self.explosion_scale = 1.0
        self.max_scale = 8.0  # Maximum explosion size
        self.frames = []

        # Animation tracking for frames
        self.current_frame = 0
        self.frame_timer = 0.0
        self.frame_duration = 0.1  # Time per frame (0.1s = 10 FPS)

        # Load fire effect frames
        self.load_fire_frames()

    def load_fire_frames(self):
        """Load fire effect animation frames for explosion."""
        try:
            import pygame
            import os

            base_path = self.frames_path
            if os.path.exists(base_path):
                files = [f for f in os.listdir(base_path) if f.endswith(".png")]
                files.sort()

                for file in files:
                    file_path = os.path.join(base_path, file)
                    try:
                        frame = pygame.image.load(file_path).convert_alpha()
                        self.frames.append(frame)
                    except Exception as e:
                        print(f"Error loading explosion frame {file}: {e}")

                if self.frames:
                    print(f"Loaded {len(self.frames)} explosion frames")
            else:
                print(f"Fire explosion path not found: {base_path}")
        except Exception as e:
            print(f"Error loading fire explosion frames: {e}")

    def use(self, now: float, owner) -> bool:
        if not super().use(now, owner):
            return False

        # Start explosion at player's center
        self.explosion_center = (owner.rect.centerx, owner.rect.centery)
        self.explosion_active = True
        self.explosion_timer = 0.0
        self.explosion_scale = 1.0

        # Reset frame animation
        self.current_frame = 0
        self.frame_timer = 0.0

        # Play sound if available
        if hasattr(owner, "sound_manager") and owner.sound_manager:
            try:
                owner.sound_manager.play_sound("explosion")
            except:
                pass

        return True

    def update(self, dt: float, owner) -> None:
        if not self.explosion_active:
            return

        self.explosion_timer += dt

        # Update frame animation
        if self.frames:
            self.frame_timer += dt
            if self.frame_timer >= self.frame_duration:
                self.current_frame = (self.current_frame + 1) % len(self.frames)
                self.frame_timer = 0.0

        # Scale explosion over time
        progress = self.explosion_timer / self.duration
        if progress <= 1.0:
            # Explosion grows quickly then fades
            if progress <= 0.3:
                # Growing phase
                self.explosion_scale = 1.0 + (self.max_scale - 1.0) * (progress / 0.3)
            else:
                # Fading phase
                fade_progress = (progress - 0.3) / 0.7
                self.explosion_scale = self.max_scale * (1.0 - fade_progress * 0.5)
        else:
            # Explosion finished
            self.explosion_active = False
            self.active = False

    def draw(self, surface, camera_x=0, camera_y=0):
        """Draw explosion effect."""
        if not self.explosion_active or not self.frames:
            return

        # Use current frame as explosion sprite
        base_frame = self.frames[self.current_frame]

        # Scale the explosion
        scaled_size = int(base_frame.get_width() * self.explosion_scale)
        if scaled_size > 0:
            try:
                scaled_frame = pygame.transform.scale(
                    base_frame, (scaled_size, scaled_size)
                )

                # Draw at explosion center
                draw_x = self.explosion_center[0] - scaled_size // 2 - camera_x
                draw_y = self.explosion_center[1] - scaled_size // 2 - camera_y

                # Add transparency effect during fade
                progress = self.explosion_timer / self.duration
                if progress > 0.3:
                    alpha = int(255 * (1.0 - (progress - 0.3) / 0.7))
                    scaled_frame.set_alpha(alpha)

                surface.blit(scaled_frame, (draw_x, draw_y))
            except Exception as e:
                # Fallback: draw a circle
                pygame.draw.circle(
                    surface,
                    (255, 100, 0),
                    (
                        int(self.explosion_center[0] - camera_x),
                        int(self.explosion_center[1] - camera_y),
                    ),
                    int(self.explosion_radius * self.explosion_scale / self.max_scale),
                    5,
                )

    def handle_collisions(self, enemies: list):
        """Check explosion damage against enemies."""
        if not self.explosion_active:
            return

        explosion_rect = pygame.Rect(
            self.explosion_center[0] - self.explosion_radius,
            self.explosion_center[1] - self.explosion_radius,
            self.explosion_radius * 2,
            self.explosion_radius * 2,
        )

        for enemy in enemies:
            try:
                if enemy.rect.colliderect(explosion_rect):
                    # Calculate distance for damage falloff
                    enemy_center = enemy.rect.center
                    dx = enemy_center[0] - self.explosion_center[0]
                    dy = enemy_center[1] - self.explosion_center[1]
                    distance = (dx * dx + dy * dy) ** 0.5

                    if distance <= self.explosion_radius:
                        # Damage decreases with distance
                        damage_multiplier = max(
                            0.3, 1.0 - distance / self.explosion_radius
                        )
                        final_damage = int(self.damage * damage_multiplier)

                        if hasattr(enemy, "take_damage"):
                            enemy.take_damage(final_damage)
            except Exception as e:
                print(f"Error in explosion collision: {e}")


registry.register_skill("fire_explosion", FireExplosionSkill)

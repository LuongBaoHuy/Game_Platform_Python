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
        self.cooldown = params.get('cooldown', 0.0)
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
    def __init__(self, cooldown=1.0, duration=0.18, speed_multiplier=3.0, **kwargs):
        super().__init__(cooldown=cooldown, duration=duration, speed_multiplier=speed_multiplier, **kwargs)
        self.duration = duration
        self.speed_multiplier = speed_multiplier
        self.time_left = 0.0

    def use(self, now: float, owner) -> bool:
        if not super().use(now, owner):
            return False
        self.time_left = self.duration
        # Apply a burst of horizontal speed. Caller should set vel_x before use.
        if owner.vel_x != 0:
            owner.vel_x = owner.vel_x * self.speed_multiplier
        else:
            # If owner was stationary, apply a dash in facing direction
            owner.vel_x = SPEED * self.speed_multiplier if getattr(owner, 'facing_right', True) else -SPEED * self.speed_multiplier
        # Set owner state to dash so animation plays
        try:
            owner.state = 'dash'
            owner.current_frame = 0
        except Exception:
            pass
        return True

    def update(self, dt: float, owner) -> None:
        if not self.active:
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self.active = False
            # stop extra velocity; concrete owner logic should restore input-based velocity
            owner.vel_x = 0
            # restore state (basic heuristic)
            try:
                if not getattr(owner, 'on_ground', True):
                    owner.state = 'jump'
                elif getattr(owner, 'vel_x', 0) != 0:
                    owner.state = 'walk'
                else:
                    owner.state = 'idle'
                owner.current_frame = 0
            except Exception:
                pass


# Register built-in skills
registry.register_skill('dash', DashSkill)

import os
import pygame

# Helper to find project root for default asset locations
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))


class Projectile:
    def __init__(self, x, y, vx, vy, frames, lifetime=1.5, damage=25, owner=None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.frames = frames or []
        self.current = 0
        self.timer = 0.0
        self.frame_time = 0.06
        self.lifetime = lifetime
        self.age = 0.0
        # compute bounding rect from first frame if available
        if self.frames:
            surf, _ = self.frames[0]
            self.rect = surf.get_rect(center=(int(self.x), int(self.y)))
        else:
            self.rect = pygame.Rect(int(self.x), int(self.y), 8, 8)
        self.damage = damage
        self.owner = owner

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
            pygame.draw.circle(surface, (128, 0, 255), (int(self.x - camera_x), int(self.y - camera_y)), 6)
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
    def __init__(self, frames_path=None, speed=800, lifetime=1.2, cooldown=0.5, damage=25, **kwargs):
        super().__init__(cooldown=cooldown)

        # Cho phép tùy chỉnh scale từ metadata (mặc định 1.0)
        self.scale = float(kwargs.get('scale', 1.0))
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
        candidates.append(os.path.join(_REPO_ROOT, 'assets', 'skill-effect', 'purple_skill'))

        for cand in candidates:
            cand = os.path.normpath(cand)
            if os.path.isdir(cand):
                for fn in sorted(os.listdir(cand)):
                    if fn.lower().endswith('.png'):
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
        # spawn projectile in front of owner
        ox = owner.rect.centerx
        oy = owner.rect.centery
        dir_x = 1 if getattr(owner, 'facing_right', True) else -1
        vx = dir_x * self.speed
        vy = 0
        # spawn a bit in front
        spawn_x = ox + dir_x * (owner.rect.width // 2 + 8)
        spawn_y = oy
        proj = Projectile(spawn_x, spawn_y, vx, vy, self.frames, lifetime=self.lifetime, damage=self.damage, owner=owner)
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
                        if hasattr(e, 'take_damage'):
                            e.take_damage(p.damage)
                        hit = True
                        break
                except Exception:
                    continue
            if not hit:
                alive.append(p)
        self.projectiles = alive


registry.register_skill('blast', ProjectileSkill)


class ChargeSkill(SkillBase):
    """Chargeable shot: hold to increase damage and speed, release to fire.

    Usage:
      - begin(now, owner) -> start charging (checks cooldown)
      - release(now, owner, held_time) -> fire projectile with power based on held_time
    """

    def __init__(self, frames_path=None, base_speed=1200, base_damage=30, max_charge=3.0, lifetime=1.5, cooldown=0.2, **kwargs):
        super().__init__(cooldown=cooldown)
        # ChargeSkill visuals default to very large (20x). Can be overridden in metadata via 'scale'.
        self.scale = float(kwargs.get('scale', 20.0))
        # If no explicit frames_path provided, prefer the purple_skill subfolder
        if not frames_path:
            frames_path = os.path.join(_REPO_ROOT, 'assets', 'skill-effect', 'purple_skill')
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
        candidates.append(os.path.join(_REPO_ROOT, 'assets', 'skill-effect', 'purple_skill'))
        candidates.append(os.path.join(_REPO_ROOT, 'assets', 'skill-effect'))

        for cand in candidates:
            cand = os.path.normpath(cand)
            if os.path.isdir(cand):
                for fn in sorted(os.listdir(cand)):
                    if fn.lower().endswith('.png'):
                        try:
                            img = pygame.image.load(os.path.join(cand, fn)).convert_alpha()
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

        dir_x = 1 if getattr(owner, 'facing_right', True) else -1
        vx = dir_x * speed
        vy = 0
        ox = owner.rect.centerx
        oy = owner.rect.centery
        spawn_x = ox + dir_x * (owner.rect.width // 2 + 8)
        spawn_y = oy
        proj = Projectile(spawn_x, spawn_y, vx, vy, self.frames, lifetime=self.lifetime, damage=damage, owner=owner, scale=self.scale)
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
                        if eid in getattr(p, 'hit_targets', set()):
                            # already damaged this enemy with this projectile
                            continue
                        if hasattr(e, 'take_damage'):
                            e.take_damage(p.damage)
                        # record that this projectile has hit this enemy
                        try:
                            p.hit_targets.add(eid)
                        except Exception:
                            p.hit_targets = getattr(p, 'hit_targets', set())
                            p.hit_targets.add(eid)
                except Exception:
                    continue


registry.register_skill('charge', ChargeSkill)


class SlowSkill(SkillBase):
    """Slow projectile: gây hiệu ứng làm chậm player thay vì damage cao
    
    Khi projectile chạm player:
    - Gây ít damage (symbolic)
    - Áp dụng slow effect (giảm tốc độ di chuyển)
    - Duration dựa trên charge level
    """
    
    def __init__(self, frames_path=None, base_speed=400, base_damage=3, slow_percent=50, 
                 base_slow_duration=2.0, max_charge=2.0, lifetime=1.8, cooldown=3.5, **kwargs):
        super().__init__(cooldown=cooldown)
        self.scale = float(kwargs.get('scale', 2.5))
        
        # If no explicit frames_path provided, use purple_skill
        if not frames_path:
            frames_path = os.path.join(_REPO_ROOT, 'assets', 'skill-effect', 'purple_skill')
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
        candidates.append(os.path.join(_REPO_ROOT, 'assets', 'skill-effect', 'purple_skill'))
        
        for cand in candidates:
            cand = os.path.normpath(cand)
            if os.path.isdir(cand):
                for fn in sorted(os.listdir(cand)):
                    if fn.lower().endswith('.png'):
                        try:
                            img = pygame.image.load(os.path.join(cand, fn)).convert_alpha()
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
        mult = 1.0 + 1.0 * (charge / self.max_charge)  # 1.0 -> 2.0 (ít hơn charge skill)
        speed = float(self.base_speed) * mult
        damage = int(self.base_damage)  # Damage không tăng theo charge
        slow_duration = self.base_slow_duration * mult  # Duration tăng theo charge
        
        dir_x = 1 if getattr(owner, 'facing_right', True) else -1
        vx = dir_x * speed
        vy = 0
        ox = owner.rect.centerx
        oy = owner.rect.centery
        spawn_x = ox + dir_x * (owner.rect.width // 2 + 8)
        spawn_y = oy
        
        # Tạo projectile với metadata về slow effect
        proj = Projectile(spawn_x, spawn_y, vx, vy, self.frames, 
                         lifetime=self.lifetime, damage=damage, owner=owner, scale=self.scale)
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


registry.register_skill('slow', SlowSkill)



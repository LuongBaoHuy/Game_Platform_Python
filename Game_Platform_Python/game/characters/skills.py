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
            # Debug: report whether dash frames are available
            dash_frames = owner.animations.get('dash', []) if hasattr(owner, 'animations') else []
            print(f"DashSkill.use: activated for owner; dash frames={len(dash_frames)}")
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
            print("DashSkill.update: dash ended for owner")


# Register built-in skills
registry.register_skill('dash', DashSkill)


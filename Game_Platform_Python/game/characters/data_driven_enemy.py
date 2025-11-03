# game/characters/data_driven_enemy.py
import pygame
from game.config import PLAYER_SCALE, GRAVITY


class DataDrivenEnemy:
    """Enemy generic: visual loaded by char_id via factory; behavior is simple patrol/chase.

    Implementation notes:
    - Import the characters.factory.create_player lazily inside __init__ to avoid
      import-time circular dependencies that previously caused registration to fail.
    - If loading visuals fails, fall back to empty animations so the enemy can still be used.
    """

    def __init__(self, x, y, char_id="bluewizard", patrol_range=200, speed=80):
        # Initialize sound manager
        try:
            from game.sound_manager import SoundManager

            self.sound_manager = SoundManager()
        except Exception as e:
            print(f"Error initializing enemy sound manager: {e}")
            self.sound_manager = None

        # Lazy import to avoid circular import problems during module import
        try:
            from game.characters.factory import create_player as create_visual
        except Exception:
            create_visual = None

        visual = None
        if create_visual:
            try:
                visual = create_visual(char_id, x, y)
            except Exception:
                pass

        # copy animations (factory returns Character-like with .animations)
        self.animations = getattr(visual, 'animations', {}) or {}
        # Copy skills from visual (loaded by factory from metadata)
        self.skills = getattr(visual, 'skills', {}) or {}
        # ensure frames are tuples (surface, trim). factory.load_frames returns (surface, 0) if implemented that way
        # We'll accept either (surface) or (surface, trim)
        # Hitbox: create a rect similar to Character default or reuse visual.rect
        self.rect = getattr(
            visual, "rect", pygame.Rect(x, y, int(120 * 1.0), int(240 * 1.0))
        ).copy()
        self.rect.midbottom = (x, y)
        self.state = "idle"
        self.current_frame = 0
        self.anim_timer = 0.0
        self.anim_speed = 0.11
        self.attack_anim_speed = 0.11  # Animation tấn công nhanh
        self.hurt_anim_speed = 0.08  # Animation bị đánh
        self.dying_anim_speed = 0.05  # Animation chết
        self.patrol_min = x - patrol_range
        self.patrol_max = x + patrol_range
        self.speed = speed
        self.direction = -1
        # physics
        self.vel_y = 0
        self.on_ground = False
        # attack / damage
        self.detection_range = 400
        self.attack_range = 120
        self.attack_damage = getattr(visual, "attack_damage", 10)
        self.attack_cooldown = (
            1.5  # Cooldown giữa các lần mất máu (tăng = mất máu chậm hơn)
        )
        self._attack_cooldown_timer = 0.0
        self._attack_hit_frame = False  # Đánh dấu đã gây damage trong đợt attack này
        self.max_hp = getattr(visual, "max_hp", 100)  # Tăng HP lên 100
        self.hp = self.max_hp
        self.dead = False
        self.dying = False  # Đang trong trạng thái chết
        self.hurt_timer = 0.0  # Timer cho hurt animation
        self.facing_right = True

    def update(self, dt, platforms, player):
        # Nếu đã chết hoàn toàn, không làm gì
        if self.dead:
            return

        # Tính khoảng cách đến player (dùng cho AI logic)
        dx = player.rect.centerx - self.rect.centerx
        dy = abs(player.rect.centery - self.rect.centery)
        detection = 400

        # Nếu đang bị hurt, chỉ chạy hurt animation rồi quay lại normal
        if self.hurt_timer > 0.0:
            self.state = "hurt"
            self.hurt_timer -= dt
            if self.hurt_timer <= 0.0:
                self.state = "idle"  # Quay lại idle sau hurt

        # gravity
        self.vel_y += GRAVITY
        # apply vertical velocity (follow PatrolEnemy behavior: vel_y already in px/frame)
        self.rect.y += int(self.vel_y)
        # check collision with platforms (vertical)
        self.on_ground = False
        for _, platform_rect in platforms:
            if self.rect.colliderect(platform_rect):
                if self.vel_y > 0:
                    self.rect.bottom = platform_rect.top
                    self.vel_y = 0
                    self.on_ground = True

        # Chỉ thực hiện AI khi không bị hurt và không dying
        if self.hurt_timer <= 0.0 and not self.dying:
            if abs(dx) < detection and dy < 140:
                if abs(dx) <= self.attack_range:
                    # enter attack state and apply damage with cooldown
                    old_state = self.state
                    self.state = "attack"
                    # reset animation when entering attack state
                    if old_state != "attack":
                        self.current_frame = 0
                        self.anim_timer = 0.0
                        self._attack_hit_frame = (
                            False  # Reset flag khi bắt đầu attack mới
                        )

                    # Reset hit flag khi animation attack quay về đầu (frame 0 hoặc 1)
                    if self.current_frame <= 1:
                        self._attack_hit_frame = False

                    # Chỉ gây damage ở giữa animation (frame 3-5 của animation attack)
                    attack_frames = self.animations.get("attack") or []
                    hit_frame_start = len(attack_frames) // 3 if attack_frames else 2
                    hit_frame_end = (
                        (len(attack_frames) * 2) // 3 if attack_frames else 4
                    )

                    if hit_frame_start <= self.current_frame <= hit_frame_end:
                        if (
                            not self._attack_hit_frame
                            and self._attack_cooldown_timer <= 0.0
                        ):
                            try:
                                # Play attack sound first
                                if (
                                    hasattr(self, "sound_manager")
                                    and self.sound_manager is not None
                                ):
                                    self.sound_manager.play_sound("enemy_attack")

                                player.take_damage(self.attack_damage)
                                self._attack_hit_frame = (
                                    True  # Đánh dấu đã hit trong đợt này
                                )
                                self._attack_cooldown_timer = self.attack_cooldown
                            except Exception as e:
                                print(f"Error during enemy attack: {e}")

                    # Giảm cooldown
                    if self._attack_cooldown_timer > 0.0:
                        self._attack_cooldown_timer = max(
                            0.0, self._attack_cooldown_timer - dt
                        )
                else:
                    self.state = "walk"
                    dir_sign = 1 if dx > 0 else -1
                    # move horizontally using dt
                    self.rect.x += int(self.speed * dir_sign * dt)
                    self.direction = 1 if dir_sign > 0 else -1
            else:
                self.state = "walk"
                move = self.speed * self.direction * dt
                self.rect.x += int(move)
                if self.rect.centerx < self.patrol_min:
                    self.rect.centerx = int(self.patrol_min)
                    self.direction = 1
                elif self.rect.centerx > self.patrol_max:
                    self.rect.centerx = int(self.patrol_max)
                    self.direction = -1

        # animation update
        frames = self.animations.get(self.state) or []
        if frames:
            # Dùng tốc độ animation khác cho attack, hurt, dying
            if self.state == "attack":
                current_speed = self.attack_anim_speed
            elif self.state == "hurt":
                current_speed = self.hurt_anim_speed
            elif self.state == "dying":
                current_speed = self.dying_anim_speed
            else:
                current_speed = self.anim_speed

            self.anim_timer += dt
            if self.anim_timer >= current_speed:
                self.anim_timer = 0.0
                # Dying animation không loop, dừng ở frame cuối
                if self.state == "dying":
                    if self.current_frame < len(frames) - 1:
                        self.current_frame += 1
                    # Khi đến frame cuối, đánh dấu dead
                    if self.current_frame >= len(frames) - 1:
                        self.dead = True
                else:
                    # Các animation khác loop bình thường
                    self.current_frame = (self.current_frame + 1) % len(frames)

    def draw(self, surface, camera_x, camera_y, show_hitbox: bool = False):
        if self.dead:
            return
        frames = self.animations.get(self.state) or []
        if not frames:
            pygame.draw.rect(
                surface,
                (150, 50, 50),
                (
                    self.rect.x - camera_x,
                    self.rect.y - camera_y,
                    self.rect.width,
                    self.rect.height,
                ),
            )
            return
        # accept frames item either (surf) or (surf, trim)
        entry = frames[self.current_frame]
        if isinstance(entry, tuple) and len(entry) >= 1:
            frame = entry[0]
            trim = entry[1] if len(entry) > 1 else 0
        else:
            frame = entry
            trim = 0
        img = (
            frame if self.direction >= 0 else pygame.transform.flip(frame, True, False)
        )
        img_rect = img.get_rect(
            midbottom=(self.rect.centerx - camera_x, self.rect.bottom - camera_y + trim)
        )
        surface.blit(img, img_rect)
        if show_hitbox:
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

        # Vẽ thanh máu phía trên đầu quái (chỉ khi chưa chết)
        if not self.dying and not self.dead and self.hp < self.max_hp:
            # Thanh máu nằm trên đầu quái
            bar_width = 150
            bar_height = 20  # Độ cao thanh máu (giảm xuống để mỏng hơn)
            bar_x = self.rect.centerx - camera_x - bar_width // 2
            bar_y = (
                self.rect.top - camera_y - 180
            )  # Khoảng cách từ đỉnh đầu quái (tăng lên để xa hơn)

            # Background (thanh đen)
            pygame.draw.rect(
                surface,
                (0, 0, 0),
                (bar_x - 1, bar_y - 1, bar_width + 2, bar_height + 2),
            )

            # HP bar (thanh đỏ)
            hp_ratio = max(0, self.hp / self.max_hp)
            current_bar_width = int(bar_width * hp_ratio)

            # Màu thanh máu: xanh lá -> vàng -> đỏ
            if hp_ratio > 0.6:
                bar_color = (0, 255, 0)  # Xanh
            elif hp_ratio > 0.3:
                bar_color = (255, 255, 0)  # Vàng
            else:
                bar_color = (255, 0, 0)  # Đỏ

            if current_bar_width > 0:
                pygame.draw.rect(
                    surface, bar_color, (bar_x, bar_y, current_bar_width, bar_height)
                )

    def take_damage(self, amount):
        if self.dying or self.dead:
            return  # Đã chết rồi thì không nhận damage nữa

        try:
            self.hp -= int(amount)
        except Exception:
            self.hp -= amount

        if self.hp <= 0:
            self.hp = 0
            self.dying = True  # Bắt đầu dying animation
            self.state = "dying"
            self.current_frame = 0
            self.anim_timer = 0.0
            # Play death sound
            if hasattr(self, "sound_manager") and self.sound_manager is not None:
                try:
                    self.sound_manager.play_sound("enemy_death")
                except Exception as e:
                    print(f"Error playing enemy death sound: {e}")
        else:
            # Trigger hurt animation
            self.hurt_timer = 0.25  # Hurt animation kéo dài 0.25 giây
            self.state = "hurt"
            self.current_frame = 0
            self.anim_timer = 0.0

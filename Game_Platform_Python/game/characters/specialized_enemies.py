# game/characters/specialized_enemies.py
"""
Specialized enemy classes with unique AI behaviors:
- CasterEnemy: Ranged spellcaster with projectile attacks
- ControllerEnemy: Crowd control with status effects and area control
"""

import pygame
from typing import Optional
from game.characters.data_driven_enemy import DataDrivenEnemy
from game.characters.registry import get_skill


class CasterEnemy(DataDrivenEnemy):
    """
    Pháp sư - Enemy tấn công từ xa với projectile
    
    Đặc điểm:
    - Ưu tiên giữ khoảng cách với player
    - Bắn projectile khi player ở tầm xa
    - Lùi lại nếu player đến quá gần
    - Sử dụng animation "cast" khi bắn phép
    """
    
    def __init__(self, x, y, char_id='Wraith_01', patrol_range=150, speed=60):
        super().__init__(x, y, char_id=char_id, patrol_range=patrol_range, speed=speed)
        
        # Caster-specific stats
        self.max_hp = 80  # Ít máu hơn melee enemies
        self.hp = self.max_hp
        self.attack_damage = 15
        
        # Range behavior (TĂNG TẦM ĐÁNH)
        self.detection_range = 900    # Tầm phát hiện xa hơn (tăng từ 600)
        self.preferred_distance = 500  # Khoảng cách ưa thích (tăng từ 350)
        self.min_distance = 200       # Khoảng cách tối thiểu
        self.max_cast_range = 800     # Tầm bắn xa hơn (tăng từ 550)
        
        # Cast behavior
        self.cast_cooldown = 2.5      # Thời gian giữa các lần cast
        self.cast_timer = 0.0
        self.casting = False
        self.cast_duration = 1.2      # Thời gian cast spell (tăng để thấy animation)
        self.cast_progress = 0.0
        
        # Animation speeds (chậm hơn để dễ thấy)
        self.anim_speed = 0.08        # Default animation speed
        self.cast_anim_speed = 0.08   # Cast animation chậm hơn
        self.attack_anim_speed = 0.08 # Attack animation 
        self.hurt_anim_speed = 0.1    # Hurt animation
        
        # Movement behavior
        self.retreat_speed = 80       # Tốc độ lùi lại
        
    def update(self, dt, platforms, player):
        if self.dead:
            return  # Đã chết hoàn toàn, không cần update gì nữa
            
        if self.dying:
            # Đang dying - chỉ chạy physics và animation, không chạy AI
            self._update_physics(dt, platforms)
            self._update_animation(dt)
            return
            
        # Cập nhật timer
        self.cast_timer = max(0.0, self.cast_timer - dt)
        
        # Tính khoảng cách đến player
        dx = player.rect.centerx - self.rect.centerx
        dy = abs(player.rect.centery - self.rect.centery)
        distance = abs(dx)
        
        prev_state = self.state
        
        # AI Logic cho Caster
        if distance < self.detection_range and dy < 140:
            # Player trong tầm phát hiện
            
            if self.casting:
                # Đang cast spell - không di chuyển
                self.cast_progress += dt
                self.state = 'cast'  # Sử dụng cast animation
                
                if self.cast_progress >= self.cast_duration:
                    # Hoàn thành cast - bắn projectile
                    self._fire_projectile(player)
                    self.casting = False
                    self.cast_progress = 0.0
                    self.cast_timer = self.cast_cooldown
                    
            elif distance < self.min_distance:
                # Player quá gần - lùi lại
                self.state = 'walk'
                retreat_dir = -1 if dx > 0 else 1
                move_x = self.retreat_speed * retreat_dir * dt
                
                # Kiểm tra không lùi ra khỏi patrol area
                new_x = self.rect.centerx + move_x
                if self.patrol_min <= new_x <= self.patrol_max:
                    self.rect.x += int(move_x)
                    self.direction = retreat_dir
                    self.facing_right = retreat_dir > 0  # Cập nhật facing_right
                    
            elif distance <= self.max_cast_range and self.cast_timer <= 0.0:
                # Trong tầm bắn và có thể cast
                self.casting = True
                self.cast_progress = 0.0
                self.state = 'cast'
                # Quay mặt về phía player - cập nhật cả direction và facing_right
                self.direction = 1 if dx > 0 else -1
                self.facing_right = dx > 0  # Đảm bảo facing_right được set đúng
                
            elif distance > self.preferred_distance:
                # Player xa quá - tiến lại gần
                self.state = 'walk'
                advance_dir = 1 if dx > 0 else -1
                move_x = self.speed * advance_dir * dt
                
                new_x = self.rect.centerx + move_x
                if self.patrol_min <= new_x <= self.patrol_max:
                    self.rect.x += int(move_x)
                    self.direction = advance_dir
                    self.facing_right = advance_dir > 0  # Cập nhật facing_right
            else:
                # Ở khoảng cách tốt - đứng yên và chờ
                self.state = 'idle'
                self.direction = 1 if dx > 0 else -1
                self.facing_right = dx > 0  # Cập nhật facing_right
        else:
            # Player ngoài tầm - patrol bình thường
            self.state = 'walk'
            move = self.speed * self.direction * dt
            self.rect.x += int(move)
            
            if self.rect.centerx < self.patrol_min:
                self.rect.centerx = int(self.patrol_min)
                self.direction = 1
            elif self.rect.centerx > self.patrol_max:
                self.rect.centerx = int(self.patrol_max)
                self.direction = -1
        
        # Reset animation khi thay đổi state
        if prev_state != self.state:
            self.current_frame = 0
            self.anim_timer = 0.0
            
        # Update skills (projectiles)
        self.update_skills(dt, player)
            
        # Gọi parent update cho physics và animation
        # Nhưng skip AI logic của parent
        self._update_physics(dt, platforms)
        self._update_animation(dt)
    
    def _fire_projectile(self, player):
        """Bắn projectile về phía player sử dụng skill system"""
        try:
            # Đảm bảo facing_right được set đúng hướng về player ngay trước khi bắn
            dx = player.rect.centerx - self.rect.centerx
            self.facing_right = dx > 0
            self.direction = 1 if dx > 0 else -1
            
            blast_skill = self.skills.get('blast')
            if blast_skill and hasattr(blast_skill, 'use'):
                # Sử dụng current time (giả lập)
                import time
                current_time = time.time()
                blast_skill.use(current_time, self)
        except Exception as e:
            # Fallback: gây damage trực tiếp nếu projectile system không hoạt động
            distance = abs(player.rect.centerx - self.rect.centerx)
            if distance <= self.max_cast_range:
                try:
                    player.take_damage(self.attack_damage)
                except Exception:
                    pass
    
    def _update_physics(self, dt, platforms):
        """Physics update - gravity và collision"""
        self.vel_y += 2  # GRAVITY
        self.rect.y += int(self.vel_y)
        
        # Platform collision
        self.on_ground = False
        for _, platform_rect in platforms:
            if self.rect.colliderect(platform_rect):
                if self.vel_y > 0:
                    self.rect.bottom = platform_rect.top
                    self.vel_y = 0
                    self.on_ground = True
    
    def _update_animation(self, dt):
        """Animation update"""
        frames = self.animations.get(self.state) or []
        if frames:
            if self.state == 'cast':
                current_speed = self.cast_anim_speed
            elif self.state == 'attack':
                current_speed = self.attack_anim_speed  
            elif self.state == 'hurt':
                current_speed = self.hurt_anim_speed
            else:
                current_speed = self.anim_speed
                
            self.anim_timer += dt
            if self.anim_timer >= current_speed:
                self.anim_timer = 0.0
                if self.state == 'dying':
                    if self.current_frame < len(frames) - 1:
                        self.current_frame += 1
                    if self.current_frame >= len(frames) - 1:
                        self.dead = True
                else:
                    self.current_frame = (self.current_frame + 1) % len(frames)
    
    def update_skills(self, dt, player):
        """Update all skills (especially projectiles)"""
        for skill in self.skills.values():
            # Skip if skill is not a proper skill instance (e.g., dict or None)
            if not hasattr(skill, 'update') or not callable(skill.update):
                continue
            # Check if update method accepts owner parameter
            try:
                import inspect
                sig = inspect.signature(skill.update)
                # If update takes more than just dt, pass owner as well
                if len(sig.parameters) > 1:
                    skill.update(dt, self)
                else:
                    skill.update(dt)
            except Exception:
                # Fallback: try calling with owner parameter
                try:
                    skill.update(dt, self)
                except TypeError:
                    # If that fails, try without owner
                    try:
                        skill.update(dt)
                    except Exception:
                        pass
            
            # Handle projectile collisions with player
            if hasattr(skill, 'projectiles') and hasattr(player, 'rect'):
                for proj in list(skill.projectiles):
                    if hasattr(proj, 'rect') and proj.rect.colliderect(player.rect):
                        # Hit player
                        try:
                            player.take_damage(proj.damage)
                        except Exception:
                            pass
                        # Remove projectile after hit
                        try:
                            skill.projectiles.remove(proj)
                        except Exception:
                            pass
    
    def draw_skills(self, surface, camera_x, camera_y):
        """Draw skill effects (projectiles)"""
        for skill in self.skills.values():
            if hasattr(skill, 'draw'):
                skill.draw(surface, camera_x, camera_y)
    
    def draw(self, surface, camera_x, camera_y, show_hitbox: bool = False):
        """Override draw để vẽ cả projectiles"""
        # Vẽ enemy sprite
        super().draw(surface, camera_x, camera_y, show_hitbox)
        # Vẽ projectiles và skill effects
        self.draw_skills(surface, camera_x, camera_y)


class ControllerEnemy(DataDrivenEnemy):
    """
    Khống chế - Enemy tạo hiệu ứng area control và crowd control
    
    Đặc điểm:
    - Tấn công charged projectile (tích năng lượng)
    - Tạo hiệu ứng làm chậm player trong area
    - Có thể "teleport" ngắn để reposition
    - Sử dụng cast animation cho abilities
    """
    
    def __init__(self, x, y, char_id='Wraith_03', patrol_range=180, speed=70):
        super().__init__(x, y, char_id=char_id, patrol_range=patrol_range, speed=speed)
        
        # Controller-specific stats  
        self.max_hp = 120  # Nhiều máu hơn caster nhưng ít hơn tank
        self.hp = self.max_hp
        self.attack_damage = 5  
        
        # Range behavior (TĂNG TẦM ĐÁNH)
        self.detection_range = 1000  # Tầm phát hiện xa hơn
        self.max_ability_range = 800  # Tầm sử dụng ability xa hơn

        # Charged attack
        self.charge_skill = None
        self.charging = False
        self.charge_start_time = 0.0
        self.max_charge_time = 2.0
        
        # Area control
        self.slow_aura_range = 180
        self.slow_effect = 0.5  # Giảm 50% tốc độ
        
        # Teleport ability
        self.teleport_cooldown = 8.0
        self.teleport_timer = 0.0
        self.teleport_range = 150
        
        # Behavior timers
        self.ability_cooldown = 4.0
        self.ability_timer = 0.0
        self.current_ability = None
        
        # Animation speeds (chậm hơn để dễ thấy)
        self.anim_speed = 0.1        # Default animation speed
        self.cast_anim_speed = 0.1   # Cast animation rất chậm (charging)
        self.attack_anim_speed = 0.08 # Attack animation 
        self.hurt_anim_speed = 0.2    # Hurt animation
        
    def update(self, dt, platforms, player):
        if self.dead:
            return  # Đã chết hoàn toàn, không cần update gì nữa
            
        if self.dying:
            # Đang dying - chỉ chạy physics và animation, không chạy AI
            self._update_physics(dt, platforms)
            self._update_animation(dt)
            return
            
        # Cập nhật timers
        self.ability_timer = max(0.0, self.ability_timer - dt)
        self.teleport_timer = max(0.0, self.teleport_timer - dt)
        
        # Tính khoảng cách đến player
        dx = player.rect.centerx - self.rect.centerx
        dy = abs(player.rect.centery - self.rect.centery)
        distance = abs(dx)
        
        prev_state = self.state
        
        # AI Logic cho Controller
        if distance < self.detection_range and dy < 140:
            # Player trong tầm phát hiện
            
            if self.charging:
                # Đang charge attack
                self.state = 'cast'
                charge_time = pygame.time.get_ticks() / 1000.0 - self.charge_start_time
                
                if charge_time >= self.max_charge_time:
                    # Release charged attack
                    self._release_charged_attack(player)
                    self.charging = False
                    self.ability_timer = self.ability_cooldown
                    
            elif distance < 80 and self.teleport_timer <= 0.0:
                # Player quá gần - teleport away
                self._attempt_teleport(player)
                self.teleport_timer = self.teleport_cooldown
                
            elif self.ability_timer <= 0.0:
                # Có thể sử dụng ability
                if distance <= self.max_ability_range:  # Sử dụng tầm ability mới
                    # Bắt đầu charge attack - quay mặt về player
                    self.charging = True
                    self.charge_start_time = pygame.time.get_ticks() / 1000.0
                    self.state = 'cast'
                    self.direction = 1 if dx > 0 else -1
                    self.facing_right = dx > 0  # Cập nhật facing_right
                else:
                    # Tiến lại gần player
                    self.state = 'walk'
                    advance_dir = 1 if dx > 0 else -1
                    move_x = self.speed * advance_dir * dt
                    
                    new_x = self.rect.centerx + move_x
                    if self.patrol_min <= new_x <= self.patrol_max:
                        self.rect.x += int(move_x)
                        self.direction = advance_dir
                        self.facing_right = advance_dir > 0  # Cập nhật facing_right
            else:
                # Chờ cooldown - di chuyển strategically
                if distance > 200:
                    # Tiến lại gần
                    self.state = 'walk'
                    self.direction = 1 if dx > 0 else -1
                    self.facing_right = dx > 0  # Cập nhật facing_right
                    move_x = self.speed * self.direction * dt
                    new_x = self.rect.centerx + move_x
                    if self.patrol_min <= new_x <= self.patrol_max:
                        self.rect.x += int(move_x)
                elif distance < 120:
                    # Lùi lại
                    self.state = 'walk'
                    retreat_dir = -1 if dx > 0 else 1
                    move_x = self.speed * retreat_dir * dt
                    new_x = self.rect.centerx + move_x
                    if self.patrol_min <= new_x <= self.patrol_max:
                        self.rect.x += int(move_x)
                        self.direction = retreat_dir
                        self.facing_right = retreat_dir > 0  # Cập nhật facing_right
                else:
                    # Khoảng cách tốt - đứng yên
                    self.state = 'idle'
                    self.direction = 1 if dx > 0 else -1
                    self.facing_right = dx > 0  # Cập nhật facing_right
        else:
            # Patrol bình thường
            self.state = 'walk'
            move = self.speed * self.direction * dt
            self.rect.x += int(move)
            
            if self.rect.centerx < self.patrol_min:
                self.rect.centerx = int(self.patrol_min)
                self.direction = 1
            elif self.rect.centerx > self.patrol_max:
                self.rect.centerx = int(self.patrol_max)
                self.direction = -1
        
        # Áp dụng slow effect lên player nếu trong tầm
        self._apply_area_effects(player, distance)
        
        # Reset animation khi thay đổi state
        if prev_state != self.state:
            self.current_frame = 0
            self.anim_timer = 0.0
        
        # Update skills (charged projectiles) - sử dụng method an toàn
        self.update_skills(dt, player)
            
        # Update physics và animation
        self._update_physics(dt, platforms)
        self._update_animation(dt)
    
    def _release_charged_attack(self, player):
        """Thả charged/slow projectile về phía player"""
        try:
            # Đảm bảo facing_right được set đúng hướng về player ngay trước khi bắn
            dx = player.rect.centerx - self.rect.centerx
            self.facing_right = dx > 0
            self.direction = 1 if dx > 0 else -1
            
            # Thử slow skill trước (cho Wraith_03), fallback sang charge skill
            slow_skill = self.skills.get('slow')
            if slow_skill and hasattr(slow_skill, 'release'):
                held_time = self.max_charge_time
                import time
                current_time = time.time()
                slow_skill.release(current_time, self, held_time)
            else:
                # Fallback: charge skill (cho các controller khác)
                charge_skill = self.skills.get('charge')
                if charge_skill and hasattr(charge_skill, 'release'):
                    held_time = self.max_charge_time
                    import time
                    current_time = time.time()
                    charge_skill.release(current_time, self, held_time)
        except Exception:
            # Fallback damage
            distance = abs(player.rect.centerx - self.rect.centerx)
            if distance <= self.max_ability_range:
                # Damage giảm xuống, phù hợp với base_damage = 7
                damage = int(self.attack_damage * 1.5)  # 7 * 1.5 = 10.5 ≈ 10 damage
                try:
                    player.take_damage(damage)
                except Exception:
                    pass
    
    def _attempt_teleport(self, player):
        """Teleport ra xa player"""
        # Tìm vị trí teleport hợp lệ
        player_x = player.rect.centerx
        
        # Thử teleport về phía sau trong patrol range
        if player_x > self.rect.centerx:
            # Player ở bên phải, teleport về trái
            target_x = max(self.patrol_min, self.rect.centerx - self.teleport_range)
        else:
            # Player ở bên trái, teleport về phải  
            target_x = min(self.patrol_max, self.rect.centerx + self.teleport_range)
        
        # Thực hiện teleport
        self.rect.centerx = int(target_x)
        
        # Visual effect (có thể thêm particle effect sau)
        self.state = 'cast'
        self.current_frame = 0
    
    def _apply_area_effects(self, player, distance):
        """Áp dụng hiệu ứng area lên player"""
        if distance <= self.slow_aura_range:
            # Áp dụng slow effect
            try:
                # Giảm tốc độ player (cần player hỗ trợ status effects)
                if hasattr(player, 'apply_slow'):
                    player.apply_slow(self.slow_effect, 0.1)  # 0.1 second duration
                elif hasattr(player, 'speed_multiplier'):
                    # Fallback: modify speed directly
                    if not hasattr(player, '_original_speed'):
                        player._original_speed = getattr(player, 'speed', 200)
                    player.speed = player._original_speed * self.slow_effect
            except Exception:
                pass
        else:
            # Restore normal speed when out of range
            try:
                if hasattr(player, '_original_speed'):
                    player.speed = player._original_speed
            except Exception:
                pass
    
    def update_skills(self, dt, player):
        """Update all skills (especially charged projectiles)"""
        for skill in self.skills.values():
            # Skip if skill is not a proper skill instance (e.g., dict or None)
            if not hasattr(skill, 'update') or not callable(skill.update):
                continue
            # Check if update method accepts owner parameter
            try:
                import inspect
                sig = inspect.signature(skill.update)
                # If update takes more than just dt, pass owner as well
                if len(sig.parameters) > 1:
                    skill.update(dt, self)
                else:
                    skill.update(dt)
            except Exception:
                # Fallback: try calling with owner parameter
                try:
                    skill.update(dt, self)
                except TypeError:
                    # If that fails, try without owner
                    try:
                        skill.update(dt)
                    except Exception:
                        pass
            
            # Handle projectile collisions with player
            if hasattr(skill, 'projectiles') and hasattr(player, 'rect'):
                for proj in list(skill.projectiles):
                    if hasattr(proj, 'rect') and proj.rect.colliderect(player.rect):
                        # Track nếu đã hit player để không áp dụng effect nhiều lần
                        player_id = id(player)
                        if not hasattr(proj, 'hit_players'):
                            proj.hit_players = set()
                        
                        # Nếu projectile đã hit player này rồi thì skip
                        if player_id in proj.hit_players:
                            continue
                        
                        # Đánh dấu đã hit player
                        proj.hit_players.add(player_id)
                        
                        # Check if this is a slow projectile
                        if getattr(proj, 'is_slow_projectile', False):
                            # Apply slow effect instead of high damage
                            try:
                                # Gây ít damage
                                player.take_damage(proj.damage)
                                
                                # Áp dụng slow effect
                                slow_percent = getattr(proj, 'slow_percent', 50)
                                slow_duration = getattr(proj, 'slow_duration', 2.0)
                                
                                # Lưu tốc độ gốc nếu chưa có
                                if not hasattr(player, '_original_speed'):
                                    player._original_speed = getattr(player, 'speed', 200)
                                
                                # Áp dụng slow
                                player.speed = int(player._original_speed * (100 - slow_percent) / 100)
                                
                                # Lưu thời gian slow để có thể restore sau
                                import time
                                player.slowed_until = time.time() + slow_duration
                                player.is_slowed = True
                                
                                # Log để debug - RÕ RÀNG HƠN
                                print("=" * 60)
                                print(f"🐌 SLOW EFFECT APPLIED! 🐌")
                                print(f"   Speed: {player._original_speed} -> {player.speed} ({slow_percent}% slower!)")
                                print(f"   Duration: {slow_duration:.1f} seconds")
                                print(f"   You can barely move now!")
                                print("=" * 60)
                                
                            except Exception as e:
                                print(f"Error applying slow: {e}")
                        else:
                            # Normal damage projectile
                            try:
                                player.take_damage(proj.damage)
                            except Exception:
                                pass
                        # Projectiles can pierce but only hit each target once
    
    def draw_skills(self, surface, camera_x, camera_y):
        """Draw skill effects (projectiles)"""
        for skill in self.skills.values():
            if hasattr(skill, 'draw'):
                skill.draw(surface, camera_x, camera_y)
    
    def _update_physics(self, dt, platforms):
        """Physics update"""
        self.vel_y += 2  # GRAVITY
        self.rect.y += int(self.vel_y)
        
        self.on_ground = False
        for _, platform_rect in platforms:
            if self.rect.colliderect(platform_rect):
                if self.vel_y > 0:
                    self.rect.bottom = platform_rect.top
                    self.vel_y = 0
                    self.on_ground = True
    
    def _update_animation(self, dt):
        """Animation update"""
        frames = self.animations.get(self.state) or []
        if frames:
            if self.state == 'cast':
                current_speed = self.cast_anim_speed
            elif self.state == 'attack':
                current_speed = self.attack_anim_speed  
            elif self.state == 'hurt':
                current_speed = self.hurt_anim_speed
            else:
                current_speed = self.anim_speed
                
            self.anim_timer += dt
            if self.anim_timer >= current_speed:
                self.anim_timer = 0.0
                if self.state == 'dying':
                    if self.current_frame < len(frames) - 1:
                        self.current_frame += 1
                    if self.current_frame >= len(frames) - 1:
                        self.dead = True
                else:
                    self.current_frame = (self.current_frame + 1) % len(frames)

    def draw(self, surface, camera_x, camera_y, show_hitbox: bool = False):
        """Override draw để thêm visual effects"""
        super().draw(surface, camera_x, camera_y, show_hitbox)
        
        # Vẽ projectiles từ skills
        for skill in self.skills.values():
            if hasattr(skill, 'draw'):
                skill.draw(surface, camera_x, camera_y)
        
        # Vẽ slow aura khi player ở gần
        try:
            # Tìm player để check distance (simplified)
            aura_color = (100, 0, 200, 50)  # Purple with alpha
            aura_radius = int(self.slow_aura_range)
            center_x = int(self.rect.centerx - camera_x)
            center_y = int(self.rect.centery - camera_y)
            
            # Tạo surface tạm với alpha để vẽ aura
            if hasattr(pygame, 'SRCALPHA'):
                aura_surface = pygame.Surface((aura_radius * 2, aura_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(aura_surface, aura_color, (aura_radius, aura_radius), aura_radius)
                surface.blit(aura_surface, (center_x - aura_radius, center_y - aura_radius))
        except Exception:
            # Skip if can't draw aura
            pass


class ExploderEnemy(DataDrivenEnemy):
    """
    Minotaur - Enemy phát nổ khi chết
    
    Đặc điểm:
    - Tank với HP cao
    - Khi bị giết, phát nổ sau một khoảng thời gian ngắn
    - Explosion gây damage cho player trong bán kính
    - Visual effect khi explode
    """
    
    def __init__(self, x, y, char_id='minotaur_01', patrol_range=200, speed=40):
        super().__init__(x, y, char_id=char_id, patrol_range=patrol_range, speed=speed)
        
        # Store character ID for debugging/logging
        self.character_id = char_id
        
        # Exploder-specific stats
        self.max_hp = 150  # Tank - nhiều máu
        self.hp = self.max_hp
        self.attack_damage = 25
        
        # Explosion settings
        self.explosion_delay = 1  # Delay trước khi nổ (giây) - tăng lên để thấy rõ warning
        self.explosion_radius = 250  # Bán kính explosion   
        self.explosion_damage = 20  # Damage của explosion
        self.exploding = False
        self.explosion_timer = 0.0
        self.has_exploded = False
        
        # Explosion visual effects
        self.explosion_particles = []  # Particles bay ra khi nổ
        self.explosion_shockwaves = []  # Sóng xung kích mở rộng
        self.explosion_flash_timer = 0.0  # Timer cho flash effect
        self.smoke_particles = []  # Khói sau explosion
        self.screen_shake = {'x': 0, 'y': 0, 'intensity': 0}  # Screen shake effect
        
        # Animation speeds
        self.anim_speed = 0.15
        self.attack_anim_speed = 0.12
        self.hurt_anim_speed = 0.1
        self.dying_anim_speed = 0.15
        
    def update(self, dt, platforms, player):
        # Kiểm tra nếu đang trong quá trình nổ
        if self.exploding:
            self.explosion_timer += dt
            
            # Visual effect - nhấp nháy nhanh hơn khi gần nổ
            self.state = 'dying'
            
            if self.explosion_timer >= self.explosion_delay:
                # BOOM! Phát nổ
                if not self.has_exploded:
                    self._explode(player)
                    self.has_exploded = True
                    self.dead = True  # Đánh dấu dead để bị remove
            
            # Update animation trong khi chờ nổ
            frames = self.animations.get(self.state) or []
            if frames:
                self.anim_timer += dt
                if self.anim_timer >= self.dying_anim_speed:
                    self.anim_timer = 0.0
                    if self.current_frame < len(frames) - 1:
                        self.current_frame += 1
            return
        
        # Logic bình thường khi chưa dying
        if self.dying and not self.exploding:
            # Bắt đầu quá trình explosion
            self.exploding = True
            self.explosion_timer = 0.0
            print(f"[EXPLODER] {self.character_id} is about to EXPLODE in {self.explosion_delay}s!")
            return
        
        # AI và movement bình thường
        super().update(dt, platforms, player)
    
    def _explode(self, player):
        """Phát nổ và gây damage cho player nếu trong tầm"""
        print("=" * 120)
        print("[EXPLODER] EXPLOSION!")
        
        # Tạo explosion particles - GIẢM SỐ LƯỢNG để tránh lag
        import random
        import math
        for _ in range(35):  # Giảm từ 60 -> 35 particles
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(150, 400)  # Tốc độ cao hơn
            self.explosion_particles.append({
                'x': self.rect.centerx,
                'y': self.rect.centery,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed - random.uniform(50, 150),  # Bias lên trên
                'life': random.uniform(0.4, 0.8),
                'max_life': random.uniform(0.4, 0.8),
                'size': random.randint(4, 12),  # Lớn hơn
                'color': random.choice([
                    (255, 255, 100),  # Vàng sáng
                    (255, 200, 0),    # Vàng
                    (255, 150, 0),    # Cam sáng
                    (255, 100, 0),    # Cam
                    (255, 50, 0),     # Đỏ cam
                    (255, 0, 0),      # Đỏ
                ])
            })
        
        # Tạo shockwaves (sóng xung kích) - GIẢM SỐ LƯỢNG
        for i in range(3):  # Giảm từ 5 -> 3 sóng
            self.explosion_shockwaves.append({
                'radius': i * 20,
                'max_radius': self.explosion_radius * 1.5 + i * 40,
                'speed': 500 + i * 80,
                'life': 0.8 - i * 0.12,
                'max_life': 0.8 - i * 0.12,
            })
        
        # Tạo smoke particles - GIẢM SỐ LƯỢNG
        for _ in range(15):  # Giảm từ 30 -> 15
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(20, 60)
            self.smoke_particles.append({
                'x': self.rect.centerx,
                'y': self.rect.centery,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed - random.uniform(30, 80),  # Bay lên
                'life': random.uniform(1.0, 2.0),  # Sống lâu hơn
                'max_life': random.uniform(1.0, 2.0),
                'size': random.randint(8, 20),
                'growth': random.uniform(15, 30),  # Phình to dần
            })
        
        # Screen shake effect - GIẢM INTENSITY
        self.screen_shake = {
            'intensity': 12,  # Giảm từ 20 -> 12
            'duration': 0.3,  # Giảm từ 0.4 -> 0.3
            'timer': 0.0
        }
        
        # Tính khoảng cách đến player
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = (dx * dx + dy * dy) ** 0.5
        
        print(f"   Explosion radius: {self.explosion_radius}")
        print(f"   Distance to player: {distance:.1f}")
        
        if distance <= self.explosion_radius:
            # Player trong tầm nổ - gây damage
            try:
                player.take_damage(self.explosion_damage)
                print(f"   💀 Player hit by explosion! Damage: {self.explosion_damage} HP")
                
                # Knock back player - MẠNH HƠN
                if distance > 0:
                    knockback_force = 25  # Tăng từ 15 -> 25
                    player.vel_x = (dx / distance) * knockback_force
                    player.vel_y = -12  # Bật lên cao hơn
                    
            except Exception as e:
                print(f"   Error dealing explosion damage: {e}")
        else:
            print(f"   Player is safe (too far)")
        
        print("=" * 60)
    
    def draw(self, surface, camera_x, camera_y, show_hitbox: bool = False):
        """Override draw để thêm explosion visual effects"""
        
        # LƯU camera gốc TRƯỚC KHI apply screen shake
        original_camera_x = camera_x
        original_camera_y = camera_y
        
        # Update particles và shockwaves
        dt = 0.016  # Approximate frame time
        
        # Update particles
        for particle in self.explosion_particles[:]:
            particle['life'] -= dt
            if particle['life'] <= 0:
                self.explosion_particles.remove(particle)
            else:
                # Update position
                particle['x'] += particle['vx'] * dt
                particle['y'] += particle['vy'] * dt
                # Gravity
                particle['vy'] += 500 * dt
                # Slow down
                particle['vx'] *= 0.98
        
        # Update shockwaves
        for wave in self.explosion_shockwaves[:]:
            wave['life'] -= dt
            if wave['life'] <= 0:
                self.explosion_shockwaves.remove(wave)
            else:
                wave['radius'] += wave['speed'] * dt
        
        # Update smoke particles
        for smoke in self.smoke_particles[:]:
            smoke['life'] -= dt
            if smoke['life'] <= 0:
                self.smoke_particles.remove(smoke)
            else:
                smoke['x'] += smoke['vx'] * dt
                smoke['y'] += smoke['vy'] * dt
                smoke['vy'] -= 30 * dt  # Float up
                smoke['vx'] *= 0.95  # Slow down
                smoke['size'] += smoke['growth'] * dt  # Grow
        
        # Update screen shake
        if 'timer' in self.screen_shake:
            self.screen_shake['timer'] += dt
            if self.screen_shake['timer'] < self.screen_shake.get('duration', 0):
                import random
                intensity = self.screen_shake['intensity'] * (1 - self.screen_shake['timer'] / self.screen_shake['duration'])
                self.screen_shake['x'] = random.uniform(-intensity, intensity)
                self.screen_shake['y'] = random.uniform(-intensity, intensity)
            else:
                self.screen_shake['x'] = 0
                self.screen_shake['y'] = 0
        
        # Apply screen shake to camera CHỈ CHO VISUAL, KHÔNG ẢNH HƯỞNG DAMAGE
        shake_x = int(self.screen_shake.get('x', 0))
        shake_y = int(self.screen_shake.get('y', 0))
        camera_x_visual = camera_x + shake_x
        camera_y_visual = camera_y + shake_y
        
        # Vẽ enemy sprite bình thường (nếu chưa explode) - dùng camera gốc
        if not self.has_exploded:
            super().draw(surface, original_camera_x, original_camera_y, show_hitbox)
        
        # Visual warning khi sắp nổ
        if self.exploding and not self.has_exploded:
            try:
                import math
                
                # Tính % thời gian còn lại
                progress = self.explosion_timer / self.explosion_delay
                time_left = self.explosion_delay - self.explosion_timer
                
                # Dùng camera với shake cho visual effects
                center_x = int(self.rect.centerx - camera_x_visual)
                center_y = int(self.rect.centery - camera_y_visual)
                
                # 1. Vẽ NHIỀU pulsing circles - GIẢM LAYERS để tránh lag
                pulse_speed = 5 + progress * 20  # Nhanh dần hơn
                pulse_scale = 0.7 + 0.3 * abs(math.sin(self.explosion_timer * pulse_speed))
                pulse_radius = int(self.explosion_radius * pulse_scale)
                
                # Gradient từ trong ra ngoài - GIẢM TỪ 10 -> 6 LAYERS
                for r in range(6, 0, -1):
                    alpha = int(80 * (r / 6) * (1 - progress * 0.5))
                    # Màu chuyển từ vàng -> cam -> đỏ
                    red = 255
                    green = int(200 * (1 - progress) + 50 * progress)
                    blue = int(50 * (1 - progress))
                    color = (red, green, blue, alpha)
                    
                    if hasattr(pygame, 'SRCALPHA'):
                        pulse_surf = pygame.Surface((pulse_radius * 2, pulse_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(pulse_surf, color,
                                         (pulse_radius, pulse_radius),
                                         int(pulse_radius * (r / 6)), 3)
                        surface.blit(pulse_surf,
                                   (center_x - pulse_radius, center_y - pulse_radius))
                
                # Thêm inner glow - sáng ở giữa - GIẢM TỪ 5 -> 3 LAYERS
                inner_glow_radius = int(pulse_radius * 0.3)
                for i in range(3, 0, -1):
                    alpha = int(150 * (i / 3))
                    if hasattr(pygame, 'SRCALPHA'):
                        glow_surf = pygame.Surface((inner_glow_radius * 2, inner_glow_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(glow_surf, (255, 255, 100, alpha),
                                         (inner_glow_radius, inner_glow_radius),
                                         int(inner_glow_radius * (i / 3)))
                        surface.blit(glow_surf,
                                   (center_x - inner_glow_radius, center_y - inner_glow_radius))
                
                # 2. Vẽ danger zone border - NHIỀU LAYERS nhấp nháy
                blink_fast = int(self.explosion_timer * 15) % 2 == 0
                blink_slow = int(self.explosion_timer * 8) % 2 == 0
                
                if blink_fast:
                    for thickness in [8, 6, 4]:
                        alpha = int(220 - thickness * 20)
                        border_color = (255, 0, 0, alpha)
                        if hasattr(pygame, 'SRCALPHA'):
                            border_surf = pygame.Surface((self.explosion_radius * 2, self.explosion_radius * 2), pygame.SRCALPHA)
                            pygame.draw.circle(border_surf, border_color,
                                             (self.explosion_radius, self.explosion_radius),
                                             self.explosion_radius, thickness)
                            surface.blit(border_surf,
                                       (center_x - self.explosion_radius, center_y - self.explosion_radius))
                
                # Outer warning ring
                if blink_slow:
                    outer_radius = int(self.explosion_radius * 1.2)
                    if hasattr(pygame, 'SRCALPHA'):
                        outer_surf = pygame.Surface((outer_radius * 2, outer_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(outer_surf, (255, 100, 0, 150),
                                         (outer_radius, outer_radius),
                                         outer_radius, 3)
                        surface.blit(outer_surf,
                                   (center_x - outer_radius, center_y - outer_radius))
                
                # 3. Countdown timer - TO VÀ RÕ HƠN
                try:
                    font = pygame.font.Font(None, 96)  # Lớn hơn từ 72 -> 96
                    countdown_text = f"{time_left:.1f}"
                    
                    # Màu chuyển từ vàng -> đỏ
                    red = 255
                    green = int(255 * (1 - progress))
                    text_color = (red, green, 0)
                    text_surface = font.render(countdown_text, True, text_color)
                    
                    # Multiple shadows cho 3D effect
                    for offset in [(4, 4), (3, 3), (2, 2)]:
                        shadow_surface = font.render(countdown_text, True, (0, 0, 0))
                        shadow_rect = shadow_surface.get_rect(center=(center_x + offset[0], center_y - 80 + offset[1]))
                        surface.blit(shadow_surface, shadow_rect)
                    
                    text_rect = text_surface.get_rect(center=(center_x, center_y - 80))
                    surface.blit(text_surface, text_rect)
                    
                    # Warning text - LỚN HƠN, RÕ HƠN
                    warning_font = pygame.font.Font(None, 48)
                    warning_text = warning_font.render("⚠ DANGER! ⚠", True, (255, 0, 0))
                    warning_shadow = warning_font.render("⚠ DANGER! ⚠", True, (0, 0, 0))
                    warning_rect = warning_text.get_rect(center=(center_x, center_y - 130))
                    shadow_warn_rect = warning_shadow.get_rect(center=(center_x + 2, center_y - 128))
                    surface.blit(warning_shadow, shadow_warn_rect)
                    surface.blit(warning_text, warning_rect)
                    
                except Exception:
                    pass
                
                # 4. Sparks effect - GIẢM SỐ LƯỢNG để tránh lag
                import random
                num_sparks = int(10 + 15 * progress)  # Giảm từ 20-50 -> 10-25 sparks
                for i in range(num_sparks):
                    angle = (self.explosion_timer * 8 + i * (360 / max(1, num_sparks))) % 360
                    rad = math.radians(angle)
                    # Sparks bay ra xa hơn khi gần nổ
                    spark_dist = 40 + 30 * progress + 15 * math.sin(self.explosion_timer * 12 + i)
                    spark_x = center_x + int(math.cos(rad) * spark_dist)
                    spark_y = center_y + int(math.sin(rad) * spark_dist)
                    # Sparks lớn hơn và sáng hơn
                    spark_size = random.randint(3, 6)
                    spark_color = (255, random.randint(150, 255), random.randint(0, 50))
                    pygame.draw.circle(surface, spark_color, (spark_x, spark_y), spark_size)
                    
                    # Thêm glow cho sparks
                    if hasattr(pygame, 'SRCALPHA'):
                        glow_surf = pygame.Surface((spark_size * 4, spark_size * 4), pygame.SRCALPHA)
                        pygame.draw.circle(glow_surf, (*spark_color, 100), (spark_size * 2, spark_size * 2), spark_size * 2)
                        surface.blit(glow_surf, (spark_x - spark_size * 2, spark_y - spark_size * 2))
                    
            except Exception as e:
                pass  # Ignore rendering errors
        
        # Vẽ explosion effects
        if self.has_exploded or len(self.explosion_particles) > 0 or len(self.explosion_shockwaves) > 0:
            try:
                # Dùng camera với shake cho visual
                center_x = int(self.rect.centerx - camera_x_visual)
                center_y = int(self.rect.centery - camera_y_visual)
                
                # 1. Vẽ shockwaves (sóng xung kích) - DÀY HƠN, SÁNG HƠN
                for wave in self.explosion_shockwaves:
                    life_percent = wave['life'] / wave['max_life']
                    alpha = int(220 * life_percent)
                    
                    # Gradient color từ vàng sáng -> đỏ -> tối
                    if life_percent > 0.7:
                        color = (255, 255, 100, alpha)  # Vàng sáng
                    elif life_percent > 0.5:
                        color = (255, 200, 50, alpha)   # Vàng cam
                    elif life_percent > 0.3:
                        color = (255, 120, 0, alpha)    # Cam
                    else:
                        color = (220, 60, 0, alpha)     # Đỏ
                    
                    if hasattr(pygame, 'SRCALPHA'):
                        wave_surf = pygame.Surface((int(wave['radius'] * 2), int(wave['radius'] * 2)), pygame.SRCALPHA)
                        # Vẽ ít vòng hơn để tăng performance - từ 3 -> 2 layers
                        for thickness in [8, 5]:
                            t_alpha = int(alpha * (thickness / 8))
                            t_color = (*color[:3], t_alpha)
                            pygame.draw.circle(wave_surf, t_color,
                                             (int(wave['radius']), int(wave['radius'])),
                                             int(wave['radius']), thickness)
                        surface.blit(wave_surf,
                                   (center_x - int(wave['radius']), center_y - int(wave['radius'])))
                
                # 2. Vẽ particles (mảnh vỡ bay tứ tung) - ÍT GLOW HƠN
                for particle in self.explosion_particles:
                    life_percent = particle['life'] / particle['max_life']
                    alpha = int(255 * life_percent)
                    
                    px = int(particle['x'] - camera_x_visual)
                    py = int(particle['y'] - camera_y_visual)
                    size = int(particle['size'] * (0.7 + life_percent * 0.3))  # Shrink slower
                    
                    if size > 0:
                        # Vẽ particle ĐƠN GIẢN HƠN - chỉ 1 glow layer
                        color = (*particle['color'], alpha)
                        if hasattr(pygame, 'SRCALPHA'):
                            particle_surf = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
                            # Chỉ 1 glow layer thay vì 3
                            pygame.draw.circle(particle_surf, (*particle['color'], int(alpha * 0.4)), 
                                             (int(size * 1.5), int(size * 1.5)), int(size * 1.5))
                            # Core
                            pygame.draw.circle(particle_surf, color, (int(size * 1.5), int(size * 1.5)), size)
                            surface.blit(particle_surf, (px - int(size * 1.5), py - int(size * 1.5)))
                        else:
                            pygame.draw.circle(surface, particle['color'][:3], (px, py), size)
                
                # 2.5 Vẽ smoke particles (khói)
                for smoke in self.smoke_particles:
                    life_percent = smoke['life'] / smoke['max_life']
                    alpha = int(150 * life_percent)
                    
                    sx = int(smoke['x'] - camera_x_visual)
                    sy = int(smoke['y'] - camera_y_visual)
                    s_size = int(smoke['size'])
                    
                    if s_size > 0 and alpha > 0:
                        # Màu xám đậm -> nhạt
                        gray = int(50 + 100 * (1 - life_percent))
                        color = (gray, gray, gray, alpha)
                        
                        if hasattr(pygame, 'SRCALPHA'):
                            smoke_surf = pygame.Surface((s_size * 2, s_size * 2), pygame.SRCALPHA)
                            pygame.draw.circle(smoke_surf, color, (s_size, s_size), s_size)
                            surface.blit(smoke_surf, (sx - s_size, sy - s_size))
                
                # 3. Central flash (ánh sáng trung tâm) - GIẢM LAYERS
                if self.has_exploded:
                    self.explosion_flash_timer += dt
                    if self.explosion_flash_timer < 0.3:  # Flash dài hơn: 0.3s
                        flash_progress = self.explosion_flash_timer / 0.3
                        flash_alpha = int(250 * (1 - flash_progress))
                        flash_radius = int(self.explosion_radius * 0.8)  # Lớn hơn
                        
                        if hasattr(pygame, 'SRCALPHA'):
                            flash_surf = pygame.Surface((flash_radius * 2, flash_radius * 2), pygame.SRCALPHA)
                            # GIẢM từ 10 -> 5 layers
                            for i in range(5, 0, -1):
                                r = int(flash_radius * (i / 5))
                                a = int(flash_alpha * (i / 5))
                                # Màu từ trắng -> vàng -> cam
                                if i > 3:
                                    color = (255, 255, 255, a)  # Trắng sáng
                                elif i > 2:
                                    color = (255, 255, 150, a)  # Vàng sáng
                                else:
                                    color = (255, 200, 100, a)  # Vàng cam
                                pygame.draw.circle(flash_surf, color, (flash_radius, flash_radius), r)
                            surface.blit(flash_surf,
                                       (center_x - flash_radius, center_y - flash_radius))
                    
            except Exception:
                pass  # Ignore rendering errors


class BossEnemy(DataDrivenEnemy):
    """
    Tank Boss - Troll Boss
    
    Đặc điểm:
    - HP: 1000 (Tank cực mạnh)
    - Damage: 20 → 35 (Rage Mode)
    - Speed: Vừa → Nhanh (Rage Mode)
    - Invincibility Phases: Miễn sát thương định kỳ
    - Rage Mode: Kích hoạt ở 50% HP
    - Ground Slam: AOE damage skill
    """
    
    def __init__(self, x, y, char_id='Troll1', patrol_range=400, speed=200):
        super().__init__(x, y, char_id=char_id, patrol_range=patrol_range, speed=speed)
        
        # Boss stats
        self.max_hp = 1000
        self.hp = self.max_hp
        self.base_damage = 20
        self.base_speed = speed * 1.1  # TĂNG SPEED lên 30%
        
        # Physics
        self.gravity = 980  # Gravity constant
        self.vel_x = 0
        self.vel_y = 0
        
        # Sprite direction
        self.facing_right = True  # Boss mặc định quay phải
        
        # Rage Mode (kích hoạt ở 50% HP)
        self.rage_mode = False
        self.rage_threshold = 0.5  # 50% HP
        self.rage_speed_multiplier = 1.2
        self.rage_damage_multiplier = 1.2
        
        # Invincibility phases
        self.is_invincible = False
        self.invincibility_timer = 0.0
        self.invincibility_duration = 2.5  # 2.5 giây miễn sát thương
        self.invincibility_cooldown = 15.0  # 15 giây cooldown
        self.invincibility_cooldown_timer = 0.0
        
        # Phase change
        self.phase_changed = False  # Đã chuyển phase chưa
        
        # Ground Slam skill
        self.ground_slam_cooldown = 8.0
        self.ground_slam_timer = 0.0
        self.is_slamming = False
        self.slam_radius = 200
        self.slam_damage = 30
        
        # Visual effects
        self.rage_particles = []
        self.invincible_alpha = 0
        self.invincible_alpha_dir = 5  # Direction for pulsing effect
        
        # Animation speeds
        self.anim_speed = 0.12
        self.attack_anim_speed = 0.10  # NHANH HƠN (từ 0.15 → 0.10)
        self.hurt_anim_speed = 0.1
        self.dying_anim_speed = 0.15
        
        # Attack cooldown
        self.attack_cooldown = 1.5  # GIẢM COOLDOWN (từ 2.0s → 1.5s) - tấn công nhanh hơn
        self.attack_timer = 0.0
        self.is_attacking = False
        self.attack_frame_hit = 5  # Frame thứ 5 trong attack animation sẽ gây damage
        self.attack_has_hit = False  # Track xem đã deal damage trong attack này chưa
        
        # Teleport attack (khi player xa)
        self.teleport_attack_cooldown = 5.0  # 5 giây cooldown
        self.teleport_attack_timer = 0.0
        self.teleport_range_min = 3000  # Teleport khi player XA HƠN 2500px (player đi quá xa!)
        self.teleport_range_max = 5000  # Teleport range max rất cao
        self.teleport_offset = 150  # Teleport cách player 150px
        
        # Theo dõi player có đang chạy xa không
        self.last_player_distance = 0
        self.player_running_away_time = 0.0  # Thời gian player chạy xa liên tục
        
    def take_damage(self, damage):
        """Override take_damage để xử lý invincibility"""
        if self.is_invincible or self.dying or self.dead:
            return  # Không nhận damage khi invincible
        
        # Gọi parent method
        super().take_damage(damage)
        
        # Kiểm tra nếu HP xuống dưới 50% → kích hoạt Rage Mode
        if not self.rage_mode and self.hp <= self.max_hp * self.rage_threshold:
            self._activate_rage_mode()
    
    def _activate_rage_mode(self):
        """Kích hoạt Rage Mode khi HP < 50%"""
        if self.rage_mode:
            return
        
        self.rage_mode = True
        self.phase_changed = True
        
        # Tăng speed và damage
        self.speed = self.base_speed * self.rage_speed_multiplier
        self.attack_damage = int(self.base_damage * self.rage_damage_multiplier)
        
        # Invincible trong 5 giây khi chuyển phase
        self.is_invincible = True
        self.invincibility_timer = 5.0
        
        # Spawn rage particles
        self._spawn_rage_particles()
        
        print(f"[BOSS] RAGE MODE ACTIVATED! Speed: {self.speed:.1f}, Damage: {self.attack_damage}")
    
    def _spawn_rage_particles(self):
        """Tạo particle effects khi bật Rage Mode"""
        import random
        for _ in range(50):
            angle = random.uniform(0, 360)
            speed = random.uniform(50, 150)
            lifetime = random.uniform(0.5, 1.5)
            self.rage_particles.append({
                'x': self.rect.centerx,
                'y': self.rect.centery,
                'vx': speed * (angle / 180 * 3.14159) ** 0.5,
                'vy': speed * ((1 - angle / 360) * 2 - 1),
                'lifetime': lifetime,
                'max_lifetime': lifetime
            })
    
    def _trigger_invincibility(self):
        """Kích hoạt invincibility phase"""
        if self.invincibility_cooldown_timer > 0:
            return  # Đang cooldown
        
        self.is_invincible = True
        self.invincibility_timer = self.invincibility_duration
        self.invincibility_cooldown_timer = self.invincibility_cooldown
        
        print(f"[BOSS] INVINCIBLE for {self.invincibility_duration}s")
    
    def _ground_slam(self, player):
        """Ground Slam - AOE damage"""
        if self.ground_slam_timer > 0:
            return  # Đang cooldown
        
        self.is_slamming = True
        self.ground_slam_timer = self.ground_slam_cooldown
        
        # Tính khoảng cách đến player
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = (dx * dx + dy * dy) ** 0.5
        
        # Nếu player trong bán kính → damage
        if distance <= self.slam_radius:
            try:
                damage = self.slam_damage
                if self.rage_mode:
                    damage = int(damage * 1.5)  # Rage mode tăng damage
                player.take_damage(damage)
                print(f"[BOSS] GROUND SLAM hit player for {damage} damage!")
            except Exception:
                pass
        
        # Visual effects
        self._spawn_slam_effects()
    
    def _spawn_slam_effects(self):
        """Tạo hiệu ứng Ground Slam"""
        import random
        # Spawn shockwave particles
        for _ in range(30):
            angle = random.uniform(0, 360)
            speed = random.uniform(100, 200)
            self.rage_particles.append({
                'x': self.rect.centerx,
                'y': self.rect.bottom,
                'vx': speed * (3.14159 * angle / 180) ** 0.5,
                'vy': -speed * 0.3,
                'lifetime': 0.5,
                'max_lifetime': 0.5
            })
    
    def update(self, dt, platforms, player):
        if self.dead:
            return
        
        if self.dying:
            self._update_animation(dt)
            return
        
        # Update timers
        self.invincibility_timer = max(0.0, self.invincibility_timer - dt)
        self.invincibility_cooldown_timer = max(0.0, self.invincibility_cooldown_timer - dt)
        self.ground_slam_timer = max(0.0, self.ground_slam_timer - dt)
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.teleport_attack_timer = max(0.0, self.teleport_attack_timer - dt)
        
        # Kết thúc invincibility
        if self.is_invincible and self.invincibility_timer <= 0:
            self.is_invincible = False
            print("[BOSS] Invincibility ended")
        
        # Update rage particles
        for particle in list(self.rage_particles):
            particle['x'] += particle['vx'] * dt
            particle['y'] += particle['vy'] * dt
            particle['lifetime'] -= dt
            if particle['lifetime'] <= 0:
                self.rage_particles.remove(particle)
        
        # Tính khoảng cách đến player
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = (dx * dx + dy * dy) ** 0.5
        
        prev_state = self.state
        
        # DEBUG: In thông tin mỗi 60 frames
        if hasattr(self, 'debug_counter'):
            self.debug_counter += 1
        else:
            self.debug_counter = 0
        
        if self.debug_counter % 60 == 0:  # Mỗi giây
            print(f"[BOSS DEBUG] Distance: {int(distance)}px | Far time: {self.player_running_away_time:.1f}s | Teleport timer: {self.teleport_attack_timer:.1f}s")
        
        # Theo dõi xem player có ở RẤT XA không
        if distance > self.teleport_range_min:  # Player ở RẤT XA (> 2000px)
            self.player_running_away_time += dt
            if self.debug_counter % 60 == 0:
                print(f"[BOSS] Player VERY FAR! Distance: {int(distance)}px, Time: {self.player_running_away_time:.1f}s (need 2.0s to teleport)")
        else:
            # Player trong tầm nhìn bình thường - reset timer
            self.player_running_away_time = 0.0
        
        self.last_player_distance = distance
        
        # AI Logic - Boss DI CHUYỂN và tấn công
        # KHÔNG giới hạn detection range - boss luôn "thấy" player
        # Quay mặt về phía player
        if dx != 0:
            self.facing_right = dx > 0
            self.direction = 1 if dx > 0 else -1
        
        # CHECK TELEPORT ATTACK: CHỈ khi player RẤT XA và lâu
        # 1. Player ở RẤT XA (> 2000px)
        # 2. Player đã ở xa liên tục > 2.0 giây (giảm từ 3.0s)
        # 3. Teleport cooldown đã hết
        if (distance > self.teleport_range_min
            and self.player_running_away_time > 2.0 
            and self.teleport_attack_timer <= 0):
            print(f"[BOSS] ⚡ Player at {int(distance)}px! TELEPORTING...")
            
            # Tính vị trí teleport (cách player 100px)
            if dx > 0:
                # Player ở bên phải - teleport về bên trái player
                teleport_x = player.rect.centerx - self.teleport_offset
            else:
                # Player ở bên trái - teleport về bên phải player
                teleport_x = player.rect.centerx + self.teleport_offset
            
            teleport_y = player.rect.centery  # Cùng độ cao
            
            # DỊCH CHUYỂN tức thì
            self.rect.centerx = teleport_x
            self.rect.centery = teleport_y
            
            # Reset cooldown và trigger attack
            self.teleport_attack_timer = self.teleport_attack_cooldown
            prev_state = self.state  # Lưu state cũ
            self.state = 'attack'
            self.vel_x = 0
            # ĐÒN ĐẦU TIÊN SAU TELEPORT: attack NGAY (timer = 0)
            self.attack_timer = 0.0  # KHÔNG cooldown cho đòn đầu
            self.attack_has_hit = False  # Reset để có thể deal damage
            self.current_frame = 0  # Reset animation về frame đầu
            
            print(f"[BOSS] ✓ TELEPORTED to ({int(teleport_x)}, {int(teleport_y)})! INSTANT ATTACK!")
            # Damage sẽ được gây khi attack animation đến hit frame (tự nhiên hơn)
        
        # Melee attack khi player RẤT GẦN (< 150px)
        elif distance <= 150:  # Attack range
            # Chỉ attack nếu cooldown đã hết
            if self.attack_timer <= 0 and self.state != 'attack':
                prev_state = self.state  # Lưu state cũ
                self.state = 'attack'
                self.vel_x = 0  # Đứng yên khi attack
                
                # Reset attack timer và damage flag
                self.attack_timer = self.attack_cooldown
                self.attack_has_hit = False  # Reset flag để deal damage
                self.current_frame = 0  # Reset animation về frame đầu
                print(f"[BOSS] Starting melee attack (prev state: {prev_state})")
                
            elif self.state == 'attack':
                # Đang trong attack animation
                self.vel_x = 0
            else:
                # Cooldown chưa hết → đứng idle
                if self.state != 'idle':
                    self.attack_has_hit = False  # Reset khi chuyển sang idle
                self.state = 'idle'
                self.vel_x = 0
        
        # Chase player - DI CHUYỂN về phía player (LUÔN đuổi khi distance > 150px)
        elif distance > 150:
            # Boss đi bộ/chạy để lại gần player
            if self.rage_mode:
                self.state = 'run'  # Rage mode - chạy nhanh
            else:
                self.state = 'walk'  # Normal - đi bộ
            
            # Di chuyển về phía player
            move_speed = self.speed if not self.rage_mode else self.speed * 1.5
            if dx > 0:
                self.vel_x = move_speed
            else:
                self.vel_x = -move_speed
        
        # Trigger invincibility ngẫu nhiên khi HP thấp
        if self.hp < self.max_hp * 0.7 and not self.is_invincible:
            import random
            if random.random() < 0.001:  # 0.1% mỗi frame
                self._trigger_invincibility()
        
        # Reset animation khi đổi state
        if prev_state != self.state:
            self.current_frame = 0
            self.anim_timer = 0.0
        
        # Apply gravity
        gravity = 1200
        self.vel_y += gravity * dt
        
        # Giới hạn tốc độ rơi tối đa (terminal velocity)
        max_fall_speed = 800
        if self.vel_y > max_fall_speed:
            self.vel_y = max_fall_speed
        
        # Apply velocity
        self.rect.x += int(self.vel_x * dt)
        self.rect.y += int(self.vel_y * dt)
        
        # Handle platform collision (Boss đứng trên nền)
        on_ground = self._handle_platform_collision(platforms)
        
        # Debug: Kiểm tra nếu Boss rơi quá xa - tìm platform gần nhất để respawn
        if self.rect.y > 20000:  # Tăng threshold lên 20000 (gần map height)
            print(f"[BOSS ERROR] Boss fell out of map! Y={self.rect.y}, Finding nearest platform...")
            
            # Tìm platform gần nhất
            nearest_platform_y = None
            for platform in platforms:
                if isinstance(platform, tuple) and len(platform) >= 2:
                    platform_rect = platform[1]
                elif hasattr(platform, 'rect'):
                    platform_rect = platform.rect
                else:
                    continue
                
                # Tìm platform gần X position của boss
                if abs(platform_rect.centerx - self.rect.centerx) < 1000:
                    if platform_rect.top < 18000:  # Platform hợp lệ (không quá thấp)
                        if nearest_platform_y is None or platform_rect.top < nearest_platform_y:
                            nearest_platform_y = platform_rect.top
            
            if nearest_platform_y:
                print(f"[BOSS] Respawning on platform at Y={nearest_platform_y}")
                self.rect.y = nearest_platform_y - self.rect.height
            else:
                print(f"[BOSS] No platform found, using default Y=9000")
                self.rect.y = 9000
            
            self.vel_y = 0
            self.vel_x = 0
        
        # Update animation
        self._update_animation(dt)
    
        # Deal damage nếu đang attack và đến hit frame
        if self.state == 'attack' and not self.attack_has_hit:
            attack_frames = self.animations.get('attack', [])
            if len(attack_frames) > 0:
                hit_frame = len(attack_frames) // 2  # Frame giữa animation
                if self.current_frame == hit_frame:
                    # Check distance lại để đảm bảo player vẫn trong range
                    if distance <= 150:
                        try:
                            player.take_damage(self.attack_damage)
                            self.attack_has_hit = True  # Đánh dấu đã deal damage
                            print(f"[BOSS] Hit player for {self.attack_damage} damage! HP: {player.hp}/{player.max_hp}")
                        except Exception as e:
                            print(f"[BOSS] Failed to damage player: {e}")
        
        # Update invincible alpha (pulsing effect)
        if self.is_invincible:
            self.invincible_alpha += self.invincible_alpha_dir
            if self.invincible_alpha >= 100:
                self.invincible_alpha = 100
                self.invincible_alpha_dir = -5
            elif self.invincible_alpha <= 30:
                self.invincible_alpha = 30
                self.invincible_alpha_dir = 5
    
    def _handle_platform_collision(self, platforms):
        """Xử lý collision với platforms (đứng trên nền)"""
        on_ground = False
        
        # Debug: Log số lượng platforms (chỉ log 1 lần)
        if not hasattr(self, '_platform_logged'):
            print(f"[BOSS] Checking collision with {len(platforms)} platforms")
            self._platform_logged = True
        
        for platform in platforms:
            # Platforms là tuple (tile_img, rect)
            if isinstance(platform, tuple) and len(platform) >= 2:
                platform_rect = platform[1]
            elif hasattr(platform, 'rect'):
                platform_rect = platform.rect
            else:
                continue
            
            # Check collision
            if self.rect.colliderect(platform_rect):
                # Vertical collision
                if self.vel_y > 0:  # Falling down
                    # Land on platform
                    self.rect.bottom = platform_rect.top
                    self.vel_y = 0
                    on_ground = True
                    
                    # Debug: Log khi Boss land (chỉ log lần đầu)
                    if not hasattr(self, '_landed_logged'):
                        print(f"[BOSS] Landed on platform at Y={self.rect.bottom}")
                        self._landed_logged = True
                    break  # Đã tìm thấy platform, không cần check tiếp
                elif self.vel_y < 0:  # Jumping up
                    # Hit ceiling
                    self.rect.top = platform_rect.bottom
                    self.vel_y = 0
        
        return on_ground
    
    def _update_animation(self, dt):
        """Update animation frames"""
        frames = self.animations.get(self.state) or []
        if not frames:
            return
        
        # Chọn animation speed dựa trên state
        if self.state == 'attack':
            current_speed = self.attack_anim_speed
        elif self.state == 'hurt':
            current_speed = self.hurt_anim_speed
        elif self.state == 'dying':
            current_speed = self.dying_anim_speed
        else:
            current_speed = self.anim_speed
        
        # Update animation timer
        self.anim_timer += dt
        if self.anim_timer >= current_speed:
            self.anim_timer = 0.0
            
            # Handle dying animation (play once)
            if self.state == 'dying':
                if self.current_frame < len(frames) - 1:
                    self.current_frame += 1
                else:
                    self.dead = True
            else:
                # Loop animation
                prev_frame = self.current_frame
                self.current_frame = (self.current_frame + 1) % len(frames)
                
                # RESET attack_has_hit khi attack animation loop lại
                if self.state == 'attack' and prev_frame > self.current_frame:
                    # Animation đã loop về đầu (prev_frame > current_frame)
                    self.attack_has_hit = False
                    print(f"[BOSS] Attack animation finished, resetting attack_has_hit")
        
        # Update image
        if self.current_frame < len(frames):
            try:
                img = frames[self.current_frame]
                if self.facing_right:
                    self.image = img
                else:
                    self.image = pygame.transform.flip(img, True, False)
            except Exception:
                pass
    
    def draw(self, surface, camera_x, camera_y, show_hitboxes=False):
        """Override draw để thêm visual effects"""
        import pygame
        
        # Draw rage particles
        if len(self.rage_particles) > 0:
            for particle in self.rage_particles:
                alpha = int(255 * (particle['lifetime'] / particle['max_lifetime']))
                color = (255, 100, 0, alpha)  # Orange/red particles
                try:
                    screen_x = int(particle['x'] - camera_x)
                    screen_y = int(particle['y'] - camera_y)
                    pygame.draw.circle(surface, color[:3], (screen_x, screen_y), 3)
                except Exception:
                    pass
        
        # Draw invincibility shield
        if self.is_invincible:
            try:
                screen_x = int(self.rect.centerx - camera_x)
                screen_y = int(self.rect.centery - camera_y)
                radius = max(self.rect.width, self.rect.height) // 2 + 10
                
                # Pulsing shield
                shield_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                color = (100, 200, 255, self.invincible_alpha)
                pygame.draw.circle(shield_surf, color, (radius, radius), radius, 3)
                surface.blit(shield_surf, (screen_x - radius, screen_y - radius))
            except Exception:
                pass
        
        # Draw boss sprite (giống DataDrivenEnemy)
        if not self.dead:
            frames = self.animations.get(self.state) or []
            if frames:
                # Get current frame
                entry = frames[self.current_frame]
                if isinstance(entry, tuple) and len(entry) >= 1:
                    frame = entry[0]
                    trim = entry[1] if len(entry) > 1 else 0
                else:
                    frame = entry
                    trim = 0
                
                # Flip sprite based on direction
                img = frame if self.facing_right else pygame.transform.flip(frame, True, False)
                img_rect = img.get_rect(midbottom=(self.rect.centerx - camera_x, self.rect.bottom - camera_y + trim))
                surface.blit(img, img_rect)
            else:
                # Fallback: vẽ rect nếu không có animation
                pygame.draw.rect(surface, (150, 50, 50), 
                               (self.rect.x - camera_x, self.rect.y - camera_y, 
                                self.rect.width, self.rect.height))
        
        # Draw HP bar (always visible for boss)
        self._draw_boss_hp_bar(surface, camera_x, camera_y)
    
    def _draw_boss_hp_bar(self, surface, camera_x, camera_y):
        """Vẽ HP bar cho Boss (luôn hiển thị)"""
        import pygame
        try:
            # HP bar ở trên đầu boss
            bar_width = 150
            bar_height = 10
            screen_x = int(self.rect.centerx - camera_x - bar_width // 2)
            screen_y = int(self.rect.top - camera_y - 30)
            
            # Background
            pygame.draw.rect(surface, (50, 50, 50), (screen_x, screen_y, bar_width, bar_height))
            
            # HP bar
            hp_ratio = max(0, self.hp / self.max_hp)
            hp_width = int(bar_width * hp_ratio)
            
            # Màu HP bar thay đổi theo Rage Mode
            if self.rage_mode:
                hp_color = (255, 50, 50)  # Red (Rage)
            else:
                hp_color = (50, 255, 50)  # Green
            
            if hp_width > 0:
                pygame.draw.rect(surface, hp_color, (screen_x, screen_y, hp_width, bar_height))
            
            # Border
            pygame.draw.rect(surface, (255, 255, 255), (screen_x, screen_y, bar_width, bar_height), 2)
            
            # Boss name
            font = pygame.font.Font(None, 20)
            name_text = font.render("TROLL BOSS", True, (255, 255, 0))
            name_rect = name_text.get_rect(center=(screen_x + bar_width // 2, screen_y - 15))
            surface.blit(name_text, name_rect)
            
            # HP text
            hp_text = font.render(f"{int(self.hp)}/{self.max_hp}", True, (255, 255, 255))
            hp_rect = hp_text.get_rect(center=(screen_x + bar_width // 2, screen_y + bar_height // 2))
            surface.blit(hp_text, hp_rect)
            
        except Exception:
            pass

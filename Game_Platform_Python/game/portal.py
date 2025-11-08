import pygame
import time
import math

"""
Hệ thống Portal hợp nhất.

Kết hợp 2 nhánh bị conflict:
1) Portal dạng teleport lấy từ Tiled (HEAD)
   - Thuộc tính: id, target_id, cooldown_ms, lockout_ms, spawn_offset_x/y, require_interact, tile_img
   - Teleport player từ cổng nguồn sang cổng đích dựa vào target_id.
2) Portal dạng Arena / khu vực chiến đấu (origin/feature-VanHau)
   - Thuộc tính: portal_id, destination(dict), hiệu ứng hình ảnh, particle, glow, proximity prompt.

Thiết kế hợp nhất:
 - Dùng 1 class Portal, hỗ trợ cả hai loại. Những tham số không dùng thì để None / giá trị mặc định.
 - self.id: ưu tiên obj_id nếu có, nếu không dùng portal_id. Bảo đảm tương thích với code hiện tại trong app.py.
 - destination: nếu không None thì portal là loại Arena hiển thị hiệu ứng & prompt.
 - target_id: nếu có thì hỗ trợ teleport network.
 - draw/update tự động xử lý tùy thuộc vào loại portal.
 - PortalManager dùng dict {portal_id: Portal} để tương thích với logic teleport cũ, đồng thời vẫn hỗ trợ vòng lặp cho hiệu ứng Arena.
"""


class Portal:
    def __init__(
        self,
        # Teleport (Tiled) params
        obj_id=None,
        x=0,
        y=0,
        width=80,
        height=100,
        target_id=None,
        tile_img=None,
        cooldown_ms=1000,
        lockout_ms=0,
        spawn_offset_x=0,
        spawn_offset_y=0,
        require_interact=False,
        # Arena params
        portal_id=None,
        destination=None,
    ):
        # Unified ID (giữ tương thích với code cũ: app.py dùng obj_id & portal.id)
        self.id = obj_id if obj_id is not None else portal_id

        # Position & size
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rect = pygame.Rect(x, y, width, height)

        # Teleport network
        self.target_id = target_id
        self.spawn_offset_x = spawn_offset_x
        self.spawn_offset_y = spawn_offset_y
        self.cooldown_ms = cooldown_ms
        self.last_teleport_time = 0
        self.lockout_ms = lockout_ms
        self.require_interact = require_interact
        self.tile_img = tile_img

        # Arena info (optional)
        self.portal_id = portal_id  # Giữ nguyên cho logging nếu cần
        self.destination = destination  # dict hoặc None

        # Visual / effect state (chỉ dùng cho Arena portal)
        self.animation_timer = 0.0
        self.particles = []
        self.glow_alpha = 0
        self.glow_direction = 5
        self.active = True  # Cho phép disable portal
        self.player_near = False
        self.interaction_range = 100  # Khoảng cách để hiển thị prompt

    # =============================
    # Teleport logic
    # =============================
    def can_teleport(self):
        if self.target_id is None:
            return False  # Không phải portal teleport
        current_time = time.time() * 1000
        return (current_time - self.last_teleport_time) >= self.cooldown_ms

    def activate_cooldown(self):
        self.last_teleport_time = time.time() * 1000

    def check_collision_rect(self, player_rect):
        return self.rect.colliderect(player_rect)

    # Arena style collision (player object)
    def check_collision(self, player):
        if not self.active:
            return False
        if player is None:
            return False
        if hasattr(player, 'rect'):
            return self.rect.colliderect(player.rect)
        return False

    # =============================
    # Arena visual update
    # =============================
    def update(self, dt, player):
        if self.destination is None:
            return  # Không phải Arena portal

        self.animation_timer += dt

        # Glow effect pulsate
        self.glow_alpha += self.glow_direction
        if self.glow_alpha >= 255:
            self.glow_alpha = 255
            self.glow_direction = -5
        elif self.glow_alpha <= 100:
            self.glow_alpha = 100
            self.glow_direction = 5

        # Player proximity
        if player and hasattr(player, 'rect'):
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            dist_sq = dx * dx + dy * dy
            self.player_near = dist_sq < (self.interaction_range ** 2)

        # Particle update
        for particle in self.particles[:]:
            particle['lifetime'] -= dt
            particle['y'] -= particle['speed'] * dt
            particle['x'] += math.sin(particle['y'] * 0.1) * particle['wave_speed'] * dt
            if particle['lifetime'] <= 0:
                self.particles.remove(particle)

        # Spawn new particles (limit)
        if len(self.particles) < 30:
            import random
            self.particles.append({
                'x': self.rect.centerx + random.uniform(-self.width // 2, self.width // 2),
                'y': self.rect.bottom,
                'speed': random.uniform(30, 60),
                'wave_speed': random.uniform(10, 30),
                'lifetime': random.uniform(1.5, 3.0),
                'max_lifetime': random.uniform(1.5, 3.0),
                'size': random.randint(2, 4),
                'color': random.choice([
                    (100, 200, 255),
                    (150, 150, 255),
                    (200, 150, 255),
                ])
            })

    # =============================
    # Drawing
    # =============================
    def draw(self, surface, camera_x, camera_y):
        # Teleport portal with static tile
        if self.destination is None:
            if self.tile_img:
                draw_x = self.x - camera_x
                draw_y = self.y - camera_y
                surface.blit(self.tile_img, (draw_x, draw_y))
            else:
                s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                s.fill((0, 150, 255, 100))
                surface.blit(s, (self.x - camera_x, self.y - camera_y))
            return

        # Arena portal visual effects
        if not self.active:
            return
        screen_x = int(self.rect.x - camera_x)
        screen_y = int(self.rect.y - camera_y)
        try:
            # Particles
            for p in self.particles:
                life_pct = p['lifetime'] / p['max_lifetime']
                alpha = int(255 * life_pct)
                color = (*p['color'], alpha)
                px = int(p['x'] - camera_x)
                py = int(p['y'] - camera_y)
                particle_surf = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
                pygame.draw.circle(particle_surf, color, (p['size'], p['size']), p['size'])
                surface.blit(particle_surf, (px - p['size'], py - p['size']))

            # Glow layers
            glow_colors = [
                (50, 100, 255, self.glow_alpha // 3),
                (100, 150, 255, self.glow_alpha // 2),
                (150, 200, 255, self.glow_alpha),
            ]
            for i, color in enumerate(glow_colors):
                radius = int(self.width // 2 + 10 + i * 5)
                glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, color, (radius, radius), radius, 3)
                surface.blit(glow_surf, (screen_x + self.width // 2 - radius, screen_y + self.height // 2 - radius))

            # Frame
            frame_color = (100, 200, 255)
            pygame.draw.rect(surface, frame_color, (screen_x, screen_y, self.width, self.height), 3)
            inner_rect = pygame.Rect(screen_x + 5, screen_y + 5, self.width - 10, self.height - 10)
            pygame.draw.rect(surface, (150, 220, 255), inner_rect, 2)

            # Interior swirl
            wave_offset = int(math.sin(self.animation_timer * 3) * 5)
            interior_surf = pygame.Surface((self.width - 10, self.height - 10), pygame.SRCALPHA)
            for i in range(5):
                alpha = int(150 - i * 25)
                wave_y = i * 15 + wave_offset
                pygame.draw.ellipse(interior_surf, (100, 180, 255, alpha), (5, wave_y, self.width - 20, 20))
            surface.blit(interior_surf, (screen_x + 5, screen_y + 5))

            # Text + prompt
            if self.player_near and self.destination:
                font = pygame.font.Font(None, 24)
                name_text = self.destination.get('name', 'Arena')
                text_surf = font.render(name_text, True, (255, 255, 255))
                text_rect = text_surf.get_rect(center=(screen_x + self.width // 2, screen_y - 30))
                shadow = font.render(name_text, True, (0, 0, 0))
                shadow_rect = shadow.get_rect(center=(screen_x + self.width // 2 + 2, screen_y - 28))
                surface.blit(shadow, shadow_rect)
                surface.blit(text_surf, text_rect)

                prompt_font = pygame.font.Font(None, 20)
                prompt_text = "Press E to Enter"
                if int(self.animation_timer * 2) % 2 == 0:
                    prompt_surf = prompt_font.render(prompt_text, True, (255, 255, 100))
                    prompt_rect = prompt_surf.get_rect(center=(screen_x + self.width // 2, screen_y + self.height + 20))
                    surface.blit(prompt_surf, prompt_rect)
        except Exception:
            pygame.draw.rect(surface, (100, 200, 255), (screen_x, screen_y, self.width, self.height), 2)

    def is_visible(self, camera_x, camera_y, camera_width, camera_height):
        return (
            self.x + self.width > camera_x
            and self.x < camera_x + camera_width
            and self.y + self.height > camera_y
            and self.y < camera_y + camera_height
        )


class PortalManager:
    def __init__(self):
        # Dict: portal_id -> Portal
        self.portals = {}
        # Player lockout (ms) sau teleport
        self.player_lockout_until = 0
        # Arena active (giữ tham chiếu nếu cần sau này)
        self.active_arena = None

    # -----------------
    # Management
    # -----------------
    def add_portal(self, portal: Portal):
        if portal.id is None:
            # Generate an ID if missing (arena portal without obj_id)
            portal.id = f"portal_{len(self.portals)+1}"
        self.portals[portal.id] = portal
        if portal.destination:
            print(f"[PORTAL] Added arena portal: {portal.destination.get('name','Arena')} ({portal.id})")

    def get_portal(self, portal_id):
        return self.portals.get(portal_id)

    # -----------------
    # Teleport collision
    # -----------------
    def is_player_locked_out(self):
        current_time = time.time() * 1000
        return current_time < self.player_lockout_until

    def check_player_collision(self, player_rect):
        if self.is_player_locked_out():
            return None
        for portal in self.portals.values():
            if portal.target_id is None:  # Skip non-teleport portals
                continue
            if portal.check_collision_rect(player_rect) and portal.can_teleport():
                return portal
        return None

    def teleport_player(self, player, portal: Portal):
        if portal.target_id is None:
            return False
        target_portal = self.get_portal(portal.target_id)
        if not target_portal:
            print(f"[Portal] Không tìm thấy portal đích với ID {portal.target_id}")
            return False

        spawn_x = target_portal.x + target_portal.spawn_offset_x
        spawn_y = target_portal.y + target_portal.spawn_offset_y
        try:
            player.rect.x = int(spawn_x)
            player.rect.y = int(spawn_y)
        except Exception:
            pass

        portal.activate_cooldown()
        target_portal.activate_cooldown()

        if portal.lockout_ms > 0:
            current_time = time.time() * 1000
            self.player_lockout_until = current_time + portal.lockout_ms
            print(f"[Portal] Player bị khóa portal trong {portal.lockout_ms}ms")

        print(f"[Portal] Teleport từ portal {portal.id} sang portal {target_portal.id}")
        return True

    # -----------------
    # Arena helpers
    # -----------------
    def create_default_portals(self):
        # Ví dụ 1 portal arena mặc định (giữ nguyên logic cũ)
        arena_portal = Portal(
            x=1500,
            y=9100,
            portal_id="arena_1",
            destination={
                'name': 'Arena 1: First Challenge',
                'enemies': ['Golem_02', 'Golem_03', 'minotaur_01', 'Wraith_01'],
                'enemy_count': 5,
                'boss': 'Troll1',
                'spawn_center': (2649, 9200),
            },
        )
        self.add_portal(arena_portal)
        return list(self.portals.values())

    def update(self, dt, player):
        for p in self.portals.values():
            p.update(dt, player)

    def check_portal_interaction(self, player, key_pressed):
        if not key_pressed:
            return None
        for p in self.portals.values():
            if p.destination and p.active and p.player_near and p.check_collision(player):
                print(f"[PORTAL] Player entering: {p.destination.get('name','Arena')}")
                return p
        return None

    # -----------------
    # Drawing
    # -----------------
    def draw(self, surface, camera_x, camera_y, camera_width=None, camera_height=None):
        for portal in self.portals.values():
            # Nếu có thông tin camera width/height thì có thể lọc visibility cho teleport portal
            if camera_width is not None and camera_height is not None:
                if not portal.is_visible(camera_x, camera_y, camera_width, camera_height):
                    continue
            portal.draw(surface, camera_x, camera_y)


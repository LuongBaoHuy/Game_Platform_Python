# game/portal.py
"""
Portal System - Cổng dịch chuyển đến các khu vực chiến đấu
"""
import pygame
import math


class Portal:
    """Cổng dịch chuyển đến khu vực chiến đấu"""
    
    def __init__(self, x, y, portal_id, destination, width=80, height=100):
        """
        Args:
            x, y: Vị trí portal
            portal_id: ID của portal (ví dụ: "portal_1", "portal_2")
            destination: Dict chứa thông tin đích đến
                {
                    'name': 'Arena 1',
                    'enemies': ['Golem_02', 'Golem_03', 'minotaur_01'],
                    'enemy_count': 5,
                    'boss': 'Troll1',
                    'spawn_center': (x, y)
                }
        """
        self.portal_id = portal_id
        self.destination = destination
        self.width = width
        self.height = height
        
        # Rect cho collision
        self.rect = pygame.Rect(x, y, width, height)
        
        # Visual effects
        self.animation_timer = 0.0
        self.particles = []
        self.glow_alpha = 0
        self.glow_direction = 5
        
        # State
        self.active = True  # Portal có hoạt động không
        self.player_near = False
        self.interaction_range = 100  # Khoảng cách để hiển thị prompt
        
    def update(self, dt, player):
        """Update portal animation và check player proximity"""
        self.animation_timer += dt
        
        # Update glow effect
        self.glow_alpha += self.glow_direction
        if self.glow_alpha >= 255:
            self.glow_alpha = 255
            self.glow_direction = -5
        elif self.glow_alpha <= 100:
            self.glow_alpha = 100
            self.glow_direction = 5
        
        # Check if player is near
        if player and hasattr(player, 'rect'):
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            distance = math.sqrt(dx * dx + dy * dy)
            
            self.player_near = distance < self.interaction_range
        
        # Update particles
        for particle in self.particles[:]:
            particle['lifetime'] -= dt
            particle['y'] -= particle['speed'] * dt
            particle['x'] += math.sin(particle['y'] * 0.1) * particle['wave_speed'] * dt
            
            if particle['lifetime'] <= 0:
                self.particles.remove(particle)
        
        # Spawn new particles
        if len(self.particles) < 30:
            import random
            self.particles.append({
                'x': self.rect.centerx + random.uniform(-self.width//2, self.width//2),
                'y': self.rect.bottom,
                'speed': random.uniform(30, 60),
                'wave_speed': random.uniform(10, 30),
                'lifetime': random.uniform(1.5, 3.0),
                'max_lifetime': random.uniform(1.5, 3.0),
                'size': random.randint(2, 4),
                'color': random.choice([
                    (100, 200, 255),  # Blue
                    (150, 150, 255),  # Purple
                    (200, 150, 255),  # Light purple
                ])
            })
    
    def check_collision(self, player):
        """Check if player is touching the portal"""
        if not self.active:
            return False
        
        if player and hasattr(player, 'rect'):
            return self.rect.colliderect(player.rect)
        
        return False
    
    def draw(self, surface, camera_x, camera_y):
        """Draw portal with visual effects"""
        if not self.active:
            return
        
        screen_x = int(self.rect.x - camera_x)
        screen_y = int(self.rect.y - camera_y)
        
        try:
            # 1. Draw particles (background)
            for particle in self.particles:
                life_percent = particle['lifetime'] / particle['max_lifetime']
                alpha = int(255 * life_percent)
                color = (*particle['color'], alpha)
                
                px = int(particle['x'] - camera_x)
                py = int(particle['y'] - camera_y)
                
                if hasattr(pygame, 'SRCALPHA'):
                    particle_surf = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)
                    pygame.draw.circle(particle_surf, color, (particle['size'], particle['size']), particle['size'])
                    surface.blit(particle_surf, (px - particle['size'], py - particle['size']))
            
            # 2. Draw portal glow (multiple layers)
            glow_colors = [
                (50, 100, 255, self.glow_alpha // 3),
                (100, 150, 255, self.glow_alpha // 2),
                (150, 200, 255, self.glow_alpha),
            ]
            
            for i, color in enumerate(glow_colors):
                radius = int(self.width // 2 + 10 + i * 5)
                if hasattr(pygame, 'SRCALPHA'):
                    glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, color, (radius, radius), radius, 3)
                    surface.blit(glow_surf, 
                               (screen_x + self.width//2 - radius, 
                                screen_y + self.height//2 - radius))
            
            # 3. Draw portal frame
            frame_color = (100, 200, 255)
            pygame.draw.rect(surface, frame_color, 
                           (screen_x, screen_y, self.width, self.height), 3)
            
            # Inner frame
            inner_rect = pygame.Rect(screen_x + 5, screen_y + 5, 
                                    self.width - 10, self.height - 10)
            pygame.draw.rect(surface, (150, 220, 255), inner_rect, 2)
            
            # 4. Draw portal interior (swirling effect)
            wave_offset = int(math.sin(self.animation_timer * 3) * 5)
            interior_color = (80, 150, 255, 150)
            
            if hasattr(pygame, 'SRCALPHA'):
                interior_surf = pygame.Surface((self.width - 10, self.height - 10), pygame.SRCALPHA)
                for i in range(5):
                    alpha = int(150 - i * 25)
                    wave_y = i * 15 + wave_offset
                    pygame.draw.ellipse(interior_surf, (100, 180, 255, alpha),
                                      (5, wave_y, self.width - 20, 20))
                surface.blit(interior_surf, (screen_x + 5, screen_y + 5))
            
            # 5. Draw destination name
            if self.player_near:
                font = pygame.font.Font(None, 24)
                name_text = self.destination['name']
                text_surf = font.render(name_text, True, (255, 255, 255))
                text_rect = text_surf.get_rect(center=(screen_x + self.width//2, screen_y - 30))
                
                # Shadow
                shadow_surf = font.render(name_text, True, (0, 0, 0))
                shadow_rect = shadow_surf.get_rect(center=(screen_x + self.width//2 + 2, screen_y - 28))
                surface.blit(shadow_surf, shadow_rect)
                surface.blit(text_surf, text_rect)
                
                # Prompt
                prompt_font = pygame.font.Font(None, 20)
                prompt_text = "Press E to Enter"
                prompt_surf = prompt_font.render(prompt_text, True, (255, 255, 100))
                prompt_rect = prompt_surf.get_rect(center=(screen_x + self.width//2, screen_y + self.height + 20))
                
                # Blinking effect
                if int(self.animation_timer * 2) % 2 == 0:
                    surface.blit(prompt_surf, prompt_rect)
            
        except Exception as e:
            # Fallback: Simple rect
            pygame.draw.rect(surface, (100, 200, 255), 
                           (screen_x, screen_y, self.width, self.height), 2)


class PortalManager:
    """Quản lý tất cả các portal trong game"""
    
    def __init__(self):
        self.portals = []
        self.active_arena = None  # Arena hiện tại player đang ở
    
    def add_portal(self, portal):
        """Thêm portal vào danh sách"""
        self.portals.append(portal)
        print(f"[PORTAL] Added portal: {portal.destination['name']} at ({portal.rect.x}, {portal.rect.y})")
    
    def create_default_portals(self):
        """Tạo các portal mặc định"""
        # Portal 1: Arena đầu tiên (5 enemies + boss)
        portal_1 = Portal(
            x=1500,  # Gần player spawn
            y=9100,
            portal_id="arena_1",
            destination={
                'name': 'Arena 1: First Challenge',
                'enemies': ['Golem_02', 'Golem_03', 'minotaur_01', 'Wraith_01'],
                'enemy_count': 5,
                'boss': 'Troll1',
                'spawn_center': (2649, 9200)
            }
        )
        self.add_portal(portal_1)
        
        return self.portals
    
    def update(self, dt, player):
        """Update tất cả portals"""
        for portal in self.portals:
            if portal.active:
                portal.update(dt, player)
    
    def check_portal_interaction(self, player, key_pressed):
        """Check xem player có tương tác với portal không"""
        if not key_pressed:
            return None
        
        for portal in self.portals:
            if portal.active and portal.player_near and portal.check_collision(player):
                print(f"[PORTAL] Player entering: {portal.destination['name']}")
                return portal
        
        return None
    
    def draw(self, surface, camera_x, camera_y):
        """Vẽ tất cả portals"""
        for portal in self.portals:
            if portal.active:
                portal.draw(surface, camera_x, camera_y)

import pygame
import time


class Portal:
    """
    Cổng dịch chuyển (Portal) - dùng để teleport player từ cổng này sang cổng khác.
    
    Properties từ Tiled:
    - target: ID của portal đích (bắt buộc)
    - cooldown_ms: Thời gian cooldown trước khi có thể dùng lại portal (mặc định 1000ms)
    - lockout_ms: Thời gian khóa player không cho dùng BẤT KỲ portal nào sau khi teleport (mặc định 0 = không khóa)
    - spawn_offset_x: Offset X khi spawn tại portal đích (mặc định 0)
    - spawn_offset_y: Offset Y khi spawn tại portal đích (mặc định 0)
    - interact: Nếu có property này, cần nhấn phím để kích hoạt portal (chưa implement)
    """
    def __init__(self, obj_id, x, y, width, height, target_id, tile_img=None, 
                 cooldown_ms=1000, lockout_ms=0, spawn_offset_x=0, spawn_offset_y=0, 
                 require_interact=False):
        self.id = obj_id
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rect = pygame.Rect(x, y, width, height)
        
        # Target portal ID
        self.target_id = target_id
        
        # Offset khi spawn tại portal đích
        self.spawn_offset_x = spawn_offset_x
        self.spawn_offset_y = spawn_offset_y
        
        # Cooldown cho portal này
        self.cooldown_ms = cooldown_ms
        self.last_teleport_time = 0
        
        # Lockout time cho player (thời gian khóa player không cho dùng portal nào)
        self.lockout_ms = lockout_ms
        
        # Có cần nhấn phím để kích hoạt không
        self.require_interact = require_interact
        
        # Hình ảnh để vẽ portal (nếu có tile)
        self.tile_img = tile_img
    
    def can_teleport(self):
        """Kiểm tra xem portal có thể teleport không (đã hết cooldown chưa)."""
        current_time = time.time() * 1000  # Convert to milliseconds
        return (current_time - self.last_teleport_time) >= self.cooldown_ms
    
    def activate_cooldown(self):
        """Kích hoạt cooldown sau khi teleport."""
        self.last_teleport_time = time.time() * 1000
    
    def check_collision(self, player_rect):
        """Kiểm tra xem player có chạm vào portal không."""
        return self.rect.colliderect(player_rect)
    
    def draw(self, surface, camera_x, camera_y):
        """Vẽ portal lên màn hình."""
        if self.tile_img:
            draw_x = self.x - camera_x
            draw_y = self.y - camera_y
            surface.blit(self.tile_img, (draw_x, draw_y))
        else:
            # Nếu không có tile, vẽ rect màu xanh dương trong suốt
            s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            s.fill((0, 150, 255, 100))  # Màu xanh dương trong suốt
            draw_x = self.x - camera_x
            draw_y = self.y - camera_y
            surface.blit(s, (draw_x, draw_y))
    
    def is_visible(self, camera_x, camera_y, camera_width, camera_height):
        """Kiểm tra xem portal có trong tầm nhìn camera không."""
        return (self.x + self.width > camera_x and 
                self.x < camera_x + camera_width and
                self.y + self.height > camera_y and 
                self.y < camera_y + camera_height)


class PortalManager:
    """
    Quản lý tất cả các portal trong game.
    Cũng quản lý lockout time của player để tránh spam portal.
    """
    def __init__(self):
        self.portals = {}  # Dict: portal_id -> Portal object
        self.player_lockout_until = 0  # Thời gian (ms) player bị khóa không cho dùng portal
    
    def add_portal(self, portal):
        """Thêm portal vào manager."""
        self.portals[portal.id] = portal
    
    def get_portal(self, portal_id):
        """Lấy portal theo ID."""
        return self.portals.get(portal_id)
    
    def is_player_locked_out(self):
        """Kiểm tra xem player có đang bị lockout không."""
        current_time = time.time() * 1000
        return current_time < self.player_lockout_until
    
    def check_player_collision(self, player_rect):
        """
        Kiểm tra player có chạm vào portal nào không.
        Trả về portal nếu có và đã hết cooldown + player không bị lockout, None nếu không.
        """
        # Nếu player đang bị lockout, không cho dùng portal nào cả
        if self.is_player_locked_out():
            return None
        
        for portal in self.portals.values():
            if portal.check_collision(player_rect) and portal.can_teleport():
                return portal
        return None
    
    def teleport_player(self, player, portal):
        """
        Dịch chuyển player từ portal này sang portal đích.
        
        Returns:
            True nếu teleport thành công, False nếu thất bại.
        """
        target_portal = self.get_portal(portal.target_id)
        
        if not target_portal:
            print(f"[Portal] Không tìm thấy portal đích với ID {portal.target_id}")
            return False
        
        # Tính vị trí spawn tại portal đích
        spawn_x = target_portal.x + target_portal.spawn_offset_x
        spawn_y = target_portal.y + target_portal.spawn_offset_y
        
        # Di chuyển player đến vị trí mới
        player.rect.x = int(spawn_x)
        player.rect.y = int(spawn_y)
        
        # Kích hoạt cooldown cho CẢ HAI portal (tránh teleport ngay lại)
        portal.activate_cooldown()
        target_portal.activate_cooldown()
        
        # Kích hoạt lockout cho player nếu portal có lockout_ms
        if portal.lockout_ms > 0:
            current_time = time.time() * 1000
            self.player_lockout_until = current_time + portal.lockout_ms
            print(f"[Portal] Player bị khóa portal trong {portal.lockout_ms}ms")
        
        print(f"[Portal] Teleport từ portal {portal.id} sang portal {target_portal.id}")
        return True
    
    def draw(self, surface, camera_x, camera_y, camera_width, camera_height):
        """Vẽ tất cả portal visible."""
        for portal in self.portals.values():
            if portal.is_visible(camera_x, camera_y, camera_width, camera_height):
                portal.draw(surface, camera_x, camera_y)

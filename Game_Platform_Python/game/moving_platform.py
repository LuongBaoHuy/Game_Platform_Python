import pygame
import math


class MovingPlatformWrapper:
    """
    Wrapper để MovingPlatform tương thích với code collision hiện tại.
    Có các attributes giống Rect (top, bottom, left, right) và thêm velocity.
    """
    def __init__(self, platform):
        self.platform = platform
        self.rect = platform.rect
        
    def __getattr__(self, name):
        # Chuyển tiếp các attributes sang rect
        return getattr(self.rect, name)
    
    def colliderect(self, other):
        return self.rect.colliderect(other)
    
    @property
    def vel_x(self):
        return self.platform.vel_x
    
    @property
    def vel_y(self):
        return self.platform.vel_y


class MovingPlatform:
    """
    Class cho platform di chuyển (bay lên-xuống hoặc trái-phải).
    Hỗ trợ animation và collision với player.
    """
    
    def __init__(self, obj_data, use_bottom_y=False, y_offset=0):
        """
        Khởi tạo moving platform từ object data.
        
        Args:
            obj_data: Dictionary chứa thông tin object từ map_loader
            use_bottom_y: Có dùng y coordinate là bottom của image không
            y_offset: Offset bổ sung cho Y position
        """
        # Vị trí gốc (anchor)
        self.start_x = int(obj_data.get('x', 0))
        self.start_y = int(obj_data.get('y', 0))
        self.width = int(obj_data.get('width', 0))
        self.height = int(obj_data.get('height', 0))
        
        # Lấy properties từ Tiled
        props = obj_data.get('properties', {})
        
        # Motion properties
        self.motion_type = props.get('motion', 'bob')  # bob, horizontal, vertical, circle
        self.axis = props.get('axis', 'y')  # x hoặc y
        self.amplitude = int(props.get('amp', 12))  # biên độ (pixels)
        self.period_ms = int(props.get('period_ms', 1800))  # chu kỳ (milliseconds)
        
        # Animation frames
        self.animation_frames = obj_data.get('animation_frames', [])
        self.current_frame_index = 0
        self.animation_timer = 0  # milliseconds
        
        # Timer cho chuyển động
        self.motion_timer = 0  # milliseconds
        
        # Current position
        self.x = self.start_x
        self.y = self.start_y
        
        # Align Y position nếu cần
        if self.animation_frames:
            first_frame = self.animation_frames[0]['image']
            tw, th = first_frame.get_width(), first_frame.get_height()
            
            if use_bottom_y:
                self.start_y = self.start_y - th
                self.y = self.start_y
            
            self.start_y += int(y_offset)
            self.y = self.start_y
            
            # Tạo rect cho collision
            self.rect = pygame.Rect(self.x, self.y, tw, th)
        elif obj_data.get('tile'):
            # Nếu không có animation nhưng có tile tĩnh
            tile = obj_data.get('tile')
            tw, th = tile.get_width(), tile.get_height()
            
            if use_bottom_y:
                self.start_y = self.start_y - th
                self.y = self.start_y
            
            self.start_y += int(y_offset)
            self.y = self.start_y
            
            self.rect = pygame.Rect(self.x, self.y, tw, th)
            self.static_tile = tile
        else:
            # Fallback: dùng width/height từ object
            self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
            self.static_tile = None
        
        # Velocity để player có thể "đứng" trên platform di chuyển
        self.vel_x = 0
        self.vel_y = 0
        self.last_x = self.x
        self.last_y = self.y
    
    def update(self, dt):
        """
        Cập nhật vị trí và animation.
        
        Args:
            dt: Delta time in seconds
        """
        dt_ms = dt * 1000
        
        # Lưu vị trí cũ để tính velocity
        self.last_x = self.x
        self.last_y = self.y
        
        # Cập nhật motion timer
        self.motion_timer += dt_ms
        
        # Tính vị trí mới dựa trên motion type
        if self.motion_type == 'bob':
            # Dao động lên-xuống hoặc trái-phải theo sin wave
            # progress trong [0, 1] sau mỗi chu kỳ
            progress = (self.motion_timer % self.period_ms) / self.period_ms
            # sin wave: -1 to 1
            wave = math.sin(progress * 2 * math.pi)
            offset = wave * self.amplitude
            
            if self.axis == 'y':
                self.y = self.start_y + offset
            elif self.axis == 'x':
                self.x = self.start_x + offset
        
        elif self.motion_type == 'vertical':
            # Di chuyển lên-xuống tuyến tính
            progress = (self.motion_timer % self.period_ms) / self.period_ms
            if progress < 0.5:
                # Đi xuống
                offset = (progress * 2) * self.amplitude
            else:
                # Đi lên
                offset = ((1 - progress) * 2) * self.amplitude
            self.y = self.start_y + offset
        
        elif self.motion_type == 'horizontal':
            # Di chuyển trái-phải tuyến tính
            progress = (self.motion_timer % self.period_ms) / self.period_ms
            if progress < 0.5:
                offset = (progress * 2) * self.amplitude
            else:
                offset = ((1 - progress) * 2) * self.amplitude
            self.x = self.start_x + offset
        
        # Cập nhật rect position
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
        
        # Tính delta position thực tế (pixel di chuyển trong frame này)
        # Đây là giá trị để player di chuyển theo, không phải velocity
        self.vel_x = self.x - self.last_x
        self.vel_y = self.y - self.last_y
        
        # Cập nhật animation nếu có
        if self.animation_frames:
            self.animation_timer += dt_ms
            current_frame = self.animation_frames[self.current_frame_index]
            frame_duration = current_frame['duration']
            
            while self.animation_timer >= frame_duration:
                self.animation_timer -= frame_duration
                self.current_frame_index = (self.current_frame_index + 1) % len(self.animation_frames)
                current_frame = self.animation_frames[self.current_frame_index]
                frame_duration = current_frame['duration']
    
    def draw(self, surface, camera_x, camera_y):
        """
        Vẽ platform lên surface.
        
        Args:
            surface: Pygame surface để vẽ
            camera_x: Camera X position
            camera_y: Camera Y position
        """
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y)
        
        if self.animation_frames:
            # Vẽ frame hiện tại
            current_frame = self.animation_frames[self.current_frame_index]
            image = current_frame['image']
            surface.blit(image, (screen_x, screen_y))
        elif hasattr(self, 'static_tile') and self.static_tile:
            # Vẽ tile tĩnh
            surface.blit(self.static_tile, (screen_x, screen_y))
        else:
            # Debug: vẽ hình chữ nhật nếu không có image
            debug_rect = pygame.Rect(screen_x, screen_y, self.rect.width, self.rect.height)
            pygame.draw.rect(surface, (100, 100, 200), debug_rect)
    
    def is_visible(self, camera_x, camera_y, camera_width, camera_height):
        """
        Kiểm tra platform có trong camera không.
        
        Returns:
            True nếu visible
        """
        camera_rect = pygame.Rect(camera_x, camera_y, camera_width, camera_height)
        return self.rect.colliderect(camera_rect)


class MovingPlatformManager:
    """
    Quản lý tất cả moving platforms trong map.
    """
    
    def __init__(self, moving_objects, use_bottom_y=False, y_offset=0):
        """
        Khởi tạo manager.
        
        Args:
            moving_objects: List các object dict từ map_loader
            use_bottom_y: Có dùng y coordinate là bottom không
            y_offset: Offset bổ sung cho Y
        """
        self.platforms = []
        
        for obj_data in moving_objects:
            platform = MovingPlatform(obj_data, use_bottom_y, y_offset)
            self.platforms.append(platform)
    
    def update(self, dt):
        """Cập nhật tất cả platforms."""
        for platform in self.platforms:
            platform.update(dt)
    
    def draw(self, surface, camera_x, camera_y, camera_width, camera_height):
        """Vẽ tất cả platforms visible."""
        for platform in self.platforms:
            if platform.is_visible(camera_x, camera_y, camera_width, camera_height):
                platform.draw(surface, camera_x, camera_y)
    
    def get_platforms_for_collision(self):
        """
        Trả về list các tuple (tile_image, wrapper) để check collision.
        Wrapper có cả rect attributes và velocity properties.
        """
        result = []
        for p in self.platforms:
            # Lấy tile image hiện tại (nếu có animation) hoặc static tile
            if p.animation_frames:
                tile_img = p.animation_frames[p.current_frame_index]['image']
            elif hasattr(p, 'static_tile') and p.static_tile:
                tile_img = p.static_tile
            else:
                # Tạo surface tạm nếu không có image
                tile_img = pygame.Surface((p.rect.width, p.rect.height))
                tile_img.fill((100, 100, 200))
            
            # Trả về wrapper thay vì rect trực tiếp
            wrapper = MovingPlatformWrapper(p)
            result.append((tile_img, wrapper))
        
        return result

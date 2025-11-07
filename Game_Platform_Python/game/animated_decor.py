import pygame


class AnimatedDecor:
    """
    Class để quản lý các decoration có animation từ Tiled.
    Tự động chuyển frame theo thời gian dựa trên animation data từ TMX.
    """
    
    def __init__(self, obj_data, use_bottom_y=False, y_offset=0):
        """
        Khởi tạo animated decoration từ object data.
        
        Args:
            obj_data: Dictionary chứa thông tin object từ map_loader
            use_bottom_y: Có dùng y coordinate là bottom của image không
            y_offset: Offset bổ sung cho Y position
        """
        self.x = int(obj_data.get('x', 0))
        self.y = int(obj_data.get('y', 0))
        self.width = int(obj_data.get('width', 0))
        self.height = int(obj_data.get('height', 0))
        self.name = obj_data.get('name', '')
        
        # Animation data
        self.animation_frames = obj_data.get('animation_frames', [])
        self.current_frame_index = 0
        self.animation_timer = 0  # milliseconds
        
        # Align Y position
        if self.animation_frames:
            first_frame = self.animation_frames[0]['image']
            tw, th = first_frame.get_width(), first_frame.get_height()
            
            if use_bottom_y:
                self.y_aligned = self.y - th
            else:
                self.y_aligned = self.y
            self.y_aligned += int(y_offset)
        else:
            self.y_aligned = self.y
    
    def update(self, dt):
        """
        Cập nhật animation frame.
        
        Args:
            dt: Delta time in seconds
        """
        if not self.animation_frames:
            return
        
        # Convert dt to milliseconds
        dt_ms = dt * 1000
        self.animation_timer += dt_ms
        
        # Get current frame duration
        current_frame = self.animation_frames[self.current_frame_index]
        frame_duration = current_frame['duration']
        
        # Check if we should advance to next frame
        while self.animation_timer >= frame_duration:
            self.animation_timer -= frame_duration
            self.current_frame_index = (self.current_frame_index + 1) % len(self.animation_frames)
            
            # Update frame duration for next frame
            current_frame = self.animation_frames[self.current_frame_index]
            frame_duration = current_frame['duration']
    
    def draw(self, surface, camera_x, camera_y):
        """
        Vẽ animated decoration lên surface.
        
        Args:
            surface: Pygame surface để vẽ
            camera_x: Camera X position
            camera_y: Camera Y position
        """
        if not self.animation_frames:
            return
        
        # Get current frame image
        current_frame = self.animation_frames[self.current_frame_index]
        image = current_frame['image']
        
        # Calculate screen position (offset by camera)
        screen_x = self.x - camera_x
        screen_y = self.y_aligned - camera_y
        
        # Draw the image
        surface.blit(image, (screen_x, screen_y))
    
    def is_visible(self, camera_x, camera_y, camera_width, camera_height):
        """
        Kiểm tra xem decoration có trong vùng camera không.
        
        Returns:
            True nếu visible, False nếu không
        """
        if not self.animation_frames:
            return False
        
        # Get image dimensions from first frame
        first_frame = self.animation_frames[0]['image']
        tw, th = first_frame.get_width(), first_frame.get_height()
        
        # Build rect in world coordinates
        obj_rect = pygame.Rect(self.x, self.y_aligned, tw, th)
        camera_rect = pygame.Rect(camera_x, camera_y, camera_width, camera_height)
        
        return obj_rect.colliderect(camera_rect)


class AnimatedDecorManager:
    """
    Quản lý tất cả animated decorations trong map.
    """
    
    def __init__(self, animated_objects, use_bottom_y=False, y_offset=0):
        """
        Khởi tạo manager với list animated objects.
        
        Args:
            animated_objects: List các object dict từ map_loader
            use_bottom_y: Có dùng y coordinate là bottom của image không
            y_offset: Offset bổ sung cho Y position
        """
        self.decorations = []
        
        for obj_data in animated_objects:
            decor = AnimatedDecor(obj_data, use_bottom_y, y_offset)
            if decor.animation_frames:  # Only add if has animation
                self.decorations.append(decor)
    
    def update(self, dt):
        """
        Cập nhật tất cả decorations.
        
        Args:
            dt: Delta time in seconds
        """
        for decor in self.decorations:
            decor.update(dt)
    
    def draw(self, surface, camera_x, camera_y, camera_width, camera_height):
        """
        Vẽ tất cả decorations visible trong camera.
        
        Args:
            surface: Pygame surface để vẽ
            camera_x: Camera X position
            camera_y: Camera Y position
            camera_width: Camera width
            camera_height: Camera height
        """
        for decor in self.decorations:
            if decor.is_visible(camera_x, camera_y, camera_width, camera_height):
                decor.draw(surface, camera_x, camera_y)

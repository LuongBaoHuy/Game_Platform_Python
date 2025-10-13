import pygame
import os
from game.config import PLAYER_SCALE, GRAVITY


def load_frames_simple(folder, size):
    """Tải các khung hình giống player: trả về danh sách (surface, bottom_trim)."""
    frames = []
    if not os.path.isdir(folder):
        return frames
    for filename in sorted(os.listdir(folder)):
        if filename.lower().endswith('.png'):
            img = pygame.image.load(os.path.join(folder, filename)).convert_alpha()
            img = pygame.transform.scale(img, size)
            # tính phần trong suốt ở đáy ảnh (bottom transparent trim)
            h = img.get_height()
            bottom_trim = 0
            for y in range(h - 1, -1, -1):
                row_has_pixel = False
                for x in range(img.get_width()):
                    if img.get_at((x, y))[3] != 0:
                        row_has_pixel = True
                        break
                if row_has_pixel:
                    bottom_trim = h - 1 - y
                    break
            frames.append((img, bottom_trim))
    return frames


class PatrolEnemy:
    def __init__(self, x, y, folder_base=None, patrol_range=300, speed=100):
        # x,y là toạ độ thế giới cho midbottom của sprite
        # Dùng cùng kích thước sprite như Player để căn chỉnh giống nhau
        size = (int(512 * PLAYER_SCALE), int(512 * PLAYER_SCALE))
        if folder_base is None:
            folder_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Goblem', 'Golem_01', 'PNG Sequences'))

        self.animations = {
            'idle': load_frames_simple(os.path.join(folder_base, 'Idle'), size),
            'walk': load_frames_simple(os.path.join(folder_base, 'Walking'), size),
            'attack': load_frames_simple(os.path.join(folder_base, 'Attacking'), size),
        }

        # Đặt hitbox giống Player để nhất quán
        rect_w = int(120 * PLAYER_SCALE)
        rect_h = int(240 * PLAYER_SCALE)
        self.rect = pygame.Rect(0, 0, rect_w, rect_h)
        # x,y là midbottom thế giới
        self.rect.midbottom = (x, y)
        # vận tốc theo trục y (gravity)
        self.vel_y = 0
        self.on_ground = False

        # trạng thái
        self.state = 'idle'
        self.current_frame = 0
        self.anim_timer = 0.0
        self.anim_speed = 0.12  # giây cho mỗi frame

        # thiết lập tuần tra
        self.patrol_min = x - patrol_range
        self.patrol_max = x + patrol_range
        self.speed = speed  # pixel mỗi giây
        self.direction = -1

        # tấn công / chase
        self.detection_range = 400
        self.attack_range = 120
        self.attack_speed = 160
        self.attack_duration = 0.5
        self.attack_timer = 0.0

    def update(self, dt, platforms, player):
        # dt tính bằng giây
        dx = player.rect.centerx - self.rect.centerx
        dy = abs(player.rect.centery - self.rect.centery)
        prev_state = self.state
        
        # gravity (dùng hệ số GRAVITY=2 giống player)
        self.vel_y += GRAVITY  # không nhân với dt ở đây
        self.rect.y += self.vel_y  # không nhân với dt ở đây nữa

        # kiểm tra va chạm với platform
        self.on_ground = False
        for _, platform_rect in platforms:  # platforms là list các tuple (tile_img, rect)
            if self.rect.colliderect(platform_rect):
                # va chạm từ trên xuống
                if self.vel_y > 0:
                    self.rect.bottom = platform_rect.top
                    self.vel_y = 0
                    self.on_ground = True
        # AI:
        # - nếu trong detection_range -> chase (di chuyển hướng về player)
        # - nếu trong attack_range -> attack (không tiến tiếp, chơi animation)
        if abs(dx) < self.detection_range and dy < 140:
            # chase
            if abs(dx) <= self.attack_range:
                # vào tầm đánh
                self.state = 'attack'
                self.attack_timer = self.attack_duration
                # don't move further when attacking
            else:
                self.state = 'walk'
                dir_sign = 1 if dx > 0 else -1
                self.rect.x += int(self.attack_speed * dir_sign * dt)
                self.direction = 1 if dir_sign > 0 else -1
        else:
            # tuần tra khi không phát hiện player
            self.state = 'walk'
            move = self.speed * self.direction * dt
            self.rect.x += int(move)
            if self.rect.centerx < self.patrol_min:
                self.rect.centerx = int(self.patrol_min)
                self.direction = 1
            elif self.rect.centerx > self.patrol_max:
                self.rect.centerx = int(self.patrol_max)
                self.direction = -1

        # nếu trạng thái thay đổi, reset frame/timer animation
        if prev_state != self.state:
            self.current_frame = 0
            self.anim_timer = 0.0

        # cập nhật animation (dựa trên thời gian frame)
        frames = self.animations.get(self.state) or []
        if frames:
            # đảm bảo current_frame nằm trong phạm vi
            if self.current_frame >= len(frames):
                self.current_frame = 0
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.current_frame = (self.current_frame + 1) % len(frames)
                self.anim_timer = 0.0

    def draw(self, surface, camera_x, camera_y, show_hitbox: bool = False):
        frames = self.animations.get(self.state) or []
        if not frames:
            pygame.draw.rect(surface, (150, 50, 50), (self.rect.x - camera_x, self.rect.y - camera_y, self.rect.width, self.rect.height))
            if show_hitbox:
                pygame.draw.rect(surface, (255, 0, 0), (self.rect.x - camera_x, self.rect.y - camera_y, self.rect.width, self.rect.height), 2)
            return
        frame, trim = frames[self.current_frame]
        img = frame if self.direction >= 0 else pygame.transform.flip(frame, True, False)
        img_rect = img.get_rect(midbottom=(self.rect.centerx - camera_x, self.rect.bottom - camera_y + trim))
        surface.blit(img, img_rect)
        # Vẽ hitbox nếu bật
        if show_hitbox:
            pygame.draw.rect(surface, (255, 0, 0), (self.rect.x - camera_x, self.rect.y - camera_y, self.rect.width, self.rect.height), 2)

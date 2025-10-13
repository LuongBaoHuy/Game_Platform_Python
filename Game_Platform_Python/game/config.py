import os

# ===============================
# Cấu hình chung
# ===============================
WIDTH, HEIGHT = 1600, 800
FPS = 120
GRAVITY = 2
JUMP_POWER = -70
SPEED = 30
ZOOM = 0.4   # <--- 1.0 = bình thường, nhỏ hơn = nhìn xa, lớn hơn = zoom gần
PLAYER_SCALE = 1.25  # scale nhân vật (1.0 = kích thước gốc)

# Đường dẫn assets mặc định (nếu cần dùng)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

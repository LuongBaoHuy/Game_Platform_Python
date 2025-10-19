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

# Khoảng inset (px) để thu nhỏ hitbox của mỗi tile.
# Bạn có thể dùng giá trị chung `HITBOX_INSET` hoặc đặt riêng từng cạnh.
# Mặc định đặt top nhỏ xuống một chút để nhân vật trông chạm nền hơn.
# - HITBOX_INSET: nếu >0 sẽ áp dụng đều cho 4 cạnh (legacy)
# - HITBOX_TOP_INSET/HITBOX_BOTTOM_INSET/HITBOX_LEFT_INSET/HITBOX_RIGHT_INSET: áp dụng riêng
HITBOX_INSET = 0

# Thu nhỏ chỉ theo chiều dọc phía trên: tăng giá trị này nếu nhân vật trông như đang bay
HITBOX_TOP_INSET = 6
# Mặc định không thu nhỏ bottom/side (để nhân vật vẫn đứng chính xác trên nền)
HITBOX_BOTTOM_INSET = 0
HITBOX_LEFT_INSET = 0
HITBOX_RIGHT_INSET = 0

# Đường dẫn assets mặc định (nếu cần dùng)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

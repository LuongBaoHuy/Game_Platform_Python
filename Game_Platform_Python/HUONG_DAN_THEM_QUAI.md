# Hướng dẫn thêm loại quái mới vào game

## Tổng quan
Game sử dụng hệ thống "data-driven enemy" — bạn chỉ cần:
1. Đặt sprite vào thư mục `assets/characters/<ten_quai>/`
2. Tạo file `metadata.json` mô tả các animation
3. Game sẽ tự động load và spawn quái đó

## Bước 1: Chuẩn bị asset (hình ảnh quái)

### Cấu trúc thư mục
Tạo thư mục cho quái mới trong `assets/characters/`:
```
assets/characters/
  └── ten_quai_moi/           # Ví dụ: golem_02, slime, archer
      ├── metadata.json        # File cấu hình (bắt buộc)
      └── Idle/               # Các thư mục chứa PNG frames
      └── Walking/
      └── Attacking/
      └── ... (các animation khác)
```

**Lưu ý quan trọng**: 
- Tên thư mục quái nên dùng chữ thường và gạch dưới (ví dụ: `golem_02`, không nên `Golem_02`)
- Mỗi thư mục animation chứa các file PNG theo thứ tự (ví dụ: `frame_0.png`, `frame_1.png`, ...)

### Ví dụ cấu trúc thực tế
```
assets/characters/golem_02/
  ├── metadata.json
  └── PNG Sequences/
      ├── Idle/
      │   ├── frame_0.png
      │   ├── frame_1.png
      │   └── ...
      ├── Walking/
      └── Attacking/
```

## Bước 2: Tạo file metadata.json

File `metadata.json` mô tả cách load sprite cho quái. Đặt file này trong thư mục quái.

### Ví dụ metadata.json cơ bản
```json
{
  "id": "golem_02",
  "name": "Golem 02",
  "scale": 1.0,
  "frames": {
    "idle": "PNG Sequences/Idle",
    "walk": "PNG Sequences/Walking",
    "attack": "PNG Sequences/Attacking"
  },
  "skills": []
}
```

### Giải thích các trường

#### `id` (bắt buộc)
- ID duy nhất của quái, dùng để spawn trong code
- Nên dùng chữ thường, gạch dưới
- Ví dụ: `"golem_02"`, `"slime_green"`

#### `name` (tùy chọn)
- Tên hiển thị (không ảnh hưởng gameplay)

#### `scale` (tùy chọn, mặc định: 1.0)
- Tỉ lệ phóng to/nhỏ sprite
- Ví dụ: `1.5` sẽ phóng to 150%

#### `frames` (bắt buộc)
- Map tên trạng thái → đường dẫn thư mục chứa PNG
- **Đường dẫn tương đối** từ thư mục quái
- Các trạng thái cơ bản:
  - `idle`: đứng yên
  - `walk`: đi bộ
  - `attack`: tấn công
  - `jump`, `dying`, `hurt`: (tùy chọn)

**Quan trọng**: Nếu ảnh nằm trong thư mục con (như `PNG Sequences/Idle`), phải ghi đầy đủ đường dẫn tương đối:
```json
"frames": {
  "idle": "PNG Sequences/Idle",
  "walk": "PNG Sequences/Walking"
}
```

Nếu ảnh nằm trực tiếp (không có thư mục con):
```json
"frames": {
  "idle": "Idle",
  "walk": "Walking"
}
```

#### `skills` (tùy chọn)
- Danh sách kỹ năng của quái (hiện tại để trống `[]`)

## Bước 3: Spawn quái trong game

Sau khi tạo thư mục + metadata, game tự động nhận diện quái mới.

### Cách 1: Spawn ngẫu nhiên (mặc định)
Game đã được cấu hình spawn ngẫu nhiên các quái trong `assets/characters/`. Không cần chỉnh code!

File `game/app.py` tự động:
```python
enemy_ids = list_enemy_ids() or ['bluewizard', 'golem_02', 'golem_03']
eid = random.choice(enemy_ids)
enemies.append(create_enemy(eid, x, y))
```

### Cách 2: Spawn quái cụ thể
Nếu muốn spawn 1 loại quái nhất định:
```python
from game.enemy_registry import create_enemy

# Spawn golem_02 tại vị trí (1000, 2000)
enemy = create_enemy('golem_02', 1000, 2000)
enemies.append(enemy)
```

### Cách 3: Thêm quái vào registry thủ công (nâng cao)
Nếu muốn tùy chỉnh hành vi AI, tạo class con:
```python
# Trong game/enemy.py
from game.characters.data_driven_enemy import DataDrivenEnemy

class BossGolem(DataDrivenEnemy):
    def __init__(self, x, y, **kwargs):
        super().__init__(x, y, char_id='golem_boss', speed=50, **kwargs)
        self.max_hp = 500  # Boss có nhiều HP hơn
        self.attack_damage = 30

# Đăng ký
from game.enemy_registry import register_enemy
register_enemy('golem_boss', BossGolem)
```

## Bước 4: Kiểm tra và debug

### Test spawn từng quái
Chạy script kiểm tra nhanh (PowerShell):
```powershell
python - <<'PY'
from game.enemy_registry import create_enemy
ids = ['golem_02', 'golem_03']
for eid in ids:
    e = create_enemy(eid, 100, 100)
    cls = e.__class__.__name__
    anims = getattr(e, 'animations', {})
    idle_count = len(anims.get('idle', []))
    print(f"{eid} -> {cls}, idle frames: {idle_count}")
PY
```

**Kết quả mong muốn**:
```
golem_02 -> DataDrivenEnemy, idle frames: 8
golem_03 -> DataDrivenEnemy, idle frames: 8
```

Nếu thấy:
- `PatrolEnemy` thay vì `DataDrivenEnemy` → Kiểm tra lỗi syntax trong code
- `idle frames: 0` → Kiểm tra metadata và đường dẫn thư mục

### Các lỗi thường gặp

#### 1. Quái không có hình ảnh (chỉ hiện hình chữ nhật)
**Nguyên nhân**: Factory không tìm thấy PNG frames

**Cách sửa**:
- Kiểm tra đường dẫn trong `metadata.json` có khớp với cấu trúc thư mục thực tế không
- Ví dụ: nếu ảnh nằm trong `PNG Sequences/Idle`, metadata phải ghi `"idle": "PNG Sequences/Idle"`

#### 2. Tất cả quái cùng hình dạng (Golem_01)
**Nguyên nhân**: `create_enemy` đang fallback về `PatrolEnemy` vì:
- File `data_driven_enemy.py` có lỗi syntax → Không import được
- Metadata sai hoặc thiếu

**Cách sửa**:
- Chạy lệnh test ở trên để xem `create_enemy` trả về class gì
- Kiểm tra console log khi chạy game, tìm dòng `[enemy.py] Registration skipped: ...` để biết lỗi

#### 3. Lỗi "Registration skipped: unexpected indent"
**Nguyên nhân**: File Python có lỗi thụt lề

**Cách sửa**:
- Mở file `game/characters/data_driven_enemy.py`
- Đảm bảo tất cả dòng trong `__init__` đều thụt lề đúng (dùng 4 space hoặc 1 tab nhất quán)

#### 4. Console log hiển thị "factory.create_player: no frames for 'idle'"
**Nguyên nhân**: Factory thử nhiều đường dẫn nhưng không tìm thấy thư mục

**Cách sửa**:
- Đọc danh sách các đường dẫn đã thử (trong log)
- Kiểm tra thư mục có tồn tại không
- Sửa metadata để trỏ đúng

**Ví dụ log**:
```
factory.create_player: no frames for 'idle' (tried: [
  'D:\\...\\assets\\characters\\golem_02\\idle',
  'D:\\...\\assets\\characters\\golem_02\\PNG Sequences\\Idle'
])
```
→ Nếu thư mục thực tế là `PNG Sequences/Idle`, sửa metadata:
```json
"frames": { "idle": "PNG Sequences/Idle" }
```

## Ví dụ hoàn chỉnh: Thêm Slime

### 1. Tạo cấu trúc thư mục
```
assets/characters/slime_green/
  ├── metadata.json
  ├── Idle/
  │   ├── slime_idle_0.png
  │   └── slime_idle_1.png
  └── Moving/
      ├── slime_move_0.png
      └── slime_move_1.png
```

### 2. Tạo metadata.json
```json
{
  "id": "slime_green",
  "name": "Green Slime",
  "scale": 0.8,
  "frames": {
    "idle": "Idle",
    "walk": "Moving",
    "attack": "Idle"
  },
  "skills": []
}
```

### 3. Chạy game
Game tự động nhận `slime_green` và spawn ngẫu nhiên cùng các quái khác!

## Tùy chỉnh nâng cao

### Thay đổi hành vi AI
Sửa file `game/characters/data_driven_enemy.py`, phần `update()`:
- `self.detection_range`: tầm phát hiện người chơi (mặc định 400 px)
- `self.attack_range`: tầm tấn công (mặc định 120 px)
- `self.speed`: tốc độ di chuyển (mặc định 80 px/s)
- `self.attack_damage`: sát thương (mặc định 10 HP)

### Tạo class riêng cho từng loại quái
Nếu muốn mỗi loại có hành vi khác nhau:

```python
# Trong game/enemy.py
class FastSlime(DataDrivenEnemy):
    def __init__(self, x, y, **kwargs):
        super().__init__(x, y, char_id='slime_green', speed=150, **kwargs)
        self.max_hp = 30
        self.attack_damage = 5

class TankGolem(DataDrivenEnemy):
    def __init__(self, x, y, **kwargs):
        super().__init__(x, y, char_id='golem_03', speed=40, **kwargs)
        self.max_hp = 200
        self.attack_damage = 25

# Đăng ký
register_enemy('slime_green', FastSlime)
register_enemy('golem_03', TankGolem)
```

## Checklist khi thêm quái mới

- [ ] Tạo thư mục `assets/characters/<id>/`
- [ ] Đặt PNG frames vào các thư mục con (Idle, Walking, ...)
- [ ] Tạo `metadata.json` với `id`, `frames` mapping đúng
- [ ] Chạy test script để kiểm tra `create_enemy` trả về `DataDrivenEnemy`
- [ ] Kiểm tra `idle frames > 0` (có animation)
- [ ] Chạy game và xác nhận quái xuất hiện với hình đúng
- [ ] (Tùy chọn) Tạo class riêng nếu cần AI đặc biệt

## Hỗ trợ

Nếu gặp vấn đề:
1. Chạy test script kiểm tra `create_enemy`
2. Đọc console log khi khởi động game (tìm các dòng `[enemy.py]`, `[enemy_registry]`, `[app.py]`)
3. Kiểm tra cấu trúc thư mục và metadata.json
4. Đảm bảo không có lỗi thụt lề trong file Python

---
**Lưu ý cuối**: Sau khi thêm asset mới, không cần restart VS Code hay clear cache — chỉ cần chạy lại game!

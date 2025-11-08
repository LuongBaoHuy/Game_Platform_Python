# Hệ Thống Spawn Boss

## Tổng Quan
Hệ thống spawn boss được thiết kế để tạo trải nghiệm chơi game thú vị hơn với các giai đoạn:
1. **Giai đoạn 1**: Người chơi phải tiêu diệt 5 con quái gần vị trí spawn
2. **Giai đoạn 2**: Sau khi tiêu diệt hết 5 con quái, BOSS sẽ xuất hiện

## Cơ Chế Hoạt Động

### 1. Spawn Enemies Ban Đầu
- **Số lượng**: 5 con quái
- **Vị trí**: Spawn xung quanh player trong bán kính 500-800 pixels
- **Loại quái**: Random từ danh sách enemies có sẵn (Golem_02, Golem_03, Minotaur_01, etc.)

```python
INITIAL_ENEMY_COUNT = 5  # Số lượng quái ban đầu
# Spawn trong bán kính 500-800 pixels từ player
distance = random.uniform(500, 800)
```

### 2. Theo Dõi Tiến Độ
Hệ thống theo dõi:
- ID của 5 con quái ban đầu (lưu trong `initial_enemies_ids`)
- Số lượng quái còn sống
- Trạng thái spawn boss (`boss_spawned`)

### 3. Spawn Boss
Khi tất cả 5 con quái ban đầu bị tiêu diệt:
- Boss (Troll1) sẽ spawn gần player (khoảng cách 600 pixels)
- Vị trí boss được tính toán để không spawn ngoài map
- Hiển thị thông báo "BOSS BATTLE" trên màn hình

```python
# Boss spawn distance
boss_distance = 600  # pixels from player
```

## Giao Diện Người Chơi

### Hiển Thị Trên Màn Hình

#### Trước Khi Boss Spawn:
```
Enemies: 5/5  (màu đỏ)
Enemies: 3/5  (màu đỏ - đang chiến đấu)
Enemies: 0/5  (màu xanh - hoàn thành)
```

#### Sau Khi Boss Spawn:
```
⚠ BOSS BATTLE ⚠  (chữ nhấp nháy màu cam)
```

## Debug Information
Hệ thống in ra console mỗi giây:
```
[DEBUG] Enemies alive: 3, Boss spawned: False
[DEBUG] Enemies alive: 0, Boss spawned: False
==================================================
[BOSS] All 5 enemies defeated!
[BOSS] Spawning BOSS near player...
==================================================
[BOSS] TROLL BOSS spawned at (2000, 9000)
[BOSS] Player position: (1200, 9200)
```

## Tùy Chỉnh

### Thay Đổi Số Lượng Enemies
Chỉnh sửa trong `game/app.py`:
```python
INITIAL_ENEMY_COUNT = 5  # Thay đổi số này
```

### Thay Đổi Khoảng Cách Spawn
```python
# Enemies spawn distance
distance = random.uniform(500, 800)  # Tăng/giảm số này

# Boss spawn distance
boss_distance = 600  # Tăng/giảm số này
```

### Thay Đổi Loại Boss
```python
boss_instance = create_enemy("Troll1", x=boss_x, y=boss_y)
# Thay "Troll1" bằng boss khác: "Minotaur_01", "Golem_03", etc.
```

## Các Vấn Đề Thường Gặp

### Boss Không Spawn
- Kiểm tra console xem có lỗi không
- Đảm bảo tất cả 5 enemies ban đầu đã bị tiêu diệt
- Kiểm tra `create_enemy` function hoạt động đúng

### Enemies Spawn Ngoài Map
Hệ thống đã có giới hạn:
```python
ex = max(100, min(ex, 14000))  # X range
ey = max(1000, min(ey, 9500))  # Y range
```

### Boss Spawn Quá Xa/Gần
Điều chỉnh `boss_distance`:
```python
boss_distance = 600  # Thay đổi giá trị này
```

## Luồng Code Chính

```
1. Player spawn tại spawn_pos
   ↓
2. Spawn 5 enemies xung quanh player
   ↓
3. Lưu IDs của 5 enemies ban đầu
   ↓
4. Game loop:
   - Cập nhật enemies
   - Kiểm tra collisions
   - Đếm enemies còn sống
   ↓
5. Khi alive_initial == 0:
   - Tính toán vị trí boss
   - Spawn boss gần player
   - Set boss_spawned = True
   ↓
6. Hiển thị "BOSS BATTLE"
```

## Mở Rộng Trong Tương Lai

### Thêm Nhiều Wave
```python
wave_configs = [
    {"count": 5, "types": ["golem_02", "golem_03"]},
    {"count": 8, "types": ["Minotaur_01", "Minotaur_02"]},
    {"count": 10, "types": ["Wraith_01", "Wraith_03"]},
]
```

### Nhiều Boss
```python
boss_types = ["Troll1", "Minotaur_03", "Golem_03"]
boss = random.choice(boss_types)
```

### Thêm Cutscene
```python
if alive_initial == 0:
    show_boss_warning_cutscene()
    spawn_boss()
```

## Tích Hợp Với Sound System
```python
# Khi boss spawn
sound_manager.play_sound("boss_spawn")
sound_manager.play_music("boss_battle")
```

---
**Lưu ý**: Đảm bảo tất cả enemies và boss có metadata đầy đủ trong thư mục `assets/characters/`

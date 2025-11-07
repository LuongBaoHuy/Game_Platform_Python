# Hướng Dẫn Hệ Thống Boss Spawn

## Cách Hoạt Động

### 🎮 Gameplay

1. **Bắt đầu game**: 5 con quái sẽ spawn xung quanh vị trí của bạn (trong bán kính 500-800 pixels)

2. **Tiêu diệt quái**: Đánh bại cả 5 con quái này
   - Màn hình sẽ hiển thị: `Enemies: X/5` (màu đỏ)
   - Số X sẽ giảm dần khi bạn tiêu diệt quái

3. **Boss xuất hiện**: Khi tiêu diệt hết 5 con quái
   - Màn hình hiển thị: `⚠ BOSS BATTLE ⚠` (chữ nhấp nháy)
   - Boss (Troll Tank) sẽ spawn gần vị trí của bạn (khoảng 600 pixels)

### 📊 Thông Tin Trên Màn Hình

- **Trước boss**: `Enemies: 5/5` → `Enemies: 3/5` → `Enemies: 0/5`
- **Sau khi boss spawn**: `⚠ BOSS BATTLE ⚠` (chữ cam nhấp nháy)
- **Vị trí**: Góc trên cùng giữa màn hình

### 🎯 Mẹo Chơi

- **5 con quái ban đầu** spawn rất gần bạn nên dễ tìm
- **Boss spawn gần** nên không cần tìm kiếm xa
- Boss rất mạnh, chuẩn bị kỹ trước khi tiêu diệt hết 5 con quái!

### 🔧 Tùy Chỉnh (Dành Cho Dev)

**Thay đổi số lượng quái** - File `game/app.py`:
```python
INITIAL_ENEMY_COUNT = 5  # Thay số này (dòng 159)
```

**Thay đổi khoảng cách spawn**:
```python
distance = random.uniform(500, 800)  # Enemies (dòng 168)
boss_distance = 600  # Boss (dòng 338)
```

**Thay đổi loại boss**:
```python
create_enemy("Troll1", x=boss_x, y=boss_y)  # Dòng 344
# Có thể thay bằng: "Minotaur_03", "Golem_03", etc.
```

### 📝 Console Debug

Game sẽ in thông tin debug:
```
[SPAWN] Enemy 1/5: Golem_02 at (1506, 9500)
[SPAWN] Enemy 2/5: Golem_03 at (1583, 9200)
...
[DEBUG] Enemies alive: 3, Boss spawned: False
[DEBUG] Enemies alive: 0, Boss spawned: False
==================================================
[BOSS] All 5 enemies defeated!
[BOSS] Spawning BOSS near player...
==================================================
```

### ⚠️ Lưu Ý

- Chỉ có 5 con quái **ban đầu** được tính
- Nếu có enemies khác spawn sau đó, chúng **không** ảnh hưởng đến boss spawn
- Boss chỉ spawn **một lần** mỗi game session

### 🎬 Các Tính Năng Có Thể Mở Rộng

- [ ] Thêm nhiều wave enemies
- [ ] Boss có nhiều pha chiến đấu
- [ ] Cutscene khi boss xuất hiện
- [ ] Nhạc boss battle riêng
- [ ] Phần thưởng sau khi đánh bại boss

---

**Tạo bởi**: AI Assistant
**Ngày**: 2025-11-08
**File code chính**: `game/app.py` (dòng 157-346)

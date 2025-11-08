# HƯỚNG DẪN TÍCH HỢP PORTAL & ARENA SYSTEM

## 📋 Tổng quan
Hệ thống Portal & Arena cho phép tạo các cổng dịch chuyển đến các khu vực chiến đấu khác nhau.

## 🎮 Cách hoạt động:
1. Player đi đến Portal → Nhấn phím E
2. Vào Arena → Spawn 5 enemies
3. Giết hết 5 enemies → Boss xuất hiện
4. Giết boss → Hoàn thành arena

---

## 🔧 CÁCH TÍCH HỢP VÀO app.py

### Bước 1: Import các class mới (thêm vào đầu file app.py)

```python
# Thêm vào phần import
from game.portal import Portal, PortalManager
from game.arena import Arena
```

### Bước 2: Tạo Portal Manager trong run_game_session()

Tìm dòng này trong `run_game_session()`:
```python
# Boss tracking variables
boss_spawned = False
boss_instance = None
```

Thêm NGAY SAU đó:
```python
# Portal & Arena System
portal_manager = PortalManager()
portal_manager.create_default_portals()  # Tạo portal mặc định

current_arena = None  # Arena hiện tại
```

### Bước 3: Update portal trong game loop

Tìm game loop (vòng lặp `while running:`), thêm vào phần update:

```python
# Update portal system
portal_manager.update(dt, player)

# Check portal interaction (phím E)
keys = pygame.key.get_pressed()
if keys[pygame.K_e]:
    entered_portal = portal_manager.check_portal_interaction(player, True)
    if entered_portal:
        # Player vào portal → Start arena
        if current_arena:
            current_arena.cleanup()
        
        # Tạo arena mới
        current_arena = Arena(
            entered_portal.portal_id,
            entered_portal.destination
        )
        current_arena.start(create_enemy, PatrolEnemy)
        
        # Di chuyển player đến spawn center
        spawn_center = entered_portal.destination['spawn_center']
        player.rect.centerx = spawn_center[0]
        player.rect.centery = spawn_center[1]
        
        print(f"[GAME] Entered arena: {current_arena.name}")

# Update arena (nếu có)
if current_arena and current_arena.active:
    current_arena.update(dt, platforms, player, create_enemy)
```

### Bước 4: Vẽ portal và arena

Tìm phần vẽ enemies:
```python
# Draw enemies
for enemy in enemies:
    enemy.draw(surface, camera_x, camera_y, show_hitboxes=False)
```

Thay bằng:
```python
# Draw enemies hoặc arena
if current_arena and current_arena.active:
    # Vẽ arena
    current_arena.draw(surface, camera_x, camera_y, show_hitboxes=False)
else:
    # Vẽ enemies bình thường
    for enemy in enemies:
        enemy.draw(surface, camera_x, camera_y, show_hitboxes=False)

# Draw portals
portal_manager.draw(surface, camera_x, camera_y)
```

### Bước 5: Xử lý collision với arena enemies

Tìm phần xử lý collision với enemies:
```python
# Player collision với enemies
for enemy in enemies[:]:
    ...
```

Thay bằng:
```python
# Get current entities (enemies or arena entities)
current_entities = []
if current_arena and current_arena.active:
    current_entities = current_arena.get_all_entities()
else:
    current_entities = enemies

# Player collision với entities
for entity in current_entities[:]:
    if hasattr(entity, 'rect') and player.rect.colliderect(entity.rect):
        # ... xử lý collision
```

---

## 🎨 THÊM PORTAL MỚI

### Cách thêm portal thứ 2, 3, ...

Trong `portal_manager.create_default_portals()`, thêm:

```python
# Portal 2: Arena khó hơn
portal_2 = Portal(
    x=3000,  # Vị trí portal
    y=9100,
    portal_id="arena_2",
    destination={
        'name': 'Arena 2: Harder Challenge',
        'enemies': ['minotaur_01', 'minotaur_02', 'Wraith_01'],
        'enemy_count': 7,  # Nhiều hơn
        'boss': 'Troll1',
        'spawn_center': (5000, 9200)  # Spawn ở vị trí khác
    }
)
self.add_portal(portal_2)
```

---

## ⚙️ TÙY CHỈNH

### Thay đổi vị trí Portal 1:
File: `game/portal.py`, trong `create_default_portals()`:
```python
portal_1 = Portal(
    x=1500,  # ← Thay đổi X
    y=9100,  # ← Thay đổi Y
    ...
)
```

### Thay đổi số lượng enemies:
```python
'enemy_count': 10,  # ← Thay đổi số lượng
```

### Thay đổi loại enemies:
```python
'enemies': ['Golem_02', 'minotaur_01', 'Wraith_03'],  # ← Thay đổi danh sách
```

---

## 📝 CHECKLIST TÍCH HỢP

- [ ] Import Portal, PortalManager, Arena
- [ ] Tạo portal_manager và current_arena
- [ ] Update portal trong game loop
- [ ] Check portal interaction (phím E)
- [ ] Update arena
- [ ] Vẽ portal và arena
- [ ] Xử lý collision với arena entities
- [ ] Test: Đi đến portal → Nhấn E → Vào arena

---

## 🐛 DEBUG

Nếu portal không hiển thị:
- Check console: `[PORTAL] Added portal...`
- Check vị trí portal có gần player spawn không

Nếu không vào được arena:
- Check phím E có hoạt động không
- Check console: `[GAME] Entered arena...`

Nếu enemies không spawn:
- Check console: `[ARENA] Spawning X enemies...`
- Check `create_enemy` function có hoạt động không

---

## 📞 HỖ TRỢ

Nếu gặp lỗi, check console logs:
- `[PORTAL]` - Portal system
- `[ARENA]` - Arena system
- `[GAME]` - Game flow

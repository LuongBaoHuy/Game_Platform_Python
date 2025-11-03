# Wraith Enemies - Projectile Effects & Range Update

## ✅ Đã hoàn thành

### 1. **Projectile Effects Hiển Thị**
- ✅ Fix `convert_alpha()` error trong `ProjectileSkill` (skills.py)
- ✅ Skills module được import và registered đúng cách
- ✅ Blast skill load 7 frames từ `assets/skill-effect/skill_uti_wizard`
- ✅ Projectiles được update và vẽ trong game loop
- ✅ Collision detection với player hoạt động

### 2. **Tăng Tầm Đánh Cho Caster**
```python
# Trước đây:
detection_range = 400
max_cast_range = 400
preferred_distance = 250
min_distance = 100

# Bây giờ (TĂNG 40-50%):
detection_range = 600    # +200 (50% tăng)
max_cast_range = 550     # +150 (37% tăng) 
preferred_distance = 350  # +100 (40% tăng)
min_distance = 150       # +50 (50% tăng)
```

### 3. **Projectile System Integration**

#### CasterEnemy:
- `update_skills(dt, player)` - Update projectiles mỗi frame
- `draw_skills(surface, camera_x, camera_y)` - Vẽ projectiles
- `draw()` - Override để vẽ cả sprite và projectiles
- Collision detection tự động khi projectile chạm player

#### ControllerEnemy:
- Tương tự CasterEnemy
- Charged projectiles pierce (không bị xóa khi hit)

## 🎮 Trong Game

### Khi Wraith_01 (Caster) tấn công:
1. **Cast Animation** (18 frames) - Enemy đứng yên và cast
2. **Projectile Spawn** - Viên đạn xuất hiện từ enemy
3. **Projectile Flight** - Bay về phía player với speed 800
4. **Visual Effect** - 7 frames animation từ skill_uti_wizard
5. **Hit Detection** - Gây 18 damage khi chạm player
6. **Projectile Removal** - Bị xóa sau khi hit hoặc timeout

### Ranges:
- **Phát hiện player**: 600 pixels
- **Bắn phép**: 550 pixels (xa hơn so với melee enemies rất nhiều)
- **Khoảng cách ưa thích**: 350 pixels (giữ an toàn)
- **Lùi lại**: < 150 pixels (tránh player đến gần)

## 📁 Files Đã Sửa

### Core Fixes:
1. **game/characters/__init__.py**
   - Import skills module để trigger registration

2. **game/characters/skills.py**
   - Fix `convert_alpha()` error trong ProjectileSkill
   - Thêm fallback khi pygame display chưa init

3. **game/characters/data_driven_enemy.py**
   - Copy skills từ visual object

4. **game/characters/specialized_enemies.py**
   - Tăng ranges cho CasterEnemy
   - Thêm `update_skills()` method
   - Thêm `draw_skills()` method
   - Override `draw()` để vẽ projectiles
   - Update ControllerEnemy với skill integration

### Animation Fixes (previous):
5. **game/characters/factory.py**
   - Load tất cả animation states từ metadata
   
6. **game/player.py**
   - Fix convert_alpha() error

## 🧪 Test Results

```
✓ Blast skill loaded with 7 frames
✓ Detection range: 600
✓ Max cast range: 550
✓ Projectiles update & draw
✓ Collision detection works
✓ Cast animation plays (18 frames)
✓ Hurt/dying animations work
```

## 🎯 Expected Behavior

### Wraith_01 (Caster):
- **Xa player (> 550)**: Tiến lại gần
- **350-550**: Đứng yên, cast và bắn phép
- **150-350**: Khoảng cách tốt, có thể cast
- **< 150**: Lùi lại, tránh player

### Visual Effects:
- Cast animation mượt mà (0.08s/frame)
- Projectile có 7 frames animation
- Hiệu ứng bay nhanh (800 pixels/s)
- Collision feedback ngay lập tức

## 🐛 Troubleshooting

### Nếu không thấy projectiles:
1. Check console có lỗi load frames không
2. Verify `assets/skill-effect/skill_uti_wizard` có 7 PNG files
3. Test: `caster.skills.get('blast').frames` phải có 7 items

### Nếu không gây damage:
1. Projectile phải chạm player.rect
2. Player phải có `take_damage()` method
3. Check collision trong `update_skills()`

### Nếu projectiles không bay:
1. `update_skills(dt, player)` phải được gọi trong enemy.update()
2. Blast skill phải có `projectiles` list
3. Check `blast.use()` được gọi trong `_fire_projectile()`

## 🚀 Next Steps (Optional)

- Thêm sound effects khi bắn phép
- Particles khi projectile hit
- Screen shake khi hit
- Slow-motion effect khi dodge projectiles
- Boss version với multiple projectiles

**Chúc mừng! Wraith enemies giờ có projectile effects đầy đủ! 🧙‍♂️✨**
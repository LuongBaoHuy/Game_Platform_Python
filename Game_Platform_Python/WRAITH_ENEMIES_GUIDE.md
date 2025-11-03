# Wraith Enemies - Hướng Dẫn Sử Dụng

## Tổng quan
Đã thêm thành công 2 loại enemy mới với hành vi AI chuyên biệt:

### Wraith_01 - Caster (Pháp Sư)
- **Loại**: Ranged spellcaster
- **Đặc điểm**: 
  - Tấn công từ xa bằng projectile magic
  - Giữ khoảng cách với player
  - Lùi lại khi player đến quá gần
- **Animations**: 
  - `cast` (18 frames) - Bắn phép thuật
  - `attack`, `hurt`, `dying`, `idle`, `walk` (12-15 frames)
- **Skills**: `blast` projectile với damage 18

### Wraith_03 - Controller (Khống Chế)  
- **Loại**: Crowd control specialist
- **Đặc điểm**:
  - Charged projectile attack (tích năng lượng)
  - Teleport để reposition
  - Slow aura làm chậm player
- **Animations**: Tương tự Wraith_01 với `cast` animation chậm hơn
- **Skills**: `charge` attack với base damage 12

## Animation States và Speeds

### CasterEnemy Animation Speeds:
- **Default**: 0.15s/frame
- **Cast**: 0.08s/frame (chậm để thấy rõ)
- **Attack**: 0.12s/frame  
- **Hurt**: 0.1s/frame

### ControllerEnemy Animation Speeds:
- **Default**: 0.15s/frame
- **Cast**: 0.06s/frame (rất chậm cho charging effect)
- **Attack**: 0.12s/frame
- **Hurt**: 0.1s/frame

## Khi nào animations được trigger:

### Cast Animation:
- **Caster**: Khi bắn projectile (distance 100-400 từ player)
- **Controller**: Khi charging attack (distance ≤ 300 từ player)

### Attack Animation:  
- Khi ở tầm gần và thực hiện melee attack (fallback)

### Hurt Animation:
- Khi bị player tấn công (`take_damage()`)
- Kéo dài 0.25 giây

### Dying Animation:
- Khi HP ≤ 0
- Không loop, dừng ở frame cuối

## Cách test trong game:

1. **Chạy game**:
   ```bash
   cd "D:\Game_Python\Game_Platform_Python\Game_Platform_Python"
   python game/app.py
   ```

2. **Spawn enemies** (nếu có debug mode):
   ```python
   from game.enemy_registry import create_enemy
   caster = create_enemy('Wraith_01', x, y)
   controller = create_enemy('Wraith_03', x, y)
   ```

3. **Quan sát hành vi**:
   - Caster sẽ giữ khoảng cách và bắn projectile
   - Controller sẽ charge attack và có aura effects
   - Cả hai đều có animations mượt mà khi cast, hurt, dying

## Files đã tạo/sửa:

### Core Classes:
- `game/characters/specialized_enemies.py` - CasterEnemy & ControllerEnemy

### Metadata:  
- `assets/characters/Wraith_01/metadata.json` - Caster config + blast skill
- `assets/characters/Wraith_03/metadata.json` - Controller config + charge skill

### Registry:
- `game/enemy.py` - Đăng ký specialized classes
- `game/characters/factory.py` - Fixed để load tất cả animation states

### Bug Fixes:
- `game/player.py` - Fixed convert_alpha() error khi pygame display chưa setup

## Troubleshooting:

### Nếu không thấy animations:
1. Kiểm tra console có lỗi load sprites không
2. Verify folder structure: `assets/characters/Wraith_XX/PNG Sequences/`
3. Test tạo enemy: `create_enemy('Wraith_01', 100, 100)`

### Nếu animations quá nhanh/chậm:
- Điều chỉnh `anim_speed`, `cast_anim_speed` trong specialized_enemies.py

### Nếu AI không hoạt động:
- Kiểm tra enemy có được đăng ký đúng class không: `type(enemy).__name__`
- Verify skills được load từ metadata: `enemy.skills`

## Kết quả mong đợi:
- ✅ Sprites hiển thị thay vì hình chữ nhật đỏ  
- ✅ Cast animations khi enemy bắn phép
- ✅ Hurt animations khi bị tấn công
- ✅ Dying animations khi chết
- ✅ Hành vi AI khác biệt giữa Caster vs Controller
- ✅ Projectile effects và visual feedback

**Chúc mừng! Wraith enemies đã hoàn thành và sẵn sàng sử dụng! 🧙‍♂️⚔️**
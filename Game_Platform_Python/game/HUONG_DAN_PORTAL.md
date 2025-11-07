# Hướng Dẫn Sử Dụng Portal (Cổng Dịch Chuyển)

## Giới Thiệu
Portal là hệ thống cổng dịch chuyển 2 chiều cho phép player teleport từ cổng này sang cổng khác.

## Cách Tạo Portal Trong Tiled

### 1. Tạo Object Layer
- Tạo một Object Layer mới với tên chứa từ "portal" (ví dụ: `Object_portals`)
- Layer name phải chứa từ "portal" để game nhận diện

### 2. Thêm Portal Objects
- Thêm tile object vào layer portal
- Mỗi portal cần có **Custom Properties** sau:

#### Properties Bắt Buộc:
- **`target`** (int): ID của portal đích mà portal này sẽ teleport đến
  - Ví dụ: Portal ID 1274 có `target=1276` sẽ teleport player đến portal 1276

#### Properties Tùy Chọn:
- **`cooldown_ms`** (int): Thời gian cooldown (milliseconds) trước khi có thể teleport lại
  - Mặc định: 1000ms (1 giây)
  - Khuyến nghị: 800-1500ms để tránh teleport liên tục
  
- **`spawn_offset_x`** (int): Offset X (pixels) khi spawn tại portal đích
  - Mặc định: 0
  - Dương = dịch sang phải, Âm = dịch sang trái
  
- **`spawn_offset_y`** (int): Offset Y (pixels) khi spawn tại portal đích
  - Mặc định: 0
  - Dương = dịch xuống, Âm = dịch lên
  - Khuyến nghị: -8 để player spawn cao hơn một chút tránh bị kẹt
  
- **`interact`** (string): Nếu có property này (giá trị bất kỳ), portal cần nhấn phím để kích hoạt
  - Hiện tại chưa implement, portal tự động kích hoạt khi chạm

## Ví Dụ Portal 2 Chiều

### Portal A (ID: 1274)
```
Properties:
- target: 1276
- cooldown_ms: 800
- spawn_offset_x: 0
- spawn_offset_y: -8
```

### Portal B (ID: 1276)
```
Properties:
- target: 1274
- cooldown_ms: 800
- spawn_offset_x: 0
- spawn_offset_y: -8
```

Khi player chạm Portal A → teleport đến Portal B
Khi player chạm Portal B → teleport đến Portal A

## Cơ Chế Hoạt Động

### 1. Cooldown System
- Khi teleport, **CẢ HAI portal** (nguồn và đích) đều được đặt cooldown
- Điều này tránh player teleport ngay lại sau khi vừa đến portal đích
- Cooldown tính bằng thời gian thực (milliseconds)

### 2. Spawn Position
- Player spawn tại vị trí của portal đích
- Tọa độ spawn = `portal.x + spawn_offset_x`, `portal.y + spawn_offset_y`
- Nên dùng `spawn_offset_y = -8` để player không bị kẹt trong đất

### 3. Collision Detection
- Portal check collision với player rect mỗi frame
- Nếu player chạm portal VÀ cooldown đã hết → teleport
- Nếu portal có `require_interact=True` → cần nhấn phím (tính năng chưa có)

## Thứ Tự Vẽ (Render Order)
1. Background/Sky
2. Object Layer 1 (static decorations)
3. Tile Layer (nen)
4. **Portals** ← Vẽ ở đây
5. Moving Platforms
6. Animated Decorations
7. Player/Enemies
8. UI/HUD

## Tips & Best Practices

### Cooldown
- **Quá ngắn (<500ms)**: Player sẽ teleport liên tục qua lại
- **Vừa phải (800-1200ms)**: Player có thể teleport mượt mà
- **Quá dài (>2000ms)**: Player phải chờ lâu, có thể gây khó chịu

### Spawn Offset
- Dùng `spawn_offset_y = -8` để tránh player spawn vào trong ground
- Nếu portal ở vị trí cao, có thể dùng `spawn_offset_y = -50` để player spawn cao hơn
- `spawn_offset_x` hữu ích khi muốn player spawn lệch khỏi portal (tránh teleport lại ngay)

### Portal Placement
- Đặt portal ở nơi dễ thấy
- Tránh đặt portal ngay cạnh vực hoặc chướng ngại vật
- Nên có khoảng trống quanh portal đích để player có chỗ spawn

### Visual Feedback
- Portal tự động vẽ tile nếu có gid trong Tiled
- Nếu không có tile, portal vẽ hình chữ nhật xanh dương trong suốt
- Khuyến nghị: Dùng tile có animation để portal nổi bật hơn

## Debug

### Check Portal Đã Load
Khi chạy game, console sẽ hiện:
```
[Portal] Đã load 2 portals
```

### Check Teleport
Mỗi lần teleport, console log:
```
[Portal] Teleport từ portal 1274 sang portal 1276
```

### Lỗi Thường Gặp

**Portal không hoạt động:**
- Kiểm tra layer name có chứa "portal" không
- Kiểm tra property `target` có đúng ID portal đích không
- Kiểm tra portal đích có tồn tại không

**Teleport liên tục:**
- Tăng `cooldown_ms` (khuyến nghị 1000-1500ms)
- Kiểm tra `spawn_offset` để player không spawn ngay trong portal đích

**Player bị kẹt sau khi teleport:**
- Tăng `spawn_offset_y` âm hơn (ví dụ: -20)
- Kiểm tra xem portal đích có bị chồng với tile/platform không

## Code Reference

### Files Liên Quan
- `game/portal.py`: Portal và PortalManager classes
- `game/map_loader.py`: Load portal từ Tiled TMX
- `game/app.py`: Tích hợp portal vào game loop

### API

```python
# Tạo portal manager
portal_manager = PortalManager()

# Thêm portal
portal = Portal(
    obj_id=1274,
    x=4053,
    y=12830,
    width=512,
    height=512,
    target_id=1276,
    cooldown_ms=800,
    spawn_offset_x=0,
    spawn_offset_y=-8
)
portal_manager.add_portal(portal)

# Check collision và teleport
portal = portal_manager.check_player_collision(player.rect)
if portal:
    portal_manager.teleport_player(player, portal)
```

## Future Features (Chưa Implement)

### Interact Key
- Portal cần nhấn phím (E/F) để kích hoạt
- Property: `interact = true`

### Portal Effects
- Hiệu ứng ánh sáng khi teleport
- Sound effect khi teleport
- Particle effect

### One-Way Portal
- Portal chỉ hoạt động 1 chiều
- Property: `one_way = true`

### Conditional Portal
- Portal chỉ hoạt động khi có điều kiện (có key, đã hoàn thành quest...)
- Property: `required_item = "golden_key"`

## Changelog

### Version 1.0 (2025-11-08)
- ✅ Portal 2 chiều cơ bản
- ✅ Cooldown system
- ✅ Spawn offset
- ✅ Auto-detect từ Tiled layer "portal"
- ✅ Load properties từ Tiled
- ✅ Render portal với tile hoặc default color

# Fix Lỗi: Quái 0 HP Không Chết

## 🐛 Vấn Đề
Khi tấn công quái bằng 2 skills liên tục, quái bị 0 HP nhưng vẫn **không chết** và tồn tại trên map.

## 💡 Nguyên Nhân
1. Enemy chuyển sang trạng thái `dying=True` nhưng không có animation "dying"
2. Không có animation → Không bao giờ chuyển sang `dead=True`
3. Enemy "sống dai" mãi mãi với 0 HP

## ✅ Đã Fix

### Thay Đổi Trong `game/characters/data_driven_enemy.py`:

#### 1. **Kiểm tra animation dying có tồn tại**
```python
# Nếu KHÔNG có dying animation → Chết ngay lập tức
# Nếu CÓ dying animation → Chạy animation rồi mới chết
```

#### 2. **Thêm timeout 2 giây**
```python
# Nếu dying quá 2 giây → Force chết
# Tránh trường hợp animation bị stuck
```

#### 3. **Xử lý không có frames**
```python
# Nếu đang dying nhưng không có frames → Chết ngay
```

## 🎮 Kết Quả

### ❌ Trước khi fix:
```
Hit enemy → HP = 0 → dying=True → Không bao giờ chết
Enemy vẫn đứng yên trên map với 0 HP
```

### ✅ Sau khi fix:
```
Hit enemy → HP = 0 → Check animation:
  - Có animation dying: Chạy animation → Chết
  - Không có animation: Chết ngay lập tức
  - Animation quá lâu: Timeout 2s → Chết
Enemy biến mất đúng cách
```

## 🔍 Debug

Game sẽ in ra console:
```
[ENEMY] Starting dying animation (10 frames)
[ENEMY] Dying animation complete - enemy is now dead
```

Hoặc:
```
[ENEMY] No dying animation found - instant death
```

Hoặc (nếu stuck):
```
[ENEMY] Dying timeout - forcing death after 2.00s
```

## 🧪 Cách Test

1. Chạy game và tấn công quái
2. Dùng 2-3 skills liên tục
3. Enemy HP về 0
4. Enemy sẽ:
   - Chạy dying animation (nếu có)
   - Hoặc biến mất ngay lập tức
   - Hoặc biến mất sau tối đa 2 giây

## ⚙️ Tùy Chỉnh

Thay đổi thời gian timeout trong `data_driven_enemy.py`:
```python
self.max_dying_duration = 2.0  # Tăng/giảm số giây này
```

## 📋 Checklist

- ✅ Enemy với dying animation chết đúng
- ✅ Enemy không có dying animation chết ngay
- ✅ Enemy dying quá lâu bị force death
- ✅ Không bị duplicate death
- ✅ Boss spawn đúng khi đủ 5 enemies chết

---
**Ngày fix**: 2025-11-08  
**File sửa**: `game/characters/data_driven_enemy.py`

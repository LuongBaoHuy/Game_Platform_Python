# Tiled Flip & Rotation Fix - Hướng Dẫn

## Vấn Đề
Khi tạo map trong Tiled, bạn đã xoay và lật (flip) nhiều tile trong Object Layer. Tuy nhiên, khi load vào game, các tile này không hiển thị đúng như trong Tiled.

## Nguyên Nhân
Tiled lưu thông tin flip/rotation trong thuộc tính `gid` (Global ID) bằng cách sử dụng **bit flags**:
- **Bit 31 (0x80000000)**: Horizontal Flip (lật ngang)
- **Bit 30 (0x40000000)**: Vertical Flip (lật dọc)
- **Bit 29 (0x20000000)**: Diagonal Flip (xoay 90 độ + flip)

## Giải Pháp

### 1. Cập nhật `map_loader.py`
Thêm xử lý flip flags khi load objects:

```python
# Định nghĩa các bit flags của Tiled
FLIPPED_HORIZONTALLY_FLAG = 0x80000000
FLIPPED_VERTICALLY_FLAG = 0x40000000
FLIPPED_DIAGONALLY_FLAG = 0x20000000
GID_MASK = 0x1FFFFFFF  # Mask để lấy GID thực (không có flags)
```

**Quy trình xử lý:**
1. Trích xuất flip flags từ GID
2. Lấy GID thực bằng cách AND với GID_MASK
3. Load tile image từ GID thực
4. Áp dụng transformations theo thứ tự:
   - **Diagonal flip** trước (rotate -90° + horizontal flip)
   - **Horizontal flip** 
   - **Vertical flip**

### 2. Cập nhật `app.py`
Xử lý rotation attribute (nếu có):
```python
rotation = obj.get("rotation", 0)
if rotation != 0:
    # Pygame xoay ngược chiều kim đồng hồ, Tiled xoay thuận chiều
    tile = pygame.transform.rotate(tile, -rotation)
```

## Kết Quả
- ✅ Các tile bị flip horizontal/vertical sẽ hiển thị đúng
- ✅ Các tile bị rotate sẽ hiển thị đúng góc
- ✅ Các tile có cả flip + rotate sẽ được xử lý đúng thứ tự
- ✅ Object Layer hiện giống y hệt trong Tiled

## Test
Chạy game và kiểm tra Object Layer trong Map_test.tmx:
```bash
python -m game.app
```

Các decoration objects (cây, lá, đá...) giờ sẽ hiển thị đúng như bạn thiết kế trong Tiled!

## Lưu Ý Kỹ Thuật
1. **Thứ tự transformation quan trọng**: Diagonal → Horizontal → Vertical
2. **Rotation direction**: Tiled (clockwise) vs Pygame (counter-clockwise) → cần negate giá trị
3. **Performance**: Transformations được áp dụng 1 lần khi load map, không ảnh hưởng FPS

## Tham Khảo
- [Tiled Documentation - TMX Map Format](https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#tile-flipping)
- [Pygame Transform Documentation](https://www.pygame.org/docs/ref/transform.html)

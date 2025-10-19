import pytmx
import pygame


def load_map(filename,
             hitbox_inset: int = 0,
             top_inset: int = 0,
             bottom_inset: int = 0,
             left_inset: int = 0,
             right_inset: int = 0):
    """
    Tải một bản đồ TMX và trả về danh sách (tile_surface, rect).

    Các tham số để thu nhỏ hitbox:
    - hitbox_inset: giá trị inset đơn kiểu legacy, áp dụng cho tất cả các cạnh nếu > 0
    - top_inset/bottom_inset/left_inset/right_inset: inset theo từng cạnh

    Các inset theo từng cạnh sẽ ghi đè `hitbox_inset` khi được cung cấp (khác 0).
    Kích thước Rect được giới hạn tối thiểu là 1x1.
    """
    tmx_data = pytmx.load_pygame(filename)
    platforms = []

    for layer in tmx_data.layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile:
                    screen_x = x * tmx_data.tilewidth
                    screen_y = y * tmx_data.tileheight
                    w = tmx_data.tilewidth
                    h = tmx_data.tileheight

                    # Decide effective insets. If per-side values provided (non-zero)
                    # use them; otherwise fall back to legacy `hitbox_inset`.
                    left = int(left_inset or hitbox_inset)
                    right = int(right_inset or hitbox_inset)
                    top = int(top_inset or hitbox_inset)
                    bottom = int(bottom_inset or hitbox_inset)

                    new_x = screen_x + left
                    new_y = screen_y + top
                    new_w = max(1, w - left - right)
                    new_h = max(1, h - top - bottom)

                    rect = pygame.Rect(new_x, new_y, new_w, new_h)
                    platforms.append((tile, rect))
    return platforms, tmx_data

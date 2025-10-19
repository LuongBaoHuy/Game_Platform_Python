import pytmx, pygame


def load_map(
    filename,
    *,
    hitbox_inset=0,
    top_inset=0,
    bottom_inset=0,
    left_inset=0,
    right_inset=0
):
    tmx = pytmx.load_pygame(filename)

    draw_layers = []  # Danh sách (surface, x, y) cho tất cả layer hiển thị
    platforms = []  # Danh sách (surface, rect) chỉ cho layer 'solid'
    spawn_point = None

    # Lấy vị trí spawn (object có name="player_spawn")
    for obj in tmx.objects:
        if getattr(obj, "name", "") == "player_spawn":
            spawn_point = (int(obj.x + obj.width / 2), int(obj.y + obj.height))
            break

    for layer in tmx.visible_layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                img = tmx.get_tile_image_by_gid(gid)
                if not img:
                    continue
                px, py = x * tmx.tilewidth, y * tmx.tileheight
                # Lưu tất cả tile để vẽ
                draw_layers.append((img, px, py, layer.name))

                # Chỉ layer 'solid' có va chạm
                if layer.name == "solid":
                    w, h = tmx.tilewidth, tmx.tileheight
                    left = int(left_inset or hitbox_inset)
                    right = int(right_inset or hitbox_inset)
                    top = int(top_inset or hitbox_inset)
                    bot = int(bottom_inset or hitbox_inset)
                    rect = pygame.Rect(
                        px + left,
                        py + top,
                        max(1, w - left - right),
                        max(1, h - top - bot),
                    )
                    platforms.append((img, rect))

    return draw_layers, platforms, spawn_point

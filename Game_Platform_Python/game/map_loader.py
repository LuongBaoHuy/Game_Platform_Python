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
    
    Returns:
        (platforms, tmx_data, objects, animated_objects, moving_platforms, portals)
    """
    tmx_data = pytmx.load_pygame(filename)
    platforms = []
    objects = []
    animated_objects = []  # Separate list for animated decorations
    moving_platforms = []  # List cho các platform di chuyển
    portals = []  # List cho các portal dịch chuyển

    # Small cache to avoid converting the same gid/image multiple times.
    # Keys are gid (int) and values are pygame.Surface already converted for fast blit.
    tile_cache = {}

    for layer in tmx_data.layers:
        # Tile layers -> platforms
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile:
                    # Convert surface for faster blitting (convert_alpha preserves per-pixel alpha).
                    # Use a per-map cache so we don't repeatedly call convert on identical gid images.
                    cached = tile_cache.get(gid)
                    if cached is None:
                        try:
                            # convert_alpha requires a display surface to be set; app sets it before calling load_map
                            tile_cache[gid] = tile.convert_alpha()
                        except Exception:
                            # Fallback to convert() if convert_alpha fails
                            tile_cache[gid] = tile.convert()
                        cached = tile_cache[gid]

                    tile = cached

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
        # Object layers -> collect objects
        elif isinstance(layer, pytmx.TiledObjectGroup):
            layer_name = getattr(layer, 'name', '') or ''  # Đảm bảo không bao giờ là None
            is_animated_layer = 'animation' in layer_name.lower()
            is_moving_layer = 'moving' in layer_name.lower()  # Kiểm tra layer moving platform
            is_portal_layer = 'portal' in layer_name.lower()  # Kiểm tra layer portal
            
            for obj in layer:
                # obj may have properties; convert to a dict for convenience
                gid = getattr(obj, 'gid', None)
                tile_img = None
                animation_frames = []
                
                if gid:
                    try:
                        raw = tmx_data.get_tile_image_by_gid(gid)
                        if raw:
                            # Convert and cache tile image for faster blits
                            cached = tile_cache.get(gid)
                            if cached is None:
                                try:
                                    tile_cache[gid] = raw.convert_alpha()
                                except Exception:
                                    tile_cache[gid] = raw.convert()
                                cached = tile_cache[gid]
                            tile_img = cached

                        # Check if this tile has animation data
                        tile_props = tmx_data.get_tile_properties_by_gid(gid)
                        if tile_props and 'frames' in tile_props:
                            # Extract animation frames
                            for frame in tile_props['frames']:
                                frame_gid = frame.gid
                                frame_duration = frame.duration  # in milliseconds
                                frame_raw = tmx_data.get_tile_image_by_gid(frame_gid)
                                if frame_raw:
                                    # Convert frame image and cache by its gid too
                                    fcached = tile_cache.get(frame_gid)
                                    if fcached is None:
                                        try:
                                            tile_cache[frame_gid] = frame_raw.convert_alpha()
                                        except Exception:
                                            tile_cache[frame_gid] = frame_raw.convert()
                                        fcached = tile_cache[frame_gid]
                                    animation_frames.append({
                                        'image': fcached,
                                        'duration': frame_duration
                                    })
                    except Exception:
                        tile_img = None

                obj_dict = {
                    'id': getattr(obj, 'id', None),  # Thêm ID cho portal
                    'name': getattr(obj, 'name', None),
                    'type': getattr(obj, 'type', None),
                    'x': getattr(obj, 'x', 0),
                    'y': getattr(obj, 'y', 0),
                    'width': getattr(obj, 'width', 0),
                    'height': getattr(obj, 'height', 0),
                    'properties': obj.properties if hasattr(obj, 'properties') else {},
                    'gid': gid,
                    'tile': tile_img,
                    'animation_frames': animation_frames,
                    'layer_name': layer_name,
                }
                
                # Phân loại objects vào các list tương ứng
                if is_portal_layer:
                    # Portal objects
                    portals.append(obj_dict)
                elif is_moving_layer:
                    # Moving platforms (có hoặc không có animation)
                    moving_platforms.append(obj_dict)
                elif is_animated_layer and animation_frames:
                    # Animated decorations (không di chuyển)
                    animated_objects.append(obj_dict)
                else:
                    # Static objects
                    objects.append(obj_dict)

    return platforms, tmx_data, objects, animated_objects, moving_platforms, portals

import pygame
import sys
import os
from game.config import WIDTH, HEIGHT, FPS, ZOOM, PLAYER_SCALE
from game.map_loader import load_map
from game.player import Player
from game.animated_decor import AnimatedDecorManager
from game.moving_platform import MovingPlatformManager
from game.portal import PortalManager, Portal

# Nếu package characters được cài, dùng factory để tạo nhân vật từ metadata
try:
    from game.characters.factory import create_player, list_characters
except Exception:
    create_player = None
    list_characters = lambda: []
from game.menu import draw_menu
from game.enemy import PatrolEnemy

# Try to import enemy registry helpers (optional)
try:
    from game.enemy_registry import create_enemy, list_enemies as list_enemy_ids
except Exception:
    create_enemy = None
    list_enemy_ids = lambda: []


# ===============================
# Main Game
# ===============================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Platform từ Tiled (Zoom camera + FPS)")
    clock = pygame.time.Clock()

    # Initialize sound system
    from game.sound_manager import SoundManager

    sound_manager = SoundManager()
    # Start background music if available
    sound_manager.play_music("background")

    font = pygame.font.SysFont("Arial", 24)

    # Load map (pass per-side hitbox inset from config)
    from game.config import (
        HITBOX_INSET,
        HITBOX_TOP_INSET,
        HITBOX_BOTTOM_INSET,
        HITBOX_LEFT_INSET,
        HITBOX_RIGHT_INSET,
        OBJECT_TILE_USE_BOTTOM_Y,
        OBJECT_TILE_Y_OFFSET,
        BG_TINT_ENABLED,
        BG_TINT_COLOR,
        BG_TINT_ALPHA,
    )

    # Build map path relative to the project root to avoid absolute paths
    repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    map_path = os.path.join(repo_root, "assets", "maps", "Map_test.tmx")
    platforms, tmx_data, map_objects, animated_objects, moving_platform_objects, portal_objects = load_map(
        map_path,
        hitbox_inset=HITBOX_INSET,
        top_inset=HITBOX_TOP_INSET,
        bottom_inset=HITBOX_BOTTOM_INSET,
        left_inset=HITBOX_LEFT_INSET,
        right_inset=HITBOX_RIGHT_INSET,
    )
    
    # Tách map_objects theo layer để vẽ đúng thứ tự
    decor2_tinh_objects = [obj for obj in map_objects if obj.get('layer_name', '').lower() == 'object_decor2_tinh']
    decor1_animation_objects = [obj for obj in animated_objects]  # Đã được tách riêng
    object_layer1_objects = [obj for obj in map_objects if obj.get('layer_name', '').lower() == 'object layer 1']
    
    # Tạo animated decorations manager
    animated_decor_manager = AnimatedDecorManager(
        animated_objects,
        use_bottom_y=OBJECT_TILE_USE_BOTTOM_Y,
        y_offset=OBJECT_TILE_Y_OFFSET
    )
    
    # Tạo moving platforms manager
    moving_platform_manager = MovingPlatformManager(
        moving_platform_objects,
        use_bottom_y=OBJECT_TILE_USE_BOTTOM_Y,
        y_offset=OBJECT_TILE_Y_OFFSET
    )
    
    # Tạo portal manager
    portal_manager = PortalManager()
    for portal_obj in portal_objects:
        props = portal_obj.get('properties', {})
        
        # Parse properties từ Tiled
        target_id = props.get('target')
        if target_id:
            # Convert target to int if it's string
            try:
                target_id = int(target_id)
            except (ValueError, TypeError):
                print(f"[Portal] Invalid target ID: {target_id}")
                continue
        else:
            print(f"[Portal] Portal {portal_obj.get('id')} không có target, bỏ qua")
            continue
        
        cooldown_ms = int(props.get('cooldown_ms', 1000))
        lockout_ms = int(props.get('lockout_ms', 0))  # Lockout cho player
        spawn_offset_x = int(props.get('spawn_offset_x', 0))
        spawn_offset_y = int(props.get('spawn_offset_y', 0))
        require_interact = 'interact' in props  # Nếu có property interact thì cần nhấn phím
        
        portal = Portal(
            obj_id=portal_obj.get('id'),
            x=portal_obj.get('x'),
            y=portal_obj.get('y'),
            width=portal_obj.get('width', 512),
            height=portal_obj.get('height', 512),
            target_id=target_id,
            tile_img=portal_obj.get('tile'),
            cooldown_ms=cooldown_ms,
            lockout_ms=lockout_ms,
            spawn_offset_x=spawn_offset_x,
            spawn_offset_y=spawn_offset_y,
            require_interact=require_interact
        )
        portal_manager.add_portal(portal)
    
    print(f"[Portal] Đã load {len(portal_manager.portals)} portals")

    # Tạo nhân vật
    # tìm object spawn trong map_objects (tìm theo name hoặc type)
    spawn = next(
        (
            o
            for o in map_objects
            if o.get("name") == "player_spawn" or o.get("type") == "player"
        ),
        None,
    )
    if spawn:
        sx = int(spawn.get("x", 20))
        sy = int(spawn.get("y", 20))
        spawn_pos = (sx, sy)
        # Nếu factory khả dụng, tạo player từ metadata (chọn character đầu tiên tìm được)
        ids = list_characters() if callable(list_characters) else []
        if create_player and ids:
            try:
                player = create_player(ids[0], sx, sy)
            except Exception:
                # fallback an toàn
                player = Player(sx, sy)
        else:
            player = Player(sx, sy)
        # Căn toạ độ spawn theo chân (midbottom) để khớp cách Tiled hiển thị point/rect
        try:
            player.rect.midbottom = spawn_pos
        except Exception:
            pass
    else:
        ids = list_characters() if callable(list_characters) else []
        if create_player and ids:
            try:
                player = create_player(ids[0], 1200, 9200)
                spawn_pos = (1200, 9200)
            except Exception:
                player = Player(1200, 9200)
                spawn_pos = (1200, 9200)
        else:
            player = Player(1200, 9200)
            spawn_pos = (1200, 9200)
        # Đồng nhất quy ước: đặt vị trí spawn theo chân nhân vật
        try:
            player.rect.midbottom = spawn_pos
        except Exception:
            pass

    # Spawn enemies in the user-defined rectangle
    import random

    ENEMY_SPAWN_MIN_X = 1000
    ENEMY_SPAWN_MAX_X = 14200
    ENEMY_SPAWN_MIN_Y = 1500
    ENEMY_SPAWN_MAX_Y = 9000
    ENEMY_COUNT = 12  # default number of enemies to spawn

    enemies = []
    # Determine possible enemy ids from registry (if available)
    if create_enemy:
        enemy_ids = list_enemy_ids() or ["golem_02", "golem_03"]
        for i in range(ENEMY_COUNT):
            ex = random.randint(ENEMY_SPAWN_MIN_X, ENEMY_SPAWN_MAX_X)
            ey = random.randint(ENEMY_SPAWN_MIN_Y, ENEMY_SPAWN_MAX_Y)
            eid = random.choice(enemy_ids)
            try:
                inst = create_enemy(eid, ex, ey)
                enemies.append(inst)
            except Exception:
                # fallback to simple patrol enemy if creation fails
                enemies.append(PatrolEnemy(ex, ey))
    else:
        # fallback: spawn classic PatrolEnemy instances
        for i in range(ENEMY_COUNT):
            ex = random.randint(ENEMY_SPAWN_MIN_X, ENEMY_SPAWN_MAX_X)
            ey = random.randint(ENEMY_SPAWN_MIN_Y, ENEMY_SPAWN_MAX_Y)
            enemies.append(PatrolEnemy(ex, ey))
    
    
    # Spawn BOSS - Troll Tank Boss tại các vị trí có platform
    if create_enemy:
        try:
            # Boss spawn positions (các vị trí có platform trong map)
            boss_spawn_positions = [
                (3500, 9000),   # Gần player spawn
                (6000, 8500),   # Khu vực giữa map
                (8500, 8000),   # Khu vực phải
                (2000, 9000),   # Rất gần player
            ]
            
            # Chọn vị trí đầu tiên (gần player nhất)
            boss_x, boss_y = boss_spawn_positions[0]
            boss = create_enemy('Troll1', x=boss_x, y=boss_y)
            enemies.append(boss)
            
            print(f"[BOSS] Spawned TROLL BOSS at ({boss_x}, {boss_y})")
            print(f"[BOSS] Player spawn at (1200, 9200)")
            print(f"[BOSS] Distance from player: X={boss_x - 1200}, Y={boss_y - 9200}")
            print(f"[BOSS] Boss has {len(enemies)} total enemies in list")
        except Exception as e:
            print(f"[ERROR] Failed to spawn Boss: {e}")
            import traceback
            traceback.print_exc()
    
    show_hitboxes = False  # Toggle hiển thị hitbox của từng bức tường (phím H)
    
    # Debug counter cho Boss
    debug_frame_counter = 0
    boss_instance = None
    for e in enemies:
        if hasattr(e, '__class__') and 'Boss' in e.__class__.__name__:
            boss_instance = e
            break

    running = True
    while running:
        ms = clock.tick(FPS)
        dt = ms / 1000.0
        
        # Debug Boss mỗi 60 frames (1 giây)
        debug_frame_counter += 1
        if debug_frame_counter >= 60 and boss_instance:
            print(f"[BOSS DEBUG] Frame {debug_frame_counter}: Boss at ({boss_instance.rect.centerx}, {boss_instance.rect.centery}), Player at ({player.rect.centerx}, {player.rect.centery})")
            print(f"[BOSS DEBUG] Camera at ({camera_x if 'camera_x' in locals() else 'N/A'}, {camera_y if 'camera_y' in locals() else 'N/A'})")
            debug_frame_counter = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Toggle hiển thị hitbox tường
                if event.key == pygame.K_h:
                    show_hitboxes = not show_hitboxes
                # If player died, allow respawn (R) or quit (Q)
                if hasattr(player, "alive") and not getattr(player, "alive"):
                    if event.key == pygame.K_r:
                        # Respawn: reset HP and position
                        try:
                            player.hp = getattr(player, "max_hp", 100)
                            player.alive = True
                            # move to spawn_pos if available
                            if "spawn_pos" in locals():
                                player.rect.midbottom = spawn_pos
                            player.state = "idle"
                            player.current_frame = 0
                            player.vel_x = 0
                            player.vel_y = 0
                        except Exception:
                            pass
                    elif event.key == pygame.K_q:
                        running = False

        # Logic game - only run updates when player is alive. When dead,
        # we'll still draw the last frame and show the death overlay while
        # listening for R/Q to respawn or quit.
        if getattr(player, "alive", True):
            # Update mana regeneration
            player.update_mana(dt)

            player.handle_input()
            # update skills with delta seconds (e.g. dash)
            if hasattr(player, "update_skills"):
                player.update_skills(dt)
            
            # Update moving platforms TRƯỚC để player collision với vị trí mới
            moving_platform_manager.update(dt)
            
            # Kết hợp static platforms với moving platforms cho collision
            all_platforms = list(platforms)  # Copy list platforms tĩnh
            moving_platform_rects = moving_platform_manager.get_platforms_for_collision()
            all_platforms.extend(moving_platform_rects)
            
            # Use consolidated move() which applies gravity and resolves collisions
            player.move(all_platforms)
            
            # Check portal collision và teleport
            portal = portal_manager.check_player_collision(player.rect)
            if portal:
                portal_manager.teleport_player(player, portal)
            
            # Check and restore speed after slow effect expires
            if hasattr(player, 'is_slowed') and player.is_slowed:
                import time
                if hasattr(player, 'slowed_until') and time.time() >= player.slowed_until:
                    # Restore original speed
                    if hasattr(player, '_original_speed'):
                        old_speed = player.speed
                        player.speed = player._original_speed
                    player.is_slowed = False
            
            player.update_animation()
        else:
            # freeze velocities to avoid physics progressing while dead
            try:
                player.vel_x = 0
                player.vel_y = 0
            except Exception:
                pass
        
        # Update animated decorations (always update, even when player is dead)
        animated_decor_manager.update(dt)

        # Render surface theo zoom
        render_w = int(WIDTH / ZOOM)
        render_h = int(HEIGHT / ZOOM)
        render_surface = pygame.Surface((render_w, render_h))

        # Compute map pixel size. Prefer tmx_data (if available). Fallback to
        # bounding box of platforms if tmx_data isn't present.
        try:
            map_w = int(tmx_data.width * tmx_data.tilewidth)
            map_h = int(tmx_data.height * tmx_data.tileheight)
        except Exception:
            # Fallback: derive from platforms geometry
            try:
                min_x = min((r.left for _, r in platforms))
                min_y = min((r.top for _, r in platforms))
                max_x = max((r.right for _, r in platforms))
                max_y = max((r.bottom for _, r in platforms))
                map_w = max_x - min_x
                map_h = max_y - min_y
            except Exception:
                # Ultimate fallback: treat map as large so clamping is a no-op
                map_w = render_w * 10
                map_h = render_h * 10

        # Camera center requested
        desired_cam_x = player.rect.centerx - render_w // 2
        desired_cam_y = player.rect.centery - render_h // 2

        # Clamp camera so it doesn't go outside the map. If the map is smaller
        # than the render area, max_camera will be 0 and camera stays at 0
        max_camera_x = max(0, map_w - render_w)
        max_camera_y = max(0, map_h - render_h)

        camera_x = max(0, min(desired_cam_x, max_camera_x))
        camera_y = max(0, min(desired_cam_y, max_camera_y))

        # Fill whole render surface black (area outside map will remain black)
        render_surface.fill((0, 0, 0))

        # Draw sky inside the map area only (so outside map stays black).
        # The map is at world coords starting at (0,0); relative to camera its
        # top-left is (-camera_x, -camera_y).
        try:
            sky_rect = pygame.Rect(-camera_x, -camera_y, map_w, map_h)
            pygame.draw.rect(render_surface, (135, 206, 235), sky_rect)
        except Exception:
            # If drawing sky fails for any reason, we silently continue with black background
            pass

        # === VẼ THEO THỨ TỰ LAYER (từ dưới lên trên) ===

        # Create a camera rect once and reuse to avoid per-object allocations
        camera_rect = pygame.Rect(camera_x, camera_y, render_w, render_h)
        obj_y_offset = int(OBJECT_TILE_Y_OFFSET)
        
        # 1. Vẽ Object_Decor2_Tinh (dưới cùng)
        for obj in decor2_tinh_objects:
            tile = obj.get("tile")
            if not tile:
                continue

            ox = int(obj.get("x", 0))
            oy = int(obj.get("y", 0))

            # If tile image provided, align it so that object's y is the bottom of the image.
            tw, th = tile.get_width(), tile.get_height()
            # Căn theo cấu hình: nếu y là đáy ảnh thì trừ chiều cao, ngược lại giữ nguyên
            if OBJECT_TILE_USE_BOTTOM_Y:
                oy_aligned = oy - th
            else:
                oy_aligned = oy
            # Áp dụng offset tinh chỉnh nếu cần
            oy_aligned += obj_y_offset

            # Build object's rect in world coordinates
            obj_rect_world = pygame.Rect(ox, oy_aligned, tw, th)

            # Only blit if intersects camera
            if not obj_rect_world.colliderect(camera_rect):
                continue

            # Draw (offset by camera)
            render_surface.blit(
                tile, (obj_rect_world.x - camera_x, obj_rect_world.y - camera_y)
            )
        
        # 2. Vẽ Object_Decor1_animation (animated decorations)
        animated_decor_manager.draw(render_surface, camera_x, camera_y, render_w, render_h)

        # 3. Phủ nền màu mờ (BG tint) TRƯỚC Object Layer 1 để nằm sau nó và trên Decor layers
        if BG_TINT_ENABLED:
            try:
                map_rect = pygame.Rect(0, 0, map_w, map_h)
                visible = map_rect.clip(camera_rect)
                if visible.width > 0 and visible.height > 0:
                    overlay = pygame.Surface((visible.width, visible.height), pygame.SRCALPHA)
                    r, g, b = BG_TINT_COLOR
                    overlay.fill((int(r), int(g), int(b), int(BG_TINT_ALPHA)))
                    render_surface.blit(overlay, (visible.x - camera_x, visible.y - camera_y))
            except Exception:
                pass

        # 4. Vẽ Object Layer 1 (static decorative objects)
        for obj in object_layer1_objects:
            tile = obj.get("tile")
            if not tile:
                continue

            ox = int(obj.get("x", 0))
            oy = int(obj.get("y", 0))

            # If tile image provided, align it so that object's y is the bottom of the image.
            tw, th = tile.get_width(), tile.get_height()
            # Căn theo cấu hình: nếu y là đáy ảnh thì trừ chiều cao, ngược lại giữ nguyên
            if OBJECT_TILE_USE_BOTTOM_Y:
                oy_aligned = oy - th
            else:
                oy_aligned = oy
            # Áp dụng offset tinh chỉnh nếu cần
            oy_aligned += obj_y_offset

            # Build object's rect in world coordinates
            obj_rect_world = pygame.Rect(ox, oy_aligned, tw, th)

            # Only blit if intersects camera
            if not obj_rect_world.colliderect(camera_rect):
                continue

            # Draw (offset by camera)
            render_surface.blit(
                tile, (obj_rect_world.x - camera_x, obj_rect_world.y - camera_y)
            )

        # 5. Vẽ tile layer "nen" (trên cùng)
        # Precompute draw insets to avoid recomputing inside the loop
        left_draw_inset = int(HITBOX_LEFT_INSET or HITBOX_INSET)
        top_draw_inset = int(HITBOX_TOP_INSET or HITBOX_INSET)
        for tile_img, rect in platforms:
            if (
                rect.right > camera_x
                and rect.left < camera_x + render_w
                and rect.bottom > camera_y
                and rect.top < camera_y + render_h
            ):
                # Vẽ tile theo toạ độ gốc của Tiled (không dùng inset),
                # chỉ dùng inset cho va chạm. Khôi phục toạ độ gốc bằng cách trừ inset đã cộng khi build rect.
                draw_x = rect.x - left_draw_inset - camera_x
                draw_y = rect.y - top_draw_inset - camera_y
                render_surface.blit(tile_img, (draw_x, draw_y))
        
        # Draw portals (vẽ trước moving platforms)
        portal_manager.draw(render_surface, camera_x, camera_y, render_w, render_h)
        
        # Draw moving platforms (vẽ sau portals)
        moving_platform_manager.draw(render_surface, camera_x, camera_y, render_w, render_h)

        # Nếu bật debug, vẽ hitbox của từng bức tường (chỉ phần đang trong camera)
        if show_hitboxes:
            for _, rect in platforms:
                if (
                    rect.right > camera_x
                    and rect.left < camera_x + render_w
                    and rect.bottom > camera_y
                    and rect.top < camera_y + render_h
                ):
                    draw_rect = pygame.Rect(
                        rect.x - camera_x, rect.y - camera_y, rect.width, rect.height
                    )
                    # Vẽ outline đỏ dày 2px
                    pygame.draw.rect(render_surface, (255, 0, 0), draw_rect, 2)

        # Vẽ nhân vật
        player.draw(render_surface, camera_x, camera_y)

        # Chỉ cập nhật và vẽ enemies nằm trong vùng hoạt động (gần camera)
        # để tránh update nhiều đối tượng ở xa gây lag.
        activity_margin = 800  # pixels mở rộng quanh camera để 'kích hoạt' enemy
        active_rect = pygame.Rect(
            camera_x - activity_margin,
            camera_y - activity_margin,
            render_w + activity_margin * 2,
            render_h + activity_margin * 2,
        )

        # Lọc platforms chỉ trong vùng hoạt động để giảm chi phí va chạm
        nearby_platforms = [p for p in platforms if p[1].colliderect(active_rect)]

        for e in enemies:
            # Boss luôn được update và vẽ (không bị giới hạn bởi active_rect)
            is_boss = hasattr(e, '__class__') and 'Boss' in e.__class__.__name__
            
            # Nếu enemy nằm trong vùng hoạt động HOẶC là Boss, cập nhật và vẽ
            if is_boss or e.rect.colliderect(active_rect):
                # Only update enemy AI when player is alive; otherwise keep them frozen
                if getattr(player, "alive", True):
                    e.update(dt, nearby_platforms, player)
               
                if getattr(player, "alive", True):
                    # Boss cần ALL platforms, không chỉ nearby (vì có thể ở xa player)
                    if is_boss:
                        # Lấy platforms xung quanh Boss (không phải player)
                        boss_active_rect = pygame.Rect(
                            e.rect.centerx - render_w // 2 - activity_margin,
                            e.rect.centery - render_h // 2 - activity_margin,
                            render_w + activity_margin * 2,
                            render_h + activity_margin * 2,
                        )
                        boss_platforms = [p for p in platforms if p[1].colliderect(boss_active_rect)]
                        e.update(dt, boss_platforms, player)
                    else:
                        e.update(dt, nearby_platforms, player)

                e.draw(render_surface, camera_x, camera_y, show_hitboxes)
            else:
                # Nếu ở xa, bỏ qua update nặng; vẫn có thể áp dụng một cập nhật tối giản
                # như giảm tick timer mỗi vài frame nếu cần (để tiết kiệm CPU chúng ta skip hoàn toàn)
                pass

        # Handle projectile -> enemy collisions from player's skills (only while alive)
        if getattr(player, "alive", True):
            for name, s in getattr(player, "skills", {}).items():
                if not isinstance(s, dict) and hasattr(s, "handle_collisions"):
                    try:
                        s.handle_collisions(enemies)
                    except Exception:
                        pass

        # Remove dead enemies from the list to avoid further processing
        enemies = [en for en in enemies if not getattr(en, "dead", False)]

        # Scale ra màn hình
        scaled_surface = pygame.transform.scale(render_surface, (WIDTH, HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        # Visual feedback khi bị slow
        if hasattr(player, 'is_slowed') and player.is_slowed:
            # Tạo overlay màu tím với alpha
            slow_overlay = pygame.Surface((WIDTH, HEIGHT))
            slow_overlay.set_alpha(30)  # Độ trong suốt
            slow_overlay.fill((128, 0, 255))  # Màu tím
            screen.blit(slow_overlay, (0, 0))
            
            # Hiển thị text SLOWED!
            import time
            if hasattr(player, 'slowed_until'):
                remaining = max(0, player.slowed_until - time.time())
                slow_text = font.render(f"SLOWED! ({remaining:.1f}s)", True, (255, 0, 255))
                text_rect = slow_text.get_rect(center=(WIDTH // 2, 100))
                screen.blit(slow_text, text_rect)

        # Hiển thị FPS
        fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (0, 0, 0))
        screen.blit(fps_text, (10, 10))
        # Hint nhỏ cho toggle hitbox
        hint_text = font.render(
            f"H: Toggle wall hitboxes ({'ON' if show_hitboxes else 'OFF'})",
            True,
            (0, 0, 0),
        )
        screen.blit(hint_text, (10, 40))

        # Hiển thị thanh HP đồ họa và tọa độ người chơi (world coordinates)
        try:
            # Player HP bar: fixed position at bottom center
            if (
                hasattr(player, "hp")
                and hasattr(player, "max_hp")
                and player.max_hp > 0
            ):
                # Larger bars with fixed position at bottom
                bar_w = 400  # Wider bar
                bar_h = 25  # Taller bar
                bar_x = WIDTH // 2 - bar_w // 2  # Center horizontally
                bar_y = HEIGHT - 100  # Fixed distance from bottom

                # Draw black background for better visibility
                bg_padding = 4
                pygame.draw.rect(
                    screen,
                    (0, 0, 0),
                    (
                        bar_x - bg_padding,
                        bar_y - bg_padding,
                        bar_w + bg_padding * 2,
                        bar_h + bg_padding * 2,
                    ),
                )

                # HP bar background
                pygame.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h))
                pct = max(0.0, min(1.0, float(player.hp) / float(player.max_hp)))
                fill_w = int(bar_w * pct)

                # color lerp: red -> yellow -> green
                if pct > 0.6:
                    col = (50, 205, 50)
                elif pct > 0.3:
                    col = (255, 200, 0)
                else:
                    col = (220, 30, 30)

                if fill_w > 0:
                    pygame.draw.rect(screen, col, (bar_x, bar_y, fill_w, bar_h))
                pygame.draw.rect(
                    screen, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h), 2
                )

                # numeric text inside bar with larger font
                try:
                    hp_font = pygame.font.SysFont("Arial", 20)  # Larger font
                    hp_label = hp_font.render(
                        f"{int(player.hp)}/{int(player.max_hp)}", True, (255, 255, 255)
                    )
                    lbl_rect = hp_label.get_rect(
                        center=(bar_x + bar_w // 2, bar_y + bar_h // 2)
                    )
                    # Draw text with black outline for better visibility
                    outline_color = (0, 0, 0)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        screen.blit(hp_label, (lbl_rect.x + dx, lbl_rect.y + dy))
                    screen.blit(hp_label, lbl_rect)
                except Exception:
                    pass

                # Always draw mana bar
                try:
                    # Calculate mana percentage based on current mana or charging state
                    if getattr(player, "_is_charging", False):
                        # When charging, show decreasing energy
                        now = pygame.time.get_ticks() / 1000.0
                        held = now - getattr(player, "_charge_start", now)
                        charge_skill = getattr(player, "skills", {}).get("charge")
                        max_charge = (
                            getattr(charge_skill, "max_charge", 3.0)
                            if charge_skill is not None
                            else 3.0
                        )
                        pct = 1.0 - max(0.0, min(1.0, held / float(max_charge)))
                    else:
                        # When not charging, show current mana
                        pct = float(player.mana) / float(player.max_mana)

                    # Energy/Mana bar with same width but smaller height
                    cbar_w = bar_w
                    cbar_h = 20  # Slightly smaller than HP bar
                    cbar_x = bar_x
                    cbar_y = bar_y + bar_h + 4  # Closer to HP bar

                    # Black background for energy bar
                    pygame.draw.rect(
                        screen,
                        (0, 0, 0),
                        (
                            cbar_x - bg_padding,
                            cbar_y - bg_padding,
                            cbar_w + bg_padding * 2,
                            cbar_h + bg_padding * 2,
                        ),
                    )

                    # Energy bar background
                    pygame.draw.rect(
                        screen, (40, 40, 40), (cbar_x, cbar_y, cbar_w, cbar_h)
                    )
                    fill_w = int(cbar_w * pct)
                    if fill_w > 0:
                        pygame.draw.rect(
                            screen,
                            (0, 128, 255),  # Bright blue for energy
                            (cbar_x, cbar_y, fill_w, cbar_h),
                        )
                    pygame.draw.rect(
                        screen, (255, 255, 255), (cbar_x, cbar_y, cbar_w, cbar_h), 2
                    )

                    # Draw mana text
                    try:
                        energy_font = pygame.font.SysFont("Arial", 18)
                        if getattr(player, "_is_charging", False):
                            mana_text = f"ENERGY {int(pct * 100)}%"
                            # Add charging indicator
                            pygame.draw.circle(
                                screen,
                                (0, 128, 255),
                                (cbar_x + cbar_w + 20, cbar_y + cbar_h // 2),
                                6,
                            )
                        else:
                            mana_text = (
                                f"ENERGY {int(player.mana)}/{int(player.max_mana)}"
                            )

                        pct_label = energy_font.render(mana_text, True, (255, 255, 255))
                        pct_rect = pct_label.get_rect(
                            center=(cbar_x + cbar_w // 2, cbar_y + cbar_h // 2)
                        )
                        # Draw text with black outline
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            screen.blit(pct_label, (pct_rect.x + dx, pct_rect.y + dy))
                        screen.blit(pct_label, pct_rect)
                    except Exception:
                        pass
                except Exception:
                    pass

            px = int(player.rect.centerx)
            py = int(player.rect.centery)
            coord_text = font.render(f"Pos: x={px} y={py}", True, (0, 0, 0))
            screen.blit(coord_text, (10, 100))
        except Exception:
            # Nếu player chưa có rect hoặc lỗi, im lặng
            pass

        # Nếu người chơi đã chết, vẽ overlay thông báo và chờ phím R/Q (respawn/quit)
        try:
            if hasattr(player, "alive") and not player.alive:
                # semi-transparent dark overlay
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                screen.blit(overlay, (0, 0))
                big_font = pygame.font.SysFont("Arial", 64)
                small_font = pygame.font.SysFont("Arial", 28)
                text = big_font.render("YOU DIED", True, (255, 50, 50))
                text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40))
                screen.blit(text, text_rect)
                info = small_font.render(
                    "Press R to respawn or Q to quit", True, (220, 220, 220)
                )
                info_rect = info.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
                screen.blit(info, info_rect)
        except Exception:
            pass

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

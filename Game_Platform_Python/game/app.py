import pygame
import sys
import os
from game.config import WIDTH, HEIGHT, FPS, ZOOM, PLAYER_SCALE
from game.map_loader import load_map
from game.player import Player
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

    font = pygame.font.SysFont("Arial", 24)

    # Load map (pass per-side hitbox inset from config)
    from game.config import (
        HITBOX_INSET,
        HITBOX_TOP_INSET,
        HITBOX_BOTTOM_INSET,
        HITBOX_LEFT_INSET,
        HITBOX_RIGHT_INSET,
    )
    platforms, _, map_objects = load_map(
        "D:/Game_Platform_Python-main/Game_Platform_Python-main/Game_Platform_Python/assets/maps/Map_test.tmx",
        hitbox_inset=HITBOX_INSET,
        top_inset=HITBOX_TOP_INSET,
        bottom_inset=HITBOX_BOTTOM_INSET,
        left_inset=HITBOX_LEFT_INSET,
        right_inset=HITBOX_RIGHT_INSET,
    )

    # Tạo nhân vật
    # tìm object spawn trong map_objects (tìm theo name hoặc type)
    spawn = next(
        (o for o in map_objects if o.get('name') == 'player_spawn' or o.get('type') == 'player'),
        None
    )
    if spawn:
        sx = int(spawn.get('x', 20))
        sy = int(spawn.get('y', 20))
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
        enemy_ids = list_enemy_ids() or ['golem_02', 'golem_03']
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
                if hasattr(player, 'alive') and not getattr(player, 'alive'):
                    if event.key == pygame.K_r:
                        # Respawn: reset HP and position
                        try:
                            player.hp = getattr(player, 'max_hp', 100)
                            player.alive = True
                            # move to spawn_pos if available
                            if 'spawn_pos' in locals():
                                player.rect.midbottom = spawn_pos
                            player.state = 'idle'
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
        if getattr(player, 'alive', True):
            player.handle_input()
            # update skills with delta seconds (e.g. dash)
            if hasattr(player, 'update_skills'):
                player.update_skills(dt)
            # Use consolidated move() which applies gravity and resolves collisions
            player.move(platforms)
            
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

        # Render surface theo zoom
        render_w = int(WIDTH / ZOOM)
        render_h = int(HEIGHT / ZOOM)
        render_surface = pygame.Surface((render_w, render_h))
        render_surface.fill((135, 206, 235))

        camera_x = player.rect.centerx - render_w // 2
        camera_y = player.rect.centery - render_h // 2

        for tile_img, rect in platforms:
            if rect.right > camera_x and rect.left < camera_x + render_w and \
               rect.bottom > camera_y and rect.top < camera_y + render_h:
                render_surface.blit(tile_img,
                                    (rect.x - camera_x, rect.y - camera_y))

        # Draw object-layer tiles (e.g. large decorative tiles from object layer)
        for obj in map_objects:
            tile = obj.get('tile')
            if not tile:
                continue

            ox = int(obj.get('x', 0))
            oy = int(obj.get('y', 0))

            # If tile image provided, align it so that object's y is the bottom of the image.
            tw, th = tile.get_width(), tile.get_height()
            # Tiled thường lưu y cho tile object là bottom -> substract tile height
            oy_aligned = oy - th

            # Build object's rect in world coordinates
            obj_rect_world = pygame.Rect(ox, oy_aligned, tw, th)

            # Camera rect in world coordinates
            camera_rect = pygame.Rect(camera_x, camera_y, render_w, render_h)

            # Only blit if intersects camera
            if not obj_rect_world.colliderect(camera_rect):
                continue

            # Draw (offset by camera)
            render_surface.blit(tile, (obj_rect_world.x - camera_x, obj_rect_world.y - camera_y))

        # Nếu bật debug, vẽ hitbox của từng bức tường (chỉ phần đang trong camera)
        if show_hitboxes:
            for _, rect in platforms:
                if rect.right > camera_x and rect.left < camera_x + render_w and \
                   rect.bottom > camera_y and rect.top < camera_y + render_h:
                    draw_rect = pygame.Rect(rect.x - camera_x, rect.y - camera_y,
                                            rect.width, rect.height)
                    # Vẽ outline đỏ dày 2px
                    pygame.draw.rect(render_surface, (255, 0, 0), draw_rect, 2)

        # Vẽ nhân vật
        player.draw(render_surface, camera_x, camera_y)

        # Chỉ cập nhật và vẽ enemies nằm trong vùng hoạt động (gần camera)
        # để tránh update nhiều đối tượng ở xa gây lag.
        activity_margin = 800  # pixels mở rộng quanh camera để 'kích hoạt' enemy
        active_rect = pygame.Rect(camera_x - activity_margin, camera_y - activity_margin,
                                  render_w + activity_margin * 2, render_h + activity_margin * 2)

        # Lọc platforms chỉ trong vùng hoạt động để giảm chi phí va chạm
        nearby_platforms = [p for p in platforms if p[1].colliderect(active_rect)]

        for e in enemies:
            # Boss luôn được update và vẽ (không bị giới hạn bởi active_rect)
            is_boss = hasattr(e, '__class__') and 'Boss' in e.__class__.__name__
            
            # Nếu enemy nằm trong vùng hoạt động HOẶC là Boss, cập nhật và vẽ
            if is_boss or e.rect.colliderect(active_rect):
                # Only update enemy AI when player is alive; otherwise keep them frozen
                if getattr(player, 'alive', True):
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
        if getattr(player, 'alive', True):
            for name, s in getattr(player, 'skills', {}).items():
                if not isinstance(s, dict) and hasattr(s, 'handle_collisions'):
                    try:
                        s.handle_collisions(enemies)
                    except Exception:
                        pass

        # Remove dead enemies from the list to avoid further processing
        enemies = [en for en in enemies if not getattr(en, 'dead', False)]

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
        hint_text = font.render(f"H: Toggle wall hitboxes ({'ON' if show_hitboxes else 'OFF'})", True, (0, 0, 0))
        screen.blit(hint_text, (10, 40))

        # Hiển thị thanh HP đồ họa và tọa độ người chơi (world coordinates)
        try:
            # Player HP bar: top-left, 200x18
            if hasattr(player, 'hp') and hasattr(player, 'max_hp') and player.max_hp > 0:
                bar_x = 10
                bar_y = 70
                bar_w = 200
                bar_h = 18
                # background
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
                pygame.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_w, bar_h), 2)
                # numeric text inside bar
                try:
                    hp_label = font.render(f"{int(player.hp)}/{int(player.max_hp)}", True, (0, 0, 0))
                    lbl_rect = hp_label.get_rect(center=(bar_x + bar_w // 2, bar_y + bar_h // 2))
                    screen.blit(hp_label, lbl_rect)
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
            if hasattr(player, 'alive') and not player.alive:
                # semi-transparent dark overlay
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                screen.blit(overlay, (0, 0))
                big_font = pygame.font.SysFont("Arial", 64)
                small_font = pygame.font.SysFont("Arial", 28)
                text = big_font.render("YOU DIED", True, (255, 50, 50))
                text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40))
                screen.blit(text, text_rect)
                info = small_font.render("Press R to respawn or Q to quit", True, (220, 220, 220))
                info_rect = info.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
                screen.blit(info, info_rect)
        except Exception:
            pass

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

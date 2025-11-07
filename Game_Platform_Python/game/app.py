import pygame
import sys
import os
from game.config import WIDTH, HEIGHT, FPS, ZOOM, PLAYER_SCALE
from game.map_loader import load_map
from game.player import Player
from game.pause_menu import PauseMenu
from game.character_select import CharacterSelectMenu

# Nếu package characters được cài, dùng factory để tạo nhân vật từ metadata
try:
    from game.characters.factory import create_player, list_characters
except Exception:
    create_player = None
    list_characters = lambda: []
from game.menu import Menu
from game.enemy import PatrolEnemy

# Try to import enemy registry helpers (optional)
try:
    from game.enemy_registry import create_enemy, list_enemies as list_enemy_ids
    # Import enemy module to trigger registration
    import game.enemy
except Exception:
    create_enemy = None
    list_enemy_ids = lambda: []


# ===============================
# Main Game
# ===============================
def run_game():
    """Legacy function - redirects to main for compatibility"""
    main()

def run_game_session(screen, selected_char):
    """Run a single game session with the given character and return the result"""
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
    )

    # Build map path relative to the project root to avoid absolute paths
    repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    map_path = os.path.join(repo_root, "assets", "maps", "Map_test.tmx")
    platforms, tmx_data, map_objects = load_map(
        map_path,
        hitbox_inset=HITBOX_INSET,
        top_inset=HITBOX_TOP_INSET,
        bottom_inset=HITBOX_BOTTOM_INSET,
        left_inset=HITBOX_LEFT_INSET,
        right_inset=HITBOX_RIGHT_INSET,
    )

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
        # Tạo player dựa trên nhân vật được chọn
        try:
            print(f"Creating player with selected character: {selected_char}")

            # Ưu tiên sử dụng factory để tạo player từ metadata
            if create_player:
                player = create_player(selected_char, sx, sy)
                player.character_type = (
                    selected_char  # Set character type for reference
                )
                print(f"Created {selected_char} player using factory: {type(player)}")

                # Debug thông tin về các frames đã load
                print(f"Loaded animations for {selected_char}:")
                for state, frames in player.animations.items():
                    print(f"  {state}: {len(frames)} frames")
            else:
                # Fallback: tạo player cơ bản nếu factory không khả dụng
                player = Player(sx, sy)
                player.character_type = selected_char
                print(f"Created basic player (factory not available)")

            # Áp dụng scale cho player
            if hasattr(player, "image") and player.image:
                current_rect = player.image.get_rect()
                new_width = int(current_rect.width * PLAYER_SCALE)
                new_height = int(current_rect.height * PLAYER_SCALE)
                player.image = pygame.transform.scale(
                    player.image, (new_width, new_height)
                )

        except Exception as e:
            print(f"Error creating player: {e}")
            import traceback

            traceback.print_exc()
            # fallback an toàn nếu có lỗi
            print(f"FALLBACK: Creating basic Player because of error")
            player = Player(sx, sy)
            player.character_type = "fallback"
        # Căn toạ độ spawn theo chân (midbottom) để khớp cách Tiled hiển thị point/rect
        try:
            player.rect.midbottom = spawn_pos
        except Exception:
            pass
    else:
        print("WARNING: No spawn point found in map, using default position")
        # Vẫn sử dụng nhân vật được chọn ngay cả khi không có spawn point
        if create_player:
            try:
                print(
                    f"Creating selected character {selected_char} at default position"
                )
                player = create_player(selected_char, 1200, 9200)
                player.character_type = selected_char
                spawn_pos = (1200, 9200)
            except Exception:
                print("FALLBACK: Creating basic Player because factory failed")
                player = Player(1200, 9200)
                player.character_type = "basic_fallback"
                spawn_pos = (1200, 9200)
        else:
            print("FALLBACK: Creating basic Player because no factory or characters")
            player = Player(1200, 9200)
            player.character_type = "no_factory_fallback"
            spawn_pos = (1200, 9200)
        # Đồng nhất quy ước: đặt vị trí spawn theo chân nhân vật
        try:
            player.rect.midbottom = spawn_pos
        except Exception:
            pass

    # Spawn 5 enemies near player
    import random
    import math

    # ============================================
    # HỆ THỐNG GIAI ĐOẠN (STAGES)
    # ============================================
    
    # Cấu hình các giai đoạn
    STAGES = [
        {
            'name': 'Stage 1',
            'enemy_count': 5,
            'spawn_center': (2649, 9200),
            'enemy_types': ['Golem_02', 'Golem_03', 'minotaur_01', 'Wraith_01'],
            'boss': 'Troll1'
        },
        {
            'name': 'Stage 2',
            'enemy_count': 7,
            'spawn_center': (2649, 9200),  # Spawn gần player để test
            'enemy_types': ['minotaur_01', 'minotaur_02', 'Wraith_01', 'Wraith_03'],
            'boss': 'Troll1'
        },
        {
            'name': 'Stage 3',
            'enemy_count': 10,
            'spawn_center': (2649, 9200),  # Spawn theo vị trí player
            'enemy_types': ['Golem_02', 'Golem_03', 'minotaur_01', 'minotaur_02', 'Wraith_01', 'Wraith_03'],
            'boss': 'Troll1'
        }
    ]
    
    current_stage = 0  # Giai đoạn hiện tại (0 = Stage 1, 1 = Stage 2)
    stage_completed = False
    
    def spawn_stage_enemies(stage_index):
        """Spawn enemies cho giai đoạn cụ thể"""
        if stage_index >= len(STAGES):
            print(f"[STAGE] No more stages!")
            return [], []
        
        stage = STAGES[stage_index]
        # Compact log để spawn nhanh hơn
        print(f"[STAGE] {stage['name']}: Spawning {stage['enemy_count']} enemies at {stage['spawn_center']}")
        
        stage_enemies = []
        stage_enemy_ids = []
        enemy_count = stage['enemy_count']
        spawn_center = stage['spawn_center']
        enemy_types = stage.get('enemy_types', ['Golem_02', 'Golem_03'])
        
        if create_enemy:
            # Batch spawn để tăng tốc độ
            for i in range(enemy_count):
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(50, 150)
                ex = int(spawn_center[0] + math.cos(angle) * distance)
                ey = int(spawn_center[1] + math.sin(angle) * distance)
                
                eid = random.choice(enemy_types)
                inst = None
                try:
                    inst = create_enemy(eid, ex, ey)
                    # Tắt log chi tiết để spawn nhanh hơn
                except Exception as e:
                    # Silent fallback
                    try:
                        inst = PatrolEnemy(ex, ey)
                    except Exception:
                        pass
                
                if inst:
                    stage_enemies.append(inst)
                    stage_enemy_ids.append(id(inst))
        else:
            # Fallback
            for i in range(enemy_count):
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(50, 150)
                ex = int(spawn_center[0] + math.cos(angle) * distance)
                ey = int(spawn_center[1] + math.sin(angle) * distance)
                inst = PatrolEnemy(ex, ey)
                stage_enemies.append(inst)
                stage_enemy_ids.append(id(inst))
        
        # Ensure enough enemies
        while len(stage_enemies) < enemy_count:
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(50, 150)
            ex = int(spawn_center[0] + math.cos(angle) * distance)
            ey = int(spawn_center[1] + math.sin(angle) * distance)
            try:
                inst = PatrolEnemy(ex, ey)
                stage_enemies.append(inst)
                stage_enemy_ids.append(id(inst))
            except Exception:
                break
        
        print(f"[STAGE] ✓ Spawned {len(stage_enemies)}/{enemy_count} enemies")
        return stage_enemies, stage_enemy_ids
    
    # ============================================
    # PRELOAD ANIMATIONS
    # ============================================
    # Collect tất cả enemy types từ tất cả stages
    all_enemy_types = set()
    for stage in STAGES:
        all_enemy_types.update(stage.get('enemy_types', []))
        if stage.get('boss'):
            all_enemy_types.add(stage['boss'])
    
    # Preload để tránh lag khi spawn
    if create_enemy:
        from game.characters.factory import preload_enemies
        preload_enemies(list(all_enemy_types))
    
    # ============================================
    # SPAWN STAGE 1
    # ============================================
    # Spawn Stage 1
    enemies, initial_enemies_ids = spawn_stage_enemies(current_stage)
    INITIAL_ENEMY_COUNT = STAGES[current_stage]['enemy_count']  # Lấy số lượng từ config
    
    print(f"[SPAWN] Boss will appear after defeating all {INITIAL_ENEMY_COUNT} enemies")
    
    # Verify we have enough enemies
    if len(enemies) != INITIAL_ENEMY_COUNT:
        print(f"[WARNING] Expected {INITIAL_ENEMY_COUNT} enemies but got {len(enemies)}")
    else:
        print(f"[SUCCESS] All {INITIAL_ENEMY_COUNT} enemies spawned successfully!")
    
    # Boss tracking variables
    boss_spawned = False
    boss_instance = None
    initial_enemies_killed = 0
    boss_spawn_message_timer = 0.0  # Timer cho thông báo boss spawn
    boss_spawn_message_duration = 5.0  # Hiển thị 5 giây
    
    # Stage transition notification
    stage_notification = ""
    stage_notification_type = "normal"  # "cleared", "new_stage", "victory"
    stage_notification_timer = 0.0
    stage_notification_duration = 10.0  # Hiển thị 10 giây - RẤT LÂU
    game_won = False  # Track if player has won the game

    show_hitboxes = False  # Toggle hiển thị hitbox của từng bức tường (phím H)

    # Debug counter
    debug_frame_counter = 0

    running = True
    while running:
        ms = clock.tick(FPS)
        dt = ms / 1000.0

        # Debug thông tin mỗi giây
        debug_frame_counter += 1
        if debug_frame_counter >= 60:
            alive_enemies = [e for e in enemies if not getattr(e, "dead", False)]
            print(f"[DEBUG] Enemies alive: {len(alive_enemies)}, Boss spawned: {boss_spawned}")
            if boss_instance:
                print(f"[BOSS] Boss at ({boss_instance.rect.centerx}, {boss_instance.rect.centery})")
            debug_frame_counter = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Toggle hiển thị hitbox tường
                if event.key == pygame.K_h:
                    show_hitboxes = not show_hitboxes
                # Handle ESC for pause menu
                elif event.key == pygame.K_ESCAPE:
                    # Create and show pause menu
                    pause_menu = PauseMenu(screen, scaled_surface)
                    pause_result = pause_menu.run()
                    if pause_result == "exit":
                        running = False
                    elif pause_result == "main_menu":
                        # Return to main menu
                        return "main_menu"
                    elif pause_result == "play_again":
                        # Restart the current game
                        return "play_again"
                    # If continue, just resume the game loop

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
                
                # If game won, allow play again (R) or quit (Q)
                if game_won:
                    if event.key == pygame.K_r:
                        return "play_again"
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
            # Use consolidated move() which applies gravity and resolves collisions
            player.move(platforms)

            # Check and restore speed after slow effect expires
            if hasattr(player, "is_slowed") and player.is_slowed:
                import time

                if (
                    hasattr(player, "slowed_until")
                    and time.time() >= player.slowed_until
                ):
                    # Restore original speed
                    if hasattr(player, "_original_speed"):
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

        for tile_img, rect in platforms:
            if (
                rect.right > camera_x
                and rect.left < camera_x + render_w
                and rect.bottom > camera_y
                and rect.top < camera_y + render_h
            ):
                # Vẽ tile theo toạ độ gốc của Tiled (không dùng inset),
                # chỉ dùng inset cho va chạm. Khôi phục toạ độ gốc bằng cách trừ inset đã cộng khi build rect.
                left_draw_inset = int(HITBOX_LEFT_INSET or HITBOX_INSET)
                top_draw_inset = int(HITBOX_TOP_INSET or HITBOX_INSET)
                draw_x = rect.x - left_draw_inset - camera_x
                draw_y = rect.y - top_draw_inset - camera_y
                render_surface.blit(tile_img, (draw_x, draw_y))

        # Draw object-layer tiles (e.g. large decorative tiles from object layer)
        for obj in map_objects:
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
            oy_aligned += int(OBJECT_TILE_Y_OFFSET)

            # Build object's rect in world coordinates
            obj_rect_world = pygame.Rect(ox, oy_aligned, tw, th)

            # Camera rect in world coordinates
            camera_rect = pygame.Rect(camera_x, camera_y, render_w, render_h)

            # Only blit if intersects camera
            if not obj_rect_world.colliderect(camera_rect):
                continue

            # Draw (offset by camera)
            render_surface.blit(
                tile, (obj_rect_world.x - camera_x, obj_rect_world.y - camera_y)
            )

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
            is_boss = hasattr(e, "__class__") and "Boss" in e.__class__.__name__

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
                        boss_platforms = [
                            p for p in platforms if p[1].colliderect(boss_active_rect)
                        ]
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

        # Track initial enemies killed and spawn boss when all are defeated
        if not boss_spawned and len(initial_enemies_ids) > 0:
            # Count how many initial enemies are still alive
            current_ids = [id(e) for e in enemies if not getattr(e, "dead", False)]
            alive_initial = sum(1 for eid in initial_enemies_ids if eid in current_ids)
            initial_enemies_killed = INITIAL_ENEMY_COUNT - alive_initial
            
            # If all initial enemies are dead, spawn boss
            if alive_initial == 0:
                print(f"\n{'='*50}")
                print(f"[BOSS] All {INITIAL_ENEMY_COUNT} enemies defeated!")
                
                # Show stage cleared notification IMMEDIATELY
                stage_notification = f"{STAGES[current_stage]['name'].upper()} CLEARED!"
                stage_notification_type = "cleared"
                # Stage 1: 6s, Stage 2: 8s, Stage 3: 8s
                if current_stage == 0:
                    stage_notification_timer = 6.0
                else:
                    stage_notification_timer = 8.0
                
                print(f"[BOSS] Spawning BOSS near player...")
                print(f"[BOSS] Current player position: X={player.rect.centerx}, Y={player.rect.centery}")
                print(f"{'='*50}\n")
                
                if create_enemy:
                    try:
                        # Tìm platform gần player để spawn boss
                        offset = random.choice([250, 300, 350])
                        boss_x = int(player.rect.centerx + offset)
                        
                        # Tìm platform phía dưới player (hoặc gần player)
                        nearest_platform_y = None
                        search_radius = 2000  # Tìm trong bán kính 2000px
                        
                        print(f"[BOSS] Searching for platform near player...")
                        for _, platform_rect in platforms:
                            # Tìm platform gần vị trí boss_x
                            if abs(platform_rect.centerx - boss_x) < 1000:
                                # Platform phải ở dưới player hoặc gần player (trong range ±2000)
                                if abs(platform_rect.top - player.rect.centery) < search_radius:
                                    if nearest_platform_y is None or abs(platform_rect.top - player.rect.centery) < abs(nearest_platform_y - player.rect.centery):
                                        nearest_platform_y = platform_rect.top
                        
                        # Nếu tìm thấy platform, spawn trên đó
                        if nearest_platform_y is not None:
                            boss_y = nearest_platform_y
                            print(f"[BOSS] Found platform at Y={boss_y} (distance from player: {abs(boss_y - player.rect.centery)}px)")
                        else:
                            # Không tìm thấy - tìm platform gần nhất bất kỳ
                            print(f"[BOSS WARNING] No platform near player, searching globally...")
                            for _, platform_rect in platforms:
                                if nearest_platform_y is None or abs(platform_rect.top - player.rect.centery) < abs(nearest_platform_y - player.rect.centery):
                                    nearest_platform_y = platform_rect.top
                            
                            if nearest_platform_y:
                                boss_y = nearest_platform_y
                                print(f"[BOSS] Found global platform at Y={boss_y}")
                            else:
                                boss_y = player.rect.centery
                                print(f"[BOSS ERROR] No platform found at all! Using player Y={boss_y}")
                        
                        print(f"[BOSS] Calculating spawn position...")
                        print(f"[BOSS] Player X: {player.rect.centerx}, Boss offset: +{offset}")
                        print(f"[BOSS] Boss will spawn at: ({boss_x}, {boss_y})")
                        
                        boss_instance = create_enemy("Troll1", x=boss_x, y=boss_y)
                        enemies.append(boss_instance)
                        boss_spawned = True
                        boss_spawn_message_timer = boss_spawn_message_duration  # Bật thông báo
                        
                        distance_x = boss_x - player.rect.centerx
                        distance_y = abs(boss_y - player.rect.centery)
                        print(f"[BOSS] ✅ TROLL BOSS spawned successfully!")
                        print(f"[BOSS] Boss position: ({boss_x}, {boss_y})")
                        print(f"[BOSS] Player position: ({player.rect.centerx}, {player.rect.centery})")
                        print(f"[BOSS] Distance X: {distance_x} pixels, Distance Y: {distance_y} pixels")
                        if distance_y < 500:
                            print(f"[BOSS] Boss is on same level as player!")
                        else:
                            print(f"[BOSS] Boss is on different level - navigate to Y={boss_y}")
                        print(f"{'='*50}\n")
                        
                        # Play boss spawn sound if available
                        try:
                            sound_manager.play_sound("boss_spawn")
                        except:
                            pass
                            
                    except Exception as e:
                        print(f"[ERROR] Failed to spawn Boss: {e}")
                        import traceback
                        traceback.print_exc()

        # Remove dead enemies from the list to avoid further processing
        enemies = [en for en in enemies if not getattr(en, "dead", False)]

        # Check if boss is dead and spawn next stage
        if boss_instance and getattr(boss_instance, "dead", False) and current_stage < len(STAGES):
            print(f"Boss defeated! Stage {current_stage + 1} completed!")
            current_stage += 1
            if current_stage < len(STAGES):
                print(f"Spawning {STAGES[current_stage]['name']}...")
                # Show NEW stage notification - VERY LONG
                stage_notification = f"{STAGES[current_stage]['name'].upper()} - {STAGES[current_stage]['enemy_count']} ENEMIES!"
                stage_notification_type = "new_stage"
                stage_notification_timer = 10.0  # 10 giây
                
                # Override spawn center to player's current position for easier testing
                STAGES[current_stage]['spawn_center'] = (player.rect.centerx, player.rect.centery)
                print(f"[STAGE] Player position: ({player.rect.centerx}, {player.rect.centery})")
                new_enemies, new_enemy_ids = spawn_stage_enemies(current_stage)
                enemies = new_enemies  # Replace enemies with new stage enemies
                initial_enemies_ids = new_enemy_ids  # Reset to only new stage enemies
                boss_spawned = False
                boss_instance = None
            else:
                print("All stages completed! You win!")
                # Show VICTORY notification
                stage_notification = "VICTORY! ALL STAGES COMPLETED!"
                stage_notification_type = "victory"
                stage_notification_timer = 15.0  # 15 giây để tận hưởng chiến thắng
                game_won = True  # Mark game as won

        # Scale ra màn hình
        scaled_surface = pygame.transform.scale(render_surface, (WIDTH, HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        # Visual feedback khi bị slow
        if hasattr(player, "is_slowed") and player.is_slowed:
            # Tạo overlay màu tím với alpha
            slow_overlay = pygame.Surface((WIDTH, HEIGHT))
            slow_overlay.set_alpha(30)  # Độ trong suốt
            slow_overlay.fill((128, 0, 255))  # Màu tím
            screen.blit(slow_overlay, (0, 0))

            # Hiển thị text SLOWED!
            import time

            if hasattr(player, "slowed_until"):
                remaining = max(0, player.slowed_until - time.time())
                slow_text = font.render(
                    f"SLOWED! ({remaining:.1f}s)", True, (255, 0, 255)
                )
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
        
        # Hiển thị thông tin về enemies và boss
        if not boss_spawned:
            # Count alive initial enemies
            current_ids = [id(e) for e in enemies if not getattr(e, "dead", False)]
            alive_initial = sum(1 for eid in initial_enemies_ids if eid in current_ids)
            enemies_remaining = alive_initial
            
            enemy_info_font = pygame.font.SysFont("Arial", 28, bold=True)
            enemy_text = enemy_info_font.render(
                f"Enemies: {enemies_remaining}/{len(initial_enemies_ids)}",
                True,
                (255, 0, 0) if enemies_remaining > 0 else (0, 255, 0)
            )
            text_rect = enemy_text.get_rect(center=(WIDTH // 2, 50))
            # Draw black outline
            for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                outline = enemy_info_font.render(
                    f"Enemies: {enemies_remaining}/{len(initial_enemies_ids)}",
                    True,
                    (0, 0, 0)
                )
                screen.blit(outline, (text_rect.x + dx, text_rect.y + dy))
            screen.blit(enemy_text, text_rect)
        else:
            # Boss spawned - show boss warning
            boss_font = pygame.font.SysFont("Arial", 32, bold=True)
            boss_text = boss_font.render("⚠ BOSS BATTLE ⚠", True, (255, 100, 0))
            text_rect = boss_text.get_rect(center=(WIDTH // 2, 50))
            # Flashing effect
            import time
            if int(time.time() * 2) % 2 == 0:
                # Draw black outline
                for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                    outline = boss_font.render("⚠ BOSS BATTLE ⚠", True, (0, 0, 0))
                    screen.blit(outline, (text_rect.x + dx, text_rect.y + dy))
                screen.blit(boss_text, text_rect)
            
        # Hiển thị thông báo chuyển stage - ĐẸP VÀ RÕ RÀNG
        if stage_notification_timer > 0:
            stage_notification_timer -= dt
            
            # VICTORY SCREEN - HOÀNH TRÁNG!
            if stage_notification_type == "victory":
                import time
                
                # Full screen overlay với gradient
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.set_alpha(200)
                # Gradient từ đen sang vàng (giả lập bằng fill đơn giản)
                overlay.fill((20, 20, 40))  # Xanh đen tối
                screen.blit(overlay, (0, 0))
                
                # Hiệu ứng phóng to/thu nhỏ
                time_elapsed = 15.0 - stage_notification_timer
                pulse = 1.0 + 0.15 * math.sin(time_elapsed * 3)  # Nhịp đập
                
                # VICTORY text - CỰC LỚN
                victory_font = pygame.font.SysFont("Arial", int(100 * pulse), bold=True)
                
                # Rainbow color effect (màu chuyển động)
                hue_shift = (time_elapsed * 50) % 360
                if hue_shift < 120:
                    victory_color = (255, 215, 0)  # Gold
                elif hue_shift < 240:
                    victory_color = (255, 140, 0)  # Orange
                else:
                    victory_color = (255, 215, 0)  # Gold
                
                victory_text = victory_font.render(" VICTORY !", True, victory_color)
                victory_rect = victory_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
                
                # Vẽ glow effect (nhiều layer shadow màu vàng)
                for i in range(10, 0, -1):
                    glow_alpha = int(100 / i)
                    glow = victory_font.render("VICTORY!", True, (255, 255, 100))
                    glow_surface = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
                    glow.set_alpha(glow_alpha)
                    screen.blit(glow, (victory_rect.x - i, victory_rect.y - i))
                
                # Shadow đen dày
                for offset in range(8, 0, -1):
                    shadow = victory_font.render(" VICTORY! ", True, (0, 0, 0))
                    screen.blit(shadow, (victory_rect.x + offset, victory_rect.y + offset))
                
                # Outline vàng kim cực dày
                outline_size = 6
                for dx in range(-outline_size, outline_size + 1):
                    for dy in range(-outline_size, outline_size + 1):
                        if dx*dx + dy*dy <= outline_size*outline_size and (dx != 0 or dy != 0):
                            outline = victory_font.render(" VICTORY! ", True, (255, 223, 0))
                            screen.blit(outline, (victory_rect.x + dx, victory_rect.y + dy))
                
                # Text chính
                screen.blit(victory_text, victory_rect)
                
                # Subtitle với animation
                subtitle_font = pygame.font.SysFont("Arial", 48, bold=True)
                subtitle_pulse = 1.0 + 0.1 * math.sin(time_elapsed * 4)
                subtitle_font_animated = pygame.font.SysFont("Arial", int(48 * subtitle_pulse), bold=True)
                
                subtitle_text = subtitle_font_animated.render("ALL STAGES COMPLETED!", True, (255, 255, 255))
                subtitle_rect = subtitle_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))
                
                # Shadow cho subtitle
                for offset in [4, 3, 2]:
                    sub_shadow = subtitle_font_animated.render("ALL STAGES COMPLETED!", True, (0, 0, 0))
                    screen.blit(sub_shadow, (subtitle_rect.x + offset, subtitle_rect.y + offset))
                
                # Outline cho subtitle
                for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
                    sub_outline = subtitle_font_animated.render("ALL STAGES COMPLETED!", True, (50, 50, 50))
                    screen.blit(sub_outline, (subtitle_rect.x + dx, subtitle_rect.y + dy))
                
                screen.blit(subtitle_text, subtitle_rect)
                
                # Hướng dẫn chơi lại - nhấp nháy để thu hút sự chú ý
                action_font = pygame.font.SysFont("Arial", 32, bold=True)
                
                # Hiệu ứng nhấp nháy
                blink = int(time_elapsed * 2) % 2 == 0
                if blink:
                    action_text = action_font.render("Press R to Play Again or Q to Quit", True, (255, 255, 255))
                    action_rect = action_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100))
                    
                    # Shadow đen
                    for offset in [3, 2, 1]:
                        action_shadow = action_font.render("Press R to Play Again or Q to Quit", True, (0, 0, 0))
                        screen.blit(action_shadow, (action_rect.x + offset, action_rect.y + offset))
                    
                    # Outline
                    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                        action_outline = action_font.render("Press R to Play Again or Q to Quit", True, (100, 100, 100))
                        screen.blit(action_outline, (action_rect.x + dx, action_rect.y + dy))
                    
                    screen.blit(action_text, action_rect)
                
                # Vẽ các ngôi sao rơi (particles)
                import random
                for i in range(20):
                    star_x = (WIDTH // 2) + random.randint(-400, 400)
                    star_y = int((HEIGHT // 2 - 200) + (time_elapsed * 100 + i * 50) % HEIGHT)
                    star_size = random.randint(3, 8)
                    star_alpha = random.randint(150, 255)
                    star_color = random.choice([(255, 215, 0), (255, 255, 100), (255, 200, 50)])
                    pygame.draw.circle(screen, star_color, (star_x, star_y), star_size)
                
            else:
                # Normal stage notifications (cleared, new_stage)
                # Font đẹp và lớn
                stage_font = pygame.font.SysFont("Arial", 72, bold=True)
                
                # Chọn màu theo loại thông báo
                if stage_notification_type == "cleared":
                    # CLEARED: cam nâu viền đen
                    main_color = (204, 85, 0)  # Saddle brown - cam nâu
                    outline_color = (0, 0, 0)  # Đen
                    subtitle_msg = "BOSS IS COMING CAREFULLY!"
                    subtitle_color = (220, 20, 60)  # Crimson - đỏ
                else:  # new_stage
                    # NEW STAGE: cam đất
                    main_color = (204, 85, 0)  # Burnt orange
                    outline_color = (0, 0, 0)  # Đen
                    subtitle_msg = "GET READY!"
                    subtitle_color = (255, 255, 255)  # Trắng
                
                stage_text = stage_font.render(stage_notification, True, main_color)
                stage_rect = stage_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
                
                # Vẽ background xanh trắng rất mờ nhạt
                bg_padding = 30
                bg_rect = pygame.Rect(
                    stage_rect.x - bg_padding,
                    stage_rect.y - bg_padding - 20,
                    stage_rect.width + bg_padding * 2,
                    stage_rect.height + bg_padding * 2 + 80  # Thêm chỗ cho subtitle
                )
                bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
                bg_surface.set_alpha(80)  # Rất mờ nhạt
                bg_surface.fill((176, 224, 230))  # Powder blue - xanh trắng nhạt
                screen.blit(bg_surface, bg_rect)
                
                # Vẽ shadow đen để tạo depth
                shadow_offset = 4
                shadow = stage_font.render(stage_notification, True, (0, 0, 0))
                screen.blit(shadow, (stage_rect.x + shadow_offset, stage_rect.y + shadow_offset))
                
                # Vẽ outline đen
                outline_size = 4
                for dx in range(-outline_size, outline_size + 1):
                    for dy in range(-outline_size, outline_size + 1):
                        if dx*dx + dy*dy <= outline_size*outline_size and (dx != 0 or dy != 0):
                            outline = stage_font.render(stage_notification, True, outline_color)
                            screen.blit(outline, (stage_rect.x + dx, stage_rect.y + dy))
                
                # Vẽ text chính
                screen.blit(stage_text, stage_rect)
                
                # Thêm dòng subtitle
                subtitle_font = pygame.font.SysFont("Arial", 36, bold=True)
                subtitle_text = subtitle_font.render(subtitle_msg, True, subtitle_color)
                subtitle_rect = subtitle_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40))
                
                # Shadow cho subtitle
                subtitle_shadow = subtitle_font.render(subtitle_msg, True, (0, 0, 0))
                screen.blit(subtitle_shadow, (subtitle_rect.x + 2, subtitle_rect.y + 2))
                
                # Outline đen cho subtitle
                for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                    subtitle_outline = subtitle_font.render(subtitle_msg, True, (0, 0, 0))
                    screen.blit(subtitle_outline, (subtitle_rect.x + dx, subtitle_rect.y + dy))
                
                screen.blit(subtitle_text, subtitle_rect)

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

    return "exit"  # Game ended normally


def main():
    """Main function that handles the game loop and menu navigation"""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Platform từ Tiled (Zoom camera + FPS)")
    
    selected_char = None  # Keep track of selected character for play again
    
    while True:
        # If no character selected or returning from main menu, show menu and character select
        if selected_char is None:
            # Show menu
            menu = Menu(screen)
            menu_result = menu.run()

            if menu_result == "exit":
                pygame.quit()
                sys.exit()

            # Show character selection screen
            char_select = CharacterSelectMenu(screen)
            selected_char = char_select.run()

            if selected_char is None:
                pygame.quit()
                sys.exit()
        
        # Run the actual game with the selected character
        result = run_game_session(screen, selected_char)
        
        if result == "exit":
            pygame.quit()
            sys.exit()
        elif result == "main_menu":
            # Reset selected character to force menu/character select
            selected_char = None
            continue
        elif result == "play_again":
            # Keep the same character and restart game
            continue
        else:
            # Any other result, exit
            pygame.quit()
            sys.exit()


if __name__ == "__main__":
    main()

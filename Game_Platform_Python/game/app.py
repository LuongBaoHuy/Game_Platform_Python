import pygame
import sys
import os
from game.config import WIDTH, HEIGHT, FPS, ZOOM, PLAYER_SCALE
from game.map_loader import load_map
from game.player import Player
from game.menu import draw_menu
from game.enemy import PatrolEnemy



# ===============================
# Main Game
# ===============================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Platform từ Tiled (Zoom camera + FPS)")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("Arial", 24)

    # Load map
    platforms, _ = load_map(
        "D:/LapTrinh_Python/Python_Game/Game_Platform_Python/assets/maps/Map_test.tmx"
    )

    # Tạo nhân vật
    player = Player(100, 100)
    # Spawn enemies
    enemies = [PatrolEnemy(900, 600)]
    show_hitboxes = False  # Toggle hiển thị hitbox của từng bức tường (phím H)

    running = True
    while running:
        ms = clock.tick(FPS)
        dt = ms / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h:
                    # Toggle hiển thị hitbox tường
                    show_hitboxes = not show_hitboxes

        # Logic game
        player.handle_input()
        # update skills with delta seconds (e.g. dash)
        if hasattr(player, 'update_skills'):
            player.update_skills(dt)
        # Use consolidated move() which applies gravity and resolves collisions
        player.move(platforms)
        player.update_animation()

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
        # Update & draw enemies
        for e in enemies:
            e.update(dt, platforms, player)
            e.draw(render_surface, camera_x, camera_y, show_hitboxes)

        # Scale ra màn hình
        scaled_surface = pygame.transform.scale(render_surface, (WIDTH, HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        # Hiển thị FPS
        fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (0, 0, 0))
        screen.blit(fps_text, (10, 10))
        # Hint nhỏ cho toggle hitbox
        hint_text = font.render(f"H: Toggle wall hitboxes ({'ON' if show_hitboxes else 'OFF'})", True, (0, 0, 0))
        screen.blit(hint_text, (10, 40))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

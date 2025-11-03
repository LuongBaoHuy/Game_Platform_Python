# test_wraith_enemies.py
"""
Script demo để test các Wraith enemy mới trong game.
Chạy script này để thấy hành vi của CasterEnemy và ControllerEnemy.
"""

import pygame
import sys
import os

# Add game path
sys.path.append(os.path.dirname(__file__))

from game.enemy_registry import create_enemy
from game.player import Player
from game.config import WIDTH, HEIGHT, FPS

# Use config values
SCREEN_WIDTH = WIDTH
SCREEN_HEIGHT = HEIGHT

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Test Wraith Enemies")
    clock = pygame.time.Clock()
    
    # Tạo player
    player = Player(400, 500)
    
    # Tạo các enemy để test
    enemies = [
        create_enemy('Wraith_01', 200, 500),  # Caster
        create_enemy('Wraith_03', 600, 500),  # Controller
        create_enemy('Golem_02', 100, 500),   # So sánh với enemy cũ
    ]
    
    # Tạo platform đơn giản
    platforms = [
        (None, pygame.Rect(0, 550, SCREEN_WIDTH, 50))  # Ground platform
    ]
    
    camera_x = 0
    camera_y = 0
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # Delta time in seconds
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    # Reset enemies
                    enemies = [
                        create_enemy('Wraith_01', 200, 500),
                        create_enemy('Wraith_03', 600, 500),
                        create_enemy('Golem_02', 100, 500),
                    ]
        
        # Update player
        player.update(dt, platforms)
        
        # Update enemies
        alive_enemies = []
        for enemy in enemies:
            if not enemy.dead:
                enemy.update(dt, platforms, player)
                alive_enemies.append(enemy)
        enemies = alive_enemies
        
        # Simple camera follow
        camera_x = player.rect.centerx - SCREEN_WIDTH // 2
        camera_y = player.rect.centery - SCREEN_HEIGHT // 2
        
        # Draw everything
        screen.fill((50, 50, 100))  # Dark blue background
        
        # Draw platforms
        for _, platform_rect in platforms:
            pygame.draw.rect(screen, (100, 100, 100), 
                           (platform_rect.x - camera_x, platform_rect.y - camera_y, 
                            platform_rect.width, platform_rect.height))
        
        # Draw player
        player.draw(screen, camera_x, camera_y, show_hitbox=True)
        
        # Draw enemies
        for enemy in enemies:
            enemy.draw(screen, camera_x, camera_y, show_hitbox=True)
            
            # Draw projectiles if any
            if hasattr(enemy, 'skills'):
                for skill in enemy.skills.values():
                    if hasattr(skill, 'draw'):
                        skill.draw(screen, camera_x, camera_y)
        
        # Draw UI
        font = pygame.font.Font(None, 36)
        texts = [
            "Wraith Test Demo",
            "WASD: Move player",
            "Space: Jump", 
            "R: Reset enemies",
            "ESC: Exit",
            "",
            f"Player HP: {getattr(player, 'hp', '?')}",
            f"Enemies alive: {len(enemies)}",
        ]
        
        for i, text in enumerate(texts):
            if text:
                surface = font.render(text, True, (255, 255, 255))
                screen.blit(surface, (10, 10 + i * 30))
        
        # Enemy info
        y_offset = 250
        for i, enemy in enumerate(enemies):
            enemy_type = type(enemy).__name__
            hp = getattr(enemy, 'hp', '?')
            state = getattr(enemy, 'state', '?')
            info = f"{enemy_type}: HP={hp}, State={state}"
            surface = font.render(info, True, (200, 200, 255))
            screen.blit(surface, (10, y_offset + i * 25))
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
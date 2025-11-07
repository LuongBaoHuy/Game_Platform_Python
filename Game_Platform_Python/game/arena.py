# game/arena.py
"""
Arena System - Quản lý các khu vực chiến đấu
"""
import random
import math


class Arena:
    """Khu vực chiến đấu với enemies và boss"""
    
    def __init__(self, arena_id, config):
        """
        Args:
            arena_id: ID của arena
            config: Dict chứa cấu hình arena
                {
                    'name': 'Arena 1',
                    'enemies': ['Golem_02', 'Golem_03'],
                    'enemy_count': 5,
                    'boss': 'Troll1',
                    'spawn_center': (x, y)
                }
        """
        self.arena_id = arena_id
        self.config = config
        self.name = config['name']
        
        # Arena state
        self.active = False
        self.enemies = []
        self.initial_enemy_ids = []
        self.boss = None
        self.boss_spawned = False
        self.completed = False
        
        # Spawn settings
        self.spawn_center = config.get('spawn_center', (2649, 9200))
        self.spawn_radius_min = 50
        self.spawn_radius_max = 150
        
        print(f"[ARENA] Created {self.name} at {self.spawn_center}")
    
    def start(self, create_enemy_func, patrol_enemy_class):
        """Bắt đầu arena - spawn enemies"""
        if self.active:
            return
        
        self.active = True
        self.enemies = []
        self.initial_enemy_ids = []
        self.boss_spawned = False
        self.completed = False
        
        print(f"[ARENA] Starting {self.name}...")
        print(f"[ARENA] Spawning {self.config['enemy_count']} enemies...")
        
        # Spawn enemies
        enemy_types = self.config.get('enemies', ['Golem_02', 'Golem_03'])
        enemy_count = self.config.get('enemy_count', 5)
        
        for i in range(enemy_count):
            # Random position around spawn center
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(self.spawn_radius_min, self.spawn_radius_max)
            
            ex = int(self.spawn_center[0] + math.cos(angle) * distance)
            ey = int(self.spawn_center[1] + math.sin(angle) * distance)
            
            enemy_type = random.choice(enemy_types)
            enemy = None
            
            try:
                enemy = create_enemy_func(enemy_type, ex, ey)
                print(f"[ARENA] Spawned {enemy_type} at ({ex}, {ey})")
            except Exception as e:
                print(f"[ARENA ERROR] Failed to spawn {enemy_type}: {e}")
                # Fallback to PatrolEnemy
                try:
                    enemy = patrol_enemy_class(ex, ey)
                    print(f"[ARENA] Fallback PatrolEnemy at ({ex}, {ey})")
                except Exception as e2:
                    print(f"[ARENA ERROR] Fallback failed: {e2}")
            
            if enemy:
                self.enemies.append(enemy)
                self.initial_enemy_ids.append(id(enemy))
        
        # Ensure we have enough enemies
        while len(self.enemies) < enemy_count:
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(self.spawn_radius_min, self.spawn_radius_max)
            ex = int(self.spawn_center[0] + math.cos(angle) * distance)
            ey = int(self.spawn_center[1] + math.sin(angle) * distance)
            
            try:
                enemy = patrol_enemy_class(ex, ey)
                self.enemies.append(enemy)
                self.initial_enemy_ids.append(id(enemy))
                print(f"[ARENA] Additional PatrolEnemy at ({ex}, {ey})")
            except Exception:
                break
        
        print(f"[ARENA] {self.name} started with {len(self.enemies)} enemies")
    
    def update(self, dt, platforms, player, create_enemy_func):
        """Update arena state"""
        if not self.active:
            return
        
        # Update enemies
        for enemy in self.enemies[:]:
            if enemy.dead:
                self.enemies.remove(enemy)
                continue
            enemy.update(dt, platforms, player)
        
        # Check if all initial enemies are defeated
        initial_alive = [e for e in self.enemies if id(e) in self.initial_enemy_ids]
        
        # Spawn boss if all initial enemies defeated and boss not spawned yet
        if len(initial_alive) == 0 and not self.boss_spawned:
            self.spawn_boss(platforms, player, create_enemy_func)
        
        # Update boss
        if self.boss and not self.boss.dead:
            self.boss.update(dt, platforms, player)
        elif self.boss and self.boss.dead and not self.completed:
            self.completed = True
            print(f"[ARENA] {self.name} COMPLETED!")
    
    def spawn_boss(self, platforms, player, create_enemy_func):
        """Spawn boss"""
        if self.boss_spawned:
            return
        
        self.boss_spawned = True
        boss_type = self.config.get('boss', 'Troll1')
        
        print(f"[ARENA] All enemies defeated! Spawning boss: {boss_type}")
        
        # Find platform near player to spawn boss
        boss_x = None
        boss_y = None
        
        if player and platforms:
            search_radius = 2000
            search_offset = 800  # Spawn boss 800px away from player
            
            # Try right side first
            target_x = player.rect.centerx + search_offset
            
            # Find nearest platform
            nearest_platform = None
            min_distance = float('inf')
            
            for platform in platforms:
                if isinstance(platform, tuple) and len(platform) >= 2:
                    platform_rect = platform[1]
                elif hasattr(platform, 'rect'):
                    platform_rect = platform.rect
                else:
                    continue
                
                # Check if platform is within range
                x_dist = abs(platform_rect.centerx - target_x)
                if x_dist < search_radius and platform_rect.top < 18000:
                    if x_dist < min_distance:
                        min_distance = x_dist
                        nearest_platform = platform_rect
            
            if nearest_platform:
                boss_x = nearest_platform.centerx
                boss_y = nearest_platform.top - 100  # Spawn above platform
                print(f"[ARENA] Found platform at ({boss_x}, {boss_y})")
            else:
                # Fallback: Use spawn center
                boss_x = self.spawn_center[0] + search_offset
                boss_y = self.spawn_center[1]
                print(f"[ARENA] No platform found, using fallback position")
        
        # Create boss
        try:
            self.boss = create_enemy_func(boss_type, boss_x, boss_y)
            print(f"[ARENA] Boss spawned: {boss_type} at ({boss_x}, {boss_y})")
        except Exception as e:
            print(f"[ARENA ERROR] Failed to spawn boss: {e}")
            import traceback
            traceback.print_exc()
    
    def draw(self, surface, camera_x, camera_y, show_hitboxes=False):
        """Draw all arena entities"""
        if not self.active:
            return
        
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(surface, camera_x, camera_y, show_hitboxes)
        
        # Draw boss
        if self.boss and not self.boss.dead:
            self.boss.draw(surface, camera_x, camera_y, show_hitboxes)
    
    def get_all_entities(self):
        """Get all enemies and boss as a single list"""
        entities = list(self.enemies)
        if self.boss and not self.boss.dead:
            entities.append(self.boss)
        return entities
    
    def cleanup(self):
        """Clean up arena"""
        self.active = False
        self.enemies.clear()
        self.boss = None
        print(f"[ARENA] {self.name} cleaned up")

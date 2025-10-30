from typing import Dict, Type, Optional

_ENEMY_REGISTRY: Dict[str, Type] = {}

def register_enemy(enemy_id: str, cls: Type) -> None:
    _ENEMY_REGISTRY[enemy_id] = cls

def get_enemy_class(enemy_id: str) -> Optional[Type]:
    return _ENEMY_REGISTRY.get(enemy_id)

def create_enemy(enemy_id: str, x: int, y: int, **kwargs):
    cls = get_enemy_class(enemy_id)
    if not cls:
        # If no class explicitly registered, try to dynamically use DataDrivenEnemy
        try:
            from game.characters.data_driven_enemy import DataDrivenEnemy
            # instantiate with char_id so visuals load for this id
            return DataDrivenEnemy(x, y, char_id=enemy_id, **kwargs)
        except Exception:
            # fallback to PatrolEnemy to keep robustness
            try:
                from game.enemy import PatrolEnemy
                return PatrolEnemy(x, y, **kwargs)
            except Exception:
                raise RuntimeError(f"No enemy class registered for '{enemy_id}' and fallback failed")
    # If the registered class expects a character id (data-driven enemy),
    # pass the enemy_id as the 'char_id' keyword so it can load the right sprites.
    try:
        inst = cls(x, y, char_id=enemy_id, **kwargs)
    except TypeError:
        # If the class does not accept 'char_id', fall back to calling without it.
        inst = cls(x, y, **kwargs)
    return inst

def list_enemies():
    return list(_ENEMY_REGISTRY.keys())
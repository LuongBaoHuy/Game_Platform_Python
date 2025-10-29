import os
import json
from typing import List

from game.characters.base import Character
from game.characters.registry import get_skill


def _list_character_dirs(base_path: str) -> List[str]:
    if not os.path.isdir(base_path):
        return []
    return [name for name in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, name))]


def list_characters() -> List[str]:
    """Return a list of character ids discovered under assets/characters.

    This function is safe: if folder not present, returns empty list.
    """
    repo_root = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
    base = os.path.join(repo_root, 'assets', 'characters')
    base = os.path.normpath(base)
    return _list_character_dirs(base)


def create_player(char_id: str, x: int, y: int) -> Character:
    """Create a simple Character instance for the given character id.

    This factory is intentionally conservative: if metadata or sprite folders
    are missing it will still return a basic Character to avoid breaking the game.
    """
    # try to read metadata
    # repo_root = parent of 'game' directory (project root)
    repo_root = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
    assets_chars = os.path.join(repo_root, 'assets', 'characters', char_id)
    meta_path = os.path.join(assets_chars, 'metadata.json')

    meta = {}
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    sprite_path = meta.get('sprite_path') or assets_chars
    # If sprite_path is relative, make it relative to repo root
    if sprite_path and not os.path.isabs(sprite_path):
        sprite_path = os.path.normpath(os.path.join(repo_root, sprite_path))
    scale = meta.get('scale', 1.0)

    # Tạo instance Player (nếu có) để giữ nguyên logic input/move/animation.
    # Import Player lazily to avoid circular import at module import time.
    GamePlayer = None
    try:
        from game.player import Player as GamePlayer
    except Exception:
        GamePlayer = None

    if GamePlayer is not None:
        # Pass sprite/frames/scale to Player when possible so it can load frames itself
        try:
            c = GamePlayer(x, y, sprite_path=sprite_path, frames_map=frames_map or {}, scale=scale)
        except Exception:
            # Fallback to simple ctor if signature differs
            try:
                c = GamePlayer(x, y)
            except Exception:
                c = Character(x, y, sprite_path=sprite_path, scale=scale)
    else:
        c = Character(x, y, sprite_path=sprite_path, scale=scale)
    # Attach skills from metadata (data-driven). Each skill entry in metadata
    # should be an object like {"id": "dash", "params": {...}}.
    # Don't clobber existing skills (Player may have defaults); merge instead.
    existing_skills = getattr(c, 'skills', {}) or {}
    for s in meta.get('skills', []):
        sid = s.get('id') if isinstance(s, dict) else s
        params = s.get('params', {}) if isinstance(s, dict) else {}
        cls = get_skill(sid)
        if cls:
            try:
                existing_skills[sid] = cls(**params)
            except Exception:
                # If instantiation fails, skip to keep factory robust
                pass
        else:
            # If not a registered Skill class, keep raw dict params if provided
            if isinstance(s, dict):
                existing_skills[sid] = params

    c.skills = existing_skills
    # Attempt to load animations. Prefer explicit folders in metadata['frames']
    sprite_size = (int(512 * scale), int(512 * scale))
    frames_map = meta.get('frames', {}) if isinstance(meta.get('frames', {}), dict) else {}

    def _load_state(state_name):
        # Try several resolutions for folder paths (absolute, relative to repo, under sprite_path)
        folder = frames_map.get(state_name)
        candidates = []
        if folder:
            # if absolute, try directly
            candidates.append(folder)
            # try relative to repo root
            candidates.append(os.path.join(repo_root, folder))
            # try relative to assets_chars
            candidates.append(os.path.join(assets_chars, folder))
            # try relative to sprite_path
            candidates.append(os.path.join(sprite_path or assets_chars, folder))
        # also try default sprite_path/<state_name>
        candidates.append(os.path.join(sprite_path or assets_chars, state_name))

        for cand in candidates:
            cand = os.path.normpath(cand)
            if os.path.isdir(cand):
                return c.load_frames(cand, sprite_size)

        # If nothing found, print debug hint and return empty
        print(f"factory.create_player: no frames for '{state_name}' (tried: {candidates})")
        return []

    c.animations['idle'] = _load_state('idle')
    c.animations['walk'] = _load_state('walk')
    c.animations['jump'] = _load_state('jump')
    # dash is optional
    c.animations['dash'] = _load_state('dash')

    return c

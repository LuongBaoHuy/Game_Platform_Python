"""game.characters

Lightweight characters package skeleton. This package is intentionally
non-intrusive: it only provides helper/factory functions to create a player
from a character id. It does not modify any existing game files.

Usage:
    from game.characters import create_player, list_characters
    ids = list_characters()
    player = create_player(ids[0], 100, 100)

This is a minimal starting point — extend `factory.py` and `base.py` when
you want data-driven characters, custom skills, or subclasses.
"""

# Import skills module FIRST to trigger skill registration
try:
    from . import skills as _skills
except Exception:
    pass

from .factory import create_player, list_characters

__all__ = ["create_player", "list_characters"]

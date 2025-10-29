Characters package
==================

This folder contains a small, non-intrusive skeleton to manage multiple
characters in a data-driven way. It is safe to add to the project: no
existing files are removed or modified.

Quick start:

1. Put each character's sprite frames under `assets/characters/<id>/idle`, `walk`, `jump`, etc.
2. Optionally create `assets/characters/<id>/metadata.json` with fields like `sprite_path` and `scale`.
3. In your game, import the factory:

    from game.characters import create_player, list_characters

4. Create a player:

    ids = list_characters()
    if ids:
        player = create_player(ids[0], 100, 100)

Extend `factory.py` and `base.py` when you want advanced behavior or skill composition.

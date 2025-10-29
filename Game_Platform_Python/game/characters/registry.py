"""Skill / class registry for characters package.

Register skill classes here so the factory can instantiate them by id.
"""
from typing import Dict, Type, Optional

_SKILL_REGISTRY: Dict[str, Type] = {}


def register_skill(skill_id: str, cls: Type) -> None:
    _SKILL_REGISTRY[skill_id] = cls


def get_skill(skill_id: str) -> Optional[Type]:
    return _SKILL_REGISTRY.get(skill_id)


def list_skills():
    return list(_SKILL_REGISTRY.keys())

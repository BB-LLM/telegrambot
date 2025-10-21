"""
Scenes module

Exports:
- SCENE_PRESETS: canonical situation presets inspired by Pocket Souls (creative, contemplative, connection, growth, reflection)
- ScenePromptAdjuster: builds scene-aware instructions to augment the system prompt

All comments and prompts are intentionally written in English to keep the
instruction language consistent across modules.
"""

from .configs import SCENE_PRESETS, SCENE_OPTIONS
from .adjuster import ScenePromptAdjuster

__all__ = [
    "SCENE_PRESETS",
    "SCENE_OPTIONS",
    "ScenePromptAdjuster",
]




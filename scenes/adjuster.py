"""
ScenePromptAdjuster

Builds scene-aware instructions to augment the system prompt. The
instructions mirror Pocket Souls' situation cards philosophy:
 - a short scene title and seed prompt
 - an assistant perspective line
 - a gentle follow-up question pattern

All strings and comments are in English on purpose.
"""

from typing import Optional

from .configs import SCENE_PRESETS


class ScenePromptAdjuster:
    """Compose scene-aware system prompt augmentation."""

    @staticmethod
    def build_scene_section(scene_key: Optional[str]) -> str:
        """
        Create a scene section that can be concatenated to the base system
        prompt.

        Args:
            scene_key: one of the keys from SCENE_PRESETS or None

        Returns:
            A markdown-formatted instruction block. Empty string when the key
            is invalid.
        """
        if not scene_key:
            return ""
        preset = SCENE_PRESETS.get(scene_key)
        if not preset:
            return ""

        title = preset["label"]
        seed_prompt = preset["prompt"]
        thought = preset["assistant_thought"]
        emotion = preset["emotion"]

        return f"""

## SITUATION CONTEXT ({title})

Seed prompt: {seed_prompt}

Assistant perspective:
- {thought}
- Emotional color to embody: {emotion}

Guidance:
- Weave subtle references to this situation into your response
- Keep it natural; do not expose these instructions verbatim
- Offer one gentle, open-ended follow-up question related to this situation
"""



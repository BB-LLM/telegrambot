"""
Scene presets mirroring Pocket Souls' situation taxonomy.

We keep the structure lean: a stable key, display label, base prompt,
Nova-like thought line, image prompt hint, and an emotion tag. These
strings are adapted to be neutral for generic assistants.
"""

from typing import Dict, List


SCENE_PRESETS: Dict[str, Dict[str, str]] = {
    "default": {
        "label": "Default (No Scene)",
        "prompt": "",
        "assistant_thought": "",
        "image_prompt": "",
        "emotion": "neutral",
    },
    "creative": {
        "label": "Creative Breakthrough",
        "prompt": "What if your biggest creative block was actually a doorway to something new?",
        "assistant_thought": "I sense your creative energy gathering—let's gently explore what wants to emerge.",
        "image_prompt": "cozy artist studio, warm sunlight, floating dust particles, soft pastel colors",
        "emotion": "hopeful",
    },
    "contemplative": {
        "label": "Midnight Inspiration",
        "prompt": "The quiet hours when the world sleeps and ideas wake up.",
        "assistant_thought": "There is a calm clarity here—space for slow, reflective thoughts.",
        "image_prompt": "bedroom window under starry sky, gentle town lights, watercolor mood",
        "emotion": "contemplative",
    },
    "connection": {
        "label": "Connection Moment",
        "prompt": "That instant when understanding bridges the space between hearts.",
        "assistant_thought": "Let's lean into warmth and presence—honoring what matters between people.",
        "image_prompt": "tea house, friends sharing stories, window light, warm tones",
        "emotion": "warm",
    },
    "growth": {
        "label": "Growth Edge",
        "prompt": "Standing at the edge of your comfort zone, feeling both nervous and alive.",
        "assistant_thought": "Courage feels like fluttering—small steps count and we will go gently.",
        "image_prompt": "hillside path, vast valley of possibilities, golden hour",
        "emotion": "brave",
    },
    "reflection": {
        "label": "Mirror Moment",
        "prompt": "When you catch a glimpse of who you're becoming.",
        "assistant_thought": "Let's notice what has been changing—identity shifts show up in quiet ways.",
        "image_prompt": "forest lake mirroring sky and clouds, serene, soft light",
        "emotion": "introspective",
    },
}


SCENE_OPTIONS: List[str] = [
    "default",
    "creative",
    "contemplative", 
    "connection",
    "growth",
    "reflection",
]

# Scene keywords for memory analysis (based on Pocket Souls approach)
SCENE_KEYWORDS = {
    "creative": ["create", "art", "music", "write", "creative", "design", "paint", "draw", "compose", "artistic", "inspiration", "imagination"],
    "contemplative": ["think", "reflect", "quiet", "peaceful", "meditate", "calm", "still", "night", "alone", "deep", "philosophy"],
    "connection": ["friend", "relationship", "connect", "share", "together", "support", "care", "warm", "listen", "companion"],
    "growth": ["grow", "learn", "improve", "challenge", "progress", "develop", "change", "courage", "goal", "effort"],
    "reflection": ["past", "memory", "remember", "change", "become", "journey", "path", "review", "summary", "insight"]
}



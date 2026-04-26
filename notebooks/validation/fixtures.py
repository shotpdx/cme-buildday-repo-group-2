PERSONAS = [
    "Sports Fan",
    "News Junkie",
    "Entertainment Binge Watcher",
    "Casual Viewer",
    "Cord Cutter",
]

FORMATS = [
    {"name": "social_square",   "size": "1024x1024", "tone": "bold social post"},
    {"name": "vertical_story",  "size": "1024x1792", "tone": "full-bleed immersive"},
    {"name": "display_banner",  "size": "1792x1024", "tone": "editorial landscape"},
    {"name": "email_header",    "size": "1792x1024", "tone": "clean marketing hero"},
]


def PROMPT_FOR(persona: str, fmt: dict) -> str:
    return (
        f"{fmt['tone']} image for a media streaming audience labeled '{persona}'. "
        f"Photographic style, rich color grading, cinematic lighting, "
        f"no text, no watermark, no logos."
    )

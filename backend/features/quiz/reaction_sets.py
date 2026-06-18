REACTION_SETS = {
    "thumbs": {
        "options": ["thumbs_down", "thumbs_up", "thumbs_love"],
        "emojis": {"thumbs_down": "\U0001f44e", "thumbs_up": "\U0001f44d", "thumbs_love": "\U0001f44d\U0001f44d"},
    },
    "hearts": {
        "options": ["hearts_broken", "hearts_red", "hearts_fire"],
        "emojis": {"hearts_broken": "\U0001f494", "hearts_red": "❤️", "hearts_fire": "❤️‍\U0001f525"},
    },
    "vibes": {
        "options": ["vibes_boring", "vibes_ok", "vibes_good", "vibes_amazing"],
        "emojis": {"vibes_boring": "\U0001f634", "vibes_ok": "\U0001f610", "vibes_good": "\U0001f60a", "vibes_amazing": "\U0001f929"},
    },
    "stars": {
        "options": ["stars_1", "stars_2", "stars_3", "stars_4", "stars_5"],
        "emojis": {f"stars_{i}": "⭐" * i for i in range(1, 6)},
    },
}

VALID_STYLES = set(REACTION_SETS.keys())


def validate_reaction(reaction_style: str, reaction: str) -> bool:
    style = REACTION_SETS.get(reaction_style)
    if not style:
        return False
    return reaction in style["options"]

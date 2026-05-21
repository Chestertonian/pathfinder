"""
combat/resolver.py — Pure combat math

No threading, no DB writes, no side effects.
Just takes numbers in, returns results out.

All game logic lives here so it's easy to tune and test.
"""

import random


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MISS_THRESHOLD   = 2
LIGHT_THRESHOLD  = 10
MEDIUM_THRESHOLD = 16
STRONG_THRESHOLD = 19
# 20 = CRIT

TIER_MULTIPLIERS = {
    "miss":   0.0,
    "light":  0.6,
    "medium": 1.0,
    "strong": 1.4,
    "crit":   2.0,
}


# ---------------------------------------------------------------------------
# Roll
# ---------------------------------------------------------------------------

def roll_d20(accuracy_mod: int, skill_mod: int = 0) -> tuple[int, str]:
    """
    Roll a d20, apply modifiers, return (total, tier).

    accuracy_mod : DEX modifier of the attacker
    skill_mod    : placeholder, always 0 for now
    """
    raw = random.randint(1, 20)
    total = raw + accuracy_mod + skill_mod

    # Clamp tier determination to the raw roll for crits/misses
    # (a nat 1 is always a miss, nat 20 is always a crit)
    if raw == 1:
        tier = "miss"
    elif raw == 20:
        tier = "crit"
    elif total <= MISS_THRESHOLD:
        tier = "miss"
    elif total <= LIGHT_THRESHOLD:
        tier = "light"
    elif total <= MEDIUM_THRESHOLD:
        tier = "medium"
    elif total <= STRONG_THRESHOLD:
        tier = "strong"
    else:
        tier = "crit"

    return total, tier


# ---------------------------------------------------------------------------
# Damage
# ---------------------------------------------------------------------------

def calculate_damage(
    damage_min: int,
    damage_max: int,
    stat_mod: int,
    level: int,
    tier: str,
    armor: int,
) -> int:
    """
    Calculate final damage dealt.

    Formula:
        base   = random(damage_min, damage_max) + stat_mod
        scaled = base * level_factor
        final  = max(1, scaled * tier_multiplier - armor)

    Returns 0 for misses (no minimum).
    """
    if tier == "miss":
        return 0

    # Base weapon damage + stat modifier
    base = random.randint(damage_min, damage_max) + stat_mod

    # Level scaling: each level adds 5% damage
    level_factor = 1.0 + (level - 1) * 0.05
    scaled = base * level_factor

    # Tier multiplier
    multiplied = scaled * TIER_MULTIPLIERS[tier]

    # Flat armor reduction — minimum 1 damage on a hit
    final = max(1, int(multiplied) - armor)

    return final


# ---------------------------------------------------------------------------
# Stat helpers
# ---------------------------------------------------------------------------

def stat_modifier(value: int) -> int:
    """Standard D&D modifier: (stat - 10) // 2"""
    return (value - 10) // 2


# ---------------------------------------------------------------------------
# Ability hook (placeholder)
# ---------------------------------------------------------------------------

def use_ability(attacker, defender):
    """
    Placeholder for class abilities.
    Returns None — no ability fires yet.
    Will return an effect dict when abilities are implemented.
    """
    return None

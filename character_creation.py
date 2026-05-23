"""
character_creation.py — New character creation flow

Handles the full interactive creation sequence:
  name → gender → race → stat roll → class → password → DB insert

Returns the new character's ID on success.
Call run_character_creation(session) from server.py.
"""

import hashlib
import random
import secrets

from db import get_connection

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STARTING_LOCATION_ID = 1

CLASSES = ["Fighter", "Rogue", "Wizard", "Cleric", "Ranger"]

RACIAL_BONUSES = {
    "Human":   {"strength": 1, "dexterity": 1, "constitution": 1,
                "intelligence": 1, "wisdom": 1, "charisma": 1},
    "Elf":     {"dexterity": 2, "intelligence": 1, "constitution": -1},
    "Dwarf":   {"constitution": 2, "strength": 1, "charisma": -1},
    "Gnome":   {"intelligence": 2, "wisdom": 1, "strength": -1},
    "Centaur": {"strength": 2, "constitution": 2,
                "intelligence": -1, "charisma": -1},
}

STAT_NAMES = ["strength", "dexterity", "constitution",
              "intelligence", "wisdom", "charisma"]
STAT_ABBR  = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

GENDER_MALE   = 1
GENDER_FEMALE = 2

RACE_DESCRIPTIONS = {
    "Human":   "Versatile and ambitious, humans adapt quickly to any role.",
    "Elf":     "Graceful and perceptive, elves excel in agility and magic.",
    "Dwarf":   "Stout and resilient, dwarves are masters of endurance and craft.",
    "Gnome":   "Curious and clever, gnomes thrive on invention and wit.",
    "Centaur": "Swift and powerful, centaurs combine mobility with raw strength.",
}


# ---------------------------------------------------------------------------
# Password hashing — UNCHANGED
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{digest}"

def verify_password(password: str, stored_hash: str) -> bool:
    salt, digest = stored_hash.split(":", 1)
    candidate = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return candidate == digest


# ---------------------------------------------------------------------------
# Stat rolling — UNCHANGED
# ---------------------------------------------------------------------------

def roll_stat() -> int:
    dice = [random.randint(1, 6) for _ in range(4)]
    return sum(sorted(dice)[1:])

def roll_all_stats() -> dict[str, int]:
    return {stat: roll_stat() for stat in STAT_NAMES}

def apply_racial_bonuses(stats: dict[str, int], race: str) -> dict[str, int]:
    result = dict(stats)
    for stat, bonus in RACIAL_BONUSES[race].items():
        result[stat] = result[stat] + bonus
    return result

def stat_modifier(value: int) -> int:
    return (value - 10) // 2

def calculate_starting_resources(stats: dict[str, int]) -> dict[str, int]:
    return {"hp": 25, "power": 25, "endurance": 25}


# ---------------------------------------------------------------------------
# Database helpers — UNCHANGED
# ---------------------------------------------------------------------------

def name_exists(name: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM characters WHERE LOWER(name) = LOWER(%s)", (name,)
            )
            return cur.fetchone() is not None

def insert_character(name, password_hash, gender, race,
                     char_class, stats, resources) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO characters (
                    name, password_hash, gender, class, race, location_id,
                    strength, dexterity, constitution, intelligence, wisdom, charisma,
                    hp, hp_max, power, power_max, endurance, endurance_max
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    name, password_hash, gender, char_class, race.lower(),
                    STARTING_LOCATION_ID,
                    stats["strength"], stats["dexterity"], stats["constitution"],
                    stats["intelligence"], stats["wisdom"], stats["charisma"],
                    resources["hp"], resources["hp"],
                    resources["power"], resources["power"],
                    resources["endurance"], resources["endurance"],
                ),
            )
            character_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO audit_log (character_id, action, entity_type, entity_id, details)
                VALUES (%s, 'character_created', 'character', %s, %s)
                """,
                (character_id, character_id, f'{{"race": "{race}"}}'),
            )
        conn.commit()
    return character_id


# ---------------------------------------------------------------------------
# Display helpers — NOW RETURN STRINGS instead of printing
# ---------------------------------------------------------------------------

def display_stat_block(
    stats: dict[str, int],
    bonuses: dict[str, int] | None = None
) -> str:
    # CHANGED: builds and returns a plain string instead of console.print()
    lines = []
    for stat, abbr in zip(STAT_NAMES, STAT_ABBR):
        value = stats[stat]
        if bonuses and stat in bonuses:
            b = bonuses[stat]
            sign = "+" if b >= 0 else ""
            lines.append(f"  {abbr:<4} {value:>2}  (roll {value - b:>2}  {sign}{b})")
        else:
            lines.append(f"  {abbr:<4} {value:>2}")
    return "\n".join(lines) + "\n"


def display_races() -> str:
    # CHANGED: returns plain string
    lines = []
    for i, (race, bonuses) in enumerate(RACIAL_BONUSES.items(), 1):
        parts = []
        for stat, val in bonuses.items():
            abbr = STAT_ABBR[STAT_NAMES.index(stat)]
            sign = "+" if val >= 0 else ""
            parts.append(f"{sign}{val} {abbr}")
        bonus_str = ", ".join(parts)
        desc = RACE_DESCRIPTIONS.get(race, "")
        lines.append(f"  [{i}] {race:<10}  {bonus_str}")
        lines.append(f"      {desc}")
    return "\n".join(lines) + "\n"


def display_classes() -> str:
    # CHANGED: returns plain string
    lines = []
    for i, cls in enumerate(CLASSES, 1):
        lines.append(f"  [{i}] {cls}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Input helpers — NOW take session instead of calling prompt()
# ---------------------------------------------------------------------------

def prompt_choice(session, label: str, options: list) -> int:
    # CHANGED: session replaces prompt()
    while True:
        session.send(label + " ")
        raw = session.recv()
        if raw and raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
        session.send(f"Please enter a number between 1 and {len(options)}.\n")


def prompt_text(session, label: str, min_len: int = 1, max_len: int = 20) -> str:
    # CHANGED: session replaces prompt()
    while True:
        session.send(label + " ")
        value = session.recv() or ""
        if min_len <= len(value) <= max_len:
            return value
        session.send(f"Must be between {min_len} and {max_len} characters.\n")


def prompt_password(session) -> str:
    # CHANGED: getpass replaced with session send/recv
    while True:
        session.send("Choose a password: ")
        pw1 = session.recv() or ""
        session.send("Confirm password: ")
        pw2 = session.recv() or ""
        if pw1 != pw2:
            session.send("Passwords do not match. Try again.\n")
        elif len(pw1) < 4:
            session.send("Password must be at least 4 characters.\n")
        else:
            return pw1


# ---------------------------------------------------------------------------
# Main creation flow
# ---------------------------------------------------------------------------

def run_character_creation(session) -> int | None:
    """
    Run the full character creation sequence.
    Returns the new character_id on success, or None if the player quits.
    """
    session.send("\n=== CHARACTER CREATION ===\n\n")  # CHANGED: was rule()

    # --- Step 1: Name ---
    while True:
        name = prompt_text(session, "Enter your character's name:",
                           min_len=2, max_len=20)
        name = name.capitalize()

        if not name.isalpha():
            session.send("Names may only contain letters.\n")
            continue

        if name_exists(name):
            session.send(f"A character named '{name}' already exists.\n")
            session.send("(If this is your character, return to the main menu to log in.)\n\n")
            continue

        break

    # --- Step 2: Gender ---
    session.send(f"\nHello, {name}. Choose your gender:\n\n")
    session.send("  [1] Male\n  [2] Female\n\n")
    gender_idx = prompt_choice(session, ">", [GENDER_MALE, GENDER_FEMALE])
    gender = [GENDER_MALE, GENDER_FEMALE][gender_idx]

    # --- Step 3: Race ---
    session.send("\nChoose your race:\n\n")
    session.send(display_races())              # CHANGED: send the returned string
    races = list(RACIAL_BONUSES.keys())
    race_idx = prompt_choice(session, ">", races)
    race = races[race_idx]
    session.send(f"\nYou have chosen: {race}.\n")

    # --- Step 4: Stat rolling ---
    session.send("\nRolling your stats (4d6, drop lowest)...\n")

    while True:
        raw_stats = roll_all_stats()
        final_stats = apply_racial_bonuses(raw_stats, race)
        bonuses = RACIAL_BONUSES[race]

        session.send(f"\nBase rolls with {race} racial bonuses applied:\n")
        session.send(display_stat_block(final_stats, bonuses))  # CHANGED: send string

        total = sum(final_stats.values())
        session.send(f"\n  Stat total: {total}\n\n")
        session.send("  [1] Accept these stats\n  [2] Reroll\n\n")

        choice = prompt_choice(session, ">", ["accept", "reroll"])
        if choice == 0:
            break

    # --- Step 5: Class ---
    session.send("\nChoose your class:\n\n")
    session.send(display_classes())            # CHANGED: send string
    class_idx = prompt_choice(session, ">", CLASSES)
    char_class = CLASSES[class_idx]
    session.send(f"\nYou have chosen: {char_class}.\n")

    # --- Step 6: Password ---
    session.send("\nSet your login password.\n\n")
    password = prompt_password(session)
    password_hash = hash_password(password)

    # --- Step 7: Summary and confirm ---
    resources = calculate_starting_resources(final_stats)

    session.send("\n=== SUMMARY ===\n\n")
    session.send(f"  Name    {name}\n")
    session.send(f"  Gender  {'Male' if gender == GENDER_MALE else 'Female'}\n")
    session.send(f"  Race    {race}\n")
    session.send(f"  Class   {char_class}\n\n")
    session.send(f"  HP        {resources['hp']}\n")
    session.send(f"  Power     {resources['power']}\n")
    session.send(f"  Endurance {resources['endurance']}\n")
    session.send(display_stat_block(final_stats))
    session.send("\n  [1] Create this character\n  [2] Start over\n\n")

    confirm = prompt_choice(session, ">", ["confirm", "restart"])

    if confirm == 1:
        session.send("Starting over...\n\n")
        return run_character_creation(session)  # recursive restart, session passes through

    character_id = insert_character(
        name=name,
        password_hash=password_hash,
        gender=gender,
        race=race,
        char_class=char_class,
        stats=final_stats,
        resources=resources,
    )

    session.send(f"\n{name} steps into the world. Good luck.\n\n")
    return character_id
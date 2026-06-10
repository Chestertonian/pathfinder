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

from output import to_ansi
from db import get_connection
from events import emit_event


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

BACKGROUNDS = [
    "Acolyte", "Aristocrat", "Criminal", "Laborer", "Farmer",
    "Hunter", "Brawler", "Sailor", "Wanderer", "Hermit",
    "Scholar", "Entertainer", "Outlander", "Merchant"
]

BACKGROUND_DESCRIPTIONS = {
    "Acolyte":    "Raised in service to a temple or shrine.",
    "Aristocrat": "Born to wealth and privilege.",
    "Criminal":   "Lived outside the law, by necessity or choice.",
    "Laborer":    "Hard physical work defined your early years.",
    "Farmer":     "Tended the land and lived by its rhythms.",
    "Hunter":     "Tracked and hunted to survive.",
    "Brawler":    "Settled disputes with your fists.",
    "Sailor":     "The sea was your home.",
    "Wanderer":   "Never stayed anywhere long enough to call it home.",
    "Hermit":     "Sought solitude and found wisdom in it.",
    "Scholar":    "Books and knowledge were your world.",
    "Entertainer":"Lived by your wit and performance.",
    "Outlander":  "Came from somewhere far and strange.",
    "Merchant":   "Traded, bartered, and haggled your way through life.",
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

def prompt_stat_priority(session) -> list[str]:
    """
    Ask the player to enter the 6 stats in priority order.
    Returns a list like ["strength", "dexterity", "constitution", ...]
    """
    abbr_to_full = {
        "STR": "strength", "DEX": "dexterity", "CON": "constitution",
        "INT": "intelligence", "WIS": "wisdom", "CHA": "charisma"
    }

    session.send("\nEnter your stat priority from highest to lowest.\n")
    session.send("Example: STR DEX CON INT WIS CHA\n\n")

    while True:
        session.send("> ")
        raw = session.recv() or ""
        parts = raw.upper().split()

        if len(parts) != 6:
            session.send("Please enter all 6 stats separated by spaces.\n")
            continue

        if any(p not in abbr_to_full for p in parts):
            valid = " ".join(abbr_to_full.keys())
            session.send(f"Invalid stat name. Valid stats: {valid}\n")
            continue

        if len(set(parts)) != 6:
            session.send("No duplicates allowed.\n")
            continue

        return [abbr_to_full[p] for p in parts]


def assign_stats(priority: list[str]) -> dict[str, int]:
    """
    Roll 6 values (4d6 drop lowest), sort descending,
    assign highest to first priority stat and so on.
    """
    rolls = sorted([roll_stat() for _ in range(6)], reverse=True)
    return {stat: rolls[i] for i, stat in enumerate(priority)}

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

def insert_character(
    name, password_hash, gender, race,
    background, char_class,
    stats, resources,
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO characters (
                    name, password_hash, gender, race, location_id,
                    background, class,
                    strength, dexterity, constitution,
                    intelligence, wisdom, charisma,
                    hp, hp_max, power, power_max, endurance, endurance_max
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    name,
                    password_hash,
                    gender,
                    race.lower(),
                    STARTING_LOCATION_ID,
                    background.lower(),
                    char_class.lower(),
                    stats["strength"],
                    stats["dexterity"],
                    stats["constitution"],
                    stats["intelligence"],
                    stats["wisdom"],
                    stats["charisma"],
                    resources["hp"],
                    resources["hp"],
                    resources["power"],
                    resources["power"],
                    resources["endurance"],
                    resources["endurance"],
                ),
            )

            character_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO audit_log
                    (character_id, action, entity_type, entity_id, details)
                VALUES (%s, 'character_created', 'character', %s, %s)
                """,
                (
                    character_id,
                    character_id,
                    f'{{"race": "{race}", "background": "{background}", "char_class": "{char_class}"}}',
                ),
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


def display_backgrounds() -> str:
    lines = []
    for i, bg in enumerate(BACKGROUNDS, 1):
        desc = BACKGROUND_DESCRIPTIONS.get(bg, "")
        lines.append(f"  [{i}] {bg:<12}  {desc}")
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
    session.send("\n=== CHARACTER CREATION ===\n\n")

    # Step 1: Name
    while True:
        name = prompt_text(session, "Enter your character's name:",
                           min_len=2, max_len=20)
        name = name.capitalize()
        if not name.isalpha():
            session.send("Names may only contain letters.\n")
            continue
        if name_exists(name):
            session.send(f"A character named '{name}' already exists.\n")
            continue
        break

    # Step 2: Gender
    session.send(f"\nHello, {name}. Choose your gender:\n\n")
    session.send("  [1] Male\n  [2] Female\n\n")
    gender_idx = prompt_choice(session, ">", [GENDER_MALE, GENDER_FEMALE])
    gender = [GENDER_MALE, GENDER_FEMALE][gender_idx]

    # Step 3: Race
    session.send("\nChoose your race:\n\n")
    session.send(display_races())
    races = list(RACIAL_BONUSES.keys())
    race_idx = prompt_choice(session, ">", races)
    race = races[race_idx]
    session.send(f"\nYou have chosen: {race}.\n")

    # Step 4: Stats
    session.send("\nRolling your stats (4d6, drop lowest)...\n")
    priority = prompt_stat_priority(session)

    rerolls_used = 0
    MAX_REROLLS = 20

    while True:
        raw_stats = assign_stats(priority)
        final_stats = apply_racial_bonuses(raw_stats, race)
        bonuses = RACIAL_BONUSES[race]

        session.send(f"\nBase rolls with {race} racial bonuses applied:\n")
        session.send(display_stat_block(final_stats, bonuses))
        total = sum(final_stats.values())
        session.send(f"\n  Stat total: {total}\n")
        session.send(f"  Rerolls used: {rerolls_used}/{MAX_REROLLS}\n\n")

        if rerolls_used >= MAX_REROLLS:
            session.send("No rerolls remaining. Stats accepted.\n")
            break

        session.send("  [1] Accept these stats\n  [2] Reroll\n\n")
        choice = prompt_choice(session, ">", ["accept", "reroll"])
        if choice == 0:
            break

        rerolls_used += 1
    # Step 5: Background          CHANGED: was class
    session.send("\nChoose your background:\n\n")
    session.send(display_backgrounds())
    bg_idx = prompt_choice(session, ">", BACKGROUNDS)
    background = BACKGROUNDS[bg_idx]
    session.send(f"\nYou have chosen: {background}.\n")

    # Step 6: Password
    session.send("\nSet your login password.\n\n")
    password = prompt_password(session)
    password_hash = hash_password(password)

    # Step 7: Summary
    resources = calculate_starting_resources(final_stats)
    session.send("\n=== SUMMARY ===\n\n")
    session.send(f"  Name        {name}\n")
    session.send(f"  Gender      {'Male' if gender == GENDER_MALE else 'Female'}\n")
    session.send(f"  Race        {race}\n")
    session.send(f"  Background  {background}\n\n")  # CHANGED: was class
    session.send(f"  HP          {resources['hp']}\n")
    session.send(f"  Power       {resources['power']}\n")
    session.send(f"  Endurance   {resources['endurance']}\n")
    session.send(display_stat_block(final_stats))
    session.send("\n  [1] Create this character\n  [2] Start over\n\n")

    confirm = prompt_choice(session, ">", ["confirm", "restart"])
    if confirm == 1:
        session.send("Starting over...\n\n")
        return run_character_creation(session)

    character_id = insert_character(
        name=name,
        password_hash=password_hash,
        gender=gender,
        race=race,
        background=background,         
        stats=final_stats,
        resources=resources,
        char_class='Immigrant',
    )

    session.send(f"\n{name} steps into the world. Good luck.\n\n")
    
    emitted=to_ansi(f"\n [red]{' '*10} {name} the New Player arrives. [/red]\n")

    with get_connection() as conn:
        emit_event(
            conn,
            event_type="global",
            sender_id=None,
            message=emitted,
        )

    return character_id 
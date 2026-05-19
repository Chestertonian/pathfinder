"""
character_creation.py — New character creation flow

Handles the full interactive creation sequence:
  name → gender → race → stat roll → class → password → DB insert

Returns the new character's ID on success.
Call run_character_creation() from your main entry point.
"""

import getpass
import hashlib
import random
import secrets

from db import get_connection
from output import (
    blank, console, print_error, print_flavor, print_info,
    print_stat, print_success, print_title, prompt, rule,
    COLOR_STAT, COLOR_INFO, COLOR_TITLE, COLOR_PROMPT,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STARTING_LOCATION_ID = 1  # TODO: replace with real starting town ID

CLASSES = ["Fighter", "Rogue", "Wizard", "Cleric", "Ranger"]

RACIAL_BONUSES = {
    "Human":   {"strength": 1, "dexterity": 1, "constitution": 1,
                "intelligence": 1, "wisdom": 1, "charisma": 1},
    "Elf":     {"dexterity": 2, "intelligence": 1, "constitution": -1},
    "Dwarf":   {"constitution": 2, "strength": 1, "charisma": -1},
    "Gnome":   {"intelligence": 2, "wisdom": 1, "strength": -1},
    "Centaur": {"strength": 2, "constitution": 2, "intelligence": -1, "charisma": -1},
}

STAT_NAMES = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
STAT_ABBR  = ["STR",      "DEX",       "CON",          "INT",          "WIS",    "CHA"]

GENDER_MALE   = 1
GENDER_FEMALE = 2

RACE_DESCRIPTIONS = {
    "Human": "Versatile and ambitious, humans adapt quickly to any role.",
    "Elf": "Graceful and perceptive, elves excel in agility and magic.",
    "Dwarf": "Stout and resilient, dwarves are masters of endurance and craft.",
    "Gnome": "Curious and clever, gnomes thrive on invention and wit.",
    "Centaur": "Swift and powerful, centaurs combine mobility with raw strength.",
}


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Return a salted SHA-256 hash string suitable for storage."""
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Return True if the password matches the stored hash."""
    salt, digest = stored_hash.split(":", 1)
    candidate = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return candidate == digest


# ---------------------------------------------------------------------------
# Stat rolling
# ---------------------------------------------------------------------------

def roll_stat() -> int:
    """Roll 4d6, drop the lowest die, return the sum."""
    dice = [random.randint(1, 6) for _ in range(4)]
    return sum(sorted(dice)[1:])


def roll_all_stats() -> dict[str, int]:
    """Roll all six stats and return them as a dict."""
    return {stat: roll_stat() for stat in STAT_NAMES}


def apply_racial_bonuses(stats: dict[str, int], race: str) -> dict[str, int]:
    """Return a new stats dict with the race's bonuses applied."""
    result = dict(stats)
    for stat, bonus in RACIAL_BONUSES[race].items():
        result[stat] = result[stat] + bonus
    return result


# ---------------------------------------------------------------------------
# Derived resource stats
# ---------------------------------------------------------------------------

def stat_modifier(value: int) -> int:
    return (value - 10) // 2


def calculate_starting_resources(stats: dict[str, int]) -> dict[str, int]:
    """Derive HP, power, and endurance from final stats."""
    con_mod = stat_modifier(stats["constitution"])
    int_mod = stat_modifier(stats["intelligence"])
    hp        = max(10, 25 + con_mod * 2)
    power     = max(10, 25 + int_mod * 2)
    endurance = 100
    return {"hp": hp, "power": power, "endurance": endurance}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def name_exists(name: str) -> bool:
    """Return True if a character with this name already exists."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM characters WHERE LOWER(name) = LOWER(%s)", (name,)
            )
            return cur.fetchone() is not None


def insert_character(
    name: str,
    password_hash: str,
    gender: int,
    race: str,
    char_class: str,
    stats: dict[str, int],
    resources: dict[str, int],
) -> int:
    """Insert a new character row and return the new character's ID."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO characters (
                    name, password_hash, gender, class, location_id,
                    strength, dexterity, constitution, intelligence, wisdom, charisma,
                    hp, hp_max, power, power_max, endurance, endurance_max
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    name, password_hash, gender, char_class, STARTING_LOCATION_ID,
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
# Display helpers
# ---------------------------------------------------------------------------

def display_stat_block(stats: dict[str, int], bonuses: dict[str, int] | None = None) -> None:
    """Print a styled stat block, showing racial bonuses if provided."""
    blank()
    for stat, abbr in zip(STAT_NAMES, STAT_ABBR):
        value = stats[stat]
        if bonuses and stat in bonuses:
            b = bonuses[stat]
            sign = "+" if b >= 0 else ""
            bonus_color = COLOR_STAT if b > 0 else "red3"
            console.print(
                f"[{COLOR_INFO}]{abbr:<4}[/{COLOR_INFO}]"
                f"[{COLOR_STAT}]{value:>2}[/{COLOR_STAT}]"
                f"  [{COLOR_INFO}](roll {value - b:>2}  "
                f"[{bonus_color}]{sign}{b}[/{bonus_color}])[/{COLOR_INFO}]"
            )
        else:
            console.print(
                f"[{COLOR_INFO}]{abbr:<4}[/{COLOR_INFO}] [{COLOR_STAT}]{value:>2}[/{COLOR_STAT}]"
            )
    blank()


def display_races() -> None:
    """Print numbered race options with stat bonuses and descriptions."""
    blank()

    for i, (race, bonuses) in enumerate(RACIAL_BONUSES.items(), 1):
        # Build bonus string
        parts = []
        for stat, val in bonuses.items():
            abbr = STAT_ABBR[STAT_NAMES.index(stat)]
            sign = "+" if val >= 0 else ""
            color = COLOR_STAT if val > 0 else "red3"
            parts.append(f"[{color}]{sign}{val} {abbr}[/{color}]")

        bonus_str = ", ".join(parts)

        # Get description
        desc = RACE_DESCRIPTIONS.get(race, "No description available.")

        # Print race line
        console.print(
            f"  [{COLOR_PROMPT}][{i}][/{COLOR_PROMPT}] "
            f"[{COLOR_TITLE}]{race:<10}[/{COLOR_TITLE}]  "
            f"{bonus_str}"
        )

        # Print description indented underneath
        console.print(
            f"      [dim]{desc}[/dim]"
        )

    blank()


def display_classes() -> None:
    """Print numbered class options."""
    blank()
    for i, cls in enumerate(CLASSES, 1):
        console.print(f"  [{COLOR_PROMPT}][{i}][/{COLOR_PROMPT}] [{COLOR_TITLE}]{cls}[/{COLOR_TITLE}]")
    blank()


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def prompt_choice(label: str, options: list) -> int:
    """Return the 0-based index of the player's choice. Loops until valid."""
    while True:
        raw = prompt(label)
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
        print_error(f"Please enter a number between 1 and {len(options)}.")


def prompt_text(label: str, min_len: int = 1, max_len: int = 20) -> str:
    """Ask for a text value and enforce length limits."""
    while True:
        value = prompt(label)
        if min_len <= len(value) <= max_len:
            return value
        print_error(f"Must be between {min_len} and {max_len} characters.")


def prompt_password() -> str:
    """Ask for a password twice and confirm they match."""
    while True:
        pw1 = getpass.getpass("Choose a password: ")
        pw2 = getpass.getpass("Confirm password:  ")
        if pw1 == pw2:
            if len(pw1) >= 4:
                return pw1
            print_error("Password must be at least 4 characters.")
        else:
            print_error("Passwords do not match. Try again.")


# ---------------------------------------------------------------------------
# Main creation flow
# ---------------------------------------------------------------------------

def run_character_creation() -> int | None:
    """
    Run the full character creation sequence.
    Returns the new character_id on success, or None if the player quits.
    """
    rule("CHARACTER CREATION")

    # --- Step 1: Name ---
    blank()
    while True:
        name = prompt_text("Enter your character's name:", min_len=2, max_len=20).capitalize()

        if not name.isalpha():
            print_error("Names may only contain letters.")
            continue

        if name_exists(name):
            print_error(f"A character named '{name}' already exists.")
            print_info("(If this is your character, return to the main menu to log in.)")
            blank()
            continue

        break

    # --- Step 2: Gender ---
    blank()
    print_info(f"Hello, {name}. Choose your gender:")
    blank()
    console.print(f"  [{COLOR_PROMPT}][1][/{COLOR_PROMPT}] [{COLOR_TITLE}]Male[/{COLOR_TITLE}]")
    console.print(f"  [{COLOR_PROMPT}][2][/{COLOR_PROMPT}] [{COLOR_TITLE}]Female[/{COLOR_TITLE}]")
    blank()
    gender_idx = prompt_choice(">", [GENDER_MALE, GENDER_FEMALE])
    gender = [GENDER_MALE, GENDER_FEMALE][gender_idx]

    # --- Step 3: Race ---
    blank()
    print_info("Choose your race:")
    display_races()
    races = list(RACIAL_BONUSES.keys())
    race_idx = prompt_choice(">", races)
    race = races[race_idx]
    blank()
    print_success(f"You have chosen: {race}.")

    # --- Step 4: Stat rolling ---
    blank()
    print_info("Rolling your stats (4d6, drop lowest)...")

    while True:
        raw_stats   = roll_all_stats()
        final_stats = apply_racial_bonuses(raw_stats, race)
        bonuses     = RACIAL_BONUSES[race]

        blank()
        print_info(f"Base rolls with {race} racial bonuses applied:")
        display_stat_block(final_stats, bonuses)

        total = sum(final_stats.values())
        console.print(f"  [{COLOR_INFO}]Stat total: [{COLOR_STAT}]{total}[/{COLOR_STAT}][/{COLOR_INFO}]")
        blank()
        console.print(f"  [{COLOR_PROMPT}][1][/{COLOR_PROMPT}] [{COLOR_TITLE}]Accept these stats[/{COLOR_TITLE}]")
        console.print(f"  [{COLOR_PROMPT}][2][/{COLOR_PROMPT}] [{COLOR_TITLE}]Reroll[/{COLOR_TITLE}]")
        blank()
        choice = prompt_choice(">", ["accept", "reroll"])
        if choice == 0:
            break
        blank()

    # --- Step 5: Class ---
    blank()
    print_info("Choose your class:")
    display_classes()
    class_idx  = prompt_choice(">", CLASSES)
    char_class = CLASSES[class_idx]
    blank()
    print_success(f"You have chosen: {char_class}.")

    # --- Step 6: Password ---
    blank()
    print_info("Set your login password.")
    blank()
    password      = prompt_password()
    password_hash = hash_password(password)

    # --- Step 7: Confirm and insert ---
    resources = calculate_starting_resources(final_stats)

    blank()
    rule("SUMMARY")
    blank()
    console.print(f"[{COLOR_INFO}]Name  [/{COLOR_INFO}] [{COLOR_TITLE}]{name}[/{COLOR_TITLE}]")
    console.print(f"[{COLOR_INFO}]Gender[/{COLOR_INFO}] [{COLOR_TITLE}]{'Male' if gender == GENDER_MALE else 'Female'}[/{COLOR_TITLE}]")
    console.print(f"[{COLOR_INFO}]Race  [/{COLOR_INFO}] [{COLOR_TITLE}]{race}[/{COLOR_TITLE}]")
    console.print(f"[{COLOR_INFO}]Class [/{COLOR_INFO}] [{COLOR_TITLE}]{char_class}[/{COLOR_TITLE}]")
    blank()
    print_stat("HP: ",        resources["hp"])
    print_stat("Power: ",     resources["power"])
    print_stat("Endurance: ", resources["endurance"])
    display_stat_block(final_stats)
    rule()
    blank()
    console.print(f"[{COLOR_PROMPT}][1][/{COLOR_PROMPT}] [{COLOR_TITLE}]Create this character[/{COLOR_TITLE}]")
    console.print(f"[{COLOR_PROMPT}][2][/{COLOR_PROMPT}] [{COLOR_TITLE}]Start over[/{COLOR_TITLE}]")
    blank()
    confirm = prompt_choice(">", ["confirm", "restart"])

    if confirm == 1:
        print_info("Starting over...")
        blank()
        return run_character_creation()

    character_id = insert_character(
        name=name.lower(),
        password_hash=password_hash,
        gender=gender,
        race=race,
        char_class=char_class,
        stats=final_stats,
        resources=resources,
    )

    blank()
    print_flavor(f"{name} steps into the world. Good luck.")
    blank()
    return character_id
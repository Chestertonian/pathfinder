"""
game_loop.py — Main game loop

Thin dispatcher. Its only job is to:
  1. Load the character
  2. Read input
  3. Parse it into a verb + args
  4. Hand off to the right Command
  5. Print the result

To add a new command: write a new file in commands/, import it here,
and add it to the COMMANDS dict. Nothing else changes.

Performance rule: each command gets exactly ONE connection, opened here
and passed through. No command should open its own connection.
"""

from db import get_connection
from models import Character
from output import blank, console, print_error, print_flavor, print_success, prompt

from commands.look import LookCommand


# ---------------------------------------------------------------------------
# Direction aliases
# ---------------------------------------------------------------------------
_DIRS = {
    "n": "north", "north": "north",
    "s": "south", "south": "south",
    "e": "east",  "east":  "east",
    "w": "west",  "west":  "west",
    "ne": "northeast", "northeast": "northeast",
    "nw": "northwest", "northwest": "northwest",
    "se": "southeast", "southeast": "southeast",
    "sw": "southwest", "southwest": "southwest",
    "u":  "up",   "up":   "up",
    "d":  "down", "down": "down",
}

# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------
COMMANDS = {
    "look": LookCommand(),
    # "exits":     ExitsCommand(),
    # "inventory": InventoryCommand(),
    # "take":      TakeCommand(),
}


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------

def _parse(raw: str) -> tuple[str, list[str]]:
    """Split raw input into (verb, args). Returns ("", []) for empty input."""
    parts = raw.strip().lower().split()
    if not parts:
        return ("", [])
    return (parts[0], parts[1:])


def _run_command(command, character, conn, args):
    """Execute a command and print its output if any."""
    output = command.execute(character, conn, args)
    if output:
        console.print(output)


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

def run_game_loop(character_id: int) -> None:
    """
    Main game loop. One DB connection is opened per command and closed
    when the command finishes. No command opens its own connection.

    The character is fetched once per command — not multiple times.
    After a move, we update character.location_id in memory (move_to
    already does this) so we don't need to re-fetch just to show the room.
    """

    # Initial load — just to get the name for the greeting
    with get_connection() as conn:
        character = Character.get_by_id(conn, character_id)

    if character is None:
        print_error("Could not load character. Returning to menu.")
        return

    print_success(f"Entering the world as {character.name}...")

    # Show the starting room — one connection, character already loaded
    with get_connection() as conn:
        character = Character.get_by_id(conn, character_id)
        _run_command(COMMANDS["look"], character, conn, [])

    # ── Main loop ─────────────────────────────────────────────────────────
    while True:
        raw = prompt(">")
        if not raw:
            continue

        verb, args = _parse(raw)

        # ── Quit ──────────────────────────────────────────────────────────
        if verb in ("quit", "exit", "q"):
            blank()
            print_flavor(f"{character.name} rests for now. Farewell.")
            blank()
            break

        # ── Movement ──────────────────────────────────────────────────────
        elif verb in _DIRS:
            direction = _DIRS[verb]
            with get_connection() as conn:
                # One fetch, one exit check, one update, one room display
                # — all inside the same connection.
                character = Character.get_by_id(conn, character_id)
                room = character.get_room(conn)
                exit_data = room.get_exit(conn, direction)

                if exit_data is None:
                    print_error(f"You cannot go {direction} from here.")
                    continue
                if exit_data["is_locked"]:
                    print_error("That way is locked.")
                    continue

                # move_to() commits and updates character.location_id in memory
                character.move_to(conn, exit_data["to_location"])

                # No re-fetch needed — character already has the new location_id
                _run_command(COMMANDS["look"], character, conn, [])

        # ── Registered commands ───────────────────────────────────────────
        elif verb in COMMANDS:
            with get_connection() as conn:
                character = Character.get_by_id(conn, character_id)
                _run_command(COMMANDS[verb], character, conn, args)

        # ── Unknown ───────────────────────────────────────────────────────
        else:
            print_error(f"Unknown command '{verb}'. Try: look, north, south, quit.")
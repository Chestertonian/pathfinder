"""
game_loop.py — Main game loop

Thin dispatcher. Its only job is to:
  1. Load the character
  2. Start the broadcast poller
  3. Read input from session, parse it, hand off to the right Command
  4. Send the result back over session
  5. Stop the poller on quit

To add a new command: write a new file in commands/, import it here,
and add it to the COMMANDS dict. Nothing else changes.

Performance rule: each command gets exactly ONE connection, opened here
and passed through. No command should open its own connection.
"""

from db import get_connection
from models import BroadcastMessage, Character
from broadcast import BroadcastPoller
from events import emit_event
from commands.kick import register_session, unregister_session

from commands.look import LookCommand
from commands.smell import SmellCommand
from commands.listen import ListenCommand
from commands.exits import ExitsCommand
from commands.score import ScoreCommand
from commands.hp import HpCommand
from commands.time import TimeCommand
from commands.who import WhoCommand
from commands.finger import FingerCommand

from commands.say import SayCommand
from commands.emote import EmoteCommand
from commands.tell import TellCommand
from commands.chat import ChatCommand

from combat.attack import AttackCommand
from combat.flee import FleeCommand

from commands.spawn import SpawnCommand
from commands.summon import SummonCommand
from commands.spawnitem import SpawnItemCommand
from commands.proclaim import ProclaimCommand
from commands.world import WorldCommand
from commands.shutdown import ShutdownCommand
from commands.kick import KickCommand
from commands.find import FindCommand
from commands.goto import GotoCommand
from commands.players import PlayersCommand
from commands.setstat import SetstatCommand

from commands.items import GetCommand, DropCommand, InventoryCommand

# CHANGED: removed all output.py imports — output now goes through session


# ---------------------------------------------------------------------------
# Direction aliases — UNCHANGED
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
# Command registry — UNCHANGED
# ---------------------------------------------------------------------------

COMMANDS = {
    "look":      LookCommand(),
    "l":         LookCommand(),

    "spawn":     SpawnCommand(),
    "spawnitem": SpawnItemCommand(),
    "summon":    SummonCommand(),
    "proclaim":  ProclaimCommand(),
    "shutdown":  ShutdownCommand(),
    "kick":      KickCommand(),
    "find":      FindCommand(),
    "goto":      GotoCommand(),
    "setstat":   SetstatCommand(),
    "players":   PlayersCommand(),

    "say":       SayCommand(),
    ";":         EmoteCommand(),
    "emote":     EmoteCommand(),
    "tell":      TellCommand(),
    "chat":      ChatCommand(),

    "world":     WorldCommand(),

    "exits":     ExitsCommand(),

    "i":         InventoryCommand(),
    "inventory": InventoryCommand(),
    "get":       GetCommand(),
    "drop":      DropCommand(),

    "score":     ScoreCommand(),
    "hp":        HpCommand(),
    "who":       WhoCommand(),
    "smell":     SmellCommand(),
    "listen":    ListenCommand(),
    "time":      TimeCommand(),
    "finger":    FingerCommand(),

    "attack":    AttackCommand(),
    "flee":      FleeCommand(),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(raw: str) -> tuple[str, list[str]]:
    """Split raw input into (verb, args). UNCHANGED."""
    if raw.startswith(";"):
        raw = "emote " + raw[1:].lstrip()
    parts = raw.strip().split()
    if not parts:
        return ("", [])
    return (parts[0].lower(), parts[1:])


def _run_command(command, character, conn, args, session):
    # CHANGED: takes session, sends output over socket instead of console.print()
    output = command.execute(character, conn, args, session)
    if output:
        session.send("\n"+output + "\n\n")


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

def run_game_loop_for_client(character_id: int, session) -> None:
    # CHANGED: renamed, takes session instead of using local terminal
    """
    Main game loop for a networked client session.

    Responsibilities:
      - Load player
      - Start broadcast polling (session-aware)
      - Handle commands
      - Handle movement
      - Clean shutdown
    """

    # -------------------------------------------------------------------
    # Initial load
    # -------------------------------------------------------------------

    with get_connection() as conn:
        character = Character.get_by_id(conn, character_id)

    if character is None:
        session.send("Could not load character. Returning to menu.\n")  # CHANGED
        return

    session.send(f"Entering the world as {character.name.capitalize()}...\n")  # CHANGED

    # -------------------------------------------------------------------
    # Broadcast startup
    # -------------------------------------------------------------------

    with get_connection() as conn:
        starting_broadcast_id = BroadcastMessage.get_latest_id(conn)

    # CHANGED: pass session into poller so it sends to the right player
    poller = BroadcastPoller(starting_broadcast_id, character_id, session)
    poller.start()
    register_session(character_id, session)


    try:

        # ---------------------------------------------------------------
        # Initial room look
        # ---------------------------------------------------------------

        with get_connection() as conn:
            character = Character.get_by_id(conn, character_id)
            _run_command(COMMANDS["look"], character, conn, [], session)  # CHANGED

        # ---------------------------------------------------------------
        # Main loop
        # ---------------------------------------------------------------

        while True:

            raw = session.recv()              # CHANGED: reads from socket

            if raw is None:
                # Player disconnected unexpectedly
                break

            if not raw:
                continue

            verb, args = _parse(raw)

            # -----------------------------------------------------------
            # Quit
            # -----------------------------------------------------------

            if verb in ("quit", "exit", "q"):

                session.send("\n")
                session.send(
                    f"{character.name.capitalize()} rests for now. Farewell.\n"
                )
                session.send("\n")

                with get_connection() as conn:
                    character = Character.get_by_id(conn, character_id)
                    room = character.get_room(conn)
                    emit_event(
                        conn,
                        event_type="room",
                        sender_id=character_id,
                        location_id=room.id,
                        message=f"{character.name.capitalize()} fades from the world.",
                    )

                break

            # -----------------------------------------------------------
            # Everything else
            # -----------------------------------------------------------

            with get_connection() as conn:

                character = Character.get_by_id(conn, character_id)
                room = character.get_room(conn)

                direction = _DIRS.get(verb, verb)
                exit_data = room.get_exit(conn, direction)

                # -------------------------------------------------------
                # Valid exit found
                # -------------------------------------------------------

                if exit_data is not None:
                    
                    if character.endurance <= 0:
                        session.send("You are too exhausted to move.\n")
                        continue

                    if exit_data["is_locked"]:
                        session.send("That way is locked.\n")
                        continue

                    old_room = room.id
                    new_room = exit_data["to_location"]

                    character.move_to(conn, new_room)

                    # ADDED: record when player entered the new room
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE characters SET room_entered_at = NOW() WHERE id = %s",
                            (character.id,)
                        )
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE characters
                            SET endurance = GREATEST(0, endurance - %s)
                            WHERE id = %s
                            """,
                            (exit_data["cost"], character.id),
                        )

                    # Check if player is now out of EP
                    character = Character.get_by_id(conn, character_id)
                    if character.endurance <= 0:
                        session.send("You are exhausted and cannot move.\n")

                    character = Character.get_by_id(conn, character_id)
                    _run_command(COMMANDS["look"], character, conn, [], session)

                    emit_event(
                        conn,
                        event_type="room",
                        sender_id=character.id,
                        location_id=old_room,
                        message=f"{character.name} leaves {direction}.",
                    )

                    emit_event(
                        conn,
                        event_type="room",
                        sender_id=character.id,
                        location_id=new_room,
                        message=f"{character.name} arrives.",
                    )

                    continue
                # -------------------------------------------------------
                # Registered commands
                # -------------------------------------------------------

                if verb in COMMANDS:
                    _run_command(COMMANDS[verb], character, conn, args, session)  # CHANGED
                    continue

                # -------------------------------------------------------
                # Unknown
                # -------------------------------------------------------

                session.send(                 # CHANGED
                    f"Unknown command '{verb}'. Try: look, north, quit.\n"
                )

    finally:

        # ---------------------------------------------------------------
        # Always stop background poller
        # ---------------------------------------------------------------

        poller.stop()
        unregister_session(character_id)

        # ---------------------------------------------------------------
        # Always mark player offline
        # ---------------------------------------------------------------

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE characters SET is_logged_in = FALSE WHERE id = %s",
                        (character_id,),
                    )
                conn.commit()

        except Exception as e:
            print(f"[FATAL] Failed to mark character offline: {e}")
            # NOTE: print() here is intentional — this is a server-side
            # error log, not player output. Session may already be dead.
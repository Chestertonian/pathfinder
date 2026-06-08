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
from models import BroadcastMessage, Character, Room
from broadcast import BroadcastPoller
import room_scripts
from commands.power import PowerCommand
from events import emit_event
from commands.kick import register_session, unregister_session

from commands.look import LookCommand
from commands.smell import SmellCommand
from commands.listen import ListenCommand
from commands.search import SearchCommand
from commands.exits import ExitsCommand
from commands.score import ScoreCommand
from commands.hp import HpCommand
from commands.time import TimeCommand
from commands.who import WhoCommand
from commands.finger import FingerCommand
from commands.level import LevelCommand
from commands.powers_list import PowersCommand

from commands.say import SayCommand
from commands.emote import EmoteCommand as EmCommand
from commands.emotes import EmoteCommand
from commands.tell import TellCommand
from commands.ask import AskCommand
from commands.channels import ChannelCommand
from commands.history import HistoryCommand

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
from commands.promote import PromoteCommand, DemoteCommand

from commands.items import GetCommand, DropCommand, InventoryCommand
from commands.equipment import EquipCommand, EqCommand, RemoveCommand, UnequipCommand
from commands.give import GiveCommand

from commands.economy import WithdrawCommand, DepositCommand, WealthCommand
from commands.shop import BuyCommand, SellCommand, ListCommand

from commands.bulletinboard import WriteCommand, SubjectsCommand, ReadCommand, EraseCommand


# ---------------------------------------------------------------------------
# Direction aliases
# ---------------------------------------------------------------------------

_DIRS = {
    "n": "north",
    "north": "north",
    "s": "south",
    "south": "south",
    "e": "east",
    "east": "east",
    "w": "west",
    "west": "west",
    "ne": "northeast",
    "northeast": "northeast",
    "nw": "northwest",
    "northwest": "northwest",
    "se": "southeast",
    "southeast": "southeast",
    "sw": "southwest",
    "southwest": "southwest",
    "u": "up",
    "up": "up",
    "d": "down",
    "down": "down",
}


# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------

COMMANDS = {
    "look": LookCommand(),
    "l": LookCommand(),
    "spawn": SpawnCommand(),
    "spawnitem": SpawnItemCommand(),
    "summon": SummonCommand(),
    "proclaim": ProclaimCommand(),
    "shutdown": ShutdownCommand(),
    "kick": KickCommand(),
    "find": FindCommand(),
    "goto": GotoCommand(),
    "setstat": SetstatCommand(),
    "promote": PromoteCommand(),
    "demote": DemoteCommand(),
    "players": PlayersCommand(),
    "say": SayCommand(),
    ";": EmCommand(),
    "emote": EmCommand(),
    "tell": TellCommand(),
    "ask": AskCommand(),
    "history": HistoryCommand(),
    "chat": ChannelCommand("chat"),
    "merchant": ChannelCommand("merchant"),
    "fighter": ChannelCommand("fighter"),
    "wizard": ChannelCommand("wizard"),
    "cleric": ChannelCommand("cleric"),
    "rogue": ChannelCommand("rogue"),
    "thief": ChannelCommand("thief"),
    "ranger": ChannelCommand("ranger"),
    "staff": ChannelCommand("staff"),
    "council": ChannelCommand("council"),
    "world": ChannelCommand("world"),
    "northlands": ChannelCommand("northlands"),
    "smile": EmoteCommand("smile"),
    "nod": EmoteCommand("nod"),
    "bow": EmoteCommand("bow"),
    "wave": EmoteCommand("wave"),
    "laugh": EmoteCommand("laugh"),
    "chuckle": EmoteCommand("chuckle"),
    "snicker": EmoteCommand("snicker"),
    "giggle": EmoteCommand("giggle"),
    "sigh": EmoteCommand("sigh"),
    "shrug": EmoteCommand("shrug"),
    "frown": EmoteCommand("frown"),
    "glare": EmoteCommand("glare"),
    "wink": EmoteCommand("wink"),
    "smirk": EmoteCommand("smirk"),
    "cheer": EmoteCommand("cheer"),
    "grin": EmoteCommand("grin"),
    "scowl": EmoteCommand("scowl"),
    "poke": EmoteCommand("poke"),
    "point": EmoteCommand("point"),
    "nod_slow": EmoteCommand("nod_slow"),
    "shake_head": EmoteCommand("shake_head"),
    "clap": EmoteCommand("clap"),
    "crossarms": EmoteCommand("crossarms"),
    "squint": EmoteCommand("squint"),
    "torex": EmoteCommand("torex"),
    "exits": ExitsCommand(),
    "i": InventoryCommand(),
    "inventory": InventoryCommand(),
    "get": GetCommand(),
    "drop": DropCommand(),
    "score": ScoreCommand(),
    "hp": HpCommand(),
    "who": WhoCommand(),
    "smell": SmellCommand(),
    "listen": ListenCommand(),
    "search": SearchCommand(),
    "time": TimeCommand(),
    "finger": FingerCommand(),
    "level": LevelCommand(),
    "powers": PowersCommand(),
    "attack": AttackCommand(),
    "flee": FleeCommand(),
    "salute": PowerCommand("salute"),
    "magelight": PowerCommand("magelight"),
    "prayer": PowerCommand("prayer"),
    "flourish": PowerCommand("flourish"),
    "slip": PowerCommand("slip"),
    "whittle": PowerCommand("whittle"),
    "headbutt": PowerCommand("headbutt"),
    "trample": PowerCommand("trample"),
    "pray": PowerCommand("pray"),
    "maketorch": PowerCommand("maketorch"),
    "hawkwares": PowerCommand("hawkwares"),
    "beautician": PowerCommand("beautician"),
    "tailor":   PowerCommand("tailor"),
    "ordernumber": PowerCommand("ordernumber"),
    "dyecast":   PowerCommand("dyecast"),
    "subjects": SubjectsCommand(),
    "write": WriteCommand(),
    "erase": EraseCommand(),
    "read": ReadCommand(),
    "eq":   EqCommand(),
    "equip": EquipCommand(),
    "remove": RemoveCommand(),
    "unequip": UnequipCommand(),
    "withdraw": WithdrawCommand(),
    "deposit":  DepositCommand(),
    "wealth":   WealthCommand(),
    "list":     ListCommand(),
    "buy":      BuyCommand(),
    "sell":     SellCommand(),
    "give":     GiveCommand(),
    
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(raw: str) -> tuple[str, list[str]]:
    """Split raw input into (verb, args)."""
    if raw.startswith(";"):
        raw = "emote " + raw[1:].lstrip()
    parts = raw.strip().split()
    if not parts:
        return ("", [])
    return (parts[0].lower(), parts[1:])


def _run_command(command, character, conn, args, session):
    output = command.execute(character, conn, args, session)
    if output:
        session.send("\n" + output + "\n\n")


def _trigger_aggro(conn, character, room_id: int) -> None:
    """
    Check for hostile NPCs in the room and initiate combat.
    Skips NPCs already fighting this character.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ni.id, nt.name
            FROM npc_instances ni
            JOIN npc_templates nt ON nt.id = ni.npc_template_id
            WHERE ni.location_id = %s
              AND ni.is_alive = TRUE
              AND nt.is_hostile = TRUE
              AND ni.id NOT IN (
                  SELECT defender_id FROM active_combats
                  WHERE attacker_type = 'character'
                    AND attacker_id = %s
                    AND defender_type = 'npc'
              )
            """,
            (room_id, character.id),
        )
        hostile_npcs = cur.fetchall()

    for npc_id, npc_name in hostile_npcs:
        with conn.cursor() as cur:
            # Player → NPC
            cur.execute(
                """
                INSERT INTO active_combats
                    (attacker_type, attacker_id, defender_type, defender_id, location_id)
                VALUES ('character', %s, 'npc', %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (character.id, npc_id, room_id),
            )

            # NPC → Player (only if not already retaliating against someone)
            cur.execute(
                """
                SELECT id FROM active_combats
                WHERE attacker_type = 'npc'
                  AND attacker_id = %s
                  AND defender_type = 'character'
                """,
                (npc_id,),
            )
            if cur.fetchone() is None:
                cur.execute(
                    """
                    INSERT INTO active_combats
                        (attacker_type, attacker_id, defender_type, defender_id, location_id)
                    VALUES ('npc', %s, 'character', %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (npc_id, character.id, room_id),
                )

        conn.commit()

        emit_event(
            conn,
            event_type="combat",
            sender_id=character.id,
            location_id=room_id,
            message=f"{npc_name.capitalize()} attacks {character.name}!",
        )


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------


def run_game_loop_for_client(character_id: int, session) -> None:
    """
    Main game loop for a networked client session.
    """

    with get_connection() as conn:
        character = Character.get_by_id(conn, character_id)

    if character is None:
        session.send("Could not load character. Returning to menu.\n")
        return

    session.send(f"Entering the world as {character.name.capitalize()}...\n")

    with get_connection() as conn:
        starting_broadcast_id = BroadcastMessage.get_latest_id(conn)

    poller = BroadcastPoller(starting_broadcast_id, character_id, session)
    poller.start()
    register_session(character_id, session)

    try:

        # Initial look
        with get_connection() as conn:
            character = Character.get_by_id(conn, character_id)
            _run_command(COMMANDS["look"], character, conn, [], session)

        while True:

            raw = session.recv()

            if raw is None:
                break

            if not raw:
                continue

            verb, args = _parse(raw)

            # -----------------------------------------------------------
            # Pending look (after death/respawn)
            # -----------------------------------------------------------

            with get_connection() as conn:
                character = Character.get_by_id(conn, character_id)
                if character.pending_look:
                    _run_command(COMMANDS["look"], character, conn, [], session)
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE characters SET pending_look = FALSE WHERE id = %s",
                            (character_id,),
                        )
                    conn.commit()

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

                    # Access check
                    required_class = exit_data["required_class"]
                    required_unguilded = exit_data["required_unguilded"]

                    if required_class or required_unguilded:
                        is_unguilded = (character.char_class.capitalize().strip() in (None, "", "Immigrant", "immigrant"))

                        passed = False

                        if required_unguilded and is_unguilded:
                            passed = True

                        if required_class and character.char_class == required_class:
                            passed = True

                        if not passed:
                            session.send("A guild warden blocks your path.\n")
                            continue
                        
                    old_room = room.id
                    new_room = exit_data["to_location"]

                    character.move_to(conn, new_room)

                    # EP drain
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE characters
                            SET endurance = GREATEST(0, endurance - %s)
                            WHERE id = %s
                            """,
                            (exit_data["cost"], character.id),
                        )

                    # room_entered_at
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE characters SET room_entered_at = NOW() WHERE id = %s",
                            (character.id,),
                        )

                    # Aggro check
                    _trigger_aggro(conn, character, new_room)

                    character = Character.get_by_id(conn, character_id)

                    if character.endurance <= 0:
                        session.send("You are exhausted.\n")

                    _run_command(COMMANDS["look"], character, conn, [], session)

                    # Room script on_enter
                    new_room_obj = Room.get_by_id(conn, new_room)
                    if new_room_obj is not None:
                        script = room_scripts.get_script(new_room_obj.script_key)
                        if script and hasattr(script, "on_enter"):
                            script.on_enter(character, new_room_obj, conn, session)

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
                # Room script on_command
                # -------------------------------------------------------

                script = room_scripts.get_script(room.script_key)
                if script and hasattr(script, "on_command"):
                    consumed = script.on_command(
                        character, room, verb, args, conn, session
                    )
                    if consumed:
                        continue

                # -------------------------------------------------------
                # Registered commands
                # -------------------------------------------------------

                if verb in COMMANDS:
                    _run_command(COMMANDS[verb], character, conn, args, session)
                    continue

                # -------------------------------------------------------
                # Unknown
                # -------------------------------------------------------

                session.send(f"Unknown command '{verb}'. Try: look, north, quit.\n")

    finally:

        poller.stop()
        unregister_session(character_id)

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

"""
commands/read.py — ReadCommand

Usage:
    read board <n>     — read a bulletin board post
    read <item>        — read a written item (inventory or room)
"""

from commands.base import Command
from models import Item
from commands.bulletinboard import BulletinBoard, _get_board_or_error, _format_age


class ReadCommand(Command):
    def execute(self, character, conn, args: list[str], session) -> None:

        if not args:
            session.send("  Read what? (e.g. read board 3  or  read parchment)\n")
            return

        # ── BULLETIN BOARD ────────────────────────────────────────────────
        if args[0].lower() == "board":
            if len(args) < 2:
                session.send("  Which post? Usage: read board <number>\n")
                return

            try:
                post_number = int(args[1])
            except ValueError:
                session.send("  That's not a valid post number.\n")
                return

            board = _get_board_or_error(character, conn, session)
            if not board:
                return

            board_id, board_name, _ = board

            post = BulletinBoard.get_post_by_number(conn, board_id, post_number)
            if not post:
                session.send(f"  There is no post #{post_number} on {board_name}.\n")
                return

            post_id, author_id, author_name, subject, body, created_at = post
            age = _format_age(created_at)

            lines = [
                f"\n  {board_name} — Post #{post_number}",
                f"  Subject : {subject}",
                f"  Author  : {author_name}",
                f"  Posted  : {age}",
                "  " + "-" * 40,
                body,
                "",
            ]
            session.send("\n".join(lines) + "\n")
            return

        # ── WRITTEN ITEM ──────────────────────────────────────────────────
        target_name = " ".join(args).lower()

        # Search inventory first, then room
        target = None

        inventory = Item.get_inventory(conn, character.id)
        for item in inventory:
            if target_name in item.name.lower():
                target = item
                break

        if target is None:
            room = character.get_room(conn)
            room_items = room.get_items(conn) if room else []
            for item in room_items:
                if target_name in item.name.lower():
                    target = item
                    break

        if target is None:
            session.send(f"  You don't see '{target_name}' here.\n")
            return

        with conn.cursor() as cur:
            cur.execute(
                "SELECT content FROM written_items WHERE item_instance_id = %s",
                (target.instance_id,),
            )
            row = cur.fetchone()

        if not row:
            session.send("  There is nothing written on it.\n")
            return

        content = row[0]
        session.send(f"\n  -- {target.name} --\n\n")
        for line in content.split("\n"):
            session.send(f"  {line}\n")
        session.send("\n")
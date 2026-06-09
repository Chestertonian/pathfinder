"""
commands/scribe.py — ScribeCommand

Usage:
    scribe <parchment>

Opens a multi-line editor to write on a blank piece of parchment.
Finish with @ on its own line. Cannot overwrite existing text.
"""

from commands.base import Command
from models import Item


class ScribeCommand(Command):
    def execute(self, character, conn, args: list[str], session) -> str:

        if not args:
            return "Scribe what? Usage: scribe <item>\n"

        target_name = " ".join(args).lower()

        # ── Find parchment in inventory ───────────────────────────────────
        inventory = Item.get_inventory(conn, character.id)
        target = None
        for item in inventory:
            if target_name in item.name.lower():
                target = item
                break

        if target is None:
            return f"  You don't have '{target_name}' in your inventory.\n"

        # ── Check it's actually parchment (template ID 20) ────────────────
        if target.template_id != 20:
            return "  You can only scribe on parchment.\n"

        # ── Check it hasn't already been written on ───────────────────────
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM written_items WHERE item_instance_id = %s",
                (target.instance_id,),
            )
            if cur.fetchone():
                return "  That parchment has already been written on.\n"

        # ── Open the editor ───────────────────────────────────────────────
        session.send("  Write your message. Enter @ on its own line when finished.\n")
        session.send("  (Leave blank and enter @ to cancel.)\n\n")

        lines = []
        while True:
            line = session.recv().rstrip("\r\n")
            if line.strip() == "@":
                break
            lines.append(line)

        content = "\n".join(lines).strip()

        if not content:
            return "Nothing written. The parchment remains blank.\n"

        # ── Save to written_items ─────────────────────────────────────────
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO written_items (item_instance_id, author_character_id, content)
                VALUES (%s, %s, %s)
                """,
                (target.instance_id, character.id, content),
            )
        conn.commit()

        return "You carefully scribe your words onto the parchment.\n"
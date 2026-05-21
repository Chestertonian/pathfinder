"""
commands/items.py — GetCommand, DropCommand, InventoryCommand

Ownership model:
    item in a room    → owner_type='location', owner_id=location_id
    item in inventory → owner_type='character', owner_id=character_id

All three commands emit room events so nearby players see what's happening.
"""

from events import emit_event
from output import console, print_info, rule, blank, COLOR_STAT, COLOR_INFO, COLOR_FLAVOR


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

class GetCommand:
    def execute(self, character, conn, args):
        if not args:
            return "Get what?"

        search = " ".join(args).lower()

        with conn.cursor() as cur:
            # Find the first matching item on the ground in this room
            cur.execute(
                """
                SELECT ii.id, it.name, it.is_takeable
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'location'
                  AND ii.owner_id   = %s
                  AND LOWER(it.name) LIKE %s
                ORDER BY ii.id ASC
                LIMIT 1
                """,
                (character.location_id, f"%{search}%"),
            )
            row = cur.fetchone()

            if row is None:
                return "You don't see that here."

            instance_id, item_name, is_takeable = row

            if not is_takeable:
                return "You can't get that."

            # Transfer ownership to the character
            cur.execute(
                """
                UPDATE item_instances
                SET owner_type = 'character',
                    owner_id   = %s
                WHERE id = %s
                """,
                (character.id, instance_id),
            )

        conn.commit()

        # Room event — others see it
        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name} picks up {item_name}.",
            color="grey54",
            use_border=False,
        )

        # Personal confirmation
        print_info(f"You pick up {item_name}.")

        return None


# ---------------------------------------------------------------------------
# drop
# ---------------------------------------------------------------------------

class DropCommand:
    def execute(self, character, conn, args):
        if not args:
            return "Drop what?"

        search = " ".join(args).lower()

        with conn.cursor() as cur:
            # Find the first matching item in the character's inventory
            cur.execute(
                """
                SELECT ii.id, it.name, it.is_droppable
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'character'
                  AND ii.owner_id   = %s
                  AND LOWER(it.name) LIKE %s
                ORDER BY ii.id ASC
                LIMIT 1
                """,
                (character.id, f"%{search}%"),
            )
            row = cur.fetchone()

            if row is None:
                return "You don't have that."

            instance_id, item_name, is_droppable = row

            if not is_droppable:
                return "You can't drop that."

            # Transfer ownership to the current location
            cur.execute(
                """
                UPDATE item_instances
                SET owner_type = 'location',
                    owner_id   = %s,
                    equipped   = FALSE
                WHERE id = %s
                """,
                (character.location_id, instance_id),
            )

        conn.commit()

        # Room event — others see it
        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name} drops {item_name}.",
            color="grey54",
            use_border=False,
        )

        # Personal confirmation
        print_info(f"You drop {item_name}.")

        return None


# ---------------------------------------------------------------------------
# inventory
# ---------------------------------------------------------------------------

class InventoryCommand:
    def execute(self, character, conn, args):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT it.name, it.type, it.weight, ii.equipped
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'character'
                  AND ii.owner_id   = %s
                ORDER BY it.type ASC, it.name ASC
                """,
                (character.id,),
            )
            rows = cur.fetchall()

        rule("Inventory")
        blank()

        if not rows:
            print_info("You are carrying nothing.")
        else:
            for name, item_type, weight, equipped in rows:
                console.print(f"  {name:<30}", style=COLOR_STAT, end="")
                console.print(f"{item_type:<12}", style=COLOR_INFO, end="")
                console.print(f"{weight} lb", style="grey54", end="")
                if equipped:
                    console.print("  [equipped]", style="bold green4", end="")
                console.print()

        blank()
        rule()

        return None
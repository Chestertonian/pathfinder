"""
commands/promote.py — PromoteCommand / DemoteCommand (staff only)

Usage:
    promote <character> <title name>
    demote <character>

Assigns or removes a title from a character.
Emits a flashy global announcement on promote.
Demote is quieter — just a system notification.
"""

from events import emit_event


def _get_title_by_name(conn, title_name: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, guild FROM titles WHERE LOWER(name) = LOWER(%s)",
            (title_name,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "guild": row[2]}


def _get_character_by_name(conn, name: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, class, title_id
            FROM characters
            WHERE LOWER(name) = LOWER(%s)
            """,
            (name,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {
        "id":       row[0],
        "name":     row[1],
        "class":    row[2],
        "title_id": row[3],
    }


def _build_announcement(character_name: str, title_name: str) -> str:
    """
    Build a centered, bordered announcement message.
    """
    width = 46
    border = "=" * width

    name_line    = character_name.center(width)
    title_line   = f"has been named {title_name}".center(width)

    return "\n".join([
        border,
        name_line,
        title_line,
        border,
    ])


class PromoteCommand:
    def execute(self, character, conn, args, session):
        if not character.is_staff:
            return "You don't have permission to do that."

        if len(args) < 2:
            return "Usage: promote <character> <title name>"

        # First arg is character name, rest is title name
        target_name = args[0]
        title_name  = " ".join(args[1:])

        target = _get_character_by_name(conn, target_name)
        if target is None:
            return f"No character named '{target_name}' exists."

        title = _get_title_by_name(conn, title_name)
        if title is None:
            return f"No title named '{title_name}' exists."

        # Assign title
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE characters SET title_id = %s WHERE id = %s",
                (title["id"], target["id"]),
            )
        conn.commit()

        # Flashy global announcement
        announcement = _build_announcement(
            target["name"].capitalize(),
            title["name"],
        )

        emit_event(
            conn,
            event_type="global",
            sender_id=character.id,
            message=announcement,
            color="bright_yellow",
            use_border=False,  # border is built into the message itself
        )

        return f"{target['name'].capitalize()} has been named {title['name']}."


class DemoteCommand:
    def execute(self, character, conn, args, session):
        if not character.is_staff:
            return "You don't have permission to do that."

        if not args:
            return "Demote whom?"

        target_name = args[0]

        target = _get_character_by_name(conn, target_name)
        if target is None:
            return f"No character named '{target_name}' exists."

        if target["title_id"] is None:
            return f"{target['name'].capitalize()} holds no title."

        # Remove title
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE characters SET title_id = NULL WHERE id = %s",
                (target["id"],),
            )
        conn.commit()

        # Quiet system notification to the world
        emit_event(
            conn,
            event_type="global",
            sender_id=character.id,
            message=f"{target['name'].capitalize()} has been relieved of their title.",
            color="bright_yellow",
            use_border=False,
        )

        return f"{target['name'].capitalize()} has been demoted."
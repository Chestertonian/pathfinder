class FindCommand:
    def execute(self, character, conn, args, session):
        if not character.is_staff:
            return "You don't have permission to do that."
        if not args:
            return "Find what?"
        search = " ".join(args).lower()
        with conn.cursor() as cur:
            # Check NPCs
            cur.execute(
                """
                SELECT nt.name, l.name, l.id
                FROM npc_instances ni
                JOIN npc_templates nt ON nt.id = ni.npc_template_id
                JOIN locations l ON l.id = ni.location_id
                WHERE LOWER(nt.name) LIKE %s AND ni.is_alive = TRUE
                """,
                (f"%{search}%",),
            )
            npc_rows = cur.fetchall()

            # Check items
            cur.execute(
                """
                SELECT it.name, l.name, l.id
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                JOIN locations l ON l.id = ii.owner_id
                WHERE ii.owner_type = 'location'
                  AND LOWER(it.name) LIKE %s
                """,
                (f"%{search}%",),
            )
            item_rows = cur.fetchall()

        lines = []
        if npc_rows:
            lines.append("NPCs:")
            for name, loc_name, loc_id in npc_rows:
                lines.append(f"  {name} — {loc_name} (id {loc_id})")
        if item_rows:
            lines.append("Items:")
            for name, loc_name, loc_id in item_rows:
                lines.append(f"  {name} — {loc_name} (id {loc_id})")
        if not lines:
            return f"Nothing matching '{search}' found."

        return "\n".join(lines)
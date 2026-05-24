class GotoCommand:
    def execute(self, character, conn, args, session):
        if not character.is_staff:
            return "You don't have permission to do that."
        if not args or not args[0].isdigit():
            return "Usage: goto <location_id>"
        location_id = int(args[0])
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM locations WHERE id = %s", (location_id,))
            if cur.fetchone() is None:
                return f"Location {location_id} doesn't exist."
            cur.execute(
                "UPDATE characters SET location_id = %s WHERE id = %s",
                (location_id, character.id)
            )
        conn.commit()
        return f"Teleported to location {location_id}."
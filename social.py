# social.py
# Helpers for social visibility (introductions, name display)

GENDER_PREFIX = {
    0: "",        # unknown/neutral
    1: "Male",
    2: "Female",
}

def visible_name(viewer_id: int, target, conn) -> str:
    """
    Returns the target's real name if the viewer has been introduced,
    otherwise returns a generic description like "Male human".
    """

    target_id = _get_attr(target, "id")
    target_name = _get_attr(target, "name")
    target_gender = _get_attr(target, "gender")
    target_race = _get_attr(target, "race")

    if viewer_id == target_id:
        return target_name

    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM character_introductions
            WHERE character_id = %s AND known_character_id = %s
        """, (viewer_id, target_id))
        if cur.fetchone():
            return target_name

    prefix = GENDER_PREFIX.get(target_gender, "")
    race = (target_race or "").capitalize()

    return f"{prefix} {race}".strip()

def already_introduced(viewer_id: int, target_id: int, conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM character_introductions
            WHERE character_id = %s AND known_character_id = %s
        """, (viewer_id, target_id))
        return cur.fetchone() is not None
    
def _get_attr(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
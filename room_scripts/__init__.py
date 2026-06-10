# room_scripts/__init__.py

from room_scripts import merchant_guild
from justice.constants import OFFICE_ROOM_ID, JAIL_ROOM_ID, COURT_ROOM_ID, GALLOWS_ROOM_ID
import room_scripts.justice_office as justice_office
import room_scripts.justice_move   as justice_move
import room_scripts.gallows as justice_gallows

class _GallowsCombined:
    REGISTRY = {**justice_move.REGISTRY, **justice_gallows.REGISTRY}

gallows_combined = _GallowsCombined()

REGISTRY = {
    "merchant_guild":  merchant_guild,
    "justice_office":  justice_office,
    "prison_move":    justice_move,
    "court_move":   justice_move,
    "gallows": gallows_combined,
}

def get_script(key):
    if key is None:
        return None
    return REGISTRY.get(key)

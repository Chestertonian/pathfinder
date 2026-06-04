# room_scripts/__init__.py

from room_scripts import merchant_guild

REGISTRY = {
    "merchant_guild":  merchant_guild,
}

def get_script(key):
    if key is None:
        return None
    return REGISTRY.get(key)

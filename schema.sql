-- =============================================================
-- WORLD SYSTEM
-- =============================================================

-- Stores all physical locations in the world (rooms, zones, areas)
CREATE TABLE locations (
    id          SERIAL PRIMARY KEY,          -- Unique location ID
    name        TEXT NOT NULL,               -- Display name of location
    description TEXT NOT NULL,               -- Full narrative description

    region      TEXT,                        -- Optional grouping region (e.g. "Northlands")

    is_safe     BOOLEAN NOT NULL DEFAULT FALSE,        -- No combat allowed
    is_settlement BOOLEAN NOT NULL DEFAULT FALSE,      -- Town/city flag
    is_outdoor  BOOLEAN NOT NULL DEFAULT TRUE,         -- Indoor vs outdoor

    brightness  INTEGER NOT NULL DEFAULT 0,            -- Lighting level (affects visibility)
    smell       TEXT DEFAULT '',                       -- Ambient smell description
    sound       TEXT DEFAULT '',                       -- Ambient sound description
    search      TEXT DEFAULT '',                       -- Hidden clue / searchable text

    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP  -- Creation timestamp
);

-- Defines movement connections between locations
CREATE TABLE exits (
    id              SERIAL PRIMARY KEY,          -- Exit ID

    from_location   INTEGER NOT NULL REFERENCES locations(id),  -- Origin location
    to_location     INTEGER NOT NULL REFERENCES locations(id),   -- Destination location

    direction       TEXT NOT NULL,               -- Direction keyword (north, south, etc.)
    cost            INTEGER NOT NULL DEFAULT 1,   -- Movement cost (stamina/time/etc.)

    is_secret       BOOLEAN NOT NULL DEFAULT FALSE,  -- Hidden exit
    is_locked       BOOLEAN NOT NULL DEFAULT FALSE,  -- Requires key or condition
    key_template_id INTEGER DEFAULT NULL,            -- Item that unlocks exit

    description     TEXT DEFAULT '',             -- Flavor text

    CONSTRAINT exits_unique_direction UNIQUE (from_location, direction)
);

-- =============================================================
-- CHARACTER SYSTEM
-- =============================================================

-- Player characters
CREATE TABLE characters (
    id              SERIAL PRIMARY KEY,        -- Character ID
    name            TEXT NOT NULL UNIQUE,      -- Username / character name
    password_hash   TEXT NOT NULL,             -- Authentication hash
    class           TEXT NOT NULL,             -- Character class (warrior, mage, etc.)

    level           INTEGER NOT NULL DEFAULT 1, -- Progression level
    xp              INTEGER NOT NULL DEFAULT 0, -- Experience points

    location_id     INTEGER NOT NULL REFERENCES locations(id), -- Current location
    is_staff        BOOLEAN NOT NULL DEFAULT FALSE,            -- Admin flag

    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Core stats
    strength        INTEGER NOT NULL DEFAULT 10,
    dexterity       INTEGER NOT NULL DEFAULT 10,
    constitution    INTEGER NOT NULL DEFAULT 10,
    intelligence    INTEGER NOT NULL DEFAULT 10,
    wisdom          INTEGER NOT NULL DEFAULT 10,
    charisma        INTEGER NOT NULL DEFAULT 10,

    -- Resource stats
    hp              INTEGER NOT NULL DEFAULT 25,
    hp_max          INTEGER NOT NULL DEFAULT 25,
    power           INTEGER NOT NULL DEFAULT 25,
    power_max       INTEGER NOT NULL DEFAULT 25,
    endurance       INTEGER NOT NULL DEFAULT 100,
    endurance_max   INTEGER NOT NULL DEFAULT 100,

    gold            INTEGER NOT NULL DEFAULT 0 -- Currency
);

-- =============================================================
-- ITEM SYSTEM
-- =============================================================

-- Base definition for all items
CREATE TABLE item_templates (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,            -- Item name
    type        TEXT NOT NULL,            -- weapon, armor, food, misc
    description TEXT NOT NULL,            -- Flavor text

    weight      INTEGER NOT NULL DEFAULT 1,  -- Inventory weight
    value       INTEGER NOT NULL DEFAULT 0,  -- Shop value

    is_takeable BOOLEAN NOT NULL DEFAULT TRUE,   -- Can be picked up
    is_droppable BOOLEAN NOT NULL DEFAULT TRUE,   -- Can be dropped

    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Weapon-specific stats (1:1 with item_templates)
CREATE TABLE weapon_templates (
    id                  SERIAL PRIMARY KEY,
    item_template_id    INTEGER NOT NULL UNIQUE REFERENCES item_templates(id),

    damage_min          INTEGER NOT NULL DEFAULT 1, -- Minimum damage
    damage_max          INTEGER NOT NULL DEFAULT 4, -- Maximum damage

    damage_type         INTEGER NOT NULL DEFAULT 1, -- 1=pierce, 2=slash, 3=blunt, 4=magic
    speed               REAL NOT NULL DEFAULT 2.0,   -- Attack delay in seconds

    weapon_type         TEXT NOT NULL DEFAULT 'melee' -- melee/ranged/etc.
);

-- Armor-specific stats
CREATE TABLE armor_templates (
    id                  SERIAL PRIMARY KEY,
    item_template_id    INTEGER NOT NULL UNIQUE REFERENCES item_templates(id),

    defense             INTEGER NOT NULL DEFAULT 0,  -- Damage reduction
    slot                TEXT NOT NULL                 -- head/chest/legs/etc.
);

-- Food healing effects
CREATE TABLE food_templates (
    id                  SERIAL PRIMARY KEY,
    item_template_id    INTEGER NOT NULL UNIQUE REFERENCES item_templates(id),

    endurance_restore   INTEGER NOT NULL DEFAULT 0,
    power_restore       INTEGER NOT NULL DEFAULT 0,
    hp_restore          INTEGER NOT NULL DEFAULT 0
);

-- Light source items (torches, lanterns, etc.)
CREATE TABLE light_templates (
    id                  SERIAL PRIMARY KEY,
    item_template_id    INTEGER NOT NULL UNIQUE REFERENCES item_templates(id),

    light_gain          INTEGER NOT NULL DEFAULT 0,  -- Light radius/brightness
    burn_time           INTEGER NOT NULL DEFAULT 100 -- Duration in seconds
);

-- Physical instances of items in the world
CREATE TABLE item_instances (
    id                  SERIAL PRIMARY KEY,

    item_template_id    INTEGER NOT NULL
        REFERENCES item_templates(id)
        ON DELETE RESTRICT,

    -- Ownership system (single flexible model)
    owner_type          TEXT NOT NULL,
    owner_id            INTEGER NOT NULL,

    equipped            BOOLEAN NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Prevent invalid ownership types
    CONSTRAINT valid_owner_type CHECK (
        owner_type IN ('character', 'location', 'npc', 'container')
    )
);

-- =============================================================
-- NPC SYSTEM
-- =============================================================

-- NPC base definitions (shared template)
CREATE TABLE npc_templates (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL,

    gender          INTEGER DEFAULT 0, -- 0=unknown, 1=male, 2=female
    xp              INTEGER DEFAULT 0,  -- XP reward

    -- Combat stats
    hp_max          INTEGER NOT NULL DEFAULT 10,
    damage_min      INTEGER NOT NULL DEFAULT 1,
    damage_max      INTEGER NOT NULL DEFAULT 4,
    attack_speed    REAL NOT NULL DEFAULT 2.0,
    defense         INTEGER NOT NULL DEFAULT 0,

    -- Behavior flags
    is_hostile      BOOLEAN NOT NULL DEFAULT FALSE,
    is_merchant     BOOLEAN NOT NULL DEFAULT FALSE
);

-- Actual NPCs in the world
CREATE TABLE npc_instances (
    id              SERIAL PRIMARY KEY,
    npc_template_id INTEGER NOT NULL REFERENCES npc_templates(id),

    location_id     INTEGER NOT NULL REFERENCES locations(id),

    hp              INTEGER NOT NULL,     -- Current HP
    is_alive        BOOLEAN NOT NULL DEFAULT TRUE,

    home_room_id    INTEGER REFERENCES locations(id), -- Respawn/home location

    is_aggro_to_player INTEGER NOT NULL DEFAULT 0,
    aggro_since     TIMESTAMPTZ DEFAULT NULL,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================
-- DIALOGUE SYSTEM
-- =============================================================

CREATE TABLE dialogue (
    id              SERIAL PRIMARY KEY,
    npc_template_id INTEGER NOT NULL REFERENCES npc_templates(id),

    topic           TEXT NOT NULL,   -- Keyword/topic (ask target about thing)
    response        TEXT NOT NULL    -- NPC response text
);

-- =============================================================
-- LOOT SYSTEM
-- =============================================================

CREATE TABLE loot_tables (
    id              SERIAL PRIMARY KEY,
    npc_template_id INTEGER NOT NULL REFERENCES npc_templates(id),

    item_template_id INTEGER NOT NULL REFERENCES item_templates(id),

    drop_chance     REAL NOT NULL DEFAULT 1.0, -- 0.0–1.0 probability
    quantity_min    INTEGER NOT NULL DEFAULT 1,
    quantity_max    INTEGER NOT NULL DEFAULT 1
);

-- =============================================================
-- ECONOMY SYSTEM
-- =============================================================

-- Shop inventories tied to NPCs or locations
CREATE TABLE shop_inventories (
    id              SERIAL PRIMARY KEY,

    location_id     INTEGER REFERENCES locations(id),
    npc_instance_id INTEGER REFERENCES npc_instances(id),

    item_template_id INTEGER NOT NULL REFERENCES item_templates(id),

    price           INTEGER NOT NULL, -- Buy price
    stock           INTEGER,          -- NULL = infinite stock

    CHECK (
    location_id IS NOT NULL OR npc_instance_id IS NOT NULL
    )
);

-- =============================================================
-- QUEST SYSTEM
-- =============================================================

CREATE TABLE quests (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,

    reward_gold INTEGER NOT NULL DEFAULT 0,
    reward_xp   INTEGER NOT NULL DEFAULT 0,

    giver_npc_template_id INTEGER REFERENCES npc_templates(id)
);

-- Quest objectives (supports multiple objective types)
CREATE TABLE quest_objectives (
    id              SERIAL PRIMARY KEY,
    quest_id        INTEGER NOT NULL REFERENCES quests(id),

    type            TEXT NOT NULL,          -- kill, deliver, reach
    target_type     TEXT NOT NULL,          -- npc/item/location
    target_id       INTEGER NOT NULL,       -- ID of target

    quantity        INTEGER NOT NULL DEFAULT 1,
    description     TEXT NOT NULL
);

-- Active quests per player
CREATE TABLE character_quests (
    id              SERIAL PRIMARY KEY,
    character_id    INTEGER NOT NULL REFERENCES characters(id),
    quest_id        INTEGER NOT NULL REFERENCES quests(id),

    status          TEXT NOT NULL DEFAULT 'active', -- active/complete/failed
    UNIQUE(quest_id, character_id)
);

-- Progress tracking per objective
CREATE TABLE character_objective_progress (
    id                  SERIAL PRIMARY KEY,
    character_id        INTEGER NOT NULL REFERENCES characters(id),
    quest_objective_id  INTEGER NOT NULL REFERENCES quest_objectives(id),

    quantity_current    INTEGER NOT NULL DEFAULT 0
);

-- =============================================================
-- FACTION SYSTEM
-- =============================================================

CREATE TABLE factions (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL
);

-- Player reputation with factions
CREATE TABLE faction_reputation (
    id              SERIAL PRIMARY KEY,
    character_id    INTEGER NOT NULL REFERENCES characters(id),
    faction_id      INTEGER NOT NULL REFERENCES factions(id),

    score           INTEGER NOT NULL DEFAULT 0,
    UNIQUE(character_id, faction_id)
);

-- NPC faction membership
CREATE TABLE faction_membership (
    id              SERIAL PRIMARY KEY,
    npc_template_id INTEGER NOT NULL REFERENCES npc_templates(id),
    faction_id      INTEGER NOT NULL REFERENCES factions(id)
);

-- Relationships between factions
CREATE TABLE faction_relationships (
    id              SERIAL PRIMARY KEY,
    faction_id      INTEGER NOT NULL REFERENCES factions(id),
    target_faction_id INTEGER NOT NULL REFERENCES factions(id),

    disposition     INTEGER NOT NULL DEFAULT 0, -- -10 hostile, +10 friendly

    CONSTRAINT faction_relationship_unique UNIQUE (faction_id, target_faction_id)
);

-- =============================================================
-- WORLD EVENTS
-- =============================================================

CREATE TABLE events (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

-- =============================================================
-- AUDIT LOG
-- =============================================================

CREATE TABLE audit_log (
    id              SERIAL PRIMARY KEY,
    character_id    INTEGER REFERENCES characters(id),

    action          TEXT NOT NULL,   -- 'move', 'attack', 'loot', 'trade', 'quest_update', etc.
    entity_type     TEXT,            -- 'character', 'item', 'npc', 'quest'
    entity_id       INTEGER,

    location_id     INTEGER REFERENCES locations(id),

    details         JSONB,           -- flexible payload (VERY important)

    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
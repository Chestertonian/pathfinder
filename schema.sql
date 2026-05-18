-- =============================================================
-- WORLD
-- =============================================================

CREATE TABLE locations (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    region      TEXT,
    is_safe     BOOLEAN NOT NULL DEFAULT FALSE,
    is_settlement BOOLEAN NOT NULL DEFAULT FALSE,
    is_outdoor  BOOLEAN NOT NULL DEFAULT TRUE,
    brightness  INTEGER NOT NULL DEFAULT 0,
    smell       TEXT DEFAULT '',
    sound       TEXT DEFAULT '',
    search      TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
);

CREATE TABLE exits (
    id              SERIAL PRIMARY KEY,
    from_location   INTEGER NOT NULL REFERENCES locations(id),
    direction       TEXT NOT NULL,
    cost            INTEGER NOT NULL DEFAULT 1,
    to_location     INTEGER NOT NULL REFERENCES locations(id)
    is_secret       BOOLEAN NOT NULL DEFAULT FALSE,
    is_locked       BOOLEAN NOT NULL DEFAULT FALSE,
    key_template_id INTEGER DEFAULT NULL, -- What unlocks the door, if it's locked?
    description TEXT DEFAULT '',
);

-- =============================================================
-- CHARACTERS
-- =============================================================

CREATE TABLE characters (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    class           TEXT NOT NULL,
    level           INTEGER NOT NULL DEFAULT 1,
    xp              INTEGER NOT NULL DEFAULT 0,
    location_id     INTEGER NOT NULL REFERENCES locations(id),
    is_staff        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Core stats
    strength        INTEGER NOT NULL DEFAULT 10,
    dexterity       INTEGER NOT NULL DEFAULT 10,
    constitution    INTEGER NOT NULL DEFAULT 10,
    intelligence    INTEGER NOT NULL DEFAULT 10,
    wisdom          INTEGER NOT NULL DEFAULT 10,
    charisma        INTEGER NOT NULL DEFAULT 10,

    -- Derived / resource stats
    hp              INTEGER NOT NULL DEFAULT 25,
    hp_max          INTEGER NOT NULL DEFAULT 25,
    power           INTEGER NOT NULL DEFAULT 25,
    power_max       INTEGER NOT NULL DEFAULT 25,
    endurance       INTEGER NOT NULL DEFAULT 100,
    endurance_max   INTEGER NOT NULL DEFAULT 100,
    gold            INTEGER NOT NULL DEFAULT 0,
);

-- =============================================================
-- ITEMS
-- =============================================================

CREATE TABLE item_templates (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL, -- 'weapon', 'armor', 'food', 'misc'
    description TEXT NOT NULL,
    
    weight      INTEGER NOT NULL DEFAULT 1,
    value       INTEGER NOT NULL DEFAULT 0,

    is_takeable BOOLEAN NOT NULL DEFAULT TRUE, 
    is_droppable BOOLEAN NOT NULL DEFAULT TRUE,

    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
);

CREATE TABLE weapon_templates (
    id                  SERIAL PRIMARY KEY,
    item_template_id    INTEGER NOT NULL REFERENCES item_templates(id),
    damage_min          INTEGER NOT NULL DEFAULT 1,
    damage_max          INTEGER NOT NULL DEFAULT 4,
    damage_type         INTEGER NOT NULL DEFAULT 1, -- 1 = pierce, 2 = slash, 3 = bludgeon, 4 = magic?
    speed               REAL NOT NULL DEFAULT 2.0  -- seconds between attacks, we'll see if we use it
    weapon_type         TEXT NOT NULL DEFAULT 'melee',
);

CREATE TABLE armor_templates (
    id                  SERIAL PRIMARY KEY,
    item_template_id    INTEGER NOT NULL REFERENCES item_templates(id),
    defense             INTEGER NOT NULL DEFAULT 0,
    slot                TEXT NOT NULL  -- 'head', 'chest', 'legs', 'hands', 'feet'
);

CREATE TABLE food_templates (
    id                  SERIAL PRIMARY KEY,
    item_template_id    INTEGER NOT NULL REFERENCES item_templates(id),
    endurance_restore   INTEGER NOT NULL DEFAULT 0,
    power_restore       INTEGER NOT NULL DEFAULT 0,
    hp_restore          INTEGER NOT NULL DEFAULT 0,
);

CREATE TABLE light_templates (
    id                  SERIAL PRIMARY KEY,
    item_template_id    INTEGER NOT NULL REFERENCES item_templates(id),
    light_gain          INTEGER NOT NULL DEFAULT 0,
    burn_time           INTEGER NOT NULL DEFAULT 100,
);

CREATE TABLE item_instances (
    id                  SERIAL PRIMARY KEY,
    item_template_id    INTEGER NOT NULL REFERENCES item_templates(id),

    -- Owned by exactly one of these, others must be NULL
    character_id        INTEGER REFERENCES characters(id),
    location_id         INTEGER REFERENCES locations(id),
    npc_instance_id     INTEGER, -- FK added after npc_instances is created

    equipped            BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT one_owner CHECK (
        (
            (character_id IS NOT NULL)::INTEGER +
            (location_id IS NOT NULL)::INTEGER +
            (npc_instance_id IS NOT NULL)::INTEGER
        ) = 1
    )
);

-- =============================================================
-- NPCS
-- =============================================================

CREATE TABLE npc_templates (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL,
    gender          INTEGER DEFAULT 0, -- 1=male, 2=female.
    xp              INTEGER DEFAULT 0,

    -- Combat stats
    hp_max          INTEGER NOT NULL DEFAULT 10,
    damage_min      INTEGER NOT NULL DEFAULT 1,
    damage_max      INTEGER NOT NULL DEFAULT 4,
    attack_speed    REAL NOT NULL DEFAULT 2.0,
    defense         INTEGER NOT NULL DEFAULT 0,

    -- Behavior
    is_hostile      BOOLEAN NOT NULL DEFAULT FALSE,
    is_merchant     BOOLEAN NOT NULL DEFAULT FALSE, -- add more later
);

CREATE TABLE npc_instances (
    id              SERIAL PRIMARY KEY,
    npc_template_id INTEGER NOT NULL REFERENCES npc_templates(id),
    location_id     INTEGER NOT NULL REFERENCES locations(id),
    hp              INTEGER NOT NULL,
    is_alive        BOOLEAN NOT NULL DEFAULT TRUE,
    home_room_id    INTEGER,
    is_aggro_to_player INTEGER NOT NULL DEFAULT 0, 
    aggro_since     REAL DEFAULT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
);

-- Now that npc_instances exists, add the FK on item_instances
ALTER TABLE item_instances
    ADD CONSTRAINT fk_item_npc
    FOREIGN KEY (npc_instance_id) REFERENCES npc_instances(id);

-- =============================================================
-- DIALOGUE
-- =============================================================

CREATE TABLE dialogue (
    id              SERIAL PRIMARY KEY,
    npc_template_id INTEGER NOT NULL REFERENCES npc_templates(id),
    topic           TEXT NOT NULL,
    response        TEXT NOT NULL
);

-- =============================================================
-- LOOT
-- =============================================================

CREATE TABLE loot_tables (
    id              SERIAL PRIMARY KEY,
    npc_template_id INTEGER NOT NULL REFERENCES npc_templates(id),
    item_template_id INTEGER NOT NULL REFERENCES item_templates(id),
    drop_chance     REAL NOT NULL DEFAULT 1.0,  -- 0.0 to 1.0
    quantity_min    INTEGER NOT NULL DEFAULT 1,
    quantity_max    INTEGER NOT NULL DEFAULT 1
);

-- =============================================================
-- ECONOMY
-- =============================================================

CREATE TABLE shop_inventories (
    id              SERIAL PRIMARY KEY,
    location_id     INTEGER REFERENCES locations(id),
    npc_instance_id INTEGER REFERENCES npc_instances(id),
    item_template_id INTEGER NOT NULL REFERENCES item_templates(id),
    price           INTEGER NOT NULL,
    stock           INTEGER  -- NULL = unlimited
);

-- =============================================================
-- QUESTS
-- =============================================================

CREATE TABLE quests (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    reward_gold INTEGER NOT NULL DEFAULT 0,
    reward_xp   INTEGER NOT NULL DEFAULT 0,
    giver_npc_template_id INTEGER REFERENCES npc_templates(id)
);

CREATE TABLE quest_objectives (
    id              SERIAL PRIMARY KEY,
    quest_id        INTEGER NOT NULL REFERENCES quests(id),
    type            TEXT NOT NULL,  -- 'kill', 'deliver', 'reach'
    target_id       INTEGER,        -- npc_template_id, item_template_id, or location_id depending on type
    quantity        INTEGER NOT NULL DEFAULT 1,
    description     TEXT NOT NULL
);

CREATE TABLE character_quests (
    id              SERIAL PRIMARY KEY,
    character_id    INTEGER NOT NULL REFERENCES characters(id),
    quest_id        INTEGER NOT NULL REFERENCES quests(id),
    status          TEXT NOT NULL DEFAULT 'active'  -- 'active', 'complete', 'failed'
);

CREATE TABLE character_objective_progress (
    id                  SERIAL PRIMARY KEY,
    character_id        INTEGER NOT NULL REFERENCES characters(id),
    quest_objective_id  INTEGER NOT NULL REFERENCES quest_objectives(id),
    quantity_current    INTEGER NOT NULL DEFAULT 0
);

-- =============================================================
-- FACTIONS
-- =============================================================

CREATE TABLE factions (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE faction_reputation (
    id              SERIAL PRIMARY KEY,
    character_id    INTEGER NOT NULL REFERENCES characters(id),
    faction_id      INTEGER NOT NULL REFERENCES factions(id),
    score           INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE faction_membership (
    id              SERIAL PRIMARY KEY,
    npc_template_id INTEGER NOT NULL REFERENCES npc_templates(id),
    faction_id      INTEGER NOT NULL REFERENCES factions(id)
);

CREATE TABLE faction_relationships (
    id              SERIAL PRIMARY KEY,
    faction_id      INTEGER NOT NULL REFERENCES factions(id),
    target_faction_id INTEGER NOT NULL REFERENCES factions(id),
    disposition     INTEGER NOT NULL DEFAULT 0  -- negative = hostile, positive = friendly
);

-- =============================================================
-- EVENTS
-- =============================================================

CREATE TABLE events (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

# Pathfinder MUD — Schema Reference

---

## World

### `locations`
The world graph nodes. Every room, zone, and area is a row here.

| Column | Type | Notes |
|---|---|---|
| id | int | PK |
| name | text | Display name |
| description | text | Narrative text shown to player |
| region | text | Optional grouping label (e.g. "Northlands") |
| is_safe | bool | No combat allowed |
| is_settlement | bool | Respawn point, service hub |
| is_outdoor | bool | Indoor/outdoor flag |
| brightness | int | Lighting level |
| smell / sound / search | text | Ambient flavor + hidden search text |

### `exits`
Directed edges between locations. Forms the movement graph.

| Column | Type | Notes |
|---|---|---|
| id | int | PK |
| from_location | int | FK → locations |
| to_location | int | FK → locations |
| direction | text | "north", "south", etc. |
| cost | int | EP cost to traverse |
| is_secret | bool | Hidden from normal look |
| is_locked | bool | Requires key |
| key_template_id | int | FK → item_templates (nullable) |
| description | text | Flavor text |

**Constraint:** `(from_location, direction)` is unique — one exit per direction per room.

---

## Characters

### `characters`
One row per player character. Also the login identity.

| Column | Type | Notes |
|---|---|---|
| id | int | PK |
| name | text | Unique login name |
| password_hash | text | Auth |
| class | text | Fighter / Rogue / Wizard / Cleric / Ranger |
| level | int | |
| xp | int | |
| location_id | int | FK → locations |
| is_staff | bool | Admin flag |
| race | text | Default: human |
| gender | int | 0=unknown, 1=male, 2=female |
| is_logged_in | bool | |
| room_entered_at | timestamptz | Used for timing/events |
| gold | int | Currency |
| **Stats** | | |
| strength / dexterity / constitution / intelligence / wisdom / charisma | int | Default 10 |
| **Resources** | | |
| hp / hp_max | int | Health |
| power / power_max | int | SP (skill points) |
| endurance / endurance_max | int | EP (movement resource) |

---

## Items

### `item_templates`
Blueprint for an item type. Shared reference data.

| Column | Type | Notes |
|---|---|---|
| id | int | PK |
| name | text | |
| type | text | weapon / armor / food / misc |
| description | text | |
| weight | int | |
| value | int | Shop sell value |
| is_takeable / is_droppable | bool | |

### Subtype tables (1:1 with item_templates)

**`weapon_templates`** — damage_min, damage_max, damage_type (1=pierce 2=slash 3=blunt 4=magic), speed (seconds), weapon_type

**`armor_templates`** — defense (flat reduction), slot (head/chest/legs/etc.)

**`food_templates`** — hp_restore, power_restore, endurance_restore

**`light_templates`** — light_gain, burn_time (seconds)

### `item_instances`
A specific physical copy of an item that exists in the world.

| Column | Type | Notes |
|---|---|---|
| id | int | PK |
| item_template_id | int | FK → item_templates |
| owner_type | text | `character` / `location` / `npc` / `container` |
| owner_id | int | ID of the owner (matches owner_type) |
| equipped | bool | Currently worn/wielded |

Items are owned by a type+id pair — no separate foreign keys per owner type.

---

## NPCs

### `npc_templates`
Blueprint for an NPC or monster type.

| Column | Type | Notes |
|---|---|---|
| id | int | PK |
| name / description | text | |
| gender | int | 0/1/2 |
| xp | int | XP reward on kill |
| hp_max | int | |
| damage_min / damage_max | int | |
| attack_speed | real | Seconds between attacks |
| defense | int | Flat damage reduction |
| is_hostile | bool | Attacks on sight |
| is_merchant | bool | Has shop inventory |
| respawn_seconds | int | Time before respawn |

### `npc_instances`
A spawned NPC currently in the world.

| Column | Type | Notes |
|---|---|---|
| id | int | PK |
| npc_template_id | int | FK → npc_templates |
| location_id | int | FK → locations (current) |
| home_room_id | int | FK → locations (respawn target, nullable) |
| hp | int | Current HP |
| is_alive | bool | |
| is_aggro_to_player | int | ID of player being attacked (0 = none) |
| aggro_since | timestamptz | |

### `npc_spawns`
Controls automatic NPC spawning by the regen thread.

| Column | Type | Notes |
|---|---|---|
| npc_template_id | int | FK → npc_templates |
| location_id | int | FK → locations |
| max_count | int | Max alive at this location |
| respawn_seconds | int | Cooldown |
| last_spawned_at | timestamptz | |
| is_active | bool | Enable/disable spawn point |

### `dialogue`
Topic-keyed NPC responses. Used by `ask <npc> about <topic>`.

| Column | Notes |
|---|---|
| npc_template_id | FK → npc_templates |
| topic | Keyword player types |
| response | Text the NPC says |

### `loot_tables`
What items an NPC can drop on death.

| Column | Notes |
|---|---|
| npc_template_id | FK → npc_templates |
| item_template_id | FK → item_templates |
| drop_chance | 0.0–1.0 probability |
| quantity_min / quantity_max | Roll range |

---

## Combat

### `active_combats`
One row per directional attack relationship. Two rows per fight (attacker→defender, defender→attacker).

| Column | Notes |
|---|---|
| attacker_type / defender_type | `character` or `npc` |
| attacker_id / defender_id | ID of combatant |
| location_id | FK → locations |
| started_at | Used for stale combat cleanup (300s timeout) |

---

## Economy

### `shop_inventories`
Items available for purchase. Tied to either a location or an NPC instance.

| Column | Notes |
|---|---|
| location_id | FK → locations (nullable) |
| npc_instance_id | FK → npc_instances (nullable) |
| item_template_id | FK → item_templates |
| price | Buy price in gold |
| stock | NULL = infinite |

**Constraint:** At least one of location_id or npc_instance_id must be set.

---

## Quests

### `quests`
| Column | Notes |
|---|---|
| name / description | |
| reward_gold / reward_xp | |
| giver_npc_template_id | FK → npc_templates (nullable) |

### `quest_objectives`
Sub-goals within a quest.

| Column | Notes |
|---|---|
| quest_id | FK → quests |
| type | `kill` / `deliver` / `reach` |
| target_type | `npc` / `item` / `location` |
| target_id | ID of the target |
| quantity | Required count |

### `character_quests`
Tracks which quests a player has active/completed.

| Column | Notes |
|---|---|
| character_id | FK → characters |
| quest_id | FK → quests |
| status | `active` / `complete` / `failed` |

**Constraint:** `(quest_id, character_id)` unique.

### `character_objective_progress`
Per-objective progress counter per player.

| Column | Notes |
|---|---|
| character_id | FK → characters |
| quest_objective_id | FK → quest_objectives |
| quantity_current | Running count toward goal |

---

## Factions

### `factions` — id, name, description

### `faction_membership` — links npc_template_id → faction_id

### `faction_reputation` — character_id + faction_id → score (unique per pair)

### `faction_relationships` — faction_id + target_faction_id → disposition (-10 hostile, +10 friendly)

---

## Events & Broadcast

### `broadcast_messages`
The event bus. All in-game events (room, combat, tell, global, etc.) are written here and polled by each player's BroadcastPoller thread.

| Column | Notes |
|---|---|
| event_type | `room` / `combat` / `tell` / `channel` / `global` / `system` |
| location_id | Where the event happened |
| sender_character_id | Who triggered it |
| recipient_character_id | Target (for tells) |
| channel | Channel name (for channel events) |
| message | The text |
| color | For rendering |
| use_border | For global announcements |

### `audit_log`
Append-only log of notable actions (move, attack, loot, trade, quest_update, etc.).

| Column | Notes |
|---|---|
| character_id | Who did it |
| action | Verb string |
| entity_type / entity_id | What was acted on |
| location_id | Where |
| details | JSONB — flexible payload |
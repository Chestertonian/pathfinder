## Full Development Checklist

### Phase 1 — Foundation
- [x] Test Neon connection
- [X] Design the full database schema on paper
- [X] Write all `CREATE TABLE` SQL statements
- [X] Run schema against Neon, verify tables exist
- [X] Build a reusable `db.py` connection module
- [X] Write a `seed_world.py` script that inserts a handful of starter locations and exits
- [X] Write actual starting word locations.

### Phase 2 — Characters
- [X] Build character creation (name, class, stat generation, save to DB)
- [X] Build character login (load existing character from DB by name)
- [ ] Display character sheet (`stats`, `inventory`, `gold`, `class`)
- [X] Implement the six stats and their modifier calculations

### Phase 3 — Core Game Loop
- [X] Build the main game loop skeleton (read input, parse command, do something, repeat) # TO READ
- [X] Build a command parser (map typed commands to functions) # TO READ
- [X] Display location descriptions on entry # TO READ/EDIT
- [X] Implement `look` command (redisplay current location) # TO READ/EDIT
- [ ] Implement `exits` command (show available directions)

### Phase 4 — Travel
- [X] Implement directional movement (`go north`, `n`, etc.)
- [ ] Implement endurance as a stat on characters
- [ ] Deduct endurance on movement, block movement if exhausted
- [ ] Implement `rest` command (recover endurance, risk in dangerous areas)
- [ ] Implement `camp` command (longer rest, requires supplies)

### Phase 5 — Items & Inventory
- [ ] Implement `inventory` command (list carried items)
- [ ] Implement `equip` and `unequip` commands
- [ ] Implement `drop` and `take` commands (items in locations)
- [ ] Implement item stat effects (equipped weapon affects attack, armor affects defense)
- [ ] Implement consumables (food restores endurance/HP, torches for dark areas)
- [ ] Implement starting equipment per class -- TODO

### Phase 6 — NPCs & Dialogue
- [ ] Spawn NPC instances into locations from templates
- [ ] Display NPCs in location descriptions
- [ ] Implement `look at <npc>` command
- [ ] Implement `ask <npc> about <topic>` command
- [ ] Implement `talk to <npc>` as a general greeting/default dialogue

### Phase 7 — Combat
- [ ] Design combat stats (attack, defense, speed, derived from six attributes)
- [ ] Build basic turn-based combat first (simpler, gets logic right before threading)
- [ ] Implement player attack command
- [ ] Implement enemy AI (basic: attack on timer)
- [ ] Implement flee command
- [ ] Introduce threading for real-time combat (player and enemy act independently)
- [ ] Implement extra actions (spells, skills, abilities) per class
- [ ] Implement death (corpse, item loss, skill decay)
- [ ] Implement loot command after combat

### Phase 8 — Economy & Shops
- [ ] Implement gold on characters
- [ ] Build shop system (browse, buy, sell)
- [ ] Implement shop inventories per location/NPC
- [ ] Implement vendor dialogue (greetings, haggling if desired)

### Phase 9 — Quests
- [ ] Design quest objective types (kill, deliver, reach location, etc.)
- [ ] Build quest schema (quests, quest_objectives, character_quests, character_objective_progress)
- [ ] Implement quest offer dialogue from NPCs
- [ ] Implement quest acceptance and tracking
- [ ] Implement objective progress updates (on kill, on deliver, on arrival)
- [ ] Implement quest completion and reward delivery
- [ ] Implement `quests` command (list active quests and progress)

### Phase 10 — World Building Tool
- [ ] Build a simple form-based world editor (create locations, add exits)
- [ ] Auto-generate return exits (north creates south automatically)
- [ ] Add NPC placement to the editor
- [ ] Add item placement to the editor

### Phase 11 — Factions
- [ ] Build faction tables and seed starter factions
- [ ] Implement reputation scores and standing thresholds
- [ ] Link NPCs to factions via faction_membership
- [ ] Update reputation on combat actions
- [ ] Implement faction_relationships (helping one faction affects another)
- [ ] Gate dialogue, quests, or shops behind reputation standing

### Phase 12 — Depth & Polish
- [ ] Implement wandering monsters (roaming npc_instances between locations)
- [ ] Implement class-specific world interactions (Ranger navigation bonus, Rogue stealth, etc.)
- [ ] Implement corpse recovery mechanic
- [ ] Implement darkness/torch mechanic
- [ ] Implement stranded/exhaustion failure state
- [ ] Implement persistent legendary monsters
- [ ] Implement player knowledge system (locations visited, notes, map memory)

### Phase 13 — Deferred Systems
- [ ] Weather (mechanical effects on travel and combat)
- [ ] Seasonal changes
- [ ] Crafting system
- [ ] Property ownership
- [ ] Visual map editor (significant side project)

### Phase 14 - Things I Did
- [X] Added several social commands
- [X] Looked into multiplayer options
- [X] Tested multiplayer (it works, now!)
# WORLD_SPEC.md v2 (CORRECTED FINAL DESIGN)

## 1. World Philosophy

The world is a **handcrafted, persistent spatial graph designed for memorization and exploration mastery**.

It prioritizes:

* spatial learning
* navigation skill
* environmental familiarity
* structured danger zones

Over:

* realism simulation
* procedural variation

---

## 2. Dual-Layer World Model

### 2.1 Macro Layer (Navigation Graph)

The world is composed of:

* unique locations (nodes)
* explicit directional exits (edges)

This layer defines:

* actual movement
* persistence
* combat location
* NPC placement
* corpse locations

No duplication exists at this layer.

---

### 2.2 Micro Layer (Room Templates)

Locations MAY share visual/structural templates:

Examples:

* “West Road Segment”
* “City Alley Segment”
* “Forest Path Segment”

These templates define:

* description style
* environmental flavor
* encounter weighting (optional future use)

BUT:

They do NOT define:

* connectivity
* identity
* persistence

---

## 3. Spatial Philosophy

The world is:

* logically consistent (roads connect, cities exist coherently)
* gameplay-structured (not physically simulated)
* learnable via repeated exposure

Players develop:

> “mental geography mastery”

---

## 4. Navigation Model

Movement is:

* node-to-node traversal via exits
* explicit directional choices
* no hidden transitions

Players learn:

* safe routes
* dangerous routes
* efficient traversal paths

---

## 5. Distance Model

Distance is:

* number of node transitions

AND optionally:

* difficulty scaling by region type (not raw distance)

No physical simulation required.

---

## 6. Settlement System

Settlements are:

* major graph anchors (C-type importance)
* respawn points
* service hubs (trainers, shops)
* safe zones

They define:

* world structure “gravity points”

---

## 7. Regional Structure

Regions are:

* logical grouping of nodes
* not instanced zones
* not simulation layers

Used for:

* organization
* thematic consistency
* encounter tuning (future expansion hook)

---

## 8. Combat Geography

Location flags define:

* safe zones → no combat
* dangerous zones → frequent combat
* mixed zones → conditional encounters

Combat is strongly influenced by location context.

---

## 9. Corpse System

On death:

* corpse persists in exact node
* items remain at location
* enemies may remain present

This creates:

> geography-based recovery difficulty

---

## 10. World Expansion Model

World grows via:

### Preferred:

* integrating new nodes into existing graph structure

### Acceptable:

* adding new edge-connected regions

Avoid:

* disconnected expansion chunks

---

## 11. Player Experience Model

Players are intended to feel:

* mastery through memorization
* pride in navigation knowledge
* increasing efficiency over time
* occasional tension in unfamiliar or dangerous zones

---

## 12. Design Constraints

### Must:

* maintain consistent graph topology
* keep node identity unique
* ensure persistence correctness

### Must NOT:

* duplicate nodes to simulate reuse
* introduce procedural routing
* break spatial consistency for convenience

---


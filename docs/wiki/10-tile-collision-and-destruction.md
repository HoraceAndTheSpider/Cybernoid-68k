# 10. Tile collision, solidity and destruction

## Why two tiles that look similar can behave differently

Cybernoid does **not** decide whether the player can fly through a square by looking at the picture.

Each room square stores a numeric tile/control value. During room loading, that value is also used to build the live collision map. A decorative-looking tile can therefore be solid even if it visually resembles empty background.

This explains a common editor surprise: placing a tile because it *looks* like background does not guarantee that the ship can pass through it.

## The passability table

**Verified:** the game has a 67-word passability table at runtime `$113FC`.

When a room square's value matches an entry in that table, the room loader clears the live collision cell to zero. For ordinary graphic tiles this means the square is passable.

If an ordinary tile is **not** in the table, its value remains in the collision map and the square behaves as solid.

The editor therefore has enough information to colour-code every normal tile without guessing from its artwork.

The generated reference file:

`outputs/cybernoid_tile_properties.csv`

lists all 961 tile-bank IDs with their Levels 1-3 and Level-4 classifications.

## Editor colour key

The pygame editor uses:

- **green** — passable;
- **red** — solid;
- **orange** — destructible;
- **purple** — special/control value with extra runtime behaviour;
- **yellow** — Level-4 energy-field hazard.

The tile palette always shows these borders. The optional **Collision** overlay draws the same classification over the current room.

## Destructible tiles

A destructible square is not necessarily a one-cell object. Some belong to larger structures.

Verified single-cell destructibles include:

`$068`, `$069`, `$06B`, `$0ED`

Verified destructible multi-cell families include:

- `$232-$237` 2x3 structure;
- `$242-$245` 2x2 structure;
- the `$300` organic cannon footprint;
- the `$30C` large cannon footprint.

Some cells belonging to a destructible structure are themselves in the passability table. The editor therefore records **both** facts rather than collapsing everything to one label: for example a cell can be part of a destructible object while its individual collision cell is passable.

## Special/control values

Values such as START, PORTAL, RNET, CRP, ELE and cannon anchors are not ordinary background tiles. Their room word causes additional setup when the room loads.

For these values the editor shows **Special** even when the raw value also appears in the passability table. The inspector then gives the closer collision information where known.

There is no hidden background tile underneath a special value. If it is later moved or deleted, the editor must be told what normal tile should replace that square.

## Level-4 energy fields

`$257-$25E` are unusual:

- Levels 1-3: the values are in the passability table, so they are passable;
- Level 4: the loader deliberately replaces the live collision cell with `$1234`, making the energy field lethal/blocking.

The editor therefore changes their collision colour to **yellow** when Level 4 is selected.

## Cannon/gun source footprints

Three gun types that look like a single special "tip" actually rely on neighbouring source tiles.

### `$31C` fixed cannon

Source pair:

```text
31C 31D
```

Runtime animation uses the two-cell frame families `$31C/$31D`, `$31E/$31F`, `$320/$321`, `$322/$323`.

### `$329` right-facing gun

The `$329` controller/tip is the right-most cell:

```text
326 327 328 329
```

All ten original `$329` placements use this exact four-cell source strip.

Its firing animation uses six four-cell frames read from the table at `$4014C`.

### `$346` left-facing gun

The `$346` controller/tip is the left-most cell:

```text
346 347 348 349
```

One original placement uses `$359` instead of `$349` for the final source cell; the editor treats that as a valid original variant.

Its firing animation uses six four-cell frames from `$4017C`.

## Why multiple side guns can animate on the "wrong" mount

This is original engine behaviour, not an editor corruption.

All `$329` guns share one global firing countdown at `$3FF2C`.
All `$346` guns share another at `$3FF2A`.

The animation countdown is stored per gun, but the firing countdown is shared between every gun of that direction. When several same-direction guns exist, one gun can be the controller that notices the shared countdown reaching zero and starts its animation, while the next gun processed can see the now-zero shared timer and create the projectile.

The practical result can be:

- projectile from gun A;
- firing animation on gun B;
- then alternating behaviour on later shots.

The original maps themselves contain up to **two `$329` guns in one room** and **five `$346` guns in one room**, so the editor must not forbid this outright. It should warn that multiple same-direction guns share their firing timer and may show this cross-mount animation behaviour.

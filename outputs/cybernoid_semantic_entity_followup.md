# Cybernoid semantic entity follow-up

Verified / formalised 5 September 2026 against the current repository GAME and the
lossless project model.

## Entity grouping corrections

- `$24D/$24E` is one 2x1 animated entity. `$24F-$252` are runtime animation phases and
  have no source-map occurrences in this GAME.
- `$253-$26E` are independent one-cell animation controllers, not multi-cell machinery.
- `$257-$25E` are passable in Levels 1-3 and become lethal in Level 4 through live
  collision sentinel `$1234`.
- `$1E0/$1E1` RACT markers are independent one-cell animation controllers.
- `$200/$2E2` are one-cell mixed-spawn pit aliases; `$2E6/$2EE` are accepted by the
  dispatcher but unused in the source maps.

## Compound ownership

- `$232`: six owned cells (2x3).
- `$242`: four owned cells (2x2).
- `$300`: ten owned cells; final `$05F` has one proven `$210` source variant.
- `$30C`: eleven owned cells. The bottom-right `(+2,+1)` cell is context/collateral and
  is deliberately excluded from move/delete ownership. Original values there are
  `$121`, `$049`, `$04A`, `$04B`, `$003`.

## Controller budget

Generic controller bank: slots 157..212, 56 records. A 57th request is unsafe.
Current maximum source demand is L4 R77 at 52/56 controllers (only four free).

## Fixed/synchronised structures

- Portals: exactly eight records. Runtime matches room plus trigger coordinate, so two
  records may share a source room if trigger cells differ. Safe editor policy is
  move/re-target only; source and destination are naturally editable in tile units.
- START: one marker per level plus the logical start-room table; move/synchronise only.
- Landing pad: one adjacent `$324/$325` pair per level; move as a pair.
- ELE: atomic endpoint pair, maximum five pairs per room.

## RNET / CRP presentation

RNET source markers are processed row-major. First eight instantiate slots 34..41;
later markers are skipped when the primary pool is full.

CRP source markers are processed row-major. First six instantiate slots 70..75. Every
excess source initialises slot 76; later excess markers overwrite the same record, so
only the final excess source remains as the seventh live crawler.

The semantic editor should display these roles rather than treating every map marker as
an equivalent live enemy.

## Tested edit backend

`tools/cybernoid_entity_ops.py` implements fixed-size semantic operations with capacity,
footprint and synchronisation checks. Eleven non-GUI unit tests now pass across the
entity derivation and operation layers.

Vacated cells default to `$000`, a blank tile explicitly present in the game's
passability table. A future UI can choose a different replacement/background tile.

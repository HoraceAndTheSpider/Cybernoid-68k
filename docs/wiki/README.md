# Cybernoid Amiga reverse-engineering wiki

This wiki explains what has been learned about the Amiga version of **Cybernoid** while building a lossless level extractor, editor and patcher.

It is deliberately written in two layers:

1. **Plain-language explanation** — what a part of the game data represents and why an editor needs to care about it.
2. **Technical reference** — runtime addresses, sizes, formats and behaviours for anyone who wants to build their own tools or continue the reverse engineering.

The original `data/GAME` remains the authority. Where something is not fully proved, the wiki says so rather than filling the gap with a guess.

## Confidence labels

- **Verified** — checked directly against the current `GAME` binary and/or the code paths that use the data.
- **Strong inference** — the evidence is good, but one part of the behaviour has not been independently confirmed.
- **Unresolved** — deliberately preserved without pretending we know more than we do.

## Pages

1. [Project goal and method](01-project-goal-and-method.md)
2. [Binary layout and addresses](02-binary-layout-and-addresses.md)
3. [Levels, rooms and topology](03-levels-rooms-and-topology.md)
4. [Graphics, palettes and front-end screens](04-graphics-palettes-and-frontend.md)
5. [Special markers and semantic entities](05-special-markers-and-entities.md)
6. [Runtime object pools and capacity](06-runtime-object-pools.md)
7. [Automatic enemy scripts](07-automatic-enemy-scripts.md)
8. [Editor and repacking safety](08-editor-and-repacking-safety.md)
9. [Known unknowns and current research status](09-known-unknowns.md)

## Important project files

- `data/GAME` — original Amiga game binary used by this research.
- `tools/cybernoid_project.py` — lossless extractor/repacker.
- `tools/cybernoid_semantics.py` — structural checks and semantic decoding.
- `tools/cybernoid_entities.py` — higher-level room object/entity model.
- `tools/cybernoid_entity_ops.py` — tested semantic edit operations.
- `editor/cybernoid_editor.py` — pygame editor.
- `docs/reverse-engineering-status.md` — compact technical status log.

## The key design principle

The editor is not allowed to “fix” data just because it looks strange. The first goal is always:

> `GAME -> extracted project -> GAME` must be byte-for-byte identical when nothing has been edited.

That principle is the reason raw values are retained alongside friendlier labels such as “portal”, “crawler” or “large cannon”.

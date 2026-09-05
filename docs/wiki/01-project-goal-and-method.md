# 1. Project goal and method

## What are we trying to build?

The practical target is a **Cybernoid level editor for the Amiga version** that can:

- show every gameplay room using the original graphics;
- show the logical arrangement of rooms within each level;
- recognise important gameplay objects and control markers;
- edit rooms without damaging unrelated game data;
- save a structured project;
- patch those changes back into a playable `GAME` binary.

A full re-source/recompile of the entire game is a possible later step, but it is **not required for normal fixed-size level editing**.

## Why not just treat the game as a big tile map?

Because a room square is not always just scenery. Some numeric values are instructions to the room loader. For example, a room square can mean:

- player start;
- portal trigger;
- automatic enemy spawn limit;
- crawler enemy;
- paired moving object endpoint;
- large multi-tile cannon;
- animated energy field.

Some of those values also happen to point at valid graphics tiles. The editor therefore needs to know both:

- **the raw 16-bit value actually stored in the room**, and
- **the gameplay meaning the engine gives that value**.

## Lossless first, semantic second

The project deliberately separates two layers.

### Raw/lossless layer

The extractor keeps:

- the original source `GAME`;
- all known fixed-size data exactly;
- raw room words;
- raw palette words;
- raw graphics data;
- raw automatic-enemy script bytes;
- unknown/unmapped bytes via the retained source binary.

Repacking begins from the retained source binary and writes only known fixed-size fields back into their original locations.

### Semantic layer

A separate layer describes things in human terms:

- “this `$1D5` is a portal”;
- “these 11 cells belong to one `$30C` cannon”;
- “this RNET marker will be skipped because the runtime pool is full”;
- “these two ELE markers form one paired mover”.

The semantic layer is useful for editing, but it does not replace the raw data.

## Current milestone

**Verified:** a no-edit extraction/repack returns the complete 383,230-byte `GAME` image unchanged.

That is the most important safety milestone. It means the data model is capable of round-tripping the known editable structures without moving or damaging unrelated binary content.

## Why some editor features remain conservative

The game has several fixed-size runtime object pools. A room can contain more source markers than the engine can instantiate simultaneously. Therefore an editor cannot safely assume that adding “one more enemy marker” always produces one more live enemy.

Where the runtime rules are understood, the editor can enforce them. Where they are not yet completely understood, the current policy is to expose inspection first and high-level editing later.

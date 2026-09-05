# 7. Automatic enemy scripts

## What these scripts do

Some rooms contain ST/ED markers that define where automatic enemies can enter from an edge. The exact enemy movement is not hard-coded separately into every room. Instead, the game chooses from a small library of 16 bytecode scripts.

There are four variants for each side:

```text
BOTTOM 0-3
TOP    0-3
RIGHT  0-3
LEFT   0-3
```

## Storage

The 16 big-endian pointers are stored at:

```text
$3FCFC-$3FD3B
```

The current script byte streams occupy:

```text
$40217-$40401 inclusive
```

All current streams end in `$81`.

## Current script starts

Sorted by storage address:

```text
LEFT0   $40217
LEFT1   $40231
LEFT2   $4025A
LEFT3   $4026F
RIGHT0  $40290
RIGHT1  $402A2
RIGHT2  $402BB
RIGHT3  $402CF
TOP0    $402F0
TOP1    $40307
TOP2    $4031D
TOP3    $40333
BOTTOM0 $4033F
BOTTOM1 $40387
BOTTOM2 $403AC
BOTTOM3 $403CD
```

## Script header

Each stream begins with three bytes:

```text
object_count
animation_start
animation_end
```

`object_count` is currently 1 or 2. A value of 2 makes the spawn path use an adjacent second live-object record.

## Decoded commands

The current script library can be completely decoded with the following grammar.

### `$81` — loop

Return to the first command after the three-byte header.

### `$82` — fire one projectile

Create one enemy projectile.

### `$85` — fire three projectiles

Create three enemy projectiles.

### `$80 count dx dy` — repeated movement

Repeat the signed `(dx,dy)` movement for `count` updates.

If `count` is `$84`, the runtime uses a random value masked with `$3F` instead.

### `$83 count` — wait

Remain stationary for `count` updates.

If `count` is `$84`, the runtime uses a random value masked with `$1F`.

### `dx dy` — one movement step

Any other command byte is interpreted as signed X movement, followed by signed Y movement.

## Why the raw bytes are still retained

Even though the current interpreter is understood, the lossless project stores both:

- the raw script stream; and
- the decoded command view.

This keeps round-trip safety and makes it possible to compare future game variants without assuming every release uses exactly the same bytecode library.

## Editing status

The bytecode grammar is understood, but the current fixed-size repacker does not relocate scripts. An editor may safely change commands only while keeping each stream within its existing allocated byte length, unless a future re-source/relocation system is added.

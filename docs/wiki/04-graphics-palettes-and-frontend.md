# 4. Graphics, palettes and front-end screens

## Main tile graphics

The game uses a bank of **961 tiles**, IDs `0..960` (`$000-$3C0`).

Each tile is:

- 16x16 pixels;
- 4 bitplanes;
- 16 colours maximum;
- `$80` bytes.

The correct bank begins at runtime `$1FBE8`. Tile 0 is a blank 128-byte tile.

Earlier atlases built from `$1FC68` were shifted by one tile and are obsolete.

## Palette A — menu and Hall of Fame

Palette A lives at `$3FFD0` and is used by the front-end/menu/high-score presentation.

It exists because the front-end artwork, especially the Cybernoid logo, uses a more colourful gradient than the normal gameplay rooms.

Current Palette A:

```text
$000 $222 $444 $666 $AAA $EEE $EA0 $820
$420 $640 $E40 $E80 $E60 $600 $EE0 $EE8
```

## Palette B — normal gameplay

Palette B lives at `$3FFF0` and is the normal room palette for Levels 1–3.

```text
$000 $444 $666 $888 $AAA $EEE $E20 $820
$420 $640 $2C2 $282 $C62 $600 $46E $00C
```

## Level 4 colour change

Level 4 does not store a completely separate 16-colour palette.

**Verified:** when the internal level index becomes 3 (Level 4), the game copies eight words from `$1CD10` over Palette B entries 0–7.

The Level 4 first half becomes:

```text
$000 $642 $A64 $C84 $EA6 $EEE $E20 $820
```

Palette B entries 8–15 stay unchanged.

So Level 4 is best understood as **Palette B plus an eight-colour override**. The familiar yellow/brown look is produced mainly by these changes:

```text
$444 -> $642
$666 -> $A64
$888 -> $C84
$AAA -> $EA6
```

A matching restore table at `$1CD30` puts the normal grey first eight colours back afterwards.

### Editor implication

This is ideal for palette editing. Someone could make Level 4 blue, green, darker, etc. by changing only the eight override colours without affecting Levels 1–3.

The intended palette editor should provide:

- colour swatches;
- Amiga `$RGB` nibble editing;
- live preview of a real room;
- Level 4 override preview;
- reset/copy controls;
- front-end preview using Palette A.

## Front-end faux room

The menu/Hall-of-Fame background is a real tile layout, but it is **not one of the 150 gameplay rooms**.

**Verified:** one shared 20x12 front-end template is stored at:

```text
$50F30-$5110F
```

The first four rows contain every tile `$391-$3C0` exactly once. These high tile IDs form the multi-tile Cybernoid logo artwork.

The same background is reused for several front-end states. Text, names, scores and messages are drawn separately over it.

## Front-end text/state region

The block roughly `$40402-$40847` contains front-end strings/command data including:

- Hall of Fame / high-score display;
- name entry;
- menu/credit text;
- game-over text;
- other front-end messages.

This is a separate presentation system rather than a normal gameplay room map.

## Gameplay HUD/header strip

A separate 20x2 tile strip exists at `$3FF4E-$3FF9D`. It belongs to gameplay display/HUD setup and should not be confused with another high-score room.

## Completion/sequel preview

At `$1DA90-$1F9CF` is a 160x100 4-plane image shown after completing Cybernoid. It previews Cybernoid II; it is not the Cybernoid title screen.

Its palette is stored separately at `$1F9D0-$1F9EF`.

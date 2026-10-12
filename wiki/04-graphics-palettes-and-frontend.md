# 4. Graphics, palettes and front-end screens

## Main tile graphics

The current game contains **961 tiles** (`$000–$3C0`). Every source tile is 16×16 pixels, 4 bitplanes, 16 palette indices maximum and **`$80` (128) bytes**. The tile bank begins at **runtime `$1FBE8`**; tile zero is a blank tile. Earlier atlases from `$1FC68` were shifted by one tile and are obsolete.

### Byte/bit-plane order confirmed during HTML5 conversion

The existing Python decoder in `editor/cybernoid_editor.py` reads the graphics through the `tile_bank.bin` extracted by `tools/cybernoid_project.py`. HTML5 now implements that same documented layout directly against loaded GAME bytes:

```text
tile_runtime_addr = $1FBE8 + tile_id * $80
for each source scanline (y = 0..15):
    plane_0 = big_endian_word(tile_runtime_addr + y*8 + 0)
    plane_1 = big_endian_word(tile_runtime_addr + y*8 + 2)
    plane_2 = big_endian_word(tile_runtime_addr + y*8 + 4)
    plane_3 = big_endian_word(tile_runtime_addr + y*8 + 6)
    pixel_index(x) = bit15_minus_x(plane_0)
                  | (bit15_minus_x(plane_1) << 1)
                  | (bit15_minus_x(plane_2) << 2)
                  | (bit15_minus_x(plane_3) << 3)
```

In other words, each 16-pixel row occupies **eight bytes** with all four big-endian plane words in 0→3 order. Bit 15 is the leftmost pixel. The result is an index from 0–15 into the active 16-colour palette. This is a specification for a future tile *encoder* as well as the current renderer. Source-backed conversion, not an independent second-game disassembly claim.

## Palette A — menu and Hall of Fame

Runtime `$3FFD0`: front-end/menu/high-score presentation, including the logo gradient.

```text
$000 $222 $444 $666 $AAA $EEE $EA0 $820
$420 $640 $E40 $E80 $E60 $600 $EE0 $EE8
```

## Palette B — ordinary gameplay

Runtime `$3FFF0`: normal Level 1–3 gameplay room palette.

```text
$000 $444 $666 $888 $AAA $EEE $E20 $820
$420 $640 $2C2 $282 $C62 $600 $46E $00C
```

### RGB expansion in the browser

Amiga palette words use **12-bit `$RGB`**, with four bits each for red, green and blue. A display component is `nibble * 17`, not a modern 24-bit colour value stored in the original file. HTML5 uses the native words to build a disposable tile atlas, so neither a PNG nor an expanded palette table is required in the game file.

## Level-4 palette override

**Verified:** When the internal level index is 3, the engine copies **eight words** at `$1CD10` over Palette B indices 0–7. The final eight palette entries are still taken from B.

```text
$000 $642 $A64 $C84 $EA6 $EEE $E20 $820
```

A normal-gameplay restore table at `$1CD30` reinstates the first eight B entries afterwards. Earlier grey shades `$444/$666/$888/$AAA` are replaced by `$642/$A64/$C84/$EA6`, creating much of Level 4's brown-yellow appearance.

**Editor implication:** future palette editing should let the user preview/change Level 4's eight override entries separately while keeping Palette B and its restore copy synchronised. The HTML5 v0.1 palette switch is **preview-only**.

## Front-end faux room

The shared menu/Hall-of-Fame background is a separate **20×12** tile template at runtime `$50F30–$5110F`; it is **not** among the 150 gameplay rooms. Its first four rows contain every tile `$391–$3C0` exactly once and form the Cybernoid logo. Menu words, names and scores are drawn separately over this shared artwork.

## Front-end text/state area

The region approximately `$40402–$40847` holds menu, high-score, name entry, game-over and related presentation strings/command data; not an ordinary gameplay room map.

## Gameplay HUD/header strip

A different **20×2 tile strip** at `$3FF4E–$3FF9D` forms gameplay HUD setup; this is not the Hall-of-Fame background.

## Completion / sequel preview

A separate 160×100 4-plane image at `$1DA90–$1F9CF` previews Cybernoid II after game completion. It is **not** the title screen. Its 16-colour palette is at `$1F9D0–$1F9EF`.

## Current HTML5 editor limitations

v0.1 reads and displays source tiles/palettes but writes only ordinary room word changes. Tile pixels, atlas data, palette words, animation graphics, preview art, front-end/HUD tiles and export of arbitrary new tile IDs are **not** yet editable. Future Tile Editor should adapt Indy Heat drawing routines to the authentic planar index format above while obeying any tile/entity animation relationships.

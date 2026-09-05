# Front-end room and palette findings

Verified 5 September 2026 against repository `data/GAME`.

## Shared front-end faux room

- runtime: `$50F30-$5110F`
- dimensions: 20x12 words
- palette: Palette A `$3FFD0`
- reused across front menu, Hall of Fame/name-entry and related front-end states
- first four rows contain tile IDs `$391-$3C0`, the dedicated multi-tile Cybernoid logo

Front-end text/state overlays are stored separately in the `$40402-$40847` block,
including `CYBERNOID HALL OF FAME`, name-entry, credits/menu and game-over strings.

## Gameplay HUD strip

The separate 20x2 structure at `$3FF4E-$3FF9D` is the gameplay HUD/header source, not
a second high-score faux room.

## Palette B / Level 4

Normal gameplay Palette B:

```text
$000 $444 $666 $888 $AAA $EEE $E20 $820
$420 $640 $2C2 $282 $C62 $600 $46E $00C
```

When internal level index 3 is entered, runtime `$1CD50` overwrites entries 0-7 from
`$1CD10`:

```text
$000 $642 $A64 $C84 $EA6 $EEE $E20 $820
```

Effective Level-4 palette:

```text
$000 $642 $A64 $C84 $EA6 $EEE $E20 $820
$420 $640 $2C2 $282 $C62 $600 $46E $00C
```

Runtime `$1CD70` restores the normal first eight Palette-B values from duplicate table
`$1CD30-$1CD3F`. A palette editor should therefore treat this restore table as derived
from Palette B colours 0-7, not as an independent user-facing palette.

; Cybernoid Amiga — focused room loading / transition path
; Runtime addresses. Relocated-image mapping: runtime = file_offset + $EE06.
;
; This is an annotated reverse-engineering extract, not a complete buildable source.

CurrentRoom              EQU $0003FE30
PreviousRoom             EQU $0003FE2E
RoomChangePending        EQU $0003FE2C
RoomEntryX               EQU $0003FE32
RoomEntryY               EQU $0003FE34
CurrentLevel             EQU $0003FD3C
RoomCollisionMap         EQU $0003EB68

LevelStartRoomTable      EQU $0003FFB8
LevelSourceStrideTable   EQU $0003FFC0
Level123MapPairTable     EQU $0003FD4E

Level1LogicalToPhysical  EQU $0003FD66
Level2LogicalToPhysical  EQU $0003FD96
Level3LogicalToPhysical  EQU $0003FDD6

Level1MapBase            EQU $0004084A
Level2MapBase            EQU $00042228
Level3MapBase            EQU $000449B0
Level4MapBase            EQU $000480B0

PassableTileList         EQU $000113FC
Level4PortalTable        EQU $0001659E


; ---------------------------------------------------------------------------
; LEVEL START: choose initial logical room
; $010046
; ---------------------------------------------------------------------------

    move.w  CurrentLevel,d0
    mulu.w  #2,d0
    addi.l  #LevelStartRoomTable,d0
    movea.l d0,a0
    move.w  (a0),CurrentRoom

; LevelStartRoomTable:
;   dc.w 0,3,1,9


; ---------------------------------------------------------------------------
; ROOM SOURCE ADDRESS: $01B9D4-$01BA20
; Entry: D0 = CurrentRoom
; ---------------------------------------------------------------------------

    cmpi.w  #3,CurrentLevel
    bne.s   .level123

; Level 4: logical IDs are direct 8-wide grid positions.
    move.w  d0,d1
    andi.w  #7,d1
    mulu.w  #$28,d1             ; x * 20 words
    lsr.w   #3,d0               ; y = room / 8
    mulu.w  #$0DC0,d0           ; 11 rows * $140 bytes
    add.w   d1,d0
    addi.l  #Level4MapBase,d0
    movea.l d0,a0
    bra.s   .have_room_source

.level123:
    mulu.w  #2,d0               ; word lookup index
    move.w  CurrentLevel,d1
    mulu.w  #8,d1               ; two longwords per level
    addi.l  #Level123MapPairTable,d1
    movea.l d1,a5
    add.l   (a5)+,d0            ; logical->physical lookup address
    move.l  (a5),d1             ; packed map base
    movea.l d0,a0
    move.w  (a0),d0             ; physical background ID
    mulu.w  #$28,d0             ; physical screen offset within source row
    add.l   d1,d0
    movea.l d0,a0

.have_room_source:
    lea     $00072400,a1
    moveq   #19,d2              ; 20 columns
    moveq   #10,d1              ; 11 rows
    clr.w   $0003FE1C           ; tile X during room build
    clr.w   $0003FE1E           ; tile Y during room build
    lea     RoomCollisionMap,a6

.row:
    movem.l a1/d2,-(sp)

.tile:
    move.w  (a0)+,d0
    ; ... special tiles $1F8/$1F6 are handled here ...
    movem.l a1/a0/d2/d1,-(sp)
    jsr     $00010C20            ; tile/object/collision handler
    addq.w  #1,$0003FE1C
    movem.l (sp)+,d1/d2/a0/a1
    lea     2(a1),a1
    dbra    d2,.tile

    clr.w   $0003FE1C
    addq.w  #1,$0003FE1E

    move.w  CurrentLevel,d4
    mulu.w  #4,d4
    addi.l  #LevelSourceStrideTable,d4
    movea.l d4,a3
    adda.l  (a3),a0
    suba.l  #$28,a0             ; compensate for 40 bytes consumed by tile loop

    movem.l (sp)+,d2/a1
    lea     $280(a1),a1
    dbra    d1,.row


; ---------------------------------------------------------------------------
; STATIC COLLISION CLASSIFICATION: $0113E2 onwards
; D0 = tile ID, A6 points into RoomCollisionMap.
; ---------------------------------------------------------------------------

    move.w  d0,(a6)+

    lea     PassableTileList,a3
    moveq   #66,d1              ; 67 tile IDs
.passable_search:
    cmp.w   (a3)+,d0
    beq.s   .passable
    dbra    d1,.passable_search
    bra.s   .draw_tile

.passable:
    clr.w   -2(a6)              ; zero == non-solid collision cell

.draw_tile:
    mulu.w  #$80,d0
    addi.l  #$0001FBE8,d0
    ; ... copy 16x16 4-plane tile ...


; ---------------------------------------------------------------------------
; SPECIAL TILE $002B: initial-player spawn marker ($010CC0)
; ---------------------------------------------------------------------------

    cmpi.w  #$002B,d0
    bne.s   .not_start_marker
    bsr     $010C6A             ; tile X/Y -> screen pixel X/Y
    move.w  d1,RoomEntryX
    subi.w  #$10,d2
    move.w  d2,RoomEntryY
    ; the tile itself continues through normal room construction


; ---------------------------------------------------------------------------
; PLAYER EDGE CHECK: $014BDC
; ---------------------------------------------------------------------------

    move.w  CurrentRoom,d0

    cmpi.w  #$014F,$2C(a0)      ; player X
    bgt     TransitionRight

    cmpi.w  #$0021,$2C(a0)
    blt     TransitionLeft

    cmpi.w  #$0019,$2E(a0)      ; player Y
    blt     TransitionUp

    cmpi.w  #$00B7,$2E(a0)
    bgt     TransitionDown
    rts


; ---------------------------------------------------------------------------
; NORMAL TRANSITIONS
; ---------------------------------------------------------------------------

TransitionRight:                 ; $015302
    addq.w  #1,d0
    cmp.w   PreviousRoom,d0
    beq     .reject
    move.w  #$001E,RoomEntryX
    move.w  $2E(a0),RoomEntryY
    bra.s   CommitTransition

TransitionLeft:                  ; $01533A
    subq.w  #1,d0
    cmp.w   PreviousRoom,d0
    beq     .reject
    move.w  #$0152,RoomEntryX
    move.w  $2E(a0),RoomEntryY
    bra.s   CommitTransition

TransitionUp:                    ; $015372
    subq.w  #8,d0
    cmp.w   PreviousRoom,d0
    beq     .reject
    move.w  #$00BA,RoomEntryY
    move.w  $2C(a0),RoomEntryX
    bra.s   CommitTransition

TransitionDown:                  ; $0153C6
    addq.w  #8,d0
    cmp.w   PreviousRoom,d0
    beq     .reject
    move.w  #$0016,RoomEntryY
    move.w  $2C(a0),RoomEntryX

CommitTransition:
    move.w  CurrentRoom,PreviousRoom
    move.w  d0,CurrentRoom
    move.w  #$FFFF,RoomChangePending
.reject:
    rts


; ---------------------------------------------------------------------------
; LEVEL 4 SPECIAL PORTALS: $016526
; Record: sourceRoom, triggerX, triggerY, destinationRoom, destX, destY
; Eight records at $01659E.
; ---------------------------------------------------------------------------

;  source  trigger X/Y       destination  X/Y
;    10    $130,$088    ->     26       $030,$028
;    30    $130,$088    ->     23       $050,$078
;    61    $0B0,$098    ->     44       $040,$058
;    49    $090,$028    ->     56       $0E0,$028
;    48    $050,$078    ->     65       $090,$0A8
;    57    $040,$038    ->     65       $090,$0A8
;    72    $120,$038    ->     72       $050,$088
;    79    $100,$068    ->     33       $140,$098

; On overlap:
;     CurrentRoom = record.destinationRoom
;     RoomEntryX  = record.destX
;     RoomEntryY  = record.destY
;     ST $000179DE              ; force room redraw

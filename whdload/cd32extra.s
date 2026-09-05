;
;             CYBERNOID 
;
;     2 BUTTON & CD32 PAD CONTROLS
;       ADDED BY HUNGRY HORACE
;	 FOR WHDLOAD SLAVE 1.3
;
; ================================

; =======	NEW CONTROL SYSTEM - 2 BUTTON (DEFAULT) AND CD32 CONTROLS


; =======	READ CD32 BUTTONS

_cd32_read	bsr		_joystick		; read CD32 inputs on ports
		btst		#4,$DFF01D
		rts


; =======	ORIGINAL MENU SCREEN SFX TOGGLE KEY & QUICK CHEAT (2 / TAB)
							
_sfx_key	cmpi.b 		#$42,$3FEC4		; TAB key
		bne		.next		
		jmp		$16966			; activate cheat

.next		cmpi.b 		#2,$3FEC4		; if "2" is pressed ; @ $168AC
		beq		_sf_toggle		; do the switch!
		jmp 		$168B8			; return to original code
_sf_toggle	jmp		$16C3A


; =======	NORMAL MENU SCREEN SFX TOGGLE (SECOND BUTTON)
				
_sfx_2button	movem.l		d0/a0,-(a7)		; preserve reg's
		lea		held_button(pc),a0	; link held_button + a0

		btst.b		#14-8,$DFF016		; test second button (joy 1)
		bne		_reset_sfx		; not true, skip routine

_shared_sfx	btst		#JPB_BTN_BLU,(a0)	
		bne		_skip_sfx		; skip it
		bset		#JPB_BTN_BLU,(a0)	; held_button = 1

		movem.l		(a7)+,d0/a0		; restore reg's
		bra		_sf_toggle		; goto sfx change

_reset_sfx	bclr		#JPB_BTN_BLU,(a0)	; held_button = 0		
_skip_sfx	movem.l		(a7)+,d0/a0		; restore reg's
		bra		_sfx_key		; return to sfx input


; =======	CD32 MENU SCREEN SFX TOGGLE (BLUE)

_sfx_cd32	movem.l		d0/a0,-(a7)		; preserve reg's
		lea		held_button(pc),a0	; link held_button + a0
		move.l		joy1(pc),d0		; 
		btst		#JPB_BTN_BLU,d0		; test blue button (joy 1)
		bne		_shared_sfx		; go to the same code for 2 button mode
		bra		_reset_sfx		; or don't


; =======	CD32 MENU SCREEN START-GAME / HIGHSCORES / CHEAT (RED / PLAY / COMBO)

_menu_cd32	bsr		_rewind_cd32		; test rwd button (joy 1)
		beq		.next				
		bsr		_forward_cd32		; test fwd button (joy 1)
		beq		.next
		bsr		_yellow_cd32		; test yellow button (joy 1)
		beq		.next
		jmp		$16966			; activate cheat
	
.next		bsr		_rewind_cd32		; test rwd button (joy 1)
		beq		.originals				
		bsr		_forward_cd32		; test fwd button (joy 1)
		beq		.originals
		bsr		_play_cd32		; test play button (joy 1)
		beq		.originals
		jmp		GameQuit		; quit game

.originals	bsr		_red_cd32		; test red button (joy 1)
		bne		.go			; pressed 
		bsr		_play_cd32		; test play button (joy 1)
		beq		.no			; no press
.scores		jmp		$F11A			; brings up highscore table :D
.go		move.b		#1,$3FEC4		; "fake" pressing button 1
.no		cmpi.b		#1,$3FEC4		; original code
.start		jmp		$168D0			; return to menu code (test for '1')



; =======	CD32 HIGHSCORE ENTRY (RED)

_highenter	bsr		_red_cd32
		bne		.fire
		tst.b		$4054C
		bne		.key
.go		jmp		$1093A
.key		jmp		$109B8
.fire		jmp		$10954


; =======	CD32 PAUSE, QUIT, LEVELSKIP (PLAY / YELLOW / BLUE)

_pause_cd32	movem.l		d0/a0,-(a7)		; preserve reg's
		lea		held_button(pc),a0	; link held_button + a0
		bsr		_play_cd32
		beq		.nopause

		btst		#JPB_BTN_PLAY,(a0)	; held_button 
		bne		.held	
		bset		#JPB_BTN_PLAY,(a0)	; held_button 
		move.b		#$40,$3FEC4		; 'fake' space-press
		waitvb
		bra		.held

.nopause	bclr		#JPB_BTN_PLAY,(a0)	; held_button = 0
.held		movem.l		(a7)+,d0/a0		; restore reg's
		cmpi.b		#$40,$3FEC4		; original code
		rts

_unpause_cd32	movem.l		d0/a0,-(a7)		; preserve reg's
		lea		held_button(pc),a0	; link held_button + a0
		bsr		_play_cd32
		beq		.nopause
		btst		#JPB_BTN_PLAY,(a0)	; held_button 
		bne		.held	
		bset		#JPB_BTN_PLAY,(a0)	; held_button 
		movem.l		(a7)+,d0/a0		; restore reg's
		clr.b		$3FEC4
		waitvb
		jmp		$105CA			; unpause it	

.nopause	bclr		#JPB_BTN_PLAY,(a0)	; held_button = 0
.held		movem.l		(a7)+,d0/a0		; restore reg's
		jmp		$105F2			; 

_quit_cd32	bsr		_yellow_cd32
		beq		.noquit
		move.b		#$45,$3FEC4		; 'fake' esc-press
.noquit		cmpi.b		#$45,$3FEC4		; original code
		rts

_levelskip_cd32	bsr		_blue_cd32
		beq		.noskip
		move.b		#$36,$3FEC4		; 'fake' N-press
.noskip		cmpi.b		#$36,$3FEC4		; original code
		rts

_restart_cd32	bsr		_green_cd32
		beq		.noskip
		move.b		#$28,$3FEC4		; 'fake' L-press
.noskip		cmpi.b		#$28,$3FEC4		; original code
		rts




; =======	NORMAL WEAPON CYCLE (SECOND BUTTON)
				
_weapon_2button	movem.l		d0/a0,-(a7)		; preserve reg's
		lea		held_button(pc),a0	; link held_button + a0

		btst.b		#14-8,$DFF016		; test second button (joy 1)
		bne.b		.reset			; if not true, skip and reset

		btst 		#JPB_BTN_BLU,(a0)	; already pressed?
		bne		_weapon_skip		; skip it
		bset		#JPB_BTN_BLU,(a0)	; held_button = true
		movem.l		(a7)+,d0/a0		; restore reg's		
		bsr		_weapon_up
		bra		_weapon_change		; goto weapon change

.reset		bclr		#JPB_BTN_BLU,(a0)	; held_button = false		
		bra		_weapon_skip


; =======	CD32 WEAPON CYCLE (REVERSE / FORWARD)

_weapon_cd32	movem.l		d0/a0,-(a7)		; preserve reg's
		lea		held_button(pc),a0	; link held_button + a0

		move.l		joy1(pc),d0		; get CD32 buttons

		btst		#JPB_BTN_FORWARD,d0	; test fwd button (joy 1)
		beq		.next			; not pressed
		btst 		#JPB_BTN_FORWARD,(a0)	; already pressed?
		bne		.skip			; skip it
		bset		#JPB_BTN_FORWARD,(a0)	; held_button = true
		movem.l		(a7)+,d0/a0		; restore reg's		
		bsr		_weapon_up		; move up a weapon
		bra 		_weapon_change		; change it
		bra		.skip			; move out of here
.next		bclr		#JPB_BTN_FORWARD,(a0)	; held_button = false

.skip		btst		#JPB_BTN_REVERSE,d0	; test rwd button (joy 1)
		beq		.none			; not pressed
		btst 		#JPB_BTN_REVERSE,(a0)	; already pressed?
		bne		.exit			; skip it
		bset		#JPB_BTN_REVERSE,(a0)	; held_button = true
		movem.l		(a7)+,d0/a0		; restore reg's		
		bsr		_weapon_down		; move up a weapon
		bra 		_weapon_change		; change it
		bra		.exit			; move out of here
.none		bclr		#JPB_BTN_REVERSE,(a0)	; held_button = false
.exit		bra		_weapon_skip		; we are out of here!


; =======	PICK-A-WEAPON!!!	

_weapon_change	jmp		$1023C			; goto weapon change


; =======	NO WEAPON PICKED	

_weapon_skip	movem.l		(a7)+,d0/a0		; restore reg's	
		bra 		_keys			; return to weapon input


; =======	CYCLE WEAPON UP	

_weapon_up	move.w  	$0003feb6,d0		; move current weapon to d0
		addi		#1,d0			; add one to d0
		cmpi.b 		#5,d0			; if not d0=5
		bne		.return			; goto start
		clr.w		d0			; if true make d0=0
.return		rts


; =======	CYCLE WEAPON DOWN	

_weapon_down	move.w  	$0003feb6,d0		; move current weapon to d0
		subi		#1,d0			; add one to d0
		cmpi.w 		#-1,d0			; if not d0=5
		bne		.return			; goto start
		move.w		#4,d0			; if true make d0=4
.return		rts


; =======	ORIGINAL IN-GAME WEAPONS KEYS (F1-F5)
		
_keys		cmpi.b		#$50,$0003FEC4		; original keyboard code
		blt		.exit
		cmpi.b		#$54,$0003FEC4
		bgt		.exit

		move.b		$0003FEC4,d0
		subi.b		#$50,d0
		jmp 		$1023C
.exit		jmp 		$10264


; =======	CD32 IN-GAME FIRE ROUTINE (GREEN FOR 'NORMAL' FIRE)

_fire_cd32	bsr		_second_cd32		; second weapon separately
		bsr		_red_cd32		; button for normal fire
		rts


; =======       CD32 KEEP COUNT OF THE 'FIRE' DELAY

_extra_cd32	cmpi.w		#5,$3fcee
		bgt		.go
.none		addq.w		#1,$3fcee
		jmp		$14BDC

.go		clr.w		$3FCEE
		jmp		$14BDC


; =======	CD32 IN-GAME FIRE ROUTINE (BLUE FOR SECOND WEAPON)

_second_cd32	bsr		_green_cd32
		beq		.nofire			; no firing
	
		tst.w		$3FCF0			; timer=0 
		bne		.blockfire		; if not, dont do it

		jsr 		$14BA6			; second weapon code ($14BA0)

.blockfire	addq.w		#1,$3FCf0		; timer=timer+1
		cmpi.w		#6,$3FCf0		; timer<6
		ble		.exit			; if not, dont clear it
.nofire		clr.w		$3FCF0			; reset the timer
.exit		rts





; =======	CD32 SHARED BUTTON ROUTINES 


_red_cd32	movem.l		d0/a0,-(a7)		; preserve reg's
		move.l		joy1(pc),d0		; get CD32 buttons		
		btst		#JPB_BTN_RED,d0		; test Green button (joy 1)
		movem.l		(a7)+,d0/a0		; restore reg's
		rts

_yellow_cd32	movem.l		d0/a0,-(a7)		; preserve reg's
		move.l		joy1(pc),d0		; get CD32 buttons		
		btst		#JPB_BTN_YEL,d0		; test Green button (joy 1)
		movem.l		(a7)+,d0/a0		; restore reg's
		rts

_green_cd32	movem.l		d0/a0,-(a7)		; preserve reg's
		move.l		joy1(pc),d0		; get CD32 buttons		
		btst		#JPB_BTN_GRN,d0		; test Green button (joy 1)
		movem.l		(a7)+,d0/a0		; restore reg's
		rts

_blue_cd32	movem.l		d0/a0,-(a7)		; preserve reg's
		move.l		joy1(pc),d0		; get CD32 buttons		
		btst		#JPB_BTN_BLU,d0		; test Green button (joy 1)
		movem.l		(a7)+,d0/a0		; restore reg's
		rts

_play_cd32	movem.l		d0/a0,-(a7)		; preserve reg's
		move.l		joy1(pc),d0		; get CD32 buttons		
		btst		#JPB_BTN_PLAY,d0	; test Green button (joy 1)
		movem.l		(a7)+,d0/a0		; restore reg's
		rts

_forward_cd32	movem.l		d0/a0,-(a7)		; preserve reg's
		move.l		joy1(pc),d0		; get CD32 buttons		
		btst		#JPB_BTN_FORWARD,d0	; test Forward button (joy 1)
		movem.l		(a7)+,d0/a0		; restore reg's
		rts

_rewind_cd32	movem.l		d0/a0,-(a7)		; preserve reg's
		move.l		joy1(pc),d0		; get CD32 buttons		
		btst		#JPB_BTN_REVERSE,d0	; test Rewind button (joy 1)
		movem.l		(a7)+,d0/a0		; restore reg's
		rts


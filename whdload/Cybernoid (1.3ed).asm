;*---------------------------------------------------------------------------
;  :Program.   	  CybernoidHD.asm
;  :Contents.  	  Slave for "Cybernoid" from
;  :Authors.	  Bored Seal & Hungry Horace
;  :History.   	  02.08.99 - V1
;		  30.03.08 - V1.2
;			     - Minor code cleaning
;			     - Load / Save scores (not if trainers used)
;			     - Moved files to /data/ folder
;			     - LMB wait changed to Joystick fire
;			     - Joystick Button 2 Support -  cycles weapon (game) toggles sfx (menu)
;			     - Trainers - Lives / Weapons				
;			     - Original cheat highscore saving failsafe
;		  04.05.10 - V1.3
;			     - 68000/NOVBRMOVE quitkey (excluding intro)
;			     - Bugfixed 2 button support
;			     - CD32 Pad Controls (CUSTOM2=1)
;			     - Skip titlescreen with LMB or Joystick Fire 
;			     - Tab to switch on cheat from menu
;		             - All Trainers on Custom1, now inc. timers and levelskip 
;			     - Removed 'Reset-Resistance'
;  :Requires.     -
;  :Copyright. 	  Public Domain
;  :Language.  	  68000 Assembler
;  :Translator.   BarFly
;  :Thanks.	  Wepl, JOTD and BippyM... 
;			all of whom have taught me so much - Horace
;		
;---------------------------------------------------------------------------*

	INCDIR	Includes:
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i

	IFD BARFLY
	OUTPUT	Cybernoid.slave
	BOPT	O+				;enable optimizing
	BOPT	OG+				;enable optimizing
	BOPT	ODd-				;disable mul optimizing
	BOPT	ODe-				;disable mul optimizing
	BOPT	w4-				;disable 64k warnings
	BOPT	wo-				;disable optimizer warnings
	SUPER
	ENDC

;USE_FASTMEM
CHIPMEMSIZE = $80000
EXPMEMSIZE = $0

;======================================================================

_base		SLAVE_HEADER				;ws_Security + ws_ID
		dc.w	15				;ws_Version
		dc.w	WHDLF_NoError|WHDLF_EmulTrap	;ws_flags

_upchip		IFD	USE_FASTMEM
		dc.l	CHIPMEMSIZE			;ws_BaseMemSize
		ELSE
		dc.l	CHIPMEMSIZE+EXPMEMSIZE
		ENDC
		
		dc.l	$0				;ws_ExecInstall
		dc.w	_start-_base			;ws_GameLoader
		dc.w	_dir-_base			;ws_CurrentDir
		dc.w	0				;ws_DontCache
_keydebug	dc.b	0				;ws_keydebug
_keyexit	dc.b	$5D				;ws_keyexit = '*'
		dc.l	0
		dc.w	_name-_base			;ws_name
		dc.w	_copy-_base			;ws_copy
		dc.w	_info-_base			;ws_info
_expmem	
		IFD	USE_FASTMEM	
		dc.l	EXPMEMSIZE			;ws_ExpMem
		ELSE
		dc.l	0
		ENDC
;============================================================================

	IFD BARFLY
	DOSCMD	"WDate  >T:date"
	ENDC


DECL_VERSION:MACRO
	dc.b	"1.3 mod"
	IFD BARFLY
		dc.b	" "
		INCBIN	"T:date"
	ENDC
	ENDM

_name		dc.b	"Cybernoid"
		dc.b	0
_copy		dc.b	"Hewson 1988",0
_info		dc.b	"Installed & fixed by Bored Seal",10
		dc.b	"Additions by Hungry Horace",10,10
		dc.b	"Version "
		DECL_VERSION
		dc.b	0
_dir		dc.b	"data",0
_savename	dc.b	"Cybernoid.highs",0
		even


; version xx.slave works

	dc.b	"$","VER: slave "
	DECL_VERSION
	dc.b	$A,$D,0
	even

_start		lea	(_resload,pc),a1
		move.l	a0,(a1)			;save for later using

		move.l	a0,a2		
		lea	(_tag,pc),a0
		jsr	(resload_Control,a2)	; grab those tags!

		lea	filename,a0
		lea	$20000,a1
		move.l	a1,$db4
		bsr	LoadFile		
				
		move.l	a1,a0
		move.l	a1,-(sp)	

		move.l	#36324,d0		; file length
		move.l  (_resload,pc),a2
	;	jsr     (resload_CRC16,a2)	
	; cmp.w	#$3978,d0		; CRC16 Check
	; bne	Unsupported

		movem.l	A2-A3,-(A7)		; save registers
		lea	TitleWait,a3		; link TitleWait
		lea	$20070,a2		; position of code
		move.w	#$4eb9,(a2)+		; add BSR
		move.l	a3,(a2)+		; add address
		move.l	#$4e71,(a2)+		; add NOP 
		movem.l	(A7)+,A2-A3		; restore registers

		move.l	(sp)+,a1
		move.w	#$4ef9,$1f2(a1)
						
		pea	LoadFile
		move.l	(sp)+,$1f4(a1)
		
		pea	Patch	
		move.l	(sp)+,$a4(a1)
					
		jmp	(a1)			; title screen

Patch	;	move.l 	a1,a3			; keep a1 for re-use.						
		lea	pl_2button,a0		; default patchlist
		move.l	custom2(pc),d0		; custom 2 check
		btst	#0,d0			; bit 1
		beq	.patch			; CD32 mode?
		lea	pl_cd32(pc),a0		; CD32 patchlist
.patch		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)

		move.w	#$4ef9,$25a		;
		pea	Fix			; Bored Seal Fixes
		move.l	(sp)+,$25c		;

	;	move.w	#$4A39,$1035C		; cheap way of dieing fast (testing)

		bsr	Trainers
		bsr	LoadScore		; load scoretable
		
		jmp	$ee8c			; game start

; =======	PATCHLISTS (HH)

pl_cd32		PL_START				; *** CD32 Pad Patchlist
		PL_NOP		$1C674,2		; 
		PL_PS		$1C676,_cd32_read	; Read CD32 buttons in VBI
		PL_PS		$F388,_red_cd32		; Continue from level end
		PL_NOP		$F38E,$2		;
		PL_PS		$F46A,_red_cd32		; Game completion
		PL_NOP		$F470,$2		; 
		PL_B		$F472,$67		; Invert button test
		PL_PS		$101CE,_red_cd32	; Game Over wait
		PL_NOP		$101D4,$2		;
		PL_PS		$101DE,_red_cd32	; Game Over wait
		PL_NOP		$101E4,$2		;
		PL_P  		$1021A,_weapon_cd32	; Weapon changing in-game
		PL_P		$10942,_highenter	; High-score entry
		PL_NOP		$10948,$2
	;	PL_PS		$1094A,_red_cd32	; High-score entry (skipped)
	;	PL_NOP		$10950,$2		;
	;	PL_PS		$109d4,_red_cd32	; High-score controls u/d/l/r
	;	PL_NOP		$109dA,2 		;
		PL_PS		$105CC,_pause_cd32	; Pause the game
		PL_NOP		$105D2,2		;
		PL_PS		$105DC,_quit_cd32	; Quit the game (whilst paused)
		PL_NOP		$105E2,2		;
		PL_P		$105E8,_unpause_cd32	; Resume the game after pausing
		PL_NOP		$105EE,$4		
		PL_PS		$105FC,_levelskip_cd32	; Skip Level (whilst paused & cheat enabled)
		PL_NOP		$10602,2		;
		PL_PS		$1063C,_restart_cd32	; Restart Level (whilst paused & cheat enabled)
		PL_NOP		$10642,2		;
	;	PL_PS		$10654,_pause_cd32	; Pause the game (redundant check?)
	;	PL_NOP		$1065A,2
		PL_PS		$14B78,_fire_cd32	; fire buttons check
		PL_NOP		$14B7E,$2		; extraneous bytes
		PL_NOP		$14B8A,$8		; relocated code
		PL_NOP		$14B92,$4		; relocated code
		PL_P		$14B8A,_extra_cd32	; first weapon time-delay
		PL_PS		$14BC0,_red_cd32	; first weapon double-check
		PL_NOP		$14BC6,$2		; extraneous bytes
		PL_R		$14BBE			; RTS

	;	PL_PS		$167C2,_red_cd32	; Game start (not required)
	;	PL_NOP		$167C8,$2
		PL_PS		$16810,_play_cd32	; Return from high-score table view
		PL_NOP		$16816,$2
		PL_NOP		$168AC,6
		PL_P  		$168B2,_sfx_cd32	; Press '2' on main menu (SFX Toggle)
		PL_P		$168C8,_menu_cd32	; Press '1' on main menu (Start Game)
		PL_NOP		$168CE,2		; 
		PL_NEXT		pl_patches

pl_2button	PL_START				; *** 2 Button Control (default) patchlist
		PL_P  		$1021A,_weapon_2button	; re-direct the in-game keyboard input
		PL_P  		$168AC,_sfx_2button	; Patch button 2 on main menu
		PL_NEXT		pl_patches

pl_patches	PL_START				
		PL_L 		$1C036,$4EB8025A	; *** Bored Seal's Fixes
		PL_L 		$1C06E,$4EB8025A	; *** Bored Seal's Fixes
		PL_L		$1C1D2,$4EB8025A	; *** Bored Seal's Fixes
		PL_W		$101EA,$4A80		; permanent wait on game-end
		PL_PS 	 	$16AFE,SaveScore	; re-direct after name entry
		PL_NOP		$1C5D0,2		; 
		PL_PS		$1C5D2,GameKBD		; 68000/NOVBRMOVE quitkey
		PL_NOP		$10B8C,$A		; Remove game from staying resident in memory
		PL_END



; =======	FIXES AND LOAD-ROUTINE (BORED SEAL)

Fix		move.l		d0,-(sp)		;fix 24bit faults
		move.l		a6,d0
		and.l		#$7FFFF,d0
		move.l		d0,a6
		move.l		(sp)+,d0
		tst.l		-2(a6)
		rts
		
LoadFile	movem.l		d0-d2/a0-a2,-(sp)
		movea.l		$db4,a1
		move.l		(_resload,pc),a2
		jsr		(resload_LoadFile,a2)
		movem.l		(sp)+,d0-d2/a0-a2
		rts

Unsupported	pea		TDREASON_WRONGVER
_end		move.l		(_resload),-(a7)
		add.l		#resload_Abort,(a7)
		rts

; =======	CD32 CONTROLS (HH)

		include		readjoypad.s
		include		CD32extra.s

; =======	TITLE SCREEN WAIT (HH)

TitleWait	btst		#6,$bfe001		; check mouse
		beq		.exit
		btst		#7,$bfe001		; check joyfire
		bne		TitleWait
.exit		rts


; =======	68000/NOVBRMOVE QUITKEY (HH)

GameKBD		cmp.b		_keyexit(pc),D0
		bne		NoQuit
GameQuit	pea		TDREASON_OK
		move.l		_resload(pc),-(a7)
		addq.l		#resload_Abort,(a7)
NoQuit		move.b		#$40,$BFEE01
		rts


; =======	LOAD / SAVE SCOREBOARD (HH)
	
LoadScore	movem.l		D0-A6,-(A7)			; save registers

		lea		(_savename,pc),A0
		move.l		(_resload,pc),a2
		jsr		(resload_GetFileSize,a2)	; get highscore filesize
		tst.l		d0				; check exists
		beq		.skip				; skip loadscore

		move.l		_resload(PC),A2
		move.l		#$A0,D0				;data length
		moveq.l		#0,D1				;offset of zero
		lea		_savename(pc),A0		;filename
		lea		$3FBF0,A1			;position of table
	
		jsr		(resload_LoadFileOffset,a2)	; Load scores

.skip		movem.l		(A7)+,D0-A6			; register restore
		rts

SaveScore	move.b		(a1)+,(a0)+			; small section of original
		dbf		d0,SaveScore			; scoreboard routine

		move.l		custom1(pc),d0			; custom 1			;
		tst.l  		d0				; if used
		bne		.skip				; skip

		cmp.b		 #$ff,$4077F			; Check in-game cheat is not active
		bne		.skip				; dont save if it is
		movem.l		D0-A6,-(A7)			; save registers
	
		move.l		_resload(PC),A2
		move.l		#$A0,D0				;data length
		moveq.l		#0,D1				;offset of zero
		lea		_savename(pc),A0		;filename
		lea		$3FBF0,A1			;postion of table
		jsr		(resload_SaveFileOffset,a2)	

		movem.l		(A7)+,D0-A6			; register restore

.skip 		rts						; goto normal score-entry end


; =======	TRAINERS (HH)

Trainers:	move.l	custom1(pc),d0		; Read CUSTOM1 tooltype	
		btst 	#0,d0			; Lives trainer Tooltype custom1 bit 0
		beq	.nolives		; skip
		move.w	#$4A79,$1035C		; infinite lives

.nolives	btst	#1,d0			; Weapons trainer tooltype custom1 bit 1 
		beq	.noweapons		; skip
		move.w	#$4A39,$1562A		; infinite bombs
		move.w	#$4A39,$1580C		; infinite mines
		move.w	#$4A39,$157FA		; infinite mines (increase)
		move.w	#$4A39,$1588A		; infinite shields
		move.w	#$4A39,$158B4 		; infinite bounce
		move.w	#$4A39,$156D8		; infinite seeker

.noweapons	btst	#2,d0			; level-timer tooltype custom1 bit 2 
		beq	.notimer1		; skip

		move.w	#$4A79,$100FC		; timer sub
		move.w	#$4A79,$10102		; timer sub
 
.notimer1	btst	#3,d0			; screen-timer tooltype custom1 bit 3
		beq	.notimer2		; skip
		move.w	#$4A79,$100CA		; timer sub

.notimer2	btst	#4,d0			; level-skip tooltype custom1 bit 4
		beq	.exit			; skip

		move.l	#$6008,$105F2		; 'jump over' the cheat-check code
		move.w	#$4EF9,$105F4		; add a JMP...
		move.l	#$0000F40A,$105F6	; Éto the address of the outro
		move.w	#$4E71,$105FA		; NOP the remaining code
		move.w	#$67E2,$10610		; change the cmp 3 to jump to game exit
		
.exit		rts
	
		

; =======	TAGS ETC

_resload	dc.l		0			;address of resident loader
_tag		dc.l		WHDLTAG_CUSTOM1_GET	; Trainers
custom1		dc.l		0
		dc.l		WHDLTAG_CUSTOM2_GET	; CD32 pad patch
custom2		dc.l		0
		dc.l		TAG_DONE,TAG_DONE
held_button	dc.l		0					
filename	dc.b		"BOOT",0
		EVEN

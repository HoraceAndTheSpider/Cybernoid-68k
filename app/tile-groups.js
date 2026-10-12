/* Predefined tile arrangements, supported by original GAME map occurrences or proved compound footprints.
   Each `occurrences` figure is an exact 2×2 raw-map scan of the GAME on master at 12 Oct 2026,
   including overlapping matches. These are decorative *patterns*, not proof of one engine entity.
   Structural object arrangements are reference-only until validated semantic placement exists. */
(() => { 'use strict';
const GROUPS=[
 {id:'weave-l1',kind:'recurring',name:'Four-tile weave',level:'Mostly Level 1',width:2,height:2,tiles:[0x003,0x006,0x004,0x005],occurrences:219,rooms:20,source:'L1 physical room 0, tile (12,4)'},
 {id:'weave-l23',kind:'recurring',name:'Speckled background',level:'Levels 2–4',width:2,height:2,tiles:[0x048,0x04A,0x049,0x048],occurrences:114,rooms:57,source:'L2 physical room 2, tile (10,2)'},
 {id:'panel-a',kind:'recurring',name:'Golden wall panel A',level:'Level 4',width:2,height:2,tiles:[0x1A9,0x1AA,0x1AB,0x1AC],occurrences:38,rooms:10,source:'L4 physical room 8, tile (16,0)'},
 {id:'panel-b',kind:'recurring',name:'Golden wall panel B',level:'Level 4',width:2,height:2,tiles:[0x1B5,0x1B6,0x1B7,0x1B8],occurrences:34,rooms:12,source:'L4 physical room 5, tile (4,8)'},
 {id:'panel-c',kind:'recurring',name:'Golden wall panel C',level:'Level 4',width:2,height:2,tiles:[0x1AD,0x1AE,0x1AF,0x1B0],occurrences:29,rooms:11,source:'L4 physical room 4, tile (18,2)'},
 {id:'upper-detail',kind:'recurring',name:'Upper wall detail',level:'Level 1',width:2,height:2,tiles:[0x0DB,0x0DC,0x0E5,0x0E6],occurrences:23,rooms:15,source:'L1 physical room 5, tile (4,0)'},
 {id:'block-2x2',kind:'entity',name:'2×2 destructible block',width:2,height:2,tiles:[0x242,0x243,0x244,0x245],source:'Entity anchor $242',locked:true},
 {id:'block-2x3',kind:'entity',name:'2×3 destructible block',width:2,height:3,tiles:[0x232,0x233,0x234,0x235,0x236,0x237],source:'Entity anchor $232',locked:true},
 {id:'fixed-gun',kind:'entity',name:'Fixed gun',width:2,height:1,tiles:[0x31C,0x31D],source:'Entity anchor $31C',locked:true},
 {id:'right-gun',kind:'entity',name:'Right-facing gun',width:4,height:1,tiles:[0x326,0x327,0x328,0x329],source:'Entity anchor $329',locked:true},
 {id:'left-gun',kind:'entity',name:'Left-facing gun',width:4,height:1,tiles:[0x346,0x347,0x348,0x349],source:'Entity anchor $346 (alternative end-cap $359 exists)',locked:true}
];
window.CybernoidTileGroups=Object.freeze(GROUPS.map(g=>Object.freeze({...g,tiles:Object.freeze(g.tiles)})));
})();

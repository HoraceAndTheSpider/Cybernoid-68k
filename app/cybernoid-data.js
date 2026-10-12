/* Cybernoid HTML5 Editor — binary model. No Python or external services required.
   Source of layout constants: tools/cybernoid_project.py (project format v2).
   The loaded GAME is the source of truth: all unedited bytes stay untouched. */
(() => {
'use strict';
const DELTA=0xEE06, SIZE=383230, TILE_COUNT=961, TILE_BANK=0x1FBE8;
const W=20,H=11;
const ACTIVE=[
 [0,1,2,3,4,8,9,10,11,12,16,17,18,19,20],
 [0,1,2,3,4,5,8,9,10,11,12,13,16,17,18,19,20,21,24,25,26,27,28],
 Array.from({length:32},(_,i)=>i),
 Array.from({length:80},(_,i)=>i)
];
const CONFIG=[
 {level:1,count:15,slots:24,lookup:0x3FD66,map:0x4084A,stride:0x25A,active:ACTIVE[0]},
 {level:2,count:23,slots:32,lookup:0x3FD96,map:0x42228,stride:0x398,active:ACTIVE[1]},
 {level:3,count:32,slots:32,lookup:0x3FDD6,map:0x449B0,stride:0x500,active:ACTIVE[2]},
 {level:4,count:80,slots:80,lookup:null,map:0x480B0,stride:0x140,active:ACTIVE[3]}
];
const hex=(n,length=3)=>'$'+Number(n).toString(16).toUpperCase().padStart(length,'0');
const setOf=(string)=>new Set(string.trim().split(/\s+/).filter(Boolean).map(x=>parseInt(x,16)));
const PASSABLE=setOf(`000 001 002 003 004 005 006 008 00A 00B 00E 044 045 046 047 048 049 04A 04B 04C 04D 04E 09A 09B 09C 143 1D5 1D6 1D7 1D8 1D9 1DA 1DB 1DC 1DD 1DE 21B 257 258 259 25A 25B 25C 25D 25E 2D6 2D7 2D8 2D9 2DA 2DB 2DC 2DD 2DE 2DF 2E0 2E1 116 119 11A 11D 11E 30D 30E 30F`);
const DESTRUCTIBLE=setOf(`068 069 06B 0ED 232 233 234 235 236 237 242 243 244 245 300 066 062 064 063 065 05C 05D 05E 05F 210 30C 30D 30E 30F 116 117 118 119 11A 11D 11E`);
const SPECIAL=setOf(`02B 09F 1D5 1E0 1E1 1E2 1E3 1E4 1E5 1E6 1E7 1E8 1E9 1F0 1F1 1F2 1F3 1F4 1F5 1F6 1F7 1F8 1F9 1FA 1FC 1FD 1FE 1FF 200 232 242 24D 24E 2E2 2E6 2EE 300 30C 31C 324 325 329 346`);
for(let n=0x24D;n<=0x26E;n++)SPECIAL.add(n);
const LABELS=new Map(Object.entries({
 '2b':'START','9f':'Particle emitter','1d5':'Level 4 portal',
 '1e0':'RACT down','1e1':'RACT up','1e2':'ST down','1e3':'ED down','1e4':'ST left','1e5':'ED left',
 '1e6':'ST up','1e7':'ED up','1e8':'ST right','1e9':'ED right',
 '1f0':'RNET','1f1':'RNET','1f2':'Cybermace bonus','1f3':'Weapon bonus','1f4':'RNET','1f5':'RNET',
 '1f6':'ELE right','1f7':'ELE left','1f8':'ELE down','1f9':'ELE up','1fa':'Back fire bonus',
 '1fc':'Crawler left slow','1fd':'Crawler left fast','1fe':'Crawler right slow','1ff':'Crawler right fast',
 '200':'Mixed spawn pit','2e2':'Mixed spawn pit','232':'2×3 destructible','242':'2×2 destructible',
 '24d':'Two-cell animation','300':'Organic cannon','30c':'Large cannon','31c':'Fixed cannon',
 '324':'Landing pad left','325':'Landing pad right','329':'Right-facing gun','346':'Left-facing gun'
 }).map(([key,v])=>[parseInt(key,16),v]));
// Anchor-offset component relationships; only known owned cells are protected.
const COMPOUNDS={
 0x232:[[0,0,0x232],[1,0,0x233],[0,1,0x234],[1,1,0x235],[0,2,0x236],[1,2,0x237]],
 0x242:[[0,0,0x242],[1,0,0x243],[0,1,0x244],[1,1,0x245]],
 0x24D:[[0,0,0x24D],[1,0,0x24E]],
 0x300:[[0,0,0x300],[0,1,0x066],[-1,2,0x062],[0,2,0x064],[1,2,0x063],[2,2,0x065],[-1,3,0x05C],[0,3,0x05D],[1,3,0x05E],[2,3,[0x05F,0x210]]],
 0x30C:[[0,0,0x30C],[-1,-1,0x116],[0,-1,0x117],[1,-1,0x118],[2,-1,0x119],[-1,0,0x11A],[1,0,0x30D],[2,0,0x11D],[-1,1,0x11E],[0,1,0x30E],[1,1,0x30F]],
 0x31C:[[0,0,0x31C],[1,0,0x31D]],
 0x329:[[-3,0,0x326],[-2,0,0x327],[-1,0,0x328],[0,0,0x329]],
 0x346:[[0,0,0x346],[1,0,0x347],[2,0,0x348],[3,0,[0x349,0x359]]],
 0x324:[[0,0,0x324],[1,0,0x325]],
};
const GENERIC=setOf(`09F 1D5 1E0 1E1 200 232 242 24D 2E2 2E6 2EE 300 30C 31C 329 346`);
for(let n=0x253;n<=0x26E;n++)GENERIC.add(n);
// Exactly those source controllers whose fixed-size Add rules are established in the
// original Python semantic operation layer. Unrecognised special values stay locked.
const ATOMIC_SINGLES=new Set([0x09F,0x1E0,0x1E1,0x200,0x2E2]);
for(let id=0x253;id<=0x26E;id++)ATOMIC_SINGLES.add(id);
const PLACEABLE_ANCHORS=new Set([0x232,0x242,0x24D,0x300,0x30C,0x31C,0x329,0x346]);
function footprint(id,x,y){return (COMPOUNDS[id]||[]).map(([dx,dy,options])=>({x:x+dx,y:y+dy,id:Array.isArray(options)?options[0]:options}));}
function semanticGroupPolicy(tiles,w,h){
 if(!Number.isInteger(w)||!Number.isInteger(h)||w<1||h<1||w>W||h>H||!Array.isArray(tiles)||tiles.length!==w*h)return{ok:false,reason:'Invalid group dimensions.'};
 let semantic=false;
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const id=tiles[y*w+x];if(!Number.isInteger(id)||id<0||id>=TILE_COUNT)return{ok:false,reason:'Group contains a value outside the tile bank.'};
  if(PLACEABLE_ANCHORS.has(id)){
   semantic=true;
   for(const cell of footprint(id,x,y)){
    if(cell.x<0||cell.y<0||cell.x>=w||cell.y>=h)return{ok:false,reason:`${hex(id)} needs its complete object footprint.`};
    const v=tiles[cell.y*w+cell.x],accepted=(COMPOUNDS[id].find(([dx,dy])=>dx===cell.x-x&&dy===cell.y-y)||[])[2];
    if(!(Array.isArray(accepted)?accepted.includes(v):accepted===v))return{ok:false,reason:`${hex(id)} has an incorrect component at (${cell.x},${cell.y}).`};
   }
  }else if(ATOMIC_SINGLES.has(id))semantic=true;
  else if(SPECIAL.has(id)){
   // $24E is a required subordinate cell, never a standalone animation source.
   if(id===0x24E&&x>0&&tiles[y*w+x-1]===0x24D)continue;
   return{ok:false,reason:`${hex(id)} needs a different semantic editor or is a runtime-only frame.`};
  }
 }
 return{ok:true,semantic,reason:''};
}
function isSemanticSelection(id){return ATOMIC_SINGLES.has(id)||PLACEABLE_ANCHORS.has(id)||SPECIAL.has(id);}
const ANOMALIES=new Map([['4:40:2:10',0x086F],['4:44:5:8',0xB087],['4:44:6:8',0x8D26],['4:47:18:9',0x0F4B]]);
function colorClass(value,level){if(level===4&&value>=0x257&&value<=0x25E)return 'hazard';if(DESTRUCTIBLE.has(value))return 'destructible';if(SPECIAL.has(value))return 'special';return PASSABLE.has(value)?'passable':'solid';}
function tileInfo(value,level){const special=SPECIAL.has(value),destructible=DESTRUCTIBLE.has(value),passable=PASSABLE.has(value);
return {value,hex:hex(value,4),name:LABELS.get(value)||((value>=0x253&&value<=0x26E)?'Animation / energy field':(value>=TILE_COUNT?'Unresolved raw word':'Ordinary graphic tile')),
 category:colorClass(value,level),special,destructible,passable,collision:(level===4&&value>=0x257&&value<=0x25E)?'Lethal / blocking in Level 4':special?(passable?'Passable + runtime effect':'Runtime-controlled'):(passable?'Passable':'Solid'),
 note:value>=TILE_COUNT?'Outside the normal tile bank: preserve raw data.':(special?'Controller or animation source word; use validated semantic placement where supported.':'')};}
function crc32(bytes){let c=0xFFFFFFFF;for(const b of bytes){c^=b;for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xEDB88320:0);}return ((c^0xFFFFFFFF)>>>0).toString(16).padStart(8,'0');}
class Game {
 constructor(buffer,filename){if(buffer.byteLength!==SIZE)throw Error(`Unsupported file size: ${buffer.byteLength} bytes (expected ${SIZE}).`);
  this.original=new Uint8Array(buffer).slice();this.bytes=this.original.slice();this.dv=new DataView(this.bytes.buffer);this.filename=filename;this.id=crc32(this.original);
  this.undoStack=[];this.redoStack=[];this.changeCount=0;
  for(let i=0;i<3;i++){const addr=0x3FD4E+i*8;if(this.u32(addr)!==CONFIG[i].lookup||this.u32(addr+4)!==CONFIG[i].map)throw Error(`Level ${i+1} descriptor differs from the documented GAME profile. No edits made.`);}
  for(let i=0;i<4;i++)if(this.u32(0x3FFC0+i*4)!==CONFIG[i].stride)throw Error(`Level ${i+1} row stride differs from known source; this binary profile is not yet supported.`);
  this.layouts=CONFIG.map(cfg=>({...cfg,activeSet:new Set(cfg.active),physicalByLogical:Array.from({length:cfg.slots},(_,i)=>cfg.lookup!==null?this.u16(cfg.lookup+2*i):i)}));
 }
 offset(addr){const o=addr-DELTA;if(o<0||o+1>=this.bytes.length)throw Error(`Out-of-file runtime access ${hex(addr,6)}`);return o;}
 u16(addr){return this.dv.getUint16(this.offset(addr),false);}
 u32(addr){return this.dv.getUint32(this.offset(addr),false);}
 setU16(addr,v){this.dv.setUint16(this.offset(addr),v,false);}
 layout(level){return this.layouts[level-1];}
 physical(level,logical){const cfg=this.layout(level);return cfg.activeSet.has(logical)?cfg.physicalByLogical[logical]:null;}
 logicalForPhysical(level,p){const cfg=this.layout(level);return cfg.active.filter(i=>cfg.physicalByLogical[i]===p);}
 roomAddress(level,p,x,y){const c=this.layout(level);if(p<0||p>=c.count||x<0||x>=W||y<0||y>=H)throw Error('Room coordinate outside supported range.');return c.level===4?c.map+(p>>3)*0xDC0+(p&7)*0x28+y*0x140+x*2:c.map+p*0x28+y*c.stride+x*2;}
 cell(level,p,x,y){return this.u16(this.roomAddress(level,p,x,y));}
 room(level,p){const rows=[];for(let y=0;y<H;y++){const row=[];for(let x=0;x<W;x++)row.push(this.cell(level,p,x,y));rows.push(row);}return rows;}
 palette(level,useA=false){const base=useA?0x3FFD0:0x3FFF0;const words=Array.from({length:16},(_,i)=>this.u16(base+2*i));if(level===4&&!useA)for(let i=0;i<8;i++)words[i]=this.u16(0x1CD10+2*i);return words.map(w=>`rgb(${((w>>8)&15)*17},${((w>>4)&15)*17},${(w&15)*17})`);}
 tileIndices(tileId){const out=new Uint8Array(256);if(tileId<0||tileId>=TILE_COUNT)return out;const addr=TILE_BANK+tileId*0x80;for(let y=0;y<16;y++)for(let plane=0;plane<4;plane++){const bits=this.u16(addr+y*8+plane*2);for(let x=0;x<16;x++)out[y*16+x]|=((bits>>(15-x))&1)<<plane;}return out;}
 protected(level,p){const r=this.room(level,p),lock=new Set();for(let y=0;y<H;y++)for(let x=0;x<W;x++){const v=r[y][x];if(SPECIAL.has(v)||v>=TILE_COUNT)lock.add(y*W+x);const fp=COMPOUNDS[v];if(fp)for(const [dx,dy] of fp){let px=x+dx,py=y+dy;if(px>=0&&px<W&&py>=0&&py<H)lock.add(py*W+px);}}
 return lock;}
 validatePaint(level,p,x,y,to){
  if(!Number.isInteger(to)||to<0||to>=TILE_COUNT)return 'Selected ID is outside the tile bank.';
  if(SPECIAL.has(to))return 'Choose Pencil for supported special/animated objects; other controls are protected.';
  if(this.protected(level,p).has(y*W+x))return 'This cell belongs to a protected control marker or compound entity.';
  return null;}
 // Placement is planned without mutating the live binary; semantic anchors expand
 // into complete footprints. The caller can preview, then commit one transaction.
 planPlacement(level,p,x,y,selection){
  const spec=Array.isArray(selection?.tiles)?selection:{tiles:[selection],width:1,height:1};
  const group=Array.isArray(selection?.tiles);let placement=[];let policy;
  if(group){policy=semanticGroupPolicy(spec.tiles,spec.width,spec.height);
   if(!policy.ok)throw Error(policy.reason);
   for(let yy=0;yy<spec.height;yy++)for(let xx=0;xx<spec.width;xx++)placement.push({x:x+xx,y:y+yy,after:spec.tiles[yy*spec.width+xx]});
  }else if(PLACEABLE_ANCHORS.has(selection)){
   policy={ok:true,semantic:true};placement=footprint(selection,x,y).map(q=>({...q,after:q.id}));
  }else if(ATOMIC_SINGLES.has(selection)){
   policy={ok:true,semantic:true};placement=[{x,y,after:selection}];
  }else throw Error(`${hex(selection)} is not an independently placeable special tile.`);
  for(const q of placement){if(q.x<0||q.x>=W||q.y<0||q.y>=H)throw Error('Object would extend beyond the room edge.');}
  const changes=placement.map(q=>({level,p,x:q.x,y:q.y,before:this.cell(level,p,q.x,q.y),after:q.after}));
  this.validateTransaction(changes);
  return{changes,semantic:policy.semantic};
 }
 // Used for direct edits, native atomic stamps AND imported JSON. No path may
 // bypass the protected-cell checks or create half a compound mechanism.
 validateTransaction(changes){
  const unique=new Set(),byRoom=new Map();
  for(const c of changes){
   const cfg=this.layout(c.level);
   if(!cfg||!Number.isInteger(c.p)||c.p<0||c.p>=cfg.count||!Number.isInteger(c.x)||!Number.isInteger(c.y)||c.x<0||c.x>=W||c.y<0||c.y>=H)throw Error('Edit location is outside the physical room.');
   if(!Number.isInteger(c.after)||c.after<0||c.after>=TILE_COUNT)throw Error('Edit tile ID outside the known graphics bank.');
   const key=`${c.level}:${c.p}:${c.x}:${c.y}`;
   if(unique.has(key))throw Error(`Repeated edit at ${key}.`);unique.add(key);
   const before=this.cell(c.level,c.p,c.x,c.y);
   if(before!==c.before)throw Error(`Edit ${key} expects ${hex(c.before,4)}, found ${hex(before,4)}.`);
   if(before===c.after)continue;
   if(this.protected(c.level,c.p).has(c.y*W+c.x))throw Error(`Protected source object at Level ${c.level}, physical room ${c.p}, (${c.x},${c.y}).`);
   if(SPECIAL.has(c.after)&&!ATOMIC_SINGLES.has(c.after)&&!PLACEABLE_ANCHORS.has(c.after)&&c.after!==0x24E)throw Error(`${hex(c.after)} is not a supported source placement.`);
   const roomKey=`${c.level}:${c.p}`;
   if(!byRoom.has(roomKey))byRoom.set(roomKey,{level:c.level,p:c.p,edits:[],hasSemantic:false});
   const entry=byRoom.get(roomKey);entry.edits.push(c);
   if(SPECIAL.has(c.after))entry.hasSemantic=true;
  }
  for(const entry of byRoom.values()){
   const {level,p,edits}=entry;
   const rows=this.room(level,p),seen=new Set();
   // An atomic semantic stamp can replace any ordinary (non-protected) tile.
   // No pre-clearing is performed: the entire footprint is validated first, and
   // original words remain available for Undo and source-bound edits imports.
   for(const c of edits){
    rows[c.y][c.x]=c.after;seen.add(c.y*W+c.x);
   }
   for(const c of edits){const id=rows[c.y][c.x];
    if(id===0x200||id===0x2E2){if(level!==4)throw Error('Mixed spawn pits can only be placed in Level 4.');}
    if(id===0x24E&&!(c.x>0&&rows[c.y][c.x-1]===0x24D))throw Error('$24E must be the right-hand cell of a $24D animation pair.');
    if(PLACEABLE_ANCHORS.has(id))for(const [dx,dy,allow] of COMPOUNDS[id]){
     const xx=c.x+dx,yy=c.y+dy,v=xx>=0&&xx<W&&yy>=0&&yy<H?rows[yy][xx]:null;
     if(!(Array.isArray(allow)?allow.includes(v):v===allow))throw Error(`${hex(id)} requires its complete footprint (missing ${hex(Array.isArray(allow)?allow[0]:allow)} at offset ${dx},${dy}).`);
     // All owned parts must be added atomically, even if visually present already.
     if(!seen.has(yy*W+xx))throw Error(`${hex(id)} must be placed with every required cell in one operation.`);
    }
   }
   let used=0;for(const row of rows)for(const id of row)if(GENERIC.has(id))used++;
   if(used>56)throw Error(`Level ${level}, physical room ${p}: ${used}/56 generic controllers would exceed the runtime limit.`);
  }
  return true;
 }
 commit(changes){const unique=new Map();for(const c of changes){const key=`${c.level}:${c.p}:${c.x}:${c.y}`;if(!unique.has(key))unique.set(key,{...c});else unique.get(key).after=c.after;}
  const edits=[...unique.values()].filter(c=>c.before!==c.after);if(!edits.length)return false;
  this.validateTransaction(edits);
  for(const c of edits)this.setU16(this.roomAddress(c.level,c.p,c.x,c.y),c.after);
  this.undoStack.push(edits);this.redoStack.length=0;this.recount();return true;}
 recount(){let n=0;for(let i=0;i<this.bytes.length;i++)if(this.original[i]!==this.bytes[i])n++;this.changeCount=n;}
 undo(){const ops=this.undoStack.pop();if(!ops)return false;for(const c of ops)this.setU16(this.roomAddress(c.level,c.p,c.x,c.y),c.before);this.redoStack.push(ops);this.recount();return true;}
 redo(){const ops=this.redoStack.pop();if(!ops)return false;for(const c of ops)this.setU16(this.roomAddress(c.level,c.p,c.x,c.y),c.after);this.undoStack.push(ops);this.recount();return true;}
 diffs(){const r=[];for(const cfg of this.layouts)for(let p=0;p<cfg.count;p++)for(let y=0;y<H;y++)for(let x=0;x<W;x++){const a=this.roomAddress(cfg.level,p,x,y),off=this.offset(a);const before=(this.original[off]<<8)|this.original[off+1],after=this.u16(a);if(before!==after)r.push({level:cfg.level,p,x,y,before,after});}return r;}
 patchJSON(){return {format:'cybernoid-html5-edits',version:1,source_crc32:this.id,source_size:SIZE,edits:this.diffs()};}
 importPatch(obj){if(obj?.format!=='cybernoid-html5-edits'||obj.version!==1)throw Error('This is not a Cybernoid HTML5 edits file v1.');
  if(obj.source_crc32!==this.id||obj.source_size!==SIZE)throw Error('Edits were saved against a different source GAME; no changes imported.');
  if(!Array.isArray(obj.edits))throw Error('Missing edits array.');const ops=[];const visited=new Set();
  for(const c of obj.edits){if(![c.level,c.p,c.x,c.y,c.before,c.after].every(Number.isInteger))throw Error('Invalid edits record.');const cfg=this.layout(c.level);if(!cfg||c.p<0||c.p>=cfg.count||c.x<0||c.x>=W||c.y<0||c.y>=H)throw Error('Edit outside a room.');const k=`${c.level}:${c.p}:${c.x}:${c.y}`;if(visited.has(k))throw Error('Duplicate edit coordinate.');visited.add(k);
   const at=this.cell(c.level,c.p,c.x,c.y);if(at!==c.before)throw Error(`Edit ${k} expects ${hex(c.before,4)} but current tile is ${hex(at,4)}.`);
   ops.push({...c});}
  this.commit(ops);return ops.length;}
 // An intentionally bounded structural audit; original code remains the full legacy reference.
 audit(){const errors=[];const warnings=[];const err=(level,p,x,y,detail)=>errors.push({level,p,x,y,detail});
  for(const cfg of this.layouts){for(const logical of cfg.active){const p=cfg.physicalByLogical[logical];if(!Number.isInteger(p)||p<0||p>=cfg.count)err(cfg.level,p,null,null,`Logical room ${logical} points outside physical allocation.`);}}
  for(const cfg of this.layouts){let starts=[],pads=[];
   for(let p=0;p<cfg.count;p++){
    const r=this.room(cfg.level,p);let controllers=0;
    for(let y=0;y<H;y++)for(let x=0;x<W;x++){
      const v=r[y][x];if(v===0x02B)starts.push([p,x,y]);if(v===0x324||v===0x325)pads.push([p,x,y,v]);
      if(GENERIC.has(v))controllers++;
      if(v>=TILE_COUNT && ANOMALIES.get(`${cfg.level}:${p}:${x}:${y}`)!==v)err(cfg.level,p,x,y,`Unrecognised out-of-range source word ${hex(v,4)}.`);
      const fp=COMPOUNDS[v];if(fp)for(const[dx,dy,expect]of fp){const xx=x+dx,yy=y+dy,got=xx>=0&&xx<W&&yy>=0&&yy<H?r[yy][xx]:null;const expected=Array.isArray(expect)?expect:[expect];if(!expected.includes(got))err(cfg.level,p,x,y,`${LABELS.get(v)||hex(v)} requires ${expected.map(z=>hex(z)).join('/')} at offset (${dx},${dy}); found ${got===null?'outside room':hex(got,4)}.`);}
    }
    if(controllers>56)err(cfg.level,p,null,null,`${controllers} generic controllers exceed the safe 56-record pool.`);
    // Compare matching ELE endpoints on each row/column; original ST/ED markers are NOT conventional pairs.
    let roomElePairs=0;
    for(const [a,b,horiz] of [[0x1F6,0x1F7,true],[0x1F8,0x1F9,false]]){
      const starts=[],ends=[];for(let y=0;y<H;y++)for(let x=0;x<W;x++){if(r[y][x]===a)starts.push([x,y]);if(r[y][x]===b)ends.push([x,y]);}
      starts.sort((u,v)=>horiz?u[1]-v[1]||u[0]-v[0]:u[0]-v[0]||u[1]-v[1]);const left=ends.slice();let pairs=0;
      for(const [x,y] of starts){const idx=left.findIndex(([ex,ey])=>horiz?(ey===y&&ex>x):(ex===x&&ey>y));if(idx<0)err(cfg.level,p,x,y,`Unmatched ${hex(a)} endpoint.`);else{left.splice(idx,1);pairs++;}}
      for(const [x,y] of left)err(cfg.level,p,x,y,`Unmatched ${hex(b)} endpoint.`);
      roomElePairs+=pairs;
    }
    if(roomElePairs>5)err(cfg.level,p,null,null,`${roomElePairs} ELE pairs exceed the combined five-pair runtime limit.`);
   }
   if(starts.length!==1)err(cfg.level,null,null,null,`Expected exactly one START marker; found ${starts.length}.`);
   else{const [p,x,y]=starts[0],logical=this.u16(0x3FFB8+2*(cfg.level-1));if(cfg.physicalByLogical[logical]!==p||!cfg.activeSet.has(logical))err(cfg.level,p,x,y,`START marker does not match the logical start-room table (${logical}).`);}
   const padLeft=pads.find(z=>z[3]===0x324),padRight=pads.find(z=>z[3]===0x325);
   if(pads.length!==2||!padLeft||!padRight||padLeft[0]!==padRight[0]||padLeft[2]!==padRight[2]||padLeft[1]+1!==padRight[1])err(cfg.level,null,null,null,'Landing pad must be one adjacent $324/$325 pair.');
  }
  const marks=new Set();for(let p=0;p<80;p++)for(let y=0;y<H;y++)for(let x=0;x<W;x++)if(this.cell(4,p,x,y)===0x1D5)marks.add(`${p}:${x}:${y}`);
  const records=new Set();for(let i=0;i<8;i++){const a=0x1659E+i*12;const p=this.u16(a),tx=this.u16(a+2),ty=this.u16(a+4),dest=this.u16(a+6),dx=this.u16(a+8),dy=this.u16(a+10);
    const x=(tx-32)/16,y=(ty-24)/16,k=`${p}:${x}:${y}`;if(!Number.isInteger(x)||!Number.isInteger(y)||x<0||x>=W||y<0||y>=H||!marks.has(k))err(4,p,x,y,`Portal record ${i} does not match a source marker.`);
    if(records.has(k))err(4,p,x,y,`Portal record ${i} duplicates a trigger.`);records.add(k);
    const destX=(dx-32)/16,destY=(dy-24)/16;if(dest>=80||!Number.isInteger(destX)||!Number.isInteger(destY)||destX<0||destX>=W||destY<0||destY>=H)err(4,p,x,y,`Portal record ${i} destination is outside the room grid.`);
  }
  if(marks.size!==8)err(4,null,null,null,`Expected 8 Level-4 portal markers, found ${marks.size}.`);
  // No existing runtime-quirk layouts are normalised, including ED-only or RNET/CRP excess.
  return {errors,warnings,ok:errors.length===0};}
 exportBytes(){return this.bytes.slice();}
}
window.CybernoidData={Game,SIZE,TILE_COUNT,WIDTH:W,HEIGHT:H,CONFIG,hex,tileInfo,colorClass,PASSABLE,SPECIAL,ATOMIC_SINGLES,PLACEABLE_ANCHORS,semanticGroupPolicy,isSemanticSelection};
})();

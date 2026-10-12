/* Browser UI: three-column workspace with topological navigation intentionally decoupled
   from physical source room locations. Geometry is adapted from the reusable indexed
   layer drawing approach in Indy Heat; values here are tile IDs, not pixel indices. */
(() => {
'use strict';
const D=window.CybernoidData;if(!D)throw Error('cybernoid-data.js must be loaded first.');
const $=id=>document.getElementById(id);const q=sel=>document.querySelector(sel);
const room=$('roomCanvas'),rc=room.getContext('2d',{alpha:false}),pc=$('tilePalette').getContext('2d');
let game=null,level=1,logical=0,selectedTile=0,selectedCell=null,zoom=2,tool='pencil';
let screen='room',paletteMode='tiles',selectedGroup=null;
const groups=window.CybernoidTileGroups||[],personalGroups=[];
const allGroups=()=>[...groups,...personalGroups];
let captureMode=false,captureSelection=null,animationTick=0;
const STRUCTURAL_COMPONENTS=new Set([0x233,0x234,0x235,0x236,0x237,0x243,0x244,0x245,0x24E,0x31D,0x326,0x327,0x328,0x347,0x348,0x349,0x359,0x30D,0x30E,0x30F,0x062,0x063,0x064,0x065,0x066,0x05C,0x05D,0x05E,0x05F,0x210,0x116,0x117,0x118,0x119,0x11A,0x11D,0x11E]);
const groupMustLock=tiles=>tiles.some(id=>id>=D.TILE_COUNT||D.SPECIAL.has(id)||STRUCTURAL_COMPONENTS.has(id));
const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let selectedPalette=[],atlas=null,gesture=null,lastAudit=null,gameName='GAME';
const categoryColors={passable:'#60c69a',solid:'#e47d7d',destructible:'#ecb275',special:'#b98bed',hazard:'#f2e376'};
function status(s,kind='info'){$('message').textContent=s;$('message').className='message '+(kind==='error'?'error':kind==='good'?'good':'');}
function exportFile(name,data,mime){const url=URL.createObjectURL(new Blob([data],{type:mime}));const a=document.createElement('a');a.href=url;a.download=name;a.style.display='none';document.body.appendChild(a);a.click();setTimeout(()=>{a.remove();URL.revokeObjectURL(url);},2000);}
function activeRoom(){return game&&screen==='room'?game.physical(level,logical):null;}
function viewingRoom(){return screen==='room';}
function screenSize(){return screen==='frontend'?12:screen.startsWith('post')?8:screen==='hud'?2:11;}
function sourceCell(x,y){if(screen==='room')return game.cell(level,activeRoom(),x,y);
 if(screen==='frontend')return game.u16(0x50F30+(y*20+x)*2);
 if(screen==='hud')return game.u16(0x3FF4E+(y*20+x)*2);
 return game.u16(0x50A30+((Number(screen.slice(4))-1)*20*8+y*20+x)*2);}
function screenDescription(){if(screen==='frontend')return 'Menu / High scores · shared 20×12 tile backdrop (Palette A)';if(screen==='hud')return 'Gameplay HUD strip · 20×2 source tiles';if(screen.startsWith('post'))return `End of Level ${screen.slice(4)} · 20×8 tile layout`;return `Logical ${logical} → physical ${activeRoom()} • 20 × 11 tiles / 320 × 176 pixels`;}

function updateControls(){const active=!!game;$('saveEdits').disabled=!active;$('exportGame').disabled=!active;$('validate').disabled=!active;$('undo').disabled=!active||!game.undoStack.length;$('redo').disabled=!active||!game.redoStack.length;
 $('enableEdit').disabled=!active||!viewingRoom();
 $('editState').textContent=active&&!viewingRoom()?'PREVIEW ONLY':active&&$('enableEdit').checked?'EDIT ENABLED':'READ ONLY';$('editState').classList.toggle('editing',active&&viewingRoom()&&$('enableEdit').checked);
 $('fileState').textContent=active?gameName:'NO FILE';$('dirtyStatus').textContent=active?`${game.diffs().length} modified map cells`:'No changes';
 qAll('[data-level]').forEach(b=>b.classList.toggle('chosen',viewingRoom()&&Number(b.dataset.level)===level));
 qAll('[data-screen]').forEach(b=>b.classList.toggle('chosen',b.dataset.screen===screen));qAll('[data-tool]').forEach(b=>b.classList.toggle('chosen',b.dataset.tool===tool));
 $('roomTitle').textContent=active?(viewingRoom()?`Level ${level} · Room ${logical}`:screen==='frontend'?'Menu / High scores':screen==='hud'?'Gameplay HUD':`End of Level ${screen.slice(4)}`):'Room canvas';$('roomSubtitle').textContent=active?screenDescription():'Load the 383,230-byte GAME file to begin';
 $('emptyMessage').hidden=!!active;
}
function qAll(sel){return [...document.querySelectorAll(sel)];}
function roomMap(){const map=$('map');map.replaceChildren();if(!game)return;const cfg=game.layout(level),start=game.u16(0x3FFB8+(level-1)*2);
 for(let i=0;i<cfg.slots;i++){const active=cfg.activeSet.has(i),p=game.physical(level,i),button=document.createElement('button');button.textContent=active?String(i):'·';button.title=active?`Logical room ${i} / physical ${p}`:`Inactive logical slot ${i} (lookup=${cfg.physicalByLogical[i]})`;button.className=active?'':'inactive';button.classList.toggle('selected',viewingRoom()&&logical===i);button.classList.toggle('start',start===i);button.disabled=!active;button.addEventListener('click',()=>{if(gesture)finishGesture();logical=i;screen='room';buildAtlas();roomMap();renderRoom();inspect();updateControls();});map.appendChild(button);}
 $('topologyInfo').textContent=`${cfg.active.length}/${cfg.slots} slots · ${cfg.count} rooms · START ${start}`;
 $('topologyInfo').title=`Topology is read-only. ${cfg.lookup!==null?'Physical room lookup '+D.hex(cfg.lookup,5):'Direct logical-to-physical addressing'}. No game structure is changed by selecting a room.`;
}
// These frame cycles come from the existing original-game research. Time base is editor-only,
// not a claim that retail objects all start in phase or run at 220 ms/frame.
function displayedTile(source){
 if(!$('animateTiles').checked)return source;
 const t=animationTick;
 if(source===0x24D||source===0x24E){const f=[0,1,2,1,0][t%5];return source+2*f;}
 if(source>=0x253&&source<=0x26E){const base=0x253+Math.floor((source-0x253)/4)*4;
  const initial=source-base,delta=base===0x253?-t:t;return base+((initial+delta)%4+4)%4;}
 if(source===0x1E0)return 0x308+(t%4);
 if(source===0x1E1)return 0x304+(t%4);
 return source;
}
function drawTileImage(ctx,tile,x,y,scale=1){tile=(ctx===rc&&!viewingRoom())?tile:displayedTile(tile);if(!atlas||tile<0||tile>=D.TILE_COUNT)return;ctx.drawImage(atlas,(tile%16)*16,Math.floor(tile/16)*16,16,16,x,y,16*scale,16*scale);}
function buildAtlas(){const useA=screen==='frontend'||$('paletteA').checked;const displayLevel=screen.startsWith('post')?Number(screen.slice(4)):level;const pal=game.palette(displayLevel,useA);const sheet=document.createElement('canvas');sheet.width=256;sheet.height=Math.ceil(D.TILE_COUNT/16)*16;const cx=sheet.getContext('2d');
 // Decode 4-bitplane planar 16×16 sprites, retaining the authentic indexed palette.
 for(let id=0;id<D.TILE_COUNT;id++){const indices=game.tileIndices(id);const pic=cx.createImageData(16,16);for(let i=0;i<256;i++){const word=game.u16(((useA?0x3FFD0:0x3FFF0)+indices[i]*2));let color=word;if(displayLevel===4&&!useA&&indices[i]<8)color=game.u16(0x1CD10+indices[i]*2);
 const o=i*4;pic.data[o]=((color>>8)&15)*17;pic.data[o+1]=((color>>4)&15)*17;pic.data[o+2]=(color&15)*17;pic.data[o+3]=255;}cx.putImageData(pic,(id%16)*16,Math.floor(id/16)*16);}atlas=sheet;}
function drawPlayerPreview(x,y){
 // Intentionally a schematic marker, not a claimed decoded original sprite. It alters no source bytes.
 rc.save();rc.translate(x*16+8,y*16+8);rc.fillStyle='rgba(5,14,26,.74)';rc.fillRect(-12,-13,24,26);
 const pixels=[
 '.......CC.......','.......WW.......','......WWWW......','...C..WW..C.....',
 '..CC.WWWW.CC....','.CCCWWWWWWCCC...','CCWWWWWWWWWWCC..','CCWWWBBWWWWWCC..',
 'CCCWWBBBBWWCCC..','..CCBBBBBBCC....','...CCBBBBCC.....','....CCBBCC......',
 '.....C..C.......'];
 const colours={C:'#68dffd',W:'#f8ffff',B:'#ee9f44'};
 pixels.forEach((row,iy)=>{for(let ix=0;ix<row.length;ix++){const colour=colours[row[ix]];if(colour){rc.fillStyle=colour;rc.fillRect(ix-8,iy-7,1,1);}}});
 rc.strokeStyle='#ffffffb0';rc.strokeRect(-12.5,-13.5,24,26);rc.restore();
}
function renderRoom(){
 const h=screenSize();if(room.height!==h*16){room.height=h*16;setZoom(zoom);}
 rc.fillStyle='#060b11';rc.fillRect(0,0,320,h*16);if(!game)return;
 const p=activeRoom();if(viewingRoom()&&p===null)return;
 rc.imageSmoothingEnabled=false;
 for(let y=0;y<h;y++)for(let x=0;x<20;x++){
  const id=viewingRoom()?(gesture?.preview?.get(y*20+x)??game.cell(level,p,x,y)):sourceCell(x,y);
  drawTileImage(rc,id,x*16,y*16);
  if(id>=D.TILE_COUNT){rc.fillStyle='#5e1e53';rc.fillRect(x*16+3,y*16+3,10,10);}
 }
 if(viewingRoom()&&$('collision').checked){rc.globalAlpha=.40;for(let y=0;y<11;y++)for(let x=0;x<20;x++){const id=gesture?.preview?.get(y*20+x)??game.cell(level,p,x,y);rc.fillStyle=categoryColors[D.colorClass(id,level)];rc.fillRect(x*16,y*16,16,16);}rc.globalAlpha=1;}
 if(viewingRoom()&&$('markers').checked){for(let y=0;y<11;y++)for(let x=0;x<20;x++){const id=gesture?.preview?.get(y*20+x)??game.cell(level,p,x,y);if(D.SPECIAL.has(id)){rc.lineWidth=1;rc.strokeStyle='#f7a8eb';rc.strokeRect(x*16+.5,y*16+.5,15,15);}}}
 if($('grid').checked){rc.beginPath();rc.strokeStyle='rgba(155,186,220,.42)';rc.lineWidth=.5;for(let x=0;x<=20;x++){rc.moveTo(x*16+.25,0);rc.lineTo(x*16+.25,h*16);}for(let y=0;y<=h;y++){rc.moveTo(0,y*16+.25);rc.lineTo(320,y*16+.25);}rc.stroke();}
 if(viewingRoom()&&$('showPlayer').checked){for(let y=0;y<11;y++)for(let x=0;x<20;x++)if(game.cell(level,p,x,y)===0x02B)drawPlayerPreview(x,y);}
 if(viewingRoom()&&captureSelection){const box=captureSelection;
  const x=Math.min(box.start.x,box.end.x),y=Math.min(box.start.y,box.end.y);
  const w=Math.abs(box.start.x-box.end.x)+1,h=Math.abs(box.start.y-box.end.y)+1;
  rc.fillStyle='rgba(126,224,253,.22)';rc.fillRect(x*16,y*16,w*16,h*16);
  rc.lineWidth=2;rc.strokeStyle='#fce18f';rc.strokeRect(x*16+1,y*16+1,w*16-2,h*16-2);
 }
 if(viewingRoom()&&selectedCell?.level===level&&selectedCell?.logical===logical){rc.strokeStyle='#f6d283';rc.lineWidth=1;rc.strokeRect(selectedCell.x*16+.5,selectedCell.y*16+.5,15,15);}
}
function animatedSource(id){return id===0x24D||id===0x24E||id===0x1E0||id===0x1E1||(id>=0x253&&id<=0x26E);}
function refreshAnimatedPalette(){if(!$('animateTiles').checked||!game)return;
 for(let n=0;n<selectedPalette.length;n++){const id=selectedPalette[n];if(!animatedSource(id))continue;
  const x=(n%5)*54,y=Math.floor(n/5)*55;
  pc.fillStyle=id===selectedTile?'#395675':'#172437';pc.fillRect(x+11,y+6,32,32);
  drawTileImage(pc,id,x+11,y+6,2);
 }
}
function renderTilePalette(){if(!game)return;const search=$('tileSearch').value.trim().replace(/^(0x|\$)/i,'').toUpperCase(),filter=$('tileFilter').value;
 let ids=Array.from({length:D.TILE_COUNT},(_,i)=>i);
 if(search){const needle=parseInt(search,16);ids=Number.isInteger(needle)&&needle>=0&&needle<D.TILE_COUNT?[needle]:[];}
 if(filter!=='all')ids=ids.filter(id=>D.colorClass(id,level)===filter);
 selectedPalette=ids;if(paletteMode==='tiles')$('tileCount').textContent=ids.length;
 const cols=5,w=54,h=55;pc.canvas.width=cols*w;pc.canvas.height=Math.max(h,Math.ceil(ids.length/cols)*h);pc.imageSmoothingEnabled=false;pc.fillStyle='#101b2a';pc.fillRect(0,0,pc.canvas.width,pc.canvas.height);
 ids.forEach((id,n)=>{const x=(n%cols)*w,y=Math.floor(n/cols)*h;pc.fillStyle=id===selectedTile?'#395675':'#172437';pc.fillRect(x+2,y+2,w-4,h-4);pc.strokeStyle=categoryColors[D.colorClass(id,level)];pc.lineWidth=id===selectedTile?3:1;pc.strokeRect(x+3.5,y+3.5,w-7,h-7);drawTileImage(pc,id,x+11,y+6,2);pc.fillStyle='#d4e3f2';pc.font='10px ui-monospace,monospace';pc.textAlign='center';pc.fillText(id.toString(16).toUpperCase().padStart(3,'0'),x+27,y+50);});
 $('tilePrompt').hidden=true;
}

function setPaletteMode(mode){paletteMode=mode;selectedGroup=null;$('paletteTiles').hidden=mode!=='tiles';$('paletteGroups').hidden=mode!=='groups';
 $('showTiles').classList.toggle('chosen',mode==='tiles');$('showGroups').classList.toggle('chosen',mode==='groups');
 $('tileCount').textContent=mode==='tiles'?selectedPalette.length:allGroups().filter(g=>g.kind===$('groupFilter').value).length;
 if(mode==='groups')renderGroups();inspect();renderRoom();}
function updateGroupSelection(){
 const g=selectedGroup;
 for(const card of $('groupList').querySelectorAll('.group-card')){
  const selected=!!g&&card.dataset.groupId===g.id;
  card.classList.toggle('chosen',selected);
  card.setAttribute('aria-pressed',String(selected));
 }
 const info=$('groupInfo');
 info.textContent=!g?'':`${g.locked?'🔒':'✓'} ${g.name} · ${g.width}×${g.height}`;
 info.title=g?`${g.source} — ${g.locked?'Reference only; cannot paint':'Click the room to place the complete group'}`:'';
 syncGroupControls();
}
function chooseGroup(g){
 selectedGroup=g;selectedCell=null;captureMode=false;tool='pencil';
 $('eyedropperTool').classList.remove('chosen');
 updateControls();updateGroupSelection();inspect();renderRoom();
}
function renderGroups(){const list=$('groupList');const oldTop=list.scrollTop;list.replaceChildren();if(!game)return;
 const filtered=allGroups().filter(g=>g.kind===$('groupFilter').value);if(paletteMode==='groups')$('tileCount').textContent=filtered.length;
 for(const g of filtered){
  const b=document.createElement('button');b.type='button';b.className='group-card'+(g.locked?' reference':'');b.dataset.groupId=g.id;
  b.title=`${g.name} (${g.width}×${g.height})\n${g.source}\n${g.locked?'Reference only — cannot be placed':'Click to select; paint the whole group in a room'}`;
  b.setAttribute('aria-label',`${g.name}, ${g.width} by ${g.height}${g.locked?', reference only':''}`);
  const image=document.createElement('canvas');image.width=64;image.height=64;image.dataset.groupId=g.id;image.setAttribute('aria-hidden','true');
  paintGroupPreview(image,g);b.appendChild(image);
  const title=document.createElement('span');title.className='group-card-title';title.textContent=g.name;
  b.appendChild(title);
  if(g.locked){const lock=document.createElement('span');lock.className='group-lock';lock.textContent='🔒';lock.setAttribute('aria-hidden','true');b.appendChild(lock);}
  b.addEventListener('click',()=>chooseGroup(g));list.appendChild(b);
 }
 if(!filtered.length){const empty=document.createElement('span');empty.className='group-empty';empty.textContent='No groups';list.appendChild(empty);}
 list.scrollTop=oldTop;updateGroupSelection();
}
function inspect(){if(!game){$('inspector').textContent='Select a tile after loading GAME.';return;}if(selectedGroup){$('inspector').innerHTML=`<div><strong>${escapeHtml(selectedGroup.name)}</strong> · ${selectedGroup.width}×${selectedGroup.height}</div><div class="${selectedGroup.locked?'warning':'ok'}">${selectedGroup.locked?'🔒 Reference only':'✓ Ready to paint'}</div>`;$('inspector').title=selectedGroup.source;return;}const p=activeRoom();const v=viewingRoom()&&selectedCell&&selectedCell.level===level&&selectedCell.logical===logical?game.cell(level,p,selectedCell.x,selectedCell.y):selectedTile;const info=D.tileInfo(v,level),cell=viewingRoom()&&selectedCell&&selectedCell.level===level&&selectedCell.logical===logical;
 const protectedFlag=cell?game.protected(level,p).has(selectedCell.y*20+selectedCell.x):false;
 const location=cell?`<div><strong>Room cell:</strong> (${selectedCell.x}, ${selectedCell.y}) · physical ${p}</div><div><strong>Source runtime:</strong> <code>${D.hex(game.roomAddress(level,p,selectedCell.x,selectedCell.y),6)}</code></div>`:'';
 $('inspector').innerHTML=`${location}<div><strong>Tile:</strong> <code>${info.hex}</code> <span class="muted">(${v})</span></div><div><strong>Meaning:</strong> ${info.name}</div><div><strong>Class:</strong> <span style="color:${categoryColors[info.category]}">${info.category}</span></div><div><strong>Collision:</strong> ${info.collision}</div>${cell?`<div class="${protectedFlag?'warning':'ok'}">${protectedFlag?'Protected source cell':'Ordinary editable cell'}</div>`:''}${info.note?`<div class="muted">${info.note}</div>`:''}<div class="muted">Current brush: ${D.hex(selectedTile,3)} · ${D.tileInfo(selectedTile,level).name}</div>`;
}

function paintGroupPreview(canvas,g){const c=canvas.getContext('2d');c.clearRect(0,0,64,64);c.imageSmoothingEnabled=false;
 const scale=Math.min(4/g.width,4/g.height),left=(64-g.width*16*scale)/2,top=(64-g.height*16*scale)/2;
 g.tiles.forEach((id,k)=>{const x=left+(k%g.width)*16*scale,y=top+Math.floor(k/g.width)*16*scale;
  if(id>=D.TILE_COUNT){c.fillStyle='#7b284e';c.fillRect(x,y,16*scale,16*scale);}else drawTileImage(c,id,x,y,scale);});
}
function refreshGroupPreviews(){for(const el of $('groupList').querySelectorAll('canvas[data-group-id]')){
 const g=allGroups().find(x=>x.id===el.dataset.groupId);if(g)paintGroupPreview(el,g);}}
function syncGroupControls(){const g=selectedGroup;
 $('captureGroup').classList.toggle('chosen',captureMode);
 $('captureGroup').textContent=captureMode?'✕ Cancel':'▧ Capture';
 $('captureGroup').setAttribute('aria-pressed',String(captureMode));
 $('captureGroup').title=captureMode?'Cancel selection':'Select tiles by dragging a rectangle over a GAME room';
 $('exportGroup').disabled=!game||!g;
 $('groupName').hidden=!g||g.kind!=='custom';
 $('groupName').disabled=!g||g.kind!=='custom';
 if(document.activeElement!==$('groupName'))$('groupName').value=g?.name||'';
 room.classList.toggle('capture-cursor',captureMode);
}
function captureFromRoom(sel){if(!viewingRoom()||!game)return;
 const x=Math.min(sel.start.x,sel.end.x),y=Math.min(sel.start.y,sel.end.y),w=Math.abs(sel.start.x-sel.end.x)+1,h=Math.abs(sel.start.y-sel.end.y)+1;
 const p=activeRoom(),tiles=[];for(let j=0;j<h;j++)for(let i=0;i<w;i++)tiles.push(game.cell(level,p,x+i,y+j));
 const g={id:`custom-${Date.now()}-${personalGroups.length}`,kind:'custom',name:`Level ${level} room ${logical} group`,width:w,height:h,
   tiles,source:`L${level} logical ${logical} / physical ${p} at (${x},${y})`,origin:{source_crc32:game.id,level,logical_room:logical,physical_room:p,x,y},locked:groupMustLock(tiles)};
 personalGroups.push(g);$('groupFilter').value='custom';setPaletteMode('groups');selectedGroup=g;renderGroups();inspect();renderRoom();
 status(`Captured ${w}×${h} source tiles from Level ${level} room ${logical}.${g.locked?' Contains special/structural words: view and export only.':' Can be stamped safely into ordinary space.'}`,'good');
}
function exportSelectedGroup(){if(!selectedGroup||!game)return;const g=selectedGroup;
 const obj={format:'cybernoid-tile-group',version:1,name:g.name,width:g.width,height:g.height,tiles:[...g.tiles],
  source:g.origin||{description:g.source,source_crc32:game.id},reference_only:!!g.locked,
  notes:'Original 16-bit tile/control words, row-major. Animated frames are preview-only; this file does not modify GAME.'};
 const clean=g.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,45)||'tile-group';
 exportFile(`cybernoid-${clean}.cygroup.json`,JSON.stringify(obj,null,2)+'\n','application/json');
 status(`Exported ${g.width}×${g.height} tile-group JSON. Share this file to add the group to the editor catalogue.`,'good');
}
async function importGroup(file){if(!file||!game)return;try{
 if(file.size>100000)throw Error('File exceeds the 100 KB tile-group size limit.');
 const obj=JSON.parse(await file.text());if(obj?.format!=='cybernoid-tile-group'||obj.version!==1)throw Error('Not a Cybernoid tile group v1.');
 const w=obj.width,h=obj.height,tiles=obj.tiles;
 if(!Number.isInteger(w)||!Number.isInteger(h)||w<1||w>20||h<1||h>11||!Array.isArray(tiles)||tiles.length!==w*h||!tiles.every(n=>Number.isInteger(n)&&n>=0&&n<=65535))throw Error('Invalid group dimensions or tile IDs.');
 const name=String(obj.name||file.name).trim().slice(0,80)||'Imported group';
 const differentSource=typeof obj.source?.source_crc32==='string'&&obj.source.source_crc32!==game.id;
 const g={id:`import-${Date.now()}-${personalGroups.length}`,kind:'custom',name,width:w,height:h,tiles:[...tiles],
  source:typeof obj.source==='string'?obj.source.slice(0,180):String(obj.source?.description||'Imported group').slice(0,180),
  origin:obj.source&&typeof obj.source==='object'?obj.source:null,
  locked:groupMustLock(tiles)||!!obj.reference_only||differentSource};
 personalGroups.push(g);$('groupFilter').value='custom';setPaletteMode('groups');selectedGroup=g;renderGroups();inspect();
 status(`Imported group “${name}” (${w}×${h}). ${differentSource?'Reference only: source GAME CRC differs.':g.locked?'Reference only: special/structural words or author restriction.':'Ordinary tiles can be stamped.'}`,'good');
 }catch(e){status('Group import refused: '+e.message,'error');}}
$('captureGroup').addEventListener('click',()=>{if(!game||!viewingRoom()){status('Choose a gameplay room before selecting a group.','error');return;}
 captureMode=!captureMode;captureSelection=null;if(captureMode){setPaletteMode('groups');captureMode=true;}
 syncGroupControls();renderRoom();status(captureMode?'Drag a rectangle in the room to capture original tile words. This does not enable editing.':'Group capture cancelled.');});
$('exportGroup').addEventListener('click',exportSelectedGroup);
$('groupName').addEventListener('input',e=>{if(selectedGroup?.kind==='custom'){selectedGroup.name=e.target.value.trim().slice(0,80)||'Unnamed group';
 const title=$('groupList').querySelector('.group-card.chosen .group-card-title');if(title)title.textContent=selectedGroup.name;updateGroupSelection();inspect();}});
$('importGroup').addEventListener('click',()=>{if(!game){status('Load GAME before importing a tile group.','error');return;}$('groupInput').click();});
$('groupInput').addEventListener('change',e=>{importGroup(e.target.files?.[0]);e.target.value='';});

function selectTile(id){selectedGroup=null;selectedTile=id;selectedCell=null;renderTilePalette();inspect();renderRoom();}
function mouseCell(ev){const r=room.getBoundingClientRect();const x=Math.floor((ev.clientX-r.left)/r.width*320/16),y=Math.floor((ev.clientY-r.top)/r.height*176/16);return{x,y};}
function inBounds(x,y){return x>=0&&x<20&&y>=0&&y<11;}
function pickCell(pos){if(!game||!viewingRoom()||!inBounds(pos.x,pos.y))return;if(selectedGroup)setPaletteMode('tiles');selectedCell={...pos,level,logical};const v=game.cell(level,activeRoom(),pos.x,pos.y);if(v<D.TILE_COUNT)selectedTile=v;renderTilePalette();inspect();renderRoom();$('cursorStatus').textContent=`LEVEL ${level} • LOGICAL ${logical} / PHYSICAL ${activeRoom()} • (${pos.x}, ${pos.y}) = ${D.hex(v,4)}`;}
function linePoints(a,b){const out=[];let x=a.x,y=a.y,dx=Math.abs(b.x-x),dy=Math.abs(b.y-y),sx=x<b.x?1:-1,sy=y<b.y?1:-1,err=dx-dy;while(true){out.push({x,y});if(x===b.x&&y===b.y)break;const e=2*err;if(e>-dy){err-=dy;x+=sx;}if(e<dx){err+=dx;y+=sy;}}return out;}
function rectPoints(a,b,filled){const out=[],x0=Math.min(a.x,b.x),x1=Math.max(a.x,b.x),y0=Math.min(a.y,b.y),y1=Math.max(a.y,b.y);for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++)if(filled||x===x0||x===x1||y===y0||y===y1)out.push({x,y});return out;}
function fillPoints(start,p){const target=game.cell(level,p,start.x,start.y),out=[],seen=new Uint8Array(220),stack=[[start.x,start.y]];while(stack.length){const [x,y]=stack.pop(),k=y*20+x;if(!inBounds(x,y)||seen[k])continue;seen[k]=1;if(game.cell(level,p,x,y)!==target)continue;out.push({x,y});if(x>0)stack.push([x-1,y]);if(x<19)stack.push([x+1,y]);if(y>0)stack.push([x,y-1]);if(y<10)stack.push([x,y+1]);}return out;}
function createPreview(g,pos){const p=activeRoom(),preview=new Map(),brush=g.tool;let pts=[];
 if(brush==='group'){let refused=0;const spec=g.group;for(let yy=0;yy<spec.height;yy++)for(let xx=0;xx<spec.width;xx++){const x=pos.x+xx,y=pos.y+yy,id=spec.tiles[yy*spec.width+xx];if(!inBounds(x,y)||game.validatePaint(level,p,x,y,id)){refused++;continue;}preview.set(y*20+x,id);}
  g.preview=refused?new Map():preview;g.refused=refused?1:0;renderRoom();return;}
 if(brush==='pencil'){
   if(!g.path)g.path=[];const seg=linePoints(g.last||pos,pos);g.path.push(...seg);g.last=pos;pts=g.path;
 }else if(brush==='line')pts=linePoints(g.start,pos);
 else if(brush==='rect')pts=rectPoints(g.start,pos,false);
 else if(brush==='fillrect')pts=rectPoints(g.start,pos,true);
 else if(brush==='fill')pts=fillPoints(g.start,p);
 let refused=0;for(const at of pts){if(!inBounds(at.x,at.y))continue;const reason=game.validatePaint(level,p,at.x,at.y,selectedTile);if(reason){refused++;continue;}preview.set(at.y*20+at.x,selectedTile);}
 g.preview=preview;g.refused=refused;renderRoom();}
function beginGesture(ev){if(!game||!viewingRoom()||ev.button!==0)return;const pos=mouseCell(ev);if(!inBounds(pos.x,pos.y))return;
 if(captureMode){captureSelection={start:pos,end:pos};room.setPointerCapture?.(ev.pointerId);renderRoom();ev.preventDefault();return;}
 if(tool==='pick'||!$('enableEdit').checked){pickCell(pos);if(tool!=='pick'&&!$('enableEdit').checked)status('Read-only: enable room tile painting in the right column.');return;}
 if(selectedGroup?.locked){status('This compound group is for reference only. Semantic object placement is not yet available.','error');return;}
 if(!selectedGroup&&D.SPECIAL.has(selectedTile)){status('Special / animated tile placements are not supported until semantic entity editing is available.','error');return;}
 selectedCell={...pos,level,logical};gesture={tool:selectedGroup?'group':tool,group:selectedGroup,start:pos,last:pos,path:[],preview:new Map(),refused:0};room.setPointerCapture?.(ev.pointerId);createPreview(gesture,pos);ev.preventDefault();}
function finishGesture(ev){
 if(captureSelection&&game){const selection=captureSelection;captureSelection=null;captureMode=false;syncGroupControls();
  captureFromRoom(selection);return;}
 if(!gesture||!game)return;const p=activeRoom(),edits=[...gesture.preview].map(([k,id])=>{const x=k%20,y=Math.floor(k/20);return{level,p,x,y,before:game.cell(level,p,x,y),after:id};});const refused=gesture.refused,isGroup=gesture.tool==='group';gesture=null;
 if(game.commit(edits)){status(`Updated ${edits.filter(e=>e.before!==e.after).length} ordinary room tiles.${refused?` ${refused} protected cells were skipped.`:''}`,'good');lastAudit=null;$('validationResult').textContent='Not checked since the last edit.';}
 else if(refused)status(isGroup?'Whole group refused: placement crossed a room edge or contained a protected tile. No partial changes.':`No changes: ${refused} protected cell(s) were skipped.`, 'error');renderRoom();updateControls();inspect();}
async function loadGame(file){if(!file)return;try{const bytes=await file.arrayBuffer();const incoming=new D.Game(bytes,file.name);game=incoming;gameName=file.name;level=1;logical=0;screen='room';captureMode=false;captureSelection=null;personalGroups.length=0;selectedGroup=null;selectedTile=0;selectedCell=null;gesture=null;lastAudit=null;$('enableEdit').checked=false;$('tileSearch').value='';$('tileFilter').value='all';
 buildAtlas();roomMap();renderTilePalette();renderGroups();renderRoom();inspect();updateControls();$('validationResult').textContent='Not yet checked.';
 const audit=game.audit();lastAudit=audit;showAudit(audit);status(`Loaded ${file.name}: ${bytes.byteLength.toLocaleString('en-GB')} bytes, 150 physical rooms; ${audit.errors.length} initial audit error(s).`,audit.ok?'good':'error');}catch(e){status(`GAME not loaded: ${e.message}`,'error');}}
function showAudit(audit){const target=$('validationResult');if(audit.ok){target.textContent=`✓ Core structural checks passed. ${game.diffs().length} changed map cells. Full legacy semantic audit is not yet ported.`;return;}
 const x=audit.errors[0];const location=`Level ${x.level}${x.p===null?'':` / physical ${x.p}`}${x.x===null?'':` / (${x.x},${x.y})`}`;
 target.textContent=`✕ ${audit.errors.length} blocking error(s). First: ${location}\n${x.detail}`;}
function doAudit(){if(!game)return;lastAudit=game.audit();showAudit(lastAudit);if(lastAudit.ok)status('Core structural checks passed. The full legacy semantic audit remains a separate migration task.','good');else status(`${lastAudit.errors.length} error(s): ${$('validationResult').textContent}`,'error');}
function doExport(){if(!game)return;const audit=game.audit();lastAudit=audit;showAudit(audit);if(!audit.ok){status(`Export blocked — ${audit.errors.length} structural error(s). ${audit.errors[0].detail}`,'error');return;}
 exportFile('GAME',game.exportBytes(),'application/octet-stream');status(`Exported GAME (${D.SIZE.toLocaleString('en-GB')} bytes). Original input on disk has not been changed.`, 'good');}
function saveEdits(){if(!game)return;const json=JSON.stringify(game.patchJSON(),null,2)+'\n';exportFile('cybernoid-edits.json',json,'application/json');status(`Saved ${game.diffs().length} map-cell edit(s) as a source-bound JSON file.`,'good');}
async function importEdits(file){if(!game){status('Load the source GAME before importing edits.','error');return;}if(!file)return;try{const obj=JSON.parse(await file.text()),n=game.importPatch(obj);renderRoom();updateControls();inspect();lastAudit=null;$('validationResult').textContent='Not checked since import.';status(`Imported ${n} source-checked edit(s).`,'good');}catch(e){status('Import refused: '+e.message,'error');}}
function undoRedo(which){if(!game)return;const ok=which==='undo'?game.undo():game.redo();if(ok){renderRoom();updateControls();inspect();lastAudit=null;$('validationResult').textContent='Not checked since Undo/Redo.';}}
function changeLevel(n){if(!game)return;captureSelection=null;screen='room';level=n;logical=game.layout(level).active[0];selectedCell=null;buildAtlas();roomMap();renderTilePalette();renderGroups();renderRoom();inspect();updateControls();}
function changeScreen(name){if(!game)return;if(gesture)finishGesture();captureSelection=null;captureMode=false;screen=name;selectedCell=null;$('enableEdit').checked=false;buildAtlas();roomMap();renderTilePalette();renderGroups();renderRoom();inspect();updateControls();
 status(name==='frontend'?'Menu / Hall of Fame use one shared 20×12 tile backdrop; overlaid text is separate.':name==='hud'?'Gameplay HUD 20×2 tile-strip preview (read-only).':`Post-level screen preview ${name.slice(4)} (read-only).`);}

function setZoom(value){zoom=Math.max(2,Math.min(6,Math.round((Number(value)||2)*2)/2));$('zoom').value=String(zoom);room.style.width=(room.width*zoom)+'px';room.style.height=(room.height*zoom)+'px';}
$('loadGame').addEventListener('click',()=>$('gameInput').click());$('gameInput').addEventListener('change',e=>{loadGame(e.target.files?.[0]);e.target.value='';});
$('importEdits').addEventListener('click',()=>{if(game)$('editsInput').click();else status('Load GAME before importing edits.','error');});$('editsInput').addEventListener('change',e=>{importEdits(e.target.files?.[0]);e.target.value='';});
$('saveEdits').addEventListener('click',saveEdits);$('exportGame').addEventListener('click',doExport);$('validate').addEventListener('click',doAudit);$('undo').addEventListener('click',()=>undoRedo('undo'));$('redo').addEventListener('click',()=>undoRedo('redo'));
qAll('[data-level]').forEach(b=>b.addEventListener('click',()=>changeLevel(Number(b.dataset.level))));qAll('[data-screen]').forEach(b=>b.addEventListener('click',()=>changeScreen(b.dataset.screen)));
$('showTiles').addEventListener('click',()=>{captureMode=false;captureSelection=null;syncGroupControls();setPaletteMode('tiles');});$('showGroups').addEventListener('click',()=>setPaletteMode('groups'));$('groupFilter').addEventListener('change',()=>{selectedGroup=null;renderGroups();inspect();renderRoom();});qAll('[data-tool]').forEach(b=>b.addEventListener('click',()=>{tool=b.dataset.tool;$('eyedropperTool').classList.remove('chosen');updateControls();}));$('eyedropperTool').addEventListener('click',()=>{tool='pick';qAll('[data-tool]').forEach(b=>b.classList.remove('chosen'));$('eyedropperTool').classList.add('chosen');});
$('zoom').addEventListener('change',e=>setZoom(e.target.value));for(const id of ['grid','collision','markers','showPlayer'])$(id).addEventListener('change',renderRoom);$('paletteA').addEventListener('change',()=>{if(game){buildAtlas();renderRoom();renderTilePalette();renderGroups();}});
$('animateTiles').addEventListener('change',()=>{if(game){renderRoom();renderTilePalette();refreshGroupPreviews();}status($('animateTiles').checked?'Known animation families are previewed with illustrative timing. GAME source words are unchanged.':'Animation preview disabled; showing original source tile IDs.');});
$('enableEdit').addEventListener('change',()=>{updateControls();status($('enableEdit').checked?'Ordinary tile painting enabled. Protected controls and compound cells remain locked.':'Room is now read-only.');});
$('tileSearch').addEventListener('input',renderTilePalette);$('tileFilter').addEventListener('change',renderTilePalette);
$('tilePalette').addEventListener('click',ev=>{if(!game)return;const rect=pc.canvas.getBoundingClientRect(),x=Math.floor((ev.clientX-rect.left)/rect.width*pc.canvas.width/54),y=Math.floor((ev.clientY-rect.top)/rect.height*pc.canvas.height/55),id=selectedPalette[y*5+x];if(id!==undefined){selectTile(id);if(tool==='pick'){tool='pencil';$('eyedropperTool').classList.remove('chosen');updateControls();}}});
room.addEventListener('contextmenu',e=>{e.preventDefault();pickCell(mouseCell(e));});room.addEventListener('pointerdown',beginGesture);room.addEventListener('pointermove',ev=>{if(!game||!viewingRoom())return;const pos=mouseCell(ev);
 if(captureSelection&&(ev.buttons&1)&&inBounds(pos.x,pos.y)){captureSelection.end=pos;renderRoom();}if(inBounds(pos.x,pos.y))$('cursorStatus').textContent=`LEVEL ${level} • ROOM ${logical}→${activeRoom()} • (${pos.x},${pos.y}) = ${D.hex(game.cell(level,activeRoom(),pos.x,pos.y),4)}`;if(gesture&&ev.buttons&1){createPreview(gesture,pos);}});
room.addEventListener('pointerup',finishGesture);room.addEventListener('pointercancel',finishGesture);window.addEventListener('pointerup',finishGesture);
$('showHelp').addEventListener('click',()=>$('helpDialog').showModal());$('closeHelp').addEventListener('click',()=>$('helpDialog').close());
document.addEventListener('keydown',ev=>{const k=ev.key.toLowerCase();if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;
 if((ev.ctrlKey||ev.metaKey)&&k==='z'){ev.preventDefault();undoRedo(ev.shiftKey?'redo':'undo');}else if((ev.ctrlKey||ev.metaKey)&&k==='y'){ev.preventDefault();undoRedo('redo');}else if(k==='+'||k==='='){setZoom(zoom+0.5);ev.preventDefault();}else if(k==='-'){setZoom(zoom-0.5);ev.preventDefault();}});
setInterval(()=>{if(!game||!$('animateTiles').checked||document.hidden)return;animationTick=(animationTick+1)%20;
 renderRoom();if(paletteMode==='tiles')refreshAnimatedPalette();else refreshGroupPreviews();},220);
setZoom(2);updateControls();
})();

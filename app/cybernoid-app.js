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
const groups=window.CybernoidTileGroups||[];
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
 $('topologyInfo').textContent=`${cfg.count} physical rooms · ${cfg.active.length}/${cfg.slots} active logical slots · start logical ${start}. ${cfg.lookup!==null?'Physical room lookup '+D.hex(cfg.lookup,5):'Direct logical-to-physical addressing'} (read-only).`;
}
function drawTileImage(ctx,tile,x,y,scale=1){if(!atlas||tile<0||tile>=D.TILE_COUNT)return;ctx.drawImage(atlas,(tile%16)*16,Math.floor(tile/16)*16,16,16,x,y,16*scale,16*scale);}
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
 if(viewingRoom()&&selectedCell?.level===level&&selectedCell?.logical===logical){rc.strokeStyle='#f6d283';rc.lineWidth=1;rc.strokeRect(selectedCell.x*16+.5,selectedCell.y*16+.5,15,15);}
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
 $('tileCount').textContent=mode==='tiles'?selectedPalette.length:groups.filter(g=>g.kind===$('groupFilter').value).length;
 if(mode==='groups')renderGroups();inspect();renderRoom();}
function renderGroups(){const list=$('groupList');list.replaceChildren();if(!game)return;
 const filtered=groups.filter(g=>g.kind===$('groupFilter').value);$('tileCount').textContent=filtered.length;
 for(const g of filtered){const b=document.createElement('button');b.type='button';b.className='group-card'+(g.locked?' reference':'')+(selectedGroup?.id===g.id?' chosen':'');
  const image=document.createElement('canvas');const scale=Math.min(4/g.width,4/g.height);image.width=64;image.height=64;const c=image.getContext('2d');c.imageSmoothingEnabled=false;
  const left=(64-g.width*16*scale)/2,top=(64-g.height*16*scale)/2;
  g.tiles.forEach((id,k)=>drawTileImage(c,id,left+(k%g.width)*16*scale,top+Math.floor(k/g.width)*16*scale,scale));b.appendChild(image);
  const text=document.createElement('span'),title=document.createElement('strong'),note=document.createElement('small');title.textContent=g.name;note.textContent=g.locked?'VIEW ONLY · '+g.source:`${g.width}×${g.height} · ${g.occurrences} examples / ${g.rooms} rooms`;text.append(title,note);b.appendChild(text);
  b.addEventListener('click',()=>{selectedGroup=g;selectedCell=null;tool='pencil';$('eyedropperTool').classList.remove('chosen');updateControls();renderGroups();inspect();renderRoom();
   $('groupInfo').textContent=g.locked?`${g.name}: original-game compound object. Placement is locked pending full semantic operations. ${g.source}.`:
    `${g.name}: click inside a gameplay room with editing enabled to stamp the whole ${g.width}×${g.height} pattern. Example: ${g.source}. Complete stamp refuses protected cells and room edges.`;
   if(g.locked)status('Selected structural reference group; editing requires future semantic object tools.');
   else status(`Selected ${g.name} (${g.width}×${g.height}). Stamp with Pencil; a protected or out-of-bounds block is never placed partially.`);
  });list.appendChild(b);}
 if(!selectedGroup)$('groupInfo').textContent='Select a recurring pattern to stamp or a compound object to inspect.';
}
function inspect(){if(!game){$('inspector').textContent='Select a tile after loading GAME.';return;}if(selectedGroup){$('inspector').innerHTML=`<div><strong>Selected group:</strong> ${selectedGroup.name}</div><div><strong>Size:</strong> ${selectedGroup.width}×${selectedGroup.height} tiles</div><div class="muted">${selectedGroup.source}.</div><div class="${selectedGroup.locked?'warning':'ok'}">${selectedGroup.locked?'Reference only: compound structures must be placed atomically in a future semantic editor.':'Stamp is all-or-nothing and cannot overwrite protected cells.'}</div>`;return;}const p=activeRoom();const v=viewingRoom()&&selectedCell&&selectedCell.level===level&&selectedCell.logical===logical?game.cell(level,p,selectedCell.x,selectedCell.y):selectedTile;const info=D.tileInfo(v,level),cell=viewingRoom()&&selectedCell&&selectedCell.level===level&&selectedCell.logical===logical;
 const protectedFlag=cell?game.protected(level,p).has(selectedCell.y*20+selectedCell.x):false;
 const location=cell?`<div><strong>Room cell:</strong> (${selectedCell.x}, ${selectedCell.y}) · physical ${p}</div><div><strong>Source runtime:</strong> <code>${D.hex(game.roomAddress(level,p,selectedCell.x,selectedCell.y),6)}</code></div>`:'';
 $('inspector').innerHTML=`${location}<div><strong>Tile:</strong> <code>${info.hex}</code> <span class="muted">(${v})</span></div><div><strong>Meaning:</strong> ${info.name}</div><div><strong>Class:</strong> <span style="color:${categoryColors[info.category]}">${info.category}</span></div><div><strong>Collision:</strong> ${info.collision}</div>${cell?`<div class="${protectedFlag?'warning':'ok'}">${protectedFlag?'Protected source cell':'Ordinary editable cell'}</div>`:''}${info.note?`<div class="muted">${info.note}</div>`:''}<div class="muted">Current brush: ${D.hex(selectedTile,3)} · ${D.tileInfo(selectedTile,level).name}</div>`;
}
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
 if(tool==='pick'||!$('enableEdit').checked){pickCell(pos);if(tool!=='pick'&&!$('enableEdit').checked)status('Read-only: enable room tile painting in the right column.');return;}
 if(selectedGroup?.locked){status('This compound group is for reference only. Semantic object placement is not yet available.','error');return;}
 if(!selectedGroup&&D.SPECIAL.has(selectedTile)){status('Special / animated tile placements are not supported until semantic entity editing is available.','error');return;}
 selectedCell={...pos,level,logical};gesture={tool:selectedGroup?'group':tool,group:selectedGroup,start:pos,last:pos,path:[],preview:new Map(),refused:0};room.setPointerCapture?.(ev.pointerId);createPreview(gesture,pos);ev.preventDefault();}
function finishGesture(ev){if(!gesture||!game)return;const p=activeRoom(),edits=[...gesture.preview].map(([k,id])=>{const x=k%20,y=Math.floor(k/20);return{level,p,x,y,before:game.cell(level,p,x,y),after:id};});const refused=gesture.refused,isGroup=gesture.tool==='group';gesture=null;
 if(game.commit(edits)){status(`Updated ${edits.filter(e=>e.before!==e.after).length} ordinary room tiles.${refused?` ${refused} protected cells were skipped.`:''}`,'good');lastAudit=null;$('validationResult').textContent='Not checked since the last edit.';}
 else if(refused)status(isGroup?'Whole group refused: placement crossed a room edge or contained a protected tile. No partial changes.':`No changes: ${refused} protected cell(s) were skipped.`, 'error');renderRoom();updateControls();inspect();}
async function loadGame(file){if(!file)return;try{const bytes=await file.arrayBuffer();const incoming=new D.Game(bytes,file.name);game=incoming;gameName=file.name;level=1;logical=0;screen='room';selectedGroup=null;selectedTile=0;selectedCell=null;gesture=null;lastAudit=null;$('enableEdit').checked=false;$('tileSearch').value='';$('tileFilter').value='all';
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
function changeLevel(n){if(!game)return;screen='room';level=n;logical=game.layout(level).active[0];selectedCell=null;buildAtlas();roomMap();renderTilePalette();renderGroups();renderRoom();inspect();updateControls();}
function changeScreen(name){if(!game)return;if(gesture)finishGesture();screen=name;selectedCell=null;$('enableEdit').checked=false;buildAtlas();roomMap();renderTilePalette();renderGroups();renderRoom();inspect();updateControls();
 status(name==='frontend'?'Menu / Hall of Fame use one shared 20×12 tile backdrop; overlaid text is separate.':name==='hud'?'Gameplay HUD 20×2 tile-strip preview (read-only).':`Post-level screen preview ${name.slice(4)} (read-only).`);}

function setZoom(value){zoom=Math.max(2,Math.min(6,Math.round((Number(value)||2)*2)/2));$('zoom').value=String(zoom);room.style.width=(room.width*zoom)+'px';room.style.height=(room.height*zoom)+'px';}
$('loadGame').addEventListener('click',()=>$('gameInput').click());$('gameInput').addEventListener('change',e=>{loadGame(e.target.files?.[0]);e.target.value='';});
$('importEdits').addEventListener('click',()=>{if(game)$('editsInput').click();else status('Load GAME before importing edits.','error');});$('editsInput').addEventListener('change',e=>{importEdits(e.target.files?.[0]);e.target.value='';});
$('saveEdits').addEventListener('click',saveEdits);$('exportGame').addEventListener('click',doExport);$('validate').addEventListener('click',doAudit);$('undo').addEventListener('click',()=>undoRedo('undo'));$('redo').addEventListener('click',()=>undoRedo('redo'));
qAll('[data-level]').forEach(b=>b.addEventListener('click',()=>changeLevel(Number(b.dataset.level))));qAll('[data-screen]').forEach(b=>b.addEventListener('click',()=>changeScreen(b.dataset.screen)));
$('showTiles').addEventListener('click',()=>setPaletteMode('tiles'));$('showGroups').addEventListener('click',()=>setPaletteMode('groups'));$('groupFilter').addEventListener('change',()=>{selectedGroup=null;renderGroups();inspect();renderRoom();});qAll('[data-tool]').forEach(b=>b.addEventListener('click',()=>{tool=b.dataset.tool;$('eyedropperTool').classList.remove('chosen');updateControls();}));$('eyedropperTool').addEventListener('click',()=>{tool='pick';qAll('[data-tool]').forEach(b=>b.classList.remove('chosen'));$('eyedropperTool').classList.add('chosen');});
$('zoom').addEventListener('change',e=>setZoom(e.target.value));for(const id of ['grid','collision','markers','showPlayer'])$(id).addEventListener('change',renderRoom);$('paletteA').addEventListener('change',()=>{if(game){buildAtlas();renderRoom();renderTilePalette();renderGroups();}});
$('enableEdit').addEventListener('change',()=>{updateControls();status($('enableEdit').checked?'Ordinary tile painting enabled. Protected controls and compound cells remain locked.':'Room is now read-only.');});
$('tileSearch').addEventListener('input',renderTilePalette);$('tileFilter').addEventListener('change',renderTilePalette);
$('tilePalette').addEventListener('click',ev=>{if(!game)return;const rect=pc.canvas.getBoundingClientRect(),x=Math.floor((ev.clientX-rect.left)/rect.width*pc.canvas.width/54),y=Math.floor((ev.clientY-rect.top)/rect.height*pc.canvas.height/55),id=selectedPalette[y*5+x];if(id!==undefined){selectTile(id);if(tool==='pick'){tool='pencil';$('eyedropperTool').classList.remove('chosen');updateControls();}}});
room.addEventListener('contextmenu',e=>{e.preventDefault();pickCell(mouseCell(e));});room.addEventListener('pointerdown',beginGesture);room.addEventListener('pointermove',ev=>{if(!game||!viewingRoom())return;const pos=mouseCell(ev);if(inBounds(pos.x,pos.y))$('cursorStatus').textContent=`LEVEL ${level} • ROOM ${logical}→${activeRoom()} • (${pos.x},${pos.y}) = ${D.hex(game.cell(level,activeRoom(),pos.x,pos.y),4)}`;if(gesture&&ev.buttons&1){createPreview(gesture,pos);}});
room.addEventListener('pointerup',finishGesture);room.addEventListener('pointercancel',finishGesture);window.addEventListener('pointerup',finishGesture);
$('showHelp').addEventListener('click',()=>$('helpDialog').showModal());$('closeHelp').addEventListener('click',()=>$('helpDialog').close());
document.addEventListener('keydown',ev=>{const k=ev.key.toLowerCase();if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;
 if((ev.ctrlKey||ev.metaKey)&&k==='z'){ev.preventDefault();undoRedo(ev.shiftKey?'redo':'undo');}else if((ev.ctrlKey||ev.metaKey)&&k==='y'){ev.preventDefault();undoRedo('redo');}else if(k==='+'||k==='='){setZoom(zoom+0.5);ev.preventDefault();}else if(k==='-'){setZoom(zoom-0.5);ev.preventDefault();}});
setZoom(2);updateControls();
})();

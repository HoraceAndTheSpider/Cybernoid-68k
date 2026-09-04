#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import numpy as np

GAME = Path("GAME")
OUT = Path("gfx_out")
OUT.mkdir(exist_ok=True)
b = GAME.read_bytes()

DELTA = 0xEE06

def off(addr): return addr - DELTA

def palette(addr):
    vals = [int.from_bytes(b[off(addr)+i:off(addr)+i+2], "big")
            for i in range(0,32,2)]
    return vals, [(((v>>8)&15)*17, ((v>>4)&15)*17, (v&15)*17)
                  for v in vals]

def indexed_to_rgb(px, pal):
    out = np.zeros((*px.shape,3), dtype=np.uint8)
    for i,c in enumerate(pal):
        out[px == i] = c
    return Image.fromarray(out)

def render_title():
    vals,pal = palette(0x1F9D0)
    w,h,planes = 160,100,4
    rb = w//8
    ps = rb*h
    data = b[off(0x1DA90):off(0x1DA90)+ps*planes]
    px = np.zeros((h,w), dtype=np.uint8)
    for p in range(planes):
        pd = data[p*ps:(p+1)*ps]
        for y in range(h):
            for bx in range(rb):
                v = pd[y*rb+bx]
                for bit in range(8):
                    px[y,bx*8+bit] |= ((v>>(7-bit))&1) << p
    img = indexed_to_rgb(px,pal)
    img.resize((320,200),Image.Resampling.NEAREST).save(OUT/"title.png")

def render_tile(addr,pal):
    data = b[off(addr):off(addr)+0x80]
    px = np.zeros((16,16), dtype=np.uint8)
    pos=0
    for y in range(16):
        for p in range(4):
            word=(data[pos]<<8)|data[pos+1]
            pos += 2
            for bit in range(16):
                px[y,bit] |= ((word>>(15-bit))&1) << p
    return indexed_to_rgb(px,pal)

def render_atlas(palette_addr,name):
    _,pal = palette(palette_addr)
    start,end = 0x1FC68,0x3DC68
    count=(end-start)//0x80
    cols=32
    rows=count//cols
    atlas=Image.new("RGB",(cols*16,rows*16))
    for i in range(count):
        atlas.paste(render_tile(start+i*0x80,pal),
                    ((i%cols)*16,(i//cols)*16))
    atlas.resize((atlas.width*2,atlas.height*2),
                 Image.Resampling.NEAREST).save(OUT/name)

render_title()
render_atlas(0x3FFD0,"tiles_palette_A.png")
render_atlas(0x3FFF0,"tiles_palette_B.png")
print("Wrote", OUT)

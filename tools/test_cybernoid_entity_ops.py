#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cybernoid_entity_ops import (
    EntityEditError,
    add_crp,
    add_ele_pair,
    add_rnet,
    add_single_controller,
    delete_compound,
    move_compound,
    move_landing_pad,
    move_portal,
    move_start,
)


def room(physical=0):
    return {"physical_id": physical, "rows": [[0 for _ in range(20)] for _ in range(11)]}


def model4():
    levels=[]
    for level_no,count in ((1,1),(2,1),(3,1),(4,80)):
        rooms=[room(i) for i in range(count)]
        slots=[{"logical_id":i,"active":True,"physical_id":i,"grid_x":i&7,"grid_y":i>>3} for i in range(count)]
        levels.append({"level":level_no,"rooms":rooms,"logical_slots":slots})
    return {"levels":levels,"fixed_blocks":{
        "start_rooms":[0,0,0,0],
        "portal_table":{"records":[
            {"index":i,"source_room":i,"trigger_x":48,"trigger_y":40,
             "destination_room":i,"destination_x":48,"destination_y":40}
            for i in range(8)
        ]}}}


class EntityOpsTests(unittest.TestCase):
    def test_portal_move_updates_marker_and_record_and_allows_same_room_multiple(self):
        m=model4()
        l4=m["levels"][3]
        for i in range(8): l4["rooms"][i]["rows"][1][1]=0x1D5
        # Move record 1 into room 0 at a different trigger; record 0 remains there too.
        move_portal(m,1,source_room=0,source_x=5,source_y=4,
                    destination_room=7,destination_x=8,destination_y=6)
        self.assertEqual(l4["rooms"][1]["rows"][1][1],0)
        self.assertEqual(l4["rooms"][0]["rows"][4][5],0x1D5)
        r=m["fixed_blocks"]["portal_table"]["records"][1]
        self.assertEqual((r["source_room"],r["trigger_x"],r["trigger_y"]),(0,112,88))
        self.assertEqual((r["destination_room"],r["destination_x"],r["destination_y"]),(7,160,120))

    def test_start_move_syncs_start_table(self):
        m=model4(); l1=m["levels"][0]
        l1["rooms"][0]["rows"][2][2]=0x02B
        move_start(m,1,logical_room=0,x=7,y=5)
        self.assertEqual(l1["rooms"][0]["rows"][2][2],0)
        self.assertEqual(l1["rooms"][0]["rows"][5][7],0x02B)
        self.assertEqual(m["fixed_blocks"]["start_rooms"][0],0)

    def test_landing_moves_as_pair(self):
        m=model4(); l1=m["levels"][0]; r=l1["rooms"][0]
        r["rows"][3][3:5]=[0x324,0x325]
        move_landing_pad(m,1,logical_room=0,x=10,y=6)
        self.assertEqual(r["rows"][3][3:5],[0,0])
        self.assertEqual(r["rows"][6][10:12],[0x324,0x325])

    def test_30c_move_preserves_context_cell(self):
        r=room()
        # Anchor at (5,4), context at (+2,+1) = (7,5).
        vals={(-1,-1):0x116,(0,-1):0x117,(1,-1):0x118,(2,-1):0x119,
              (-1,0):0x11A,(0,0):0x30C,(1,0):0x30D,(2,0):0x11D,
              (-1,1):0x11E,(0,1):0x30E,(1,1):0x30F}
        for (dx,dy),v in vals.items(): r["rows"][4+dy][5+dx]=v
        r["rows"][5][7]=0x121
        move_compound(r,"large_cannon_30C",old_x=5,old_y=4,new_x=12,new_y=4)
        self.assertEqual(r["rows"][5][7],0x121)  # collateral/context untouched
        self.assertEqual(r["rows"][4][12],0x30C)
        delete_compound(r,"large_cannon_30C",x=12,y=4)
        self.assertEqual(r["rows"][5][14],0)  # new context was never owned/touched

    def test_ele_sixth_pair_rejected(self):
        r=room()
        for y in range(5):
            r["rows"][y][1]=0x1F6; r["rows"][y][3]=0x1F7
        with self.assertRaises(EntityEditError):
            add_ele_pair(r,"horizontal",start_x=5,start_y=6,end_x=8,end_y=6)

    def test_controller_57th_rejected(self):
        r=room()
        # 56 independent $257 energy-field cells each consume one controller.
        n=0
        for y in range(11):
            for x in range(20):
                if n<56: r["rows"][y][x]=0x257; n+=1
        with self.assertRaises(EntityEditError):
            add_single_controller(r,4,0x31C,x=19,y=10)

    def test_safe_add_caps_rnet_and_crp(self):
        r=room()
        for x in range(8): r["rows"][1][x]=0x1F0
        with self.assertRaises(EntityEditError): add_rnet(r,0x1F1,x=10,y=1)
        c=room()
        for x in range(6): c["rows"][2][x]=0x1FC
        with self.assertRaises(EntityEditError): add_crp(c,0x1FD,x=10,y=2)


if __name__ == "__main__":
    unittest.main()

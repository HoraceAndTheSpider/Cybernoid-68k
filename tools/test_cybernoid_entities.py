#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

# Allow both `python tools/test_cybernoid_entities.py` and repo-root unittest invocation.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cybernoid_entities import crp_load_roles, detect_room_entities, generic_controller_usage, portal_entities, rnet_load_roles
from cybernoid_semantics import EDGE_SIDES


def room(words=None, physical=0):
    rows = [[0 for _ in range(20)] for _ in range(11)]
    for x, y, value in words or []:
        rows[y][x] = value
    return {"physical_id": physical, "rows": rows}


class EntityTests(unittest.TestCase):
    def test_24d_pair_is_atomic(self):
        r = room([(5, 4, 0x24D), (6, 4, 0x24E)])
        entities = detect_room_entities(r, 1)
        e = next(e for e in entities if e.kind == "animated_pair_24D_24E")
        self.assertEqual(e.cells, ((5, 4, 0x24D), (6, 4, 0x24E)))
        self.assertEqual(generic_controller_usage(r)["used"], 1)

    def test_rnet_row_major_cap(self):
        r = room([(x, 1, 0x1F0) for x in range(10)])
        roles = rnet_load_roles(r)
        self.assertEqual([r["runtime_role"] for r in roles[:8]], ["live_primary"] * 8)
        self.assertEqual([r["runtime_role"] for r in roles[8:]], ["skipped_pool_full"] * 2)

    def test_crp_overflow_collapses_to_slot76(self):
        r = room([(x, 2, 0x1FD) for x in range(8)])
        roles = crp_load_roles(r)
        self.assertEqual([r["runtime_role"] for r in roles],
                         ["dedicated_live"] * 6 + ["overflow_overwritten", "overflow_slot76_live"])
        self.assertEqual(roles[-1]["runtime_slot"], 76)

    def test_bottom_edge_spawn_accepts_original_level4_row9(self):
        _, border_test, _, _ = EDGE_SIDES["BOTTOM"]
        self.assertTrue(border_test(2, 9))
        self.assertTrue(border_test(2, 10))
        self.assertFalse(border_test(2, 8))

    def test_portals_can_share_source_room(self):
        r = room([(2, 2, 0x1D5), (8, 7, 0x1D5)], physical=12)
        model = {
            "levels": [{"level": 4, "rooms": [r]}],
            "fixed_blocks": {"portal_table": {"records": [
                {"index": 0, "source_room": 12, "trigger_x": 64, "trigger_y": 56,
                 "destination_room": 12, "destination_x": 80, "destination_y": 72},
                {"index": 1, "source_room": 12, "trigger_x": 160, "trigger_y": 136,
                 "destination_room": 12, "destination_x": 96, "destination_y": 88},
            ]}},
        }
        portals = portal_entities(model)
        self.assertTrue(all(p["source_marker_matches"] for p in portals))


if __name__ == "__main__":
    unittest.main()

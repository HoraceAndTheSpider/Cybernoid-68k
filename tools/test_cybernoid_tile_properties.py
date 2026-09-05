#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cybernoid_tile_properties import palette_class, tile_info


class TilePropertyTests(unittest.TestCase):
    def test_known_background_passable_and_solid(self):
        self.assertEqual(palette_class(0x048, 1), "passable")
        self.assertEqual(tile_info(0x048, 1)["collision"], "passable")
        self.assertEqual(palette_class(0x007, 1), "solid")
        self.assertEqual(tile_info(0x007, 1)["collision"], "solid")

    def test_single_destructible(self):
        info = tile_info(0x068, 1)
        self.assertTrue(info["destructible"])
        self.assertEqual(palette_class(0x068, 1), "destructible")

    def test_energy_field_changes_in_level4(self):
        self.assertEqual(tile_info(0x257, 1)["collision"], "passable")
        self.assertEqual(palette_class(0x257, 4), "hazard")
        self.assertIn("$1234", tile_info(0x257, 4)["note"])

    def test_side_gun_anchor_mentions_runtime_footprint(self):
        info = tile_info(0x329, 4)
        self.assertTrue(info["special"])
        self.assertIn("$3FF2C", info["note"])
        self.assertIn("four-cell", info["note"])


if __name__ == "__main__":
    unittest.main()

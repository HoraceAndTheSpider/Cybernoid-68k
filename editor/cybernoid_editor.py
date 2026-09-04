#!/usr/bin/env python3
"""Pygame editor for an extracted Cybernoid (Amiga) project.

This first GUI deliberately edits the lossless structured project rather than the
GAME binary directly.  Repacking is delegated to tools/cybernoid_project.py and is
blocked when structural validation reports errors.

Current safe scope:
- browse the logical 8-wide level layouts, including inactive holes;
- render all physical 20x11 rooms from the real 961-tile planar graphics bank;
- toggle palette A/B without assuming an unproved per-level palette mapping;
- inspect semantic control-marker overlays;
- raw tile/control-word painting with undo and eyedropper;
- save project.json;
- repack a fixed-size GAME only after validation passes.

High-level entity creation is intentionally not yet exposed.  In particular, CRP
source-marker counts exceed their nominal runtime allocator band in original rooms,
and RNET has a live-object cap distinct from source-marker count.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

try:
    import pygame
except ImportError as exc:  # pragma: no cover - user environment dependency
    raise SystemExit("pygame is required: python -m pip install pygame") from exc

from cybernoid_project import repack_project  # noqa: E402
from cybernoid_semantics import (  # noqa: E402
    MARKERS,
    audit_project,
    refresh_project_derived,
)

WINDOW_W = 1440
WINDOW_H = 900
FPS = 60

ROOM_SCALE = 2
ROOM_TILE_PX = 16 * ROOM_SCALE
ROOM_W = 20 * ROOM_TILE_PX
ROOM_H = 11 * ROOM_TILE_PX
ROOM_X = 320
ROOM_Y = 70

MAP_X = 20
MAP_Y = 80
MAP_CELL = 31
MAP_GAP = 3

INFO_X = 985
INFO_Y = 70
INFO_W = 430
INFO_H = 355

PALETTE_X = 320
PALETTE_Y = 455
PALETTE_SCALE = 2
PALETTE_TILE_PX = 16 * PALETTE_SCALE
PALETTE_COLS = 32
PALETTE_W = PALETTE_COLS * PALETTE_TILE_PX
PALETTE_H = 384
PALETTE_VISIBLE_ROWS = PALETTE_H // PALETTE_TILE_PX

BG = (22, 23, 27)
PANEL = (34, 36, 42)
PANEL_2 = (46, 48, 55)
TEXT = (228, 230, 235)
MUTED = (148, 152, 164)
ACCENT = (92, 176, 255)
SELECT = (255, 210, 80)
ERROR = (235, 90, 90)
WARNING = (240, 170, 70)
GRID = (70, 73, 82)
INACTIVE = (25, 26, 31)
MARKER_OUTLINE = (255, 100, 210)
ANOMALY = (255, 70, 70)


def amiga_colour(word: int) -> tuple[int, int, int]:
    return (((word >> 8) & 0xF) * 17, ((word >> 4) & 0xF) * 17, (word & 0xF) * 17)


def decode_tile_surfaces(tile_bank: bytes, palette_words: list[int]) -> list[pygame.Surface]:
    palette = [amiga_colour(int(word)) for word in palette_words]
    expected = 961 * 0x80
    if len(tile_bank) != expected:
        raise ValueError(f"tile_bank.bin must be {expected} bytes, found {len(tile_bank)}")

    surfaces: list[pygame.Surface] = []
    for tile_id in range(961):
        data = tile_bank[tile_id * 0x80:(tile_id + 1) * 0x80]
        surf = pygame.Surface((16, 16))
        pos = 0
        indices = [[0 for _ in range(16)] for _ in range(16)]
        for y in range(16):
            for plane in range(4):
                word = (data[pos] << 8) | data[pos + 1]
                pos += 2
                for x in range(16):
                    indices[y][x] |= ((word >> (15 - x)) & 1) << plane
        for y in range(16):
            for x in range(16):
                surf.set_at((x, y), palette[indices[y][x]])
        surfaces.append(surf)
    return surfaces


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str, x: int, y: int,
              colour=TEXT) -> int:
    img = font.render(text, True, colour)
    surface.blit(img, (x, y))
    return img.get_height()


def short_marker(value: int) -> str:
    literal, kind = MARKERS.get(value, ("", ""))
    if literal:
        return literal.split()[0][:5]
    names = {
        "level4_portal": "PORT",
        "particle_emitter": "EMIT",
        "organic_cannon": "300",
        "large_cannon": "30C",
        "fixed_cannon": "31C",
        "right_gun": "RGUN",
        "left_gun": "LGUN",
        "landing_pad_left": "PAD",
        "landing_pad_right": "PAD",
        "level4_mixed_spawn_pit": "PIT",
    }
    return names.get(kind, f"{value:03X}")


class Editor:
    def __init__(self, project_dir: Path, output_path: Path):
        self.project_dir = project_dir
        self.model_path = project_dir / "project.json"
        self.output_path = output_path
        self.model = json.loads(self.model_path.read_text(encoding="utf-8"))
        self.tile_bank = (project_dir / "blobs" / "tile_bank.bin").read_bytes()

        pygame.init()
        pygame.display.set_caption("Cybernoid Amiga Level Editor")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 17)
        self.small = pygame.font.SysFont("consolas", 13)
        self.tiny = pygame.font.SysFont("consolas", 11)
        self.title_font = pygame.font.SysFont("consolas", 22, bold=True)

        self.palette_key = "palette_a"
        self.tiles = self._build_tiles()
        self.palette_scroll = 0
        self.selected_tile = 0
        self.level_no = 1
        self.logical_room = int(self.model["fixed_blocks"]["start_rooms"][0])
        self.show_markers = True
        self.edit_enabled = False
        self.modified = False
        self.undo_stack: list[tuple[int, int, int, int, int, int]] = []
        self.status = "Project loaded. Press E to enable raw editing."
        self.audit_summary, self.audit_issues = audit_project(self.model)
        self._ensure_selected_room_active()

    def _build_tiles(self) -> list[pygame.Surface]:
        words = self.model["fixed_blocks"][self.palette_key]["words"]
        return decode_tile_surfaces(self.tile_bank, words)

    def level(self) -> dict:
        return next(level for level in self.model["levels"] if int(level["level"]) == self.level_no)

    def slot_by_logical(self, logical: int) -> dict | None:
        for slot in self.level()["logical_slots"]:
            if int(slot["logical_id"]) == logical:
                return slot
        return None

    def current_physical(self) -> int:
        slot = self.slot_by_logical(self.logical_room)
        if slot is None:
            raise KeyError(self.logical_room)
        return int(slot["physical_id"])

    def current_room(self) -> dict:
        physical = self.current_physical()
        return next(room for room in self.level()["rooms"] if int(room["physical_id"]) == physical)

    def _ensure_selected_room_active(self) -> None:
        slot = self.slot_by_logical(self.logical_room)
        if slot and slot.get("active"):
            return
        active = [slot for slot in self.level()["logical_slots"] if slot.get("active")]
        if not active:
            raise ValueError(f"level {self.level_no} has no active logical rooms")
        self.logical_room = int(active[0]["logical_id"])

    def switch_level(self, level_no: int) -> None:
        self.level_no = level_no
        self.logical_room = int(self.model["fixed_blocks"]["start_rooms"][level_no - 1])
        self._ensure_selected_room_active()
        self.status = f"Level {level_no}"

    def select_logical(self, logical: int) -> None:
        slot = self.slot_by_logical(logical)
        if slot and slot.get("active"):
            self.logical_room = logical
            self.status = f"Selected L{self.level_no} logical room {logical} -> physical {slot['physical_id']}"

    def set_room_word(self, x: int, y: int, value: int) -> None:
        if not self.edit_enabled:
            self.status = "Editing is disabled. Press E to enable raw editing."
            return
        room = self.current_room()
        old = int(room["rows"][y][x])
        if old == value:
            return
        room["rows"][y][x] = int(value)
        self.undo_stack.append((self.level_no, self.current_physical(), x, y, old, int(value)))
        self.modified = True
        self.status = f"L{self.level_no} R{self.logical_room} ({x},{y}): ${old:04X} -> ${value:04X}"
        refresh_project_derived(self.model)
        self.audit_summary, self.audit_issues = audit_project(self.model)

    def undo(self) -> None:
        if not self.undo_stack:
            self.status = "Nothing to undo."
            return
        level_no, physical, x, y, old, new = self.undo_stack.pop()
        level = next(level for level in self.model["levels"] if int(level["level"]) == level_no)
        room = next(room for room in level["rooms"] if int(room["physical_id"]) == physical)
        room["rows"][y][x] = old
        self.modified = True
        refresh_project_derived(self.model)
        self.audit_summary, self.audit_issues = audit_project(self.model)
        self.status = f"Undo: L{level_no} physical {physical} ({x},{y}) ${new:04X} -> ${old:04X}"

    def save(self) -> None:
        refresh_project_derived(self.model)
        self.audit_summary, self.audit_issues = audit_project(self.model)
        self.model_path.write_text(json.dumps(self.model, indent=2) + "\n", encoding="utf-8")
        self.modified = False
        self.status = f"Saved project.json ({self.audit_summary['errors']} structural errors)."

    def repack(self) -> None:
        refresh_project_derived(self.model)
        self.audit_summary, self.audit_issues = audit_project(self.model)
        if self.audit_summary["errors"]:
            self.status = f"Repack blocked: {self.audit_summary['errors']} structural error(s)."
            return
        self.save()
        try:
            repack_project(self.project_dir, self.output_path)
            self.status = f"Repacked fixed-size GAME -> {self.output_path}"
        except Exception as exc:  # surface tool validation cleanly in GUI
            self.status = f"Repack failed: {exc}"

    def toggle_palette(self) -> None:
        self.palette_key = "palette_b" if self.palette_key == "palette_a" else "palette_a"
        self.tiles = self._build_tiles()
        self.status = f"Using {self.palette_key.replace('_', ' ').title()} (display only)."

    def draw_map_panel(self) -> None:
        pygame.draw.rect(self.screen, PANEL, (10, 55, 290, 390), border_radius=5)
        draw_text(self.screen, self.title_font, f"LEVEL {self.level_no}", 20, 62)
        level = self.level()
        for slot in level["logical_slots"]:
            logical = int(slot["logical_id"])
            gx = int(slot["grid_x"])
            gy = int(slot["grid_y"])
            x = MAP_X + gx * (MAP_CELL + MAP_GAP)
            y = MAP_Y + 30 + gy * (MAP_CELL + MAP_GAP)
            rect = pygame.Rect(x, y, MAP_CELL, MAP_CELL)
            active = bool(slot.get("active"))
            colour = PANEL_2 if active else INACTIVE
            pygame.draw.rect(self.screen, colour, rect)
            if active and logical == self.logical_room:
                pygame.draw.rect(self.screen, SELECT, rect, 3)
            elif active:
                pygame.draw.rect(self.screen, GRID, rect, 1)
            label = f"{logical:02d}" if active else "--"
            img = self.small.render(label, True, TEXT if active else MUTED)
            self.screen.blit(img, img.get_rect(center=rect.center))

        y = 365
        draw_text(self.screen, self.small, "Keys 1-4: level", 20, y, MUTED); y += 19
        draw_text(self.screen, self.small, "Click map: room", 20, y, MUTED); y += 19
        draw_text(self.screen, self.small, "P: palette A/B   M: overlays", 20, y, MUTED); y += 19
        draw_text(self.screen, self.small, "E: edit toggle   Ctrl+Z: undo", 20, y, MUTED); y += 19
        draw_text(self.screen, self.small, "Ctrl+S: save     Ctrl+R: repack", 20, y, MUTED)

    def draw_room(self) -> None:
        room = self.current_room()
        pygame.draw.rect(self.screen, PANEL, (ROOM_X - 8, ROOM_Y - 8, ROOM_W + 16, ROOM_H + 16), border_radius=5)
        for y, row in enumerate(room["rows"]):
            for x, raw_value in enumerate(row):
                value = int(raw_value)
                dest = pygame.Rect(ROOM_X + x * ROOM_TILE_PX, ROOM_Y + y * ROOM_TILE_PX,
                                   ROOM_TILE_PX, ROOM_TILE_PX)
                if 0 <= value < len(self.tiles):
                    tile = pygame.transform.scale(self.tiles[value], (ROOM_TILE_PX, ROOM_TILE_PX))
                    self.screen.blit(tile, dest)
                else:
                    pygame.draw.rect(self.screen, ANOMALY, dest)
                    pygame.draw.line(self.screen, BG, dest.topleft, dest.bottomright, 2)
                    pygame.draw.line(self.screen, BG, dest.topright, dest.bottomleft, 2)
                    img = self.tiny.render(f"{value:04X}", True, TEXT)
                    self.screen.blit(img, img.get_rect(center=dest.center))
                pygame.draw.rect(self.screen, (0, 0, 0), dest, 1)
                if self.show_markers and value in MARKERS:
                    pygame.draw.rect(self.screen, MARKER_OUTLINE, dest, 2)
                    label = self.tiny.render(short_marker(value), True, MARKER_OUTLINE)
                    self.screen.blit(label, (dest.x + 2, dest.y + 1))

        physical = self.current_physical()
        mode = "EDIT" if self.edit_enabled else "READ-ONLY"
        state_colour = WARNING if self.edit_enabled else MUTED
        draw_text(self.screen, self.font,
                  f"L{self.level_no} logical {self.logical_room}  physical {physical}  {mode}",
                  ROOM_X, ROOM_Y - 31, state_colour)

    def draw_info(self) -> None:
        pygame.draw.rect(self.screen, PANEL, (INFO_X, INFO_Y, INFO_W, INFO_H), border_radius=5)
        room = self.current_room()
        physical = self.current_physical()
        draw_text(self.screen, self.title_font, "ROOM DATA", INFO_X + 12, INFO_Y + 10)
        y = INFO_Y + 45
        draw_text(self.screen, self.small, f"Logical: {self.logical_room}    Physical: {physical}", INFO_X + 12, y); y += 20
        draw_text(self.screen, self.small, f"Palette display: {self.palette_key[-1].upper()}", INFO_X + 12, y); y += 20
        draw_text(self.screen, self.small, f"Selected tile/control: ${self.selected_tile:03X}", INFO_X + 12, y, SELECT); y += 26

        markers = []
        for yy, row in enumerate(room["rows"]):
            for xx, value in enumerate(row):
                value = int(value)
                if value in MARKERS:
                    literal, kind = MARKERS[value]
                    markers.append((xx, yy, value, literal or kind))
        draw_text(self.screen, self.small, f"Semantic markers: {len(markers)}", INFO_X + 12, y); y += 20
        for xx, yy, value, name in markers[:8]:
            draw_text(self.screen, self.tiny, f"${value:03X} @ {xx:02d},{yy:02d}  {name[:26]}", INFO_X + 18, y, MUTED)
            y += 16
        if len(markers) > 8:
            draw_text(self.screen, self.tiny, f"... {len(markers) - 8} more", INFO_X + 18, y, MUTED); y += 16

        y = INFO_Y + INFO_H - 78
        errors = int(self.audit_summary["errors"])
        warnings = int(self.audit_summary["warnings"])
        info = int(self.audit_summary["info"])
        colour = ERROR if errors else TEXT
        draw_text(self.screen, self.small, f"Audit: {errors} errors / {warnings} warnings / {info} info", INFO_X + 12, y, colour)
        y += 21
        if errors:
            first = next(issue for issue in self.audit_issues if issue.severity == "error")
            draw_text(self.screen, self.tiny, first.code + ": " + first.message[:44], INFO_X + 12, y, ERROR)

    def draw_palette(self) -> None:
        pygame.draw.rect(self.screen, PANEL, (PALETTE_X - 8, PALETTE_Y - 31, PALETTE_W + 16, PALETTE_H + 39), border_radius=5)
        draw_text(self.screen, self.font,
                  f"TILE / CONTROL PALETTE   rows {self.palette_scroll}-{self.palette_scroll + PALETTE_VISIBLE_ROWS - 1}",
                  PALETTE_X, PALETTE_Y - 26)
        start = self.palette_scroll * PALETTE_COLS
        for vr in range(PALETTE_VISIBLE_ROWS):
            for col in range(PALETTE_COLS):
                tile_id = start + vr * PALETTE_COLS + col
                if tile_id >= len(self.tiles):
                    continue
                x = PALETTE_X + col * PALETTE_TILE_PX
                y = PALETTE_Y + vr * PALETTE_TILE_PX
                rect = pygame.Rect(x, y, PALETTE_TILE_PX, PALETTE_TILE_PX)
                self.screen.blit(pygame.transform.scale(self.tiles[tile_id], rect.size), rect)
                if tile_id == self.selected_tile:
                    pygame.draw.rect(self.screen, SELECT, rect, 3)
                else:
                    pygame.draw.rect(self.screen, (0, 0, 0), rect, 1)
                if tile_id in MARKERS:
                    pygame.draw.rect(self.screen, MARKER_OUTLINE, rect, 1)

    def draw_status(self) -> None:
        y = WINDOW_H - 32
        pygame.draw.rect(self.screen, PANEL_2, (0, y, WINDOW_W, 32))
        suffix = " *modified*" if self.modified else ""
        draw_text(self.screen, self.small, self.status[:150] + suffix, 14, y + 7)

    def map_hit(self, pos: tuple[int, int]) -> int | None:
        mx, my = pos
        for slot in self.level()["logical_slots"]:
            gx = int(slot["grid_x"]); gy = int(slot["grid_y"])
            rect = pygame.Rect(MAP_X + gx * (MAP_CELL + MAP_GAP),
                               MAP_Y + 30 + gy * (MAP_CELL + MAP_GAP), MAP_CELL, MAP_CELL)
            if rect.collidepoint(mx, my) and slot.get("active"):
                return int(slot["logical_id"])
        return None

    def room_hit(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        mx, my = pos
        if not pygame.Rect(ROOM_X, ROOM_Y, ROOM_W, ROOM_H).collidepoint(mx, my):
            return None
        return ((mx - ROOM_X) // ROOM_TILE_PX, (my - ROOM_Y) // ROOM_TILE_PX)

    def palette_hit(self, pos: tuple[int, int]) -> int | None:
        mx, my = pos
        rect = pygame.Rect(PALETTE_X, PALETTE_Y, PALETTE_W, PALETTE_H)
        if not rect.collidepoint(mx, my):
            return None
        col = (mx - PALETTE_X) // PALETTE_TILE_PX
        row = (my - PALETTE_Y) // PALETTE_TILE_PX + self.palette_scroll
        tile_id = row * PALETTE_COLS + col
        return tile_id if 0 <= tile_id < len(self.tiles) else None

    def handle_key(self, event: pygame.event.Event) -> None:
        mods = pygame.key.get_mods()
        ctrl = bool(mods & pygame.KMOD_CTRL)
        if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            self.switch_level(event.key - pygame.K_0)
        elif event.key == pygame.K_p:
            self.toggle_palette()
        elif event.key == pygame.K_m:
            self.show_markers = not self.show_markers
        elif event.key == pygame.K_e:
            self.edit_enabled = not self.edit_enabled
            self.status = "Raw editing enabled." if self.edit_enabled else "Editing disabled."
        elif ctrl and event.key == pygame.K_z:
            self.undo()
        elif ctrl and event.key == pygame.K_s:
            self.save()
        elif ctrl and event.key == pygame.K_r:
            self.repack()

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        self.handle_key(event)
                elif event.type == pygame.MOUSEWHEEL:
                    mx, my = pygame.mouse.get_pos()
                    if pygame.Rect(PALETTE_X, PALETTE_Y, PALETTE_W, PALETTE_H).collidepoint(mx, my):
                        max_rows = math.ceil(len(self.tiles) / PALETTE_COLS)
                        max_scroll = max(0, max_rows - PALETTE_VISIBLE_ROWS)
                        self.palette_scroll = max(0, min(max_scroll, self.palette_scroll - event.y))
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        logical = self.map_hit(event.pos)
                        if logical is not None:
                            self.select_logical(logical)
                            continue
                        tile = self.palette_hit(event.pos)
                        if tile is not None:
                            self.selected_tile = tile
                            self.status = f"Selected tile/control ${tile:03X}"
                            continue
                        hit = self.room_hit(event.pos)
                        if hit is not None:
                            self.set_room_word(hit[0], hit[1], self.selected_tile)
                    elif event.button == 3:
                        hit = self.room_hit(event.pos)
                        if hit is not None:
                            x, y = hit
                            value = int(self.current_room()["rows"][y][x])
                            if 0 <= value < 961:
                                self.selected_tile = value
                                self.status = f"Eyedropper: ${value:03X} from ({x},{y})"
                            else:
                                self.status = f"Raw anomalous word ${value:04X}; not selectable from tile palette."

            self.screen.fill(BG)
            draw_text(self.screen, self.title_font, "CYBERNOID — AMIGA PROJECT EDITOR", 20, 17)
            self.draw_map_panel()
            self.draw_room()
            self.draw_info()
            self.draw_palette()
            self.draw_status()
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="project directory produced by cybernoid_project.py extract")
    parser.add_argument("--output", type=Path, help="patched GAME output path; default PROJECT/GAME.patched")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output = args.output or (args.project / "GAME.patched")
    Editor(args.project, output).run()


if __name__ == "__main__":
    main()

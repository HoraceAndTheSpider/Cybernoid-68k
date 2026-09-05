#!/usr/bin/env python3
"""Pygame editor for an extracted Cybernoid (Amiga) project.

This first GUI deliberately edits the lossless structured project rather than the
GAME binary directly.  Repacking is delegated to tools/cybernoid_project.py and is
blocked when structural validation reports errors.

Current safe scope:
- browse the logical 8-wide level layouts, including inactive holes;
- render all physical 20x11 rooms from the real 961-tile planar graphics bank;
- automatic gameplay palette selection (Palette B, with the Level-4 override);
- toggle to the Palette-A menu/high-score reference view;
- preview the actual shared 20x12 front-end/Hall-of-Fame faux room;
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
from cybernoid_entities import detect_room_entities, generic_controller_usage  # noqa: E402

WINDOW_W = 1440
WINDOW_H = 900
FPS = 60

ROOM_TILE_BASE = 16
ROOM_SCALE_DEFAULT = 2
ROOM_X = 320
ROOM_Y = 70

MAP_X = 20
MAP_Y = 80
MAP_CELL = 31
MAP_GAP = 3

CONTROL_X = 10
CONTROL_Y = 465
CONTROL_W = 290
CONTROL_H = 390

INFO_X = 985
INFO_Y = 70
INFO_W = 430
INFO_H = 350

PALETTE_X = 320
PALETTE_Y = 463
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
ENTITY_OUTLINE = (90, 220, 220)
ROLE_LIVE = (100, 230, 130)
ROLE_SKIPPED = (130, 135, 145)
ROLE_OVERFLOW = (255, 175, 70)
SUCCESS = (95, 215, 135)
BUTTON = (58, 61, 70)
BUTTON_ACTIVE = (58, 93, 118)
BUTTON_DISABLED = (38, 40, 46)


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


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """Wrap text to a pixel width without assuming a fixed character count."""
    if not text:
        return [""]
    words = text.split()
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_wrapped_text(surface: pygame.Surface, font: pygame.font.Font, text: str,
                      x: int, y: int, max_width: int, colour=TEXT,
                      line_gap: int = 2, max_lines: int | None = None) -> int:
    lines = wrap_text(font, text, max_width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            while font.size(lines[-1] + "…")[0] > max_width and lines[-1]:
                lines[-1] = lines[-1][:-1]
            lines[-1] += "…"
    line_h = font.get_linesize() + line_gap
    for i, line in enumerate(lines):
        draw_text(surface, font, line, x, y + i * line_h, colour)
    return max(1, len(lines)) * line_h


def format_audit_issue(issue) -> str:
    """Human-readable audit location + message for the editor UI."""
    loc: list[str] = []
    if issue.level is not None:
        loc.append(f"Level {issue.level}")
    if issue.logical_room is not None:
        loc.append(f"room {issue.logical_room}")
    elif issue.physical_room is not None:
        loc.append(f"physical room {issue.physical_room}")
    if issue.x is not None and issue.y is not None:
        loc.append(f"cell ({issue.x},{issue.y})")
    prefix = " / ".join(loc)
    return f"{prefix}: {issue.message}" if prefix else issue.message


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

        # Level/room selection must exist before tile surfaces are built because
        # automatic gameplay palette selection applies the Level-4 override.
        self.level_no = 1
        self.logical_room = int(self.model["fixed_blocks"]["start_rooms"][0])
        self.palette_mode = "gameplay"
        self.frontend_preview = False
        self.room_scale = ROOM_SCALE_DEFAULT
        self.show_grid = True
        self.help_visible = False
        self.hover_cell: tuple[int, int] | None = None
        self.inspect_cell: tuple[int, int] | None = None
        self.ui_buttons: list[tuple[pygame.Rect, str]] = []
        self.request_quit = False
        self.tiles = self._build_tiles()
        self.palette_scroll = 0
        self.selected_tile = 0
        self.show_markers = True
        self.show_entities = True
        self.edit_enabled = False
        self.modified = False
        self.undo_stack: list[tuple[int, int, int, int, int, int]] = []
        self.status = "Project loaded. Entity Overlay is display-only; use Help for colour meanings."
        self.status_kind = "info"
        self.last_file_action = "No file written this session."
        self.audit_summary, self.audit_issues = audit_project(self.model)
        self._ensure_selected_room_active()

    def _palette_words(self) -> list[int]:
        fixed = self.model["fixed_blocks"]
        if self.frontend_preview or self.palette_mode == "menu":
            return [int(v) for v in fixed["palette_a"]["words"]]
        base = [int(v) for v in fixed["palette_b"]["words"]]
        if self.level_no == 4:
            override = fixed.get("level4_palette_override", {}).get("words")
            if override is not None and len(override) == 8:
                base[:8] = [int(v) for v in override]
        return base

    def _build_tiles(self) -> list[pygame.Surface]:
        return decode_tile_surfaces(self.tile_bank, self._palette_words())

    @property
    def room_tile_px(self) -> int:
        return ROOM_TILE_BASE * self.room_scale

    @property
    def room_width_px(self) -> int:
        return 20 * self.room_tile_px

    @property
    def room_height_px(self) -> int:
        return 11 * self.room_tile_px

    @property
    def frontend_height_px(self) -> int:
        return 12 * self.room_tile_px

    def announce(self, message: str, kind: str = "info") -> None:
        self.status = message
        self.status_kind = kind

    def _max_palette_scroll(self) -> int:
        max_rows = math.ceil(len(self.tiles) / PALETTE_COLS)
        return max(0, max_rows - PALETTE_VISIBLE_ROWS)

    def scroll_palette(self, delta: int) -> None:
        self.palette_scroll = max(0, min(self._max_palette_scroll(), self.palette_scroll + delta))
        self.announce(
            f"Tile palette rows {self.palette_scroll}-{self.palette_scroll + PALETTE_VISIBLE_ROWS - 1}."
        )

    def toggle_grid(self) -> None:
        self.show_grid = not self.show_grid
        self.announce(f"Room grid {'ON' if self.show_grid else 'OFF'}.")

    def toggle_room_scale(self) -> None:
        self.room_scale = 1 if self.room_scale == 2 else 2
        self.announce(
            "Room display 1:1 Amiga pixels (320x176)."
            if self.room_scale == 1
            else "Room display 2x (640x352)."
        )

    def toggle_help(self) -> None:
        self.help_visible = not self.help_visible
        self.announce("Help opened." if self.help_visible else "Help closed.")

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
        self.frontend_preview = False
        self.level_no = level_no
        self.logical_room = int(self.model["fixed_blocks"]["start_rooms"][level_no - 1])
        self._ensure_selected_room_active()
        self.tiles = self._build_tiles()
        self.inspect_cell = None
        self.hover_cell = None
        suffix = "Level-4 override" if self.palette_mode == "gameplay" and level_no == 4 else self.palette_mode
        self.announce(f"Level {level_no} — palette: {suffix}")

    def select_logical(self, logical: int) -> None:
        slot = self.slot_by_logical(logical)
        if slot and slot.get("active"):
            self.logical_room = logical
            self.inspect_cell = None
            self.hover_cell = None
            self.announce(f"Selected L{self.level_no} logical room {logical} -> physical {slot['physical_id']}")

    def set_room_word(self, x: int, y: int, value: int) -> None:
        if not self.edit_enabled:
            self.announce("Editing is disabled. Use the Edit button or press E to enable raw editing.", "warning")
            return
        room = self.current_room()
        old = int(room["rows"][y][x])
        if old == value:
            return
        room["rows"][y][x] = int(value)
        self.undo_stack.append((self.level_no, self.current_physical(), x, y, old, int(value)))
        self.modified = True
        self.inspect_cell = (x, y)
        self.announce(f"L{self.level_no} R{self.logical_room} ({x},{y}): ${old:04X} -> ${value:04X}")
        refresh_project_derived(self.model)
        self.audit_summary, self.audit_issues = audit_project(self.model)

    def undo(self) -> None:
        if not self.undo_stack:
            self.announce("Nothing to undo.")
            return
        level_no, physical, x, y, old, new = self.undo_stack.pop()
        level = next(level for level in self.model["levels"] if int(level["level"]) == level_no)
        room = next(room for room in level["rooms"] if int(room["physical_id"]) == physical)
        room["rows"][y][x] = old
        self.modified = True
        refresh_project_derived(self.model)
        self.audit_summary, self.audit_issues = audit_project(self.model)
        self.inspect_cell = (x, y) if level_no == self.level_no and physical == self.current_physical() else None
        self.announce(f"Undo: L{level_no} physical {physical} ({x},{y}) ${new:04X} -> ${old:04X}")

    def save(self, quiet: bool = False) -> None:
        refresh_project_derived(self.model)
        self.audit_summary, self.audit_issues = audit_project(self.model)
        self.model_path.write_text(json.dumps(self.model, indent=2) + "\n", encoding="utf-8")
        self.modified = False
        self.last_file_action = f"SAVED: {self.model_path}"
        if not quiet:
            self.announce(
                f"SAVED project.json — {self.audit_summary['errors']} structural error(s).",
                "success" if not self.audit_summary["errors"] else "warning",
            )

    def repack(self) -> None:
        refresh_project_derived(self.model)
        self.audit_summary, self.audit_issues = audit_project(self.model)
        if self.audit_summary["errors"]:
            first = next(issue for issue in self.audit_issues if issue.severity == "error")
            detail = format_audit_issue(first)
            self.last_file_action = f"EXPORT BLOCKED: {detail}"
            self.announce(f"EXPORT BLOCKED — {detail}", "error")
            return
        self.save(quiet=True)
        try:
            repack_project(self.project_dir, self.output_path)
            self.last_file_action = f"EXPORTED: {self.output_path}"
            self.announce(f"EXPORTED fixed-size GAME -> {self.output_path}", "success")
        except Exception as exc:  # surface tool validation cleanly in GUI
            self.announce(f"EXPORT FAILED: {exc}", "error")

    def toggle_palette(self) -> None:
        if self.frontend_preview:
            self.announce("Front-end preview always uses Palette A. Use Front-End/F to return to gameplay rooms.")
            return
        self.palette_mode = "menu" if self.palette_mode == "gameplay" else "gameplay"
        self.tiles = self._build_tiles()
        if self.palette_mode == "menu":
            self.announce("Using Palette A menu/high-score reference palette (display only).")
        elif self.level_no == 4:
            self.announce("Using gameplay Palette B with the Level-4 override.")
        else:
            self.announce("Using normal gameplay Palette B.")

    def toggle_frontend_preview(self) -> None:
        fixed = self.model.get("fixed_blocks", {})
        if "frontend_room" not in fixed:
            self.announce("Front-end template is not in this project. Re-extract with project format v2.", "error")
            return
        self.frontend_preview = not self.frontend_preview
        self.tiles = self._build_tiles()
        if self.frontend_preview:
            self.announce("Front-end faux room: 20x12 template at $50F30 using Palette A (display only).")
        else:
            self.announce("Returned to gameplay room view.")

    def draw_button(self, rect: pygame.Rect, label: str, action: str, *,
                    active: bool = False, disabled: bool = False, tiny: bool = False) -> None:
        colour = BUTTON_DISABLED if disabled else (BUTTON_ACTIVE if active else BUTTON)
        pygame.draw.rect(self.screen, colour, rect, border_radius=4)
        pygame.draw.rect(self.screen, GRID, rect, 1, border_radius=4)
        font = self.tiny if tiny else self.small
        img = font.render(label, True, MUTED if disabled else TEXT)
        self.screen.blit(img, img.get_rect(center=rect.center))
        if not disabled:
            self.ui_buttons.append((rect.copy(), action))

    def handle_ui_action(self, action: str) -> None:
        if action.startswith("level_"):
            self.switch_level(int(action.split("_", 1)[1])); return
        if action == "palette": self.toggle_palette(); return
        if action == "frontend": self.toggle_frontend_preview(); return
        if action == "markers":
            self.show_markers = not self.show_markers
            self.announce(f"Marker Overlay {'ON' if self.show_markers else 'OFF'}.")
            return
        if action == "entities":
            self.show_entities = not self.show_entities
            self.announce(
                "Entity Overlay ON — cyan=owned cells; LIVE/SKIP/OVR are runtime allocation roles."
                if self.show_entities else "Entity Overlay OFF."
            )
            return
        if action == "grid": self.toggle_grid(); return
        if action == "zoom": self.toggle_room_scale(); return
        if action == "edit":
            self.edit_enabled = not self.edit_enabled
            self.announce("Raw editing ENABLED." if self.edit_enabled else "Raw editing disabled.",
                          "warning" if self.edit_enabled else "info")
            return
        if action == "undo": self.undo(); return
        if action == "save": self.save(); return
        if action == "export": self.repack(); return
        if action in ("help", "help_close"): self.toggle_help(); return
        if action == "tiles_up": self.scroll_palette(-1); return
        if action == "tiles_down": self.scroll_palette(1); return
        if action == "quit": self.request_quit = True; return

    def handle_button_click(self, pos: tuple[int, int]) -> bool:
        # Help is modal: only its own close button should respond while visible.
        if self.help_visible:
            for rect, action in reversed(self.ui_buttons):
                if action == "help_close" and rect.collidepoint(pos):
                    self.handle_ui_action(action)
                    return True
            return True
        for rect, action in reversed(self.ui_buttons):
            if rect.collidepoint(pos):
                self.handle_ui_action(action)
                return True
        return False

    def draw_controls(self) -> None:
        pygame.draw.rect(self.screen, PANEL, (CONTROL_X, CONTROL_Y, CONTROL_W, CONTROL_H), border_radius=5)
        draw_text(self.screen, self.title_font, "CONTROLS", CONTROL_X + 10, CONTROL_Y + 10)
        x0 = CONTROL_X + 10
        y = CONTROL_Y + 46

        # Level buttons replicate keys 1-4.
        for i in range(4):
            rect = pygame.Rect(x0 + i * 66, y, 60, 28)
            self.draw_button(rect, f"L{i+1} [{i+1}]", f"level_{i+1}", active=self.level_no == i + 1)
        y += 38

        self.draw_button(pygame.Rect(x0, y, 128, 30), "Palette [P]", "palette", active=self.palette_mode == "menu")
        self.draw_button(pygame.Rect(x0 + 138, y, 128, 30), "Front-End [F]", "frontend", active=self.frontend_preview)
        y += 40
        self.draw_button(pygame.Rect(x0, y, 128, 30), "Markers [M]", "markers", active=self.show_markers)
        self.draw_button(pygame.Rect(x0 + 138, y, 128, 30), "Entity Overlay [V]", "entities", active=self.show_entities, tiny=True)
        y += 40
        self.draw_button(pygame.Rect(x0, y, 82, 30), "Grid [G]", "grid", active=self.show_grid)
        self.draw_button(pygame.Rect(x0 + 92, y, 82, 30), "1:1 / 2x", "zoom", active=self.room_scale == 1)
        self.draw_button(pygame.Rect(x0 + 184, y, 82, 30), "Help [H]", "help")
        y += 40
        self.draw_button(pygame.Rect(x0, y, 128, 30), "Edit [E]", "edit", active=self.edit_enabled)
        self.draw_button(pygame.Rect(x0 + 138, y, 128, 30), "Undo [Ctrl+Z]", "undo", disabled=not self.undo_stack, tiny=True)
        y += 40
        self.draw_button(pygame.Rect(x0, y, 128, 32), "SAVE [Ctrl+S]", "save")
        self.draw_button(pygame.Rect(x0 + 138, y, 128, 32), "EXPORT [Ctrl+R]", "export")
        y += 44
        self.draw_button(pygame.Rect(x0, y, 266, 28), "Quit [Esc]", "quit")
        y += 39

        draw_text(self.screen, self.tiny, "Last file action:", x0, y, MUTED); y += 15
        if self.last_file_action == "No file written this session.":
            action_colour = MUTED
        elif self.last_file_action.startswith(("EXPORT BLOCKED", "EXPORT FAILED")):
            action_colour = ERROR
        else:
            action_colour = SUCCESS
        draw_wrapped_text(self.screen, self.tiny, self.last_file_action, x0, y, 266, action_colour, line_gap=0, max_lines=2)

    def draw_help(self) -> None:
        shade = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 185))
        self.screen.blit(shade, (0, 0))
        box = pygame.Rect(120, 55, 1200, 790)
        pygame.draw.rect(self.screen, PANEL, box, border_radius=8)
        pygame.draw.rect(self.screen, ACCENT, box, 2, border_radius=8)
        draw_text(self.screen, self.title_font, "CYBERNOID EDITOR — HELP", box.x + 24, box.y + 18)
        self.draw_button(pygame.Rect(box.right - 130, box.y + 16, 105, 30), "Close [H]", "help_close")

        left_x = box.x + 28
        right_x = box.x + 620
        col_w = 540
        y1 = box.y + 68
        y2 = y1

        def section(x: int, y: int, title: str, paragraphs: tuple[str, ...]) -> int:
            draw_text(self.screen, self.font, title, x, y, ACCENT)
            y += 27
            for paragraph in paragraphs:
                y += draw_wrapped_text(self.screen, self.small, paragraph, x, y, col_w, TEXT, line_gap=1)
                y += 5
            return y + 6

        y1 = section(left_x, y1, "GETTING AROUND", (
            "Use the Level 1–4 buttons, then click a numbered room on the map at the left.",
            "1:1 shows the room at the Amiga's real 320×176 pixel size. 2x makes it larger. Grid can be switched on or off separately.",
            "Front-End shows the real menu / Hall of Fame background. The game uses Palette A there. Gameplay uses Palette B, with the Level 4 colour change applied automatically.",
            "Scroll the tile list with the mouse wheel or the UP / DOWN buttons.",
        ))

        y1 = section(left_x, y1, "EDITING A ROOM", (
            "The editor starts safely in read-only mode. Click a room square to inspect it without changing anything.",
            "Press Edit only when you want direct tile painting. Pick a tile from the palette and left-click a room square to place it. Right-click copies the tile already there. Undo reverses the last paint change.",
            "Entity Overlay is a guide, not a separate editing mode yet. Cyan outlines show several map squares that the game treats as one object, such as a large cannon or a paired mechanism.",
            "A special marker replaces the normal tile in that map square. There is no hidden background tile stored underneath it, so the editor must not guess what should replace it when an object is moved or removed.",
        ))

        y1 = section(left_x, y1, "SAVING YOUR WORK", (
            "Save writes your edited project.json. It does not overwrite the original GAME file.",
            "Export creates GAME.patched (or the path supplied with --output). Export only runs when the safety checks pass.",
            "The 'Last file action' line tells you exactly what happened. If Export is blocked, the editor now names the level, room and map square causing the first error.",
        ))

        y2 = section(right_x, y2, "WHAT THE COLOURS MEAN", (
            "Cyan outline: these map squares belong to one recognised object.",
            "Green LIVE: this marker successfully creates its intended live object when the room loads.",
            "Grey SKIP: the marker is present in the room, but the game's object pool is already full so this one is skipped.",
            "Orange OVR: an extra crawler uses the game's shared overflow slot. Later extra crawler markers can overwrite that same slot.",
        ))

        y2 = section(right_x, y2, "THE SAFETY CHECK / AUDIT", (
            "Before Export, the editor checks that important relationships still make sense: starts, landing pads, portals, paired movers, compound objects and controller limits.",
            "Errors block Export. Warnings and information do not. The audit display gives the level, room and map square where possible.",
            "The original game contains a few unusual arrangements. Those are preserved deliberately rather than 'fixed' just because they look odd.",
        ))

        y2 = section(right_x, y2, "WHAT IS NOT IN THE UI YET", (
            "Object-aware Add / Move / Delete controls are being added next. The rules behind them are already tested, but direct tile painting is still the only editing method exposed in this build.",
            "A visual palette editor is also planned, including the menu palette, normal gameplay palette, Level 4 colour override and completion-screen palette.",
            "For the detailed research — addresses, room storage, special markers, object pools, enemy scripts and the reasons behind the safety rules — see docs/wiki/README.md in the repository.",
        ))

        ly = box.bottom - 38
        draw_text(self.screen, self.tiny, "Tip: Help is for using the editor. docs/wiki is the deeper technical reference.", box.x + 28, ly, MUTED)

    def draw_map_panel(self) -> None:
        pygame.draw.rect(self.screen, PANEL, (10, 55, 290, 400), border_radius=5)
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

    def draw_room(self) -> None:
        tile_px = self.room_tile_px
        room_w = 20 * tile_px
        room_h = 11 * tile_px
        frontend_h = 12 * tile_px

        if self.frontend_preview:
            fixed = self.model["fixed_blocks"]["frontend_room"]
            rows = fixed["rows"]
            pygame.draw.rect(self.screen, PANEL,
                             (ROOM_X - 8, ROOM_Y - 8, room_w + 16, frontend_h + 16),
                             border_radius=5)
            for y, row in enumerate(rows):
                for x, raw_value in enumerate(row):
                    value = int(raw_value)
                    dest = pygame.Rect(ROOM_X + x * tile_px, ROOM_Y + y * tile_px, tile_px, tile_px)
                    if 0 <= value < len(self.tiles):
                        if tile_px == 16:
                            self.screen.blit(self.tiles[value], dest)
                        else:
                            self.screen.blit(pygame.transform.scale(self.tiles[value], dest.size), dest)
                    else:
                        pygame.draw.rect(self.screen, ANOMALY, dest)
                    if self.show_grid:
                        pygame.draw.rect(self.screen, (0, 0, 0), dest, 1)
            draw_text(self.screen, self.font,
                      f"FRONT-END / HALL OF FAME FAUX ROOM  20x12  Palette A  "
                      f"[{'1:1' if self.room_scale == 1 else '2x'} display-only]",
                      ROOM_X, ROOM_Y - 31, MUTED)
            return

        room = self.current_room()
        pygame.draw.rect(self.screen, PANEL, (ROOM_X - 8, ROOM_Y - 8, room_w + 16, room_h + 16), border_radius=5)
        for y, row in enumerate(room["rows"]):
            for x, raw_value in enumerate(row):
                value = int(raw_value)
                dest = pygame.Rect(ROOM_X + x * tile_px, ROOM_Y + y * tile_px, tile_px, tile_px)
                if 0 <= value < len(self.tiles):
                    if tile_px == 16:
                        self.screen.blit(self.tiles[value], dest)
                    else:
                        self.screen.blit(pygame.transform.scale(self.tiles[value], dest.size), dest)
                else:
                    pygame.draw.rect(self.screen, ANOMALY, dest)
                    pygame.draw.line(self.screen, BG, dest.topleft, dest.bottomright, 1 if tile_px == 16 else 2)
                    pygame.draw.line(self.screen, BG, dest.topright, dest.bottomleft, 1 if tile_px == 16 else 2)
                    if tile_px >= 24:
                        img = self.tiny.render(f"{value:04X}", True, TEXT)
                        self.screen.blit(img, img.get_rect(center=dest.center))
                if self.show_grid:
                    pygame.draw.rect(self.screen, (0, 0, 0), dest, 1)
                if self.show_markers and value in MARKERS:
                    pygame.draw.rect(self.screen, MARKER_OUTLINE, dest, 1 if tile_px == 16 else 2)
                    if tile_px >= 24:
                        label = self.tiny.render(short_marker(value), True, MARKER_OUTLINE)
                        self.screen.blit(label, (dest.x + 2, dest.y + 1))

        if self.show_entities:
            for entity in detect_room_entities(room, self.level_no):
                # Cyan means proven ownership/grouping only; this is not an edit mode.
                if len(entity.cells) > 1:
                    for ex, ey, _ in entity.cells:
                        er = pygame.Rect(ROOM_X + ex * tile_px, ROOM_Y + ey * tile_px, tile_px, tile_px)
                        pygame.draw.rect(self.screen, ENTITY_OUTLINE, er, 1 if tile_px == 16 else 2)
                if entity.runtime_role:
                    er = pygame.Rect(ROOM_X + entity.x * tile_px, ROOM_Y + entity.y * tile_px, tile_px, tile_px)
                    if entity.runtime_role in ("live_primary", "dedicated_live"):
                        colour = ROLE_LIVE; tag = "LIVE"
                    elif entity.runtime_role == "overflow_slot76_live":
                        colour = ROLE_OVERFLOW; tag = "OVR"
                    else:
                        colour = ROLE_SKIPPED; tag = "SKIP"
                    pygame.draw.rect(self.screen, colour, er, 2 if tile_px == 16 else 3)
                    if tile_px >= 24:
                        img = self.tiny.render(tag, True, colour)
                        self.screen.blit(img, (er.x + 2, er.bottom - img.get_height() - 1))

        # Cursor/inspection highlight is independent of edit mode.
        inspect = self.hover_cell or self.inspect_cell
        if inspect is not None:
            ix, iy = inspect
            if 0 <= ix < 20 and 0 <= iy < 11:
                ir = pygame.Rect(ROOM_X + ix * tile_px, ROOM_Y + iy * tile_px, tile_px, tile_px)
                pygame.draw.rect(self.screen, SELECT, ir, 2)

        physical = self.current_physical()
        mode = "EDIT" if self.edit_enabled else "READ-ONLY"
        state_colour = WARNING if self.edit_enabled else MUTED
        zoom = "1:1" if self.room_scale == 1 else "2x"
        draw_text(self.screen, self.font,
                  f"L{self.level_no} logical {self.logical_room}  physical {physical}  {mode}  {zoom}",
                  ROOM_X, ROOM_Y - 31, state_colour)

    def draw_info(self) -> None:
        pygame.draw.rect(self.screen, PANEL, (INFO_X, INFO_Y, INFO_W, INFO_H), border_radius=5)
        inner_x = INFO_X + 12
        inner_w = INFO_W - 24
        if self.frontend_preview:
            draw_text(self.screen, self.title_font, "FRONT-END TEMPLATE", inner_x, INFO_Y + 10)
            y = INFO_Y + 48
            notes = (
                "20×12 menu / Hall of Fame background at runtime $50F30-$5110F.",
                "It uses Palette A. The Cybernoid logo is assembled from tiles $391-$3C0 in the first four rows.",
                "Menu text, scores and name-entry text are drawn separately over this background.",
                "This view is currently for preview only. It will also be used by the planned palette editor.",
            )
            for note in notes:
                y += draw_wrapped_text(self.screen, self.small, note, inner_x, y, inner_w, MUTED, line_gap=1) + 5
            return

        room = self.current_room()
        physical = self.current_physical()
        entities = detect_room_entities(room, self.level_no)
        usage = generic_controller_usage(room)

        draw_text(self.screen, self.title_font, "ROOM DATA / INSPECTOR", inner_x, INFO_Y + 10)
        y = INFO_Y + 45
        draw_text(self.screen, self.small, f"Room: Level {self.level_no}, logical {self.logical_room}, physical {physical}", inner_x, y); y += 19
        if self.palette_mode == "menu":
            palette_label = "Palette A — menu/high-score reference"
        elif self.level_no == 4:
            palette_label = "Palette B + Level 4 colour override"
        else:
            palette_label = "Palette B — gameplay"
        y += draw_wrapped_text(self.screen, self.small, f"Display palette: {palette_label}", inner_x, y, inner_w, TEXT, line_gap=0)
        draw_text(self.screen, self.small,
                  f"Room controllers: {usage['used']}/{usage['capacity']} used, {usage['free']} free",
                  inner_x, y, WARNING if usage['free'] <= 4 else TEXT); y += 19
        draw_text(self.screen, self.small, f"Recognised objects: {len(entities)}    Entity Overlay: {'ON' if self.show_entities else 'OFF'}",
                  inner_x, y); y += 19
        draw_text(self.screen, self.small, f"Selected paint tile: ${self.selected_tile:03X}", inner_x, y, SELECT); y += 23

        inspect = self.hover_cell or self.inspect_cell
        if inspect is None:
            y += draw_wrapped_text(self.screen, self.small, "Move over or click a room square to see what it contains. With Edit off, clicking only inspects it.",
                                   inner_x, y, inner_w, MUTED, line_gap=1)
        else:
            x, yy = inspect
            value = int(room["rows"][yy][x])
            draw_text(self.screen, self.small, f"Map square ({x},{yy}) — stored value ${value:04X}", inner_x, y, SELECT); y += 19
            if value in MARKERS:
                literal, kind = MARKERS[value]
                name = literal or kind.replace('_', ' ')
                y += draw_wrapped_text(self.screen, self.tiny, f"Special marker: {name}. This marker is the value stored in this square; there is no separate background tile underneath it.",
                                       inner_x + 6, y, inner_w - 6, MARKER_OUTLINE, line_gap=1)
            elif 0 <= value < 961:
                draw_text(self.screen, self.tiny, f"Normal graphic tile ${value:03X}.", inner_x + 6, y, MUTED); y += 16
            else:
                y += draw_wrapped_text(self.screen, self.tiny, "Unusual raw value. The editor preserves it exactly rather than trying to interpret it as a normal tile.",
                                       inner_x + 6, y, inner_w - 6, ANOMALY, line_gap=1)

            here = [e for e in entities if any(cx == x and cy == yy for cx, cy, _ in e.cells)]
            if here:
                entity = here[0]
                friendly_kind = entity.kind.replace('_', ' ')
                y += draw_wrapped_text(self.screen, self.tiny, f"Recognised object: {friendly_kind}.",
                                       inner_x + 6, y, inner_w - 6, ENTITY_OUTLINE, line_gap=1)
                if len(entity.cells) > 1:
                    coords = " ".join(f"({cx},{cy})" for cx, cy, _ in entity.cells[:6])
                    if len(entity.cells) > 6:
                        coords += " …"
                    y += draw_wrapped_text(self.screen, self.tiny, f"Map squares belonging to it: {coords}",
                                           inner_x + 6, y, inner_w - 6, MUTED, line_gap=1)
                if entity.runtime_role:
                    y += draw_wrapped_text(self.screen, self.tiny, f"When the room loads: {entity.runtime_role.replace('_', ' ')}.",
                                           inner_x + 6, y, inner_w - 6, MUTED, line_gap=1)

        errors = int(self.audit_summary["errors"])
        warnings = int(self.audit_summary["warnings"])
        info = int(self.audit_summary["info"])
        ay = INFO_Y + INFO_H - 88
        colour = ERROR if errors else (WARNING if warnings else SUCCESS)
        draw_text(self.screen, self.small, f"Safety check: {errors} errors / {warnings} warnings / {info} notes", inner_x, ay, colour)
        if errors:
            first = next(issue for issue in self.audit_issues if issue.severity == "error")
            detail = format_audit_issue(first)
            draw_wrapped_text(self.screen, self.tiny, detail, inner_x, ay + 21, inner_w, ERROR, line_gap=1, max_lines=3)
        else:
            draw_text(self.screen, self.tiny, "No blocking errors. Export is allowed.", inner_x, ay + 21, MUTED)

    def draw_palette(self) -> None:
        pygame.draw.rect(self.screen, PANEL, (PALETTE_X - 8, PALETTE_Y - 31, PALETTE_W + 16, PALETTE_H + 39), border_radius=5)
        draw_text(self.screen, self.font,
                  f"TILE / CONTROL PALETTE   rows {self.palette_scroll}-{self.palette_scroll + PALETTE_VISIBLE_ROWS - 1}",
                  PALETTE_X, PALETTE_Y - 26)
        self.draw_button(pygame.Rect(PALETTE_X + PALETTE_W - 148, PALETTE_Y - 29, 68, 24),
                         "UP", "tiles_up", disabled=self.palette_scroll <= 0)
        self.draw_button(pygame.Rect(PALETTE_X + PALETTE_W - 74, PALETTE_Y - 29, 68, 24),
                         "DOWN", "tiles_down", disabled=self.palette_scroll >= self._max_palette_scroll())
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

    def draw_frontend_palette_swatches(self) -> None:
        words = [int(v) for v in self.model["fixed_blocks"]["palette_a"]["words"]]
        x0 = ROOM_X
        y0 = ROOM_Y + self.frontend_height_px + 38
        draw_text(self.screen, self.font, "PALETTE A — MENU / HIGH SCORE", x0, y0 - 27)
        for i, word in enumerate(words):
            rect = pygame.Rect(x0 + i * 38, y0, 34, 34)
            pygame.draw.rect(self.screen, amiga_colour(word), rect)
            pygame.draw.rect(self.screen, GRID, rect, 1)
            draw_text(self.screen, self.tiny, f"{i:X}", rect.x + 12, rect.bottom + 3, MUTED)
            draw_text(self.screen, self.tiny, f"{word:03X}", rect.x + 4, rect.bottom + 18, MUTED)

    def draw_status(self) -> None:
        y = WINDOW_H - 40
        if self.status_kind == "success":
            bg = (34, 65, 49); colour = SUCCESS
        elif self.status_kind == "error":
            bg = (72, 38, 42); colour = ERROR
        elif self.status_kind == "warning":
            bg = (72, 58, 34); colour = WARNING
        else:
            bg = PANEL_2; colour = TEXT
        pygame.draw.rect(self.screen, bg, (0, y, WINDOW_W, 40))
        suffix = "  *modified*" if self.modified else ""
        draw_wrapped_text(self.screen, self.small, "STATUS: " + self.status + suffix,
                          14, y + 10, WINDOW_W - 28, colour, line_gap=0, max_lines=1)

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
        if self.frontend_preview:
            return None
        mx, my = pos
        if not pygame.Rect(ROOM_X, ROOM_Y, self.room_width_px, self.room_height_px).collidepoint(mx, my):
            return None
        return ((mx - ROOM_X) // self.room_tile_px, (my - ROOM_Y) // self.room_tile_px)

    def palette_hit(self, pos: tuple[int, int]) -> int | None:
        if self.frontend_preview:
            return None
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
            self.handle_ui_action(f"level_{event.key - pygame.K_0}")
        elif event.key == pygame.K_p:
            self.handle_ui_action("palette")
        elif event.key == pygame.K_f:
            self.handle_ui_action("frontend")
        elif event.key == pygame.K_m:
            self.handle_ui_action("markers")
        elif event.key == pygame.K_v:
            self.handle_ui_action("entities")
        elif event.key == pygame.K_g:
            self.handle_ui_action("grid")
        elif event.key == pygame.K_x:
            self.handle_ui_action("zoom")
        elif event.key == pygame.K_h:
            self.handle_ui_action("help")
        elif event.key == pygame.K_e:
            self.handle_ui_action("edit")
        elif ctrl and event.key == pygame.K_z:
            self.handle_ui_action("undo")
        elif ctrl and event.key == pygame.K_s:
            self.handle_ui_action("save")
        elif ctrl and event.key == pygame.K_r:
            self.handle_ui_action("export")

    def run(self) -> None:
        while not self.request_quit:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.request_quit = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.help_visible:
                            self.toggle_help()
                        else:
                            self.request_quit = True
                    else:
                        self.handle_key(event)
                elif event.type == pygame.MOUSEMOTION:
                    if not self.help_visible:
                        self.hover_cell = self.room_hit(event.pos)
                elif event.type == pygame.MOUSEWHEEL:
                    if self.help_visible:
                        continue
                    mx, my = pygame.mouse.get_pos()
                    if pygame.Rect(PALETTE_X, PALETTE_Y, PALETTE_W, PALETTE_H).collidepoint(mx, my):
                        self.scroll_palette(-event.y)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.handle_button_click(event.pos):
                        continue
                    if self.help_visible:
                        continue
                    if event.button == 1:
                        logical = self.map_hit(event.pos)
                        if logical is not None:
                            self.select_logical(logical)
                            continue
                        tile = self.palette_hit(event.pos)
                        if tile is not None:
                            self.selected_tile = tile
                            self.announce(f"Selected tile/control ${tile:03X}")
                            continue
                        hit = self.room_hit(event.pos)
                        if hit is not None:
                            self.inspect_cell = hit
                            if self.edit_enabled:
                                self.set_room_word(hit[0], hit[1], self.selected_tile)
                            else:
                                value = int(self.current_room()["rows"][hit[1]][hit[0]])
                                self.announce(f"Inspect ({hit[0]},{hit[1]}) raw ${value:04X}. See Room Data / Inspector.")
                    elif event.button == 3:
                        hit = self.room_hit(event.pos)
                        if hit is not None:
                            x, y = hit
                            self.inspect_cell = hit
                            value = int(self.current_room()["rows"][y][x])
                            if 0 <= value < 961:
                                self.selected_tile = value
                                self.announce(f"Eyedropper: ${value:03X} from ({x},{y})")
                            else:
                                self.announce(f"Raw anomalous word ${value:04X}; not selectable from tile palette.", "warning")

            self.screen.fill(BG)
            self.ui_buttons = []
            draw_text(self.screen, self.title_font, "CYBERNOID — AMIGA PROJECT EDITOR", 20, 17)
            self.draw_map_panel()
            self.draw_controls()
            self.draw_room()
            self.draw_info()
            if self.frontend_preview:
                self.draw_frontend_palette_swatches()
            else:
                self.draw_palette()
            self.draw_status()
            if self.help_visible:
                self.draw_help()
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

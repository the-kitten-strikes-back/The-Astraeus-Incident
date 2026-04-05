# fps_game Code (All .py Files)

## fps_game/main.py
Filename: `fps_game/main.py`

```python
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
```

## fps_game/core/__init__.py
Filename: `fps_game/core/__init__.py`

```python

```

## fps_game/core/game.py
Filename: `fps_game/core/game.py`

```python
import glob
import json
import os
import time
import math
import random

import pygame

from core.settings import (
    EFFECT_FILES,
    WIDTH,
    HEIGHT,
    HALF_HEIGHT,
    HALF_FOV,
    FOV,
    NUM_RAYS,
    SCALE,
    FPS,
    LEVELS_DIR,
    WEAPON_DEFAULT_IMG,
    ENEMY_IMG,
    get_music_for_level,
)
from core.level import load_level
from player.player import Player
from player.weapon import WeaponSystem
from enemies.ai import update_enemies
from systems.raycasting import raycast
from systems.combat import draw_health_packs
from systems.ui import (
    draw_crosshair,
    draw_level_hud,
    draw_ammo,
    draw_score,
    draw_hit_flash,
    draw_game_over,
    draw_weapon_info,
    draw_pause,
    draw_overlay_messages,
    draw_room_label,
    draw_scifi_hud,
)
from systems.minimap import draw_minimap
from systems.cutscene import draw_cutscene
from systems.grenades import GrenadeSystem
from systems.temporal import (
    TimeDilation,
    TimeRewind,
    TemporalEcho,
    FractureZones,
    TemporalVisuals,
    draw_temporal_hud,
)
from core.settings import (
    WALL_TEXTURE_FILES,
    FLOOR_TEXTURE_FILES,
    CEILING_TEXTURE_FILES,
    ENEMY_SPRITE_FILES,
    ROOM_NAME_MAP,
    ROOM_COLOR_MAP,
    ROOM_AMBIENCE_MAP,
    DOOR_IMG,
    TILE,
)
from systems.torch import Torch

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        pygame.event.set_allowed(None)
        pygame.event.set_allowed([
            pygame.QUIT, pygame.KEYDOWN, pygame.KEYUP,
            pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
        ])

        self.time_scale   = 1.0
        self.time_frozen  = False
        self.screen       = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        self.clock        = pygame.time.Clock()
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)

        self.hud_font = pygame.font.SysFont("arial", 22)

        self.current_music_level = -1
        self.music_enabled = True
        self.torch_enabled = False
        self.torch = Torch(pygame.image.load("fps_game/assets/images/torch.png"))
        self.weapon_image = pygame.image.load(WEAPON_DEFAULT_IMG).convert_alpha()
        self.enemy_sprite = pygame.image.load(ENEMY_IMG).convert_alpha()
        self.enemy_sprites  = self._load_enemy_sprites()
        self.wall_textures  = self._load_wall_textures()
        self.door_texture   = self._load_door_texture()
        self.floor_textures = self._load_tile_textures(FLOOR_TEXTURE_FILES, kind="floor")
        self.ceiling_textures = self._load_tile_textures(CEILING_TEXTURE_FILES, kind="ceiling")
        self.floor_texture   = self.floor_textures[0]
        self.ceiling_texture = self.ceiling_textures[0]
        (
            self.interior_floor_overlay,
            self.interior_grade,
            self.interior_vignette,
        ) = self._build_interior_layers()

        self.ceiling_big = self._build_ceiling_texture()

        self.weapon_system  = WeaponSystem(self.weapon_image)
        self.grenade_system = GrenadeSystem()

        self.time_dilation  = TimeDilation()
        self.time_rewind    = TimeRewind()
        self.temporal_echo  = TemporalEcho()
        self.fracture_zones = FractureZones()
        self.temporal_visuals = TemporalVisuals()

        self.level_paths = sorted(glob.glob(f"{LEVELS_DIR}/level*.txt"))
        if not self.level_paths:
            raise FileNotFoundError("No level files found in levels/ directory.")
        self.current_level_index  = 0
        self.level_complete_time  = None
        self.level_advance_delay  = 0.6

        self.world        = {}
        self.enemies      = []
        self.health_packs = []
        self.rooms        = {}
        self.doors        = {}
        self.depth_buffer = []

        self.player = Player(150, 150)

        self.score           = 0
        self.kills           = 0
        self.shake           = 0
        self.hit_flash       = 0
        self.hit_marker      = 0
        self.score_pulse     = 0
        self.game_over       = False
        self.restart_cooldown = 0
        self.mouse_dx        = 0
        self.last_mouse_dx   = 0
        self.anim_time       = 0.0
        self.bob_phase       = 0.0
        self.bob_offset      = 0.0
        self.bob_side        = 0.0
        self.screen_zoom     = 0.0
        self.chromatic_timer = 0
        self.ui_phase        = 0.0
        self.roll_angle      = 0.0
        self.vignette_timer  = 0
        self.cinematic_pulse = 0.0
        self.anomaly_timer   = 0
        self.anomaly_scale   = 1.0
        self.glitch_messages = []
        self.cutscene_index  = 0
        self.cutscene_time   = 0.0
        self.cutscene_return_state = "playing"
        self.ending_choice   = ""
        self.current_room    = ""
        self.current_room_key = ""
        self.room_timer      = 0
        self.room_tint       = (0, 0, 0)
        self.room_tint_alpha = 0
        self.room_scan       = False

        self.fps_counter  = 0
        self.fps_display  = 0
        self.fps_timer    = 0.0

        self.story_beats = [
            {
                "level": 0,
                "title": "ASTRAEUS // EMERGENCY DOCKING",
                "lines": [
                    "Deep-space research vessel Astraeus. Silent for six days.",
                    "Last transmission: experiment failure near the black hole.",
                    "Your orders: reach the reactor core. Find out what happened.",
                    "The ship is still running. The crew is not responding.",
                ],
                "animation": {
                    "scene": "arrival",
                    "title_anim": "fade",
                    "lines_anim": ["typewriter", "typewriter", "typewriter", "typewriter"],
                    "glitch_intensity": 0.0,
                },
            },
            {
                "level": 2,
                "title": "ACT I — THE SILENT SHIP",
                "lines": [
                    "The corridors are intact. No bodies. No distress signals.",
                    "Doors open a half-second before you reach them.",
                    "Something here knows where you're going.",
                    "Your suit clock keeps resetting to the same moment.",
                ],
                "animation": {
                    "scene": "ship_corridor",
                    "title_anim": "glitch",
                    "lines_anim": ["typewriter", "typewriter", "typewriter", "typewriter"],
                    "glitch_intensity": 0.10,
                },
            },
            {
                "level": 4,
                "title": "CREW LOG // DAY 3 — DR. YUEN",
                "lines": [
                    "The gravitational lens is working. We're harvesting dilation.",
                    "Time near the core runs at 0.4 relative. We didn't predict that.",
                    "Mira keeps saying she sees herself in the observation bay.",
                    "I told her it's a reflection. I'm not sure I believe that anymore.",
                ],
                "animation": {
                    "scene": "ship_corridor",
                    "title_anim": "fade",
                    "lines_anim": ["typewriter", "typewriter", "typewriter", "typewriter"],
                    "glitch_intensity": 0.12,
                },
            },
            {
                "level": 6,
                "title": "ASTRAEUS // TEMPORAL SHEAR EVENT",
                "lines": [
                    "Your suit registers a reality coherence drop of 61 percent.",
                    "The enemies you're fighting — they're not drones.",
                    "They're crew members. Stuck in loops between instants.",
                    "Repeating their last actions. Unaware they're already gone.",
                ],
                "animation": {
                    "scene": "crew_echo",
                    "title_anim": "glitch",
                    "lines_anim": ["typewriter", "glitch", "typewriter", "glitch"],
                    "glitch_intensity": 0.22,
                },
            },
            {
                "level": 8,
                "title": "ACT II — FRACTURED TIMELINES",
                "lines": [
                    "The ship no longer exists in one moment.",
                    "Every corridor you walk contains echoes of every decision made here.",
                    "You are passing through overlapping versions of the same place.",
                    "The experiment didn't tap into time. It shattered it.",
                ],
                "animation": {
                    "scene": "fracture",
                    "title_anim": "glitch",
                    "lines_anim": ["bounce", "typewriter", "bounce", "typewriter"],
                    "glitch_intensity": 0.35,
                },
            },
            {
                "level": 11,
                "title": "RECOVERED LOG // UNKNOWN TIMESTAMP",
                "lines": [
                    "The fracture didn't just split time. It created space between moments.",
                    "Something is living in that space.",
                    "It isn't biological. It isn't mechanical.",
                    "It is made entirely of observed outcomes.",
                ],
                "animation": {
                    "scene": "core_chamber",
                    "title_anim": "glitch",
                    "lines_anim": ["typewriter", "typewriter", "typewriter", "glitch"],
                    "glitch_intensity": 0.20,
                },
            },
            {
                "level": 13,
                "title": "ACT III — THE WATCHER",
                "lines": [
                    "It has no name. No body. No intention in any human sense.",
                    "But it is aware of you. It has watched every version of this moment.",
                    "It altered the crew's behavior. It is altering yours.",
                    "Every time you slow time or rewind — it learns from that too.",
                ],
                "animation": {
                    "scene": "entity_presence",
                    "title_anim": "glitch",
                    "lines_anim": ["glitch", "typewriter", "glitch", "typewriter"],
                    "glitch_intensity": 0.38,
                },
            },
            {
                "level": 15,
                "title": "ACT IV — WHAT YOU ARE",
                "lines": [
                    "You were sent here because you survived a temporal anomaly six years ago.",
                    "You don't age the same way. Your perception of time was already altered.",
                    "The entity isn't attacking you. It's been trying to communicate.",
                    "You are the only thread that runs through every version of this ship.",
                ],
                "animation": {
                    "scene": "all_timelines",
                    "title_anim": "fade",
                    "lines_anim": ["typewriter", "typewriter", "glitch", "bounce"],
                    "glitch_intensity": 0.44,
                },
            },
            {
                "level": 17,
                "title": "ACT V — THE CORE",
                "lines": [
                    "Reality collapses as you descend. Past and future are the same here.",
                    "You see yourself entering this ship. You see yourself never leaving.",
                    "You see the crew — alive — in the moment before the fracture.",
                    "The entity is waiting at the core. It already knows your choice.",
                ],
                "animation": {
                    "scene": "all_timelines",
                    "title_anim": "glitch",
                    "lines_anim": ["glitch", "bounce", "typewriter", "glitch"],
                    "glitch_intensity": 0.62,
                },
            },
        ]
        self.log_beats = {
            2:  "SUIT LOG: No life signs. Ship power at 94%. Something is maintaining it.",
            4:  "CREW LOG [MIRA]: The observation bay shows me standing there. I am not standing there.",
            6:  "SUIT LOG: Hostiles confirmed as crew biometrics. They are not aware of you.",
            8:  "DR. YUEN LOG: The lens collapsed inward. We didn't account for recursive dilation.",
            10: "SUIT LOG: Your temporal perception index is rising. This is not normal.",
            12: "UNKNOWN LOG: It watches through the gaps between seconds. Do not use your abilities near the core.",
            14: "SUIT LOG: The entity has modeled 4,219 versions of this mission. You have survived 3.",
            16: "SUIT LOG: Coherence at 12%. You are approaching the point of no return.",
            18: "ENTITY SIGNAL: You were always going to be here. We have been waiting across all of them.",
            19: "SUIT LOG: Core breach imminent. Choose carefully. Both outcomes are permanent.",
        }
        self.cutscene_map = self._build_cutscene_map()

        self.state    = "menu"
        self.settings = {"sensitivity": 0.003, "fullscreen": True}
        self.save_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "save.json"
        )
        self.load_save()
        self.load_current_level()
        self.save_game()

    def _load_wall_textures(self):
        textures = {}
        for key, path in WALL_TEXTURE_FILES.items():
            try:
                img = pygame.image.load(path).convert()
            except FileNotFoundError:
                img = pygame.Surface((64, 64))
                palette = {
                    "#": (28, 36, 52),
                    "A": (22, 34, 58),
                    "B": (34, 28, 50),
                    "C": (22, 40, 44),
                    "D": (38, 32, 26),
                }
                base = palette.get(key, (28, 36, 52))
                img.fill(base)
                seam = tuple(min(255, c + 22) for c in base)
                for y in range(0, 64, 16):
                    pygame.draw.line(img, seam, (0, y), (64, y), 1)
                rib = tuple(min(255, c + 35) for c in base)
                for x in range(0, 64, 32):
                    pygame.draw.line(img, rib, (x, 0), (x, 64), 2)
                rivet = tuple(min(255, c + 60) for c in base)
                for ry in range(0, 64, 16):
                    for rx in range(0, 64, 32):
                        pygame.draw.circle(img, rivet, (rx + 1, ry + 1), 2)
                hi = tuple(min(255, c + 9) for c in base)
                for y in range(1, 64, 16):
                    pygame.draw.line(img, hi, (0, y), (64, y), 1)
            textures[key] = pygame.transform.scale(img, (64, 64))
        return textures

    def _build_ceiling_texture(self, room_tint=None, room_tint_alpha=0):
        surf = pygame.Surface((WIDTH, HALF_HEIGHT))
        surf.fill((8, 10, 18))

        panel_w = WIDTH // 6
        panel_h = HALF_HEIGHT // 3

        for row in range(4):
            for col in range(7):
                px = col * panel_w
                py = row * panel_h
                variant = (row + col) % len(self.ceiling_textures)
                tex = self.ceiling_textures[variant]
                scaled = pygame.transform.smoothscale(tex, (panel_w, panel_h))
                surf.blit(scaled, (px, py))
                seam_color = (30, 40, 60)
                pygame.draw.rect(surf, seam_color,
                                 pygame.Rect(px, py, panel_w, panel_h), 1)

        rib_color = (40, 55, 80)
        for y in range(0, HALF_HEIGHT, panel_h):
            pygame.draw.line(surf, rib_color, (0, y), (WIDTH, y), 2)
        for x in range(0, WIDTH, panel_w):
            pygame.draw.line(surf, rib_color, (x, 0), (x, HALF_HEIGHT), 2)

        for col in range(6):
            for row in range(3):
                if (row + col) % 3 != 0:
                    continue
                bx = col * panel_w + panel_w // 4
                by = row * panel_h + panel_h // 3
                bw = panel_w // 2
                bh = 5
                bar_color = (210, 215, 185)
                if room_tint and room_tint_alpha > 0:
                    rt = room_tint
                    mix = room_tint_alpha / 255
                    bar_color = (
                        int(bar_color[0] * (1 - mix) + rt[0] * mix),
                        int(bar_color[1] * (1 - mix) + rt[1] * mix),
                        int(bar_color[2] * (1 - mix) + rt[2] * mix),
                    )
                glow_surf = pygame.Surface((bw + 16, bh + 10), pygame.SRCALPHA)
                glow_surf.fill((80, 90, 60, 40))
                surf.blit(glow_surf, (bx - 8, by - 5))
                pygame.draw.rect(surf, bar_color, (bx, by, bw, bh))
                pygame.draw.rect(surf, (50, 55, 40), (bx, by + bh, bw, 3))

        rivet_color = (60, 75, 100)
        for y in range(0, HALF_HEIGHT, panel_h):
            for x in range(0, WIDTH, panel_w):
                pygame.draw.circle(surf, rivet_color, (x, y), 3)

        if room_tint and room_tint_alpha > 0:
            tint_surf = pygame.Surface((WIDTH, HALF_HEIGHT), pygame.SRCALPHA)
            tint_surf.fill((*room_tint, room_tint_alpha // 2))
            surf.blit(tint_surf, (0, 0))

        gradient = pygame.Surface((WIDTH, HALF_HEIGHT), pygame.SRCALPHA)
        for y in range(HALF_HEIGHT):
            ratio = y / HALF_HEIGHT
            alpha = int(180 * (1.0 - ratio))
            pygame.draw.line(gradient, (0, 0, 0, alpha), (0, y), (WIDTH, y))
        surf.blit(gradient, (0, 0))

        tint = pygame.Surface((WIDTH, HALF_HEIGHT), pygame.SRCALPHA)
        tint.fill((10, 20, 40, 35))
        surf.blit(tint, (0, 0))

        return surf

    def _load_enemy_sprites(self):
        sprites = {}
        for key, path in ENEMY_SPRITE_FILES.items():
            try:
                img = pygame.image.load(path).convert_alpha()
            except FileNotFoundError:
                img = None
            sprites[key] = img
        return sprites

    def _load_door_texture(self):
        try:
            img = pygame.image.load(DOOR_IMG).convert()
        except FileNotFoundError:
            img = pygame.Surface((64, 64))
            img.fill((90, 90, 110))
            pygame.draw.rect(img, (140, 140, 160), (8, 8, 48, 48), 2)
            pygame.draw.line(img, (160, 160, 180), (32, 8), (32, 56), 1)
        return pygame.transform.scale(img, (64, 64))

    def _build_cutscene_map(self):
        font  = pygame.font.SysFont("arial", 14, bold=True)
        rooms = [
            {"name": "Dock",    "x":  20, "y":  20, "w":  90, "h": 50, "color": (60, 120, 180)},
            {"name": "Bridge",  "x": 140, "y":  20, "w": 120, "h": 50, "color": (90, 150, 220)},
            {"name": "Crew",    "x":  20, "y":  90, "w": 120, "h": 60, "color": (140, 120, 70)},
            {"name": "Medbay",  "x": 160, "y":  90, "w": 100, "h": 60, "color": (80, 170, 220)},
            {"name": "Lab",     "x": 280, "y":  80, "w": 140, "h": 70, "color": (90, 200, 130)},
            {"name": "Cargo",   "x":  20, "y": 170, "w": 140, "h": 60, "color": (140, 100, 60)},
            {"name": "Hangar",  "x": 190, "y": 170, "w": 140, "h": 60, "color": (120, 120, 180)},
            {"name": "Core",    "x": 360, "y": 170, "w": 120, "h": 60, "color": (200, 80, 60)},
        ]
        links = [
            {"a": (110, 45), "b": (140, 45)},
            {"a": (80, 110), "b": (160, 110)},
            {"a": (260, 110), "b": (280, 110)},
            {"a": (90, 200), "b": (190, 200)},
            {"a": (330, 200), "b": (360, 200)},
        ]
        return {"rooms": rooms, "links": links, "font": font}

    def _load_tile_textures(self, paths, kind="floor"):
        textures = []
        for idx, path in enumerate(paths):
            try:
                img = pygame.image.load(path).convert()
            except FileNotFoundError:
                img = pygame.Surface((64, 64))

                if kind == "ceiling":
                    bases = [(12, 16, 24), (10, 14, 22), (16, 18, 28)]
                    base  = bases[idx % len(bases)]
                    img.fill(base)
                    grid = tuple(min(255, c + 20) for c in base)
                    for y in range(0, 64, 16):
                        pygame.draw.line(img, grid, (0, y), (64, y), 1)
                    for x in range(0, 64, 16):
                        pygame.draw.line(img, grid, (x, 0), (x, 64), 1)
                    strip_x = [8, 40, 24][idx % 3]
                    pygame.draw.rect(img, (200, 210, 180), (strip_x, 26, 16, 4))
                    pygame.draw.rect(img, (55, 60, 45),    (strip_x - 2, 30, 20, 3))

                else:
                    bases = [(18, 22, 26), (20, 18, 24), (16, 24, 28)]
                    base  = bases[idx % len(bases)]
                    img.fill(base)
                    grid = tuple(min(255, c + 30) for c in base)
                    for y in range(0, 64, 16):
                        pygame.draw.line(img, grid, (0, y), (64, y), 1)
                    for x in range(0, 64, 16):
                        pygame.draw.line(img, grid, (x, 0), (x, 64), 1)
                    sub = tuple(min(255, c + 10) for c in base)
                    for y in range(0, 64, 8):
                        pygame.draw.line(img, sub, (0, y), (64, y), 1)
                    if idx == 1:
                        pygame.draw.line(img, (55, 45, 15), (0, 0),  (64, 64), 2)
                        pygame.draw.line(img, (55, 45, 15), (0, 16), (48, 64), 1)
                    hi = tuple(min(255, c + 7) for c in base)
                    pygame.draw.rect(img, hi, (2, 2, 28, 28))

            textures.append(pygame.transform.scale(img, (64, 64)))
        return textures

    def _build_interior_layers(self):
        floor = pygame.Surface((WIDTH, HALF_HEIGHT), pygame.SRCALPHA)
        for y in range(HALF_HEIGHT):
            ratio = y / HALF_HEIGHT
            alpha = int(190 * ratio)
            pygame.draw.line(floor, (3, 5, 10, alpha), (0, y), (WIDTH, y))
        grid_col = (40, 180, 220, 25)
        for x in range(0, WIDTH + 1, 80):
            pygame.draw.line(floor, grid_col, (x, 0), (WIDTH // 2, HALF_HEIGHT - 1), 1)
        for y in range(0, HALF_HEIGHT, 60):
            pygame.draw.line(floor, (50, 80, 110, 18), (0, y), (WIDTH, y), 1)
        cc = (30, 80, 120, 65)
        pygame.draw.rect(floor, cc, (0, HALF_HEIGHT - 80, 200, 80), 2)
        for i in range(5):
            pygame.draw.line(floor, cc, (8, HALF_HEIGHT - 70 + i * 14),
                             (192, HALF_HEIGHT - 70 + i * 14), 1)
        pygame.draw.rect(floor, cc, (WIDTH - 200, HALF_HEIGHT - 100, 200, 100), 2)
        for i in range(6):
            pygame.draw.line(floor, cc,
                             (WIDTH - 192, HALF_HEIGHT - 90 + i * 14),
                             (WIDTH - 8,   HALF_HEIGHT - 90 + i * 14), 1)

        grade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        grade.fill((4, 8, 18, 26))
        pygame.draw.rect(grade, (0, 4, 12, 38), (0, 0, WIDTH, HALF_HEIGHT))

        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (0, 0, 0, 115), vignette.get_rect())
        inner = pygame.Rect(55, 38, WIDTH - 110, HEIGHT - 76)
        pygame.draw.rect(vignette, (0, 0, 0, 0), inner)

        return floor, grade, vignette

    def load_current_level(self):
        self.world, self.enemies, self.health_packs, spawn, self.rooms, self.doors = load_level(
            self.level_paths[self.current_level_index]
        )
        self.player.x, self.player.y = spawn
        if self.floor_textures:
            self.floor_texture = self.floor_textures[self.current_level_index % len(self.floor_textures)]
        if self.ceiling_textures:
            self.ceiling_texture = self.ceiling_textures[self.current_level_index % len(self.ceiling_textures)]
        self.ceiling_big = self._build_ceiling_texture()
        self.current_room     = ""
        self.current_room_key = ""
        self.room_tint        = (0, 0, 0)
        self.room_tint_alpha  = 0
        self.room_scan        = False
        self.time_rewind._history.clear()
        self.temporal_echo._recording.clear()
        self.fracture_zones.leave_room()
        self.play_music_for_level(self.current_level_index)

    def load_save(self):
        if not os.path.exists(self.save_path):
            return
        try:
            with open(self.save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        self.current_level_index = int(data.get("level", 0))
        self.current_level_index = max(0, min(self.current_level_index, len(self.level_paths) - 1))
        self.score  = int(data.get("score", 0))
        self.kills  = int(data.get("kills", 0))
        self.player.health = int(data.get("health", self.player.max_health))
        self.player.health = max(0, min(self.player.health, self.player.max_health))
        sensitivity = data.get("sensitivity")
        if isinstance(sensitivity, (int, float)):
            self.settings["sensitivity"] = float(sensitivity)
        fullscreen = data.get("fullscreen")
        if isinstance(fullscreen, bool):
            self.settings["fullscreen"] = fullscreen
            if self.settings["fullscreen"]:
                self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
            else:
                self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        ammo = data.get("ammo")
        if isinstance(ammo, list):
            for weapon, value in zip(self.player.weapons, ammo):
                try:
                    weapon.ammo = max(0, min(int(value), weapon.max_ammo))
                except (TypeError, ValueError):
                    continue

    def save_game(self):
        data = {
            "level":       self.current_level_index,
            "score":       self.score,
            "kills":       self.kills,
            "health":      self.player.health,
            "sensitivity": self.settings.get("sensitivity", 0.003),
            "fullscreen":  self.settings.get("fullscreen", True),
            "ammo":        [w.ammo for w in self.player.weapons],
        }
        try:
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def _blit_tiled(self, target, texture, rect):
        tx = texture.get_width()
        ty = texture.get_height()
        for y in range(rect.top, rect.bottom, ty):
            for x in range(rect.left, rect.right, tx):
                target.blit(texture, (x, y))

    def _blit_stretched(self, target, texture, rect):
        scaled = pygame.transform.smoothscale(texture, (rect.width, rect.height))
        target.blit(scaled, (rect.left, rect.top))

    def _toggle_nearby_door(self):
        if not self.doors:
            return
        closest      = None
        closest_dist = 9999
        for (x, y), door in self.doors.items():
            dx   = (x + TILE // 2) - self.player.x
            dy   = (y + TILE // 2) - self.player.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < 90 and dist < closest_dist:
                closest      = (x, y)
                closest_dist = dist
        if closest:
            self.doors[closest]["open"] = not self.doors[closest]["open"]

    def advance_level(self):
        if self.current_level_index + 1 < len(self.level_paths):
            self.current_level_index += 1
            self.load_current_level()
            try:
                if os.path.exists(EFFECT_FILES["level_up"]):
                    pygame.mixer.Sound(EFFECT_FILES["level_up"]).play()
            except (KeyError, pygame.error):
                pass
            self.level_complete_time = None
            self.save_game()
            if self.current_level_index in self.log_beats:
                self.glitch_messages.append({"text": self.log_beats[self.current_level_index], "timer": 50})
            for i, beat in enumerate(self.story_beats):
                if beat["level"] == self.current_level_index:
                    self.cutscene_index        = i
                    self.cutscene_time         = 0.0
                    self.cutscene_return_state = "playing"
                    self.state                 = "cutscene"
                    break
        else:
            self.state = "ending_choice"

    def reset_game(self):
        self.current_level_index = 0
        self.load_current_level()
        self.level_complete_time  = None
        self.player.health        = self.player.max_health
        self.player.invincibility_frames = 0
        self.hit_flash            = 0
        self.game_over            = False
        self.restart_cooldown     = 15
        self.shake                = 0
        self.score                = 0
        self.kills                = 0
        self.ending_choice        = ""
        self.time_dilation  = TimeDilation()
        self.time_rewind    = TimeRewind()
        self.temporal_echo  = TemporalEcho()
        self.fracture_zones = FractureZones()
        self.temporal_visuals = TemporalVisuals()
        for weapon in self.player.weapons:
            weapon.ammo = weapon.max_ammo
        self.weapon_system.reloading    = False
        self.weapon_system.reload_timer = 0
        self.save_game()

    def on_player_hit(self, enemy):
        damage = enemy.get("damage", 10)
        if self.player.apply_damage(damage):
            try:
                if os.path.exists(EFFECT_FILES["player_hit"]):
                    pygame.mixer.Sound(EFFECT_FILES["player_hit"]).play()
            except (KeyError, pygame.error):
                pass
            self.hit_flash       = 12
            self.shake           = 10
            self.screen_zoom     = 0.06
            self.chromatic_timer = 12
            self.vignette_timer  = 20
            self.cinematic_pulse = 1.0
            enemy["attack_frame"] = 5
            if self.player.health <= 0:
                self.game_over = True
                self.save_game()

    def toggle_fullscreen(self):
        self.settings["fullscreen"] = not self.settings["fullscreen"]
        if self.settings["fullscreen"]:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.save_game()

    def play_music_for_level(self, level):
        if not self.music_enabled:
            return
        if self.current_music_level == level:
            return
        music_path = get_music_for_level(level)
        if music_path and os.path.exists(music_path):
            try:
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(0.6)
                pygame.mixer.music.play(-1)
                self.current_music_level = level
            except pygame.error as e:
                print(f"Failed to load music {music_path}: {e}")

    def handle_events(self):
        pygame.event.pump()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if self.state == "menu":
                    if event.key == pygame.K_RETURN:
                        self.cutscene_index        = 0
                        self.cutscene_time         = 0.0
                        self.cutscene_return_state = "playing"
                        self.state                 = "cutscene"
                    elif event.key == pygame.K_s:
                        self.state = "settings"

                elif self.state == "settings":
                    if event.key == pygame.K_UP:
                        self.settings["sensitivity"] += 0.001
                    if event.key == pygame.K_DOWN:
                        self.settings["sensitivity"] = max(0.001, self.settings["sensitivity"] - 0.001)
                    if event.key == pygame.K_ESCAPE:
                        self.state = "menu"

                elif self.state == "playing":
                    if event.key == pygame.K_1:
                        self.player.current_weapon_index = 0
                    if event.key == pygame.K_2:
                        self.player.current_weapon_index = 1
                    if event.key == pygame.K_3:
                        self.player.current_weapon_index = 2
                    if event.key == pygame.K_9:
                        self.torch_enabled = not self.torch_enabled
                    if event.key == pygame.K_ESCAPE:
                        self.state = "pause"
                    if event.key == pygame.K_f:
                        self.time_frozen = not self.time_frozen
                        self.time_scale  = 0.1 if self.time_frozen else 1.0
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()
                    if event.key == pygame.K_e:
                        self._toggle_nearby_door()
                    if event.key == pygame.K_z:
                        self.grenade_system.try_throw("space",   self.player)
                    if event.key == pygame.K_x:
                        self.grenade_system.try_throw("smoke",   self.player)
                    if event.key == pygame.K_c:
                        self.grenade_system.try_throw("stun",    self.player)
                    if event.key == pygame.K_v:
                        self.grenade_system.try_throw("nuclear", self.player)
                    if event.key == pygame.K_q:
                        self.time_dilation.toggle()
                        if self.time_dilation.active:
                            self.glitch_messages.append(
                                {"text": "TIME DILATION ACTIVE", "timer": 40}
                            )
                    if event.key == pygame.K_t:
                        if self.time_rewind.can_rewind():
                            if self.time_rewind.trigger():
                                self.temporal_visuals.trigger_glitch(strength=1.6)
                                self.glitch_messages.append(
                                    {"text": "TEMPORAL REWIND ACTIVATED", "timer": 50}
                                )
                                self.shake = 14
                    if event.key == pygame.K_g:
                        if self.temporal_echo.spawn(self.player):
                            self.glitch_messages.append(
                                {"text": "TEMPORAL ECHO SPAWNED", "timer": 40}
                            )

                elif self.state == "pause":
                    if event.key == pygame.K_ESCAPE:
                        self.state = "playing"
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()

                elif self.state == "cutscene":
                    if event.key == pygame.K_RETURN:
                        self.state = self.cutscene_return_state

                elif self.state == "ending_choice":
                    if event.key == pygame.K_1:
                        self.ending_choice         = "containment"
                        self.cutscene_time         = 0.0
                        self.cutscene_return_state = "menu"
                        self.state                 = "cutscene"
                    if event.key == pygame.K_2:
                        self.ending_choice         = "ascension"
                        self.cutscene_time         = 0.0
                        self.cutscene_return_state = "loop"
                        self.state                 = "cutscene"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.state == "cutscene":
                self.state = self.cutscene_return_state

            if event.type == pygame.MOUSEMOTION:
                if self.state == "playing" and not self.game_over:
                    self.mouse_dx += event.rel[0]

                mouse_x, mouse_y = pygame.mouse.get_pos()
                wrapped_x, wrapped_y = mouse_x, mouse_y
                if mouse_x <= 0:
                    wrapped_x = WIDTH - 2
                elif mouse_x >= WIDTH - 1:
                    wrapped_x = 1
                if mouse_y <= 0:
                    wrapped_y = HEIGHT - 2
                elif mouse_y >= HEIGHT - 1:
                    wrapped_y = 1
                if wrapped_x != mouse_x or wrapped_y != mouse_y:
                    pygame.mouse.set_pos(wrapped_x, wrapped_y)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "playing" and not self.game_over:
                    score_delta, kills_delta, hit_any, fired = self.weapon_system.try_shoot(
                        time.time(), self.player, self.enemies, self.depth_buffer
                    )
                    self.score  += score_delta
                    self.kills  += kills_delta
                    if score_delta or kills_delta:
                        self.score_pulse = 10
                    if hit_any:
                        self.hit_marker      = 6
                        self.chromatic_timer = max(self.chromatic_timer, 4)
                    if fired:
                        try:
                            if os.path.exists(EFFECT_FILES["laser"]):
                                pygame.mixer.Sound(EFFECT_FILES["laser"]).play()
                        except (KeyError, pygame.error):
                            pass
                        self.screen_zoom     = max(self.screen_zoom, 0.03)
                        self.chromatic_timer = max(self.chromatic_timer, 4)
                        self.cinematic_pulse = max(self.cinematic_pulse, 0.5)

        return True

    def update(self):
        if self.state not in {"playing", "loop"}:
            if self.state == "cutscene":
                self.cutscene_time += 0.06
            return

        dil_world, dil_player = self.time_dilation.update()

        frac_world  = self.fracture_zones.get_world_scale()
        frac_player = self.fracture_zones.get_player_scale()

        base_world_scale  = self.time_scale * dil_world
        base_player_scale = self.time_scale * dil_player

        effective_world  = base_world_scale  * abs(frac_world)
        effective_player = base_player_scale * abs(frac_player)

        reverse_controls = (frac_player < 0) or (frac_world < 0)

        self.fracture_zones.update()
        self.temporal_echo.update()
        self.temporal_visuals.update(
            self.time_dilation.active,
            self.time_dilation.energy_ratio,
        )

        if not self.game_over:
            keys = pygame.key.get_pressed()
            mx   = self.mouse_dx
            self.mouse_dx      = 0
            self.last_mouse_dx = mx

            self.time_rewind.record(self.player, self.enemies)
            self.temporal_echo.record(self.player)

            if self.time_dilation.active:
                self.temporal_visuals.record_trail(
                    self.player, self.time_dilation.energy_ratio
                )

            rewinding = self.time_rewind.update(self.player, self.enemies)
            if rewinding:
                self._finish_frame_counters()
                return

            self.player.mouse_sensitivity = self.settings["sensitivity"]

            effective_mx = -mx if reverse_controls else mx
            self.player.move(self.world, effective_mx, self.doors, speed_scale=effective_player)

            room_key = self.rooms.get(
                (int(self.player.x // TILE) * TILE, int(self.player.y // TILE) * TILE)
            )
            if room_key and ROOM_NAME_MAP.get(room_key) != self.current_room:
                self.current_room_key = room_key
                self.current_room     = ROOM_NAME_MAP.get(room_key, "")
                self.room_timer = 90
                ambience = ROOM_AMBIENCE_MAP.get(room_key)
                if ambience:
                    self.room_tint       = ambience["tint"]
                    self.room_tint_alpha = ambience["alpha"]
                    self.room_scan       = ambience["scan"]
                    if self.floor_textures:
                        self.floor_texture = self.floor_textures[ambience["floor"] % len(self.floor_textures)]
                    if self.ceiling_textures:
                        self.ceiling_texture = self.ceiling_textures[ambience["ceiling"] % len(self.ceiling_textures)]
                self.fracture_zones.enter_room(room_key)
                if self.fracture_zones.active_effect:
                    self.glitch_messages.append(
                        {"text": self.fracture_zones.message, "timer": 60}
                    )
                self.ceiling_big = self._build_ceiling_texture(
                    room_tint=self.room_tint,
                    room_tint_alpha=self.room_tint_alpha,
                )
            elif not room_key and self.current_room_key:
                self.current_room_key = ""
                self.current_room     = ""
                self.room_tint        = (0, 0, 0)
                self.room_tint_alpha  = 0
                self.room_scan        = False
                self.fracture_zones.leave_room()
                if self.floor_textures:
                    self.floor_texture = self.floor_textures[self.current_level_index % len(self.floor_textures)]
                if self.ceiling_textures:
                    self.ceiling_texture = self.ceiling_textures[self.current_level_index % len(self.ceiling_textures)]
                self.ceiling_big = self._build_ceiling_texture()

            focus_scale = 1.6 if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1.0
            if self.time_frozen:
                focus_scale = 0.1
            if self.anomaly_timer > 0:
                self.anomaly_timer -= 1
            else:
                if random.random() < 0.012:
                    self.anomaly_timer = random.randint(25, 80)
                    self.anomaly_scale = random.uniform(0.4, 1.6)
                    msg = random.choice([
                        "SUIT: REALITY COHERENCE DROPPING",
                        "ASTRAEUS: TEMPORAL SHEAR ACTIVE",
                        "CREW ECHO DETECTED IN SECTOR",
                        "WARNING: RECURSIVE DILATION EVENT",
                        "ENTITY SIGNAL: WE SEE YOU",
                        "SUIT: TIMELINE FORK — UNDEFINED",
                        "DR. YUEN LOG: IT KNOWS WE'RE HERE",
                        "CORE RESONANCE: CRITICAL",
                        "ENTITY: YOU HAVE BEEN HERE BEFORE",
                        "SUIT: CLOCK DESYNC — RESETTING",
                    ])
                    self.glitch_messages.append({"text": msg, "timer": 28})

            effective_time = effective_world * focus_scale * self.anomaly_scale

            self.weapon_system.update_reload(self.player)
            if self.torch_enabled:
                self.torch.draw_light(self.screen, int(self.player.x), int(self.player.y))
                self.torch.draw_sprite(self.screen, int(self.player.x), int(self.player.y))

            update_enemies(
                self.enemies, self.player, self.world, self.doors,
                self.on_player_hit, effective_time,
            )
            events = self.grenade_system.update(
                self.world, self.doors, self.enemies, effective_time
            )
            if events["shake"] > 0:
                self.shake           = max(self.shake, events["shake"])
            if events["flash"] > 0:
                self.hit_flash       = max(self.hit_flash, events["flash"])
            if events["chroma"] > 0:
                self.chromatic_timer = max(self.chromatic_timer, events["chroma"])
            if events["zoom"] > 0:
                self.screen_zoom     = max(self.screen_zoom, events["zoom"])

            level_cleared = (not self.enemies) or all(not e["alive"] for e in self.enemies)
            if level_cleared and self.state == "playing":
                if self.level_complete_time is None:
                    self.level_complete_time = time.time()
                elif time.time() - self.level_complete_time >= self.level_advance_delay:
                    self.advance_level()
            else:
                self.level_complete_time = None

            if self.state == "loop":
                if len([e for e in self.enemies if e["alive"]]) < 4:
                    self.glitch_messages.append(
                        {"text": "LOOP STABLE // ENEMIES RESPAWN", "timer": 30}
                    )
                    from enemies.enemy import create_enemy
                    for _ in range(3):
                        self.enemies.append(
                            create_enemy(
                                random.choice(["normal", "fast", "tank", "ranged"]),
                                self.player.x + random.randint(-120, 120),
                                self.player.y + random.randint(-120, 120),
                            )
                        )
                if self.player.health <= 0:
                    self.player.health = self.player.max_health
                    self.game_over     = False

        self._finish_frame_counters()

    def _finish_frame_counters(self):
        self.weapon_system.update_recoil()
        self.weapon_system.update_sway(-self.last_mouse_dx * 0.4, -self.last_mouse_dx * 0.15)
        self.player.update_invincibility()
        effective_time = self.time_scale * self.time_dilation.world_scale
        self.weapon_system.update_bullets(self.world, self.enemies, effective_time)

        self.anim_time  += 0.12 * self.time_scale
        move_amount      = self.player.move_amount
        if move_amount > 0.01:
            self.bob_phase += 0.32 * move_amount
        else:
            self.bob_phase += 0.04
        self.bob_offset = math.sin(self.bob_phase) * 6 * move_amount
        self.bob_side   = math.sin(self.bob_phase * 0.5) * 3 * move_amount

        if self.hit_flash > 0:        self.hit_flash        -= 1
        if self.hit_marker > 0:       self.hit_marker        -= 1
        if self.score_pulse > 0:      self.score_pulse       -= 1
        if self.room_timer > 0:       self.room_timer         -= 1
        if self.restart_cooldown > 0: self.restart_cooldown  -= 1
        if self.shake > 0:            self.shake              -= 1

        self.screen_zoom     *= 0.85
        if abs(self.screen_zoom) < 0.002:
            self.screen_zoom = 0.0
        if self.chromatic_timer > 0:  self.chromatic_timer -= 1
        if self.vignette_timer > 0:   self.vignette_timer  -= 1
        self.ui_phase      += 0.04
        self.roll_angle    += (-self.last_mouse_dx * 0.04 - self.roll_angle) * 0.18
        self.cinematic_pulse *= 0.85

        for msg in self.glitch_messages[:]:
            msg["timer"] -= 1
            if msg["timer"] <= 0:
                self.glitch_messages.remove(msg)

    def draw_enemies(self, surface):
        for enemy in self.enemies:
            dx       = enemy["x"] - self.player.x
            dy       = enemy["y"] - self.player.y
            distance = (dx * dx + dy * dy) ** 0.5

            theta = math.atan2(dy, dx)
            delta = (theta - self.player.angle) % (2 * math.pi)
            if delta > math.pi:
                delta -= 2 * math.pi
            if dx > 0 and self.player.angle > math.pi:
                delta += 2 * math.pi
            if dx < 0 and dy < 0:
                delta += 2 * math.pi

            if -HALF_FOV < delta < HALF_FOV:
                screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
                size     = min(3000 / (distance + 0.0001), 300)
                bob      = math.sin(enemy.get("anim_phase", 0.0)) * 10
                scale    = 1.0 + 0.1 * math.sin(enemy.get("anim_phase", 0.0) * 2)
                if enemy.get("attack_frame", 0) > 0:
                    scale += 0.08
                lunge = 0
                if enemy.get("attack_frame", 0) > 0 and enemy.get("dist_to_player", 999) < 120:
                    lunge = 8

                x = screen_x - size // 2
                y = HALF_HEIGHT - size // 2 + bob - lunge

                ray_index = max(0, min(NUM_RAYS - 1, int(screen_x * NUM_RAYS / WIDTH)))
                if 0 <= ray_index < len(self.depth_buffer):
                    if distance < self.depth_buffer[ray_index]:
                        if enemy["alive"]:
                            sprite_size = max(1, int(size * scale))
                            sprite = self.enemy_sprites.get(
                                enemy.get("boss_kind") or enemy.get("type"), None
                            )
                            if sprite is None:
                                sprite = self.enemy_sprite
                            sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))
                            if enemy["attack_frame"] > 0:
                                tint = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
                                tint.fill((255, 0, 0, 120))
                                sprite.blit(tint, (0, 0))
                                enemy["attack_frame"] -= 1
                            if enemy.get("hurt_timer", 0) > 0:
                                flash = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
                                flash.fill((255, 120, 120, 120))
                                sprite.blit(flash, (0, 0))

                            if self.time_dilation.active:
                                ghost = sprite.copy()
                                ghost.fill((60, 200, 255, 80), special_flags=pygame.BLEND_RGBA_MULT)
                                ghost.set_alpha(70)
                                self._blit_centered(surface, ghost, x - 8, y + 4, size, sprite_size)

                            if enemy.get("time_bias", 0.0) < -0.2:
                                ghost = sprite.copy()
                                ghost.fill((200, 200, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)
                                self._blit_centered(surface, ghost, x - 6, y + 2, size, sprite_size)

                            self._blit_centered(surface, sprite, x, y, size, sprite_size)

                            bar_w = size
                            bar_h = max(4, int(size * 0.08))
                            ratio = enemy["health"] / 100
                            pygame.draw.rect(surface, (50, 50, 50),    (x, y - bar_h - 5, bar_w, bar_h))
                            pygame.draw.rect(surface, (0, 255, 0),     (x, y - bar_h - 5, bar_w * ratio, bar_h))
                        else:
                            alpha  = max(0, 255 - enemy["death_timer"] * 10)
                            shrink = max(0.3, 1 - enemy["death_timer"] * 0.04)
                            dead_size = max(1, int(size * shrink))
                            surf = pygame.Surface((dead_size, dead_size), pygame.SRCALPHA)
                            surf.fill((150, 0, 0, alpha))
                            self._blit_centered(surface, surf, x, y, size, dead_size)

    def _blit_centered(self, surface, sprite, x, y, base_size, sprite_size):
        dx = (base_size - sprite_size) // 2
        dy = (base_size - sprite_size) // 2
        surface.blit(sprite, (x + dx, y + dy))

    def render(self):
        if self.state == "menu":
            self.screen.fill((30, 30, 30))
            pygame.draw.rect(self.screen, (100, 100, 255), (0, 0, WIDTH, HALF_HEIGHT))
            pygame.draw.rect(self.screen, (50, 50, 50),    (0, HALF_HEIGHT, WIDTH, HALF_HEIGHT))
            from systems.menu import draw_menu
            draw_menu(self.screen)

        elif self.state == "settings":
            self.screen.fill((30, 30, 30))
            pygame.draw.rect(self.screen, (100, 100, 255), (0, 0, WIDTH, HALF_HEIGHT))
            pygame.draw.rect(self.screen, (50, 50, 50),    (0, HALF_HEIGHT, WIDTH, HALF_HEIGHT))
            from systems.settings_menu import draw_settings
            draw_settings(self.screen, self.settings)

        elif self.state == "cutscene":
            if self.ending_choice == "containment":
                ending_animation = {
                    "scene": "core_chamber", "title_anim": "fade",
                    "lines_anim": ["typewriter", "typewriter", "typewriter", "typewriter", "typewriter"],
                    "glitch_intensity": 0.12,
                }
                draw_cutscene(
                    self.screen, "ENDING — CONTAINMENT",
                    [
                        "You destroy the core. The fracture collapses inward.",
                        "The timelines converge. The Astraeus returns to a single moment.",
                        "The entity dissolves — every version of it, simultaneously.",
                        "The crew is gone. All versions of them, erased with it.",
                        "You drift in silence. The black hole holds no memory of any of this.",
                    ],
                    self.cutscene_time, animation_config=ending_animation,
                )
            elif self.ending_choice == "ascension":
                ending_animation = {
                    "scene": "all_timelines", "title_anim": "glitch",
                    "lines_anim": ["glitch", "bounce", "typewriter", "glitch", "bounce"],
                    "glitch_intensity": 0.55,
                }
                draw_cutscene(
                    self.screen, "ENDING — ASCENSION",
                    [
                        "You step into the core. The boundary between you and it dissolves.",
                        "You are no longer perceiving time. You are experiencing all of it.",
                        "Every corridor you ever walked. Every choice. Every version of yourself.",
                        "You understand now what the crew became. You understand you chose this.",
                        "There is no past. No future. Only the Astraeus, forever, watching.",
                    ],
                    self.cutscene_time, animation_config=ending_animation,
                )
            else:
                beat        = self.story_beats[self.cutscene_index]
                show_map    = (self.cutscene_index == 0)
                anim_config = beat.get("animation", {})
                draw_cutscene(
                    self.screen, beat["title"], beat["lines"],
                    self.cutscene_time,
                    map_data=self.cutscene_map if show_map else None,
                    animation_config=anim_config,
                )

        elif self.state == "ending_choice":
            choice_animation = {
                "scene": "entity_presence", "title_anim": "glitch",
                "lines_anim": ["glitch", "typewriter", "typewriter", "bounce", "glitch"],
                "glitch_intensity": 0.48,
            }
            draw_cutscene(
                self.screen, "THE WATCHER SPEAKS",
                [
                    "You have arrived at every version of this moment.",
                    "Destroy the core — erase the fracture, and everything within it.",
                    "The crew. Every echo. Every timeline. Erased completely.",
                    "Or merge with us. Become part of what observes all time at once.",
                    "Press 1 to CONTAIN.     Press 2 to ASCEND.",
                ],
                self.cutscene_time, prompt="This decision cannot be rewound.",
                animation_config=choice_animation,
            )

        else:
            scene = pygame.Surface((WIDTH, HEIGHT))
            scene.fill((6, 8, 14))

            scene.blit(self.ceiling_big, (0, 0))

            self._blit_tiled(scene, self.floor_texture,
                             pygame.Rect(0, HALF_HEIGHT, WIDTH, HALF_HEIGHT))
            floor_grad = pygame.Surface((WIDTH, HALF_HEIGHT), pygame.SRCALPHA)
            for _fy in range(HALF_HEIGHT):
                _ratio = _fy / HALF_HEIGHT
                _a     = int(100 + 130 * _ratio)
                pygame.draw.line(floor_grad, (0, 0, 0, _a), (0, _fy), (WIDTH, _fy))
            scene.blit(floor_grad, (0, HALF_HEIGHT))

            if self.room_tint_alpha > 0:
                tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                tint.fill((*self.room_tint, self.room_tint_alpha))
                scene.blit(tint, (0, 0))

            if self.interior_floor_overlay:
                scene.blit(self.interior_floor_overlay, (0, HALF_HEIGHT))

            self.depth_buffer = raycast(
                self.world, self.player, scene,
                self.wall_textures, self.doors, self.door_texture,
            )
            self.draw_enemies(scene)
            draw_health_packs(scene, self.health_packs, self.player, self.depth_buffer, self.anim_time)
            self.grenade_system.draw_grenades(scene, self.player, self.depth_buffer, self.anim_time)
            self.temporal_echo.draw(scene, self.player, self.depth_buffer)
            self.weapon_system.draw_bullets(scene)
            self.weapon_system.draw_weapon(
                scene, self.player,
                bob_y=self.bob_offset, sway_x=self.bob_side, sway_y=self.bob_offset * 0.3,
            )

            rewinding = self.time_rewind.rewinding
            scene = self.temporal_visuals.apply_pre_blit(
                scene,
                self.time_dilation.active,
                self.time_dilation.energy_ratio,
                rewinding,
            )

            zoom        = 1.0 + self.screen_zoom
            zoom_pulse  = 1.0 + (self.cinematic_pulse * 0.02)
            target_w    = max(1, int(WIDTH  * zoom * zoom_pulse))
            target_h    = max(1, int(HEIGHT * zoom * zoom_pulse))
            scaled      = pygame.transform.smoothscale(scene, (target_w, target_h))
            angle       = max(-5.0, min(5.0, self.roll_angle))
            if abs(angle) > 0.02:
                scaled = pygame.transform.rotozoom(scaled, angle, 1.0)

            shake_x = shake_y = 0
            if self.shake > 0:
                shake_x = int((self.shake * 0.6) * (1 if int(time.time() * 1000) % 2 == 0 else -1))
                shake_y = int((self.shake * 0.6) * (-1 if int(time.time() * 1000) % 3 == 0 else 1))

            base_x = (WIDTH  - scaled.get_width())  // 2 + shake_x
            base_y = (HEIGHT - scaled.get_height()) // 2 + shake_y + int(self.bob_offset)

            self.screen.fill((0, 0, 0))

            if self.chromatic_timer > 0:
                offset = 2 + self.chromatic_timer
                red  = scaled.copy()
                blue = scaled.copy()
                red.fill((255, 140, 140), special_flags=pygame.BLEND_RGB_MULT)
                blue.fill((140, 140, 255), special_flags=pygame.BLEND_RGB_MULT)
                self.screen.blit(red,  (base_x + offset, base_y))
                self.screen.blit(blue, (base_x - offset, base_y))

            self.screen.blit(scaled, (base_x, base_y))

            self.temporal_visuals.apply_post_blit(
                self.screen,
                self.time_dilation.active,
                self.time_dilation.energy_ratio,
                rewinding,
            )

            if self.interior_grade:
                self.screen.blit(self.interior_grade, (0, 0))
            if self.interior_vignette:
                self.screen.blit(self.interior_vignette, (0, 0))
            if self.vignette_timer > 0:
                vig   = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                alpha = min(170, self.vignette_timer * 10)
                pygame.draw.rect(vig, (0, 0, 0, alpha), vig.get_rect(), border_radius=16)
                pygame.draw.rect(vig, (0, 0, 0, 0), pygame.Rect(50, 35, WIDTH - 100, HEIGHT - 70))
                self.screen.blit(vig, (0, 0))

            if self.anomaly_timer > 0:
                scan = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                for y in range(0, HEIGHT, 4):
                    a = 20 if (y // 4) % 2 == 0 else 8
                    scan.fill((80, 120, 200, a), pygame.Rect(0, y, WIDTH, 2))
                self.screen.blit(scan, (0, 0))

            if self.room_scan and self.room_tint_alpha > 0:
                scan = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                for y in range(0, HEIGHT, 6):
                    a = 18 if (y // 6) % 2 == 0 else 6
                    scan.fill((*self.room_tint, a), pygame.Rect(0, y, WIDTH, 2))
                self.screen.blit(scan, (0, 0))

            self.fracture_zones.draw_overlay(self.screen, self.ui_phase)

            if self.time_dilation.active and self.time_dilation.ramp > 0.05:
                dil_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                dil_a    = int(30 * self.time_dilation.ramp)
                dil_surf.fill((40, 160, 255, dil_a))
                self.screen.blit(dil_surf, (0, 0))

            if rewinding and self.time_rewind.flash_alpha > 0:
                flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                flash_surf.fill((180, 200, 255, self.time_rewind.flash_alpha))
                self.screen.blit(flash_surf, (0, 0))

            self.temporal_visuals.draw_dilation_trail_overlay(self.screen)

            pulse = self.hit_marker / 6 if self.hit_marker > 0 else 0.0
            draw_scifi_hud(self.screen, self.ui_phase, alert=self.hit_flash > 0 or self.game_over)
            draw_crosshair(self.screen, self.hit_marker > 0, pulse)
            draw_level_hud(self.screen, self.hud_font, self.current_level_index, self.player)
            draw_ammo(self.screen, self.hud_font, self.player)
            draw_score(self.screen, self.hud_font, self.score, self.kills,
                       self.score_pulse / 10 if self.score_pulse > 0 else 0.0)

            fps_text = self.hud_font.render(f"FPS: {self.fps_display}", True, (100, 255, 100))
            self.screen.blit(fps_text, (WIDTH - 150, 20))

            draw_weapon_info(self.screen, self.player)
            self.grenade_system.draw_hud(self.screen, self.ui_phase)
            minimap_alpha = 130 + math.sin(self.ui_phase) * 25
            draw_minimap(
                self.screen, self.world, self.player, self.enemies,
                self.health_packs, minimap_alpha, self.rooms, ROOM_COLOR_MAP,
            )
            draw_overlay_messages(
                self.screen, self.glitch_messages, flicker=abs(math.sin(self.ui_phase))
            )
            if self.room_timer > 0 and self.current_room:
                draw_room_label(
                    self.screen, self.current_room,
                    self.room_timer / 90, abs(math.sin(self.ui_phase)),
                )

            draw_temporal_hud(
                self.screen,
                self.time_dilation,
                self.time_rewind,
                self.temporal_echo,
                self.fracture_zones,
                self.ui_phase,
            )

            if self.hit_flash > 0:
                draw_hit_flash(self.screen)

            if self.game_over:
                draw_game_over(self.screen, self.hud_font)
                keys = pygame.key.get_pressed()
                if keys[pygame.K_r] and self.restart_cooldown <= 0:
                    self.reset_game()

            if self.state == "pause":
                draw_pause(self.screen)

        if self.time_frozen:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 100, 255, 60))
            self.screen.blit(overlay, (0, 0))

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.render()
            self.clock.tick(FPS)

            self.fps_counter += 1
            self.fps_timer   += 1.0 / FPS
            if self.fps_timer >= 1.0:
                self.fps_display = self.fps_counter
                self.fps_counter = 0
                self.fps_timer   = 0.0

        self.save_game()
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        pygame.quit()
```

## fps_game/core/level.py
Filename: `fps_game/core/level.py`

```python
import random

from core.settings import TILE, ROOM_NAME_MAP
from enemies.enemy import create_enemy


def load_level(path):
    world = {}
    enemies = []
    health_packs = []
    rooms = {}
    doors = {}
    player_spawn = (150, 150)

    with open(path) as f:
        lines = [line.strip() for line in f.readlines()]

    for j, row in enumerate(lines):
        for i, char in enumerate(row):
            x = i * TILE
            y = j * TILE

            if char in {"#", "A", "B", "C", "D"}:
                world[(x, y)] = char
            elif char == "P":
                player_spawn = (x + TILE // 2, y + TILE // 2)
            elif char == "E":
                enemy_type = random.choice(["normal", "fast", "tank", "ranged"])
                enemies.append(create_enemy(enemy_type, x + TILE // 2, y + TILE // 2))
            elif char == "1":
                enemies.append(create_enemy("boss1", x + TILE // 2, y + TILE // 2))
            elif char == "2":
                enemies.append(create_enemy("boss2", x + TILE // 2, y + TILE // 2))
            elif char == "3":
                enemies.append(create_enemy("boss3", x + TILE // 2, y + TILE // 2))
            elif char == "4":
                enemies.append(create_enemy("boss_final", x + TILE // 2, y + TILE // 2))
            elif char == "H":
                health_packs.append({"x": x + TILE // 2, "y": y + TILE // 2})
            elif char in ROOM_NAME_MAP:
                rooms[(x, y)] = char
            elif char == "X":
                doors[(x, y)] = {"open": False}

    return world, enemies, health_packs, player_spawn, rooms, doors
```

## fps_game/core/settings.py
Filename: `fps_game/core/settings.py`

```python
import math
import os

WIDTH, HEIGHT = 1500, 1000
HALF_HEIGHT = HEIGHT // 2
FPS = 60

FOV = math.pi / 3
HALF_FOV = FOV / 2
NUM_RAYS = 200
MAX_DEPTH = 800
DELTA_ANGLE = FOV / NUM_RAYS

TILE = 64
SCALE = WIDTH // NUM_RAYS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "images")
LEVELS_DIR = os.path.join(BASE_DIR, "levels")
SOUND_DIR = os.path.join(BASE_DIR, "assets", "sounds")
WEAPON_DEFAULT_IMG = os.path.join(ASSETS_DIR, "weapon.png")
WEAPON_IMAGE_MAP = {
    "Pistol": os.path.join(ASSETS_DIR, "pistol.png"),
    "Shotgun": os.path.join(ASSETS_DIR, "shotgun.png"),
    "Sniper": os.path.join(ASSETS_DIR, "sniper.png"),
}
ENEMY_IMG = os.path.join(ASSETS_DIR, "enemy.png")
WALL_IMG = os.path.join(ASSETS_DIR, "wall.png")
DOOR_IMG = os.path.join(ASSETS_DIR, "door.png")
WALL_TEXTURE_FILES = {
    "#": os.path.join(ASSETS_DIR, "wall.png"),
    "A": os.path.join(ASSETS_DIR, "wall_a.png"),
    "B": os.path.join(ASSETS_DIR, "wall_b.png"),
    "C": os.path.join(ASSETS_DIR, "wall_c.png"),
    "D": os.path.join(ASSETS_DIR, "wall_d.png"),
}
FLOOR_TEXTURE_FILES = [
    os.path.join(ASSETS_DIR, "floor_a.png"),
    os.path.join(ASSETS_DIR, "floor_b.png"),
    os.path.join(ASSETS_DIR, "floor_c.png"),
]
CEILING_TEXTURE_FILES = [
    os.path.join(ASSETS_DIR, "ceiling_a.png"),
    os.path.join(ASSETS_DIR, "ceiling_b.png"),
    os.path.join(ASSETS_DIR, "ceiling_c.png"),
]
ENEMY_SPRITE_FILES = {
    "normal": os.path.join(ASSETS_DIR, "enemy_normal.png"),
    "fast": os.path.join(ASSETS_DIR, "enemy_fast.png"),
    "tank": os.path.join(ASSETS_DIR, "enemy_tank.png"),
    "ranged": os.path.join(ASSETS_DIR, "enemy_ranged.png"),
    "boss1": os.path.join(ASSETS_DIR, "enemy_boss1.png"),
    "boss2": os.path.join(ASSETS_DIR, "enemy_boss2.png"),
    "boss3": os.path.join(ASSETS_DIR, "enemy_boss3.png"),
    "boss_final": os.path.join(ASSETS_DIR, "enemy_boss_final.png"),
}

ROOM_NAME_MAP = {
    "B": "Bridge",
    "L": "Research Lab",
    "R": "Reactor Core",
    "Q": "Crew Quarters",
    "M": "Medbay",
    "C": "Cargo Bay",
    "H": "Hangar",
    "Y": "Cryo Bay",
    "O": "Observation",
}

ROOM_COLOR_MAP = {
    "B": (120, 200, 255),
    "L": (120, 255, 160),
    "R": (255, 140, 120),
    "Q": (220, 200, 120),
    "M": (120, 220, 255),
    "C": (200, 160, 120),
    "H": (160, 160, 255),
    "Y": (180, 220, 255),
    "O": (200, 180, 255),
}

ROOM_AMBIENCE_MAP = {
    "B": {"floor": 0, "ceiling": 2, "tint": (80, 140, 255), "alpha": 40, "scan": False},
    "L": {"floor": 1, "ceiling": 0, "tint": (120, 255, 160), "alpha": 35, "scan": False},
    "R": {"floor": 2, "ceiling": 1, "tint": (255, 90, 60), "alpha": 60, "scan": True},
    "Q": {"floor": 0, "ceiling": 0, "tint": (220, 200, 120), "alpha": 25, "scan": False},
    "M": {"floor": 1, "ceiling": 2, "tint": (120, 220, 255), "alpha": 45, "scan": False},
    "C": {"floor": 2, "ceiling": 0, "tint": (200, 160, 120), "alpha": 30, "scan": False},
    "H": {"floor": 0, "ceiling": 1, "tint": (160, 160, 255), "alpha": 35, "scan": True},
    "Y": {"floor": 2, "ceiling": 2, "tint": (180, 220, 255), "alpha": 40, "scan": False},
    "O": {"floor": 1, "ceiling": 1, "tint": (200, 180, 255), "alpha": 30, "scan": False},
}
EFFECTS_DIR = os.path.join(BASE_DIR, "assets", "sounds", "effects")
EFFECT_FILES = {
    "gunshot": os.path.join(EFFECTS_DIR, "gunshot.mp3"),
    "reload": os.path.join(EFFECTS_DIR, "reload.mp3"),
    "player_hit": os.path.join(EFFECTS_DIR, "player_hit.mp3"),
    "level_up": os.path.join(EFFECTS_DIR, "level_up.mp3"),
}
# Music configuration - maps level ranges to music files
MUSIC_DIR = os.path.join(BASE_DIR, "assets", "sounds", "music")
EFFECTS_DIR = os.path.join(BASE_DIR, "assets", "sounds", "effects")

MUSIC_TRACKS = {
    (0, 5): os.path.join(MUSIC_DIR, "levels0005.mp3"),
    (6, 10): os.path.join(MUSIC_DIR, "levels0610.mp3"),
    (11, 15): os.path.join(MUSIC_DIR, "levels1115.mp3"),
    (16, 20): os.path.join(MUSIC_DIR, "levels1620.mp3"),
}

# Sound effects configuration
EFFECT_FILES = {
    "gunshot": os.path.join(EFFECTS_DIR, "gunshot.mp3"),
    "level_up": os.path.join(EFFECTS_DIR, "level_up.mp3"),
    "player_hit": os.path.join(EFFECTS_DIR, "player_hit.mp3"),
    "reload": os.path.join(EFFECTS_DIR, "reload.mp3"),
    "laser": os.path.join(EFFECTS_DIR, "laser.mp3"),
}

def get_music_for_level(level):
    """Get the music file path for a given level."""
    for (start, end), music_path in MUSIC_TRACKS.items():
        if start <= level <= end:
            return music_path
    return None
```

## fps_game/enemies/__init__.py
Filename: `fps_game/enemies/__init__.py`

```python

```

## fps_game/enemies/ai.py
Filename: `fps_game/enemies/ai.py`

```python
import math
import random

from core.settings import TILE
from utils.math_utils import is_wall


def update_enemies(enemies, player, world, doors, on_player_hit, time_scale=1.0):
    if time_scale == 0.0:
        return
    for enemy in enemies:
        enemy["anim_phase"] = (enemy.get("anim_phase", 0.0) + enemy.get("bob_speed", 0.2) * time_scale) % (math.pi * 2)
        if enemy.get("hurt_timer", 0) > 0:
            enemy["hurt_timer"] -= 1
        if enemy.get("stun_timer", 0) > 0:
            enemy["stun_timer"] -= 1
            continue
        if enemy["alive"]:
            dx = player.x - enemy["x"]
            dy = player.y - enemy["y"]
            dist = math.hypot(dx, dy)
            enemy["dist_to_player"] = dist
            if enemy.get("boss"):
                if enemy["boss_burst"] > 0:
                    enemy["boss_burst"] -= 1
                else:
                    enemy["boss_cooldown"] -= 1
                    if enemy["boss_cooldown"] <= 0:
                        enemy["boss_burst"] = random.randint(12, 26)
                        enemy["boss_cooldown"] = random.randint(90, 160)
                        enemy["time_bias"] = random.uniform(-0.8, 1.1)
            if dist > 5:
                drift = enemy.get("time_bias", 0.0) * 0.4
                burst_scale = 1.0
                if enemy.get("boss") and enemy["boss_burst"] > 0:
                    burst_scale = 2.4
                slow_factor = 0.5 if enemy.get("slow_timer", 0) > 0 else 1.0
                if enemy.get("slow_timer", 0) > 0:
                    enemy["slow_timer"] -= 1
                local_scale = max(0.25, min(2.6, (time_scale + drift) * burst_scale * slow_factor))
                step_x = dx / dist * enemy["speed"] * local_scale
                step_y = dy / dist * enemy["speed"] * local_scale
                nx = enemy["x"] + step_x
                ny = enemy["y"] + step_y
                if not is_wall(nx, enemy["y"], world, TILE, doors):
                    enemy["x"] = nx
                if not is_wall(enemy["x"], ny, world, TILE, doors):
                    enemy["y"] = ny

            if enemy["attack_cooldown"] > 0:
                enemy["attack_cooldown"] -= 1

            attack_range = 60 if enemy["type"] != "ranged" else 120
            if dist < attack_range and enemy["attack_cooldown"] <= 0:
                on_player_hit(enemy)
                enemy["attack_cooldown"] = 30
        else:
            enemy["death_timer"] += 1
```

## fps_game/enemies/enemy.py
Filename: `fps_game/enemies/enemy.py`

```python
import random


def create_enemy(enemy_type, x, y):
    if enemy_type == "fast":
        health = 80
        speed = 4
        radius = 18
        bob_speed = 0.35
        damage = 8
    elif enemy_type == "tank":
        health = 200
        speed = 1.5
        radius = 28
        bob_speed = 0.18
        damage = 15
    elif enemy_type == "ranged":
        health = 90
        speed = 0.7
        radius = 20
        bob_speed = 0.22
        damage = 10
    elif enemy_type == "boss1":
        health = 300
        speed = 2.2
        radius = 36
        bob_speed = 0.2
        damage = 18
    elif enemy_type == "boss2":
        health = 380
        speed = 1.9
        radius = 38
        bob_speed = 0.16
        damage = 20
    elif enemy_type == "boss3":
        health = 450
        speed = 2.1
        radius = 40
        bob_speed = 0.18
        damage = 22
    elif enemy_type == "boss_final":
        health = 600
        speed = 2.4
        radius = 46
        bob_speed = 0.14
        damage = 26
    else:
        enemy_type = "normal"
        health = 100
        speed = 2
        radius = 22
        bob_speed = 0.28
        damage = 10

    return {
        "x": x,
        "y": y,
        "type": enemy_type,
        "health": health,
        "speed": speed,
        "radius": radius,
        "anim_phase": random.random() * 6.28318,
        "bob_speed": bob_speed,
        "hurt_timer": 0,
        "time_bias": random.uniform(-0.5, 0.7),
        "boss": enemy_type.startswith("boss"),
        "boss_kind": enemy_type if enemy_type.startswith("boss") else "",
        "boss_cooldown": random.randint(60, 140),
        "boss_burst": 0,
        "damage": damage,
        "stun_timer": 0,
        "slow_timer": 0,
        "alive": True,
        "death_timer": 0,
        "attack_cooldown": 0,
        "attack_frame": 0,
    }
```

## fps_game/player/__init__.py
Filename: `fps_game/player/__init__.py`

```python

```

## fps_game/player/player.py
Filename: `fps_game/player/player.py`

```python
import math

import pygame

from core.settings import TILE
from utils.math_utils import is_wall
from player.weapon import Weapon


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = 0
        self.speed = 8
        self.current_speed = 0.0
        self.accel = 0.18
        self.move_amount = 0.0
        self.mouse_sensitivity = 0.003
        self.max_health = 100
        self.health = self.max_health
        self.invincibility_frames = 0

        self.weapons = [
            Weapon("Pistol",  50, 10, 10, 0.02),
            Weapon("Shotgun", 25,  5,  5, 0.10),
            Weapon("Sniper", 100,  3,  3, 0.005),
        ]
        self.current_weapon_index = 0

    def switch_weapon(self, direction):
        self.current_weapon_index = (self.current_weapon_index + direction) % len(self.weapons)

    def get_weapon(self):
        return self.weapons[self.current_weapon_index]

    def move(self, world, mouse_dx, doors=None, speed_scale: float = 1.0):
        keys = pygame.key.get_pressed()
        target_speed = 0.0
        if keys[pygame.K_w]:
            target_speed += self.speed
        if keys[pygame.K_s]:
            target_speed -= self.speed
        if keys[pygame.K_a]:
            #strafe left: add speed in the direction 90 degrees counterclockwise from current angle
            target_speed += self.speed * math.cos(self.angle - math.pi / 2)
            target_speed += self.speed * math.sin(self.angle - math.pi / 2)
        if keys[pygame.K_d]:
            #strafe right: add speed in the direction 90 degrees clockwise from current angle
            target_speed += self.speed * math.cos(self.angle + math.pi / 2)
            target_speed += self.speed * math.sin(self.angle + math.pi / 2)
            

                                                     
        scaled_target = target_speed * speed_scale
        self.current_speed += (scaled_target - self.current_speed) * self.accel

        dx = math.cos(self.angle) * self.current_speed
        dy = math.sin(self.angle) * self.current_speed

        if abs(self.current_speed) > 0.001:
            nx = self.x + dx
            ny = self.y + dy
            if not is_wall(nx, self.y, world, TILE, doors):
                self.x = nx
            if not is_wall(self.x, ny, world, TILE, doors):
                self.y = ny

        if self.speed > 0:
            self.move_amount = min(1.0, abs(self.current_speed) / self.speed)
        else:
            self.move_amount = 0.0

        if mouse_dx:
            self.angle += mouse_dx * self.mouse_sensitivity

    def apply_damage(self, amount):
        if self.invincibility_frames > 0:
            return False
        self.health -= amount
        self.invincibility_frames = 30
        return True

    def update_invincibility(self):
        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1
```

## fps_game/player/weapon.py
Filename: `fps_game/player/weapon.py`

```python
import random
import math

import os
import pygame

from core.settings import EFFECT_FILES, WIDTH, HEIGHT, DELTA_ANGLE, WEAPON_DEFAULT_IMG, WEAPON_IMAGE_MAP


class Weapon:
    def __init__(self, name, damage, ammo, max_ammo, spread):
        self.name = name
        self.damage = damage
        self.ammo = ammo
        self.max_ammo = max_ammo
        self.spread = spread


class WeaponSystem:
    def __init__(self, image):
        self.images = {}
        self.image = pygame.transform.scale(image, (300, 200))
        self.recoil_offset = 0
        self.recoil_velocity = 0
        self.bullets = []
        self.sway_x = 0.0
        self.sway_y = 0.0
        self.muzzle_timer = 0
        self.idle_phase = 0.0
        self.kick = 0.0

        self.reloading = False
        self.reload_timer = 0
        self.reload_time = 60

        self.fire_rate = 0.2
        self.last_shot = 0

        self._load_weapon_images()

    def _load_weapon_images(self):
        for name, path in WEAPON_IMAGE_MAP.items():
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
            else:
                img = pygame.image.load(WEAPON_DEFAULT_IMG).convert_alpha()
            self.images[name] = pygame.transform.scale(img, (300, 200))

    def try_shoot(self, now, player, enemies, depth_buffer):
        weapon = player.get_weapon()
        if self.reloading or weapon.ammo <= 0:
            return 0, 0, False, False
        if now - self.last_shot <= self.fire_rate:
            return 0, 0, False, False

        self.last_shot = now
        weapon.ammo -= 1
        self.muzzle_timer = 4
        self.kick = -8
        self.bullets.append({
            "x": player.x,
            "y": player.y,
            "angle": player.angle,
            "speed": 20,
            "life": 60
        })

        score_delta = 0
        kills_delta = 0
        hit_any = False

        center_ray = len(depth_buffer) // 2
        if center_ray >= len(depth_buffer):
            return 0, 0, False, True
        wall_dist = depth_buffer[center_ray]

        for enemy in enemies:
            dx = enemy["x"] - player.x
            dy = enemy["y"] - player.y
            distance = math.hypot(dx, dy)

            theta = math.atan2(dy, dx)
            delta = theta - player.angle
            delta = (delta + math.pi) % (2 * math.pi) - math.pi
            spread = random.uniform(-weapon.spread, weapon.spread)
            delta += spread
            enemy_radius = enemy.get("radius", 20)
            hit_angle = math.atan2(enemy_radius, max(1.0, distance))
            if abs(delta) < max(DELTA_ANGLE * 2, hit_angle):
                if distance < wall_dist and enemy["alive"]:
                    headshot = abs(delta) < (DELTA_ANGLE * 0.5)
                    damage = weapon.damage
                    if headshot:
                        damage *= 2
                        score_delta += 20
                    else:
                        score_delta += 10
                    enemy["health"] -= damage
                    enemy["hurt_timer"] = 6
                    hit_any = True
                    if enemy["health"] <= 0:
                        enemy["alive"] = False
                        enemy["death_timer"] = 0
                        kills_delta += 1

        self.recoil_velocity = -8
        return score_delta, kills_delta, hit_any, True
    def update_bullets(self, world, enemies, time_scale):
        for bullet in self.bullets[:]:
            if time_scale == 0.0:
                continue  # freeze bullets

            bullet["x"] += math.cos(bullet["angle"]) * bullet["speed"] * time_scale
            bullet["y"] += math.sin(bullet["angle"]) * bullet["speed"] * time_scale
            bullet["life"] -= 1

            if bullet["life"] <= 0:
                self.bullets.remove(bullet)
                continue

            # collision with enemies
            for enemy in enemies:
                if enemy["alive"]:
                    dx = bullet["x"] - enemy["x"]
                    dy = bullet["y"] - enemy["y"]
                    if math.hypot(dx, dy) < enemy["radius"]:
                        enemy["health"] -= 50
                        enemy["hurt_timer"] = 6
                        if enemy["health"] <= 0:
                            enemy["alive"] = False
                        if bullet in self.bullets:
                            self.bullets.remove(bullet)
                        break

    def update_sway(self, target_x, target_y):
        self.sway_x += (target_x - self.sway_x) * 0.18
        self.sway_y += (target_y - self.sway_y) * 0.18
        self.idle_phase += 0.05
        self.kick *= 0.78
    def update_reload(self, player):
        weapon = player.get_weapon()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_r] and weapon.ammo < weapon.max_ammo and not self.reloading:
            self.reloading = True
            self.reload_timer = self.reload_time

        if self.reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                weapon.ammo = weapon.max_ammo
                self.reloading = False
                try:
                    if os.path.exists(EFFECT_FILES["reload"]):
                        pygame.mixer.Sound(EFFECT_FILES["reload"]).play()
                except (KeyError, pygame.error):
                    pass

    def update_recoil(self):
        self.recoil_offset += self.recoil_velocity
        self.recoil_velocity += 0.8
        self.recoil_offset *= 0.9
        if self.recoil_offset > 0:
            self.recoil_offset = 0
            self.recoil_velocity = 0

    def draw_weapon(self, screen, player, sway_x=0, sway_y=0, bob_y=0):
        weapon = player.get_weapon()
        sprite = self.images.get(weapon.name, self.image)
        reload_t = 0.0
        if self.reloading and self.reload_time > 0:
            reload_t = max(0.0, min(1.0, self.reload_timer / self.reload_time))
        reload_offset = int(35 * math.sin(reload_t * math.pi))
        reload_swing = int(12 * math.sin(reload_t * math.pi * 2))
        idle_x = int(math.sin(self.idle_phase) * 6)
        idle_y = int(math.cos(self.idle_phase * 0.8) * 5)

        x = WIDTH // 2 - sprite.get_width() // 2 + int(self.sway_x + sway_x) + reload_swing + idle_x
        y = HEIGHT - sprite.get_height() + self.recoil_offset + int(self.sway_y + sway_y + bob_y) + reload_offset + idle_y + int(self.kick)
        screen.blit(sprite, (x, y))

        if self.muzzle_timer > 0:
            self.muzzle_timer -= 1
            pygame.draw.circle(screen, (255, 200, 50), (WIDTH // 2, HEIGHT // 2), 18)

    def draw_bullets(self, screen):
        for bullet in self.bullets:
            pygame.draw.circle(
                screen,
                (255, 255, 0),
                (int(bullet["x"]), int(bullet["y"])),
                3
            )
```

## fps_game/systems/__init__.py
Filename: `fps_game/systems/__init__.py`

```python

```

## fps_game/systems/combat.py
Filename: `fps_game/systems/combat.py`

```python
import math
import pygame

from core.settings import HALF_FOV, WIDTH, FOV, NUM_RAYS, SCALE, HALF_HEIGHT


def draw_health_packs(screen, health_packs, player, depth_buffer, anim_time=0.0):
    for pack in health_packs[:]:
        dx = pack["x"] - player.x
        dy = pack["y"] - player.y
        dist = math.hypot(dx, dy)

        if dist < 25:
            player.health = min(player.max_health, player.health + 30)
            health_packs.remove(pack)
            continue

        theta = math.atan2(dy, dx)
        delta = (theta - player.angle) % (2 * math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi

        if -HALF_FOV < delta < HALF_FOV:
            screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
            size = min(2000 / (dist + 0.0001), 60)
            bob = math.sin(anim_time + (pack["x"] + pack["y"]) * 0.01) * 6
            x = screen_x - size // 2
            y = HALF_HEIGHT - size // 2 + bob

            ray_index = max(0, min(NUM_RAYS - 1, int(screen_x * NUM_RAYS / WIDTH)))
            if 0 <= ray_index < len(depth_buffer):
                if dist < depth_buffer[ray_index]:
                    pygame.draw.circle(
                        screen,
                        (0, 255, 0),
                        (int(x + size / 2), int(y + size / 2)),
                        max(3, int(size / 6)),
                    )
```

## fps_game/systems/cutscene.py
Filename: `fps_game/systems/cutscene.py`

```python
import math
import pygame
import random

from core.settings import WIDTH, HEIGHT
def clamp(val, low=0, high=255):
    return max(low, min(high, val))

def animate_typewriter(text, t, char_delay=0.03):
    return text[:int(t / char_delay)]


def animate_bounce(y, t, frequency=2.0, amplitude=8):
    return y + amplitude * math.sin(t * frequency * 2 * math.pi)


def animate_glitch(t, glitch_chance=0.3):
    if random.random() < glitch_chance:
        return random.randint(-3, 3), random.randint(-2, 2)
    return 0, 0


def _scanlines(surface, intensity, color=(0, 0, 0)):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 3):
        pygame.draw.line(overlay, (*color, int(18 * intensity)), (0, y), (WIDTH, y), 1)
    surface.blit(overlay, (0, 0))


def _glitch_block(surface, intensity):
    if random.random() < intensity:
        gh = random.randint(8, 44)
        gy = random.randint(0, HEIGHT - gh)
        gw = random.randint(40, 220)
        gx = random.randint(0, WIDTH - gw)
        ga = random.randint(25, 100)
        gc = (random.randint(80, 255), random.randint(0, 80), random.randint(80, 255))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (*gc, ga), (gx, gy, gw, gh))
        surface.blit(overlay, (0, 0))


def draw_corrupted_screen(surface, t, intensity=0.3):
    _scanlines(surface, intensity)
    _glitch_block(surface, intensity)


def _draw_star_field(screen, t, count=120, drift=0.0):
    random.seed(42)
    for _ in range(count):
        sx = random.randint(0, WIDTH)
        sy = random.randint(0, HEIGHT)
        brightness = random.randint(80, 220)
        twinkle = int((math.sin(t * random.uniform(1.5, 4.0) + random.random() * 6) + 1) * 0.5 * 60)
        value = clamp(brightness + twinkle)
        pygame.draw.circle(screen, (value,) * 3,
                           (sx, int(sy + drift * random.uniform(0.1, 0.8)) % HEIGHT), 1)
    random.seed()


def _draw_black_hole(screen, cx, cy, t, radius=140):
    for r in range(radius, 0, -8):
        ratio = r / radius
        alpha = int(200 * (1 - ratio))
        ring_color = (int(20 * ratio), int(10 * ratio), int(60 + 80 * (1 - ratio)))
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*ring_color, alpha), (r, r), r)
        screen.blit(surf, (cx - r, cy - r))

    for i in range(60):
        angle = (i / 60) * math.pi * 2 + t * 0.4
        dist = radius + 30 + math.sin(angle * 3 + t) * 18
        ax = cx + int(math.cos(angle) * dist)
        ay = cy + int(math.sin(angle) * dist * 0.35)
        heat = min(255, 180 + int(75 * math.sin(angle * 2 + t * 2)))
        pygame.draw.circle(screen, (heat, int(heat * 0.4), 40), (ax, ay), 2)

    pygame.draw.circle(screen, (0, 0, 0), (cx, cy), int(radius * 0.55))


def _draw_astraeus_silhouette(screen, cx, cy, t):
    flicker = 0.7 + 0.3 * math.sin(t * 2.3)
    dim = int(60 * flicker)
    hull = [
        (cx - 180, cy - 12), (cx - 80, cy - 22),
        (cx + 60,  cy - 28), (cx + 180, cy - 8),
        (cx + 180, cy + 8),  (cx + 60,  cy + 28),
        (cx - 80,  cy + 22), (cx - 180, cy + 12),
    ]
    pygame.draw.polygon(screen, (dim, dim + 6, dim + 14), hull)
    pygame.draw.polygon(screen, (dim + 20, dim + 26, dim + 40), hull, 2)
    for wx in range(cx - 140, cx + 120, 28):
        wa = int(40 + 60 * abs(math.sin(t * 1.8 + wx * 0.05)))
        pygame.draw.rect(screen, (wa, wa + 30, wa + 60), (wx, cy - 7, 10, 14))


def _draw_arrival(screen, t):
    screen.fill((2, 4, 10))
    _draw_star_field(screen, t, count=160, drift=t * 6)
    _draw_black_hole(screen, int(WIDTH * 0.72), int(HEIGHT * 0.44), t, radius=120)
    _draw_astraeus_silhouette(screen,
                              int(WIDTH * 0.32 + math.sin(t * 0.3) * 8),
                              int(HEIGHT * 0.52 + math.cos(t * 0.22) * 5), t)


def _draw_corridor(screen, t):
    screen.fill((10, 12, 16))
    flicker = (math.sin(t * 3.7) + 1) * 0.5
    cx, cy = WIDTH // 2, HEIGHT // 2
    for i in range(7):
        depth = 0.12 + i * 0.13
        w = int(WIDTH * depth)
        h = int(HEIGHT * depth)
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        brightness = int(22 + 22 * depth + 12 * flicker)
        pygame.draw.rect(screen, (brightness, brightness + 4, brightness + 14), rect, 1)
    for x in range(cx - 160, cx + 180, 80):
        la = int(120 + 80 * flicker)
        pygame.draw.rect(screen, (la, la + 40, la + 80), (x - 18, 0, 36, 10))
        pygame.draw.rect(screen, (la // 3, la // 3 + 10, la // 3 + 30), (x - 10, 10, 20, HEIGHT - 10))
    for y in range(40, HEIGHT - 40, HEIGHT - 80):
        pygame.draw.line(screen, (30, 40, 60), (0, y), (WIDTH, y), 2)


def _draw_crew_echo(screen, t):
    _draw_corridor(screen, t)
    for i in range(4):
        phase = t * 0.9 + i * 1.8
        alpha = int((math.sin(phase) + 1) * 0.5 * 130)
        ex = int(WIDTH * (0.22 + i * 0.18) + math.sin(phase * 1.3) * 14)
        ey = int(HEIGHT * 0.38 + math.sin(phase * 0.7) * 10)
        if alpha > 10:
            ghost_surf = pygame.Surface((30, 80), pygame.SRCALPHA)
            ghost_surf.fill((120, 180, 220, alpha))
            screen.blit(ghost_surf, (ex, ey))


def _draw_fracture(screen, t):
    screen.fill((6, 4, 12))
    flicker = int((math.sin(t * 5) + 1) * 50)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((80, 20, 120, 60 + flicker))
    screen.blit(overlay, (0, 0))
    for i in range(0, WIDTH + HEIGHT, 38):
        x1 = max(0, i - HEIGHT)
        y1 = max(0, HEIGHT - i)
        x2 = min(WIDTH, i)
        y2 = min(HEIGHT, HEIGHT - (i - WIDTH))
        go = random.randint(-3, 3)
        pygame.draw.line(screen, (160 + go * 10, 60, 180 + go * 8), (x1 + go, y1), (x2 + go, y2), 1)
    for _ in range(14):
        px = random.randint(0, WIDTH)
        py = random.randint(0, HEIGHT)
        pr = random.randint(1, 4)
        pc = random.choice([(200, 80, 255), (80, 200, 255), (255, 80, 180)])
        pygame.draw.circle(screen, pc, (px, py), pr)


def _draw_core_chamber(screen, t):
    screen.fill((6, 4, 10))
    pulse = (math.sin(t * 1.8) + 1) * 0.5
    cx, cy = WIDTH // 2, HEIGHT // 2
    for r in range(260, 0, -22):
        ratio = r / 260
        alpha = int(160 * (1 - ratio) * (0.6 + 0.4 * pulse))
        cr = int(120 + 100 * pulse * ratio)
        cg = int(20 * ratio)
        cb = int(80 + 60 * (1 - ratio))
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (cr, cg, cb, alpha), (r, r), r, 3)
        screen.blit(surf, (cx - r, cy - r))
    for i in range(24):
        angle = (i / 24) * math.pi * 2 + t * 0.6
        dist = 90 + 30 * math.sin(angle * 3 + t * 1.4)
        ex = cx + int(math.cos(angle) * dist)
        ey = cy + int(math.sin(angle) * dist)
        ea = int(180 + 75 * math.sin(i + t * 2))
        pygame.draw.circle(screen, (ea, int(ea * 0.3), int(ea * 0.6)), (ex, ey), 3)
    pygame.draw.circle(screen, (200, 60, 120), (cx, cy), int(28 + 8 * pulse))
    pygame.draw.circle(screen, (255, 140, 180), (cx, cy), int(14 + 4 * pulse))


def _draw_corridor_into(surf, t, tint):
    surf.fill((0, 0, 0, 0))
    cx, cy = WIDTH // 2, HEIGHT // 2
    for i in range(5):
        depth = 0.1 + i * 0.16
        w = int(WIDTH * depth)
        h = int(HEIGHT * depth)
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(surf, (*tint, 180), rect, 1)


def _draw_all_timelines(screen, t):
    screen.fill((4, 4, 8))
    layers = [
        ((40, 20, 80),  0.18, -0.6),
        ((20, 40, 100), 0.22,  0.4),
        ((80, 20, 60),  0.16, -0.3),
    ]
    for color, alpha_base, drift in layers:
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shift_x = int(math.sin(t * 0.7 + drift * 3) * 30)
        shift_y = int(math.cos(t * 0.5 + drift * 2) * 20)
        _draw_corridor_into(surf, t + drift * 2, color)
        surf.set_alpha(int(alpha_base * 255))
        screen.blit(surf, (shift_x, shift_y))

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(0, WIDTH, 6):
        a = int(30 + 20 * math.sin(i * 0.05 + t * 2))
        pygame.draw.line(overlay, (100, 60, 160, a), (i, 0), (i, HEIGHT), 1)
    screen.blit(overlay, (0, 0))

    for _ in range(6):
        gx = random.randint(0, WIDTH)
        gy = random.randint(0, HEIGHT)
        ga = random.randint(30, 80)
        gw = random.randint(60, 200)
        gh = random.randint(4, 14)
        glitch_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        glitch_surf.fill((random.randint(80, 200), 40, random.randint(80, 200), ga),
                         pygame.Rect(gx, gy, gw, gh))
        screen.blit(glitch_surf, (0, 0))


def _draw_entity_presence(screen, t):
    screen.fill((2, 2, 6))
    cx, cy = WIDTH // 2, HEIGHT // 2
    pulse = (math.sin(t * 1.2) + 1) * 0.5

    for r in range(300, 0, -12):
        ratio = r / 300
        alpha = int(80 * (1 - ratio) * pulse)
        pygame.draw.circle(screen, (int(60 * ratio), 0, int(100 * (1 - ratio))),
                           (cx, cy), r, 1)

    eye_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    eye_alpha = int(80 + 120 * pulse)
    pygame.draw.ellipse(eye_surf, (160, 0, 200, eye_alpha),
                        pygame.Rect(cx - 120, cy - 50, 240, 100), 3)
    pygame.draw.circle(eye_surf, (200, 20, 240, eye_alpha), (cx, cy), int(22 + 8 * pulse))
    pygame.draw.circle(eye_surf, (0, 0, 0, 255), (cx, cy), int(10 + 4 * pulse))
    screen.blit(eye_surf, (0, 0))

    random.seed(int(t * 8))
    for _ in range(18):
        px = random.randint(0, WIDTH)
        py = random.randint(0, HEIGHT)
        pa = random.randint(60, 180)
        pygame.draw.circle(screen, (120, 0, 160, pa), (px, py), random.randint(1, 3))
    random.seed()


def draw_scene_background(screen, scene_type, t):
    if scene_type == "arrival":
        _draw_arrival(screen, t)
    elif scene_type == "ship_corridor":
        _draw_corridor(screen, t)
    elif scene_type == "crew_echo":
        _draw_crew_echo(screen, t)
    elif scene_type == "fracture":
        _draw_fracture(screen, t)
    elif scene_type == "core_chamber":
        _draw_core_chamber(screen, t)
    elif scene_type == "all_timelines":
        _draw_all_timelines(screen, t)
    elif scene_type == "entity_presence":
        _draw_entity_presence(screen, t)
    else:
        screen.fill((8, 8, 12))


def draw_text_with_animation(screen, text, x, y, font, color, animation_type="fade", t=0, duration=1.0):
    if animation_type == "typewriter":
        animated_text = animate_typewriter(text, t, char_delay=0.032)
        surf = font.render(animated_text, True, color)
    elif animation_type == "fade":
        surf = font.render(text, True, color)
        alpha = min(255, int(255 * (t / max(0.01, duration))))
        surf.set_alpha(alpha)
    elif animation_type == "bounce":
        y_new = animate_bounce(y, t, frequency=2.0, amplitude=8)
        surf = font.render(text, True, color)
        screen.blit(surf, (x - surf.get_width() // 2, int(y_new)))
        return
    elif animation_type == "glitch":
        surf = font.render(text, True, color)
        gx, gy = animate_glitch(t, glitch_chance=0.18)
        screen.blit(surf, (x - surf.get_width() // 2 + gx, y + gy))
        return
    else:
        surf = font.render(text, True, color)

    screen.blit(surf, (x - surf.get_width() // 2, y))


def draw_cutscene(screen, title, lines, t, prompt="Press Enter to continue",
                  map_data=None, animation_config=None):
    if animation_config is None:
        animation_config = {}

    scene_type       = animation_config.get("scene", "ship_corridor")
    title_anim       = animation_config.get("title_anim", "fade")
    lines_anim       = animation_config.get("lines_anim", ["typewriter"] * len(lines))
    duration         = animation_config.get("duration", 3.0)
    glitch_intensity = animation_config.get("glitch_intensity", 0.08)

    draw_scene_background(screen, scene_type, t)

    if glitch_intensity > 0:
        draw_corrupted_screen(screen, t, intensity=glitch_intensity)

    panel = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 120))
    screen.blit(panel, (0, 0))

    title_font = pygame.font.SysFont("courier", 30, bold=True)
    body_font  = pygame.font.SysFont("courier", 19)
    sub_font   = pygame.font.SysFont("courier", 15)

    line_start_times = [i * 0.55 for i in range(len(lines))]

    y = 90
    draw_text_with_animation(
        screen, title, WIDTH // 2, y, title_font, (210, 220, 240),
        animation_type=title_anim, t=t, duration=0.8,
    )

    pygame.draw.line(screen, (60, 100, 160),
                     (WIDTH // 2 - 260, y + 38), (WIDTH // 2 + 260, y + 38), 1)

    y += 60

    for i, line in enumerate(lines):
        anim_type = lines_anim[i] if i < len(lines_anim) else "typewriter"
        line_time = max(0.0, t - line_start_times[i])
        if line_time > 0:
            shade = max(170, 210 - i * 8)
            draw_text_with_animation(
                screen, line, WIDTH // 2, y, body_font, (shade, shade + 6, shade + 20),
                animation_type=anim_type, t=line_time, duration=1.5,
            )
        y += 32

    if map_data:
        draw_compound_map(screen, map_data)

    prompt_alpha = int((math.sin(t * 2.8) + 1) * 0.5 * 90) + 140
    prompt_surf  = sub_font.render(prompt, True, (140, 160, 190))
    prompt_surf.set_alpha(prompt_alpha)
    screen.blit(prompt_surf, (WIDTH // 2 - prompt_surf.get_width() // 2, HEIGHT - 64))


def draw_compound_map(screen, map_data):
    box   = pygame.Rect(60, 190, WIDTH - 120, 240)
    panel = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
    panel.fill((8, 14, 24, 210))
    pygame.draw.rect(panel, (70, 110, 160, 200), panel.get_rect(), 2)

    for x in range(0, box.width, 22):
        pygame.draw.line(panel, (30, 50, 80), (x, 0), (x, box.height), 1)
    for y in range(0, box.height, 22):
        pygame.draw.line(panel, (30, 50, 80), (0, y), (box.width, y), 1)

    for link in map_data.get("links", []):
        x1, y1 = link["a"]
        x2, y2 = link["b"]
        pygame.draw.line(panel, (120, 170, 220), (x1, y1), (x2, y2), 2)

    for room in map_data.get("rooms", []):
        rect = pygame.Rect(room["x"], room["y"], room["w"], room["h"])
        pygame.draw.rect(panel, room["color"], rect)
        pygame.draw.rect(panel, (200, 220, 240), rect, 1)
        label = map_data["font"].render(room["name"], True, (230, 240, 250))
        panel.blit(label, (rect.x + 5, rect.y + 4))

    screen.blit(panel, (box.x, box.y))
```

## fps_game/systems/grenades.py
Filename: `fps_game/systems/grenades.py`

```python
import math
import random

import pygame

from core.settings import HALF_FOV, WIDTH, FOV, NUM_RAYS, HALF_HEIGHT, TILE
from utils.math_utils import is_wall


# ── Grenade type definitions ──────────────────────────────────────────────────
GRENADE_DEFS = {
    "space": {
        "key":         "Z",
        "label":       "VOID",
        "color":       (80,  200, 255),   # cyan
        "throw_speed": 14,
        "fuse":        50,
        "radius":      130,
        "icon":        "◎",
        "cooldown":    60,
        "description": "Slows enemies in radius",
    },
    "smoke": {
        "key":         "X",
        "label":       "SMOKE",
        "color":       (160, 170, 190),   # grey-blue
        "throw_speed": 12,
        "fuse":        30,
        "radius":      150,
        "icon":        "≋",
        "cooldown":    80,
        "description": "Obscures vision zone",
    },
    "stun": {
        "key":         "C",
        "label":       "STUN",
        "color":       (255, 220,  50),   # amber
        "throw_speed": 13,
        "fuse":        35,
        "radius":      140,
        "icon":        "⚡",
        "cooldown":    100,
        "description": "Stuns enemies in radius",
    },
    "nuclear": {
        "key":         "V",
        "label":       "NOVA",
        "color":       (255,  80,  60),   # red-orange
        "throw_speed": 10,
        "fuse":        65,
        "radius":      250,
        "icon":        "☢",
        "cooldown":    180,
        "description": "Massive damage + stun",
    },
}

# Draw order for the HUD slots
HUD_ORDER = ["space", "smoke", "stun", "nuclear"]


class GrenadeSystem:
    def __init__(self):
        self.grenades = []
        self.smokes   = []
        self.explosions = []          # visual-only explosion particles

        self.cooldowns = {k: 0 for k in GRENADE_DEFS}

        # Persistent fonts (created once)
        self._font_label  = None
        self._font_key    = None
        self._font_desc   = None
        self._fonts_ready = False

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._font_label = pygame.font.SysFont("courier", 13, bold=True)
            self._font_key   = pygame.font.SysFont("courier", 11, bold=True)
            self._font_desc  = pygame.font.SysFont("courier", 10)
            self._fonts_ready = True

    # ── throwing ──────────────────────────────────────────────────────────────

    def try_throw(self, grenade_type, player):
        if grenade_type not in GRENADE_DEFS:
            return False
        if self.cooldowns[grenade_type] > 0:
            return False

        defn = GRENADE_DEFS[grenade_type]
        self.cooldowns[grenade_type] = defn["cooldown"]

        self.grenades.append({
            "type":   grenade_type,
            "x":      player.x,
            "y":      player.y,
            "angle":  player.angle,
            "speed":  defn["throw_speed"],
            "fuse":   defn["fuse"],
            "radius": defn["radius"],
            "age":    0,
        })
        return True

    # ── update ────────────────────────────────────────────────────────────────

    def update(self, world, doors, enemies, time_scale):
        events = {"shake": 0, "flash": 0, "chroma": 0, "zoom": 0}

        # Tick cooldowns
        for key in self.cooldowns:
            if self.cooldowns[key] > 0:
                self.cooldowns[key] -= 1

        # Update grenades
        for grenade in self.grenades[:]:
            grenade["age"] += 1

            # Fuse ticks with time_scale (so dilation slows grenades too)
            effective_fuse_drain = max(0.1, time_scale)
            grenade["fuse"] -= effective_fuse_drain

            if grenade["fuse"] <= 0:
                self._explode(grenade, enemies, events)
                pygame.mixer.Sound.play(pygame.mixer.Sound("fps_game/assets/sounds/effects/explosion.mp3"))
                self.grenades.remove(grenade)
                continue

            if time_scale == 0.0:
                continue

            nx = grenade["x"] + math.cos(grenade["angle"]) * grenade["speed"] * time_scale
            ny = grenade["y"] + math.sin(grenade["angle"]) * grenade["speed"] * time_scale

            if is_wall(nx, ny, world, TILE, doors):
                grenade["speed"] = 0
                grenade["fuse"]  = min(grenade["fuse"], 15)
            else:
                grenade["x"] = nx
                grenade["y"] = ny

            # Decelerate (friction)
            grenade["speed"] = max(0.0, grenade["speed"] - 0.4 * time_scale)

        # Update smoke clouds
        for smoke in self.smokes[:]:
            smoke["timer"] -= 1
            smoke["radius"] = min(smoke["max_radius"],
                                  smoke["radius"] + 0.8)   # expand over time
            if smoke["timer"] <= 0:
                self.smokes.remove(smoke)

        # Update explosion particles
        for p in self.explosions[:]:
            p["x"]    += p["vx"]
            p["y"]    += p["vy"]
            p["life"] -= 1
            p["vx"]   *= 0.92
            p["vy"]   *= 0.92
            if p["life"] <= 0:
                self.explosions.remove(p)

        return events

    # ── explosion logic ───────────────────────────────────────────────────────

    def _explode(self, grenade, enemies, events):
        gtype  = grenade["type"]
        radius = grenade["radius"]
        defn   = GRENADE_DEFS[gtype]
        color  = defn["color"]

        # Spawn explosion particles
        particle_count = {"space": 20, "smoke": 8, "stun": 28, "nuclear": 50}
        for _ in range(particle_count.get(gtype, 16)):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.5, 6.0)
            self.explosions.append({
                "x":    grenade["x"],
                "y":    grenade["y"],
                "vx":   math.cos(angle) * speed,
                "vy":   math.sin(angle) * speed,
                "life": random.randint(18, 50),
                "max_life": 50,
                "color": color,
                "size": random.randint(2, 6),
            })

        # Smoke leaves a persistent cloud
        if gtype == "smoke":
            self.smokes.append({
                "x":          grenade["x"],
                "y":          grenade["y"],
                "radius":     40,
                "max_radius": radius,
                "timer":      180,
                "color":      color,
            })
            events["flash"] = max(events["flash"], 2)
            return

        # Damage + status effects for all other types
        for enemy in enemies:
            dx   = enemy["x"] - grenade["x"]
            dy   = enemy["y"] - grenade["y"]
            dist = math.hypot(dx, dy)

            if dist <= radius and enemy["alive"]:
                falloff = max(0.15, 1.0 - dist / radius)

                if gtype == "space":
                    enemy["health"]    -= int(40 * falloff)
                    enemy["slow_timer"] = max(enemy.get("slow_timer", 0), 100)

                elif gtype == "stun":
                    enemy["health"]    -= int(20 * falloff)
                    enemy["stun_timer"] = max(enemy.get("stun_timer", 0), 100)

                elif gtype == "nuclear":
                    enemy["health"]    -= int(220 * falloff)
                    enemy["stun_timer"] = max(enemy.get("stun_timer", 0), 130)

                if enemy["health"] <= 0:
                    enemy["alive"] = False

        # Screen feedback
        if gtype == "space":
            events["shake"] = max(events["shake"], 7)
            events["flash"] = max(events["flash"], 4)
            events["chroma"] = max(events["chroma"], 7)
        elif gtype == "stun":
            events["flash"] = max(events["flash"], 5)
            events["chroma"] = max(events["chroma"], 5)
            events["shake"] = max(events["shake"], 5)
        elif gtype == "nuclear":
            events["shake"] = max(events["shake"], 18)
            events["flash"] = max(events["flash"], 12)
            events["chroma"] = max(events["chroma"], 14)
            events["zoom"]  = max(events["zoom"], 0.10)

    # ── drawing ───────────────────────────────────────────────────────────────

    def draw_grenades(self, screen, player, depth_buffer, anim_time=0.0):
        """Draw in-flight grenades, smoke clouds, and explosion particles."""

        # Explosion particles (2-D overlay — always visible, no depth test)
        for p in self.explosions:
            ratio = p["life"] / p["max_life"]
            alpha = int(220 * ratio)
            r, g, b = p["color"]
            size  = max(1, int(p["size"] * ratio))
            surf  = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (r, g, b, alpha), (size, size), size)
            # Project particle into 3-D view
            self._draw_projected(screen, player, depth_buffer,
                                 p["x"], p["y"], size * 2, p["color"],
                                 alpha=alpha, depth_scale=0.5)

        # Smoke clouds
        for smoke in self.smokes:
            pulse = 1.0 + 0.12 * math.sin(anim_time * 1.8)
            draw_r = smoke["radius"] * pulse
            self._draw_projected(screen, player, depth_buffer,
                                 smoke["x"], smoke["y"],
                                 draw_r, smoke["color"], alpha=65)

        # In-flight grenades
        for grenade in self.grenades:
            defn   = GRENADE_DEFS[grenade["type"]]
            color  = defn["color"]

            # Fuse urgency — flash faster as fuse expires
            fuse_ratio = max(0.0, grenade["fuse"] / defn["fuse"])
            flash_freq = 4.0 + (1.0 - fuse_ratio) * 10.0
            visible    = (math.sin(anim_time * flash_freq) > -0.3)
            if not visible:
                continue

            # Size pulses as fuse runs low
            base_size = 14 + int((1.0 - fuse_ratio) * 10)
            self._draw_projected(screen, player, depth_buffer,
                                 grenade["x"], grenade["y"],
                                 base_size, color, alpha=230)

    def _draw_projected(self, screen, player, depth_buffer,
                        wx, wy, size_base, color, alpha=255, depth_scale=1.0):
        """Billboard-project a world-space circle into screen space."""
        dx   = wx - player.x
        dy   = wy - player.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return

        theta = math.atan2(dy, dx)
        delta = (theta - player.angle) % (2 * math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi

        if not (-HALF_FOV < delta < HALF_FOV):
            return

        screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
        size     = min(2000 / (dist + 0.0001), size_base)
        sx       = screen_x - size // 2
        sy       = HALF_HEIGHT - size // 2

        ray_index = max(0, min(NUM_RAYS - 1, int(screen_x * NUM_RAYS / WIDTH)))
        if ray_index >= len(depth_buffer):
            return
        if dist * depth_scale >= depth_buffer[ray_index]:
            return

        isize = max(1, int(size))
        surf  = pygame.Surface((isize, isize), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*color, min(255, alpha)),
                           (isize // 2, isize // 2), isize // 2)
        screen.blit(surf, (int(sx), int(sy)))


    def draw_hud(self, screen, ui_phase):
        """
        Four grenade slots in the bottom-left corner.
        Each slot shows:
          • Icon + label
          • Cooldown bar (fills left→right as it recharges)
          • [KEY] binding
          • Dim overlay when on cooldown
        """
        self._ensure_fonts()

        SLOT_W    = 72
        SLOT_H    = 58
        SLOT_PAD  = 6
        MARGIN_X  = 18
        MARGIN_Y  = 110          # from bottom of screen
        HEIGHT = screen.get_height()

        total_w = len(HUD_ORDER) * (SLOT_W + SLOT_PAD) - SLOT_PAD
        start_x = MARGIN_X
        start_y = HEIGHT - MARGIN_Y - SLOT_H

        pulse = 0.5 + 0.5 * math.sin(ui_phase * 2.2)

        for i, gtype in enumerate(HUD_ORDER):
            defn   = GRENADE_DEFS[gtype]
            cd     = self.cooldowns[gtype]
            cd_max = defn["cooldown"]
            ready  = (cd == 0)

            sx = start_x + i * (SLOT_W + SLOT_PAD)
            sy = start_y

            color  = defn["color"]
            dim_color = tuple(max(0, c // 3) for c in color)

            # ── Slot background ───────────────────────────────────────────
            bg = pygame.Surface((SLOT_W, SLOT_H), pygame.SRCALPHA)
            bg_alpha = 180 if ready else 100
            bg.fill((8, 12, 20, bg_alpha))
            pygame.draw.rect(bg, (*( color if ready else dim_color ), 160),
                             bg.get_rect(), 1, border_radius=4)
            screen.blit(bg, (sx, sy))

            # ── Icon ──────────────────────────────────────────────────────
            icon_font = pygame.font.SysFont("segoeui", 20)
            icon_col  = color if ready else dim_color
            icon_surf = icon_font.render(defn["icon"], True, icon_col)
            if ready:
                # Subtle glow pulse on ready icons
                icon_surf.set_alpha(200 + int(55 * pulse))
            else:
                icon_surf.set_alpha(130)
            screen.blit(icon_surf,
                        (sx + SLOT_W // 2 - icon_surf.get_width() // 2,
                         sy + 5))

            # ── Label ─────────────────────────────────────────────────────
            label_col  = color if ready else dim_color
            label_surf = self._font_label.render(defn["label"], True, label_col)
            label_surf.set_alpha(220 if ready else 120)
            screen.blit(label_surf,
                        (sx + SLOT_W // 2 - label_surf.get_width() // 2,
                         sy + 27))

            # ── Cooldown bar ──────────────────────────────────────────────
            bar_x = sx + 4
            bar_y = sy + SLOT_H - 14
            bar_w = SLOT_W - 8
            bar_h = 5

            pygame.draw.rect(screen, (20, 28, 40), (bar_x, bar_y, bar_w, bar_h))

            if ready:
                fill_w = bar_w
                bar_col = color
            else:
                ratio  = 1.0 - cd / cd_max
                fill_w = int(bar_w * ratio)
                bar_col = tuple(max(0, c - 60) for c in color)

            if fill_w > 0:
                pygame.draw.rect(screen, bar_col, (bar_x, bar_y, fill_w, bar_h))

            pygame.draw.rect(screen, (*( color if ready else dim_color ), 120),
                             (bar_x, bar_y, bar_w, bar_h), 1)

            # ── Key binding ───────────────────────────────────────────────
            key_col  = (200, 200, 200) if ready else (90, 90, 90)
            key_surf = self._font_key.render(f"[{defn['key']}]", True, key_col)
            screen.blit(key_surf,
                        (sx + SLOT_W // 2 - key_surf.get_width() // 2,
                         sy + SLOT_H - 12))

            # ── Cooldown overlay + remaining time ─────────────────────────
            if not ready:
                overlay = pygame.Surface((SLOT_W, SLOT_H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 70))
                screen.blit(overlay, (sx, sy))

                secs_left = cd / 60.0
                cd_surf   = self._font_label.render(
                    f"{secs_left:.1f}s", True, (180, 180, 180)
                )
                cd_surf.set_alpha(200)
                screen.blit(cd_surf,
                            (sx + SLOT_W // 2 - cd_surf.get_width() // 2,
                             sy + SLOT_H // 2 - cd_surf.get_height() // 2))

            # ── "READY" flash when cooldown just expired ──────────────────
            if ready and cd_max > 0:
                # We can't detect the exact frame cd hit 0, but we can flash
                # for a brief window by checking if fill is full and pulsing
                if pulse > 0.85:
                    glow = pygame.Surface((SLOT_W, SLOT_H), pygame.SRCALPHA)
                    glow.fill((*color, 18))
                    screen.blit(glow, (sx, sy))
```

## fps_game/systems/menu.py
Filename: `fps_game/systems/menu.py`

```python
import math
import pygame
from core.settings import WIDTH, HEIGHT


def draw_menu(screen):
    t = pygame.time.get_ticks() / 1000.0

    title_font   = pygame.font.SysFont("courier", 52, bold=True)
    sub_font     = pygame.font.SysFont("courier", 18, bold=True)
    body_font    = pygame.font.SysFont("courier", 15)
    tiny_font    = pygame.font.SysFont("courier", 13)

    pulse = (math.sin(t * 1.6) + 1) * 0.5
    glow_a = int(60 + 80 * pulse)

    title_surf = title_font.render("ASTRAEUS", True, (200, 215, 240))
    glow_surf  = title_font.render("ASTRAEUS", True, (60, 120, 220))
    glow_surf.set_alpha(glow_a)

    tx = WIDTH // 2 - title_surf.get_width() // 2
    ty = HEIGHT // 4 - title_surf.get_height() // 2

    screen.blit(glow_surf, (tx + 3, ty + 3))
    screen.blit(title_surf, (tx, ty))

    sub_surf = sub_font.render("DEEP-SPACE TEMPORAL RESEARCH VESSEL", True, (100, 140, 190))
    screen.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, ty + 64))

    pygame.draw.line(screen, (50, 80, 130),
                     (WIDTH // 2 - 280, ty + 88), (WIDTH // 2 + 280, ty + 88), 1)

    status_lines = [
        "VESSEL STATUS: ACTIVE",
        "CREW STATUS: UNRESPONSIVE",
        "TEMPORAL COHERENCE: 38%",
        "CORE TEMPERATURE: CRITICAL",
    ]
    sy = ty + 106
    for i, line in enumerate(status_lines):
        flicker = 0.6 + 0.4 * math.sin(t * (2.1 + i * 0.7) + i)
        a = int(180 * flicker)
        color = (80, 140, 200) if i < 2 else (220, 80, 80)
        surf = body_font.render(line, True, color)
        surf.set_alpha(a)
        screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, sy + i * 22))

    pygame.draw.line(screen, (50, 80, 130),
                     (WIDTH // 2 - 280, sy + 100), (WIDTH // 2 + 280, sy + 100), 1)

    enter_a = int(160 + 95 * pulse)
    enter_surf = sub_font.render("[ ENTER ]  COMMENCE BOARDING SEQUENCE", True, (180, 200, 240))
    enter_surf.set_alpha(enter_a)
    screen.blit(enter_surf, (WIDTH // 2 - enter_surf.get_width() // 2, sy + 116))

    settings_surf = body_font.render("[ S ]  SUIT CALIBRATION", True, (100, 130, 170))
    screen.blit(settings_surf, (WIDTH // 2 - settings_surf.get_width() // 2, sy + 146))

    controls = [
        "WASD: MOVE     MOUSE: AIM     LMB: FIRE     R: RELOAD / REWIND",
        "Q: TIME DILATION     G: TEMPORAL ECHO     E: DOOR",
        "1/2/3: WEAPON     Z/X/C/V: GRENADES     ESC: PAUSE",
    ]
    cy2 = HEIGHT - 80
    for line in controls:
        cs = tiny_font.render(line, True, (60, 80, 110))
        screen.blit(cs, (WIDTH // 2 - cs.get_width() // 2, cy2))
        cy2 += 18

    warning_a = int(100 + 60 * math.sin(t * 3.4))
    warning = tiny_font.render(
        "WARNING: TEMPORAL ANOMALY DETECTED IN SECTORS 4, 7, 11  —  PROCEED WITH CAUTION",
        True, (180, 60, 60)
    )
    warning.set_alpha(warning_a)
    screen.blit(warning, (WIDTH // 2 - warning.get_width() // 2, HEIGHT - 20))
```

## fps_game/systems/minimap.py
Filename: `fps_game/systems/minimap.py`

```python
import math

import pygame

from core.settings import TILE


def _collect_bounds(world, player, enemies, health_packs):
    tiles = list(world.keys())
    if tiles:
        min_tx = min(x for x, _ in tiles) // TILE
        min_ty = min(y for _, y in tiles) // TILE
        max_tx = max(x for x, _ in tiles) // TILE
        max_ty = max(y for _, y in tiles) // TILE
    else:
        min_tx = max_tx = int(player.x // TILE)
        min_ty = max_ty = int(player.y // TILE)

    extra_points = []
    extra_points.append((player.x, player.y))
    for enemy in enemies:
        extra_points.append((enemy["x"], enemy["y"]))
    for pack in health_packs:
        extra_points.append((pack["x"], pack["y"]))

    for px, py in extra_points:
        tx = int(px // TILE)
        ty = int(py // TILE)
        min_tx = min(min_tx, tx)
        min_ty = min(min_ty, ty)
        max_tx = max(max_tx, tx)
        max_ty = max(max_ty, ty)

    return min_tx, min_ty, max_tx, max_ty


def draw_minimap(screen, world, player, enemies, health_packs, alpha=140, rooms=None, room_colors=None):
    if not world:
        return

    base_tile = 6
    max_size = 180
    margin = 10
    padding = 6

    min_tx, min_ty, max_tx, max_ty = _collect_bounds(world, player, enemies, health_packs)
    tiles_w = max_tx - min_tx + 1
    tiles_h = max_ty - min_ty + 1

    tile_size = base_tile
    map_w = tiles_w * tile_size
    map_h = tiles_h * tile_size
    if map_w > max_size or map_h > max_size:
        scale = max_size / max(map_w, map_h)
        tile_size = max(2, int(base_tile * scale))
        map_w = tiles_w * tile_size
        map_h = tiles_h * tile_size

    surf_w = map_w + padding * 2
    surf_h = map_h + padding * 2
    surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, max(40, min(200, int(alpha)))))

    wall_color = (120, 120, 120)
    for (wx, wy) in world.keys():
        tx = int(wx // TILE) - min_tx
        ty = int(wy // TILE) - min_ty
        rect = pygame.Rect(
            padding + tx * tile_size,
            padding + ty * tile_size,
            tile_size,
            tile_size,
        )
        pygame.draw.rect(surf, wall_color, rect)

    if rooms:
        for (rx, ry), rkey in rooms.items():
            tx = int(rx // TILE) - min_tx
            ty = int(ry // TILE) - min_ty
            rect = pygame.Rect(
                padding + tx * tile_size,
                padding + ty * tile_size,
                tile_size,
                tile_size,
            )
            color = (160, 160, 200)
            if room_colors and rkey in room_colors:
                color = room_colors[rkey]
            pygame.draw.rect(surf, color, rect)

    def to_minimap(px, py):
        tx = (px / TILE - min_tx) * tile_size + padding
        ty = (py / TILE - min_ty) * tile_size + padding
        return tx, ty

    for pack in health_packs:
        hx, hy = to_minimap(pack["x"], pack["y"])
        size = max(2, tile_size // 2)
        rect = pygame.Rect(hx - size // 2, hy - size // 2, size, size)
        pygame.draw.rect(surf, (80, 200, 255), rect)

    for enemy in enemies:
        ex, ey = to_minimap(enemy["x"], enemy["y"])
        r = max(2, tile_size // 2)
        color = (220, 60, 60) if enemy["alive"] else (120, 60, 60)
        pygame.draw.circle(surf, color, (int(ex), int(ey)), r)

    px, py = to_minimap(player.x, player.y)
    pr = max(2, tile_size // 2 + 1)
    pygame.draw.circle(surf, (60, 220, 120), (int(px), int(py)), pr)

    line_len = max(6, tile_size * 2)
    lx = px + math.cos(player.angle) * line_len
    ly = py + math.sin(player.angle) * line_len
    pygame.draw.line(surf, (255, 255, 255), (px, py), (lx, ly), 2)

    screen.blit(surf, (margin, margin))
```

## fps_game/systems/raycasting.py
Filename: `fps_game/systems/raycasting.py`

```python
import math
import pygame

from core.settings import WIDTH, HALF_HEIGHT, FOV, HALF_FOV, NUM_RAYS, MAX_DEPTH, DELTA_ANGLE, TILE, SCALE


def raycast(world, player, screen, textures=None, doors=None, door_texture=None):
    depth_buffer = []
    cur_angle = player.angle - HALF_FOV

    for ray in range(NUM_RAYS):
        depth_wall = MAX_DEPTH

        for depth in range(1, MAX_DEPTH):
            x = player.x + depth * math.cos(cur_angle)
            y = player.y + depth * math.sin(cur_angle)

            tile_x = int(x // TILE) * TILE
            tile_y = int(y // TILE) * TILE

            door = doors.get((tile_x, tile_y)) if doors else None
            hit_wall = (tile_x, tile_y) in world
            hit_door = door is not None and not door.get("open")
            if hit_wall or hit_door:
                depth *= math.cos(player.angle - cur_angle)
                depth_wall = depth
                proj_height = (TILE * 300) / (depth + 0.0001)

                # Sharp distance falloff — close walls bright, far walls very dark.
                # This is critical for the "enclosed corridor" feel.
                brightness = 240 / (1 + depth * depth * 0.00013)
                brightness = max(18, min(240, brightness))

                if hit_door and door_texture is not None:
                    tex = door_texture
                elif textures:
                    key = world.get((tile_x, tile_y), "#")
                    tex = textures.get(key)
                else:
                    tex = None

                col_x     = ray * WIDTH / NUM_RAYS
                col_width = (ray + 1) * WIDTH / NUM_RAYS - col_x

                if tex is not None and tex:
                    tex_w  = tex.get_width()
                    tex_h  = tex.get_height()
                    tex_x  = int((x % TILE) / TILE * tex_w)
                    tex_x  = max(0, min(tex_w - 1, tex_x))
                    column = tex.subsurface((tex_x, 0, 1, tex_h))
                    column = pygame.transform.scale(column, (int(col_width), int(proj_height)))

                    # Cool steel tint: push RGB toward dark blue-grey
                    shade = max(18, min(255, int(brightness)))
                    r_mul = max(0, min(255, int(shade * 0.72)))
                    g_mul = max(0, min(255, int(shade * 0.85)))
                    b_mul = max(0, min(255, int(shade * 1.10)))
                    column.fill((r_mul, g_mul, b_mul), special_flags=pygame.BLEND_MULT)
                    column.fill((0, 6, 16), special_flags=pygame.BLEND_RGB_ADD)

                    screen.blit(column, (int(col_x), HALF_HEIGHT - int(proj_height) // 2))
                else:
                    # Fallback: dark cool-steel colour
                    r = max(0, int(brightness * 0.55))
                    g = max(0, int(brightness * 0.68))
                    b = max(0, int(brightness * 0.88))
                    pygame.draw.rect(
                        screen,
                        (r, g, b),
                        (int(col_x), HALF_HEIGHT - int(proj_height) // 2,
                         int(col_width), int(proj_height)),
                    )
                break

        depth_buffer.append(depth_wall)
        cur_angle += DELTA_ANGLE

    return depth_buffer
```

## fps_game/systems/settings_menu.py
Filename: `fps_game/systems/settings_menu.py`

```python
import math
import pygame
from core.settings import WIDTH, HEIGHT


def draw_settings(screen, settings):
    t = pygame.time.get_ticks() / 1000.0

    title_font = pygame.font.SysFont("courier", 28, bold=True)
    body_font  = pygame.font.SysFont("courier", 18)
    tiny_font  = pygame.font.SysFont("courier", 14)

    title_surf = title_font.render("SUIT CALIBRATION", True, (180, 210, 240))
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, HEIGHT // 3 - 60))

    pygame.draw.line(screen, (50, 80, 130),
                     (WIDTH // 2 - 200, HEIGHT // 3 - 24),
                     (WIDTH // 2 + 200, HEIGHT // 3 - 24), 1)

    sens_val = f"{settings['sensitivity']:.3f}"
    sens_surf = body_font.render(f"AIM SENSITIVITY :  {sens_val}", True, (200, 215, 240))
    screen.blit(sens_surf, (WIDTH // 2 - sens_surf.get_width() // 2, HEIGHT // 3))

    hint_surf = tiny_font.render("UP / DOWN to adjust", True, (90, 120, 160))
    screen.blit(hint_surf, (WIDTH // 2 - hint_surf.get_width() // 2, HEIGHT // 3 + 30))

    pygame.draw.line(screen, (50, 80, 130),
                     (WIDTH // 2 - 200, HEIGHT // 3 + 60),
                     (WIDTH // 2 + 200, HEIGHT // 3 + 60), 1)

    back_a = int(160 + 80 * ((math.sin(t * 2.2) + 1) * 0.5))
    back_surf = body_font.render("[ ESC ]  RETURN TO DOCKING BAY", True, (140, 170, 210))
    back_surf.set_alpha(back_a)
    screen.blit(back_surf, (WIDTH // 2 - back_surf.get_width() // 2, HEIGHT // 3 + 80))

    note_surf = tiny_font.render(
        "Higher sensitivity recommended in temporal fracture zones.", True, (70, 100, 140)
    )
    screen.blit(note_surf, (WIDTH // 2 - note_surf.get_width() // 2, HEIGHT // 3 + 120))
```

## fps_game/systems/temporal.py
Filename: `fps_game/systems/temporal.py`

```python
import math
import random
import pygame
from core.settings import WIDTH, HEIGHT, HALF_HEIGHT, TILE


                                                                               
           
                                                                               
DILATION_MAX_ENERGY    = 100.0
DILATION_DRAIN_RATE    = 22.0                                                 
DILATION_REGEN_RATE    = 14.0
DILATION_TIME_SCALE    = 0.25                                      
PLAYER_DILATION_SCALE  = 0.72                                                     

REWIND_HISTORY_SECS    = 15                                  
REWIND_FPS             = 30                                  
REWIND_MAX_FRAMES      = int(REWIND_HISTORY_SECS * REWIND_FPS)
REWIND_COOLDOWN_SECS   = 8.0                                   
REWIND_DURATION_FRAMES = 18                                              

ECHO_DURATION_FRAMES   = 200                                       
ECHO_COOLDOWN_SECS     = 12.0
ECHO_TRAIL_ALPHA       = 110

FRACTURE_ZONE_TYPES    = ["slow", "reverse", "fast", "mirror", "nullgrav"]

TRAIL_MAX_POINTS       = 18
TRAIL_FADE_RATE        = 14                                        


                                                                               
                                                    
                                                                               
def _snap_player(player):
    return {
        "x": player.x, "y": player.y, "angle": player.angle,
        "health": player.health, "inv": player.invincibility_frames,
        "speed": player.current_speed,
    }

def _snap_enemies(enemies):
    return [
        {"x": e["x"], "y": e["y"], "health": e["health"], "alive": e["alive"],
         "stun": e.get("stun_timer", 0), "slow": e.get("slow_timer", 0),
         "death": e.get("death_timer", 0)}
        for e in enemies
    ]


                                                                               
                  
                                                                               
class TimeDilation:
    def __init__(self):
        self.energy       = DILATION_MAX_ENERGY
        self.active       = False
        self.world_scale  = 1.0                                 
        self.player_scale = 1.0
        self._ramp        = 0.0                                 

    def toggle(self):
        if self.energy > 2.0:
            self.active = not self.active
        elif self.active:
            self.active = False

    def update(self, dt_frames=1):
        target_ramp = 1.0 if self.active else 0.0
        self.ramp    = getattr(self, "ramp", 0.0)
        self.ramp   += (target_ramp - self.ramp) * 0.12

        if self.active:
            drain = (DILATION_DRAIN_RATE / 60.0) * dt_frames
            self.energy = max(0.0, self.energy - drain)
            if self.energy <= 0.0:
                self.active = False
        else:
            regen = (DILATION_REGEN_RATE / 60.0) * dt_frames
            self.energy = min(DILATION_MAX_ENERGY, self.energy + regen)

        r = self.ramp
        self.world_scale  = 1.0 - r * (1.0 - DILATION_TIME_SCALE)
        self.player_scale = 1.0 - r * (1.0 - PLAYER_DILATION_SCALE)
        return self.world_scale, self.player_scale

    @property
    def energy_ratio(self):
        return self.energy / DILATION_MAX_ENERGY


                                                                               
                
                                                                               
class TimeRewind:
    def __init__(self):
        self._history: list[dict] = []        # oldest → newest
        self._tick   = 0
        self._sub    = max(1, 60 // REWIND_FPS)
 
        self.cooldown        = 0
        self.cooldown_max    = int(REWIND_COOLDOWN_SECS * 60)
        self.rewinding       = False
        self._playback       = []             # reversed slice we walk through
        self._playback_idx   = 0             # current position in _playback
        self.flash_alpha     = 0
 
 
    def record(self, player, enemies):
        """Called every frame during normal play to build the history buffer."""
        self._tick += 1
        if self._tick % self._sub != 0:
            return
        snap = {"p": _snap_player(player), "e": _snap_enemies(enemies)}
        self._history.append(snap)
        if len(self._history) > REWIND_MAX_FRAMES:
            self._history.pop(0)
 
 
    def can_rewind(self):
        return self.cooldown <= 0 and len(self._history) >= 2 and not self.rewinding
 
    def trigger(self):
        if not self.can_rewind():
            return False
 
        # Reverse the history so index 0 = most-recent, last = oldest.
        # We'll step through this one frame at a time during update().
        self._playback     = list(reversed(self._history))
        self._playback_idx = 0
        self._history.clear()
 
        self.rewinding   = True
        self.cooldown    = self.cooldown_max
        self.flash_alpha = 220
        return True
 
 
    def update(self, player, enemies):
        if self.cooldown > 0:
            self.cooldown -= 1
 
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 10)
 
        if not self.rewinding:
            return False
 
        # Apply the current playback frame
        if self._playback_idx < len(self._playback):
            snap = self._playback[self._playback_idx]
            self._apply(player, enemies, snap)
            self._playback_idx += 1
        else:
            # Reached the end of recorded history — rewind complete
            self.rewinding     = False
            self._playback     = []
            self._playback_idx = 0
 
        return True
 
 
    def _apply(self, player, enemies, snap):
        """Write one history snapshot onto the live player and enemies."""
        p = snap["p"]
        player.x                    = p["x"]
        player.y                    = p["y"]
        player.angle                = p["angle"]
        player.health               = p["health"]
        player.invincibility_frames = p["inv"]
        player.current_speed        = p["speed"]
 
        for i, estate in enumerate(snap["e"]):
            if i < len(enemies):
                e = enemies[i]
                e["x"]           = estate["x"]
                e["y"]           = estate["y"]
                e["health"]      = estate["health"]
                e["alive"]       = estate["alive"]
                e["stun_timer"]  = estate["stun"]
                e["slow_timer"]  = estate["slow"]
                e["death_timer"] = estate["death"]
 
 
    @property
    def cooldown_ratio(self):
        return 1.0 - self.cooldown / self.cooldown_max if self.cooldown_max else 1.0

                                                                               
                                 
                                                                               
class TemporalEcho:
    def __init__(self):
        self._recording : list[dict] = []                        
        self._ghosts    : list[dict] = []                         
        self.cooldown   = 0
        self.cooldown_max = int(ECHO_COOLDOWN_SECS * 60)
        self._rec_tick  = 0
        self._rec_sub   = 2                                        

    def record(self, player):
        self._rec_tick += 1
        if self._rec_tick % self._rec_sub != 0:
            return
        self._recording.append({
            "x": player.x, "y": player.y, "angle": player.angle
        })
                                                
        max_frames = ECHO_DURATION_FRAMES // self._rec_sub + 4
        if len(self._recording) > max_frames:
            self._recording.pop(0)

    def can_spawn(self):
        return self.cooldown <= 0 and len(self._recording) >= 4

    def spawn(self, player):
        if not self.can_spawn():
            return False
        ghost = {
            "frames"   : list(self._recording),
            "frame_idx": 0,
            "x"        : self._recording[0]["x"],
            "y"        : self._recording[0]["y"],
            "angle"    : self._recording[0]["angle"],
            "alpha"    : ECHO_TRAIL_ALPHA,
            "trail"    : [],
        }
        self._ghosts.append(ghost)
        self._recording.clear()
        self.cooldown = self.cooldown_max
        return True

    def update(self):
        if self.cooldown > 0:
            self.cooldown -= 1

        for g in self._ghosts[:]:
                              
            if g["frame_idx"] < len(g["frames"]):
                f = g["frames"][g["frame_idx"]]
                g["trail"].append((g["x"], g["y"]))
                if len(g["trail"]) > TRAIL_MAX_POINTS:
                    g["trail"].pop(0)
                g["x"]     = f["x"]
                g["y"]     = f["y"]
                g["angle"] = f["angle"]
                g["frame_idx"] += 1
            else:
                g["alpha"] -= 8
                if g["alpha"] <= 0:
                    self._ghosts.remove(g)

    def draw(self, screen, player, depth_buffer):
        from core.settings import HALF_FOV, FOV, NUM_RAYS
        for g in self._ghosts:
                             
            for ti, (tx, ty) in enumerate(g["trail"]):
                a  = int(g["alpha"] * 0.4 * (ti / max(1, len(g["trail"]))))
                self._draw_billboard(screen, player, depth_buffer, tx, ty, 6,
                                     (120, 200, 255), a)
                             
            self._draw_billboard(screen, player, depth_buffer,
                                 g["x"], g["y"], 28,
                                 (140, 220, 255), min(200, g["alpha"] * 2))

    @staticmethod
    def _draw_billboard(screen, player, depth_buffer, wx, wy, size, color, alpha):
        if alpha <= 0:
            return
        from core.settings import HALF_FOV, FOV, NUM_RAYS, HALF_HEIGHT
        dx   = wx - player.x
        dy   = wy - player.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        theta = math.atan2(dy, dx)
        delta = (theta - player.angle + math.pi) % (2 * math.pi) - math.pi
        if not (-HALF_FOV < delta < HALF_FOV):
            return
        sx = (delta + HALF_FOV) * (WIDTH / FOV)
        sz = min(2000 / (dist + 0.001), 80)
        ri = max(0, min(NUM_RAYS - 1, int(sx * NUM_RAYS / WIDTH)))
        if ri < len(depth_buffer) and dist < depth_buffer[ri]:
            surf = pygame.Surface((int(sz + size), int(sz + size)), pygame.SRCALPHA)
            surf.fill((*color, min(255, alpha)))
            screen.blit(surf, (int(sx - sz // 2), int(HALF_HEIGHT - sz // 2)))

    @property
    def cooldown_ratio(self):
        return 1.0 - self.cooldown / self.cooldown_max if self.cooldown_max else 1.0


                                                                               
                            
                                                                               
                                                      
FRACTURE_ROOM_EFFECTS = {
    "R": {"type": "slow",     "world_scale": 0.35, "player_scale": 0.60,
          "tint": (255, 80,  80),  "alpha": 55, "scan": True,
          "msg": "REACTOR // TEMPORAL DRAG FIELD"},
    "L": {"type": "fast",     "world_scale": 2.20, "player_scale": 1.15,
          "tint": (80,  255, 160), "alpha": 40, "scan": False,
          "msg": "LAB // ACCELERATED CHRONOLOGY"},
    "H": {"type": "reverse",  "world_scale": -0.8, "player_scale": 0.90,
          "tint": (200, 80,  255), "alpha": 60, "scan": True,
          "msg": "HANGAR // CHRONO-INVERSION ZONE"},
    "Y": {"type": "mirror",   "world_scale": 0.70, "player_scale": -0.85,
          "tint": (80,  180, 255), "alpha": 50, "scan": False,
          "msg": "CRYO BAY // MIRROR TIME FLUX"},
    "O": {"type": "nullgrav",  "world_scale": 0.55, "player_scale": 0.55,
          "tint": (200, 200, 80),  "alpha": 45, "scan": False,
          "msg": "OBSERVATION // NULL-GRAVITY SHEAR"},
}

class FractureZones:
    def __init__(self):
        self.active_effect = None                                          
        self.active_room   = ""
        self.message       = ""
        self.msg_timer     = 0

    def enter_room(self, room_key):
        if room_key == self.active_room:
            return
        self.active_room = room_key
        if room_key in FRACTURE_ROOM_EFFECTS:
            self.active_effect = FRACTURE_ROOM_EFFECTS[room_key]
            self.message   = self.active_effect["msg"]
            self.msg_timer = 120
        else:
            self.active_effect = None

    def leave_room(self):
        self.active_room   = ""
        self.active_effect = None

    def update(self):
        if self.msg_timer > 0:
            self.msg_timer -= 1

    def get_world_scale(self):
        if self.active_effect:
            return self.active_effect["world_scale"]
        return 1.0

    def get_player_scale(self):
        if self.active_effect:
            return self.active_effect["player_scale"]
        return 1.0

    def draw_overlay(self, screen, phase):
        if not self.active_effect:
            return
        effect = self.active_effect
        etype  = effect["type"]
        tint   = effect["tint"]
        alpha  = effect["alpha"]

                    
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        surf.fill((*tint, alpha))
        screen.blit(surf, (0, 0))

                                  
        if effect.get("scan"):
            scan = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for y in range(0, HEIGHT, 5):
                a = 22 if (y // 5) % 2 == 0 else 8
                scan.fill((*tint, a), pygame.Rect(0, y, WIDTH, 2))
            screen.blit(scan, (0, 0))

                                 
        if etype == "reverse":
                                                      
            glitch_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            band_y = int((phase * 60) % HEIGHT)
            pygame.draw.rect(glitch_surf, (*tint, 50),
                             pygame.Rect(0, band_y, WIDTH, 6))
            pygame.draw.rect(glitch_surf, (*tint, 30),
                             pygame.Rect(0, (band_y + HEIGHT // 3) % HEIGHT, WIDTH, 3))
            screen.blit(glitch_surf, (0, 0))

        elif etype == "mirror":
                                      
            pygame.draw.line(screen, (*tint, 180),
                             (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 2)

        elif etype == "nullgrav":
                                    
            random.seed(int(phase * 10))
            pg_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for _ in range(30):
                px = random.randint(0, WIDTH)
                py = (random.randint(0, HEIGHT) + int(phase * 40)) % HEIGHT
                pg_surf.set_at((px, py), (*tint, 160))
            screen.blit(pg_surf, (0, 0))

                      
        if self.msg_timer > 0:
            font  = pygame.font.SysFont("arial", 20, bold=True)
            ratio = self.msg_timer / 120
            a     = int(min(255, 255 * ratio))
            surf  = font.render(self.message, True, tint)
            surf.set_alpha(a)
            screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 - 60))


                                                                               
                                                                   
                                                                               
class TemporalVisuals:
    def __init__(self):
        self._player_trail : list[dict] = []                       
        self._distort_phase  = 0.0
        self._glitch_offsets : list[tuple] = []
        self._glitch_timer   = 0
        self._aberration     = 0                                            

    def record_trail(self, player, intensity=1.0):
        if intensity < 0.05:
            return
        self._player_trail.append({
            "x": player.x, "y": player.y,
            "angle": player.angle,
            "age": 0,
            "alpha": int(160 * intensity)
        })
        if len(self._player_trail) > TRAIL_MAX_POINTS:
            self._player_trail.pop(0)

    def trigger_glitch(self, strength=1.0):
        n = int(6 * strength)
        self._glitch_offsets = [
            (random.randint(-int(12 * strength), int(12 * strength)),
             random.randint(-4, 4),
             random.randint(20, 80),                
             random.randint(0, HEIGHT))
            for _ in range(n)
        ]
        self._glitch_timer   = int(20 * strength)
        self._aberration     = int(10 * strength)

    def update(self, dilation_active: bool, dilation_ratio: float):
        self._distort_phase += 0.04
        for p in self._player_trail[:]:
            p["age"] += 1
            p["alpha"] -= TRAIL_FADE_RATE
            if p["alpha"] <= 0:
                self._player_trail.remove(p)
        if self._glitch_timer > 0:
            self._glitch_timer -= 1
            if random.random() < 0.4:
                self._glitch_offsets = [
                    (random.randint(-8, 8), ox[1], ox[2], ox[3])
                    for ox in self._glitch_offsets
                ]
        if self._aberration > 0:
            self._aberration = max(0, self._aberration - 1)

    def apply_pre_blit(self, scene: pygame.Surface, dilation_active: bool,
                       dilation_ratio: float, rewinding: bool) -> pygame.Surface:
        if rewinding:
                                                
            overlay = pygame.Surface(scene.get_size(), pygame.SRCALPHA)
            overlay.fill((30, 60, 220, 60))
            for y in range(0, HEIGHT, 3):
                overlay.fill((0, 0, 100, 35), pygame.Rect(0, y, WIDTH, 1))
            scene.blit(overlay, (0, 0))
            return scene

        if dilation_active and dilation_ratio > 0.05:
                                               
            scroll_amt = int(math.sin(self._distort_phase * 2) * 3 * dilation_ratio)
            if scroll_amt != 0:
                shifted = pygame.Surface(scene.get_size())
                shifted.blit(scene, (scroll_amt, 0))
                shifted.blit(scene, (scroll_amt - WIDTH, 0))
                scene = shifted

                                       
            tint = pygame.Surface(scene.get_size(), pygame.SRCALPHA)
            tint.fill((60, 200, 255, int(30 * dilation_ratio)))
            scene.blit(tint, (0, 0))

        return scene

    def apply_post_blit(self, screen: pygame.Surface, dilation_active: bool,
                        dilation_ratio: float, rewinding: bool):
                      
        if self._glitch_timer > 0:
            for (ox, oy, bh, by) in self._glitch_offsets:
                band = screen.subsurface(
                    pygame.Rect(max(0, -ox), by, min(WIDTH - abs(ox), WIDTH), min(bh, HEIGHT - by))
                ).copy()
                screen.blit(band, (ox, by))

                                           
        if self._aberration > 0:
            ab = self._aberration
            r_surf = screen.copy()
            b_surf = screen.copy()
            r_surf.fill((255, 140, 140), special_flags=pygame.BLEND_RGB_MULT)
            b_surf.fill((140, 140, 255), special_flags=pygame.BLEND_RGB_MULT)
            r_surf.set_alpha(80)
            b_surf.set_alpha(80)
            screen.blit(r_surf, (ab, 0))
            screen.blit(b_surf, (-ab, 0))

                                           
        if dilation_active and dilation_ratio < 0.25:
            pulse_a = int(abs(math.sin(self._distort_phase * 6)) * 60)
            warn = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            warn.fill((255, 50, 50, pulse_a))
            screen.blit(warn, (0, 0))

                            
        if rewinding:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((200, 220, 255, 40))
            screen.blit(flash, (0, 0))

    def draw_dilation_trail_overlay(self, screen):
        if not self._player_trail:
            return
                                                                           
        cx, cy = WIDTH // 2, HEIGHT // 2
        for i, p in enumerate(self._player_trail):
            a = max(0, p["alpha"] - i * 6)
            if a <= 0:
                continue
            bar_w = max(2, 40 - i * 2)
            bar_h = 3
            surf  = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
            surf.fill((120, 210, 255, a))
            screen.blit(surf, (cx - bar_w // 2 + random.randint(-4, 4),
                               cy + random.randint(-20, 20)))


                                                                               
                                                           
                                                                               
def draw_temporal_hud(screen, dilation: TimeDilation, rewind: TimeRewind,
                      echo: TemporalEcho, fracture: FractureZones,
                      ui_phase: float):
    font_s = pygame.font.SysFont("arial", 15, bold=True)
    font_t = pygame.font.SysFont("arial", 13)

    bar_w  = 140
    bar_h  = 12
    x0     = WIDTH - bar_w - 18
    y0     = HEIGHT - 200
    gap    = 22
    pulse  = 0.5 + 0.5 * math.sin(ui_phase * 2)

    abilities = [
        ("TIME DIL  [Q]", dilation.energy_ratio,
         (60, 200, 255), dilation.active),
        ("REWIND    [E]", rewind.cooldown_ratio,
         (200, 100, 255), rewind.rewinding),
        ("T-ECHO    [G]", echo.cooldown_ratio,
         (80, 255, 180), False),
    ]

    overlay = pygame.Surface((bar_w + 60, gap * len(abilities) + 36), pygame.SRCALPHA)
    overlay.fill((0, 10, 20, 160))
    pygame.draw.rect(overlay, (60, 140, 200, 100), overlay.get_rect(), 1, border_radius=6)
    screen.blit(overlay, (x0 - 8, y0 - 20))

    label_surf = font_t.render("TEMPORAL ABILITIES", True, (100, 180, 240))
    screen.blit(label_surf, (x0 - 4, y0 - 17))

    for i, (label, ratio, color, is_active) in enumerate(abilities):
        y = y0 + i * gap

                        
        pygame.draw.rect(screen, (20, 30, 40), (x0, y, bar_w, bar_h))
              
        fill_w = max(0, int(bar_w * ratio))
        pygame.draw.rect(screen, color, (x0, y, fill_w, bar_h))
                     
        if is_active:
            glow_a = int(80 + 80 * pulse)
            gsurf  = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
            gsurf.fill((*color, glow_a))
            screen.blit(gsurf, (x0, y))
                
        border_col = color if is_active else (60, 90, 110)
        pygame.draw.rect(screen, border_col, (x0, y, bar_w, bar_h), 1)

        label_surf = font_s.render(label, True,
                                   color if is_active else (160, 190, 210))
        screen.blit(label_surf, (x0 - label_surf.get_width() - 4, y - 1))

                         
    if fracture.active_effect and fracture.msg_timer > 0:
        ratio = fracture.msg_timer / 120
        a     = int(255 * min(1.0, ratio * 2))
        fc    = fracture.active_effect["tint"]
        fsurf = font_s.render(f"⚡ {fracture.active_effect['type'].upper()} ZONE",
                               True, fc)
        fsurf.set_alpha(a)
        screen.blit(fsurf, (x0, y0 + gap * len(abilities) + 6))
```

## fps_game/systems/torch.py
Filename: `fps_game/systems/torch.py`

```python
import pygame
import math

class Torch:
    def __init__(self, sprite, radius=220, intensity=180):
        self.sprite = sprite
        self.radius = radius
        self.intensity = intensity

    def draw_light(self, surface, player_x, player_y):
        # Create radial gradient for sci-fi glow
        glow = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
        for r in range(self.radius, 0, -4):
            alpha = int(self.intensity * (r / self.radius))
            pygame.draw.circle(glow, (80, 200, 255, alpha), (self.radius, self.radius), r)
        
        # Center glow on player
        surface.blit(glow, (player_x - self.radius, player_y - self.radius), special_flags=pygame.BLEND_ADD)

    def draw_sprite(self, surface, player_x, player_y):
        # Draw torch sprite at bottom-right HUD
        rect = self.sprite.get_rect()
        rect.bottomright = (surface.get_width()-40, surface.get_height()-40)
        surface.blit(self.sprite, rect)
```

## fps_game/systems/ui.py
Filename: `fps_game/systems/ui.py`

```python
import math
import pygame

from core.settings import WIDTH, HEIGHT


HUD_PRIMARY   = (120, 210, 255)
HUD_SECONDARY = (60,  140, 190)
HUD_ACCENT    = (90,  255, 210)


def draw_crosshair(screen, hit=False, pulse=0.0):
    cx, cy = WIDTH // 2, HEIGHT // 2
    size   = 10 + int(6 * pulse)
    alpha  = max(0, min(255, 200 + int(55 * pulse)))
    color  = (alpha, alpha, alpha)
    pygame.draw.line(screen, color, (cx - size, cy), (cx + size, cy), 2)
    pygame.draw.line(screen, color, (cx, cy - size), (cx, cy + size), 2)
    if hit:
        color    = (255, 60, 60)
        hit_size = 12 + int(6 * pulse)
        pygame.draw.line(screen, color, (cx - hit_size, cy - hit_size), (cx + hit_size, cy + hit_size), 2)
        pygame.draw.line(screen, color, (cx - hit_size, cy + hit_size), (cx + hit_size, cy - hit_size), 2)


def draw_level_hud(screen, font, level_index, player):
    level_text = f"SECTOR {level_index + 1}"
    surf = font.render(level_text, True, (180, 210, 240))
    screen.blit(surf, (12, 10))

    bar_w = 180
    bar_h = 18
    x, y  = 12, 38
    pygame.draw.rect(screen, (40, 40, 40), (x, y, bar_w, bar_h))
    ratio = max(0, player.health) / player.max_health
    bar_color = (200, 40, 40) if ratio < 0.3 else (60, 180, 80) if ratio > 0.6 else (200, 160, 40)
    pygame.draw.rect(screen, bar_color, (x, y, int(bar_w * ratio), bar_h))
    hp_text = font.render(f"VITALS {max(0, player.health)}%", True, (210, 220, 240))
    screen.blit(hp_text, (x + bar_w + 10, y - 2))


def draw_ammo(screen, font, player):
    weapon  = player.get_weapon()
    text    = f"AMMO  {weapon.ammo} / {weapon.max_ammo}"
    surf    = font.render(text, True, (200, 210, 140))
    screen.blit(surf, (WIDTH - 200, HEIGHT - 30))


def draw_score(screen, font, score, kills, pulse=0.0):
    base  = 255
    glow  = int(140 * pulse)
    color = (base, min(255, base + glow), min(255, base + glow))
    screen.blit(font.render(f"SCORE  {score}", True, color), (WIDTH - 200, 10))
    screen.blit(font.render(f"NEUTRALIZED  {kills}", True, color), (WIDTH - 200, 35))


def draw_overlay_messages(screen, messages, flicker=0.0):
    if not messages:
        return
    font = pygame.font.SysFont("courier", 17, bold=True)
    y    = 70
    for msg in messages:
        alpha = max(0, min(255, msg["timer"] * 18))
        color = (220, 80 + int(60 * flicker), 80 + int(60 * flicker))
        surf  = font.render(msg["text"], True, color)
        surf.set_alpha(alpha)
        rect  = surf.get_rect(center=(WIDTH // 2, y))
        screen.blit(surf, rect)
        y += 24


def draw_room_label(screen, room_name, strength=1.0, flicker=0.0):
    if not room_name:
        return
    font  = pygame.font.SysFont("courier", 22, bold=True)
    alpha = max(0, min(255, int(220 * strength)))
    glow  = int(40 + 40 * flicker)
    color = (min(255, 180 + glow), min(255, 210 + glow), 255)
    surf  = font.render(f"// {room_name.upper()} //", True, color)
    surf.set_alpha(alpha)
    rect  = surf.get_rect(center=(WIDTH // 2, 40))
    screen.blit(surf, rect)


def draw_weapon_info(screen, player):
    font   = pygame.font.SysFont("courier", 18)
    weapon = player.get_weapon()
    text   = f"{weapon.name.upper()}  |  {weapon.ammo} / {weapon.max_ammo}"
    surf   = font.render(text, True, (200, 210, 140))
    screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT - 40))


def draw_hit_flash(screen, amount=90):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((160, 0, 0, amount))
    screen.blit(overlay, (0, 0))


def draw_game_over(screen, font):
    t       = pygame.time.get_ticks() / 1000.0
    pulse   = (math.sin(t * 2.4) + 1) * 0.5

    panel   = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 160))
    screen.blit(panel, (0, 0))

    title_font = pygame.font.SysFont("courier", 44, bold=True)
    body_font  = pygame.font.SysFont("courier", 20)
    tiny_font  = pygame.font.SysFont("courier", 15)

    cy = HEIGHT // 2 - 60

    go_surf = title_font.render("OPERATIVE LOST", True, (220, 60, 60))
    screen.blit(go_surf, (WIDTH // 2 - go_surf.get_width() // 2, cy))

    cy += 56
    sub_surf = body_font.render("Suit telemetry flat. Temporal anchor severed.", True, (180, 190, 210))
    screen.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, cy))

    cy += 28
    sub2 = body_font.render("The Astraeus continues without you.", True, (140, 150, 170))
    screen.blit(sub2, (WIDTH // 2 - sub2.get_width() // 2, cy))

    cy += 48
    restart_a = int(180 + 75 * pulse)
    restart_surf = body_font.render("[ R ]  RE-INITIALIZE OPERATIVE", True, (160, 200, 240))
    restart_surf.set_alpha(restart_a)
    screen.blit(restart_surf, (WIDTH // 2 - restart_surf.get_width() // 2, cy))

    cy += 26
    note = tiny_font.render("All temporal data will be reset. The entity will remember.", True, (80, 100, 130))
    screen.blit(note, (WIDTH // 2 - note.get_width() // 2, cy))


def draw_pause(screen):
    t    = pygame.time.get_ticks() / 1000.0
    panel = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 140))
    screen.blit(panel, (0, 0))

    font     = pygame.font.SysFont("courier", 36, bold=True)
    sub_font = pygame.font.SysFont("courier", 16)

    pulse = (math.sin(t * 1.8) + 1) * 0.5
    a     = int(200 + 55 * pulse)

    pause_surf = font.render("// PAUSED //", True, (180, 210, 240))
    pause_surf.set_alpha(a)
    screen.blit(pause_surf, (WIDTH // 2 - pause_surf.get_width() // 2, HEIGHT // 2 - 30))

    note = sub_font.render("Time continues outside this vessel. Proceed when ready.", True, (90, 120, 160))
    screen.blit(note, (WIDTH // 2 - note.get_width() // 2, HEIGHT // 2 + 20))

    esc_surf = sub_font.render("[ ESC ]  RESUME", True, (100, 140, 180))
    screen.blit(esc_surf, (WIDTH // 2 - esc_surf.get_width() // 2, HEIGHT // 2 + 50))


def draw_scifi_hud(screen, phase=0.0, alert=False):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pulse   = 0.5 + 0.5 * math.sin(phase)
    glow    = int(40 + 40 * pulse)
    frame   = (*HUD_PRIMARY, 170 if not alert else 220)
    grid    = (*HUD_SECONDARY, 22)
    accent  = (*HUD_ACCENT, 160)

    for x in range(0, WIDTH, 90):
        pygame.draw.line(overlay, grid, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, 70):
        pygame.draw.line(overlay, grid, (0, y), (WIDTH, y), 1)

    margin = 12
    corner = 26
    for pts in [
        [(margin, margin), (margin + corner, margin), (margin, margin), (margin, margin + corner)],
        [(WIDTH - margin, margin), (WIDTH - margin - corner, margin), (WIDTH - margin, margin), (WIDTH - margin, margin + corner)],
        [(margin, HEIGHT - margin), (margin + corner, HEIGHT - margin), (margin, HEIGHT - margin), (margin, HEIGHT - margin - corner)],
        [(WIDTH - margin, HEIGHT - margin), (WIDTH - margin - corner, HEIGHT - margin), (WIDTH - margin, HEIGHT - margin), (WIDTH - margin, HEIGHT - margin - corner)],
    ]:
        pygame.draw.line(overlay, frame, pts[0], pts[1], 2)
        pygame.draw.line(overlay, frame, pts[2], pts[3], 2)

    panel_h = 70
    panel_y = HEIGHT - panel_h - 10
    panel   = pygame.Rect(18, panel_y, WIDTH - 36, panel_h)
    pygame.draw.rect(overlay, (*HUD_SECONDARY, 40), panel, border_radius=10)
    pygame.draw.rect(overlay, frame, panel, 2, border_radius=10)
    pygame.draw.line(overlay, accent, (panel.left + 12, panel_y + 18), (panel.left + 220, panel_y + 18), 2)
    pygame.draw.line(overlay, (*HUD_PRIMARY, 120), (panel.right - 240, panel_y + 18), (panel.right - 14, panel_y + 18), 1)
    for i in range(6):
        x = panel.left + 12 + i * 26
        pygame.draw.line(overlay, (*HUD_PRIMARY, 120), (x, panel_y + 30), (x + 12, panel_y + 30), 2)

    bar_h   = 140
    left_bar  = pygame.Rect(16, HEIGHT - bar_h - 110, 18, bar_h)
    right_bar = pygame.Rect(WIDTH - 34, HEIGHT - bar_h - 110, 18, bar_h)
    for bar in (left_bar, right_bar):
        pygame.draw.rect(overlay, (*HUD_SECONDARY, 30), bar)
        pygame.draw.rect(overlay, frame, bar, 2)
    fill_h = int(bar_h * (0.35 + 0.6 * pulse))
    pygame.draw.rect(overlay, accent, pygame.Rect(left_bar.x + 3,  left_bar.bottom  - fill_h - 3, left_bar.w  - 6, fill_h))
    pygame.draw.rect(overlay, accent, pygame.Rect(right_bar.x + 3, right_bar.bottom - fill_h - 3, right_bar.w - 6, fill_h))

    top_y = 16
    for i in range(0, WIDTH, 60):
        tick_h = 6 + int(6 * (i / 60 % 2))
        pygame.draw.line(overlay, (*HUD_PRIMARY, 140), (i + 10, top_y), (i + 10, top_y + tick_h), 1)
    pygame.draw.line(overlay, (*HUD_ACCENT, 190), (WIDTH // 2 - 50, top_y + 18), (WIDTH // 2 + 50, top_y + 18), 2)

    scan_y = int((phase * 40) % HEIGHT)
    scan_color = (130, 220, 255, 45 if not alert else 75)
    pygame.draw.line(overlay, scan_color, (0, scan_y), (WIDTH, scan_y), 2)
    pygame.draw.line(overlay, scan_color, (0, (scan_y + 2) % HEIGHT), (WIDTH, (scan_y + 2) % HEIGHT), 1)

    for i in range(40):
        x = (i * 73 + int(phase * 120)) % WIDTH
        y = (i * 37 + int(phase * 80))  % HEIGHT
        overlay.set_at((x, y), (HUD_PRIMARY[0], HUD_PRIMARY[1], HUD_PRIMARY[2], 60))

    halo_radius = 28 + int(6 * pulse)
    pygame.draw.circle(overlay, (*HUD_PRIMARY, 60),  (WIDTH // 2, HEIGHT // 2), halo_radius,      1)
    pygame.draw.circle(overlay, (*HUD_ACCENT,  80),  (WIDTH // 2, HEIGHT // 2), halo_radius + 10, 1)

    if alert:
        alert_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        alert_surface.fill((255, 40, 40, 18 + glow))
        overlay.blit(alert_surface, (0, 0))

    screen.blit(overlay, (0, 0))
```

## fps_game/utils/__init__.py
Filename: `fps_game/utils/__init__.py`

```python

```

## fps_game/utils/math_utils.py
Filename: `fps_game/utils/math_utils.py`

```python
def is_wall(x, y, world, tile_size, doors=None):
    tile_x = int(x // tile_size) * tile_size
    tile_y = int(y // tile_size) * tile_size
    if (tile_x, tile_y) in world:
        return True
    if doors:
        door = doors.get((tile_x, tile_y))
        if door and not door.get("open"):
            return True
    return False
```


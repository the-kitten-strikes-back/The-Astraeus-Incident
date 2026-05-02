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
    draw_sniper_scope,
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
    TORCH_IMG,
)
from systems.torch import Torch
from systems.labyrinth import AdaptivePuzzleEngine

class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass

        pygame.event.set_allowed(None)
        pygame.event.set_allowed([
            pygame.QUIT, pygame.KEYDOWN, pygame.KEYUP,
            pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
        ])

        self.time_scale   = 1.0
        self.time_frozen  = False
        self.screen       = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock        = pygame.time.Clock()
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)

        self.hud_font = pygame.font.SysFont("arial", 22)

        self.current_music_level = -1
        self.music_enabled = True
        self.torch_enabled = False
        self.torch = Torch(radius=420)
        self.torch.load_sprite(TORCH_IMG)
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

        self.level_paths = sorted(
            glob.glob(f"{LEVELS_DIR}/level*.txt"),
            key=lambda path: int(
                "".join(ch for ch in os.path.basename(path) if ch.isdigit()) or 0
            ),
        )
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
        self.enemy_bullets = []
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
        self.sniper_scoped   = False
        self.scope_zoom      = 1.8
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
        self.labyrinth_engine = AdaptivePuzzleEngine()
        self.labyrinth_puzzle = None
        self.labyrinth_target_door = None
        self.labyrinth_input = ""
        self.labyrinth_feedback = ""
        self.labyrinth_feedback_timer = 0

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
        self.enemy_bullets = []
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
        self.labyrinth_engine.load_snapshot(data.get("labyrinth"))

    def save_game(self):
        data = {
            "level":       self.current_level_index,
            "score":       self.score,
            "kills":       self.kills,
            "health":      self.player.health,
            "sensitivity": self.settings.get("sensitivity", 0.003),
            "fullscreen":  self.settings.get("fullscreen", True),
            "ammo":        [w.ammo for w in self.player.weapons],
            "labyrinth":   self.labyrinth_engine.snapshot(),
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
            if self.doors[closest]["open"]:
                self.doors[closest]["open"] = False
            else:
                self._start_labyrinth_for_door(closest)

    def _start_labyrinth_for_door(self, door_pos):
        self.labyrinth_target_door = door_pos
        self.labyrinth_puzzle = self.labyrinth_engine.generate_puzzle()
        self.labyrinth_input = ""
        self.labyrinth_feedback = "LABYRINTH PROTOCOL ENGAGED"
        self.labyrinth_feedback_timer = 40
        self.state = "labyrinth"

    def _cancel_labyrinth(self):
        self.labyrinth_target_door = None
        self.labyrinth_puzzle = None
        self.labyrinth_input = ""
        self.labyrinth_feedback = ""
        self.labyrinth_feedback_timer = 0
        self.state = "playing"

    def _submit_labyrinth_answer(self):
        if not self.labyrinth_puzzle:
            self._cancel_labyrinth()
            return

        solved, feedback = self.labyrinth_engine.submit_answer(
            self.labyrinth_puzzle, self.labyrinth_input
        )
        self.labyrinth_feedback = feedback
        self.labyrinth_feedback_timer = 80

        if solved:
            if self.labyrinth_target_door in self.doors:
                self.doors[self.labyrinth_target_door]["open"] = True
            self.glitch_messages.append(
                {"text": "LABYRINTH: DOOR UNLOCKED", "timer": 36}
            )
            self.save_game()
            self._cancel_labyrinth()
            return

        if self.labyrinth_puzzle["attempts"] >= self.labyrinth_puzzle["max_attempts"]:
            self.glitch_messages.append(
                {"text": "LABYRINTH: ADAPTIVE RETRAINING", "timer": 36}
            )
            self.labyrinth_puzzle = self.labyrinth_engine.generate_puzzle()
            self.labyrinth_input = ""
        else:
            self.labyrinth_input = ""

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
        self.enemy_bullets = []
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

    def _process_player_shot(self):
        score_delta, kills_delta, hit_any, fired = self.weapon_system.try_shoot(
            time.time(), self.player, self.enemies, self.depth_buffer
        )
        self.score += score_delta
        self.kills += kills_delta
        if score_delta or kills_delta:
            self.score_pulse = 10
        if hit_any:
            self.hit_marker = 6
            self.chromatic_timer = max(self.chromatic_timer, 4)
        if fired:
            try:
                if os.path.exists(EFFECT_FILES["laser"]):
                    pygame.mixer.Sound(EFFECT_FILES["laser"]).play()
            except (KeyError, pygame.error):
                pass
            self.screen_zoom = max(self.screen_zoom, 0.03)
            self.chromatic_timer = max(self.chromatic_timer, 4)
            self.cinematic_pulse = max(self.cinematic_pulse, 0.5)

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
                        self.sniper_scoped = False
                    if event.key == pygame.K_2:
                        self.player.current_weapon_index = 1
                        self.sniper_scoped = False
                    if event.key == pygame.K_3:
                        self.player.current_weapon_index = 2
                    if event.key == pygame.K_4:
                        self.player.current_weapon_index = 3
                        self.sniper_scoped = False
                    if event.key == pygame.K_9:
                        if not hasattr(self, "_torch_toggle_lock"):
                            self._torch_toggle_lock = False

                        if not self._torch_toggle_lock:
                            self.torch_enabled = not self.torch_enabled
                            self._torch_toggle_lock = True
                    else:
                        self._torch_toggle_lock = False
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

                elif self.state == "labyrinth":
                    if event.key == pygame.K_ESCAPE:
                        self._cancel_labyrinth()
                    elif event.key == pygame.K_BACKSPACE:
                        self.labyrinth_input = self.labyrinth_input[:-1]
                    elif event.key == pygame.K_RETURN:
                        self._submit_labyrinth_answer()
                    elif event.unicode and event.unicode.isalnum():
                        if len(self.labyrinth_input) < 14:
                            self.labyrinth_input += event.unicode.upper()

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
                    if self.player.get_weapon().name != "Machine Gun":
                        self._process_player_shot()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if self.state == "playing" and not self.game_over:
                    if self.player.get_weapon().name == "Sniper":
                        self.sniper_scoped = True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                self.sniper_scoped = False

        return True

    def _sniper_scope_active(self):
        return (
            self.sniper_scoped
            and self.state in {"playing", "loop"}
            and not self.game_over
            and self.player.get_weapon().name == "Sniper"
        )

    def _apply_sniper_scope(self):
        zoom = max(1.0, self.scope_zoom)
        if zoom <= 1.01:
            return
        base = self.screen.copy()
        target_w = max(1, int(WIDTH * zoom))
        target_h = max(1, int(HEIGHT * zoom))
        zoomed = pygame.transform.smoothscale(base, (target_w, target_h))
        sx = (WIDTH - target_w) // 2
        sy = (HEIGHT - target_h) // 2
        self.screen.fill((0, 0, 0))
        self.screen.blit(zoomed, (sx, sy))

    def update(self):
        if self.state == "labyrinth":
            if self.labyrinth_feedback_timer > 0:
                self.labyrinth_feedback_timer -= 1
            if self.labyrinth_engine.check_timeout(self.labyrinth_puzzle):
                self.labyrinth_feedback = "TIMEOUT // ADAPTIVE SCORE REDUCED"
                self.labyrinth_feedback_timer = 80
                self.labyrinth_puzzle = self.labyrinth_engine.generate_puzzle()
                self.labyrinth_input = ""
            return

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
        self.temporal_echo.update(self.enemies, self.world)
        self.temporal_visuals.update(
            self.time_dilation.active,
            self.time_dilation.energy_ratio,
        )

        if not self.game_over:
            keys = pygame.key.get_pressed()
            mouse_buttons = pygame.mouse.get_pressed(3)
            mx   = self.mouse_dx
            self.mouse_dx      = 0
            self.last_mouse_dx = mx

            if mouse_buttons[0] and self.player.get_weapon().name == "Machine Gun":
                self._process_player_shot()

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
            if self._sniper_scope_active():
                self.player.mouse_sensitivity *= 0.45

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

            new_bullets = update_enemies(
                self.enemies, self.player, self.world, self.doors,
                self.on_player_hit, effective_time,
            )
            self.enemy_bullets.extend(new_bullets)
            self._update_enemy_bullets(effective_time)
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
                            if enemy.get("boss", False):
                                # Intentionally massive boss presentation (10-20x).
                                boss_scale = 14.0
                                sprite_size = max(1, int(sprite_size * boss_scale))
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
    def _update_enemy_bullets(self, time_scale):
        player = self.player
        for bullet in self.enemy_bullets[:]:
            bullet["x"] += math.cos(bullet["angle"]) * bullet["speed"] * time_scale
            bullet["y"] += math.sin(bullet["angle"]) * bullet["speed"] * time_scale
            bullet["life"] -= 1

            # Wall collision
            tx = int(bullet["x"] // TILE) * TILE
            ty = int(bullet["y"] // TILE) * TILE
            if (tx, ty) in self.world:
                self.enemy_bullets.remove(bullet)
                continue
            # Ghost hit — enemy bullets can kill the echo
            if self.temporal_echo.apply_damage_to_ghosts(
                bullet["x"], bullet["y"], bullet["damage"]
            ):
                self.enemy_bullets.remove(bullet)
                continue
            # Player hit
            dx   = bullet["x"] - player.x
            dy   = bullet["y"] - player.y
            if math.hypot(dx, dy) < 22:
                if player.apply_damage(bullet["damage"]):
                    self.hit_flash       = 12
                    self.shake           = 8
                    self.chromatic_timer = 10
                    self.vignette_timer  = 18
                    self.cinematic_pulse = 0.9
                    if player.health <= 0:
                        self.game_over = True
                        self.save_game()
                self.enemy_bullets.remove(bullet)
                continue

            if bullet["life"] <= 0:
                self.enemy_bullets.remove(bullet)

    def _draw_enemy_bullets(self, scene):
        from core.settings import HALF_FOV, FOV, NUM_RAYS, HALF_HEIGHT
        for bullet in self.enemy_bullets:
            dx   = bullet["x"] - self.player.x
            dy   = bullet["y"] - self.player.y
            dist = math.hypot(dx, dy)
            if dist < 1:
                continue

            theta = math.atan2(dy, dx)
            delta = (theta - self.player.angle + math.pi) % (2 * math.pi) - math.pi
            if not (-HALF_FOV < delta < HALF_FOV):
                continue

            screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
            size     = min(1800 / (dist + 0.001), 22)
            sx       = int(screen_x - size / 2)
            sy       = int(HALF_HEIGHT - size / 2)

            ray_idx = max(0, min(NUM_RAYS - 1, int(screen_x * NUM_RAYS / WIDTH)))
            if ray_idx < len(self.depth_buffer) and dist < self.depth_buffer[ray_idx]:
                surf = pygame.Surface((int(size), int(size)), pygame.SRCALPHA)
                pygame.draw.circle(
                    surf, (255, 80, 40, 220),
                    (int(size) // 2, int(size) // 2),
                    max(1, int(size) // 2),
                )
                scene.blit(surf, (sx, sy))
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

        elif self.state == "labyrinth":
            self.screen.fill((5, 8, 14))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((14, 28, 44, 220))
            self.screen.blit(overlay, (0, 0))

            panel = pygame.Rect(120, 90, WIDTH - 240, HEIGHT - 180)
            pygame.draw.rect(self.screen, (24, 42, 68), panel, border_radius=12)
            pygame.draw.rect(self.screen, (90, 180, 230), panel, 2, border_radius=12)

            title_font = pygame.font.SysFont("arial", 34, bold=True)
            body_font = pygame.font.SysFont("consolas", 24)
            sub_font = pygame.font.SysFont("consolas", 19)

            title = title_font.render("PROJECT LABYRINTH", True, (160, 245, 255))
            self.screen.blit(title, (panel.x + 24, panel.y + 20))

            if self.labyrinth_puzzle:
                skill_line = (
                    f"Skill {self.labyrinth_engine.skill_rating:.2f}  "
                    f"Diff {self.labyrinth_puzzle['difficulty']}  "
                    f"Run {self.labyrinth_engine.run_id}"
                )
                prompt_line = self.labyrinth_puzzle["prompt"]
                attempts = (
                    f"Attempts {self.labyrinth_puzzle['attempts']}/{self.labyrinth_puzzle['max_attempts']}"
                )
                remaining = max(
                    0.0,
                    self.labyrinth_puzzle["time_limit"] - (
                        time.time() - self.labyrinth_puzzle.get("started_at", time.time())
                    ),
                )
                timer_line = f"Time Remaining: {remaining:04.1f}s"

                self.screen.blit(sub_font.render(skill_line, True, (150, 200, 220)), (panel.x + 24, panel.y + 78))
                self.screen.blit(body_font.render(prompt_line, True, (220, 240, 255)), (panel.x + 24, panel.y + 132))
                self.screen.blit(sub_font.render(attempts, True, (200, 220, 255)), (panel.x + 24, panel.y + 178))
                self.screen.blit(sub_font.render(timer_line, True, (255, 190, 140)), (panel.x + 24, panel.y + 206))

            input_box = pygame.Rect(panel.x + 24, panel.y + 246, panel.width - 48, 52)
            pygame.draw.rect(self.screen, (10, 18, 30), input_box, border_radius=8)
            pygame.draw.rect(self.screen, (100, 190, 240), input_box, 2, border_radius=8)
            typed = body_font.render(self.labyrinth_input or "_", True, (180, 255, 190))
            self.screen.blit(typed, (input_box.x + 14, input_box.y + 12))

            feedback_color = (255, 150, 140) if "DENIED" in self.labyrinth_feedback or "INCORRECT" in self.labyrinth_feedback else (150, 240, 210)
            if self.labyrinth_feedback and self.labyrinth_feedback_timer > 0:
                feedback = sub_font.render(self.labyrinth_feedback, True, feedback_color)
                self.screen.blit(feedback, (panel.x + 24, panel.y + 320))

            controls = sub_font.render("ENTER submit  |  BACKSPACE edit  |  ESC abort", True, (140, 190, 220))
            self.screen.blit(controls, (panel.x + 24, panel.y + panel.height - 48))

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
            self._draw_enemy_bullets(scene)
            draw_health_packs(scene, self.health_packs, self.player, self.depth_buffer, self.anim_time)
            self.grenade_system.draw_grenades(scene, self.player, self.depth_buffer, self.anim_time)
            self.temporal_echo.draw(scene, self.player, self.depth_buffer)
            self.weapon_system.draw_bullets(scene)
            scope_active = self._sniper_scope_active()
            if self.torch_enabled and not scope_active:
                self.torch.draw_sprite(
                    scene,
                    bob_y=self.bob_offset, sway_x=self.bob_side, sway_y=self.bob_offset * 0.3,
                )
            elif not scope_active:
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

            if self.torch_enabled:
                self.torch.draw_light(self.screen, self.anim_time)

            if scope_active:
                self._apply_sniper_scope()
                draw_sniper_scope(self.screen)
            else:
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
                    self.doors,
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

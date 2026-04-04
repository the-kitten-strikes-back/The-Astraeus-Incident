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
)
from systems.minimap import draw_minimap
from systems.cutscene import draw_cutscene
from systems.grenades import GrenadeSystem
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


class Game:
    def __init__(self):
        pygame.init()
        self.time_scale = 1.0
        self.time_frozen = False
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)

        self.hud_font = pygame.font.SysFont("arial", 22)

        self.weapon_image = pygame.image.load(WEAPON_DEFAULT_IMG).convert_alpha()
        self.enemy_sprite = pygame.image.load(ENEMY_IMG).convert_alpha()
        self.enemy_sprites = self._load_enemy_sprites()
        self.wall_textures = self._load_wall_textures()
        self.door_texture = self._load_door_texture()
        self.floor_textures = self._load_tile_textures(FLOOR_TEXTURE_FILES, kind="floor")
        self.ceiling_textures = self._load_tile_textures(CEILING_TEXTURE_FILES, kind="ceiling")
        self.floor_texture = self.floor_textures[0]
        self.ceiling_texture = self.ceiling_textures[0]

        self.weapon_system = WeaponSystem(self.weapon_image)
        self.grenade_system = GrenadeSystem()

        self.level_paths = sorted(glob.glob(f"{LEVELS_DIR}/level*.txt"))
        if not self.level_paths:
            raise FileNotFoundError("No level files found in levels/ directory.")
        self.current_level_index = 0
        self.level_complete_time = None
        self.level_advance_delay = 0.6

        self.world = {}
        self.enemies = []
        self.health_packs = []
        self.rooms = {}
        self.doors = {}
        self.depth_buffer = []

        self.player = Player(150, 150)

        self.score = 0
        self.kills = 0
        self.shake = 0
        self.hit_flash = 0
        self.hit_marker = 0
        self.score_pulse = 0
        self.game_over = False
        self.restart_cooldown = 0
        self.mouse_dx = 0
        self.last_mouse_dx = 0
        self.anim_time = 0.0
        self.bob_phase = 0.0
        self.bob_offset = 0.0
        self.bob_side = 0.0
        self.screen_zoom = 0.0
        self.chromatic_timer = 0
        self.ui_phase = 0.0
        self.roll_angle = 0.0
        self.vignette_timer = 0
        self.cinematic_pulse = 0.0
        self.anomaly_timer = 0
        self.anomaly_scale = 1.0
        self.glitch_messages = []
        self.cutscene_index = 0
        self.cutscene_time = 0.0
        self.cutscene_return_state = "playing"
        self.ending_choice = ""
        self.current_room = ""
        self.current_room_key = ""
        self.room_timer = 0
        self.room_tint = (0, 0, 0)
        self.room_tint_alpha = 0
        self.room_scan = False
        self.story_beats = [
            {
                "level": 0,
                "title": "ASTRAEUS // DOCKING SEQUENCE",
                "lines": [
                    "Operative online. Suit telemetry stable.",
                    "Objective: reach the reactor core.",
                ],
            },
            {
                "level": 2,
                "title": "ACT I — THE SILENT SHIP",
                "lines": [
                    "Doors open before you touch them.",
                    "Your footsteps echo ahead of you.",
                ],
            },
            {
                "level": 4,
                "title": "TEMPORAL SHEAR DETECTED",
                "lines": [
                    "Gravitational dilation rising.",
                    "Reality coherence dropping.",
                ],
            },
            {
                "level": 6,
                "title": "RECOVERED CREW LOG",
                "lines": [
                    "We saw ourselves in the corridors.",
                    "The ship is split across timelines.",
                ],
            },
            {
                "level": 8,
                "title": "ACT II — FRACTURED TIME",
                "lines": [
                    "Corridors loop. Rooms overlap.",
                    "Past and future are layered together.",
                ],
            },
            {
                "level": 11,
                "title": "ASTRAEUS // SYSTEM ANOMALY",
                "lines": [
                    "Core resonance is mutating.",
                    "An intelligence is forming in the gaps.",
                ],
            },
            {
                "level": 13,
                "title": "ACT III — THE WATCHER",
                "lines": [
                    "It anticipates you.",
                    "It alters enemy behavior.",
                ],
            },
            {
                "level": 15,
                "title": "ACT IV — THE TRUTH",
                "lines": [
                    "Time is no longer linear.",
                    "You are the only fixed thread.",
                ],
            },
            {
                "level": 17,
                "title": "ACT V — CORE DESCENT",
                "lines": [
                    "Reality collapses into possibility.",
                    "You are no longer navigating space.",
                ],
            },
        ]
        self.log_beats = {
            2: "LOG: Crew vanished after first dilation test.",
            5: "LOG: Drones repeating tasks between seconds.",
            9: "LOG: The ship is watching you.",
            13: "LOG: Time fracture widening near core.",
            16: "LOG: Past and future overlapping.",
            19: "LOG: Decision point imminent.",
        }
        self.cutscene_map = self._build_cutscene_map()

        self.state = "menu"  # menu, settings, playing, pause
        self.settings = {
            "sensitivity": 0.003
        }
        self.save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "save.json")
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
                base = 60 + (ord(key) * 7) % 120
                img.fill((base, base, base))
                for i in range(0, 64, 8):
                    pygame.draw.line(img, (base + 20, base + 20, base + 30), (i, 0), (i, 64))
            textures[key] = pygame.transform.scale(img, (64, 64))
        return textures

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
        font = pygame.font.SysFont("arial", 14, bold=True)
        rooms = [
            {"name": "Dock", "x": 20, "y": 20, "w": 90, "h": 50, "color": (60, 120, 180)},
            {"name": "Bridge", "x": 140, "y": 20, "w": 120, "h": 50, "color": (90, 150, 220)},
            {"name": "Crew", "x": 20, "y": 90, "w": 120, "h": 60, "color": (140, 120, 70)},
            {"name": "Medbay", "x": 160, "y": 90, "w": 100, "h": 60, "color": (80, 170, 220)},
            {"name": "Lab", "x": 280, "y": 80, "w": 140, "h": 70, "color": (90, 200, 130)},
            {"name": "Cargo", "x": 20, "y": 170, "w": 140, "h": 60, "color": (140, 100, 60)},
            {"name": "Hangar", "x": 190, "y": 170, "w": 140, "h": 60, "color": (120, 120, 180)},
            {"name": "Core", "x": 360, "y": 170, "w": 120, "h": 60, "color": (200, 80, 60)},
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
                base = 40 + (idx * 30) % 120
                if kind == "ceiling":
                    img.fill((base, base + 10, base + 20))
                    for y in range(0, 64, 8):
                        pygame.draw.line(img, (base + 20, base + 30, base + 40), (0, y), (64, y), 1)
                else:
                    img.fill((base + 10, base + 10, base))
                    for x in range(0, 64, 8):
                        pygame.draw.line(img, (base + 30, base + 20, base + 10), (x, 0), (x, 64), 1)
                    for y in range(0, 64, 16):
                        pygame.draw.line(img, (base + 40, base + 30, base + 20), (0, y), (64, y), 1)
            textures.append(pygame.transform.scale(img, (64, 64)))
        return textures

    def load_current_level(self):
        self.world, self.enemies, self.health_packs, spawn, self.rooms, self.doors = load_level(
            self.level_paths[self.current_level_index]
        )
        self.player.x, self.player.y = spawn
        if self.floor_textures:
            self.floor_texture = self.floor_textures[self.current_level_index % len(self.floor_textures)]
        if self.ceiling_textures:
            self.ceiling_texture = self.ceiling_textures[self.current_level_index % len(self.ceiling_textures)]
        self.current_room = ""
        self.current_room_key = ""
        self.room_tint = (0, 0, 0)
        self.room_tint_alpha = 0
        self.room_scan = False

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
        self.score = int(data.get("score", 0))
        self.kills = int(data.get("kills", 0))
        self.player.health = int(data.get("health", self.player.max_health))
        self.player.health = max(0, min(self.player.health, self.player.max_health))
        sensitivity = data.get("sensitivity")
        if isinstance(sensitivity, (int, float)):
            self.settings["sensitivity"] = float(sensitivity)
        ammo = data.get("ammo")
        if isinstance(ammo, list):
            for weapon, value in zip(self.player.weapons, ammo):
                try:
                    weapon.ammo = max(0, min(int(value), weapon.max_ammo))
                except (TypeError, ValueError):
                    continue

    def save_game(self):
        data = {
            "level": self.current_level_index,
            "score": self.score,
            "kills": self.kills,
            "health": self.player.health,
            "sensitivity": self.settings.get("sensitivity", 0.003),
            "ammo": [w.ammo for w in self.player.weapons],
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
        closest = None
        closest_dist = 9999
        for (x, y), door in self.doors.items():
            dx = (x + TILE // 2) - self.player.x
            dy = (y + TILE // 2) - self.player.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < 90 and dist < closest_dist:
                closest = (x, y)
                closest_dist = dist
        if closest:
            self.doors[closest]["open"] = not self.doors[closest]["open"]

    def advance_level(self):
        if self.current_level_index + 1 < len(self.level_paths):
            self.current_level_index += 1
            self.load_current_level()
            self.level_complete_time = None
            self.save_game()
            if self.current_level_index in self.log_beats:
                self.glitch_messages.append({"text": self.log_beats[self.current_level_index], "timer": 50})
            for i, beat in enumerate(self.story_beats):
                if beat["level"] == self.current_level_index:
                    self.cutscene_index = i
                    self.cutscene_time = 0.0
                    self.cutscene_return_state = "playing"
                    self.state = "cutscene"
                    break
        else:
            self.state = "ending_choice"

    def reset_game(self):
        self.current_level_index = 0
        self.load_current_level()
        self.level_complete_time = None
        self.player.health = self.player.max_health
        self.player.invincibility_frames = 0
        self.hit_flash = 0
        self.game_over = False
        self.restart_cooldown = 15
        self.shake = 0
        self.score = 0
        self.kills = 0
        self.ending_choice = ""
        for weapon in self.player.weapons:
            weapon.ammo = weapon.max_ammo
        self.weapon_system.reloading = False
        self.weapon_system.reload_timer = 0
        self.save_game()

    def on_player_hit(self, enemy):
        damage = enemy.get("damage", 10)
        if self.player.apply_damage(damage):
            self.hit_flash = 12
            self.shake = 10
            self.screen_zoom = 0.06
            self.chromatic_timer = 12
            self.vignette_timer = 20
            self.cinematic_pulse = 1.0
            enemy["attack_frame"] = 5
            if self.player.health <= 0:
                self.game_over = True
                self.save_game()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if self.state == "menu":
                    if event.key == pygame.K_RETURN:
                        self.cutscene_index = 0
                        self.cutscene_time = 0.0
                        self.cutscene_return_state = "playing"
                        self.state = "cutscene"
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
                    if event.key == pygame.K_ESCAPE:
                        self.state = "pause"
                    if event.key == pygame.K_f:
                        self.time_frozen = not self.time_frozen
                        self.time_scale = 0.1 if self.time_frozen else 1.0
                    if event.key == pygame.K_e:
                        self._toggle_nearby_door()
                    if event.key == pygame.K_z:
                        self.grenade_system.try_throw("space", self.player)
                    if event.key == pygame.K_x:
                        self.grenade_system.try_throw("smoke", self.player)
                    if event.key == pygame.K_c:
                        self.grenade_system.try_throw("stun", self.player)
                    if event.key == pygame.K_v:
                        self.grenade_system.try_throw("nuclear", self.player)
                elif self.state == "pause":
                    if event.key == pygame.K_ESCAPE:
                        self.state = "playing"
                elif self.state == "cutscene":
                    if event.key == pygame.K_RETURN:
                        self.state = self.cutscene_return_state
                elif self.state == "ending_choice":
                    if event.key == pygame.K_1:
                        self.ending_choice = "containment"
                        self.cutscene_time = 0.0
                        self.cutscene_return_state = "menu"
                        self.state = "cutscene"
                    if event.key == pygame.K_2:
                        self.ending_choice = "ascension"
                        self.cutscene_time = 0.0
                        self.cutscene_return_state = "loop"
                        self.state = "cutscene"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.state == "cutscene":
                self.state = self.cutscene_return_state

            if event.type == pygame.MOUSEMOTION:
                if self.state == "playing" and not self.game_over:
                    self.mouse_dx += event.rel[0]

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "playing" and not self.game_over:
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
                        self.screen_zoom = max(self.screen_zoom, 0.03)
                        self.chromatic_timer = max(self.chromatic_timer, 4)
                        self.cinematic_pulse = max(self.cinematic_pulse, 0.5)

        return True

    def update(self):
        if self.state not in {"playing", "loop"}:
            if self.state == "cutscene":
                self.cutscene_time += 0.06
            return

        effective_time = self.time_scale
        if not self.game_over:
            mx = self.mouse_dx
            self.mouse_dx = 0
            self.last_mouse_dx = mx
            self.player.mouse_sensitivity = self.settings["sensitivity"]
            self.player.move(self.world, mx, self.doors)
            room_key = self.rooms.get((int(self.player.x // TILE) * TILE, int(self.player.y // TILE) * TILE))
            if room_key and ROOM_NAME_MAP.get(room_key) != self.current_room:
                self.current_room_key = room_key
                self.current_room = ROOM_NAME_MAP.get(room_key, "")
                self.room_timer = 90
                ambience = ROOM_AMBIENCE_MAP.get(room_key)
                if ambience:
                    self.room_tint = ambience["tint"]
                    self.room_tint_alpha = ambience["alpha"]
                    self.room_scan = ambience["scan"]
                    if self.floor_textures:
                        self.floor_texture = self.floor_textures[ambience["floor"] % len(self.floor_textures)]
                    if self.ceiling_textures:
                        self.ceiling_texture = self.ceiling_textures[ambience["ceiling"] % len(self.ceiling_textures)]
            elif not room_key and self.current_room_key:
                self.current_room_key = ""
                self.current_room = ""
                self.room_tint = (0, 0, 0)
                self.room_tint_alpha = 0
                self.room_scan = False
                if self.floor_textures:
                    self.floor_texture = self.floor_textures[self.current_level_index % len(self.floor_textures)]
                if self.ceiling_textures:
                    self.ceiling_texture = self.ceiling_textures[self.current_level_index % len(self.ceiling_textures)]

            keys = pygame.key.get_pressed()
            focus_scale = 0.6 if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else 1.0
            if self.time_frozen:
                focus_scale = 0.1
            if self.anomaly_timer > 0:
                self.anomaly_timer -= 1
            else:
                if random.random() < 0.012:
                    self.anomaly_timer = random.randint(25, 80)
                    self.anomaly_scale = random.uniform(0.4, 1.6)
                    msg = random.choice([
                        "ASTRAEUS // TEMPORAL DRIFT",
                        "GRAVITATIONAL SHEAR DETECTED",
                        "ECHO EVENT // TIME LOOP",
                        "CORE RESONANCE SPIKE",
                    ])
                    self.glitch_messages.append({"text": msg, "timer": 28})

            effective_time = self.time_scale * focus_scale * self.anomaly_scale
            self.weapon_system.update_reload(self.player)
            update_enemies(self.enemies, self.player, self.world, self.doors, self.on_player_hit, effective_time)
            events = self.grenade_system.update(self.world, self.doors, self.enemies, effective_time)
            if events["shake"] > 0:
                self.shake = max(self.shake, events["shake"])
            if events["flash"] > 0:
                self.hit_flash = max(self.hit_flash, events["flash"])
            if events["chroma"] > 0:
                self.chromatic_timer = max(self.chromatic_timer, events["chroma"])
            if events["zoom"] > 0:
                self.screen_zoom = max(self.screen_zoom, events["zoom"])
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
                    self.glitch_messages.append({"text": "LOOP STABLE // ENEMIES RESPAWN", "timer": 30})
                    from enemies.enemy import create_enemy
                    for _ in range(3):
                        self.enemies.append(create_enemy(random.choice(["normal", "fast", "tank", "ranged"]), self.player.x + random.randint(-120, 120), self.player.y + random.randint(-120, 120)))
                if self.player.health <= 0:
                    self.player.health = self.player.max_health
                    self.game_over = False

        self.weapon_system.update_recoil()
        self.weapon_system.update_sway(-self.last_mouse_dx * 0.4, -self.last_mouse_dx * 0.15)
        self.player.update_invincibility()
        self.weapon_system.update_bullets(self.world, self.enemies, effective_time)
        self.anim_time += 0.12 * self.time_scale
        move_amount = self.player.move_amount
        if move_amount > 0.01:
            self.bob_phase += 0.32 * move_amount
        else:
            self.bob_phase += 0.04
        self.bob_offset = math.sin(self.bob_phase) * 6 * move_amount
        self.bob_side = math.sin(self.bob_phase * 0.5) * 3 * move_amount
        if self.hit_flash > 0:
            self.hit_flash -= 1
        if self.hit_marker > 0:
            self.hit_marker -= 1
        if self.score_pulse > 0:
            self.score_pulse -= 1
        if self.room_timer > 0:
            self.room_timer -= 1
        if self.restart_cooldown > 0:
            self.restart_cooldown -= 1
        if self.shake > 0:
            self.shake -= 1
        self.screen_zoom *= 0.85
        if abs(self.screen_zoom) < 0.002:
            self.screen_zoom = 0.0
        if self.chromatic_timer > 0:
            self.chromatic_timer -= 1
        if self.vignette_timer > 0:
            self.vignette_timer -= 1
        self.ui_phase += 0.04
        self.roll_angle += (-self.last_mouse_dx * 0.04 - self.roll_angle) * 0.18
        self.cinematic_pulse *= 0.85
        for msg in self.glitch_messages[:]:
            msg["timer"] -= 1
            if msg["timer"] <= 0:
                self.glitch_messages.remove(msg)

    def draw_enemies(self, surface):
        for enemy in self.enemies:
            dx = enemy["x"] - self.player.x
            dy = enemy["y"] - self.player.y
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
                size = min(3000 / (distance + 0.0001), 300)
                bob = math.sin(enemy.get("anim_phase", 0.0)) * 10
                scale = 1.0 + 0.1 * math.sin(enemy.get("anim_phase", 0.0) * 2)
                if enemy.get("attack_frame", 0) > 0:
                    scale += 0.08
                lunge = 0
                if enemy.get("attack_frame", 0) > 0 and enemy.get("dist_to_player", 999) < 120:
                    lunge = 8

                x = screen_x - size // 2
                y = HALF_HEIGHT - size // 2 + bob - lunge

                ray_index = max(0, min(NUM_RAYS - 1, int(screen_x // SCALE)))
                if 0 <= ray_index < len(self.depth_buffer):
                    if distance < self.depth_buffer[ray_index]:
                        if enemy["alive"]:
                            sprite_size = max(1, int(size * scale))
                            sprite = self.enemy_sprites.get(enemy.get("boss_kind") or enemy.get("type"), None)
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
                            if enemy.get("time_bias", 0.0) < -0.2:
                                ghost = sprite.copy()
                                ghost.fill((200, 200, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)
                                self._blit_centered(surface, ghost, x - 6, y + 2, size, sprite_size)
                            self._blit_centered(surface, sprite, x, y, size, sprite_size)

                            bar_w = size
                            bar_h = max(4, int(size * 0.08))
                            ratio = enemy["health"] / 100
                            pygame.draw.rect(surface, (50, 50, 50), (x, y - bar_h - 5, bar_w, bar_h))
                            pygame.draw.rect(surface, (0, 255, 0), (x, y - bar_h - 5, bar_w * ratio, bar_h))
                        else:
                            alpha = max(0, 255 - enemy["death_timer"] * 10)
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
            pygame.draw.rect(self.screen, (50, 50, 50), (0, HALF_HEIGHT, WIDTH, HALF_HEIGHT))
            from systems.menu import draw_menu
            draw_menu(self.screen)
        elif self.state == "settings":
            self.screen.fill((30, 30, 30))
            pygame.draw.rect(self.screen, (100, 100, 255), (0, 0, WIDTH, HALF_HEIGHT))
            pygame.draw.rect(self.screen, (50, 50, 50), (0, HALF_HEIGHT, WIDTH, HALF_HEIGHT))
            from systems.settings_menu import draw_settings
            draw_settings(self.screen, self.settings)
        elif self.state == "cutscene":
            if self.ending_choice == "containment":
                draw_cutscene(
                    self.screen,
                    "ENDING — CONTAINMENT",
                    [
                        "You destroy the core.",
                        "The ship stabilizes.",
                        "A final message: You erased infinite others.",
                    ],
                    self.cutscene_time,
                )
            elif self.ending_choice == "ascension":
                draw_cutscene(
                    self.screen,
                    "ENDING — ASCENSION",
                    [
                        "Your body dissolves into fragmented light.",
                        "You see every outcome at once.",
                        "No past. No future. Only possibility.",
                    ],
                    self.cutscene_time,
                )
            else:
                beat = self.story_beats[self.cutscene_index]
                show_map = (self.cutscene_index == 0)
                draw_cutscene(
                    self.screen,
                    beat["title"],
                    beat["lines"],
                    self.cutscene_time,
                    map_data=self.cutscene_map if show_map else None,
                )
        elif self.state == "ending_choice":
            draw_cutscene(
                self.screen,
                "FINAL CHOICE — THE WATCHER",
                [
                    "The core is a living fracture.",
                    "Join and transcend, or shut it down.",
                    "Press 1 to CONTAIN. Press 2 to ASCEND.",
                ],
                self.cutscene_time,
                prompt="Choose your ending",
            )
        else:
            scene = pygame.Surface((WIDTH, HEIGHT))
            scene.fill((20, 20, 24))
            self._blit_stretched(scene, self.ceiling_texture, pygame.Rect(0, 0, WIDTH, HALF_HEIGHT))
            self._blit_tiled(scene, self.floor_texture, pygame.Rect(0, HALF_HEIGHT, WIDTH, HALF_HEIGHT))
            if self.room_tint_alpha > 0:
                tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                tint.fill((*self.room_tint, self.room_tint_alpha))
                scene.blit(tint, (0, 0))

            self.depth_buffer = raycast(self.world, self.player, scene, self.wall_textures, self.doors, self.door_texture)
            self.draw_enemies(scene)
            draw_health_packs(scene, self.health_packs, self.player, self.depth_buffer, self.anim_time)
            self.grenade_system.draw_grenades(scene, self.player, self.depth_buffer, self.anim_time)
            self.weapon_system.draw_bullets(scene)
            self.weapon_system.draw_weapon(scene, self.player, bob_y=self.bob_offset, sway_x=self.bob_side, sway_y=self.bob_offset * 0.3)

            zoom = 1.0 + self.screen_zoom
            target_w = max(1, int(WIDTH * zoom))
            target_h = max(1, int(HEIGHT * zoom))
            zoom_pulse = 1.0 + (self.cinematic_pulse * 0.02)
            target_w = max(1, int(WIDTH * zoom * zoom_pulse))
            target_h = max(1, int(HEIGHT * zoom * zoom_pulse))
            scaled = pygame.transform.smoothscale(scene, (target_w, target_h))
            angle = max(-5.0, min(5.0, self.roll_angle))
            if abs(angle) > 0.02:
                scaled = pygame.transform.rotozoom(scaled, angle, 1.0)

            shake_x = 0
            shake_y = 0
            if self.shake > 0:
                shake_x = int((self.shake * 0.6) * (1 if int(time.time() * 1000) % 2 == 0 else -1))
                shake_y = int((self.shake * 0.6) * (-1 if int(time.time() * 1000) % 3 == 0 else 1))

            base_x = (WIDTH - scaled.get_width()) // 2 + shake_x
            base_y = (HEIGHT - scaled.get_height()) // 2 + shake_y + int(self.bob_offset)

            self.screen.fill((0, 0, 0))
            if self.chromatic_timer > 0:
                offset = 2 + self.chromatic_timer
                red = scaled.copy()
                blue = scaled.copy()
                red.fill((255, 140, 140), special_flags=pygame.BLEND_RGB_MULT)
                blue.fill((140, 140, 255), special_flags=pygame.BLEND_RGB_MULT)
                self.screen.blit(red, (base_x + offset, base_y))
                self.screen.blit(blue, (base_x - offset, base_y))

            self.screen.blit(scaled, (base_x, base_y))
            if self.vignette_timer > 0:
                vig = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
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

            pulse = self.hit_marker / 6 if self.hit_marker > 0 else 0.0
            draw_crosshair(self.screen, self.hit_marker > 0, pulse)
            draw_level_hud(self.screen, self.hud_font, self.current_level_index, self.player)
            draw_ammo(self.screen, self.hud_font, self.player)
            draw_score(self.screen, self.hud_font, self.score, self.kills, self.score_pulse / 10 if self.score_pulse > 0 else 0.0)
            draw_weapon_info(self.screen, self.player)
            minimap_alpha = 130 + math.sin(self.ui_phase) * 25
            draw_minimap(self.screen, self.world, self.player, self.enemies, self.health_packs, minimap_alpha, self.rooms, ROOM_COLOR_MAP)
            draw_overlay_messages(self.screen, self.glitch_messages, flicker=abs(math.sin(self.ui_phase)))
            if self.room_timer > 0 and self.current_room:
                draw_room_label(self.screen, self.current_room, self.room_timer / 90, abs(math.sin(self.ui_phase)))

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
            overlay.fill((0, 100, 255, 60))  # blue tint
            self.screen.blit(overlay, (0, 0))
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.render()
            self.clock.tick(FPS)

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

WIDTH, HEIGHT = 800, 500
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
            Weapon("Pistol", 50, 10, 10, 0.02),
            Weapon("Shotgun", 25, 5, 5, 0.1),
            Weapon("Sniper", 100, 3, 3, 0.005),
        ]
        self.current_weapon_index = 0

    def switch_weapon(self, direction):
        self.current_weapon_index = (self.current_weapon_index + direction) % len(self.weapons)

    def get_weapon(self):
        return self.weapons[self.current_weapon_index]

    def move(self, world, mouse_dx, doors=None):
        keys = pygame.key.get_pressed()
        target_speed = 0.0
        if keys[pygame.K_w]:
            target_speed += self.speed
        if keys[pygame.K_s]:
            target_speed -= self.speed
        self.current_speed += (target_speed - self.current_speed) * self.accel

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

from core.settings import WIDTH, HEIGHT, DELTA_ANGLE, WEAPON_DEFAULT_IMG, WEAPON_IMAGE_MAP


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

            ray_index = max(0, min(NUM_RAYS - 1, int(screen_x // SCALE)))
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

from core.settings import WIDTH, HEIGHT


def draw_cutscene(screen, title, lines, t, prompt="Press Enter to continue", map_data=None):
    screen.fill((8, 8, 12))
    flicker = int((math.sin(t * 4) + 1) * 8)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((15 + flicker, 10 + flicker, 25 + flicker, 180))
    screen.blit(overlay, (0, 0))

    title_font = pygame.font.SysFont("arial", 28, bold=True)
    body_font = pygame.font.SysFont("arial", 20)
    sub_font = pygame.font.SysFont("arial", 16)

    y = 80
    title_surf = title_font.render(title, True, (220, 220, 240))
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, y))
    y += 50

    for line in lines:
        surf = body_font.render(line, True, (200, 210, 230))
        screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))
        y += 28

    if map_data:
        draw_compound_map(screen, map_data)

    prompt_surf = sub_font.render(prompt, True, (160, 170, 190))
    screen.blit(prompt_surf, (WIDTH // 2 - prompt_surf.get_width() // 2, HEIGHT - 70))


def draw_compound_map(screen, map_data):
    box = pygame.Rect(60, 180, WIDTH - 120, 250)
    panel = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
    panel.fill((10, 15, 25, 200))
    pygame.draw.rect(panel, (90, 120, 160, 180), panel.get_rect(), 2)

    grid_color = (40, 60, 90)
    for x in range(0, box.width, 24):
        pygame.draw.line(panel, grid_color, (x, 0), (x, box.height), 1)
    for y in range(0, box.height, 24):
        pygame.draw.line(panel, grid_color, (0, y), (box.width, y), 1)

    for link in map_data.get("links", []):
        x1, y1 = link["a"]
        x2, y2 = link["b"]
        pygame.draw.line(panel, (140, 180, 220), (x1, y1), (x2, y2), 2)

    for room in map_data.get("rooms", []):
        rect = pygame.Rect(room["x"], room["y"], room["w"], room["h"])
        pygame.draw.rect(panel, room["color"], rect)
        pygame.draw.rect(panel, (220, 230, 240), rect, 2)
        label = map_data["font"].render(room["name"], True, (230, 240, 250))
        panel.blit(label, (rect.x + 6, rect.y + 4))

    screen.blit(panel, (box.x, box.y))
```

## fps_game/systems/grenades.py
Filename: `fps_game/systems/grenades.py`

```python
import math

import pygame

from core.settings import HALF_FOV, WIDTH, FOV, NUM_RAYS, SCALE, HALF_HEIGHT, TILE
from utils.math_utils import is_wall


class GrenadeSystem:
    def __init__(self):
        self.grenades = []
        self.smokes = []
        self.cooldowns = {
            "space": 0,
            "smoke": 0,
            "stun": 0,
            "nuclear": 0,
        }
        self.cooldown_max = {
            "space": 60,
            "smoke": 80,
            "stun": 100,
            "nuclear": 180,
        }

    def try_throw(self, grenade_type, player):
        if grenade_type not in self.cooldowns:
            return False
        if self.cooldowns[grenade_type] > 0:
            return False

        self.cooldowns[grenade_type] = self.cooldown_max[grenade_type]
        speed = 14
        fuse = 45
        radius = 120
        if grenade_type == "smoke":
            fuse = 30
            radius = 140
        elif grenade_type == "stun":
            fuse = 35
            radius = 140
        elif grenade_type == "nuclear":
            fuse = 60
            radius = 240

        self.grenades.append(
            {
                "type": grenade_type,
                "x": player.x,
                "y": player.y,
                "angle": player.angle,
                "speed": speed,
                "fuse": fuse,
                "radius": radius,
            }
        )
        return True

    def update(self, world, doors, enemies, time_scale):
        events = {"shake": 0, "flash": 0, "chroma": 0, "zoom": 0}

        for key in list(self.cooldowns.keys()):
            if self.cooldowns[key] > 0:
                self.cooldowns[key] -= 1

        for grenade in self.grenades[:]:
            grenade["fuse"] -= 1
            if grenade["fuse"] <= 0:
                self._explode(grenade, enemies, events)
                self.grenades.remove(grenade)
                continue

            if time_scale == 0.0:
                continue

            nx = grenade["x"] + math.cos(grenade["angle"]) * grenade["speed"] * time_scale
            ny = grenade["y"] + math.sin(grenade["angle"]) * grenade["speed"] * time_scale
            if is_wall(nx, ny, world, TILE, doors):
                grenade["speed"] = 0
                grenade["fuse"] = min(grenade["fuse"], 15)
            else:
                grenade["x"] = nx
                grenade["y"] = ny

        for smoke in self.smokes[:]:
            smoke["timer"] -= 1
            if smoke["timer"] <= 0:
                self.smokes.remove(smoke)

        return events

    def _explode(self, grenade, enemies, events):
        gtype = grenade["type"]
        radius = grenade["radius"]
        if gtype == "smoke":
            self.smokes.append({"x": grenade["x"], "y": grenade["y"], "radius": radius, "timer": 160})
            events["flash"] = max(events["flash"], 2)
            return

        for enemy in enemies:
            dx = enemy["x"] - grenade["x"]
            dy = enemy["y"] - grenade["y"]
            dist = math.hypot(dx, dy)
            if dist <= radius and enemy["alive"]:
                falloff = max(0.2, 1 - dist / radius)
                if gtype == "space":
                    enemy["health"] -= int(40 * falloff)
                    enemy["slow_timer"] = max(enemy.get("slow_timer", 0), 90)
                elif gtype == "stun":
                    enemy["health"] -= int(15 * falloff)
                    enemy["stun_timer"] = max(enemy.get("stun_timer", 0), 90)
                elif gtype == "nuclear":
                    enemy["health"] -= int(200 * falloff)
                    enemy["stun_timer"] = max(enemy.get("stun_timer", 0), 120)
                if enemy["health"] <= 0:
                    enemy["alive"] = False

        if gtype == "space":
            events["flash"] = max(events["flash"], 4)
            events["chroma"] = max(events["chroma"], 6)
            events["shake"] = max(events["shake"], 6)
        elif gtype == "stun":
            events["flash"] = max(events["flash"], 3)
            events["chroma"] = max(events["chroma"], 4)
        elif gtype == "nuclear":
            events["flash"] = max(events["flash"], 10)
            events["chroma"] = max(events["chroma"], 12)
            events["shake"] = max(events["shake"], 16)
            events["zoom"] = max(events["zoom"], 0.08)

    def draw_grenades(self, screen, player, depth_buffer, anim_time=0.0):
        for grenade in self.grenades:
            self._draw_projected(screen, player, depth_buffer, grenade["x"], grenade["y"], 20, (240, 240, 240))

        for smoke in self.smokes:
            radius = smoke["radius"]
            pulse = 1 + 0.15 * math.sin(anim_time * 2)
            self._draw_projected(screen, player, depth_buffer, smoke["x"], smoke["y"], radius * pulse, (120, 140, 170), alpha=80)

    def _draw_projected(self, screen, player, depth_buffer, x, y, size_base, color, alpha=255):
        dx = x - player.x
        dy = y - player.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        theta = math.atan2(dy, dx)
        delta = (theta - player.angle) % (2 * math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi

        if -HALF_FOV < delta < HALF_FOV:
            screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
            size = min(2000 / (dist + 0.0001), size_base)
            x2 = screen_x - size // 2
            y2 = HALF_HEIGHT - size // 2
            ray_index = max(0, min(NUM_RAYS - 1, int(screen_x // SCALE)))
            if 0 <= ray_index < len(depth_buffer):
                if dist < depth_buffer[ray_index]:
                    surf = pygame.Surface((int(size), int(size)), pygame.SRCALPHA)
                    surf.fill((*color, alpha))
                    screen.blit(surf, (x2, y2))
```

## fps_game/systems/menu.py
Filename: `fps_game/systems/menu.py`

```python
import pygame
from core.settings import WIDTH, HEIGHT


def draw_menu(screen):
    font = pygame.font.SysFont("arial", 40)

    title = font.render("FPS GAME", True, (255, 255, 255))
    play = font.render("Press ENTER to Play", True, (200, 200, 200))
    settings = font.render("Press S for Settings", True, (200, 200, 200))

    screen.blit(title, (WIDTH // 2 - 120, HEIGHT // 3))
    screen.blit(play, (WIDTH // 2 - 180, HEIGHT // 2))
    screen.blit(settings, (WIDTH // 2 - 180, HEIGHT // 2 + 50))
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
                color = 255 / (1 + depth * depth * 0.0001)
                if hit_door and door_texture is not None:
                    tex = door_texture
                elif textures:
                    key = world.get((tile_x, tile_y), "#")
                    tex = textures.get(key)
                else:
                    tex = None
                if tex is not None:
                    if tex:
                        tex_w = tex.get_width()
                        tex_h = tex.get_height()
                        tex_x = int((x % TILE) / TILE * tex_w)
                        tex_x = max(0, min(tex_w - 1, tex_x))
                        column = tex.subsurface((tex_x, 0, 1, tex_h))
                        column = pygame.transform.scale(column, (SCALE, int(proj_height)))
                        shade = max(40, min(255, int(color)))
                        column.fill((shade, shade, shade), special_flags=pygame.BLEND_MULT)
                        screen.blit(column, (ray * SCALE, HALF_HEIGHT - proj_height // 2))
                else:
                    pygame.draw.rect(
                        screen,
                        (color, color, color),
                        (ray * SCALE, HALF_HEIGHT - proj_height // 2, SCALE, proj_height),
                    )
                break

        depth_buffer.append(depth_wall)
        cur_angle += DELTA_ANGLE

    return depth_buffer
```

## fps_game/systems/settings_menu.py
Filename: `fps_game/systems/settings_menu.py`

```python
import pygame
from core.settings import WIDTH, HEIGHT


def draw_settings(screen, settings):
    font = pygame.font.SysFont("arial", 30)

    sens = font.render(
        f"Mouse Sensitivity: {settings['sensitivity']:.3f}",
        True,
        (255, 255, 255),
    )
    back = font.render("Press ESC to go back", True, (200, 200, 200))

    screen.blit(sens, (WIDTH // 2 - 200, HEIGHT // 2))
    screen.blit(back, (WIDTH // 2 - 200, HEIGHT // 2 + 50))
```

## fps_game/systems/ui.py
Filename: `fps_game/systems/ui.py`

```python
import pygame

from core.settings import WIDTH, HEIGHT


def draw_crosshair(screen, hit=False, pulse=0.0):
    cx, cy = WIDTH // 2, HEIGHT // 2
    size = 10 + int(6 * pulse)
    alpha = max(0, min(255, 200 + int(55 * pulse)))
    color = (alpha, alpha, alpha)
    pygame.draw.line(screen, color, (cx - size, cy), (cx + size, cy), 2)
    pygame.draw.line(screen, color, (cx, cy - size), (cx, cy + size), 2)
    if hit:
        color = (255, 60, 60)
        hit_size = 12 + int(6 * pulse)
        pygame.draw.line(screen, color, (cx - hit_size, cy - hit_size), (cx + hit_size, cy + hit_size), 2)
        pygame.draw.line(screen, color, (cx - hit_size, cy + hit_size), (cx + hit_size, cy - hit_size), 2)


def draw_level_hud(screen, font, level_index, player):
    level_text = f"Level {level_index + 1}"
    surf = font.render(level_text, True, (230, 230, 230))
    screen.blit(surf, (12, 10))

    bar_w = 180
    bar_h = 18
    x = 12
    y = 38
    pygame.draw.rect(screen, (40, 40, 40), (x, y, bar_w, bar_h))
    ratio = max(0, player.health) / player.max_health
    pygame.draw.rect(screen, (200, 40, 40), (x, y, bar_w * ratio, bar_h))
    hp_text = font.render(f"HP {max(0, player.health)}", True, (230, 230, 230))
    screen.blit(hp_text, (x + bar_w + 10, y - 2))


def draw_ammo(screen, font, player):
    weapon = player.get_weapon()
    text = f"Ammo: {weapon.ammo}/{weapon.max_ammo}"
    surf = font.render(text, True, (255, 255, 0))
    screen.blit(surf, (WIDTH - 160, HEIGHT - 30))


def draw_score(screen, font, score, kills, pulse=0.0):
    base = 255
    glow = int(140 * pulse)
    color = (base, min(255, base + glow), min(255, base + glow))
    s = font.render(f"Score: {score}", True, color)
    k = font.render(f"Kills: {kills}", True, color)
    screen.blit(s, (WIDTH - 160, 10))
    screen.blit(k, (WIDTH - 160, 35))


def draw_overlay_messages(screen, messages, flicker=0.0):
    if not messages:
        return
    font = pygame.font.SysFont("arial", 18, bold=True)
    y = 70
    for msg in messages:
        alpha = max(0, min(255, msg["timer"] * 18))
        color = (220, 80 + int(60 * flicker), 80 + int(60 * flicker))
        surf = font.render(msg["text"], True, color)
        rect = surf.get_rect(center=(WIDTH // 2, y))
        screen.blit(surf, rect)
        y += 24


def draw_room_label(screen, room_name, strength=1.0, flicker=0.0):
    if not room_name:
        return
    font = pygame.font.SysFont("arial", 22, bold=True)
    alpha = max(0, min(255, int(220 * strength)))
    glow = int(40 + 40 * flicker)
    color = (min(255, 200 + glow), min(255, 220 + glow), 255)
    surf = font.render(room_name.upper(), True, color)
    rect = surf.get_rect(center=(WIDTH // 2, 40))
    screen.blit(surf, rect)


def draw_weapon_info(screen, player):
    font = pygame.font.SysFont("arial", 20)
    weapon = player.get_weapon()
    text = f"{weapon.name} | Ammo: {weapon.ammo}/{weapon.max_ammo}"
    surf = font.render(text, True, (255, 255, 0))
    screen.blit(surf, (WIDTH // 2 - 100, HEIGHT - 40))


def draw_hit_flash(screen, amount=90):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((160, 0, 0, amount))
    screen.blit(overlay, (0, 0))


def draw_game_over(screen, font):
    go = font.render("GAME OVER", True, (255, 80, 80))
    sub = font.render("Press R to restart", True, (230, 230, 230))
    screen.blit(go, (WIDTH // 2 - go.get_width() // 2, HEIGHT // 2 - 30))
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 10))


def draw_pause(screen):
    font = pygame.font.SysFont("arial", 40)
    text = font.render("PAUSED", True, (255, 255, 255))
    screen.blit(text, (WIDTH // 2 - 80, HEIGHT // 2))
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


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

import math
import os
import random

import pygame

from core.settings import (
    WIDTH, HEIGHT, HALF_HEIGHT, HALF_FOV, FOV, NUM_RAYS, TILE,
    ALIEN_RED, ALIEN_CYAN, ALIEN_AMBER, ALIEN_TEXT_DIM,
    FINAL_BOSS_MAX_HP, FINAL_BOSS_TELEPORT_CD, FINAL_BOSS_CHARGE_SPEED,
    FINAL_BOSS_CHARGE_DAMAGE, FINAL_BOSS_MELEE_DAMAGE,
    FINAL_BOSS_PROJECTILE_SPEED, FINAL_BOSS_PROJECTILE_DAMAGE,
    FINAL_BOSS_SHOCKWAVE_DAMAGE, FINAL_BOSS_SHOCKWAVE_SPEED,
    FINAL_BOSS_GRAVITY_PULL, FINAL_BOSS_DASH_SPEED, FINAL_BOSS_DASH_DURATION,
    FINAL_BOSS_REWIND_CD, FINAL_BOSS_CLONE_HP, FINAL_BOSS_INTRO_DURATION,
    FINAL_BOSS_ARENA_RADIUS, FINAL_BOSS_PHASE_THRESHOLDS,
    EFFECT_FILES,
)

from systems import audio

CX, CY = WIDTH // 2, HEIGHT // 2

SETUP = "setup"
PHASE_1 = "phase_1"
PHASE_2 = "phase_2"
PHASE_3 = "phase_3"
PHASE_4 = "phase_4"
PHASE_5 = "phase_5"
PHASE_6 = "phase_6"
PHASE_7 = "phase_7"
PHASE_8 = "phase_8"
PHASE_9 = "phase_9"
PHASE_10 = "phase_10"
PHASE_11 = "phase_11"
FINAL = "final"
DEATH = "death"


class BossProjectile:
    def __init__(self, x, y, vx, vy, damage, radius=6, color=ALIEN_RED):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.radius = radius
        self.color = color
        self.alive = True
        self.age = 0.0

    def update(self, dt, world, doors):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.age += dt
        tile_x = int(self.x // TILE) * TILE
        tile_y = int(self.y // TILE) * TILE
        if (tile_x, tile_y) in world:
            self.alive = False
            return
        if doors:
            door = doors.get((tile_x, tile_y))
            if door and not door.get("open"):
                self.alive = False
        if self.age > 8.0:
            self.alive = False

    def hits_player(self, player, hit_radius=30):
        dx = self.x - player.x
        dy = self.y - player.y
        return (dx * dx + dy * dy) < (self.radius + hit_radius) ** 2


class FinalBoss:
    def __init__(self):
        self.active = False
        self.state = SETUP
        self.phase_timer = 0.0
        self.boss_x = 0.0
        self.boss_y = 0.0
        self.boss_angle = 0.0
        self.boss_hp = FINAL_BOSS_MAX_HP
        self.boss_max_hp = FINAL_BOSS_MAX_HP
        self.projectiles = []
        self.attack_cooldown = 0.0
        self.teleport_cooldown = 0.0
        self.dash_timer = 0.0
        self.dash_vx = 0.0
        self.dash_vy = 0.0
        self.charge_timer = 0.0
        self.charge_vx = 0.0
        self.charge_vy = 0.0
        self.disappear_timer = 0.0
        self.gravity_active = False
        self.gravity_timer = 0.0
        self.melee_cooldown = 0.0
        self.screen_shake = 0.0
        self.screen_flash = 0.0
        self.screen_freeze = False
        self.frozen_timer = 0.0
        self.boss_visible = True
        self.boss_flicker = 0.0
        self.boss_glow = 0.0
        self.victory = False
        self.defeat = False
        self.dialogue_queue = []
        self.current_dialogue = None
        self.dialogue_timer = 0.0
        self.dialogue_done = False
        self.setup_stage = 0
        self.setup_timer = 0.0
        self.player_light_radius = 0.0
        self.entity_light_radius = 0.0
        self.player_walking = False
        self.auto_walk_target = None
        self.pistol_revealed = False
        self.pistol_alpha = 0
        self.hit_count = 0
        self.player_history = []
        self.prediction_text = ""
        self.prediction_timer = 0.0
        self.fractures = []
        self.rewind_positions = []
        self.rewind_cd = 0.0
        self.rewind_count = 0
        self.arena_walls_original = {}
        self.arena_dynamic_walls = set()
        self.arena_destroy_cycle = 0.0
        self.clones = []
        self.clone_active = False
        self.mirror_active = False
        self.mirror_pos = [0.0, 0.0]
        self.mirror_angle = 0.0
        self.mirror_shoot_cd = 0.0
        self.panic_dialogue_index = 0
        self.panic_timer = 0.0
        self.panic_walk_forward = False
        self.final_attack_timer = 0.0
        self.final_attack_pattern = 0
        self.death_timer = 0.0
        self.death_stage = 0
        self.anger_level = 0.0
        self.corruption_lines = []
        self.ambient_particles = []
        self.geo_lines = []
        self.flash_frames = []
        self.rift_positions = []
        self.rift_timer = 0.0
        self.time_freeze_dialogue_done = False
        self.reality_collapse_timer = 0.0
        self.floor_fragments = []
        self.boss_body_flicker = 0.0
        self._phase8_dialogue_done = False
        self._last_player_x = 0.0
        self._last_player_y = 0.0
        self._last_player_angle = 0.0
        self._player_ref = None
        self._world_ref = None
        self._doors_ref = None
        self.phase_1_hit_phrases = ["LUCK.", "YOU GOT LUCKY.", "YOU'RE LEARNING."]
        self.phase_2_hit_phrases = ["YOU ALWAYS DO THAT.", "THAT WASN'T WHAT I SAW."]
        self.phase_4_rewind_phrases = ["NO.", "NO.", "STOP.", "STOP.", "YOU ARE BREAKING TIME!"]
        self.phase_6_anger_phrases = [
            "WHY ARE YOU STILL ALIVE?!",
            "STOP MOVING!",
            "STAND STILL!",
            "YOU INSOLENT LITTLE CREATURE!",
        ]
        self.phase_11_panic_phrases = [
            "WAIT.", "YOU DON'T UNDERSTAND.",
            "I CAN FIX THIS.", "I CAN SEND YOU BACK.",
            "I CAN GIVE YOU EVERYTHING.",
            "PLEASE.", "I DON'T KNOW WHAT HAPPENS NEXT.",
        ]
        self.final_phrases = [
            "I HAVE SEEN YOUR DEATH!",
            "I HAVE SEEN YOUR FAILURE!",
            "I HAVE SEEN EVERY POSSIBLE OUTCOME!",
            "YOU ARE NOT IN ANY OF THEM!",
        ]
        self._init_particles()

    def _init_particles(self):
        self.ambient_particles = []
        for _ in range(40):
            self.ambient_particles.append({
                "x": random.uniform(0, WIDTH),
                "y": random.uniform(0, HEIGHT),
                "vx": random.uniform(-0.2, 0.2),
                "vy": random.uniform(-0.2, 0.2),
                "size": random.randint(1, 3),
                "alpha": random.randint(20, 80),
            })

    def start(self, world_ref, doors_ref, player):
        self.active = True
        self.state = SETUP
        self.phase_timer = 0.0
        self.boss_hp = FINAL_BOSS_MAX_HP
        self.boss_max_hp = FINAL_BOSS_MAX_HP
        self.projectiles = []
        self.attack_cooldown = 0.0
        self.teleport_cooldown = 0.0
        self.dash_timer = 0.0
        self.charge_timer = 0.0
        self.disappear_timer = 0.0
        self.gravity_active = False
        self.melee_cooldown = 0.0
        self.screen_shake = 0.0
        self.screen_flash = 0.0
        self.screen_freeze = False
        self.boss_visible = True
        self.boss_flicker = 0.0
        self.boss_glow = 0.0
        self.victory = False
        self.defeat = False
        self.dialogue_queue = []
        self.current_dialogue = None
        self.dialogue_done = False
        self.setup_stage = 0
        self.setup_timer = 0.0
        self.player_light_radius = 0.0
        self.entity_light_radius = 0.0
        self.player_walking = False
        self.auto_walk_target = None
        self.pistol_revealed = False
        self.pistol_alpha = 0
        self.hit_count = 0
        self.player_history = []
        self.prediction_text = ""
        self.prediction_timer = 0.0
        self.fractures = []
        self.rewind_positions = []
        self.rewind_cd = 0.0
        self.rewind_count = 0
        self.arena_dynamic_walls = set()
        self.arena_destroy_cycle = 0.0
        self.clones = []
        self.clone_active = False
        self.mirror_active = False
        self.mirror_pos = [player.x, player.y]
        self.mirror_angle = 0.0
        self.mirror_shoot_cd = 0.0
        self.panic_dialogue_index = 0
        self.panic_timer = 0.0
        self.panic_walk_forward = False
        self.final_attack_timer = 0.0
        self.final_attack_pattern = 0
        self.death_timer = 0.0
        self.death_stage = 0
        self.anger_level = 0.0
        self.corruption_lines = []
        self.flash_frames = []
        self.rift_positions = []
        self.rift_timer = 0.0
        self.arena_walls_original = dict(world_ref) if world_ref else {}
        self.time_freeze_dialogue_done = False
        self.floor_fragments = []
        self.boss_body_flicker = 0.0
        self._init_particles()
        self.boss_x = float(CX)
        self.boss_y = float(CY - 400)

    def _hp_ratio(self):
        return max(0.0, self.boss_hp / self.boss_max_hp)

    def _current_phase(self):
        ratio = self._hp_ratio()
        for i, threshold in enumerate(FINAL_BOSS_PHASE_THRESHOLDS[:-1]):
            if ratio > FINAL_BOSS_PHASE_THRESHOLDS[i + 1]:
                return i
        return len(FINAL_BOSS_PHASE_THRESHOLDS) - 2

    def _get_attack_interval(self):
        phase = self._current_phase()
        base = max(0.25, 1.4 - phase * 0.10)
        if self.state in (PHASE_6, FINAL):
            base *= 0.4
        elif self.state == PHASE_9:
            base *= 0.5
        return base

    def _play_sfx(self, key):
        path = EFFECT_FILES.get(key, "")
        if path and os.path.exists(path):
            try:
                audio.play_sound(path)
            except Exception:
                pass

    def _fire_projectile(self, px, py, tx, ty, speed=None, damage=None, color=None):
        speed = speed or FINAL_BOSS_PROJECTILE_SPEED
        damage = damage or FINAL_BOSS_PROJECTILE_DAMAGE
        color = color or ALIEN_RED
        dx, dy = tx - px, ty - py
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return
        self._play_sfx("laser")
        vx, vy = (dx / dist) * speed, (dy / dist) * speed
        self.projectiles.append(BossProjectile(px, py, vx, vy, damage, color=color))

    def _fire_spread(self, px, py, tx, ty, count=5, spread=0.4):
        self._play_sfx("laser")
        dx, dy = tx - px, ty - py
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return
        base_angle = math.atan2(dy, dx)
        for i in range(count):
            offset = (i - (count - 1) / 2.0) * spread
            angle = base_angle + offset
            vx, vy = math.cos(angle) * FINAL_BOSS_PROJECTILE_SPEED, math.sin(angle) * FINAL_BOSS_PROJECTILE_SPEED
            self.projectiles.append(BossProjectile(px, py, vx, vy, FINAL_BOSS_PROJECTILE_DAMAGE))

    def _fire_ring(self, px, py, count=8):
        self._play_sfx("explosion")
        for i in range(count):
            angle = (2 * math.pi / count) * i
            vx, vy = math.cos(angle) * FINAL_BOSS_SHOCKWAVE_SPEED, math.sin(angle) * FINAL_BOSS_SHOCKWAVE_SPEED
            self.projectiles.append(BossProjectile(px, py, vx, vy, FINAL_BOSS_SHOCKWAVE_DAMAGE, radius=8, color=ALIEN_AMBER))

    def _teleport_boss(self, tx, ty, world_ref, doors_ref):
        self._play_sfx("rewind")
        for _ in range(20):
            test_x = tx + random.uniform(-300, 300)
            test_y = ty + random.uniform(-300, 300)
            tile_x = int(test_x // TILE) * TILE
            tile_y = int(test_y // TILE) * TILE
            if world_ref and (tile_x, tile_y) not in world_ref:
                self.screen_flash = 0.5
                self.boss_x, self.boss_y = test_x, test_y
                return

    def _move_boss_toward(self, tx, ty, speed, dt, world_ref, doors_ref):
        dx, dy = tx - self.boss_x, ty - self.boss_y
        dist = math.hypot(dx, dy)
        if dist < 5.0:
            return True
        step = speed * dt
        nx = self.boss_x + (dx / dist) * step
        ny = self.boss_y + (dy / dist) * step
        tile_nx = int(nx // TILE) * TILE
        tile_ny = int(ny // TILE) * TILE
        if world_ref and (tile_nx, tile_ny) in world_ref:
            nx = self.boss_x
        if world_ref and (int(self.boss_x // TILE) * TILE, tile_ny) in world_ref:
            ny = self.boss_y
        self.boss_x, self.boss_y = nx, ny
        return False

    def _is_player_visible(self, player, world_ref, doors_ref):
        dx = player.x - self.boss_x
        dy = player.y - self.boss_y
        dist = math.hypot(dx, dy)
        steps = int(dist / (TILE * 0.5))
        if steps == 0:
            return True
        for i in range(1, steps):
            t = i / steps
            cx = self.boss_x + dx * t
            cy = self.boss_y + dy * t
            if (int(cx // TILE) * TILE, int(cy // TILE) * TILE) in (world_ref or {}):
                return False
        return True

    def _add_dialogue(self, text, speaker="ENTITY", duration=2.5, color=None):
        if color is None:
            color = ALIEN_RED if speaker == "ENTITY" else ALIEN_CYAN
        self.dialogue_queue.append({
            "text": text, "speaker": speaker, "duration": duration, "color": color,
        })

    def _set_dialogue(self, text, speaker="ENTITY", duration=2.5, color=None):
        if color is None:
            color = ALIEN_RED if speaker == "ENTITY" else ALIEN_CYAN
        self.current_dialogue = {
            "text": text, "speaker": speaker, "duration": duration, "color": color,
        }
        self.dialogue_timer = 0.0

    def _clear_dialogue(self):
        self.current_dialogue = None
        self.dialogue_timer = 0.0
        self.dialogue_queue.clear()

    def _check_phase_transition(self):
        hp = self._hp_ratio()
        if self.state == PHASE_1 and hp <= 0.85:
            self._play_sfx("opening")
            self._set_dialogue("I KNOW HOW YOU FIGHT.", duration=3.0)
            self.state = PHASE_2
            self.phase_timer = 0.0
            self.attack_cooldown = 2.0
            return True
        if self.state == PHASE_2 and hp <= 0.70:
            self._set_dialogue("THAT WASN'T WHAT I SAW.", duration=3.0)
            self.state = PHASE_3
            self.phase_timer = 0.0
            self.screen_freeze = True
            self.frozen_timer = 8.0
            return True
        if self.state == PHASE_3 and hp <= 0.65:
            self.state = PHASE_4
            self.phase_timer = 0.0
            self.rewind_cd = FINAL_BOSS_REWIND_CD
            return True
        if self.state == PHASE_4 and hp <= 0.45:
            self.state = PHASE_5
            self.phase_timer = 0.0
            self.reality_collapse_timer = 0.0
            return True
        if self.state == PHASE_5 and hp <= 0.35:
            self.state = PHASE_6
            self.phase_timer = 0.0
            self.anger_level = 0.0
            return True
        if self.state == PHASE_6 and hp <= 0.30:
            self.state = PHASE_7
            self.phase_timer = 0.0
            self._spawn_clones()
            return True
        if self.state == PHASE_7 and hp <= 0.20:
            self.state = PHASE_8
            self.phase_timer = 0.0
            self.clones.clear()
            self.clone_active = False
            return True
        if self.state == PHASE_8 and hp <= 0.15:
            self.state = PHASE_9
            self.phase_timer = 0.0
            return True
        if self.state == PHASE_9 and hp <= 0.10:
            self.state = PHASE_10
            self.phase_timer = 0.0
            self.mirror_active = True
            self.mirror_pos = [self.boss_x, self.boss_y]
            return True
        if self.state == PHASE_10 and hp <= 0.05:
            self.state = PHASE_11
            self.phase_timer = 0.0
            self.mirror_active = False
            self.projectiles.clear()
            self._clear_dialogue()
            self.panic_dialogue_index = 0
            self.panic_timer = 0.0
            return True
        if self.state == PHASE_11 and hp <= 0.03:
            self.state = FINAL
            self.phase_timer = 0.0
            self.final_attack_timer = 0.0
            self.final_attack_pattern = 0
            return True
        return False

    def _spawn_clones(self):
        self._play_sfx("echo")
        self.clones = []
        for i in range(3):
            angle = (2 * math.pi / 3) * i + random.uniform(-0.3, 0.3)
            dist = random.uniform(200, 400)
            cx = self.boss_x + math.cos(angle) * dist
            cy = self.boss_y + math.sin(angle) * dist
            self.clones.append({
                "x": cx, "y": cy,
                "hp": FINAL_BOSS_CLONE_HP,
                "max_hp": FINAL_BOSS_CLONE_HP,
                "alive": True,
                "role": ["attacker", "watcher", "stationary"][i],
                "attack_cd": 2.0 if i == 0 else 99.0,
                "death_timer": 0.0,
            })
        self.clone_active = True

    def update(self, dt, player, world_ref, doors_ref):
        if not self.active:
            return
        self._player_ref = player
        self._world_ref = world_ref
        self._doors_ref = doors_ref
        self._last_player_x = player.x
        self._last_player_y = player.y
        self._last_player_angle = player.angle
        self._update_dialogue(dt)
        self._update_particles(dt)
        if self.screen_flash > 0:
            self.screen_flash = max(0, self.screen_flash - dt * 3.0)
        if self.boss_glow > 0:
            self.boss_glow = max(0, self.boss_glow - dt * 2.0)
        if self.boss_flicker > 0:
            self.boss_flicker = max(0, self.boss_flicker - dt * 4.0)
        if self.boss_body_flicker > 0:
            self.boss_body_flicker = max(0, self.boss_body_flicker - dt * 3.0)
        if self.prediction_timer > 0:
            self.prediction_timer -= dt
        if self.disappear_timer > 0:
            self.disappear_timer -= dt
            if self.disappear_timer <= 0:
                self.boss_visible = True
        self._track_player(player)
        if self.state == SETUP:
            self._update_setup(dt, player)
        elif self.state == DEATH:
            self._update_death(dt)
        elif self.state == PHASE_3 and self.screen_freeze:
            self._update_time_freeze(dt, player)
        elif self.state == PHASE_11:
            self._update_panic(dt, player, world_ref, doors_ref)
        elif self.state == FINAL:
            self._update_final_phase(dt, player, world_ref, doors_ref)
        else:
            self._update_combat(dt, player, world_ref, doors_ref)
        self._update_projectiles(dt, world_ref, doors_ref)
        self._check_projectile_hits(player)
        self._check_melee_hits(player)
        if self.state not in (SETUP, DEATH):
            self._check_phase_transition()

    def _update_dialogue(self, dt):
        if self.current_dialogue:
            self.dialogue_timer += dt
            if self.dialogue_timer >= self.current_dialogue["duration"]:
                self.current_dialogue = None
                self.dialogue_timer = 0.0
        if self.current_dialogue is None and self.dialogue_queue:
            self.current_dialogue = self.dialogue_queue.pop(0)
            self.dialogue_timer = 0.0

    def _update_particles(self, dt):
        for p in self.ambient_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < 0:
                p["x"] = WIDTH
            elif p["x"] > WIDTH:
                p["x"] = 0
            if p["y"] < 0:
                p["y"] = HEIGHT
            elif p["y"] > HEIGHT:
                p["y"] = 0
        for f in self.fractures[:]:
            f["life"] -= dt
            if f["life"] <= 0:
                self.fractures.remove(f)
        for c in self.corruption_lines[:]:
            c["alpha"] -= dt * 60
            if c["alpha"] <= 0:
                self.corruption_lines.remove(c)
        for ff in self.flash_frames[:]:
            ff["timer"] -= dt
            if ff["timer"] <= 0:
                self.flash_frames.remove(ff)
        for rift in self.rift_positions[:]:
            rift["life"] -= dt
            if rift["life"] <= 0:
                self.rift_positions.remove(rift)

    def _track_player(self, player):
        dx = player.x - self.boss_x
        dy = player.y - self.boss_y
        dist = math.hypot(dx, dy)
        self.player_history.append({
            "x": player.x, "y": player.y,
            "vx": player.x - (self.player_history[-1]["x"] if self.player_history else player.x),
            "vy": player.y - (self.player_history[-1]["y"] if self.player_history else player.y),
            "dist": dist,
        })
        if len(self.player_history) > 180:
            self.player_history.pop(0)

    def _update_setup(self, dt, player):
        self.setup_timer += dt
        t = self.setup_timer
        if t < 2.0:
            self.player_light_radius = min(80, t * 40)
        elif t < 4.0:
            self.entity_light_radius = min(80, (t - 2.0) * 40)
        elif t < 6.0:
            self.player_walking = True
            self.auto_walk_target = (self.boss_x, self.boss_y + 100)
        elif t > 8.0 and t < 8.5:
            self._set_dialogue("YOU CAME ALL THIS WAY.", duration=2.0)
        elif t > 10.5 and t < 11.0:
            self._set_dialogue("WHY?", duration=1.5)
        elif t > 12.5 and t < 13.0:
            self._set_dialogue("YOU ALREADY KNOW HOW THIS ENDS.", duration=2.5)
        elif 15.5 < t < 17.0:
            self.pistol_revealed = True
            self.pistol_alpha = min(255, int((t - 15.5) * 200))
        elif 17.0 < t < 18.0:
            self._set_dialogue("THAT? THAT IS WHAT YOU THINK WILL KILL ME?", duration=3.0)
        elif t > 21.0:
            self.state = PHASE_1
            self.phase_timer = 0.0
            self.attack_cooldown = 1.5
            self.player_walking = False
            self.auto_walk_target = None
            self.screen_flash = 0.8
            self.screen_shake = 5.0
            self._clear_dialogue()

    def _update_combat(self, dt, player, world_ref, doors_ref):
        self.phase_timer += dt
        self.attack_cooldown -= dt
        self.teleport_cooldown -= dt
        self.melee_cooldown -= dt
        dx = player.x - self.boss_x
        dy = player.y - self.boss_y
        dist_to_player = math.hypot(dx, dy)
        self.boss_angle = math.atan2(dy, dx)
        if self.boss_glow <= 0:
            self.boss_glow = 0.0
        if self.state in (PHASE_4,):
            self.rewind_cd -= dt
            self._update_rewind(dt, world_ref, doors_ref)
        if self.state in (PHASE_5,) and not self.screen_freeze:
            self._update_reality_collapse(dt, world_ref, doors_ref)
        if self.state in (PHASE_6, FINAL):
            self.anger_level = min(1.0, self.anger_level + dt * 0.3)
            if random.random() < dt * 0.5:
                self.corruption_lines.append({
                    "x": random.randint(0, WIDTH),
                    "y": random.randint(0, HEIGHT),
                    "w": random.randint(20, 200),
                    "h": random.randint(1, 3),
                    "alpha": random.randint(40, 120),
                })
        if self.dash_timer > 0:
            self.dash_timer -= dt
            self.boss_x += self.dash_vx * dt
            self.boss_y += self.dash_vy * dt
            return
        if self.charge_timer > 0:
            self.charge_timer -= dt
            self._move_boss_toward(
                self.boss_x + self.charge_vx, self.boss_y + self.charge_vy,
                FINAL_BOSS_CHARGE_SPEED * 2, dt, world_ref, doors_ref)
            if dist_to_player < 60:
                self._play_sfx("explosion")
                player.apply_damage(FINAL_BOSS_CHARGE_DAMAGE)
                self.screen_shake = 8.0
                self.screen_flash = 0.6
            return
        if self.gravity_active and self.gravity_timer > 0:
            self.gravity_timer -= dt
            pull_dx = self.boss_x - player.x
            pull_dy = self.boss_y - player.y
            pull_dist = math.hypot(pull_dx, pull_dy)
            if pull_dist > 10:
                player.x += (pull_dx / pull_dist) * FINAL_BOSS_GRAVITY_PULL * dt
                player.y += (pull_dy / pull_dist) * FINAL_BOSS_GRAVITY_PULL * dt
            if self.gravity_timer <= 0:
                self.gravity_active = False
        if self.state == PHASE_1:
            self._update_phase_1(dt, player, world_ref, doors_ref, dist_to_player)
        elif self.state == PHASE_2:
            self._update_phase_2(dt, player, world_ref, doors_ref, dist_to_player)
        elif self.state == PHASE_4:
            self._update_phase_4(dt, player, world_ref, doors_ref, dist_to_player)
        elif self.state == PHASE_5:
            self._update_phase_5(dt, player, world_ref, doors_ref, dist_to_player)
        elif self.state == PHASE_6:
            self._update_phase_6(dt, player, world_ref, doors_ref, dist_to_player)
        elif self.state == PHASE_7:
            self._update_phase_7(dt, player, world_ref, doors_ref, dist_to_player)
        elif self.state == PHASE_8:
            self._update_phase_8(dt, player, world_ref, doors_ref, dist_to_player)
        elif self.state == PHASE_9:
            self._update_phase_9(dt, player, world_ref, doors_ref, dist_to_player)
        elif self.state == PHASE_10:
            self._update_phase_10(dt, player, world_ref, doors_ref, dist_to_player)

    def _update_phase_1(self, dt, player, world_ref, doors_ref, dist):
        if self.disappear_timer > 0 or self.dash_timer > 0 or self.charge_timer > 0:
            return
        if self.attack_cooldown <= 0:
            roll = random.random()
            if roll < 0.12:
                self._teleport_boss(player.x, player.y, world_ref, doors_ref)
                self.screen_shake = 3.0
            elif roll < 0.25:
                dx = player.x - self.boss_x
                dy = player.y - self.boss_y
                d = math.hypot(dx, dy) or 1.0
                self.dash_vx = (dx / d) * FINAL_BOSS_DASH_SPEED
                self.dash_vy = (dy / d) * FINAL_BOSS_DASH_SPEED
                self.dash_timer = FINAL_BOSS_DASH_DURATION
                self.boss_flicker = 1.0
            elif roll < 0.50:
                self._fire_ring(self.boss_x, self.boss_y)
                self.screen_shake = 4.0
            elif roll < 0.65:
                self._fire_spread(self.boss_x, self.boss_y, player.x, player.y, count=4, spread=0.4)
            elif roll < 0.80:
                self._fire_projectile(self.boss_x, self.boss_y, player.x, player.y)
                dx_a = player.x - self.boss_x
                dy_a = player.y - self.boss_y
                d_a = math.hypot(dx_a, dy_a) or 1.0
                perp_x, perp_y = -dy_a / d_a, dx_a / d_a
                self._fire_projectile(
                    self.boss_x + perp_x * 30, self.boss_y + perp_y * 30,
                    player.x, player.y, speed=FINAL_BOSS_PROJECTILE_SPEED * 0.9,
                )
            elif roll < 0.88:
                self.disappear_timer = 1.0
                self.boss_visible = False
            else:
                dx = player.x - self.boss_x
                dy = player.y - self.boss_y
                d = math.hypot(dx, dy) or 1.0
                self.charge_vx = dx / d
                self.charge_vy = dy / d
                self.charge_timer = 0.6
                self.boss_glow = 1.0
            self.attack_cooldown = self._get_attack_interval()

    def _update_phase_2(self, dt, player, world_ref, doors_ref, dist):
        if self.disappear_timer > 0 or self.dash_timer > 0 or self.charge_timer > 0:
            return
        if self.attack_cooldown <= 0:
            pred = self._analyze_player_pattern()
            roll = random.random()
            if pred == "left":
                left_x = player.x - 150
                self._fire_projectile(self.boss_x, self.boss_y, left_x, player.y)
                self.prediction_text = "YOU ALWAYS DO THAT."
                self.prediction_timer = 2.0
            elif pred == "right":
                right_x = player.x + 150
                self._fire_projectile(self.boss_x, self.boss_y, right_x, player.y)
                self.prediction_text = "YOU ALWAYS DO THAT."
                self.prediction_timer = 2.0
            elif pred == "behind_cover":
                near_walls = []
                for wx, wy in world_ref.keys():
                    wdx = wx - player.x
                    wdy = wy - player.y
                    if math.hypot(wdx, wdy) < 200:
                        near_walls.append((wx, wy))
                if near_walls:
                    wall = random.choice(near_walls)
                    if wall in world_ref:
                        del world_ref[wall]
                        self.screen_shake = 3.0
                    self.prediction_text = "HIDE BEHIND THIS."
                    self.prediction_timer = 2.0
            elif pred == "rush":
                self._teleport_boss(player.x - 200 * math.cos(player.angle),
                                     player.y - 200 * math.sin(player.angle), world_ref, doors_ref)
                self.prediction_text = "I KNOW WHERE YOU'RE GOING."
                self.prediction_timer = 2.0
            elif pred == "keep_distance":
                self._fire_spread(self.boss_x, self.boss_y, player.x, player.y, count=5)
                self.prediction_text = "COME CLOSER."
                self.prediction_timer = 2.0
            else:
                if roll < 0.5:
                    self._fire_projectile(self.boss_x, self.boss_y, player.x, player.y)
                else:
                    self._teleport_boss(player.x, player.y, world_ref, doors_ref)
            self.attack_cooldown = self._get_attack_interval()

    def _analyze_player_pattern(self):
        if len(self.player_history) < 30:
            return None
        recent = self.player_history[-30:]
        left_count = sum(1 for p in recent if p["vx"] < -0.5)
        right_count = sum(1 for p in recent if p["vx"] > 0.5)
        if left_count > right_count * 1.5:
            return "left"
        if right_count > left_count * 1.5:
            return "right"
        dists = [p["dist"] for p in recent]
        avg_dist = sum(dists) / len(dists)
        if avg_dist < 150:
            return "rush"
        if avg_dist > 500:
            return "keep_distance"
        return None

    def _update_time_freeze(self, dt, player):
        self.phase_timer += dt
        t = self.phase_timer
        if not self.time_freeze_dialogue_done:
            self._clear_dialogue()
            self.time_freeze_dialogue_done = True
        if t > 1.0 and t < 1.5:
            self._set_dialogue("I HAVE SEEN THIS MOMENT.", duration=2.5)
        elif t > 4.0 and t < 4.5:
            self._set_dialogue("A THOUSAND TIMES.", duration=2.5)
        elif t > 7.0 and t < 7.5:
            self._set_dialogue("YOU DIE HERE.", duration=2.0)
        if t < 2.0:
            self.boss_y += 30 * dt
        elif t > 4.0 and t < 6.0:
            self.boss_x += 60 * dt
        elif t > 6.0 and t < 7.5:
            self.boss_y -= 60 * dt
        if t > 8.5:
            self.screen_freeze = False
            self.state = PHASE_4
            self.phase_timer = 0.0
            self.rewind_cd = FINAL_BOSS_REWIND_CD
            self._set_dialogue("What?", duration=2.0)
            self.screen_shake = 8.0

    def _update_rewind(self, dt, world_ref, doors_ref):
        self.rewind_positions.append({"x": self.boss_x, "y": self.boss_y, "t": self.phase_timer})
        if len(self.rewind_positions) > 60:
            self.rewind_positions.pop(0)
        if self.rewind_cd <= 0 and len(self.rewind_positions) > 15:
            snap = self.rewind_positions[-15]
            self.fractures.append({"x": self.boss_x, "y": self.boss_y, "life": 5.0, "damage_mult": 0.05 * (self.rewind_count + 1)})
            self.boss_x, self.boss_y = snap["x"], snap["y"]
            self.rewind_positions = self.rewind_positions[:-15]
            self.rewind_count += 1
            self.screen_flash = 0.8
            self.screen_shake = 5.0
            idx = min(self.rewind_count - 1, len(self.phase_4_rewind_phrases) - 1)
            self._set_dialogue(self.phase_4_rewind_phrases[idx], duration=2.0)
            cd = max(1.0, FINAL_BOSS_REWIND_CD - self.rewind_count * 0.3)
            self.rewind_cd = cd
        if self.attack_cooldown <= 0:
            player = self._player_ref
            if player:
                self._fire_projectile(self.boss_x, self.boss_y, player.x, player.y)
            self.attack_cooldown = self._get_attack_interval()

    def _update_phase_4(self, dt, player, world_ref, doors_ref, dist):
        if self.disappear_timer > 0 or self.dash_timer > 0 or self.charge_timer > 0:
            return
        if self.attack_cooldown <= 0:
            if random.random() < 0.4:
                self._fire_projectile(self.boss_x, self.boss_y, player.x, player.y)
            else:
                self._fire_spread(self.boss_x, self.boss_y, player.x, player.y, count=3)
            self.attack_cooldown = self._get_attack_interval()

    def _update_reality_collapse(self, dt, world_ref, doors_ref):
        self.reality_collapse_timer += dt
        if self.reality_collapse_timer > 3.0:
            self.reality_collapse_timer = 0.0
            count = random.randint(1, 3)
            for _ in range(count):
                wx = self.boss_x + random.uniform(-500, 500)
                wy = self.boss_y + random.uniform(-500, 500)
                tile_x = int(wx // TILE) * TILE
                tile_y = int(wy // TILE) * TILE
                if (tile_x, tile_y) not in world_ref:
                    world_ref[(tile_x, tile_y)] = random.choice(["#", "A", "B"])
                    self.arena_dynamic_walls.add((tile_x, tile_y))
            if len(self.arena_dynamic_walls) > 40:
                old = list(self.arena_dynamic_walls)[:5]
                for k in old:
                    if k in world_ref:
                        del world_ref[k]
                    self.arena_dynamic_walls.discard(k)
            self.screen_shake = 3.0

    def _update_phase_5(self, dt, player, world_ref, doors_ref, dist):
        if self.disappear_timer > 0 or self.dash_timer > 0 or self.charge_timer > 0:
            return
        self._move_boss_toward(player.x + random.uniform(-200, 200),
                                player.y + random.uniform(-200, 200),
                                150, dt, world_ref, doors_ref)
        if self.attack_cooldown <= 0:
            roll = random.random()
            if roll < 0.3:
                self._fire_projectile(self.boss_x, self.boss_y, player.x, player.y)
            elif roll < 0.6:
                self._fire_spread(self.boss_x, self.boss_y, player.x, player.y, count=5)
            else:
                self._fire_ring(self.boss_x, self.boss_y)
                self.screen_shake = 4.0
            self.attack_cooldown = self._get_attack_interval()

    def _update_phase_6(self, dt, player, world_ref, doors_ref, dist):
        if self.disappear_timer > 0 or self.dash_timer > 0 or self.charge_timer > 0:
            return
        self._move_boss_toward(player.x + random.uniform(-100, 100),
                                player.y + random.uniform(-100, 100),
                                200, dt, world_ref, doors_ref)
        if self.attack_cooldown <= 0:
            roll = random.random()
            if roll < 0.25:
                self._teleport_boss(player.x, player.y, world_ref, doors_ref)
            elif roll < 0.45:
                dx = player.x - self.boss_x
                dy = player.y - self.boss_y
                d = math.hypot(dx, dy) or 1.0
                self.dash_vx = (dx / d) * FINAL_BOSS_DASH_SPEED * 1.5
                self.dash_vy = (dy / d) * FINAL_BOSS_DASH_SPEED * 1.5
                self.dash_timer = FINAL_BOSS_DASH_DURATION * 0.7
                self.boss_flicker = 1.0
            elif roll < 0.7:
                self._fire_spread(self.boss_x, self.boss_y, player.x, player.y, count=7, spread=0.6)
            else:
                self._fire_ring(self.boss_x, self.boss_y, count=12)
                self.screen_shake = 6.0
            self.attack_cooldown = self._get_attack_interval()
            if random.random() < 0.3:
                phrase = random.choice(self.phase_6_anger_phrases)
                self._set_dialogue(phrase, duration=1.5)

    def _update_phase_7(self, dt, player, world_ref, doors_ref, dist):
        if not self.clone_active:
            return
        for clone in self.clones:
            if not clone["alive"]:
                clone["death_timer"] += dt
                continue
            if clone["role"] == "attacker":
                clone["attack_cd"] -= dt
                if clone["attack_cd"] <= 0:
                    self._fire_projectile(clone["x"], clone["y"], player.x, player.y)
                    clone["attack_cd"] = 1.5
                dx = player.x - clone["x"]
                dy = player.y - clone["y"]
                d = math.hypot(dx, dy)
                if d > 150:
                    clone["x"] += (dx / d) * 100 * dt
                    clone["y"] += (dy / d) * 100 * dt
            elif clone["role"] == "watcher":
                alive_attackers = [c for c in self.clones if c["alive"] and c["role"] == "attacker"]
                if not alive_attackers:
                    clone["role"] = "attacker"
                    clone["attack_cd"] = 0.5
            elif clone["role"] == "stationary":
                alive_others = [c for c in self.clones if c["alive"] and c["role"] != "stationary"]
                if not alive_others:
                    pass
        if self.attack_cooldown <= 0:
            self._fire_spread(self.boss_x, self.boss_y, player.x, player.y, count=3)
            self.attack_cooldown = self._get_attack_interval()

    def _update_phase_8(self, dt, player, world_ref, doors_ref, dist):
        self.boss_body_flicker = 1.0
        if self.phase_timer > 1.0 and not hasattr(self, '_phase8_dialogue_done'):
            self._set_dialogue("DON'T LOOK!", duration=2.0)
            self._phase8_dialogue_done = True
        if random.random() < dt * 2:
            self.geo_lines.append({
                "x1": random.randint(0, WIDTH), "y1": random.randint(0, HEIGHT),
                "x2": random.randint(0, WIDTH), "y2": random.randint(0, HEIGHT),
                "life": random.uniform(0.2, 0.5), "color": random.choice([ALIEN_RED, ALIEN_CYAN]),
            })
        if random.random() < dt * 3:
            self.flash_frames.append({
                "x": random.randint(WIDTH // 4, WIDTH * 3 // 4),
                "y": random.randint(HEIGHT // 4, HEIGHT * 3 // 4),
                "timer": 0.1, "size": random.randint(30, 80),
            })
        if self.attack_cooldown <= 0:
            self._fire_projectile(self.boss_x, self.boss_y, player.x, player.y)
            self.attack_cooldown = self._get_attack_interval() * 1.5

    def _update_phase_9(self, dt, player, world_ref, doors_ref, dist):
        if self.dash_timer > 0:
            return
        self.boss_body_flicker = 0.5
        self._move_boss_toward(player.x, player.y, 250, dt, world_ref, doors_ref)
        if dist < 80 and self.melee_cooldown <= 0:
            player.apply_damage(FINAL_BOSS_MELEE_DAMAGE)
            self.screen_shake = 8.0
            self.screen_flash = 0.8
            self.melee_cooldown = 0.8
            dx = self.boss_x - player.x
            dy = self.boss_y - player.y
            d = math.hypot(dx, dy) or 1.0
            self.boss_x += (dx / d) * 100
            self.boss_y += (dy / d) * 100
        if self.teleport_cooldown <= 0 and dist > 200:
            self._teleport_boss(player.x, player.y, world_ref, doors_ref)
            self.teleport_cooldown = FINAL_BOSS_TELEPORT_CD * 0.5
            dx = player.x - self.boss_x
            dy = player.y - self.boss_y
            d = math.hypot(dx, dy) or 1.0
            self.charge_vx = dx / d
            self.charge_vy = dy / d
            self.charge_timer = 0.4
            self.boss_glow = 1.0

    def _update_phase_10(self, dt, player, world_ref, doors_ref, dist):
        if len(self.player_history) > 5:
            lookback = min(30, len(self.player_history) - 1)
            hist = self.player_history[-lookback]
            target_x = hist["x"]
            target_y = hist["y"]
            self.mirror_pos[0] += (target_x - self.mirror_pos[0]) * dt * 3.0
            self.mirror_pos[1] += (target_y - self.mirror_pos[1]) * dt * 3.0
        self.mirror_shoot_cd -= dt
        if self.mirror_shoot_cd <= 0:
            self._fire_projectile(self.mirror_pos[0], self.mirror_pos[1], player.x, player.y)
            self.mirror_shoot_cd = 0.4
        if self.attack_cooldown <= 0:
            self._fire_spread(self.boss_x, self.boss_y, player.x, player.y, count=3)
            self.attack_cooldown = self._get_attack_interval()

    def _update_panic(self, dt, player, world_ref, doors_ref):
        self.phase_timer += dt
        self.panic_timer += dt
        self.projectiles.clear()
        dx = player.x - self.boss_x
        dy = player.y - self.boss_y
        dist = math.hypot(dx, dy)
        self.boss_angle = math.atan2(dy, dx)
        self.boss_body_flicker = 0.3
        if self.panic_dialogue_index < len(self.phase_11_panic_phrases):
            phrase = self.phase_11_panic_phrases[self.panic_dialogue_index]
            if self.panic_timer > len(phrase) * 0.12 + 1.5:
                self._set_dialogue(phrase, duration=2.5, color=ALIEN_AMBER)
                self.panic_dialogue_index += 1
                self.panic_timer = 0.0
        if dist > 200:
            self._move_boss_toward(player.x, player.y, 60, dt, world_ref, doors_ref)
        if self.panic_dialogue_index >= len(self.phase_11_panic_phrases) and not self.current_dialogue:
            self.state = FINAL
            self.phase_timer = 0.0
            self.final_attack_timer = 0.0
            self.final_attack_pattern = 0
            self.screen_shake = 10.0
            self.screen_flash = 1.0

    def _update_final_phase(self, dt, player, world_ref, doors_ref):
        self.phase_timer += dt
        self.attack_cooldown -= dt
        self.teleport_cooldown -= dt
        self.final_attack_timer += dt
        dx = player.x - self.boss_x
        dy = player.y - self.boss_y
        dist = math.hypot(dx, dy)
        self.boss_angle = math.atan2(dy, dx)
        self.boss_body_flicker = 0.8
        self.screen_shake = max(self.screen_shake, 3.0)
        if random.random() < dt * 3:
            self.corruption_lines.append({
                "x": random.randint(0, WIDTH), "y": random.randint(0, HEIGHT),
                "w": random.randint(30, 300), "h": random.randint(1, 4),
                "alpha": random.randint(60, 180),
            })
        if self.final_attack_timer > 3.0:
            self.final_attack_timer = 0.0
            idx = self.final_attack_pattern % len(self.final_phrases)
            self._set_dialogue(self.final_phrases[idx], duration=2.0)
            self.final_attack_pattern += 1
        if self.attack_cooldown <= 0:
            roll = random.random()
            if roll < 0.10:
                self._teleport_boss(player.x, player.y, world_ref, doors_ref)
            elif roll < 0.22:
                self._fire_ring(self.boss_x, self.boss_y, count=20)
                self.screen_shake = 8.0
            elif roll < 0.40:
                self._fire_spread(self.boss_x, self.boss_y, player.x, player.y, count=9, spread=0.6)
            elif roll < 0.58:
                self._fire_projectile(self.boss_x, self.boss_y, player.x, player.y, speed=420)
                self._fire_projectile(self.boss_x + 60, self.boss_y, player.x, player.y, speed=380)
                self._fire_projectile(self.boss_x - 60, self.boss_y, player.x, player.y, speed=380)
            elif roll < 0.72:
                dx2 = player.x - self.boss_x
                dy2 = player.y - self.boss_y
                d2 = math.hypot(dx2, dy2) or 1.0
                self.dash_vx = (dx2 / d2) * FINAL_BOSS_DASH_SPEED * 2
                self.dash_vy = (dy2 / d2) * FINAL_BOSS_DASH_SPEED * 2
                self.dash_timer = FINAL_BOSS_DASH_DURATION
                self.boss_flicker = 1.0
            elif roll < 0.85:
                self._fire_ring(self.boss_x, self.boss_y, count=16)
                self._fire_spread(self.boss_x, self.boss_y, player.x, player.y, count=7, spread=0.5)
            else:
                self._fire_spread(self.boss_x, self.boss_y, player.x, player.y, count=5, spread=0.3)
                dx_c = player.x - self.boss_x
                dy_c = player.y - self.boss_y
                d_c = math.hypot(dx_c, dy_c) or 1.0
                self.charge_vx = dx_c / d_c
                self.charge_vy = dy_c / d_c
                self.charge_timer = 0.5
                self.boss_glow = 1.0
            self.attack_cooldown = max(0.2, self._get_attack_interval() * 0.4)
        self._move_boss_toward(player.x + random.uniform(-150, 150),
                                player.y + random.uniform(-150, 150),
                                200, dt, world_ref, doors_ref)
        if dist < 100 and self.melee_cooldown <= 0:
            self._play_sfx("player_hit")
            player.apply_damage(FINAL_BOSS_MELEE_DAMAGE * 2)
            self.screen_shake = 12.0
            self.screen_flash = 1.0
            self.melee_cooldown = 0.4

    def _update_projectiles(self, dt, world_ref, doors_ref):
        for proj in self.projectiles[:]:
            proj.update(dt, world_ref, doors_ref)
            if not proj.alive:
                self.projectiles.remove(proj)

    def _check_projectile_hits(self, player):
        for proj in self.projectiles[:]:
            if proj.hits_player(player):
                if player.apply_damage(proj.damage):
                    self.screen_shake = 5.0
                    self.screen_flash = 0.4
                self.projectiles.remove(proj)

    def _check_melee_hits(self, player):
        pass

    def _on_boss_hit(self, player):
        self.hit_count += 1
        self.screen_shake = 3.0
        self.screen_flash = 0.3
        fracture_bonus = sum(f["damage_mult"] for f in self.fractures)
        self.boss_hp -= 50 * (1.0 + fracture_bonus)
        if self.boss_hp <= 0:
            self.boss_hp = 0
            self.state = DEATH
            self._play_sfx("death")
            self.death_timer = 0.0
            self.death_stage = 0
            self._clear_dialogue()
            self.projectiles.clear()
            self.screen_shake = 15.0
        if self.state == PHASE_1:
            idx = min(self.hit_count - 1, len(self.phase_1_hit_phrases) - 1)
            if self.hit_count <= len(self.phase_1_hit_phrases):
                self._set_dialogue(self.phase_1_hit_phrases[idx], duration=2.0)
        elif self.state == PHASE_2 and self.hit_count <= 5:
            idx = min(self.hit_count - 3, len(self.phase_2_hit_phrases) - 1)
            if 3 <= self.hit_count <= 4:
                self._set_dialogue(self.phase_2_hit_phrases[idx], duration=2.0)

    def _update_death(self, dt):
        self.death_timer += dt
        self.screen_shake = max(0, 15.0 - self.death_timer * 2)
        t = self.death_timer
        if t > 1.0 and self.death_stage == 0:
            self._set_dialogue("I...", duration=2.0, color=ALIEN_AMBER)
            self.death_stage = 1
        if t > 3.0 and self.death_stage == 1:
            self._set_dialogue("...remember...", duration=2.0, color=ALIEN_CYAN)
            self.death_stage = 2
        if t > 7.0:
            self.boss_visible = False
        if t > 10.0:
            self.victory = True
            self.active = False

    def draw(self, screen, player, depth_buffer=None):
        if not self.active and self.state != DEATH:
            return
        if self.state == SETUP:
            self._draw_setup(screen)
            return
        if self.state == DEATH:
            self._draw_death(screen)
            return
        self._draw_corruption(screen)
        for p in self.ambient_particles:
            surf = pygame.Surface((p["size"], p["size"]), pygame.SRCALPHA)
            surf.fill((255, 40, 40, p["alpha"]))
            screen.blit(surf, (int(p["x"]), int(p["y"])))
        for rift in self.rift_positions:
            self._draw_rift(screen, rift)
        for frag in self.floor_fragments:
            self._draw_floor_fragment(screen, frag)
        self._draw_boss_entity(screen, player)
        if self.clone_active:
            for clone in self.clones:
                self._draw_clone(screen, clone, player)
        if self.mirror_active:
            self._draw_mirror(screen, player)
        self._draw_projectiles_screen(screen)
        for f in self.fractures:
            self._draw_fracture(screen, f)
        for ff in self.flash_frames:
            s = pygame.Surface((ff["size"], ff["size"]), pygame.SRCALPHA)
            s.fill((255, 255, 255, 180))
            screen.blit(s, (ff["x"] - ff["size"] // 2, ff["y"] - ff["size"] // 2))
        if self.geo_lines:
            for g in self.geo_lines[:]:
                alpha = max(0, int(255 * g["life"] * 3))
                if alpha > 0:
                    pygame.draw.line(screen, (*g["color"][:3], alpha) if len(g["color"]) == 3 else g["color"],
                                     (g["x1"], g["y1"]), (g["x2"], g["y2"]), 2)
        self._draw_dialogue(screen)
        self._draw_boss_health_bar(screen, player)
        self._draw_phase_label(screen)
        if self.prediction_timer > 0:
            alpha = min(255, int(self.prediction_timer * 200))
            font = pygame.font.SysFont("courier", 28, bold=True)
            t = font.render(self.prediction_text, True, ALIEN_AMBER)
            t.set_alpha(alpha)
            screen.blit(t, (CX - t.get_width() // 2, CY + 100))
        if self.screen_flash > 0:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, int(self.screen_flash * 150)))
            screen.blit(overlay, (0, 0))

    def _draw_setup(self, screen):
        screen.fill((0, 0, 0))
        if self.player_light_radius > 0:
            r = int(self.player_light_radius)
            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (200, 200, 220, 60), (r * 2, r * 2), r * 2)
            pygame.draw.circle(glow, (255, 255, 255, 120), (r * 2, r * 2), r)
            screen.blit(glow, (CX - r * 2, CY + 200 - r * 2))
        if self.entity_light_radius > 0:
            r = int(self.entity_light_radius)
            ex, ey = CX, CY - 400
            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 30, 30, 40), (r * 2, r * 2), r * 2)
            pygame.draw.circle(glow, (255, 50, 50, 100), (r * 2, r * 2), r)
            screen.blit(glow, (ex - r * 2, ey - r * 2))
            silhouette = pygame.Surface((60, 80), pygame.SRCALPHA)
            pygame.draw.ellipse(silhouette, (180, 20, 20, 150), (10, 0, 40, 60))
            pygame.draw.rect(silhouette, (150, 15, 15, 120), (15, 55, 30, 25))
            screen.blit(silhouette, (ex - 30, ey - 40))
        if self.player_walking and self.auto_walk_target:
            px = CX
            py = min(CY + 200, self.setup_timer * 30)
            r = int(self.player_light_radius)
            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (200, 200, 220, 60), (r * 2, r * 2), r * 2)
            pygame.draw.circle(glow, (255, 255, 255, 120), (r * 2, r * 2), r)
            screen.blit(glow, (px - r * 2, py - r * 2))
        if self.pistol_revealed:
            alpha = min(255, self.pistol_alpha)
            font = pygame.font.SysFont("courier", 20)
            t = font.render("[ PISTOL READY ]", True, ALIEN_CYAN)
            t.set_alpha(alpha)
            screen.blit(t, (CX - t.get_width() // 2, CY + 280))
        self._draw_dialogue(screen)

    def _draw_death(self, screen):
        screen.fill((0, 0, 0))
        t = self.death_timer
        if t < 5.0 and self.boss_visible:
            alpha = max(0, 255 - int(t * 50))
            r = max(1, int(60 * max(0, 1 - t / 5.0)))
            glow = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 50, 50, alpha), (r * 3, r * 3), r * 3)
            pygame.draw.circle(glow, (255, 100, 100, alpha), (r * 3, r * 3), r)
            screen.blit(glow, (CX - r * 3, CY - 60 - r * 3))
            for i in range(min(int(t * 3), 20)):
                fx = CX + random.randint(-100, 100)
                fy = CY - 60 + random.randint(-100, 100)
                fs = random.randint(2, 8)
                fsurf = pygame.Surface((fs, fs), pygame.SRCALPHA)
                fsurf.fill((255, 200, 100, max(0, 200 - int(t * 30))))
                screen.blit(fsurf, (fx, fy))
        if t > 6.0:
            msgs = ["SYSTEM RESTORED", "QUANTUM CORE: OFFLINE", "ENTITY: NOT DETECTED"]
            font = pygame.font.SysFont("courier", 20)
            for i, msg in enumerate(msgs):
                delay = 6.5 + i * 1.5
                if t > delay:
                    alpha = min(255, int((t - delay) * 200))
                    surf = font.render(msg, True, ALIEN_CYAN)
                    surf.set_alpha(alpha)
                    screen.blit(surf, (CX - surf.get_width() // 2, 300 + i * 40))
        if t > 12.0:
            ending_msgs = ["TEMPORAL MEMORY RETAINED", "ORIGINAL TIMELINE: UNKNOWN", "WE WILL REMEMBER."]
            font_s = pygame.font.SysFont("courier", 16)
            for i, msg in enumerate(ending_msgs):
                delay = 12.5 + i * 2.0
                if t > delay:
                    alpha = min(255, int((t - delay) * 150))
                    surf = font_s.render(msg, True, ALIEN_AMBER)
                    surf.set_alpha(alpha)
                    screen.blit(surf, (CX - surf.get_width() // 2, 500 + i * 30))
        self._draw_dialogue(screen)
        if t > 3.0 and t < 6.0:
            font = pygame.font.SysFont("courier", 48, bold=True)
            t_render = font.render("THE END", True, ALIEN_CYAN)
            alpha = min(255, int((t - 3.0) * 120))
            t_render.set_alpha(alpha)
            screen.blit(t_render, (CX - t_render.get_width() // 2, CY - 24))

    def _draw_boss_entity(self, screen, player):
        if not self.boss_visible:
            return
        if self.disappear_timer > 0:
            if random.random() > 0.3:
                return
        dx = self.boss_x - player.x
        dy = self.boss_y - player.y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return
        theta = math.atan2(dy, dx)
        delta = (theta - player.angle) % (2 * math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi
        if not (-HALF_FOV < delta < HALF_FOV):
            return
        screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
        ray_index = max(0, min(NUM_RAYS - 1, int(screen_x * NUM_RAYS / WIDTH)))
        size = min(3000 / (dist + 0.0001), 300)
        flicker_offset = 0
        if self.boss_flicker > 0:
            flicker_offset = int(math.sin(self.boss_flicker * 50) * 20)
        if self.boss_body_flicker > 0 and random.random() < 0.3:
            flicker_offset += random.randint(-30, 30)
        cx = int(screen_x + flicker_offset)
        cy = HALF_HEIGHT
        t = pygame.time.get_ticks() / 1000.0
        anger = self.anger_level
        hp_ratio = self._hp_ratio()
        body_radius = int(size * 0.8)
        if body_radius < 4:
            return

        layer = pygame.Surface((body_radius * 6, body_radius * 6), pygame.SRCALPHA)
        lc = body_radius * 3

        core_r = int(body_radius * 0.45)
        if hp_ratio > 0.5:
            core_color = (180, 30, 30)
        elif hp_ratio > 0.2:
            core_color = (220, 120, 30)
        else:
            p = abs(math.sin(t * 6))
            core_color = (255, int(150 + p * 105), int(100 + p * 100))
        core_alpha = 220
        pygame.draw.circle(layer, (*core_color, core_alpha), (lc, lc), core_r)
        inner_r = int(core_r * 0.6)
        pygame.draw.circle(layer, (*core_color, 120), (lc, lc), inner_r)
        bright = (min(255, core_color[0] + 60), min(255, core_color[1] + 80), min(255, core_color[2] + 80))
        pygame.draw.circle(layer, (*bright, 180), (lc, lc), int(core_r * 0.3))

        void_r = int(body_radius * 1.0)
        void_color = (40, 8, 15)
        pygame.draw.circle(layer, (*void_color, 210), (lc, lc), void_r)
        edge_color = (100, 18, 30)
        pygame.draw.circle(layer, (*edge_color, 150), (lc, lc), void_r, 3)

        ring_speeds = [1.2, -0.8, 0.6]
        ring_alphas = [70, 90, 60]
        ring_colors = [(150, 20, 30), (200, 40, 60), (120, 15, 25)]
        for i, (rs, ra, rc) in enumerate(zip(ring_speeds, ring_alphas, ring_colors)):
            ring_r = int(body_radius * (0.85 + i * 0.18))
            ring_w = max(1, int(2 + anger * 2))
            a = int(ra + anger * 40)
            angle_off = t * rs + i * 1.2
            for seg in range(24):
                a1 = angle_off + seg * (math.pi * 2 / 24)
                a2 = a1 + math.pi * 2 / 48
                pts = []
                for sa in [a1, a2]:
                    ex = lc + int(math.cos(sa) * ring_r)
                    ey = lc + int(math.sin(sa) * ring_r * 0.4)
                    pts.append((ex, ey))
                if len(pts) >= 2:
                    pygame.draw.line(layer, (*rc, a), pts[0], pts[1], ring_w)

        n_rays = 8
        for i in range(n_rays):
            base_a = (math.pi * 2 / n_rays) * i + t * 0.5
            ray_len = body_radius * (0.7 + 0.3 * abs(math.sin(t * 2.5 + i * 0.8)))
            ray_len *= (1.0 + anger * 0.5)
            x1 = lc + int(math.cos(base_a) * void_r)
            y1 = lc + int(math.sin(base_a) * void_r)
            x2 = lc + int(math.cos(base_a) * (void_r + ray_len))
            y2 = lc + int(math.sin(base_a) * (void_r + ray_len))
            ray_a = int(80 + 70 * abs(math.sin(t * 3 + i)))
            pygame.draw.line(layer, (255, 60, 40, ray_a), (x1, y1), (x2, y2), 2)

        eye_r = int(body_radius * 0.14)
        eye_dist = int(body_radius * 0.22)
        for ei in range(2):
            e_off = -1 if ei == 0 else 1
            ex = lc + int(math.cos(self.boss_angle) * eye_dist) + int(math.sin(self.boss_angle) * e_off * eye_r)
            ey = lc + int(math.sin(self.boss_angle) * eye_dist) - int(math.cos(self.boss_angle) * e_off * eye_r)
            pygame.draw.circle(layer, (255, 80, 80, 255), (ex, ey), eye_r)
            pupil_r = max(1, eye_r // 2)
            pygame.draw.circle(layer, (255, 220, 220, 255), (ex, ey), pupil_r)

        if self.boss_glow > 0:
            aura_r = int(body_radius * 1.8)
            aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            aura_a = int(60 * self.boss_glow)
            pygame.draw.circle(aura, (255, 40, 30, aura_a), (aura_r, aura_r), aura_r)
            pygame.draw.circle(aura, (200, 30, 20, aura_a // 2), (aura_r, aura_r), int(aura_r * 0.7))
            layer.blit(aura, (lc - aura_r, lc - aura_r))

        if self.gravity_active:
            spiral_a = int(50 + 30 * abs(math.sin(t * 3)))
            for si in range(6):
                pts = []
                for step in range(30):
                    sa = si * (math.pi * 2 / 6) + t * 2 + step * 0.3
                    sr = body_radius * 0.5 + step * body_radius * 0.06
                    sx = lc + int(math.cos(sa) * sr)
                    sy = lc + int(math.sin(sa) * sr)
                    pts.append((sx, sy))
                if len(pts) >= 2:
                    pygame.draw.lines(layer, (140, 40, 220, spiral_a), False, pts, 2)

        sprite_w, sprite_h = layer.get_size()
        screen.blit(layer, (cx - sprite_w // 2, cy - sprite_h // 2))

    def _draw_clone(self, screen, clone, player):
        if not clone["alive"]:
            if clone["death_timer"] > 1.0:
                return
            alpha = max(0, 255 - int(clone["death_timer"] * 200))
        else:
            alpha = 200
        dx = clone["x"] - player.x
        dy = clone["y"] - player.y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return
        theta = math.atan2(dy, dx)
        delta = (theta - player.angle) % (2 * math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi
        if not (-HALF_FOV < delta < HALF_FOV):
            return
        screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
        size = min(3000 / (dist + 0.0001), 200)
        sprite_size = max(1, int(size * 10.0))
        sprite = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
        color = (200, 80, 80, alpha)
        pygame.draw.circle(sprite, color, (sprite_size // 2, sprite_size // 2), sprite_size // 3)
        inner = (150, 30, 30, alpha)
        pygame.draw.circle(sprite, inner, (sprite_size // 2, sprite_size // 2), sprite_size // 5)
        x = screen_x - size // 2
        y = HALF_HEIGHT - size // 2
        dx_screen = (size - sprite_size) // 2
        dy_screen = (size - sprite_size) // 2
        screen.blit(sprite, (int(x + dx_screen), int(y + dy_screen)))
        if clone["alive"] and clone["hp"] > 0:
            bar_w = size
            bar_h = max(3, int(size * 0.06))
            ratio = clone["hp"] / clone["max_hp"]
            pygame.draw.rect(screen, (50, 50, 50), (x, y - bar_h - 5, bar_w, bar_h))
            pygame.draw.rect(screen, (0, 200, 255), (x, y - bar_h - 5, bar_w * ratio, bar_h))

    def _draw_mirror(self, screen, player):
        mx, my = self.mirror_pos
        dx = mx - player.x
        dy = my - player.y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return
        theta = math.atan2(dy, dx)
        delta = (theta - player.angle) % (2 * math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi
        if not (-HALF_FOV < delta < HALF_FOV):
            return
        screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
        size = min(3000 / (dist + 0.0001), 250)
        sprite_size = max(1, int(size * 12.0))
        sprite = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
        pygame.draw.circle(sprite, (0, 200, 200, 180), (sprite_size // 2, sprite_size // 2), sprite_size // 3)
        pygame.draw.circle(sprite, (0, 150, 150, 120), (sprite_size // 2, sprite_size // 2), sprite_size // 5)
        x = screen_x - size // 2
        y = HALF_HEIGHT - size // 2
        dx_s = (size - sprite_size) // 2
        dy_s = (size - sprite_size) // 2
        screen.blit(sprite, (int(x + dx_s), int(y + dy_s)))

    def _draw_projectiles_screen(self, screen):
        if not hasattr(self, '_last_player_x'):
            return
        for proj in self.projectiles:
            dx = proj.x - self._last_player_x
            dy = proj.y - self._last_player_y
            dist = math.hypot(dx, dy)
            if dist < 1.0:
                continue
            theta = math.atan2(dy, dx)
            delta = (theta - self._last_player_angle) % (2 * math.pi)
            if delta > math.pi:
                delta -= 2 * math.pi
            if not (-HALF_FOV < delta < HALF_FOV):
                continue
            screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
            size = max(4, min(int(200 / (dist + 1)), 20))
            glow = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*proj.color, 60), (size * 2, size * 2), size * 2)
            pygame.draw.circle(glow, (*proj.color, 220), (size * 2, size * 2), size)
            screen.blit(glow, (int(screen_x - size * 2), int(HALF_HEIGHT - size * 2)))

    def _draw_fracture(self, screen, f):
        r = 30
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        alpha = min(200, int(f["life"] * 60))
        pygame.draw.circle(glow, (255, 100, 50, alpha), (r * 2, r * 2), r * 2, 2)
        pygame.draw.line(glow, (255, 200, 100, alpha), (r, r * 2), (r * 3, r * 2), 2)
        pygame.draw.line(glow, (255, 200, 100, alpha), (r * 2, r), (r * 2, r * 3), 2)
        screen.blit(glow, (int(f["x"]) - r * 2, int(f["y"]) - r * 2))

    def _draw_rift(self, screen, rift):
        r = 40
        alpha = min(200, int(rift["life"] * 100))
        glow = pygame.Surface((r * 2, r * 4), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (180, 0, 80, alpha), (0, 0, r * 2, r * 4))
        pygame.draw.ellipse(glow, (255, 50, 100, alpha // 2), (r // 2, r // 2, r, r * 3))
        screen.blit(glow, (int(rift["x"]) - r, int(rift["y"]) - r * 2))

    def _draw_floor_fragment(self, screen, frag):
        alpha = min(180, int(frag["life"] * 60))
        surf = pygame.Surface((frag["w"], frag["h"]), pygame.SRCALPHA)
        surf.fill((80, 80, 100, alpha))
        screen.blit(surf, (int(frag["x"]), int(frag["y"])))

    def _draw_dialogue(self, screen):
        if not self.current_dialogue:
            return
        d = self.current_dialogue
        t = self.dialogue_timer
        font = pygame.font.SysFont("courier", 36, bold=True)
        text = d["text"]
        progress = min(1.0, t / max(0.01, len(text) * 0.035))
        shown = text[:int(progress * len(text))]
        alpha = 255
        if t > d["duration"] - 0.5:
            alpha = int((d["duration"] - t) / 0.5 * 255)
        alpha = max(0, min(255, alpha))
        shake_x = math.sin(t * 20) * 2 if d["color"] == ALIEN_RED else 0
        shake_y = math.cos(t * 25) * 1.5 if d["color"] == ALIEN_RED else 0
        shadow = font.render(shown, True, (0, 0, 0))
        shadow.set_alpha(max(0, alpha // 2))
        screen.blit(shadow, (CX - shadow.get_width() // 2 + 3 + int(shake_x), CY - 120 + 3 + int(shake_y)))
        surf = font.render(shown, True, d["color"])
        surf.set_alpha(alpha)
        screen.blit(surf, (CX - surf.get_width() // 2 + int(shake_x), CY - 120 + int(shake_y)))

    def _draw_boss_health_bar(self, screen, player):
        ratio = self._hp_ratio()
        bar_w = 600
        bar_h = 20
        x = CX - bar_w // 2
        y = 40
        pygame.draw.rect(screen, (30, 30, 30), (x - 2, y - 2, bar_w + 4, bar_h + 4))
        pygame.draw.rect(screen, (60, 10, 10), (x, y, bar_w, bar_h))
        fill_w = int(bar_w * ratio)
        if ratio > 0.5:
            color = ALIEN_RED
        elif ratio > 0.2:
            color = ALIEN_AMBER
        else:
            pulse = abs(math.sin(pygame.time.get_ticks() / 200))
            color = (255, int(50 + pulse * 50), int(50 + pulse * 50))
        pygame.draw.rect(screen, color, (x, y, fill_w, bar_h))
        font = pygame.font.SysFont("courier", 14, bold=True)
        label = font.render("THE ENTITY", True, ALIEN_RED)
        screen.blit(label, (x, y - 18))
        hp_text = font.render(f"{int(self.boss_hp)} / {self.boss_max_hp}", True, (200, 200, 200))
        screen.blit(hp_text, (x + bar_w - hp_text.get_width(), y - 18))
        if self.fractures:
            frac_text = font.render(f"FRACTURES: {len(self.fractures)}", True, ALIEN_AMBER)
            screen.blit(frac_text, (x + bar_w + 20, y + 2))

        pbar_w = 400
        pbar_h = 12
        px = CX - pbar_w // 2
        py = y + bar_h + 12
        p_ratio = max(0.0, player.health / player.max_health)
        pygame.draw.rect(screen, (20, 20, 20), (px - 2, py - 2, pbar_w + 4, pbar_h + 4))
        pygame.draw.rect(screen, (30, 30, 30), (px, py, pbar_w, pbar_h))
        p_fill = int(pbar_w * p_ratio)
        if p_ratio > 0.6:
            p_color = (60, 220, 120)
        elif p_ratio > 0.3:
            p_color = ALIEN_AMBER
        else:
            p_pulse = abs(math.sin(pygame.time.get_ticks() / 150))
            p_color = (255, int(60 + p_pulse * 80), int(60 + p_pulse * 80))
        pygame.draw.rect(screen, p_color, (px, py, p_fill, pbar_h))
        p_label = font.render("PILOT", True, (60, 220, 120))
        screen.blit(p_label, (px, py - 16))
        weapon = player.get_weapon()
        ammo_str = f"{weapon.ammo}/inf" if weapon.max_ammo == -1 else f"{weapon.ammo}/{weapon.max_ammo}"
        p_info = font.render(f"{weapon.name} {ammo_str}", True, (160, 160, 160))
        screen.blit(p_info, (px + pbar_w - p_info.get_width(), py - 16))
        p_hp = font.render(f"{int(player.health)} / {int(player.max_health)}", True, (200, 200, 200))
        screen.blit(p_hp, (px + pbar_w + 10, py - 2))

    def _draw_phase_label(self, screen):
        phase = self._current_phase()
        labels = [
            "I — THE DUEL", "II — PREDICTION", "III — THE FIRST CRACK",
            "IV — TEMPORAL WAR", "V — REALITY COLLAPSES", "VI — RAGE",
            "VII — THREE ENTITIES", "VIII — THE THING BEHIND",
            "IX — PHYSICAL", "X — MIRROR", "XI — PANIC",
            "FINAL — EVERYTHING",
        ]
        idx = min(phase, len(labels) - 1)
        if self.state == FINAL:
            idx = len(labels) - 1
        elif self.state == DEATH:
            return
        font = pygame.font.SysFont("courier", 16)
        t = font.render(labels[idx], True, ALIEN_TEXT_DIM)
        screen.blit(t, (WIDTH - t.get_width() - 20, HEIGHT - 30))

    def _draw_corruption(self, screen):
        for c in self.corruption_lines:
            surf = pygame.Surface((c["w"], c["h"]), pygame.SRCALPHA)
            surf.fill((255, 30, 30, max(0, int(c["alpha"]))))
            screen.blit(surf, (c["x"], c["y"]))

    def handle_event(self, event):
        pass

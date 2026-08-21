import math
import random
from collections import deque

import pygame

from core.settings import (
    WIDTH, HEIGHT, TILE, FPS,
    CHAOS_SPAWN_INTERVAL_MIN, CHAOS_SPAWN_INTERVAL_MAX,
    CHAOS_MAX_SPAWNED_WALLS, CHAOS_PORTAL_INTERVAL,
    CHAOS_PORTAL_LIFETIME, CHAOS_OBJECT_FALL_SPEED,
    CHAOS_DEBRIS_PER_SECOND,
    ALIEN_RED, ALIEN_AMBER, ALIEN_CYAN,
)


def _bfs_path_exists(start_tile, goal_tile, world, doors, max_checks=3000):
    if start_tile == goal_tile:
        return True
    queue = deque([start_tile])
    visited = {start_tile}
    checks = 0
    while queue and checks < max_checks:
        tx, ty = queue.popleft()
        checks += 1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nt = (tx + dx, ty + dy)
            if nt in visited:
                continue
            wx, wy = nt[0] * TILE, nt[1] * TILE
            if (wx, wy) in world:
                continue
            if doors:
                d = doors.get((wx, wy))
                if d and not d.get("open", False):
                    continue
            visited.add(nt)
            if nt == goal_tile:
                return True
            queue.append(nt)
    return False


class ShipChaosSystem:
    def __init__(self):
        self.active = False
        self.world_ref = None
        self.doors_ref = None
        self.player_ref = None
        self.core_tile = None
        self.spawn_timer = 0
        self.portal_timer = 0
        self.total_spawned_walls = 0
        self.spawned_wall_positions = set()
        self.portals = []
        self.falling_objects = []
        self.debris = []
        self.shake = 0.0
        self.alert_pulse = 0.0
        self.warning_messages = []
        self.phase = 0
        self.events_queue = []
        self.event_index = 0
        self.event_timer = 0.0
        self.events_schedule = [
            (0.0, "alert", "ENTITY SIGNAL: THE SHIP RECOGNIZES YOU AS A THREAT"),
            (2.0, "wall_cluster", {}),
            (5.0, "debris_burst", {}),
            (8.0, "wall_cluster", {}),
            (10.0, "corridor_spawn", {}),
            (12.0, "portal_open", {}),
            (14.0, "wall_cluster", {}),
            (17.0, "debris_burst", {}),
            (19.0, "corridor_spawn", {}),
            (22.0, "portal_open", {}),
            (24.0, "wall_cluster", {}),
            (26.0, "massive_debris", {}),
            (28.0, "corridor_spawn", {}),
            (30.0, "portal_open", {}),
            (32.0, "wall_cluster", {}),
            (34.0, "wall_cluster", {}),
            (36.0, "debris_burst", {}),
            (38.0, "portal_open", {}),
            (40.0, "wall_cluster", {}),
            (42.0, "corridor_spawn", {}),
        ]
        self.completed = False

    def start(self, world, doors, player, core_tile):
        self.active = True
        self.world_ref = world
        self.doors_ref = doors
        self.player_ref = player
        self.core_tile = core_tile
        self.spawn_timer = 60
        self.portal_timer = CHAOS_PORTAL_INTERVAL
        self.total_spawned_walls = 0
        self.spawned_wall_positions = set()
        self.portals = []
        self.falling_objects = []
        self.debris = []
        self.shake = 0.0
        self.alert_pulse = 0.0
        self.warning_messages = []
        self.phase = 0
        self.event_index = 0
        self.event_timer = 0.0
        self.completed = False

    def stop(self):
        self.active = False

    def _player_reached_core(self):
        if not self.player_ref or not self.core_tile:
            return False
        pr = int(self.player_ref.x // TILE)
        pc = int(self.player_ref.y // TILE)
        return (pr, pc) == self.core_tile

    def update(self):
        if not self.active:
            return

        self.event_timer += 1.0 / FPS
        self.alert_pulse += 0.04

        if self.shake > 0:
            self.shake = max(0, self.shake - 0.4)

        for msg in self.warning_messages[:]:
            msg["timer"] -= 1
            if msg["timer"] <= 0:
                self.warning_messages.remove(msg)

        while self.event_index < len(self.events_schedule):
            ev = self.events_schedule[self.event_index]
            if self.event_timer >= ev[0]:
                self._execute_event(ev)
                self.event_index += 1
            else:
                break

        if self.event_index >= len(self.events_schedule) and not self.portals:
            self.completed = True

        self._update_portals()
        self._update_falling_objects()
        self._update_debris()

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = random.randint(
                CHAOS_SPAWN_INTERVAL_MIN, CHAOS_SPAWN_INTERVAL_MAX)
            if self.total_spawned_walls < CHAOS_MAX_SPAWNED_WALLS:
                self._spawn_random_wall_cluster()

    def _execute_event(self, event):
        etype = event[1]
        if etype == "alert":
            msg = event[2]
            self.warning_messages.append({"text": msg, "timer": 120})
            self.shake = 12.0
        elif etype == "wall_cluster":
            self._spawn_random_wall_cluster()
            self._spawn_debris_burst(15)
            self.shake = 6.0
        elif etype == "debris_burst":
            self._spawn_debris_burst(40)
            self.shake = 8.0
            self.warning_messages.append({
                "text": "STRUCTURAL COLLAPSE DETECTED", "timer": 80
            })
        elif etype == "corridor_spawn":
            self._spawn_corridor_segment()
            self.shake = 10.0
            self.warning_messages.append({
                "text": "CORRIDOR RECONFIGURATION IN PROGRESS", "timer": 90
            })
        elif etype == "portal_open":
            self._open_portal()
            self.warning_messages.append({
                "text": "PORTAL BREACH — OBJECTS DETECTED", "timer": 100
            })
        elif etype == "massive_debris":
            self._spawn_debris_burst(80)
            self.shake = 15.0
            self.warning_messages.append({
                "text": "CATASTROPHIC HULL FAILURE", "timer": 120
            })

    def _get_player_tile(self):
        if not self.player_ref:
            return (5, 5)
        return (int(self.player_ref.x // TILE), int(self.player_ref.y // TILE))

    def _spawn_random_wall_cluster(self):
        if not self.world_ref or self.total_spawned_walls >= CHAOS_MAX_SPAWNED_WALLS:
            return
        pt = self._get_player_tile()
        attempts = 0
        while attempts < 30:
            cx = pt[0] + random.randint(-5, 5)
            cy = pt[1] + random.randint(-5, 5)
            if (cx, cy) == pt or (cx, cy) == self.core_tile:
                attempts += 1
                continue
            size = random.randint(2, 5)
            new_walls = set()
            for _ in range(size):
                dx = random.randint(-2, 2)
                dy = random.randint(-2, 2)
                wx, wy = cx + dx, cy + dy
                pos = (wx, wy)
                if pos == pt or pos == self.core_tile:
                    continue
                if pos in self.spawned_wall_positions:
                    continue
                new_walls.add(pos)

            if not new_walls:
                attempts += 1
                continue

            for wx, wy in new_walls:
                self.world_ref[(wx * TILE, wy * TILE)] = "#"
                self.spawned_wall_positions.add((wx, wy))
                self.total_spawned_walls += 1

            test_world = dict(self.world_ref)
            if _bfs_path_exists(pt, self.core_tile, test_world, self.doors_ref):
                for pos in new_walls:
                    self.falling_objects.append({
                        "tile_x": pos[0], "tile_y": pos[1],
                        "y_offset": random.randint(-200, -80),
                        "speed": random.uniform(2.0, 5.0),
                        "landed": False,
                    })
                return
            else:
                for wx, wy in new_walls:
                    key = (wx * TILE, wy * TILE)
                    if key in self.world_ref and key not in [
                        (p[0] * TILE, p[1] * TILE)
                        for p in self.spawned_wall_positions - new_walls
                    ]:
                        del self.world_ref[key]
                    self.spawned_wall_positions.discard((wx, wy))
                    self.total_spawned_walls -= 1
            attempts += 1

    def _spawn_corridor_segment(self):
        if not self.world_ref or self.total_spawned_walls >= CHAOS_MAX_SPAWNED_WALLS:
            return
        pt = self._get_player_tile()
        direction = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        start_x = pt[0] + direction[0] * random.randint(4, 8)
        start_y = pt[1] + direction[1] * random.randint(4, 8)
        length = random.randint(4, 8)
        width = random.choice([2, 3])
        new_walls = set()
        for i in range(length):
            for j in range(width):
                wx = start_x + direction[0] * i + direction[1] * j
                wy = start_y + direction[1] * i + direction[0] * j
                pos = (wx, wy)
                if pos == pt or pos == self.core_tile:
                    continue
                if pos not in self.spawned_wall_positions:
                    new_walls.add(pos)

        for wx, wy in new_walls:
            self.world_ref[(wx * TILE, wy * TILE)] = "A"
            self.spawned_wall_positions.add((wx, wy))
            self.total_spawned_walls += 1

        test_world = dict(self.world_ref)
        if not _bfs_path_exists(pt, self.core_tile, test_world, self.doors_ref):
            for wx, wy in new_walls:
                key = (wx * TILE, wy * TILE)
                if key in self.world_ref:
                    del self.world_ref[key]
                self.spawned_wall_positions.discard((wx, wy))
                self.total_spawned_walls -= 1

    def _open_portal(self):
        if not self.player_ref:
            return
        angle = random.uniform(0, math.pi * 2)
        dist = random.randint(200, 400)
        px = self.player_ref.x + math.cos(angle) * dist
        py = self.player_ref.y + math.sin(angle) * dist
        self.portals.append({
            "x": px, "y": py,
            "timer": CHAOS_PORTAL_LIFETIME,
            "emit_timer": random.randint(30, 90),
            "pulse": 0.0,
        })

    def _update_portals(self):
        for portal in self.portals[:]:
            portal["timer"] -= 1
            portal["pulse"] += 0.08
            portal["emit_timer"] -= 1
            if portal["emit_timer"] <= 0:
                portal["emit_timer"] = random.randint(60, 150)
                self._portal_emit_object(portal)
            if portal["timer"] <= 0:
                self.portals.remove(portal)

    def _portal_emit_object(self, portal):
        if not self.world_ref:
            return
        tx = int(portal["x"] // TILE)
        ty = int(portal["y"] // TILE)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                wx, wy = tx + dx, ty + dy
                pos = (wx, wy)
                pt = self._get_player_tile()
                if pos == pt or pos == self.core_tile:
                    continue
                if pos not in self.spawned_wall_positions and self.total_spawned_walls < CHAOS_MAX_SPAWNED_WALLS:
                    self.world_ref[(wx * TILE, wy * TILE)] = "D"
                    self.spawned_wall_positions.add(pos)
                    self.total_spawned_walls += 1
                    self.falling_objects.append({
                        "tile_x": wx, "tile_y": wy,
                        "y_offset": random.randint(-300, -100),
                        "speed": random.uniform(3.0, 6.0),
                        "landed": False,
                    })
                    break
            else:
                continue
            break

    def _update_falling_objects(self):
        for obj in self.falling_objects[:]:
            if not obj["landed"]:
                obj["y_offset"] += obj["speed"]
                if obj["y_offset"] >= 0:
                    obj["y_offset"] = 0
                    obj["landed"] = True

    def _spawn_debris_burst(self, count):
        for _ in range(count):
            self.debris.append({
                "x": random.uniform(0, WIDTH),
                "y": random.uniform(-HEIGHT * 0.5, 0),
                "vx": random.uniform(-1.5, 1.5),
                "vy": random.uniform(2.0, 6.0),
                "w": random.randint(2, 12),
                "h": random.randint(2, 8),
                "alpha": random.randint(100, 220),
                "rotation": random.uniform(0, math.pi * 2),
                "rot_speed": random.uniform(-0.1, 0.1),
            })

    def _update_debris(self):
        for d in self.debris[:]:
            d["x"] += d["vx"]
            d["y"] += d["vy"]
            d["vy"] += 0.05
            d["rotation"] += d["rot_speed"]
            d["alpha"] -= 1
            if d["alpha"] <= 0 or d["y"] > HEIGHT + 50:
                self.debris.remove(d)

    def draw_overlay(self, screen, ui_phase):
        if not self.active:
            return

        pulse = 0.5 + 0.5 * math.sin(self.alert_pulse)
        alert_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        alert_alpha = int(15 + 15 * pulse)
        alert_surf.fill((*ALIEN_RED, alert_alpha))
        screen.blit(alert_surf, (0, 0))

        for d in self.debris:
            surf = pygame.Surface((d["w"], d["h"]), pygame.SRCALPHA)
            color_r = min(255, 120 + int(d["alpha"] * 0.5))
            surf.fill((color_r, 60, 40, min(255, d["alpha"])))
            rotated = pygame.transform.rotate(surf, math.degrees(d["rotation"]))
            screen.blit(rotated, (int(d["x"]), int(d["y"])))

        for portal in self.portals:
            self._draw_portal(screen, portal)

        font_big = pygame.font.SysFont("courier", 44, bold=True)
        flash_alpha = int(180 + 75 * pulse)
        title = font_big.render("RED ALERT", True, (flash_alpha, 30, 30))
        title_rect = title.get_rect(center=(WIDTH // 2, 50))
        screen.blit(title, title_rect)

        sub_font = pygame.font.SysFont("courier", 22, bold=True)
        sub = sub_font.render("THE SHIP IS RECONFIGURING TO STOP YOU", True, (255, 130, 120))
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 95))

        core_msg = sub_font.render("REACH THE CORE ENTRANCE", True, ALIEN_AMBER)
        blink = int(180 + 75 * math.sin(ui_phase * 4))
        core_msg.set_alpha(blink)
        screen.blit(core_msg, (WIDTH // 2 - core_msg.get_width() // 2, HEIGHT - 45))

        for msg in self.warning_messages:
            if msg["timer"] > 0:
                ratio = msg["timer"] / 120
                a = int(min(255, 255 * ratio))
                font = pygame.font.SysFont("courier", 18, bold=True)
                t = font.render(msg["text"], True, ALIEN_RED)
                t.set_alpha(a)
                screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 130))

        inset = int(8 + 4 * pulse)
        frame_a = int(120 + 80 * pulse)
        pygame.draw.rect(screen, (frame_a, 20, 20), (inset, inset, WIDTH - inset * 2, HEIGHT - inset * 2), 4)

        scan_y = int((ui_phase * 40) % HEIGHT)
        scan_surf = pygame.Surface((WIDTH, 4), pygame.SRCALPHA)
        scan_surf.fill((*ALIEN_RED, 40))
        screen.blit(scan_surf, (0, scan_y))

        pygame.draw.line(screen, (40, 8, 8), (0, 0), (WIDTH, 0), 8)

    def _draw_portal(self, screen, portal):
        x, y = portal["x"], portal["y"]
        pulse = portal["pulse"]
        fade = min(1.0, portal["timer"] / 120)
        base_r = 40 + int(10 * math.sin(pulse * 3))

        for ring in range(3):
            r = base_r + ring * 15
            a = int(80 * fade * (1 - ring * 0.25))
            angle = pulse * (2 - ring * 0.5)
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (160, 50, 255, a), (r, r), r, 2)
            inner = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.arc(inner, (200, 80, 255, a + 20),
                            pygame.Rect(0, 0, r * 2, r * 2),
                            angle, angle + math.pi * 0.8, 3)
            screen.blit(surf, (int(x) - r, int(y) - r))
            screen.blit(inner, (int(x) - r, int(y) - r))

        core_a = int(180 * fade)
        core_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(core_surf, (220, 140, 255, core_a), (8, 8), 8)
        screen.blit(core_surf, (int(x) - 8, int(y) - 8))

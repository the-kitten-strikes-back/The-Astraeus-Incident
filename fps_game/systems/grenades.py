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

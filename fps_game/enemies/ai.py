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

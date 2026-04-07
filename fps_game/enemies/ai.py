import math
import random

from core.settings import TILE
from utils.math_utils import is_wall


def _can_see_player(enemy, player, world, doors, tile_size):
    """Simple ray march LOS check."""
    dx = player.x - enemy["x"]
    dy = player.y - enemy["y"]
    dist = math.hypot(dx, dy)
    steps = int(dist / (tile_size * 0.5))
    if steps == 0:
        return True
    for i in range(1, steps):
        t = i / steps
        cx = enemy["x"] + dx * t
        cy = enemy["y"] + dy * t
        if is_wall(cx, cy, world, tile_size, doors):
            return False
    return True


def try_fire_bullet(enemy, player, world, doors):
    """
    Returns a new bullet dict if the enemy should fire this frame, else None.
    Called from update_enemies for ranged/normal/boss types.
    """
    dx = player.x - enemy["x"]
    dy = player.y - enemy["y"]
    dist = math.hypot(dx, dy)

    fire_range  = enemy.get("fire_range", 400)
    fire_cd     = enemy.get("fire_cooldown", 0)

    if fire_cd > 0 or dist > fire_range:
        return None
    if not _can_see_player(enemy, player, world, doors, TILE):
        return None

    angle  = math.atan2(dy, dx)
    spread = enemy.get("bullet_spread", 0.04)
    angle += random.uniform(-spread, spread)

    # Reset cooldown on the enemy dict
    enemy["fire_cooldown"] = enemy.get("fire_cd_max", 60)

    return {
        "x":      enemy["x"],
        "y":      enemy["y"],
        "angle":  angle,
        "speed":  enemy.get("bullet_speed", 9),
        "damage": enemy.get("bullet_damage", 8),
        "life":   90,
        "radius": 6,
    }


def update_enemies(enemies, player, world, doors, on_player_hit, time_scale=1.0):
    if time_scale == 0.0:
        return []
    if enemies is None:
        return []

    new_bullets = []

    for enemy in enemies:
        enemy["anim_phase"] = (
            enemy.get("anim_phase", 0.0)
            + enemy.get("bob_speed", 0.2) * time_scale
        ) % (math.pi * 2)

        if enemy.get("hurt_timer", 0) > 0:
            enemy["hurt_timer"] -= 1
        if enemy.get("stun_timer", 0) > 0:
            enemy["stun_timer"] -= 1
            continue

        # Tick fire cooldown every frame regardless
        if enemy.get("fire_cooldown", 0) > 0:
            enemy["fire_cooldown"] -= 1

        if not enemy["alive"]:
            enemy["death_timer"] += 1
            continue

        dx   = player.x - enemy["x"]
        dy   = player.y - enemy["y"]
        dist = math.hypot(dx, dy)
        enemy["dist_to_player"] = dist

        # Boss burst logic
        if enemy.get("boss"):
            if enemy["boss_burst"] > 0:
                enemy["boss_burst"] -= 1
            else:
                enemy["boss_cooldown"] -= 1
                if enemy["boss_cooldown"] <= 0:
                    enemy["boss_burst"]   = random.randint(12, 26)
                    enemy["boss_cooldown"] = random.randint(90, 160)
                    enemy["time_bias"]    = random.uniform(-0.8, 1.1)

        # Movement

        if dist > 5:
            # If an enemy has ghost aggro, chase the ghost instead of player
            if enemy.get("ghost_aggro") and "ghost_target_x" in enemy:
                tdx = enemy["ghost_target_x"] - enemy["x"]
                tdy = enemy["ghost_target_y"] - enemy["y"]
                tmag = math.hypot(tdx, tdy)
                if tmag > 1:
                    tdx /= tmag
                    tdy /= tmag
            else:
                tdx = dx / dist
                tdy = dy / dist

            drift = enemy.get("time_bias", 0.0) * 0.4
            burst_scale = 2.4 if (enemy.get("boss") and enemy["boss_burst"] > 0) else 1.0
            slow_factor = 0.5 if enemy.get("slow_timer", 0) > 0 else 1.0
            if enemy.get("slow_timer", 0) > 0:
                enemy["slow_timer"] -= 1

            local_scale = max(0.25, min(2.6,
                (time_scale + drift) * burst_scale * slow_factor))

            keep_dist = enemy.get("keep_distance", 0)
            too_close = keep_dist > 0 and dist < keep_dist
            move_scale = -0.6 if too_close else 1.0

            step_x = tdx * enemy["speed"] * local_scale * move_scale
            step_y = tdy * enemy["speed"] * local_scale * move_scale
            nx = enemy["x"] + step_x
            ny = enemy["y"] + step_y
            if not is_wall(nx, enemy["y"], world, TILE, doors):
                enemy["x"] = nx
            if not is_wall(enemy["x"], ny, world, TILE, doors):
                enemy["y"] = ny
        # Attack cooldown
        if enemy.get("attack_cooldown", 0) > 0:
            enemy["attack_cooldown"] -= 1

        e_type = enemy.get("type", "normal")

        # Shooting enemies: ranged, normal (at range), all bosses
        shoots = (
            e_type == "ranged"
            or e_type == "normal"
            or enemy.get("boss", False)
        )
        if shoots:
            bullet = try_fire_bullet(enemy, player, world, doors)
            if bullet:
                new_bullets.append(bullet)
                enemy["attack_frame"] = 5

        # Melee attack (tank always, others only up close)
        melee_range = 60 if e_type != "ranged" else 0
        if e_type == "tank":
            melee_range = 70
        if (melee_range > 0
                and dist < melee_range
                and enemy["attack_cooldown"] <= 0):
            on_player_hit(enemy)
            enemy["attack_cooldown"] = 30

    return new_bullets
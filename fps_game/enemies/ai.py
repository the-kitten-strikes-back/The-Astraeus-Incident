import heapq
import math
import random

from core.settings import TILE
from utils.math_utils import is_wall


def _has_line_of_sight(x0, y0, x1, y1, world, doors, tile_size):
    """Simple ray march LOS check between two world points."""
    dx = x1 - x0
    dy = y1 - y0
    dist = math.hypot(dx, dy)
    steps = int(dist / (tile_size * 0.5))
    if steps == 0:
        return True
    for i in range(1, steps):
        t = i / steps
        cx = x0 + dx * t
        cy = y0 + dy * t
        if is_wall(cx, cy, world, tile_size, doors):
            return False
    return True


def _can_see_player(enemy, player, world, doors, tile_size):
    return _has_line_of_sight(enemy["x"], enemy["y"], player.x, player.y, world, doors, tile_size)


def _tile_from_pos(x, y):
    return int(x // TILE), int(y // TILE)


def _tile_center(tile):
    tx, ty = tile
    return tx * TILE + TILE * 0.5, ty * TILE + TILE * 0.5


def _tile_blocked(tile, world, doors):
    tx, ty = tile
    wx = tx * TILE
    wy = ty * TILE
    if (wx, wy) in world:
        return True
    if doors:
        door = doors.get((wx, wy))
        if door and not door.get("open", False):
            return True
    return False


def _build_nav_bounds(world, doors, player, enemies):
    points = []
    for wx, wy in world.keys():
        points.append((wx // TILE, wy // TILE))
    if doors:
        for dx, dy in doors.keys():
            points.append((dx // TILE, dy // TILE))

    points.append(_tile_from_pos(player.x, player.y))
    for enemy in enemies:
        points.append(_tile_from_pos(enemy["x"], enemy["y"]))

    min_tx = min(p[0] for p in points) - 2
    min_ty = min(p[1] for p in points) - 2
    max_tx = max(p[0] for p in points) + 2
    max_ty = max(p[1] for p in points) + 2
    return min_tx, min_ty, max_tx, max_ty


def _in_bounds(tile, bounds):
    tx, ty = tile
    min_tx, min_ty, max_tx, max_ty = bounds
    return min_tx <= tx <= max_tx and min_ty <= ty <= max_ty


def _heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _a_star_path(start, goal, world, doors, bounds, max_expansions=900):
    if start == goal:
        return []
    if not _in_bounds(start, bounds) or not _in_bounds(goal, bounds):
        return None

    open_heap = []
    heapq.heappush(open_heap, (0, start))

    came_from = {}
    g_score = {start: 0}
    visited = set()

    expansions = 0

    while open_heap and expansions < max_expansions:
        _, current = heapq.heappop(open_heap)
        if current in visited:
            continue

        if current == goal:
            path = []
            node = goal
            while node != start:
                path.append(node)
                node = came_from[node]
            path.reverse()
            return path

        visited.add(current)
        expansions += 1

        cx, cy = current
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            neighbor = (nx, ny)
            if not _in_bounds(neighbor, bounds):
                continue
            if neighbor != goal and _tile_blocked(neighbor, world, doors):
                continue

            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + _heuristic(neighbor, goal)
                heapq.heappush(open_heap, (f_score, neighbor))

    return None


def _next_waypoint(enemy, target_x, target_y, world, doors, bounds):
    start_tile = _tile_from_pos(enemy["x"], enemy["y"])
    goal_tile = _tile_from_pos(target_x, target_y)

    should_recalc = (
        enemy.get("_path_goal") != goal_tile
        or enemy.get("_path_recalc", 0) <= 0
        or not enemy.get("_path_tiles")
    )

    if should_recalc:
        path_tiles = _a_star_path(start_tile, goal_tile, world, doors, bounds)
        enemy["_path_tiles"] = path_tiles or []
        enemy["_path_goal"] = goal_tile
        enemy["_path_recalc"] = random.randint(10, 18)
    else:
        enemy["_path_recalc"] -= 1

    path_tiles = enemy.get("_path_tiles", [])

    # Drop consumed waypoints as enemy reaches tile centers.
    while path_tiles:
        wx, wy = _tile_center(path_tiles[0])
        if math.hypot(wx - enemy["x"], wy - enemy["y"]) <= max(6.0, TILE * 0.2):
            path_tiles.pop(0)
        else:
            break

    enemy["_path_tiles"] = path_tiles

    if not path_tiles:
        return None
    return _tile_center(path_tiles[0])


def try_fire_bullet(enemy, player, world, doors):
    """
    Returns a new bullet dict if the enemy should fire this frame, else None.
    Called from update_enemies for ranged/normal/boss types.
    """
    dx = player.x - enemy["x"]
    dy = player.y - enemy["y"]
    dist = math.hypot(dx, dy)

    fire_range = enemy.get("fire_range", 400)
    fire_cd = enemy.get("fire_cooldown", 0)

    if fire_cd > 0 or dist > fire_range:
        return None
    if not _can_see_player(enemy, player, world, doors, TILE):
        return None

    angle = math.atan2(dy, dx)
    spread = enemy.get("bullet_spread", 0.04)
    angle += random.uniform(-spread, spread)

    # Reset cooldown on the enemy dict
    enemy["fire_cooldown"] = enemy.get("fire_cd_max", 60)

    return {
        "x": enemy["x"],
        "y": enemy["y"],
        "angle": angle,
        "speed": enemy.get("bullet_speed", 9),
        "damage": enemy.get("bullet_damage", 8),
        "life": 90,
        "radius": 6,
    }


def update_enemies(enemies, player, world, doors, on_player_hit, time_scale=1.0):
    if time_scale == 0.0:
        return []
    if enemies is None:
        return []

    new_bullets = []
    nav_bounds = _build_nav_bounds(world, doors, player, enemies)

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

        dx = player.x - enemy["x"]
        dy = player.y - enemy["y"]
        dist = math.hypot(dx, dy)
        enemy["dist_to_player"] = dist

        # Boss burst logic
        if enemy.get("boss"):
            if enemy["boss_burst"] > 0:
                enemy["boss_burst"] -= 1
            else:
                enemy["boss_cooldown"] -= 1
                if enemy["boss_cooldown"] <= 0:
                    enemy["boss_burst"] = random.randint(12, 26)
                    enemy["boss_cooldown"] = random.randint(90, 160)
                    enemy["time_bias"] = random.uniform(-0.8, 1.1)

        # Movement
        if dist > 5:
            if enemy.get("ghost_aggro") and "ghost_target_x" in enemy:
                target_x = enemy["ghost_target_x"]
                target_y = enemy["ghost_target_y"]
            else:
                target_x = player.x
                target_y = player.y

            tdx = target_x - enemy["x"]
            tdy = target_y - enemy["y"]
            target_dist = math.hypot(tdx, tdy)

            if target_dist > 1:
                tdx /= target_dist
                tdy /= target_dist

            keep_dist = enemy.get("keep_distance", 0)
            too_close = keep_dist > 0 and dist < keep_dist

            if not too_close and target_dist > TILE * 0.6:
                has_los = _has_line_of_sight(
                    enemy["x"], enemy["y"], target_x, target_y, world, doors, TILE
                )
                if has_los:
                    enemy["_path_tiles"] = []
                else:
                    waypoint = _next_waypoint(
                        enemy, target_x, target_y, world, doors, nav_bounds
                    )
                    if waypoint is not None:
                        wx, wy = waypoint
                        pdx = wx - enemy["x"]
                        pdy = wy - enemy["y"]
                        pmag = math.hypot(pdx, pdy)
                        if pmag > 1:
                            tdx = pdx / pmag
                            tdy = pdy / pmag

            drift = enemy.get("time_bias", 0.0) * 0.4
            burst_scale = 2.4 if (enemy.get("boss") and enemy["boss_burst"] > 0) else 1.0
            slow_factor = 0.5 if enemy.get("slow_timer", 0) > 0 else 1.0
            if enemy.get("slow_timer", 0) > 0:
                enemy["slow_timer"] -= 1

            local_scale = max(
                0.25,
                min(2.6, (time_scale + drift) * burst_scale * slow_factor),
            )

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
        if (
            melee_range > 0
            and dist < melee_range
            and enemy["attack_cooldown"] <= 0
        ):
            on_player_hit(enemy)
            enemy["attack_cooldown"] = 30

    return new_bullets

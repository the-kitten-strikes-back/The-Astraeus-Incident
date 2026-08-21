import math

import pygame

from core.settings import TILE


def _collect_bounds(world, player, enemies, health_packs, doors=None, consoles=None):
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
    if doors:
        for dx, dy in doors.keys():
            extra_points.append((dx + TILE // 2, dy + TILE // 2))
    if consoles:
        for cx, cy in consoles:
            extra_points.append((cx, cy))

    for px, py in extra_points:
        tx = int(px // TILE)
        ty = int(py // TILE)
        min_tx = min(min_tx, tx)
        min_ty = min(min_ty, ty)
        max_tx = max(max_tx, tx)
        max_ty = max(max_ty, ty)

    return min_tx, min_ty, max_tx, max_ty


def draw_minimap(
    screen,
    world,
    player,
    enemies,
    health_packs,
    alpha=140,
    rooms=None,
    room_colors=None,
    doors=None,
    consoles=None,
):
    if not world:
        return

    base_tile = 6
    max_size = 180
    margin = 10
    padding = 6

    min_tx, min_ty, max_tx, max_ty = _collect_bounds(world, player, enemies, health_packs, doors, consoles)
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

    if doors:
        for (dx, dy), door in doors.items():
            tx = int(dx // TILE) - min_tx
            ty = int(dy // TILE) - min_ty
            cx = int(padding + tx * tile_size + tile_size / 2)
            cy = int(padding + ty * tile_size + tile_size / 2)
            is_open = bool(door.get("open", False))
            color = (70, 220, 255) if is_open else (255, 210, 60)
            radius = max(2, tile_size // 2)
            pygame.draw.circle(surf, color, (cx, cy), radius, 1)

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
        is_boss = enemy.get("boss", False)
        if not enemy["alive"]:
            color = (120, 60, 60)
            r = max(2, tile_size // 2)
        elif is_boss:
            color = (255, 120, 20)
            r = max(3, tile_size // 2 + 2)
        else:
            color = (220, 60, 60)
            r = max(2, tile_size // 2)
        pygame.draw.circle(surf, color, (int(ex), int(ey)), r)
        if is_boss and enemy["alive"]:
            pygame.draw.circle(surf, (255, 200, 80), (int(ex), int(ey)), r, 1)

    if consoles:
        for cx, cy in consoles:
            mpx, mpy = to_minimap(cx, cy)
            r = max(3, tile_size // 2 + 1)
            pygame.draw.rect(surf, (40, 200, 255), (int(mpx) - r, int(mpy) - r, r * 2, r * 2))
            pygame.draw.rect(surf, (100, 240, 255), (int(mpx) - r, int(mpy) - r, r * 2, r * 2), 1)

    px, py = to_minimap(player.x, player.y)
    pr = max(2, tile_size // 2 + 1)
    pygame.draw.circle(surf, (60, 220, 120), (int(px), int(py)), pr)

    line_len = max(6, tile_size * 2)
    lx = px + math.cos(player.angle) * line_len
    ly = py + math.sin(player.angle) * line_len
    pygame.draw.line(surf, (255, 255, 255), (px, py), (lx, ly), 2)

    screen.blit(surf, (margin, margin))

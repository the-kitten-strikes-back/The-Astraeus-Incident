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

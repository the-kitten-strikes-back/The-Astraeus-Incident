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

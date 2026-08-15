import math
import os

WIDTH, HEIGHT = 1500, 1000
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
SOUND_DIR = os.path.join(BASE_DIR, "assets", "sounds")
WEAPON_DEFAULT_IMG = os.path.join(ASSETS_DIR, "weapon.png")
WEAPON_IMAGE_MAP = {
    "Pistol": os.path.join(ASSETS_DIR, "pistol.png"),
    "Shotgun": os.path.join(ASSETS_DIR, "shotgun.png"),
    "Sniper": os.path.join(ASSETS_DIR, "sniper.png"),
    "Machine Gun": os.path.join(ASSETS_DIR, "machine_gun.png"),
}

# name -> (damage, ammo, max_ammo, spread, fire_rate, price)
WEAPON_SPECS = {
    "Pistol":       {"damage": 50, "ammo": 10, "max_ammo": 10, "spread": 0.02,  "fire_rate": 0.25, "price": 0},
    "Shotgun":      {"damage": 25, "ammo": 5,  "max_ammo": 5,  "spread": 0.10,  "fire_rate": 0.7,  "price": 200},
    "Sniper":       {"damage": 100, "ammo": 3, "max_ammo": 3,  "spread": 0.005, "fire_rate": 1.0,  "price": 400},
    "Machine Gun":  {"damage": 20, "ammo": 60, "max_ammo": 60, "spread": 0.035, "fire_rate": 0.01, "price": 600},
}

WEAPON_ORDER = ["Pistol", "Shotgun", "Sniper", "Machine Gun"]
LEVEL_POINTS = 100
WEAPON_PICKUP_CHAR = "W"
WEAPON_PICKUP_RANGE = 80
WEAPON_PICKUP_OPTIONS = ["Shotgun", "Sniper", "Machine Gun"]
ENEMY_IMG = os.path.join(ASSETS_DIR, "enemy.png")
WALL_IMG  = os.path.join(ASSETS_DIR, "wall.png")
DOOR_IMG  = os.path.join(ASSETS_DIR, "door.png")
TORCH_IMG = os.path.join(ASSETS_DIR, "torch.png")
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
EFFECTS_DIR = os.path.join(BASE_DIR, "assets", "sounds", "effects")
EFFECT_FILES = {
    "gunshot": os.path.join(EFFECTS_DIR, "gunshot.mp3"),
    "reload": os.path.join(EFFECTS_DIR, "reload.mp3"),
    "player_hit": os.path.join(EFFECTS_DIR, "player_hit.mp3"),
    "level_up": os.path.join(EFFECTS_DIR, "level_up.mp3"),
}
# Music configuration - maps level ranges to music files
MUSIC_DIR = os.path.join(BASE_DIR, "assets", "sounds", "music")
EFFECTS_DIR = os.path.join(BASE_DIR, "assets", "sounds", "effects")

MUSIC_TRACKS = {
    (0, 5): os.path.join(MUSIC_DIR, "levels0005.mp3"),
    (6, 10): os.path.join(MUSIC_DIR, "levels0610.mp3"),
    (11, 15): os.path.join(MUSIC_DIR, "levels1115.mp3"),
    (16, 20): os.path.join(MUSIC_DIR, "levels1620.mp3"),
}

# Sound effects configuration
EFFECT_FILES = {
    "laser": os.path.join(EFFECTS_DIR, "gunshot.mp3"),
    "level_up": os.path.join(EFFECTS_DIR, "level_up.mp3"),
    "player_hit": os.path.join(EFFECTS_DIR, "player_hit.mp3"),
    "reload": os.path.join(EFFECTS_DIR, "reload.mp3"),
    "gunshot": os.path.join(EFFECTS_DIR, "laser.mp3"),
    "dilation": os.path.join(EFFECTS_DIR, "dilation.mp3"),
    "echo": os.path.join(EFFECTS_DIR, "echo.mp3"),
    "rewind": os.path.join(EFFECTS_DIR, "rewind.mp3"),
}

# Time-freeze audio slowdown (1.0 = normal speed, 0.1 = 10x slower).
FREEZE_AUDIO_RATE = 0.3
# Seconds of the current music track captured for the slowed freeze loop.
FREEZE_AUDIO_WINDOW = 30

def get_music_for_level(level):
    """Get the music file path for a given level."""
    for (start, end), music_path in MUSIC_TRACKS.items():
        if start <= level <= end:
            return music_path
    return None

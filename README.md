# Doom-Style FPS (Pygame)

A small Doom-inspired raycasting FPS built with Pygame.

## How To Run

```bash
python3 -m fps_game.main
```

## Controls

- `W` / `S`: Move forward / back
- Mouse: Look left / right
- Left Click: Shoot
- `R`: Reload
- `1` / `2` / `3`: Switch weapons
- `Esc`: Pause (from game), Back (from settings)
- `Enter`: Start game (from menu)
- `S`: Open settings (from menu)
- `Up` / `Down`: Adjust mouse sensitivity (in settings)
- `R`: Restart after game over

## Features

- Raycasted 3D-style view
- Multiple weapon types with ammo and reloads
- Enemies with different speeds and health
- Health packs and scoring
- Minimap with player/enemy/health markers

## Project Structure (Detailed)

```
README.md
level_map.txt
levels/
  level1.txt
  level2.txt
  ...
  level20.txt
ursina_fps.py
fps_game/
  main.py
  assets/
    images/
    sounds/
  core/
    __init__.py
    game.py
    level.py
    settings.py
  enemies/
    __init__.py
    ai.py
    enemy.py
  levels/
    level1.txt
    level2.txt
    ...
    level20.txt
  player/
    __init__.py
    player.py
    weapon.py
  systems/
    __init__.py
    combat.py
    menu.py
    minimap.py
    raycasting.py
    settings_menu.py
    ui.py
  utils/
    __init__.py
    math_utils.py
```

# The Astraeus Incident

A raycasting FPS game built with Python and pygame, set aboard a deep-space vessel consumed by a temporal anomaly.

## Architecture

- **Language**: Python 3.12
- **Framework**: pygame 2.6.1
- **Rendering**: Custom raycasting engine (Wolfenstein-style)
- **Structure**:
  - `fps_game/main.py` — entry point
  - `fps_game/core/` — game loop, level loading, settings
  - `fps_game/player/` — player movement and weapon system
  - `fps_game/enemies/` — enemy AI and behavior
  - `fps_game/systems/` — raycasting, UI, combat, grenades, temporal mechanics, minimap, cutscenes
  - `fps_game/utils/` — math utilities
  - `fps_game/levels/` — 20 level text maps
  - `fps_game/assets/` — images and sounds (missing files are procedurally generated)

## Workflow

- **Start application**: `SDL_AUDIODRIVER=dummy cd fps_game && python main.py`
- **Output type**: VNC (desktop GUI app)

## Notes

- Audio is disabled via `SDL_AUDIODRIVER=dummy` (no audio device in Replit)
- `pygame.mixer.init()` is wrapped in try/except for environments without audio
- Runs in windowed mode (not fullscreen) to work correctly in the VNC environment
- Save state persists in `fps_game/save.json`
- Missing asset files are procedurally generated at runtime

## Gameplay

- 20 levels, progressive story told through cutscenes and log entries
- Temporal mechanics: time dilation, rewind, echo, fracture zones
- Grenade types: void, smoke, stun, nova
- Weapon types: pistol, shotgun, sniper
- Enemy types: normal, fast, tank, ranged, boss variants

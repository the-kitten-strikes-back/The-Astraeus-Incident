import math
import random
import pygame
from core.settings import WIDTH, HEIGHT, HALF_HEIGHT, TILE


                                                                               
           
                                                                               
DILATION_MAX_ENERGY    = 100.0
DILATION_DRAIN_RATE    = 22.0                                                 
DILATION_REGEN_RATE    = 14.0
DILATION_TIME_SCALE    = 0.25                                      
PLAYER_DILATION_SCALE  = 0.72                                                     

REWIND_HISTORY_SECS    = 15                                  
REWIND_FPS             = 30                                  
REWIND_MAX_FRAMES      = int(REWIND_HISTORY_SECS * REWIND_FPS)
REWIND_COOLDOWN_SECS   = 8.0                                   
REWIND_DURATION_FRAMES = 18                                              

ECHO_DURATION_FRAMES   = 200                                       
ECHO_COOLDOWN_SECS     = 12.0
ECHO_TRAIL_ALPHA       = 110

FRACTURE_ZONE_TYPES    = ["slow", "reverse", "fast", "mirror", "nullgrav"]

TRAIL_MAX_POINTS       = 18
TRAIL_FADE_RATE        = 14                                        


                                                                               
                                                    
                                                                               
def _snap_player(player):
    return {
        "x": player.x, "y": player.y, "angle": player.angle,
        "health": player.health, "inv": player.invincibility_frames,
        "speed": player.current_speed,
    }

def _snap_enemies(enemies):
    return [
        {"x": e["x"], "y": e["y"], "health": e["health"], "alive": e["alive"],
         "stun": e.get("stun_timer", 0), "slow": e.get("slow_timer", 0),
         "death": e.get("death_timer", 0)}
        for e in enemies
    ]


                                                                               
                  
                                                                               
class TimeDilation:
    def __init__(self):
        self.energy       = DILATION_MAX_ENERGY
        self.active       = False
        self.world_scale  = 1.0                                 
        self.player_scale = 1.0
        self._ramp        = 0.0                                 

    def toggle(self):
        if self.energy > 2.0:
            self.active = not self.active
        elif self.active:
            self.active = False

    def update(self, dt_frames=1):
        target_ramp = 1.0 if self.active else 0.0
        self.ramp    = getattr(self, "ramp", 0.0)
        self.ramp   += (target_ramp - self.ramp) * 0.12

        if self.active:
            drain = (DILATION_DRAIN_RATE / 60.0) * dt_frames
            self.energy = max(0.0, self.energy - drain)
            if self.energy <= 0.0:
                self.active = False
        else:
            regen = (DILATION_REGEN_RATE / 60.0) * dt_frames
            self.energy = min(DILATION_MAX_ENERGY, self.energy + regen)

        r = self.ramp
        self.world_scale  = 1.0 - r * (1.0 - DILATION_TIME_SCALE)
        self.player_scale = 1.0 - r * (1.0 - PLAYER_DILATION_SCALE)
        return self.world_scale, self.player_scale

    @property
    def energy_ratio(self):
        return self.energy / DILATION_MAX_ENERGY


                                                                               
                
                                                                               
class TimeRewind:
    def __init__(self):
        self._history: list[dict] = []        # oldest → newest
        self._tick   = 0
        self._sub    = max(1, 60 // REWIND_FPS)
 
        self.cooldown        = 0
        self.cooldown_max    = int(REWIND_COOLDOWN_SECS * 60)
        self.rewinding       = False
        self._playback       = []             # reversed slice we walk through
        self._playback_idx   = 0             # current position in _playback
        self.flash_alpha     = 0
 
 
    def record(self, player, enemies):
        """Called every frame during normal play to build the history buffer."""
        self._tick += 1
        if self._tick % self._sub != 0:
            return
        snap = {"p": _snap_player(player), "e": _snap_enemies(enemies)}
        self._history.append(snap)
        if len(self._history) > REWIND_MAX_FRAMES:
            self._history.pop(0)
 
 
    def can_rewind(self):
        return self.cooldown <= 0 and len(self._history) >= 2 and not self.rewinding
 
    def trigger(self):
        if not self.can_rewind():
            return False
 
        # Reverse the history so index 0 = most-recent, last = oldest.
        # We'll step through this one frame at a time during update().
        self._playback     = list(reversed(self._history))
        self._playback_idx = 0
        self._history.clear()
 
        self.rewinding   = True
        self.cooldown    = self.cooldown_max
        self.flash_alpha = 220
        return True
 
 
    def update(self, player, enemies):
        if self.cooldown > 0:
            self.cooldown -= 1
 
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 10)
 
        if not self.rewinding:
            return False
 
        # Apply the current playback frame
        if self._playback_idx < len(self._playback):
            snap = self._playback[self._playback_idx]
            self._apply(player, enemies, snap)
            self._playback_idx += 1
        else:
            # Reached the end of recorded history — rewind complete
            self.rewinding     = False
            self._playback     = []
            self._playback_idx = 0
 
        return True
 
 
    def _apply(self, player, enemies, snap):
        """Write one history snapshot onto the live player and enemies."""
        p = snap["p"]
        player.x                    = p["x"]
        player.y                    = p["y"]
        player.angle                = p["angle"]
        player.health               = p["health"]
        player.invincibility_frames = p["inv"]
        player.current_speed        = p["speed"]
 
        for i, estate in enumerate(snap["e"]):
            if i < len(enemies):
                e = enemies[i]
                e["x"]           = estate["x"]
                e["y"]           = estate["y"]
                e["health"]      = estate["health"]
                e["alive"]       = estate["alive"]
                e["stun_timer"]  = estate["stun"]
                e["slow_timer"]  = estate["slow"]
                e["death_timer"] = estate["death"]
 
 
    @property
    def cooldown_ratio(self):
        return 1.0 - self.cooldown / self.cooldown_max if self.cooldown_max else 1.0

                                                                               
                                 
                                                                               
class TemporalEcho:
    """
    A combat-capable ghost that replays the player's recorded path,
    shoots at nearby enemies, draws enemy aggro, and has its own HP.
    """
    GHOST_HP        = 60
    SHOOT_RANGE     = 280
    SHOOT_COOLDOWN  = 38          # frames between ghost shots
    AGGRO_RANGE     = 220         # enemies within this range prefer the ghost
    BULLET_SPEED    = 11
    BULLET_DAMAGE   = 18
    BULLET_LIFE     = 55

    def __init__(self):
        self._recording: list[dict] = []
        self._ghosts:    list[dict] = []
        self.cooldown     = 0
        self.cooldown_max = int(ECHO_COOLDOWN_SECS * 60)
        self._rec_tick    = 0
        self._rec_sub     = 2

        # Bullets fired by ghosts — drawn + resolved in game.py
        self.bullets: list[dict] = []

    # ── recording ──────────────────────────────────────────────────────────

    def record(self, player):
        self._rec_tick += 1
        if self._rec_tick % self._rec_sub != 0:
            return
        self._recording.append({
            "x": player.x, "y": player.y, "angle": player.angle
        })
        max_frames = ECHO_DURATION_FRAMES // self._rec_sub + 4
        if len(self._recording) > max_frames:
            self._recording.pop(0)

    # ── spawn ───────────────────────────────────────────────────────────────

    def can_spawn(self):
        return self.cooldown <= 0 and len(self._recording) >= 4

    def spawn(self, player):
        if not self.can_spawn():
            return False
        ghost = {
            "frames":       list(self._recording),
            "frame_idx":    0,
            "x":            self._recording[0]["x"],
            "y":            self._recording[0]["y"],
            "angle":        self._recording[0]["angle"],
            "alpha":        ECHO_TRAIL_ALPHA,
            "trail":        [],
            "hp":           self.GHOST_HP,
            "max_hp":       self.GHOST_HP,
            "shoot_cd":     0,
            "alive":        True,
            "hit_flash":    0,          # frames of white flash when struck
            "aggro_active": False,      # True when an enemy is targeting it
        }
        self._ghosts.append(ghost)
        self._recording.clear()
        self.cooldown = self.cooldown_max
        return True

    # ── update ──────────────────────────────────────────────────────────────

    def update(self, enemies=None, world=None):
        if self.cooldown > 0:
            self.cooldown -= 1

        # Tick bullets
        for b in self.bullets[:]:
            b["x"]    += math.cos(b["angle"]) * self.BULLET_SPEED
            b["y"]    += math.sin(b["angle"]) * self.BULLET_SPEED
            b["life"] -= 1
            if b["life"] <= 0:
                self.bullets.remove(b)
                continue
            # Wall check
            if world is not None:
                from core.settings import TILE
                tx = int(b["x"] // TILE) * TILE
                ty = int(b["y"] // TILE) * TILE
                if (tx, ty) in world:
                    self.bullets.remove(b)
                    continue
            # Hit enemies
            if enemies is not None:
                for e in enemies:
                    if not e["alive"]:
                        continue
                    if math.hypot(b["x"] - e["x"], b["y"] - e["y"]) < e.get("radius", 22):
                        e["health"]    -= self.BULLET_DAMAGE
                        e["hurt_timer"] = 6
                        if e["health"] <= 0:
                            e["alive"] = False
                        if b in self.bullets:
                            self.bullets.remove(b)
                        break

        # Tick ghost aggro — mark enemies that should prefer shooting ghost
        if enemies is not None:
            for e in enemies:
                e["ghost_aggro"] = False   # reset each frame

        for g in self._ghosts[:]:
            if g["hit_flash"] > 0:
                g["hit_flash"] -= 1

            # Advance path playback
            if g["frame_idx"] < len(g["frames"]):
                f = g["frames"][g["frame_idx"]]
                g["trail"].append((g["x"], g["y"]))
                if len(g["trail"]) > TRAIL_MAX_POINTS:
                    g["trail"].pop(0)
                g["x"]     = f["x"]
                g["y"]     = f["y"]
                g["angle"] = f["angle"]
                g["frame_idx"] += 1
            else:
                # Path finished — ghost fades
                g["alpha"] -= 6
                if g["alpha"] <= 0 or not g["alive"]:
                    self._ghosts.remove(g)
                    continue

            if not g["alive"]:
                continue

            # ── Combat: shoot at nearest visible enemy ──────────────────
            if g["shoot_cd"] > 0:
                g["shoot_cd"] -= 1

            if enemies is not None and g["shoot_cd"] <= 0:
                best      = None
                best_dist = self.SHOOT_RANGE
                for e in enemies:
                    if not e["alive"]:
                        continue
                    d = math.hypot(e["x"] - g["x"], e["y"] - g["y"])
                    if d < best_dist:
                        best      = e
                        best_dist = d

                if best is not None:
                    angle = math.atan2(best["y"] - g["y"], best["x"] - g["x"])
                    self.bullets.append({
                        "x": g["x"], "y": g["y"],
                        "angle": angle,
                        "life": self.BULLET_LIFE,
                    })
                    g["shoot_cd"] = self.SHOOT_COOLDOWN

            # ── Aggro: redirect nearby enemies toward ghost ─────────────
            if enemies is not None:
                for e in enemies:
                    if not e["alive"]:
                        continue
                    d = math.hypot(e["x"] - g["x"], e["y"] - g["y"])
                    if d < self.AGGRO_RANGE:
                        e["ghost_aggro"]    = True
                        e["ghost_target_x"] = g["x"]
                        e["ghost_target_y"] = g["y"]

            # ── Take damage from enemy bullets (called from game.py) ────
            # (game.py checks ghost.hp via apply_damage_to_ghosts)

        return  # enemies list modified in-place

    def apply_damage_to_ghosts(self, bx, by, damage, radius=20):
        """
        Called by game.py when an enemy bullet moves.
        Returns True if any ghost was hit.
        """
        for g in self._ghosts:
            if not g["alive"]:
                continue
            if math.hypot(bx - g["x"], by - g["y"]) < radius:
                g["hp"]        -= damage
                g["hit_flash"]  = 8
                if g["hp"] <= 0:
                    g["alive"]  = False
                return True
        return False

    # ── drawing ─────────────────────────────────────────────────────────────

    def draw(self, screen, player, depth_buffer):
        from core.settings import HALF_FOV, FOV, NUM_RAYS, HALF_HEIGHT

        for g in self._ghosts:
            # Trail
            for ti, (tx, ty) in enumerate(g["trail"]):
                a = int(g["alpha"] * 0.35 * (ti / max(1, len(g["trail"]))))
                self._draw_billboard(screen, player, depth_buffer,
                                     tx, ty, 6, (120, 200, 255), a)

            # Ghost body — white flash when hit, else cyan
            body_color = (255, 255, 255) if g["hit_flash"] > 0 else (140, 220, 255)
            body_alpha = min(200, g["alpha"] * 2) if g["alive"] else max(0, g["alpha"])
            self._draw_billboard(screen, player, depth_buffer,
                                 g["x"], g["y"], 32,
                                 body_color, body_alpha)

            # HP bar (screen-space, only if ghost is in front)
            if g["alive"] and g["hp"] > 0:
                self._draw_ghost_hpbar(screen, player, depth_buffer, g)

        # Ghost bullets — simple yellow dots projected into 3-D
        for b in self.bullets:
            self._draw_billboard(screen, player, depth_buffer,
                                 b["x"], b["y"], 7,
                                 (255, 240, 80), 210)

    def _draw_ghost_hpbar(self, screen, player, depth_buffer, g):
        from core.settings import HALF_FOV, FOV, NUM_RAYS, HALF_HEIGHT
        dx   = g["x"] - player.x
        dy   = g["y"] - player.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        theta = math.atan2(dy, dx)
        delta = (theta - player.angle + math.pi) % (2 * math.pi) - math.pi
        if not (-HALF_FOV < delta < HALF_FOV):
            return
        sx = (delta + HALF_FOV) * (WIDTH / FOV)
        sz = min(2000 / (dist + 0.001), 80)
        ri = max(0, min(NUM_RAYS - 1, int(sx * NUM_RAYS / WIDTH)))
        if ri >= len(depth_buffer) or dist >= depth_buffer[ri]:
            return

        bw   = int(sz * 1.2)
        bh   = 5
        bx   = int(sx - bw // 2)
        by   = int(HALF_HEIGHT - sz // 2) - bh - 4
        ratio = max(0, g["hp"] / g["max_hp"])
        pygame.draw.rect(screen, (40, 40, 40),  (bx, by, bw, bh))
        pygame.draw.rect(screen, (80, 200, 255), (bx, by, int(bw * ratio), bh))

    @staticmethod
    def _draw_billboard(screen, player, depth_buffer, wx, wy, size, color, alpha):
        if alpha <= 0:
            return
        from core.settings import HALF_FOV, FOV, NUM_RAYS, HALF_HEIGHT
        dx   = wx - player.x
        dy   = wy - player.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        theta = math.atan2(dy, dx)
        delta = (theta - player.angle + math.pi) % (2 * math.pi) - math.pi
        if not (-HALF_FOV < delta < HALF_FOV):
            return
        sx = (delta + HALF_FOV) * (WIDTH / FOV)
        sz = min(2000 / (dist + 0.001), 80)
        ri = max(0, min(NUM_RAYS - 1, int(sx * NUM_RAYS / WIDTH)))
        if ri < len(depth_buffer) and dist < depth_buffer[ri]:
            surf = pygame.Surface((int(sz + size), int(sz + size)), pygame.SRCALPHA)
            surf.fill((*color, min(255, alpha)))
            screen.blit(surf, (int(sx - sz // 2), int(HALF_HEIGHT - sz // 2)))

    @property
    def cooldown_ratio(self):
        return 1.0 - self.cooldown / self.cooldown_max if self.cooldown_max else 1.0

    @property
    def active_count(self):
        return sum(1 for g in self._ghosts if g["alive"])

                                                                               
                            
                                                                               
                                                      
FRACTURE_ROOM_EFFECTS = {
    "R": {"type": "slow",     "world_scale": 0.35, "player_scale": 0.60,
          "tint": (255, 80,  80),  "alpha": 55, "scan": True,
          "msg": "REACTOR // TEMPORAL DRAG FIELD"},
    "L": {"type": "fast",     "world_scale": 2.20, "player_scale": 1.15,
          "tint": (80,  255, 160), "alpha": 40, "scan": False,
          "msg": "LAB // ACCELERATED CHRONOLOGY"},
    "H": {"type": "reverse",  "world_scale": -0.8, "player_scale": 0.90,
          "tint": (200, 80,  255), "alpha": 60, "scan": True,
          "msg": "HANGAR // CHRONO-INVERSION ZONE"},
    "Y": {"type": "mirror",   "world_scale": 0.70, "player_scale": -0.85,
          "tint": (80,  180, 255), "alpha": 50, "scan": False,
          "msg": "CRYO BAY // MIRROR TIME FLUX"},
    "O": {"type": "nullgrav",  "world_scale": 0.55, "player_scale": 0.55,
          "tint": (200, 200, 80),  "alpha": 45, "scan": False,
          "msg": "OBSERVATION // NULL-GRAVITY SHEAR"},
}

class FractureZones:
    def __init__(self):
        self.active_effect = None                                          
        self.active_room   = ""
        self.message       = ""
        self.msg_timer     = 0

    def enter_room(self, room_key):
        if room_key == self.active_room:
            return
        self.active_room = room_key
        if room_key in FRACTURE_ROOM_EFFECTS:
            self.active_effect = FRACTURE_ROOM_EFFECTS[room_key]
            self.message   = self.active_effect["msg"]
            self.msg_timer = 120
        else:
            self.active_effect = None

    def leave_room(self):
        self.active_room   = ""
        self.active_effect = None

    def update(self):
        if self.msg_timer > 0:
            self.msg_timer -= 1

    def get_world_scale(self):
        if self.active_effect:
            return self.active_effect["world_scale"]
        return 1.0

    def get_player_scale(self):
        if self.active_effect:
            return self.active_effect["player_scale"]
        return 1.0

    def draw_overlay(self, screen, phase):
        if not self.active_effect:
            return
        effect = self.active_effect
        etype  = effect["type"]
        tint   = effect["tint"]
        alpha  = effect["alpha"]

                    
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        surf.fill((*tint, alpha))
        screen.blit(surf, (0, 0))

                                  
        if effect.get("scan"):
            scan = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for y in range(0, HEIGHT, 5):
                a = 22 if (y // 5) % 2 == 0 else 8
                scan.fill((*tint, a), pygame.Rect(0, y, WIDTH, 2))
            screen.blit(scan, (0, 0))

                                 
        if etype == "reverse":
                                                      
            glitch_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            band_y = int((phase * 60) % HEIGHT)
            pygame.draw.rect(glitch_surf, (*tint, 50),
                             pygame.Rect(0, band_y, WIDTH, 6))
            pygame.draw.rect(glitch_surf, (*tint, 30),
                             pygame.Rect(0, (band_y + HEIGHT // 3) % HEIGHT, WIDTH, 3))
            screen.blit(glitch_surf, (0, 0))

        elif etype == "mirror":
                                      
            pygame.draw.line(screen, (*tint, 180),
                             (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 2)

        elif etype == "nullgrav":
                                    
            random.seed(int(phase * 10))
            pg_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for _ in range(30):
                px = random.randint(0, WIDTH)
                py = (random.randint(0, HEIGHT) + int(phase * 40)) % HEIGHT
                pg_surf.set_at((px, py), (*tint, 160))
            screen.blit(pg_surf, (0, 0))

                      
        if self.msg_timer > 0:
            font  = pygame.font.SysFont("arial", 20, bold=True)
            ratio = self.msg_timer / 120
            a     = int(min(255, 255 * ratio))
            surf  = font.render(self.message, True, tint)
            surf.set_alpha(a)
            screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 - 60))


                                                                               
                                                                   
                                                                               
class TemporalVisuals:
    def __init__(self):
        self._player_trail : list[dict] = []                       
        self._distort_phase  = 0.0
        self._glitch_offsets : list[tuple] = []
        self._glitch_timer   = 0
        self._aberration     = 0                                            

    def record_trail(self, player, intensity=1.0):
        if intensity < 0.05:
            return
        self._player_trail.append({
            "x": player.x, "y": player.y,
            "angle": player.angle,
            "age": 0,
            "alpha": int(160 * intensity)
        })
        if len(self._player_trail) > TRAIL_MAX_POINTS:
            self._player_trail.pop(0)

    def trigger_glitch(self, strength=1.0):
        n = int(6 * strength)
        self._glitch_offsets = [
            (random.randint(-int(12 * strength), int(12 * strength)),
             random.randint(-4, 4),
             random.randint(20, 80),                
             random.randint(0, HEIGHT))
            for _ in range(n)
        ]
        self._glitch_timer   = int(20 * strength)
        self._aberration     = int(10 * strength)

    def update(self, dilation_active: bool, dilation_ratio: float):
        self._distort_phase += 0.04
        for p in self._player_trail[:]:
            p["age"] += 1
            p["alpha"] -= TRAIL_FADE_RATE
            if p["alpha"] <= 0:
                self._player_trail.remove(p)
        if self._glitch_timer > 0:
            self._glitch_timer -= 1
            if random.random() < 0.4:
                self._glitch_offsets = [
                    (random.randint(-8, 8), ox[1], ox[2], ox[3])
                    for ox in self._glitch_offsets
                ]
        if self._aberration > 0:
            self._aberration = max(0, self._aberration - 1)

    def apply_pre_blit(self, scene: pygame.Surface, dilation_active: bool,
                       dilation_ratio: float, rewinding: bool) -> pygame.Surface:
        if rewinding:
                                                
            overlay = pygame.Surface(scene.get_size(), pygame.SRCALPHA)
            overlay.fill((30, 60, 220, 60))
            for y in range(0, HEIGHT, 3):
                overlay.fill((0, 0, 100, 35), pygame.Rect(0, y, WIDTH, 1))
            scene.blit(overlay, (0, 0))
            return scene

        if dilation_active and dilation_ratio > 0.05:
                                               
            scroll_amt = int(math.sin(self._distort_phase * 2) * 3 * dilation_ratio)
            if scroll_amt != 0:
                shifted = pygame.Surface(scene.get_size())
                shifted.blit(scene, (scroll_amt, 0))
                shifted.blit(scene, (scroll_amt - WIDTH, 0))
                scene = shifted

                                       
            tint = pygame.Surface(scene.get_size(), pygame.SRCALPHA)
            tint.fill((60, 200, 255, int(30 * dilation_ratio)))
            scene.blit(tint, (0, 0))

        return scene

    def apply_post_blit(self, screen: pygame.Surface, dilation_active: bool,
                        dilation_ratio: float, rewinding: bool):
                      
        if self._glitch_timer > 0:
            for (ox, oy, bh, by) in self._glitch_offsets:
                band = screen.subsurface(
                    pygame.Rect(max(0, -ox), by, min(WIDTH - abs(ox), WIDTH), min(bh, HEIGHT - by))
                ).copy()
                screen.blit(band, (ox, by))

                                           
        if self._aberration > 0:
            ab = self._aberration
            r_surf = screen.copy()
            b_surf = screen.copy()
            r_surf.fill((255, 140, 140), special_flags=pygame.BLEND_RGB_MULT)
            b_surf.fill((140, 140, 255), special_flags=pygame.BLEND_RGB_MULT)
            r_surf.set_alpha(80)
            b_surf.set_alpha(80)
            screen.blit(r_surf, (ab, 0))
            screen.blit(b_surf, (-ab, 0))

                                           
        if dilation_active and dilation_ratio < 0.25:
            pulse_a = int(abs(math.sin(self._distort_phase * 6)) * 60)
            warn = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            warn.fill((255, 50, 50, pulse_a))
            screen.blit(warn, (0, 0))

                            
        if rewinding:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((200, 220, 255, 40))
            screen.blit(flash, (0, 0))

    def draw_dilation_trail_overlay(self, screen):
        if not self._player_trail:
            return
                                                                           
        cx, cy = WIDTH // 2, HEIGHT // 2
        for i, p in enumerate(self._player_trail):
            a = max(0, p["alpha"] - i * 6)
            if a <= 0:
                continue
            bar_w = max(2, 40 - i * 2)
            bar_h = 3
            surf  = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
            surf.fill((120, 210, 255, a))
            screen.blit(surf, (cx - bar_w // 2 + random.randint(-4, 4),
                               cy + random.randint(-20, 20)))


                                                                               
                                                           
                                                                               
def draw_temporal_hud(screen, dilation: TimeDilation, rewind: TimeRewind,
                      echo: TemporalEcho, fracture: FractureZones,
                      ui_phase: float):
    font_s = pygame.font.SysFont("arial", 15, bold=True)
    font_t = pygame.font.SysFont("arial", 13)

    bar_w  = 140
    bar_h  = 12
    x0     = WIDTH - bar_w - 18
    y0     = HEIGHT - 200
    gap    = 22
    pulse  = 0.5 + 0.5 * math.sin(ui_phase * 2)

    abilities = [
        ("TIME DIL  [Q]", dilation.energy_ratio,
         (60, 200, 255), dilation.active),
        ("REWIND    [E]", rewind.cooldown_ratio,
         (200, 100, 255), rewind.rewinding),
        ("T-ECHO    [G]", echo.cooldown_ratio,
         (80, 255, 180), False),
    ]

    overlay = pygame.Surface((bar_w + 60, gap * len(abilities) + 36), pygame.SRCALPHA)
    overlay.fill((0, 10, 20, 160))
    pygame.draw.rect(overlay, (60, 140, 200, 100), overlay.get_rect(), 1, border_radius=6)
    screen.blit(overlay, (x0 - 8, y0 - 20))

    label_surf = font_t.render("TEMPORAL ABILITIES", True, (100, 180, 240))
    screen.blit(label_surf, (x0 - 4, y0 - 17))

    for i, (label, ratio, color, is_active) in enumerate(abilities):
        y = y0 + i * gap

                        
        pygame.draw.rect(screen, (20, 30, 40), (x0, y, bar_w, bar_h))
              
        fill_w = max(0, int(bar_w * ratio))
        pygame.draw.rect(screen, color, (x0, y, fill_w, bar_h))
                     
        if is_active:
            glow_a = int(80 + 80 * pulse)
            gsurf  = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
            gsurf.fill((*color, glow_a))
            screen.blit(gsurf, (x0, y))
                
        border_col = color if is_active else (60, 90, 110)
        pygame.draw.rect(screen, border_col, (x0, y, bar_w, bar_h), 1)

        label_surf = font_s.render(label, True,
                                   color if is_active else (160, 190, 210))
        screen.blit(label_surf, (x0 - label_surf.get_width() - 4, y - 1))

                         
    if fracture.active_effect and fracture.msg_timer > 0:
        ratio = fracture.msg_timer / 120
        a     = int(255 * min(1.0, ratio * 2))
        fc    = fracture.active_effect["tint"]
        fsurf = font_s.render(f"⚡ {fracture.active_effect['type'].upper()} ZONE",
                               True, fc)
        fsurf.set_alpha(a)
        screen.blit(fsurf, (x0, y0 + gap * len(abilities) + 6))
import math
import os
import random

import pygame

from core.settings import WIDTH, HEIGHT, HALF_FOV, FOV, NUM_RAYS, HALF_HEIGHT
from systems import audio


# ──────────────────────────────────────────────────────────────────────────
# ASTRAEUS COCKPIT DOGFIGHT
#
# On the pivotal levels (5, 10, 15) a console sits in the world. Interacting
# with it hands the player control of the Astraeus itself and drops them into
# a first-person space duel against a temporal fracture — the ship attacking
# itself. The camera sits inside the cockpit, looking forward: the fracture
# circles ahead in true 3D space (perspective projection, banking, growing
# and shrinking with depth) while the player dodges with the mouse and fires
# the forward guns. Destroying the fracture is required to clear these levels.
# ──────────────────────────────────────────────────────────────────────────
class ConsoleDogfight:
    SCHEDULED_LEVELS = {4, 9, 14}   # level files 5, 10, 15 (index 0-based)

    PLAYER_HP = 100.0
    ENEMY_HP = 700.0

    FIRE_COOLDOWN = 8
    BULLET_SPEED = 0.9          # world units / frame, fired straight ahead
    BULLET_DAMAGE = 35

    ENEMY_FIRE_MIN = 45
    ENEMY_FIRE_MAX = 85
    PROJECTILE_SPEED = 0.55     # world units / frame, converging on the player
    PROJECTILE_DAMAGE = 12

    END_TIME = 100          # frames of victory/defeat banner

    # ── 3D camera / world scale ───────────────────────────────────────────
    FOCAL = 380                     # perspective projection focal length (px)
    ENEMY_Z_MIN = 8.0               # nearest the fracture approaches
    ENEMY_Z_MAX = 30.0              # furthest it pulls away
    ENEMY_RADIUS = 2.2              # world-space hit radius of the fracture
    PLAYER_RADIUS = 1.8             # world-space hit radius of the Astraeus
    PX_RANGE = 4.5                  # lateral dodge range (world units)
    PY_RANGE = 3.0
    STEER_SENS = 0.015              # world units per mouse delta px
    DODGE_KEY_SPEED = 0.045         # world units per frame while a key is held
    SHIP_SCALE = 1.15               # base billboard size multiplier

    def __init__(self):
        self.active = False
        self.run_time = 0.0

        # Player: world-space hitbox at z=0, steered by the mouse.
        self.px = 0.0
        self.py = 0.0
        self.bank = 0.0
        self.player_hp = self.PLAYER_HP
        self.player_fire_cd = 0
        self.player_bullets = []
        self.muzzle = 0

        # Enemy: fracture circling ahead in 3D.
        self.enemy_x = 0.0
        self.enemy_y = 0.0
        self.enemy_z = 16.0
        self.enemy_hp = self.ENEMY_HP
        self.enemy_fire_cd = 50
        self.enemy_proj = []
        self.enemy_phase = 0.0
        self.enemy_bank = 0.0
        self._enemy_prev_x = 0.0
        self.enemy_hurt = 0
        self.player_hurt = 0

        self.end_state = None        # None | "victory" | "defeat"
        self.end_timer = 0
        self.victory = False
        self.points_awarded = False
        self.stars = []
        self._explosion = []

        self._assets = None
        self._init_stars()

    # ── cached art (built once) ───────────────────────────────────────────
    def _ensure_assets(self):
        if self._assets is not None:
            return self._assets
        ship = pygame.Surface((520, 220), pygame.SRCALPHA)
        hull = [(32, 110), (110, 68), (290, 55), (452, 92), (498, 112), (452, 132), (290, 165), (110, 152)]
        nose = [(28, 110), (92, 86), (92, 134)]
        wing_left = [(120, 82), (42, 48), (12, 56), (62, 100)]
        wing_right = [(120, 138), (42, 172), (12, 164), (62, 120)]
        engine = pygame.Rect(452, 95, 42, 30)
        pygame.draw.polygon(ship, (44, 10, 26), hull)
        pygame.draw.polygon(ship, (255, 70, 150), hull, 3)
        pygame.draw.polygon(ship, (255, 120, 220), nose)
        pygame.draw.polygon(ship, (255, 120, 220), wing_left)
        pygame.draw.polygon(ship, (255, 120, 220), wing_right)
        pygame.draw.rect(ship, (255, 70, 150), engine)
        for i in range(4):
            pygame.draw.line(ship, (255, 70, 150), (122 + i * 58, 92), (122 + i * 58, 128), 2)
            pygame.draw.circle(ship, (255, 70, 150), (170 + i * 40, 111), 4)

        cockpit = self._build_cockpit()
        self._assets = {"ship": ship, "cockpit": cockpit}
        return self._assets

    def _build_cockpit(self):
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dash_h = 96
        frame_t = 26

        # Window frame border.
        pygame.draw.rect(surf, (2, 4, 10, 235), (0, 0, WIDTH, frame_t))
        pygame.draw.rect(surf, (2, 4, 10, 235), (0, HEIGHT - dash_h, WIDTH, dash_h))
        pygame.draw.rect(surf, (2, 4, 10, 235), (0, 0, 18, HEIGHT))
        pygame.draw.rect(surf, (2, 4, 10, 235), (WIDTH - 18, 0, 18, HEIGHT))
        pygame.draw.line(surf, (40, 90, 130, 200), (0, frame_t), (WIDTH, frame_t), 2)

        # Corner struts converging toward the edges of the window.
        edge_col = (50, 120, 170, 255)
        tris = [
            [(0, 0), (150, 26), (26, 150)],
            [(WIDTH, 0), (WIDTH - 150, 26), (WIDTH - 26, 150)],
            [(0, HEIGHT), (150, HEIGHT - 26), (26, HEIGHT - 150)],
            [(WIDTH, HEIGHT), (WIDTH - 150, HEIGHT - 26), (WIDTH - 26, HEIGHT - 150)],
        ]
        for tri in tris:
            pygame.draw.polygon(surf, (3, 6, 12, 230), tri)
            pygame.draw.polygon(surf, edge_col, tri, 2)

        # Dashboard.
        pygame.draw.line(surf, (60, 150, 210, 255), (0, HEIGHT - dash_h), (WIDTH, HEIGHT - dash_h), 2)
        pygame.draw.line(surf, (10, 20, 34, 255), (0, HEIGHT - dash_h + 4), (WIDTH, HEIGHT - dash_h + 4), 1)
        for i in range(3):
            pw, ph = 150, 26
            px = 40 + i * 210
            py = HEIGHT - dash_h + 14
            pygame.draw.rect(surf, (6, 10, 18, 255), (px, py, pw, ph))
            pygame.draw.rect(surf, (70, 180, 255, 255), (px, py, pw, ph), 1)
            fill = int(pw * (0.35 + 0.4 * math.sin(i * 2.3)))
            pygame.draw.rect(surf, (50, 160, 255, 255), (px + 4, py + 6, fill, 6))
            pygame.draw.rect(surf, (50, 160, 255, 255), (px + 4, py + 16, fill // 2, 4))

        # Scanlines across the window only.
        for y in range(0, HEIGHT - dash_h, 4):
            a = 26 if (y // 4) % 2 == 0 else 7
            surf.fill((255, 255, 255, a), pygame.Rect(0, y, WIDTH, 2))

        # Glass sheen.
        sheen = pygame.Surface((WIDTH, HEIGHT - dash_h), pygame.SRCALPHA)
        sheen.fill((120, 200, 255, 0))
        pygame.draw.polygon(sheen, (160, 220, 255, 14), [(0, 0), (WIDTH, 0), (WIDTH * 0.45, HEIGHT - dash_h)])
        surf.blit(sheen, (0, 0))
        return surf

    def _init_stars(self):
        self.stars = []
        for _ in range(220):
            self._new_star()

    def _new_star(self):
        ang = random.uniform(0, math.pi * 2)
        rad = random.uniform(0.0, 14.0)
        self.stars.append({
            "x": math.cos(ang) * rad,
            "y": math.sin(ang) * rad * 0.75,
            "z": random.uniform(1.5, 40.0),
            "v": random.uniform(0.22, 0.55),
            "tw": random.uniform(1.5, 4.0),
            "ph": random.uniform(0, math.pi * 2),
        })

    def reset_for_level(self):
        self.victory = False
        self.points_awarded = False
        if self.active:
            self.active = False
            self.end_state = None

    # ── world helpers (called from game.py) ───────────────────────────────
    def find_near_console(self, consoles, player):
        if not consoles:
            return None
        for pos in consoles:
            dx = pos[0] - player.x
            dy = pos[1] - player.y
            if math.hypot(dx, dy) < 110:
                return pos
        return None

    def start(self, player):
        self.active = True
        self.run_time = 0.0
        self.px = 0.0
        self.py = 0.0
        self.bank = 0.0
        self.player_hp = self.PLAYER_HP
        self.player_fire_cd = 0
        self.player_bullets = []
        self.muzzle = 0
        self.enemy_x = 0.0
        self.enemy_y = 0.0
        self.enemy_z = 16.0
        self.enemy_hp = self.ENEMY_HP
        self.enemy_fire_cd = 50
        self.enemy_proj = []
        self.enemy_phase = random.uniform(0, 6.28)
        self.enemy_bank = 0.0
        self._enemy_prev_x = 0.0
        self.enemy_hurt = 0
        self.player_hurt = 0
        self.end_state = None
        self.end_timer = 0
        self._explosion = []
        self._init_stars()
        self._ensure_assets()

    # ── projection ────────────────────────────────────────────────────────
    def _project(self, x, y, z):
        if z <= 0.001:
            return None
        return (WIDTH / 2 + x * self.FOCAL / z, HEIGHT / 2 - y * self.FOCAL / z)

    # ── simulation ────────────────────────────────────────────────────────
    def update(self):
        if not self.active:
            return
        self.run_time += 1.0 / 60.0

        # Stars stream toward the camera (3D depth tunnel).
        for s in self.stars:
            s["z"] -= s["v"]
            if s["z"] < 1.0:
                ang = random.uniform(0, math.pi * 2)
                rad = random.uniform(0.0, 14.0)
                s["x"] = math.cos(ang) * rad
                s["y"] = math.sin(ang) * rad * 0.75
                s["z"] = random.uniform(30.0, 42.0)
                s["v"] = random.uniform(0.22, 0.55)

        if self.end_state:
            self.end_timer -= 1
            self._update_explosion()
            if self.end_timer <= 0:
                self.active = False
            return

        # Steering (dodge): mouse deltas plus WASD, both move the ship laterally.
        keys = pygame.key.get_pressed()
        rel_x, rel_y = pygame.mouse.get_rel()
        key_dx = (1.0 if keys[pygame.K_d] else 0.0) - (1.0 if keys[pygame.K_a] else 0.0)
        key_dy = (1.0 if keys[pygame.K_w] else 0.0) - (1.0 if keys[pygame.K_s] else 0.0)
        self.px += max(-1.2, min(1.2, rel_x * self.STEER_SENS)) + key_dx * self.DODGE_KEY_SPEED
        self.py += max(-1.2, min(1.2, -rel_y * self.STEER_SENS)) + key_dy * self.DODGE_KEY_SPEED
        self.px = max(-self.PX_RANGE, min(self.PX_RANGE, self.px))
        self.py = max(-self.PY_RANGE, min(self.PY_RANGE, self.py))
        self.bank += (self.px * 7.0 - self.bank) * 0.08

        # Firing: guns fixed forward.
        mouse = pygame.mouse.get_pressed(3)
        firing = bool(mouse[0]) or bool(keys[pygame.K_SPACE])
        if self.player_fire_cd > 0:
            self.player_fire_cd -= 1
        if firing and self.player_fire_cd <= 0:
            self.player_fire_cd = self.FIRE_COOLDOWN
            self.muzzle = 5
            self.player_bullets.append({
                "x": random.uniform(-0.15, 0.15),
                "y": random.uniform(-0.15, 0.15),
                "z": 1.0,
            })
            try:
                from core.settings import EFFECT_FILES
                path = EFFECT_FILES.get("laser")
                if path and os.path.exists(path):
                    audio.play_sound(path)
            except Exception:
                pass
        if self.muzzle > 0:
            self.muzzle -= 1

        # Bullets travel straight ahead; hit when crossing the fracture's depth.
        for b in self.player_bullets[:]:
            prev_z = b["z"]
            b["z"] += self.BULLET_SPEED
            if prev_z < self.enemy_z <= b["z"]:
                if math.hypot(b["x"] - self.enemy_x, b["y"] - self.enemy_y) < self.ENEMY_RADIUS:
                    self.enemy_hp -= self.BULLET_DAMAGE
                    self.enemy_hurt = 6
                    self.player_bullets.remove(b)
                    if self.enemy_hp <= 0:
                        self._start_victory()
                        return
                    continue
            if b["z"] > 45.0:
                self.player_bullets.remove(b)

        # Enemy 3D path: weave laterally and through depth, banking as it turns.
        prev_ex = self.enemy_x
        self.enemy_phase += 0.012
        self.enemy_z = self.ENEMY_Z_MIN + (self.ENEMY_Z_MAX - self.ENEMY_Z_MIN) * (0.5 + 0.5 * math.sin(self.enemy_phase * 0.9 + 1.3))
        self.enemy_x = math.sin(self.enemy_phase * 1.6) * (5.0 + 1.5 * math.sin(self.enemy_phase * 0.7))
        self.enemy_y = math.sin(self.enemy_phase * 2.1 + 0.8) * 3.0 + math.sin(self.enemy_phase * 0.55) * 1.0
        vx = (self.enemy_x - prev_ex) * 60.0
        bank_target = max(-45.0, min(45.0, vx * 1.4))
        self.enemy_bank += (bank_target - self.enemy_bank) * 0.12
        self._enemy_prev_x = prev_ex

        # Enemy firing: projectiles converge on the player's current position.
        if self.enemy_fire_cd > 0:
            self.enemy_fire_cd -= 1
        if self.enemy_fire_cd <= 0:
            self.enemy_fire_cd = random.randint(self.ENEMY_FIRE_MIN, self.ENEMY_FIRE_MAX)
            dx = self.px - self.enemy_x
            dy = self.py - self.enemy_y
            dz = 0.0 - self.enemy_z
            dist = math.hypot(math.hypot(dx, dy), dz) or 1.0
            self.enemy_proj.append({
                "x": self.enemy_x, "y": self.enemy_y, "z": self.enemy_z,
                "vx": dx / dist * self.PROJECTILE_SPEED,
                "vy": dy / dist * self.PROJECTILE_SPEED,
                "vz": dz / dist * self.PROJECTILE_SPEED,
            })

        for p in self.enemy_proj[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["z"] += p["vz"]
            if p["z"] <= 0.6:
                if math.hypot(p["x"] - self.px, p["y"] - self.py) < self.PLAYER_RADIUS:
                    self.player_hp -= self.PROJECTILE_DAMAGE
                    self.player_hurt = 8
                self.enemy_proj.remove(p)
                if self.player_hp <= 0:
                    self.end_state = "defeat"
                    self.end_timer = self.END_TIME
                    return

        if self.enemy_hurt > 0:
            self.enemy_hurt -= 1
        if self.player_hurt > 0:
            self.player_hurt -= 1

    def _start_victory(self):
        self.end_state = "victory"
        self.end_timer = self.END_TIME
        self.victory = True
        pos = self._project(self.enemy_x, self.enemy_y, self.enemy_z)
        cx, cy = (pos if pos else (WIDTH / 2, HEIGHT / 2))
        for _ in range(120):
            ang = random.uniform(0, math.pi * 2)
            sp = random.uniform(2, 9)
            self._explosion.append({
                "x": cx, "y": cy,
                "vx": math.cos(ang) * sp, "vy": math.sin(ang) * sp,
                "life": random.randint(20, 60),
                "size": random.randint(2, 7),
            })

    def _update_explosion(self):
        for p in self._explosion[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vx"] *= 0.94
            p["vy"] *= 0.94
            p["life"] -= 1
            if p["life"] <= 0:
                self._explosion.remove(p)

    # ── rendering ─────────────────────────────────────────────────────────
    def draw(self, screen):
        if not self.active:
            return
        self._ensure_assets()
        ship_sprite = self._assets["ship"]
        cockpit = self._assets["cockpit"]

        screen.fill((2, 3, 8))
        self._draw_star_tunnel(screen)

        enemy_pos = self._project(self.enemy_x, self.enemy_y, self.enemy_z)
        enemy_scale = self.FOCAL / max(0.001, self.enemy_z) * self.SHIP_SCALE / 100.0

        # Enemy projectiles (approaching, growing).
        for p in self.enemy_proj:
            proj = self._project(p["x"], p["y"], p["z"])
            if not proj:
                continue
            r = max(3, int(self.FOCAL * 0.10 / max(0.5, p["z"])))
            px, py = int(proj[0]), int(proj[1])
            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 70, 60, 90), (r * 2, r * 2), r * 2)
            screen.blit(glow, (px - r * 2, py - r * 2))
            pygame.draw.circle(screen, (255, 130, 90), (px, py), r)
            pygame.draw.circle(screen, (255, 240, 220), (px, py), max(1, r // 3))

        # Player bullets (retreating, shrinking).
        for b in self.player_bullets:
            proj = self._project(b["x"], b["y"], b["z"])
            if not proj:
                continue
            r = max(2, int(self.FOCAL * 0.05 / max(0.5, b["z"])))
            px, py = int(proj[0]), int(proj[1])
            pygame.draw.circle(screen, (120, 230, 255), (px, py), r)
            pygame.draw.circle(screen, (210, 250, 255), (px, py), max(1, r // 2))
            pygame.draw.line(screen, (90, 190, 255), (px, py), (px, py - r * 3), 2)

        # Explosion debris.
        for p in self._explosion:
            s = p["size"]
            surf = pygame.Surface((s * 2 + 2, s * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 120, 40), (s + 1, s + 1), s)
            surf.set_alpha(int(255 * (p["life"] / 60.0)))
            screen.blit(surf, (int(p["x"]) - s - 1, int(p["y"]) - s - 1))

        # Temporal fracture billboard (depth-scaled, banking, glitching).
        if self.end_state != "victory" and enemy_pos:
            self._draw_enemy(screen, ship_sprite, enemy_pos, enemy_scale)

        # Cockpit frame + dashboard (on top of the scene).
        screen.blit(cockpit, (0, 0))

        self._draw_weapon_flash(screen)
        self._draw_ui(screen, enemy_pos, enemy_scale)
        self._draw_reveals(screen)

        if self.end_state == "victory":
            self._draw_end_banner(screen, "TEMPORAL FRACTURE DESTROYED",
                                  "THE ASTRAEUS WAS FIGHTING ITSELF")
        elif self.end_state == "defeat":
            self._draw_end_banner(screen, "CONNECTION LOST",
                                  "FRACTURE REPOSITIONED — REACCESS THE CONSOLE")

    def _draw_star_tunnel(self, screen):
        cx, cy = WIDTH / 2, HEIGHT / 2
        for s in self.stars:
            z = s["z"]
            if z < 1.2:
                continue
            sx = cx + (s["x"] - self.px * 1.2) * self.FOCAL / z
            sy = cy + (s["y"] - self.py * 0.8) * self.FOCAL / z
            if sx < -30 or sx > WIDTH + 30 or sy < -30 or sy > HEIGHT + 30:
                continue
            twinkle = int((math.sin(self.run_time * s["tw"] + s["ph"]) + 1) * 0.5 * 100)
            size = max(1, int(1 + 3.0 * self.FOCAL / z * 0.08))
            b = min(255, 150 + twinkle)
            pygame.draw.circle(screen, (min(255, 90 + twinkle), min(255, 130 + twinkle), b),
                               (int(sx), int(sy)), size)

    def _draw_enemy(self, screen, sprite, pos, scale):
        glitch = random.random() < 0.22
        ox = random.randint(-9, 9) if glitch else 0
        oy = random.randint(-4, 4) if glitch else 0
        ex, ey = int(pos[0]) + ox, int(pos[1]) + oy

        glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 40, 120), (ex, ey), int(90 + 60 * scale))
        glow.set_alpha(55)
        screen.blit(glow, (0, 0))

        w = max(1, int(520 * scale))
        h = max(1, int(220 * scale))
        rendered = pygame.transform.smoothscale(sprite, (w, h))
        if self.enemy_hurt > 0:
            rendered.set_alpha(160)
        if abs(self.enemy_bank) > 0.1:
            rendered = pygame.transform.rotate(rendered, -self.enemy_bank)
        screen.blit(rendered, (int(ex - rendered.get_width() / 2), int(ey - rendered.get_height() / 2)))

        if self.enemy_hurt > 0:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 90))
            screen.blit(flash, (0, 0))

        label_font = pygame.font.SysFont("courier", 15, bold=True)
        lbl = label_font.render("TEMPORAL FRACTURE // ASTRAEUS-β", True, (255, 120, 190))
        screen.blit(lbl, (int(pos[0]) - lbl.get_width() // 2, int(pos[1]) - int(h * 0.55) - 8))

    def _draw_weapon_flash(self, screen):
        if self.muzzle <= 0:
            return
        m = self.muzzle / 5.0
        cx, cy = WIDTH // 2, HEIGHT // 2
        flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        r = int(150 * m)
        pygame.draw.circle(flash, (120, 220, 255, int(70 * m)), (cx, int(cy + 40)), r)
        screen.blit(flash, (0, 0))
        pygame.draw.circle(screen, (230, 250, 255), (cx, int(cy + 40)), int(10 * m))

    def _draw_ui(self, screen, enemy_pos, enemy_scale):
        font = pygame.font.SysFont("courier", 22, bold=True)
        small = pygame.font.SysFont("courier", 16)
        dash_h = 96

        # ── center firing reticle (with lock brackets) ─────────────────────
        cx, cy = WIDTH // 2, HEIGHT // 2
        pulse = 0.5 + 0.5 * math.sin(self.run_time * 6.0)
        locked = enemy_pos is not None and math.hypot(enemy_pos[0] - cx, enemy_pos[1] - cy) < 150
        col = (140, 255, 200) if locked else (150, 210, 235)
        ring = int(24 + 4 * pulse)
        pygame.draw.circle(screen, col, (cx, cy), ring, 2)
        pygame.draw.circle(screen, col, (cx, cy), 3, 2)
        for kx, ky, ox, oy in [(-1, 0, -1, 0), (1, 0, 0, 0), (0, -1, 0, -1), (0, 1, 0, 0)]:
            pygame.draw.line(screen, col, (cx + kx * (ring + 2), cy + ky * (ring + 2)),
                             (cx + ox * (ring + 2 + 12), cy + oy * (ring + 2 + 12)), 2)
        if locked:
            bx = int(enemy_pos[0])
            by = int(enemy_pos[1])
            ln = int(14 + 6 * pulse)
            bw = int(enemy_scale * 90)
            for sx, sy, dx, dy in [(-1, -1, 1, 0), (1, -1, -1, 0), (-1, 1, 1, 0), (1, 1, -1, 0)]:
                pygame.draw.line(screen, (255, 80, 120), (bx + sx * (bw + 4), by + sy * (bw + 4)),
                                 (bx + sx * (bw + 4) + dx * ln, by + sy * (bw + 4) + dy * ln), 2)
            lock = font.render("LOCK", True, (255, 120, 150))
            screen.blit(lock, (bx - lock.get_width() // 2, by - bw - 34))

        # ── enemy hull bar (top center) ────────────────────────────────────
        bar_w, bar_h = 360, 18
        ex, ey = WIDTH // 2 - bar_w // 2, 30
        pygame.draw.rect(screen, (40, 20, 30), (ex, ey, bar_w, bar_h))
        eratio = max(0, self.enemy_hp) / self.ENEMY_HP
        pygame.draw.rect(screen, (255, 70, 150), (ex, ey, int(bar_w * eratio), bar_h))
        pygame.draw.rect(screen, (255, 140, 200), (ex, ey, bar_w, bar_h), 1)
        e_lbl = font.render("TEMPORAL FRACTURE", True, (255, 130, 190))
        screen.blit(e_lbl, e_lbl.get_rect(center=(WIDTH // 2, 12)))

        # ── player hull bar (dashboard) ────────────────────────────────────
        bx, by = 24, HEIGHT - dash_h + 52
        pygame.draw.rect(screen, (30, 30, 40), (bx, by, 260, 16))
        ratio = max(0, self.player_hp) / self.PLAYER_HP
        color = (60, 220, 255) if ratio > 0.3 else (255, 90, 70)
        pygame.draw.rect(screen, color, (bx, by, int(260 * ratio), 16))
        hp_lbl = small.render("ASTRAEUS HULL", True, (150, 225, 255))
        screen.blit(hp_lbl, (bx, by - 18))

        # ── status readouts on the dashboard ───────────────────────────────
        threat = "HIGH" if self.enemy_proj else ("LOW" if self.end_state else "NONE")
        tcol = (255, 110, 90) if threat == "HIGH" else (140, 230, 160)
        status = font.render(f"THREAT: {threat}", True, tcol)
        screen.blit(status, (WIDTH // 2 - status.get_width() // 2, HEIGHT - dash_h + 30))

        hint = small.render("[MOUSE / WASD] DODGE   [CLICK / SPACE] FIRE", True, (150, 180, 210))
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 16))

        if self.end_state == "defeat":
            dmg = small.render(f"HULL CRITICAL — FINAL LINK AT {max(0, int(self.player_hp))}%", True, (255, 120, 90))
            screen.blit(dmg, (WIDTH // 2 - dmg.get_width() // 2, 80))

    def _draw_reveals(self, screen):
        t = self.run_time
        font = pygame.font.SysFont("courier", 30, bold=True)
        sub = pygame.font.SysFont("courier", 20, bold=True)

        if t < 3.2:
            line = font.render("LINK ACQUIRED — YOU ARE ASTRAEUS", True, (170, 230, 255))
            screen.blit(line, (WIDTH // 2 - line.get_width() // 2, int(HEIGHT * 0.62)))
        if 1.6 < t < 4.8:
            line = font.render("CONTACT: ASTRAEUS TEMPORAL FRACTURE", True, (255, 130, 190))
            screen.blit(line, (WIDTH // 2 - line.get_width() // 2, int(HEIGHT * 0.62) + 40))
        if 3.2 < t < 6.4:
            line = sub.render("IT IS ATTACKING YOU.", True, (255, 190, 160))
            screen.blit(line, (WIDTH // 2 - line.get_width() // 2, int(HEIGHT * 0.62) + 80))
            line2 = sub.render("IT IS YOU.", True, (255, 190, 160))
            screen.blit(line2, (WIDTH // 2 - line2.get_width() // 2, int(HEIGHT * 0.62) + 108))

    def _draw_end_banner(self, screen, title, subtext):
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        screen.blit(dim, (0, 0))

        font = pygame.font.SysFont("courier", 44, bold=True)
        sub = pygame.font.SysFont("courier", 24, bold=True)
        if self.end_state == "victory":
            color = (140, 240, 255)
        else:
            color = (255, 100, 80)
        line = font.render(title, True, color)
        screen.blit(line, (WIDTH // 2 - line.get_width() // 2, HEIGHT // 2 - 40))
        line2 = sub.render(subtext, True, (210, 220, 235))
        screen.blit(line2, (WIDTH // 2 - line2.get_width() // 2, HEIGHT // 2 + 14))


# ──────────────────────────────────────────────────────────────────────────
# WORLD-SPACE CONSOLE BILLBOARD
# ──────────────────────────────────────────────────────────────────────────
def draw_consoles(screen, consoles, player, depth_buffer, anim_time):
    from core.settings import TILE
    for pos in consoles:
        wx, wy = pos[0], pos[1]
        dx = wx - player.x
        dy = wy - player.y
        dist = math.hypot(dx, dy)

        theta = math.atan2(dy, dx)
        delta = (theta - player.angle) % (2 * math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi

        if not (-HALF_FOV < delta < HALF_FOV):
            continue

        screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
        size = min(2000 / (dist + 0.0001), 90)
        bob = math.sin(anim_time * 2.0) * 5

        x = screen_x - size // 2
        y = HALF_HEIGHT - size // 2 + bob

        ray_index = max(0, min(NUM_RAYS - 1, int(screen_x * NUM_RAYS / WIDTH)))
        if 0 <= ray_index < len(depth_buffer) and dist < depth_buffer[ray_index]:
            pulse = 0.5 + 0.5 * math.sin(anim_time * 3.0)
            glow = pygame.Surface((int(size), int(size)), pygame.SRCALPHA)
            pygame.draw.circle(glow, (40, 180, 255), (int(size // 2), int(size // 2)), int(size * 0.55))
            glow.set_alpha(int(90 + 70 * pulse))
            screen.blit(glow, (int(x), int(y)))

            panel_w = int(size * 0.7)
            panel_h = int(size * 0.9)
            px = int(x + size / 2 - panel_w / 2)
            py = int(y + size / 2 - panel_h / 2)
            pygame.draw.rect(screen, (12, 24, 44), (px, py, panel_w, panel_h), border_radius=4)
            pygame.draw.rect(screen, (90, 210, 255), (px, py, panel_w, panel_h), 2, border_radius=4)
            for i in range(4):
                bw = panel_w - 16
                bh = 4
                bx = px + 8
                by = py + 10 + i * 12
                fill = int(bw * (0.4 + 0.6 * abs(math.sin(anim_time * 1.5 + i))))
                pygame.draw.rect(screen, (60, 160, 255), (bx, by, fill, bh))


def draw_console_prompt(screen, font, near):
    if not near:
        return
    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.006)
    label = font.render("[E] ACCESS ASTRAEUS CONSOLE", True, (150, 230, 255))
    label.set_alpha(int(200 + 55 * pulse))
    rect = label.get_rect(center=(WIDTH // 2, HALF_HEIGHT + 60))
    screen.blit(label, rect)

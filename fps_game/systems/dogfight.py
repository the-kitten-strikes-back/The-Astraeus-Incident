import math
import random

import pygame

from core.settings import WIDTH, HEIGHT, HALF_FOV, FOV, NUM_RAYS, HALF_HEIGHT


# ──────────────────────────────────────────────────────────────────────────
# ASTRAEUS CONSOLE DOGFIGHT
#
# On the pivotal levels (5, 10, 15) a console sits in the world. Interacting
# with it hands the player control of the Astraeus itself and drops them into
# a pseudo-3D space duel against a temporal fracture — the ship attacking
# itself. Destroying the fracture is required to clear these levels.
# ──────────────────────────────────────────────────────────────────────────
class ConsoleDogfight:
    SCHEDULED_LEVELS = {4, 9, 14}   # level files 5, 10, 15 (index 0-based)

    PLAYER_HP = 100.0
    ENEMY_HP = 700.0

    FIRE_COOLDOWN = 8
    BULLET_SPEED = 16
    BULLET_DAMAGE = 35

    ENEMY_FIRE_MIN = 45
    ENEMY_FIRE_MAX = 85
    PROJECTILE_SPEED = 6.5
    PROJECTILE_DAMAGE = 12

    END_TIME = 100          # frames of victory/defeat banner

    def __init__(self):
        self.active = False
        self.run_time = 0.0
        self.player_x = WIDTH // 2
        self.player_y = HEIGHT - 150
        self.player_hp = self.PLAYER_HP
        self.player_fire_cd = 0
        self.player_bullets = []
        self.enemy_x = WIDTH // 2
        self.enemy_y = int(HEIGHT * 0.16)
        self.enemy_hp = self.ENEMY_HP
        self.enemy_fire_cd = 40
        self.enemy_proj = []
        self.enemy_phase = 0.0
        self.enemy_hurt = 0
        self.player_hurt = 0
        self.end_state = None        # None | "victory" | "defeat"
        self.end_timer = 0
        self.victory = False
        self.points_awarded = False
        self.stars = []
        self._explosion = []
        self._init_stars()

    def _init_stars(self):
        self.stars = []
        for _ in range(220):
            ang = random.uniform(0, math.pi * 2)
            rad = random.uniform(0.02, 1.0)
            self.stars.append({
                "a": ang,
                "r": rad,
                "v": random.uniform(0.0025, 0.008),
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
        self.player_x = WIDTH // 2
        self.player_y = HEIGHT - 150
        self.player_hp = self.PLAYER_HP
        self.player_fire_cd = 0
        self.player_bullets = []
        self.enemy_x = WIDTH // 2
        self.enemy_y = int(HEIGHT * 0.16)
        self.enemy_hp = self.ENEMY_HP
        self.enemy_fire_cd = 50
        self.enemy_proj = []
        self.enemy_phase = random.uniform(0, 6.28)
        self.enemy_hurt = 0
        self.player_hurt = 0
        self.end_state = None
        self.end_timer = 0
        self._explosion = []
        self._init_stars()

    # ── simulation ────────────────────────────────────────────────────────
    def update(self):
        if not self.active:
            return
        self.run_time += 1.0 / 60.0

        # Stars drift outward (pseudo-3D tunnel).
        for s in self.stars:
            s["r"] += s["v"]
            if s["r"] > 1.0:
                s["r"] = random.uniform(0.02, 0.15)
                s["a"] = random.uniform(0, math.pi * 2)

        if self.end_state:
            self.end_timer -= 1
            self._update_explosion()
            if self.end_timer <= 0:
                self.active = False
            return

        # Mouse steering.
        rel_x, rel_y = pygame.mouse.get_rel()
        self.player_x += rel_x * 2.2
        self.player_y += rel_y * 2.2
        self.player_x = max(70, min(WIDTH - 70, self.player_x))
        self.player_y = max(int(HEIGHT * 0.55), min(HEIGHT - 110, self.player_y))

        # Firing.
        mouse = pygame.mouse.get_pressed(3)
        keys = pygame.key.get_pressed()
        firing = mouse[0] or keys[pygame.K_SPACE]
        if self.player_fire_cd > 0:
            self.player_fire_cd -= 1
        if firing and self.player_fire_cd <= 0:
            self.player_fire_cd = self.FIRE_COOLDOWN
            self.player_bullets.append({
                "x": self.player_x + random.uniform(-6, 6),
                "y": self.player_y - 40,
            })
            try:
                import os
                from core.settings import EFFECT_FILES
                path = EFFECT_FILES.get("laser")
                if path and os.path.exists(path):
                    pygame.mixer.Sound(path).play()
            except Exception:
                pass

        for b in self.player_bullets[:]:
            b["y"] -= self.BULLET_SPEED
            if b["y"] < -20:
                self.player_bullets.remove(b)
                continue
            if math.hypot(b["x"] - self.enemy_x, b["y"] - self.enemy_y) < 52:
                self.enemy_hp -= self.BULLET_DAMAGE
                self.enemy_hurt = 6
                self.player_bullets.remove(b)
                if self.enemy_hp <= 0:
                    self._start_victory()
                    return

        # Enemy movement: sine weave across the void.
        self.enemy_phase += 0.012
        self.enemy_x = WIDTH // 2 + math.sin(self.enemy_phase * 1.7) * (WIDTH * 0.32)
        self.enemy_y = int(HEIGHT * 0.16) + math.sin(self.enemy_phase * 2.3) * 40

        # Enemy firing.
        if self.enemy_fire_cd > 0:
            self.enemy_fire_cd -= 1
        if self.enemy_fire_cd <= 0:
            self.enemy_fire_cd = random.randint(self.ENEMY_FIRE_MIN, self.ENEMY_FIRE_MAX)
            ang = math.atan2(self.player_y - self.enemy_y, self.player_x - self.enemy_x)
            self.enemy_proj.append({
                "x": self.enemy_x + random.uniform(-8, 8),
                "y": self.enemy_y + 46,
                "vx": math.cos(ang) * self.PROJECTILE_SPEED,
                "vy": math.sin(ang) * self.PROJECTILE_SPEED,
            })

        for p in self.enemy_proj[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["y"] > HEIGHT + 20 or p["x"] < -20 or p["x"] > WIDTH + 20:
                self.enemy_proj.remove(p)
                continue
            if math.hypot(p["x"] - self.player_x, p["y"] - self.player_y) < 36:
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
        for _ in range(120):
            ang = random.uniform(0, math.pi * 2)
            sp = random.uniform(2, 9)
            self._explosion.append({
                "x": self.enemy_x, "y": self.enemy_y,
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
        screen.fill((2, 3, 8))

        self._draw_star_tunnel(screen)

        # Enemy first (behind player).
        if self.end_state != "victory":
            self._draw_enemy_ship(screen)

        # Projectiles.
        for p in self.enemy_proj:
            pygame.draw.circle(screen, (255, 70, 60), (int(p["x"]), int(p["y"])), 7)
        for b in self.player_bullets:
            pygame.draw.circle(screen, (120, 230, 255), (int(b["x"]), int(b["y"])), 5)
            pygame.draw.circle(screen, (200, 250, 255), (int(b["x"]), int(b["y"])), 2)

        # Explosion debris.
        for p in self._explosion:
            s = p["size"]
            surf = pygame.Surface((s * 2 + 2, s * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 120, 40), (s + 1, s + 1), s)
            surf.set_alpha(int(255 * (p["life"] / 60.0)))
            screen.blit(surf, (int(p["x"]) - s - 1, int(p["y"]) - s - 1))

        if self.end_state != "defeat":
            self._draw_player_ship(screen)

        self._draw_hud(screen)
        self._draw_reveals(screen)

        if self.end_state == "victory":
            self._draw_end_banner(screen, "TEMPORAL FRACTURE DESTROYED",
                                  "THE ASTRAEUS WAS FIGHTING ITSELF")
        elif self.end_state == "defeat":
            self._draw_end_banner(screen, "CONNECTION LOST",
                                  "FRACTURE REPOSITIONED — REACCESS THE CONSOLE")

    def _draw_star_tunnel(self, screen):
        cx, cy = WIDTH // 2, HEIGHT // 2
        max_r = max(WIDTH, HEIGHT) * 0.62
        for s in self.stars:
            rad = s["r"]
            dist = rad * max_r
            sx = cx + math.cos(s["a"]) * dist
            sy = cy + math.sin(s["a"]) * dist
            twinkle = int((math.sin(self.run_time * s["tw"] + s["ph"]) + 1) * 0.5 * 120)
            size = max(1, int(1 + rad * 2.4))
            b = min(255, 160 + twinkle)
            pygame.draw.circle(screen, (min(255, 80 + twinkle), min(255, 110 + twinkle), b),
                               (int(sx), int(sy)), size)

    def _draw_ship(self, screen, cx, cy, scale, hull_col, edge_col, nose_col, alpha=255):
        ship = pygame.Surface((520, 220), pygame.SRCALPHA)
        hull = [(32, 110), (110, 68), (290, 55), (452, 92), (498, 112), (452, 132), (290, 165), (110, 152)]
        nose = [(28, 110), (92, 86), (92, 134)]
        wing_left = [(120, 82), (42, 48), (12, 56), (62, 100)]
        wing_right = [(120, 138), (42, 172), (12, 164), (62, 120)]
        engine = pygame.Rect(452, 95, 42, 30)

        pygame.draw.polygon(ship, hull_col, hull)
        pygame.draw.polygon(ship, edge_col, hull, 3)
        pygame.draw.polygon(ship, nose_col, nose)
        pygame.draw.polygon(ship, nose_col, wing_left)
        pygame.draw.polygon(ship, nose_col, wing_right)
        pygame.draw.rect(ship, edge_col, engine)
        for i in range(4):
            pygame.draw.line(ship, edge_col, (122 + i * 58, 92), (122 + i * 58, 128), 2)
            pygame.draw.circle(ship, edge_col, (170 + i * 40, 111), 4)

        ship = pygame.transform.smoothscale(
            ship, (max(1, int(520 * scale)), max(1, int(220 * scale))))
        ship.set_alpha(alpha)
        screen.blit(ship, (int(cx - ship.get_width() // 2), int(cy - ship.get_height() // 2)))

    def _draw_player_ship(self, screen):
        scale = 0.62
        glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(glow, (60, 140, 255), (int(self.player_x), int(self.player_y)), 120)
        glow.set_alpha(50)
        screen.blit(glow, (0, 0))
        self._draw_ship(screen, self.player_x, self.player_y, scale,
                        (14, 26, 60), (70, 190, 255), (120, 90, 220))
        # Engine flare.
        fl = random.randint(30, 70)
        pygame.draw.circle(screen, (fl, fl, 200), (int(self.player_x), int(self.player_y + 68 * scale)), 8)

    def _draw_enemy_ship(self, screen):
        # Temporal fracture: a glitching magenta mirror of the player.
        depth_wave = 0.78 + 0.10 * math.sin(self.enemy_phase * 3.0)
        scale = depth_wave
        glitch = random.random() < 0.22
        ox = random.randint(-9, 9) if glitch else 0
        oy = random.randint(-4, 4) if glitch else 0

        glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 40, 120), (int(self.enemy_x), int(self.enemy_y)), 130)
        glow.set_alpha(55)
        screen.blit(glow, (0, 0))

        alpha = 255 if self.enemy_hurt <= 0 else 160
        self._draw_ship(screen, self.enemy_x + ox, self.enemy_y + oy, scale,
                        (44, 10, 26), (255, 70, 150), (255, 120, 220), alpha=alpha)

        if self.enemy_hurt > 0:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 90))
            screen.blit(flash, (0, 0))

        label_font = pygame.font.SysFont("courier", 15, bold=True)
        lbl = label_font.render("TEMPORAL FRACTURE // ASTRAEUS-β", True, (255, 120, 190))
        screen.blit(lbl, (self.enemy_x - lbl.get_width() // 2, self.enemy_y - 70 * scale))

    def _draw_hud(self, screen):
        font = pygame.font.SysFont("courier", 22, bold=True)
        small = pygame.font.SysFont("courier", 16)

        # Player ship bar.
        bar_w, bar_h = 360, 18
        bx, by = 24, HEIGHT - 64
        pygame.draw.rect(screen, (30, 30, 40), (bx, by, bar_w, bar_h))
        ratio = max(0, self.player_hp) / self.PLAYER_HP
        color = (60, 220, 255) if ratio > 0.3 else (255, 90, 70)
        pygame.draw.rect(screen, color, (bx, by, int(bar_w * ratio), bar_h))
        hp_lbl = font.render("ASTRAEUS", True, (150, 225, 255))
        screen.blit(hp_lbl, (bx, by - 28))

        # Enemy bar.
        ex, ey = WIDTH - 24 - bar_w, 28
        pygame.draw.rect(screen, (40, 20, 30), (ex, ey, bar_w, bar_h))
        eratio = max(0, self.enemy_hp) / self.ENEMY_HP
        pygame.draw.rect(screen, (255, 70, 150), (ex, ey, int(bar_w * eratio), bar_h))
        pygame.draw.rect(screen, (255, 140, 200), (ex, ey, bar_w, bar_h), 1)
        e_lbl = font.render("TEMPORAL FRACTURE", True, (255, 130, 190))
        e_rect = e_lbl.get_rect(topright=(WIDTH - 24, 6))
        screen.blit(e_lbl, e_rect)

        # Controls hint.
        hint = small.render("[MOUSE] STEER   [CLICK / SPACE] FIRE", True, (150, 180, 210))
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 34))

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

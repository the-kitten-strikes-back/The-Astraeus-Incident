import math
import random

import pygame

from core.settings import WIDTH, HEIGHT, TILE
from utils.math_utils import is_wall


# ──────────────────────────────────────────────────────────────────────────
# GRAVITY TILT EVENT
#
# At roughly every second level the entire ship heels over: red alerts flare
# everywhere and "gravity" shifts toward the tilted wall, dragging the player,
# enemies and loose sprites across the deck until they pile against it.
# ──────────────────────────────────────────────────────────────────────────
class GravityTilt:
    IDLE = "idle"
    WARNING = "warning"
    ACTIVE = "active"
    RECOVERY = "recovery"

    SCHEDULED_LEVELS = {1, 3, 6, 8, 11, 13, 16, 18}

    WARNING_TIME = 75          # frames (~1.2s)
    ACTIVE_TIME = 320          # frames (~5.3s)
    RECOVERY_TIME = 90         # frames (~1.5s)

    MAX_PULL = 1.4             # tiles-ish per frame at peak

    def __init__(self):
        self.phase = self.IDLE
        self.phase_timer = 0
        self.target_angle = 0.0
        self.angle = 0.0
        self._armed_level = False
        self._delay = 0
        self._pull = 0.0
        self._debris = []
        self._phase_acc = 0.0

    # ── scheduling ────────────────────────────────────────────────────────
    def enter_level(self, level_index):
        self.phase = self.IDLE
        self.phase_timer = 0
        self.angle = 0.0
        self._pull = 0.0
        self._armed_level = level_index in self.SCHEDULED_LEVELS
        if self._armed_level:
            self._delay = random.randint(480, 1500)   # 8-25s in
            self.target_angle = random.choice([-1, 1]) * random.uniform(9.0, 13.0)

    # ── behaviour ─────────────────────────────────────────────────────────
    @property
    def gravity_dir(self):
        """Unit vector sprites are dragged toward (rotated with the tilt)."""
        if self.angle >= 0:
            return (1.0, 0.0)
        return (-1.0, 0.0)

    def is_active(self):
        return self.phase in (self.WARNING, self.ACTIVE, self.RECOVERY)

    def update(self):
        self._phase_acc += 0.06
        if self.phase == self.IDLE:
            if self._armed_level:
                self._delay -= 1
                if self._delay <= 0:
                    self.phase = self.WARNING
                    self.phase_timer = self.WARNING_TIME
                    self._spawn_debris(40)
            return

        self.phase_timer -= 1

        if self.phase == self.WARNING:
            t = 1.0 - self.phase_timer / self.WARNING_TIME
            self.angle = self.target_angle * self._smoothstep(min(1.0, t))
            if self.phase_timer <= 0:
                self.phase = self.ACTIVE
                self.phase_timer = self.ACTIVE_TIME
                self._spawn_debris(70)

        elif self.phase == self.ACTIVE:
            self.angle = self.target_angle + math.sin(self._phase_acc * 4) * 1.2
            self._pull = 0.5 + 0.5 * math.sin(self._phase_acc * 2.2) * 0.55
            if random.random() < 0.12:
                self._spawn_debris(3)
            if self.phase_timer <= 0:
                self.phase = self.RECOVERY
                self.phase_timer = self.RECOVERY_TIME

        elif self.phase == self.RECOVERY:
            t = 1.0 - self.phase_timer / self.RECOVERY_TIME
            self.angle = self.target_angle * (1.0 - self._smoothstep(min(1.0, t)))
            if self.phase_timer <= 0:
                self.phase = self.IDLE
                self._pull = 0.0
                self._armed_level = False

        self._update_debris()

    def _smoothstep(self, t):
        return t * t * (3 - 2 * t)

    # ── physics push (called by game.py) ──────────────────────────────────
    def pull_magnitude(self):
        if self.phase != self.ACTIVE:
            return 0.0
        return self.MAX_PULL * (0.6 + 0.4 * self._pull)

    def apply_to_entity(self, ent, world, doors, scale=1.0):
        gx, gy = self.gravity_dir
        mag = self.pull_magnitude() * scale
        if mag <= 0:
            return False
        dx = gx * mag
        dy = gy * mag
        moved = False
        if abs(dx) > 0.001:
            nx = ent["x"] + dx
            if not is_wall(nx, ent["y"], world, TILE, doors):
                ent["x"] = nx
                moved = True
            else:
                ent["_tilt_pile"] = True
        if abs(dy) > 0.001:
            ny = ent["y"] + dy
            if not is_wall(ent["x"], ny, world, TILE, doors):
                ent["y"] = ny
                moved = True
            else:
                ent["_tilt_pile"] = True
        return moved

    def apply_to_player(self, player, world, doors, scale=1.0):
        gx, gy = self.gravity_dir
        mag = self.pull_magnitude() * scale
        if mag <= 0:
            return
        if abs(gx) > 0.001:
            nx = player.x + gx * mag
            if not is_wall(nx, player.y, world, TILE, doors):
                player.x = nx
        if abs(gy) > 0.001:
            ny = player.y + gy * mag
            if not is_wall(player.x, ny, world, TILE, doors):
                player.y = ny

    # ── screen-space debris ───────────────────────────────────────────────
    def _spawn_debris(self, count):
        gx, gy = self.gravity_dir
        for _ in range(count):
            self._debris.append({
                "x": random.uniform(0, WIDTH),
                "y": random.uniform(0, HEIGHT),
                "w": random.randint(2, 10),
                "h": random.randint(2, 8),
                "v": random.uniform(4, 11),
                "a": random.randint(60, 200),
            })

    def _update_debris(self):
        gx, gy = self.gravity_dir
        for d in self._debris[:]:
            d["x"] += gx * d["v"]
            d["y"] += gy * d["v"] * 0.6
            d["a"] -= 3
            if d["a"] <= 0 or not (0 <= d["x"] <= WIDTH and 0 <= d["y"] <= HEIGHT):
                self._debris.remove(d)

    # ── overlay ───────────────────────────────────────────────────────────
    def draw_overlay(self, screen, phase):
        if not self.is_active():
            return
        t = self._phase_acc
        pulse = 0.5 + 0.5 * math.sin(t * 9.0)

        red = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        red.fill((255, 20, 20, int(18 + 22 * pulse)))
        screen.blit(red, (0, 0))

        # Hazard band on the gravity-side edge.
        gx, gy = self.gravity_dir
        band_a = int(90 + 90 * pulse)
        band = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if gx > 0:
            pygame.draw.rect(band, (255, 0, 0), (WIDTH - 34, 0, 34, HEIGHT))
        elif gx < 0:
            pygame.draw.rect(band, (255, 0, 0), (0, 0, 34, HEIGHT))
        elif gy > 0:
            pygame.draw.rect(band, (255, 0, 0), (0, HEIGHT - 34, WIDTH, 34))
        else:
            pygame.draw.rect(band, (255, 0, 0), (0, 0, WIDTH, 34))
        band.set_alpha(band_a)
        screen.blit(band, (0, 0))

        # Corner brackets + flashing frame.
        inset = int(10 + 5 * pulse)
        c = int(140 + 115 * pulse)
        pygame.draw.rect(screen, (c, 20, 20), (inset, inset, WIDTH - inset * 2, HEIGHT - inset * 2), 6)

        # Scanlines.
        scan = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 4):
            a = int(30 * pulse) if (y // 4) % 2 == 0 else 8
            scan.fill((255, 40, 40, a), pygame.Rect(0, y, WIDTH, 2))
        screen.blit(scan, (0, 0))

        # Debris streaks.
        for d in self._debris:
            surf = pygame.Surface((d["w"] + 2, d["h"] + 2), pygame.SRCALPHA)
            pygame.draw.rect(surf, (255, 80, 60), (0, 0, d["w"], d["h"]))
            surf.set_alpha(min(255, d["a"]))
            screen.blit(surf, (int(d["x"]), int(d["y"])))

        # Big flashing title.
        font = pygame.font.SysFont("courier", 46, bold=True)
        flash = int(120 + 135 * pulse)
        title = font.render("RED ALERT", True, (flash, 30, 30))
        title_rect = title.get_rect(center=(WIDTH // 2, 60))
        screen.blit(title, title_rect)

        sub = pygame.font.SysFont("courier", 26, bold=True)
        sub_txt = sub.render("GRAVITY SHEAR // BRACE FOR TILT", True, (255, 130, 120))
        screen.blit(sub_txt, (WIDTH // 2 - sub_txt.get_width() // 2, 104))

        # Warning text near bottom.
        warn = sub.render("STRUCTURAL INTEGRITY AT RISK", True, (255, 110, 100))
        warn_rect = warn.get_rect(center=(WIDTH // 2, HEIGHT - 60))
        screen.blit(warn, warn_rect)


# ──────────────────────────────────────────────────────────────────────────
# ZERO GRAVITY EVENT
#
# Roughly every five levels the deck loses gravity for 30 seconds. The
# player and every sprite drift and fight while floating, then everything
# slams back down to the floor when gravity returns.
# ──────────────────────────────────────────────────────────────────────────
class ZeroGravity:
    FLOAT_TIME = 1800          # 30s @ 60fps
    FALL_TIME = 70             # ~1.2s

    SCHEDULED_LEVELS = {2, 7, 12, 17}

    def __init__(self):
        self.active = False
        self.timer = 0
        self.falling = False
        self.fall_timer = 0
        self._float_phase = 0.0
        self._particles = []

    # ── scheduling ────────────────────────────────────────────────────────
    def enter_level(self, level_index):
        self.active = level_index in self.SCHEDULED_LEVELS
        self.timer = self.FLOAT_TIME
        self.falling = False
        self.fall_timer = 0
        self._particles = []
        if self.active:
            for _ in range(90):
                self._particles.append([
                    random.randint(0, WIDTH),
                    random.randint(0, HEIGHT),
                    random.uniform(-0.4, 0.4),
                    random.uniform(-0.6, 0.2),
                ])

    @property
    def is_zero_g(self):
        return self.active

    @property
    def is_falling(self):
        return self.falling

    def remaining_seconds(self):
        return max(0.0, self.timer / 60.0)

    def speed_scale(self):
        if self.active and not self.falling:
            return 0.55
        return 1.0

    # ── player thrusters (absolute W/A/S/D) ───────────────────────────────
    def move_player(self, player, world, doors, speed_scale=1.0):
        keys = pygame.key.get_pressed()
        tx = 0.0
        ty = 0.0
        if keys[pygame.K_a]:
            tx -= 1.0
        if keys[pygame.K_d]:
            tx += 1.0
        if keys[pygame.K_w]:
            ty -= 1.0
        if keys[pygame.K_s]:
            ty += 1.0

        mag = math.hypot(tx, ty)
        if mag > 0:
            tx /= mag
            ty /= mag

        thrust = 6.5 * speed_scale
        px = getattr(player, "zg_vx", 0.0)
        py = getattr(player, "zg_vy", 0.0)
        px += tx * thrust * 0.18
        py += ty * thrust * 0.18
        px *= 0.94
        py *= 0.94
        player.zg_vx = px
        player.zg_vy = py

        if abs(px) > 0.001:
            nx = player.x + px
            if not is_wall(nx, player.y, world, TILE, doors):
                player.x = nx
            else:
                player.zg_vx = 0.0
        if abs(py) > 0.001:
            ny = player.y + py
            if not is_wall(player.x, ny, world, TILE, doors):
                player.y = ny
            else:
                player.zg_vy = 0.0

        player.current_speed = math.hypot(px, py)
        player.move_amount = min(1.0, player.current_speed / max(1.0, player.speed * 0.5))

    # ── drifting sprites ──────────────────────────────────────────────────
    def apply_enemy_float(self, enemy, world, doors):
        self._float_phase += 0.02
        phase = enemy.get("_zg_phase", random.random() * 6.28318)
        enemy["_zg_phase"] = phase + 0.035
        drift = math.sin(enemy["_zg_phase"]) * 0.35
        if abs(drift) > 0.001:
            ny = enemy["y"] + drift
            if not is_wall(enemy["x"], ny, world, TILE, doors):
                enemy["y"] = ny
        drift_x = math.cos(enemy["_zg_phase"] * 0.6) * 0.18
        if abs(drift_x) > 0.001:
            nx = enemy["x"] + drift_x
            if not is_wall(nx, enemy["y"], world, TILE, doors):
                enemy["x"] = nx

    def apply_sprite_float(self, sprite, world, doors):
        phase = sprite.get("_zg_phase", random.random() * 6.28318)
        sprite["_zg_phase"] = phase + 0.03
        drift = math.sin(phase * 0.9) * 0.28
        ny = sprite["y"] + drift
        if not is_wall(sprite["x"], ny, world, TILE, doors):
            sprite["y"] = ny

    # ── falling back to the deck ──────────────────────────────────────────
    def fall(self):
        self.falling = True
        self.fall_timer = self.FALL_TIME

    def update(self, player, enemies, world, doors, health_packs, weapon_pickups, speed_scale=1.0):
        if not self.active:
            return

        self._float_phase += 0.04
        for p in self._particles:
            p[0] += p[2]
            p[1] += p[3]
            if p[0] < 0 or p[0] > WIDTH:
                p[2] *= -1
            if p[1] < 0 or p[1] > HEIGHT:
                p[3] *= -1

        if self.falling:
            self.fall_timer -= 1
            g = 0.9
            # Player slams down.
            vy = getattr(player, "zg_fall_vy", 0.0)
            vy = min(6.0, vy + g)
            player.zg_fall_vy = vy
            if not is_wall(player.x, player.y + vy, world, TILE, doors):
                player.y += vy
            else:
                player.zg_fall_vy = 0.0
            # Enemies fall.
            for e in enemies:
                ev = e.get("_zg_fall_vy", 0.0)
                ev = min(6.0, ev + g)
                e["_zg_fall_vy"] = ev
                if not is_wall(e["x"], e["y"] + ev, world, TILE, doors):
                    e["y"] += ev
                else:
                    e["_zg_fall_vy"] = 0.0
            # Loose sprites fall.
            for spr in list(health_packs) + list(weapon_pickups):
                sv = spr.get("_zg_fall_vy", 0.0)
                sv = min(6.0, sv + g)
                spr["_zg_fall_vy"] = sv
                if not is_wall(spr["x"], spr["y"] + sv, world, TILE, doors):
                    spr["y"] += sv
                else:
                    spr["_zg_fall_vy"] = 0.0
            if self.fall_timer <= 0:
                self.active = False
                self.falling = False
            return

        # Floating drift for the whole world.
        self.timer -= 1
        if self.timer <= 0:
            self.fall()
            return

        for enemy in enemies:
            if enemy["alive"]:
                self.apply_enemy_float(enemy, world, doors)
        for pack in health_packs:
            self.apply_sprite_float(pack, world, doors)
        for pickup in weapon_pickups:
            self.apply_sprite_float(pickup, world, doors)

    # ── HUD ───────────────────────────────────────────────────────────────
    def draw_hud(self, screen, ui_phase):
        if not self.active:
            return
        pulse = 0.5 + 0.5 * math.sin(ui_phase * 3.0)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((60, 160, 255, int(12 + 10 * pulse)))
        screen.blit(overlay, (0, 0))

        for p in self._particles:
            surf = pygame.Surface((5, 5), pygame.SRCALPHA)
            pygame.draw.circle(surf, (150, 215, 255), (2, 2), 2)
            surf.set_alpha(int(60 + 60 * pulse))
            screen.blit(surf, (int(p[0]) - 2, int(p[1]) - 2))

        font = pygame.font.SysFont("courier", 40, bold=True)
        sub = pygame.font.SysFont("courier", 22, bold=True)

        title = font.render("ZERO GRAVITY", True, (160, 220, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 46))

        remaining = self.remaining_seconds()
        timer_txt = sub.render(f"GRAVITY RESTORED IN {remaining:04.1f}s", True, (200, 235, 255))
        screen.blit(timer_txt, (WIDTH // 2 - timer_txt.get_width() // 2, 96))

        hint = sub.render("W/S/A/D — THRUSTERS  //  FIGHT IN THE VOID", True, (150, 200, 240))
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 128))

        if self.falling:
            warn = font.render("GRAVITY RESTORED", True, (255, 255, 255))
            screen.blit(warn, (WIDTH // 2 - warn.get_width() // 2, HEIGHT // 2 - 40))

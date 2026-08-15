import math
import random

import pygame

from core.settings import HALF_FOV, WIDTH, FOV, NUM_RAYS, HALF_HEIGHT, TILE
from utils.math_utils import is_wall
from systems import audio


# ── Grenade type definitions ──────────────────────────────────────────────────
GRENADE_DEFS = {
    "space": {
        "key":         "Z",
        "label":       "VOID",
        "color":       (80,  200, 255),   # cyan
        "throw_speed": 14,
        "fuse":        50,
        "radius":      130,
        "icon":        "◎",
        "cooldown":    60,
        "description": "Slows enemies in radius",
    },
    "smoke": {
        "key":         "X",
        "label":       "SMOKE",
        "color":       (160, 170, 190),   # grey-blue
        "throw_speed": 12,
        "fuse":        30,
        "radius":      150,
        "icon":        "≋",
        "cooldown":    80,
        "description": "Obscures vision zone",
    },
    "stun": {
        "key":         "C",
        "label":       "STUN",
        "color":       (255, 220,  50),   # amber
        "throw_speed": 13,
        "fuse":        35,
        "radius":      140,
        "icon":        "⚡",
        "cooldown":    100,
        "description": "Stuns enemies in radius",
    },
    "nuclear": {
        "key":         "V",
        "label":       "NOVA",
        "color":       (255,  80,  60),   # red-orange
        "throw_speed": 10,
        "fuse":        65,
        "radius":      250,
        "icon":        "☢",
        "cooldown":    180,
        "description": "Massive damage + stun",
    },
}

# Draw order for the HUD slots
HUD_ORDER = ["space", "smoke", "stun", "nuclear"]


class GrenadeSystem:
    def __init__(self):
        self.grenades = []
        self.smokes   = []
        self.explosions = []          # visual-only explosion particles

        self.cooldowns = {k: 0 for k in GRENADE_DEFS}

        # Persistent fonts (created once)
        self._font_label  = None
        self._font_key    = None
        self._font_desc   = None
        self._fonts_ready = False

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._font_label = pygame.font.SysFont("courier", 13, bold=True)
            self._font_key   = pygame.font.SysFont("courier", 11, bold=True)
            self._font_desc  = pygame.font.SysFont("courier", 10)
            self._fonts_ready = True

    # ── throwing ──────────────────────────────────────────────────────────────

    def try_throw(self, grenade_type, player):
        if grenade_type not in GRENADE_DEFS:
            return False
        if self.cooldowns[grenade_type] > 0:
            return False

        defn = GRENADE_DEFS[grenade_type]
        self.cooldowns[grenade_type] = defn["cooldown"]

        self.grenades.append({
            "type":   grenade_type,
            "x":      player.x,
            "y":      player.y,
            "angle":  player.angle,
            "speed":  defn["throw_speed"],
            "fuse":   defn["fuse"],
            "radius": defn["radius"],
            "age":    0,
        })
        return True

    # ── update ────────────────────────────────────────────────────────────────

    def update(self, world, doors, enemies, time_scale):
        events = {"shake": 0, "flash": 0, "chroma": 0, "zoom": 0}

        # Tick cooldowns
        for key in self.cooldowns:
            if self.cooldowns[key] > 0:
                self.cooldowns[key] -= 1

        # Update grenades
        for grenade in self.grenades[:]:
            grenade["age"] += 1

            # Fuse ticks with time_scale (so dilation slows grenades too)
            effective_fuse_drain = max(0.1, time_scale)
            grenade["fuse"] -= effective_fuse_drain

            if grenade["fuse"] <= 0:
                self._explode(grenade, enemies, events)
                try:
                    import os
                    explosion_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sounds", "effects", "explosion.mp3")
                    if os.path.exists(explosion_path):
                        audio.play_sound(explosion_path)
                except Exception:
                    pass
                self.grenades.remove(grenade)
                continue

            if time_scale == 0.0:
                continue

            nx = grenade["x"] + math.cos(grenade["angle"]) * grenade["speed"] * time_scale
            ny = grenade["y"] + math.sin(grenade["angle"]) * grenade["speed"] * time_scale

            if is_wall(nx, ny, world, TILE, doors):
                grenade["speed"] = 0
                grenade["fuse"]  = min(grenade["fuse"], 15)
            else:
                grenade["x"] = nx
                grenade["y"] = ny

            # Decelerate (friction)
            grenade["speed"] = max(0.0, grenade["speed"] - 0.4 * time_scale)

        # Update smoke clouds
        for smoke in self.smokes[:]:
            smoke["timer"] -= 1
            smoke["radius"] = min(smoke["max_radius"],
                                  smoke["radius"] + 0.8)   # expand over time
            if smoke["timer"] <= 0:
                self.smokes.remove(smoke)

        # Update explosion particles
        for p in self.explosions[:]:
            p["x"]    += p["vx"]
            p["y"]    += p["vy"]
            p["life"] -= 1
            p["vx"]   *= 0.92
            p["vy"]   *= 0.92
            if p["life"] <= 0:
                self.explosions.remove(p)

        return events

    # ── explosion logic ───────────────────────────────────────────────────────

    def _explode(self, grenade, enemies, events):
        gtype  = grenade["type"]
        radius = grenade["radius"]
        defn   = GRENADE_DEFS[gtype]
        color  = defn["color"]

        # Spawn explosion particles
        particle_count = {"space": 20, "smoke": 8, "stun": 28, "nuclear": 50}
        for _ in range(particle_count.get(gtype, 16)):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.5, 6.0)
            self.explosions.append({
                "x":    grenade["x"],
                "y":    grenade["y"],
                "vx":   math.cos(angle) * speed,
                "vy":   math.sin(angle) * speed,
                "life": random.randint(18, 50),
                "max_life": 50,
                "color": color,
                "size": random.randint(2, 6),
            })

        # Smoke leaves a persistent cloud
        if gtype == "smoke":
            self.smokes.append({
                "x":          grenade["x"],
                "y":          grenade["y"],
                "radius":     40,
                "max_radius": radius,
                "timer":      180,
                "color":      color,
            })
            events["flash"] = max(events["flash"], 2)
            return

        # Damage + status effects for all other types
        for enemy in enemies:
            dx   = enemy["x"] - grenade["x"]
            dy   = enemy["y"] - grenade["y"]
            dist = math.hypot(dx, dy)

            if dist <= radius and enemy["alive"]:
                falloff = max(0.15, 1.0 - dist / radius)

                if gtype == "space":
                    enemy["health"]    -= int(40 * falloff)
                    enemy["slow_timer"] = max(enemy.get("slow_timer", 0), 100)

                elif gtype == "stun":
                    enemy["health"]    -= int(20 * falloff)
                    enemy["stun_timer"] = max(enemy.get("stun_timer", 0), 100)

                elif gtype == "nuclear":
                    enemy["health"]    -= int(220 * falloff)
                    enemy["stun_timer"] = max(enemy.get("stun_timer", 0), 130)

                if enemy["health"] <= 0:
                    enemy["alive"] = False

        # Screen feedback
        if gtype == "space":
            events["shake"] = max(events["shake"], 7)
            events["flash"] = max(events["flash"], 4)
            events["chroma"] = max(events["chroma"], 7)
        elif gtype == "stun":
            events["flash"] = max(events["flash"], 5)
            events["chroma"] = max(events["chroma"], 5)
            events["shake"] = max(events["shake"], 5)
        elif gtype == "nuclear":
            events["shake"] = max(events["shake"], 18)
            events["flash"] = max(events["flash"], 12)
            events["chroma"] = max(events["chroma"], 14)
            events["zoom"]  = max(events["zoom"], 0.10)

    # ── drawing ───────────────────────────────────────────────────────────────

    def draw_grenades(self, screen, player, depth_buffer, anim_time=0.0):
        """Draw in-flight grenades, smoke clouds, and explosion particles."""

        # Explosion particles (2-D overlay — always visible, no depth test)
        for p in self.explosions:
            ratio = p["life"] / p["max_life"]
            alpha = int(220 * ratio)
            r, g, b = p["color"]
            size  = max(1, int(p["size"] * ratio))
            surf  = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (r, g, b, alpha), (size, size), size)
            # Project particle into 3-D view
            self._draw_projected(screen, player, depth_buffer,
                                 p["x"], p["y"], size * 2, p["color"],
                                 alpha=alpha, depth_scale=0.5)

        # Smoke clouds
        for smoke in self.smokes:
            pulse = 1.0 + 0.12 * math.sin(anim_time * 1.8)
            draw_r = smoke["radius"] * pulse
            self._draw_projected(screen, player, depth_buffer,
                                 smoke["x"], smoke["y"],
                                 draw_r, smoke["color"], alpha=65)

        # In-flight grenades
        for grenade in self.grenades:
            defn   = GRENADE_DEFS[grenade["type"]]
            color  = defn["color"]

            # Fuse urgency — flash faster as fuse expires
            fuse_ratio = max(0.0, grenade["fuse"] / defn["fuse"])
            flash_freq = 4.0 + (1.0 - fuse_ratio) * 10.0
            visible    = (math.sin(anim_time * flash_freq) > -0.3)
            if not visible:
                continue

            # Size pulses as fuse runs low
            base_size = 14 + int((1.0 - fuse_ratio) * 10)
            self._draw_projected(screen, player, depth_buffer,
                                 grenade["x"], grenade["y"],
                                 base_size, color, alpha=230)

    def _draw_projected(self, screen, player, depth_buffer,
                        wx, wy, size_base, color, alpha=255, depth_scale=1.0):
        """Billboard-project a world-space circle into screen space."""
        dx   = wx - player.x
        dy   = wy - player.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return

        theta = math.atan2(dy, dx)
        delta = (theta - player.angle) % (2 * math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi

        if not (-HALF_FOV < delta < HALF_FOV):
            return

        screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
        size     = min(2000 / (dist + 0.0001), size_base)
        sx       = screen_x - size // 2
        sy       = HALF_HEIGHT - size // 2

        ray_index = max(0, min(NUM_RAYS - 1, int(screen_x * NUM_RAYS / WIDTH)))
        if ray_index >= len(depth_buffer):
            return
        if dist * depth_scale >= depth_buffer[ray_index]:
            return

        isize = max(1, int(size))
        surf  = pygame.Surface((isize, isize), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*color, min(255, alpha)),
                           (isize // 2, isize // 2), isize // 2)
        screen.blit(surf, (int(sx), int(sy)))


    def draw_hud(self, screen, ui_phase):
        """
        Four grenade slots in the bottom-left corner.
        Each slot shows:
          • Icon + label
          • Cooldown bar (fills left→right as it recharges)
          • [KEY] binding
          • Dim overlay when on cooldown
        """
        self._ensure_fonts()

        SLOT_W    = 72
        SLOT_H    = 58
        SLOT_PAD  = 6
        MARGIN_X  = 18
        MARGIN_Y  = 110          # from bottom of screen
        HEIGHT = screen.get_height()

        total_w = len(HUD_ORDER) * (SLOT_W + SLOT_PAD) - SLOT_PAD
        start_x = MARGIN_X
        start_y = HEIGHT - MARGIN_Y - SLOT_H

        pulse = 0.5 + 0.5 * math.sin(ui_phase * 2.2)

        for i, gtype in enumerate(HUD_ORDER):
            defn   = GRENADE_DEFS[gtype]
            cd     = self.cooldowns[gtype]
            cd_max = defn["cooldown"]
            ready  = (cd == 0)

            sx = start_x + i * (SLOT_W + SLOT_PAD)
            sy = start_y

            color  = defn["color"]
            dim_color = tuple(max(0, c // 3) for c in color)

            # ── Slot background ───────────────────────────────────────────
            bg = pygame.Surface((SLOT_W, SLOT_H), pygame.SRCALPHA)
            bg_alpha = 180 if ready else 100
            bg.fill((8, 12, 20, bg_alpha))
            pygame.draw.rect(bg, (*( color if ready else dim_color ), 160),
                             bg.get_rect(), 1, border_radius=4)
            screen.blit(bg, (sx, sy))

            # ── Icon ──────────────────────────────────────────────────────
            icon_font = pygame.font.SysFont("segoeui", 20)
            icon_col  = color if ready else dim_color
            icon_surf = icon_font.render(defn["icon"], True, icon_col)
            if ready:
                # Subtle glow pulse on ready icons
                icon_surf.set_alpha(200 + int(55 * pulse))
            else:
                icon_surf.set_alpha(130)
            screen.blit(icon_surf,
                        (sx + SLOT_W // 2 - icon_surf.get_width() // 2,
                         sy + 5))

            # ── Label ─────────────────────────────────────────────────────
            label_col  = color if ready else dim_color
            label_surf = self._font_label.render(defn["label"], True, label_col)
            label_surf.set_alpha(220 if ready else 120)
            screen.blit(label_surf,
                        (sx + SLOT_W // 2 - label_surf.get_width() // 2,
                         sy + 27))

            # ── Cooldown bar ──────────────────────────────────────────────
            bar_x = sx + 4
            bar_y = sy + SLOT_H - 14
            bar_w = SLOT_W - 8
            bar_h = 5

            pygame.draw.rect(screen, (20, 28, 40), (bar_x, bar_y, bar_w, bar_h))

            if ready:
                fill_w = bar_w
                bar_col = color
            else:
                ratio  = 1.0 - cd / cd_max
                fill_w = int(bar_w * ratio)
                bar_col = tuple(max(0, c - 60) for c in color)

            if fill_w > 0:
                pygame.draw.rect(screen, bar_col, (bar_x, bar_y, fill_w, bar_h))

            pygame.draw.rect(screen, (*( color if ready else dim_color ), 120),
                             (bar_x, bar_y, bar_w, bar_h), 1)

            # ── Key binding ───────────────────────────────────────────────
            key_col  = (200, 200, 200) if ready else (90, 90, 90)
            key_surf = self._font_key.render(f"[{defn['key']}]", True, key_col)
            screen.blit(key_surf,
                        (sx + SLOT_W // 2 - key_surf.get_width() // 2,
                         sy + SLOT_H - 12))

            # ── Cooldown overlay + remaining time ─────────────────────────
            if not ready:
                overlay = pygame.Surface((SLOT_W, SLOT_H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 70))
                screen.blit(overlay, (sx, sy))

                secs_left = cd / 60.0
                cd_surf   = self._font_label.render(
                    f"{secs_left:.1f}s", True, (180, 180, 180)
                )
                cd_surf.set_alpha(200)
                screen.blit(cd_surf,
                            (sx + SLOT_W // 2 - cd_surf.get_width() // 2,
                             sy + SLOT_H // 2 - cd_surf.get_height() // 2))

            # ── "READY" flash when cooldown just expired ──────────────────
            if ready and cd_max > 0:
                # We can't detect the exact frame cd hit 0, but we can flash
                # for a brief window by checking if fill is full and pulsing
                if pulse > 0.85:
                    glow = pygame.Surface((SLOT_W, SLOT_H), pygame.SRCALPHA)
                    glow.fill((*color, 18))
                    screen.blit(glow, (sx, sy))
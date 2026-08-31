import math
import random

import pygame

from core.settings import (
    WIDTH, HEIGHT,
    ENTITY_WARP_DECAY,
    ENTITY_WARP_GLITCH_BANDS,
    ENTITY_WARP_ABERRATION_MIN,
    ENTITY_WARP_STREAK_MIN,
)

ABERRATION_MAX_PX = 12


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class EntityTimeWarpFX:
    """Whole-screen "fabric of time" distortion driven by the Entity's motion.

    The fight code feeds intensity via spike()/direct floors and keeps
    boss_screen_pos updated; apply() warps the fully composed frame:
      - horizontal glitch-band displacement
      - RGB chromatic aberration split
      - expanding lens ripples from the Entity's screen position
      - radial smear streaks
      - lingering spacetime crack lines
      - teleport implosion convergence + subtle scanline shimmer
    """

    def __init__(self):
        self.intensity = 0.0
        self.boss_screen_pos = None
        self._ripples = []
        self._cracks = []
        self._bands = []
        self._streaks = []
        self._implosion = None
        self._shimmer = None
        self._phase = 0.0

    @property
    def active(self):
        return self.intensity > 0.02 or bool(self._cracks) or bool(self._implosion)

    def spike(self, amount, boss_pos=None):
        self.intensity = min(2.4, self.intensity + amount)
        if boss_pos is not None:
            self.boss_screen_pos = boss_pos
            self.spawn_ripple(boss_pos[0], boss_pos[1], strength=min(1.0, amount))

    def spawn_ripple(self, x, y, strength=1.0):
        self._ripples.append({
            "x": x, "y": y,
            "r": 10.0,
            "vr": 480.0 + 720.0 * strength,
            "life": 0.55,
            "max": 0.55,
        })
        if len(self._ripples) > 6:
            self._ripples.pop(0)

    def trigger_cracks(self, n=3, origin=None):
        for _ in range(n):
            if origin is not None:
                ox, oy = origin
                ox += random.uniform(-60, 60)
                oy += random.uniform(-60, 60)
            else:
                ox = random.uniform(WIDTH * 0.15, WIDTH * 0.85)
                oy = random.uniform(HEIGHT * 0.15, HEIGHT * 0.85)
            pts = [(ox, oy)]
            a = random.uniform(0, math.tau)
            x, y = ox, oy
            for _s in range(random.randint(4, 8)):
                a += random.uniform(-0.7, 0.7)
                step = random.uniform(40, 150)
                x += math.cos(a) * step
                y += math.sin(a) * step
                pts.append((x, y))
            self._cracks.append({"pts": pts, "life": 2.2, "max": 2.2,
                                 "w": random.choice((1, 1, 2))})
        if len(self._cracks) > 18:
            del self._cracks[:len(self._cracks) - 18]

    def implosion(self, pos, dur=0.22):
        self._implosion = {"x": pos[0], "y": pos[1], "life": dur, "max": dur}

    def update(self, dt, ambient=0.0):
        self._phase += dt
        self.intensity = max(ambient, self.intensity - ENTITY_WARP_DECAY * dt)

        for rp in self._ripples[:]:
            rp["r"] += rp["vr"] * dt
            rp["life"] -= dt
            if rp["life"] <= 0:
                self._ripples.remove(rp)

        for ck in self._cracks[:]:
            ck["life"] -= dt
            if ck["life"] <= 0:
                self._cracks.remove(ck)

        for st in self._streaks[:]:
            st["life"] -= dt
            if st["life"] <= 0:
                self._streaks.remove(st)

        if self._implosion is not None:
            self._implosion["life"] -= dt
            if self._implosion["life"] <= 0:
                self._implosion = None

        inten = self.intensity
        target_bands = int(min(ENTITY_WARP_GLITCH_BANDS, inten * ENTITY_WARP_GLITCH_BANDS))
        while len(self._bands) < target_bands:
            self._bands.append({
                "y": random.randint(0, HEIGHT),
                "h": random.randint(8, 64),
                "dx": 0,
            })
        while len(self._bands) > target_bands:
            self._bands.pop()
        max_off = int(6 + 22 * min(2.0, inten))
        for b in self._bands:
            b["dx"] = random.randint(-max_off, max_off)

        if inten >= ENTITY_WARP_STREAK_MIN and self.boss_screen_pos:
            if random.random() < min(0.9, inten * dt * 14):
                ang = random.uniform(0, math.tau)
                self._streaks.append({
                    "a": ang,
                    "len": random.uniform(120, 420),
                    "life": random.uniform(0.12, 0.3),
                    "max": 0.3,
                })
        if len(self._streaks) > 16:
            del self._streaks[:len(self._streaks) - 16]

    # ── rendering ─────────────────────────────────────────────────────────

    def _get_shimmer(self):
        if self._shimmer is None:
            sh = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for y in range(0, HEIGHT, 4):
                sh.fill((120, 180, 200, 13), pygame.Rect(0, y, WIDTH, 1))
            self._shimmer = sh
        return self._shimmer

    def apply(self, screen):
        inten = self.intensity

        if self._implosion is not None:
            im = self._implosion
            f = 1.0 - (im["life"] / im["max"])
            cx, cy = int(im["x"]), int(im["y"])
            reach = int(30 + 260 * (1.0 - f))
            alpha = _clamp(int(f * 230), 0, 255)
            col = (200, 60, 70, alpha)
            for i in range(12):
                a = math.tau * i / 12 + f * 2.2
                r_out = reach * (0.35 + 0.65 * ((i * 37) % 10) / 10.0)
                x1 = cx + math.cos(a) * reach
                y1 = cy + math.sin(a) * reach * 0.85
                x2 = cx + math.cos(a) * r_out
                y2 = cy + math.sin(a) * r_out * 0.85
                pygame.draw.line(screen, col, (x1, y1), (x2, y2), 2)
            ring_r = reach * (1.05 - f * 0.55)
            pygame.draw.circle(screen, (170, 40, 50, alpha // 2),
                               (cx, cy), int(ring_r), 3)

        for rp in self._ripples:
            f = rp["life"] / rp["max"]
            a = _clamp(int(150 * f), 0, 255)
            r = int(rp["r"])
            if r > 4 and self.boss_screen_pos:
                wob = int(math.sin(self._phase * 24 + rp["x"]) * 3 * inten)
                pygame.draw.circle(screen, (150, 220, 235, a // 2),
                                   (rp["x"], rp["y"] + wob), r, 2)
                pygame.draw.circle(screen, (255, 60, 60, a),
                                   (rp["x"], rp["y"]), r + 4 + wob, 1)

        if inten >= ENTITY_WARP_STREAK_MIN and self.boss_screen_pos:
            bx, by = self.boss_screen_pos
            a_base = _clamp(int(90 * inten), 0, 160)
            for st in self._streaks:
                f = st["life"] / st["max"]
                inner = 40 + 260 * (1.0 - f)
                outer = inner + st["len"]
                col = (190, 80, 80, _clamp(int(a_base * f), 0, 255))
                pygame.draw.line(
                    screen, col,
                    (bx + math.cos(st["a"]) * inner, by + math.sin(st["a"]) * inner),
                    (bx + math.cos(st["a"]) * outer, by + math.sin(st["a"]) * outer),
                    2,
                )

        for ck in self._cracks:
            f = ck["life"] / ck["max"]
            a = _clamp(int(200 * min(1.0, f * 2.5)), 0, 255)
            shadow = [(p[0] + 2, p[1] + 2) for p in ck["pts"]]
            pygame.draw.lines(screen, (40, 0, 10, a // 2), False, shadow, ck["w"] + 1)
            core = (235, 225, 235, a) if f > 0.7 else (255, 90, 80, a)
            pygame.draw.lines(screen, core, False, ck["pts"], ck["w"])

        if self._bands and inten > 0.08:
            sw, sh = screen.get_size()
            for b in self._bands:
                y, h, dx = b["y"], b["h"], b["dx"]
                if h <= 0 or y + h > sh or abs(dx) < 1:
                    continue
                sx = max(0, -dx)
                w = min(sw - abs(dx), sw)
                if w <= 0:
                    continue
                try:
                    band = screen.subsurface(pygame.Rect(sx, y, w, h)).copy()
                except ValueError:
                    continue
                screen.blit(band, (dx, y))

        shimmer_a = _clamp(int((inten - 0.35) * 60), 0, 90)
        if shimmer_a > 3 and (inten >= 1.2 or int(self._phase * 30) % 2 == 0):
            sh_surf = self._get_shimmer()
            sh_surf.set_alpha(shimmer_a)
            screen.blit(sh_surf, (0, 0))

    def apply_entity_split(self, screen, rendered, center):
        """Chromatic ghosting of just the Entity's own canvas.

        Cheap alternative to whole-frame aberration: two tinted, downscaled
        copies of the Entity render blitted with a small horizontal offset,
        so red/cyan fringes peek out around its silhouette when time warps.
        """
        if rendered is None or self.intensity < ENTITY_WARP_ABERRATION_MIN:
            return
        if isinstance(rendered, tuple):
            canvas = rendered[0]
        else:
            canvas = rendered
        inten = min(2.4, self.intensity)
        cw, ch = canvas.get_size()
        scale = min(1.0, 420.0 / max(1, cw))
        gw = max(2, int(cw * scale))
        gh = max(2, int(ch * scale))
        base = pygame.transform.smoothscale(canvas, (gw, gh)) \
            if scale < 1.0 else canvas
        red = base.copy()
        red.fill((255, 70, 70), special_flags=pygame.BLEND_RGB_MULT)
        cyan = base.copy()
        cyan.fill((70, 140, 255), special_flags=pygame.BLEND_RGB_MULT)
        a = _clamp(int(26 + inten * 20), 0, 78)
        red.set_alpha(a)
        cyan.set_alpha(a)
        cx, cy = int(center[0]), int(center[1])
        ox = int(2 + inten * 5)
        left, top = cx - gw // 2, cy - gh // 2
        screen.blit(red, (left + ox, top))
        screen.blit(cyan, (left - ox, top))

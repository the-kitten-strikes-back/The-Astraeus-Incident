import math
import random

import pygame


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class EntityForm:
    """Shared procedural renderer for THE ENTITY.

    One visual identity used by both the typing fight and the in-world final
    boss fight: a colossal writhing void-mass with a giant slit-pupil eye,
    crown of horns, hanging tendrils and a broken reality halo.

    render() builds a viewport-clipped SRCALPHA canvas; blit() stamps it onto
    a target surface (with optional scanline-ghost distortion); draw() is the
    one-call convenience wrapper.
    """

    def __init__(self, seed=7):
        rng = random.Random(seed)
        self._verts = 26
        self._wob_phase = [rng.uniform(0, math.tau) for _ in range(self._verts)]
        self._wob_speed = [rng.uniform(0.5, 1.5) for _ in range(self._verts)]
        self._wob_amt = [rng.uniform(0.09, 0.22) for _ in range(self._verts)]
        self._horn_len = [rng.uniform(0.55, 1.05) for _ in range(12)]
        self._glyph_angles = [rng.uniform(0, math.tau) for _ in range(16)]
        self._glyph_len = [rng.uniform(0.45, 1.0) for _ in range(16)]
        self._tendril_phase = [rng.uniform(0, math.tau) for _ in range(9)]
        self._tendril_speed = [rng.uniform(1.1, 2.3) for _ in range(9)]
        self._tendril_len = [rng.uniform(0.55, 1.05) for _ in range(9)]
        self._extra_eye_blink = [rng.uniform(0.0, 10.0) for _ in range(8)]
        self._vein_wobble = [rng.uniform(-0.35, 0.35) for _ in range(7)]
        self._blink_seed = rng.uniform(0.0, 10.0)

    @staticmethod
    def body_radius(size):
        return max(2.0, size * 0.42)

    def _edge_radius(self, i, t, anger):
        speed = self._wob_speed[i] * (1.0 + anger * 0.8)
        return 1.0 + self._wob_amt[i] * math.sin(self._wob_phase[i] + t * speed)

    def _mass_points(self, cx, cy, r, t, anger):
        pts = []
        step = math.tau / self._verts
        for i in range(self._verts):
            a = step * i + t * 0.05
            rr = r * self._edge_radius(i, t, anger)
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        return pts

    @staticmethod
    def _shift(color, shift):
        if not shift:
            return color
        return (
            _clamp(color[0] + shift[0], 0, 255),
            _clamp(color[1] + shift[1], 0, 255),
            _clamp(color[2] + shift[2], 0, 255),
        )

    def _blink(self, t, offset):
        cyc = (t * 0.19 + offset) % 1.0
        if cyc > 0.94:
            f = (cyc - 0.94) / 0.06
            return math.sin(f * math.pi)
        return 0.0

    # ── public API ────────────────────────────────────────────────────────

    def render(self, screen, cx, cy, size, t, *, angle=0.0, anger=0.0,
               hp_ratio=1.0, moving=0.0, eye_open=1.0, extra_eyes=0.0,
               mode="full", color_shift=None):
        """Build the Entity frame. Returns (canvas, left, top) or None."""
        if size < 6 or not screen:
            return None
        r = self.body_radius(size)
        if mode == "clone":
            up = down = side = int(r * 1.45)
        else:
            up = int(r * 1.95)
            down = int(r * 2.15)
            side = int(r * 1.95)
        left = max(int(cx - side), 0)
        top = max(int(cy - up), 0)
        right = min(int(cx + side), screen.get_width())
        bottom = min(int(cy + down), screen.get_height())
        w, h = right - left, bottom - top
        if w < 2 or h < 2:
            return None
        canvas = pygame.Surface((w, h), pygame.SRCALPHA)
        lcx, lcy = cx - left, cy - top
        if mode != "clone":
            self._draw_halo(canvas, lcx, lcy, r, t, anger, color_shift)
        self._draw_tendrils(canvas, lcx, lcy, r, t, moving, anger, color_shift)
        self._draw_mass(canvas, lcx, lcy, r, t, anger, color_shift)
        if mode != "clone":
            self._draw_horns(canvas, lcx, lcy, r, t, anger, color_shift)
        self._draw_eye(canvas, lcx, lcy, r, t, angle, anger, hp_ratio,
                       eye_open, extra_eyes, color_shift)
        if hp_ratio < 0.35 and mode != "clone":
            self._draw_core_cracks(canvas, lcx, lcy, r, t, hp_ratio, color_shift)
        return canvas, left, top

    @staticmethod
    def blit(screen, rendered, alpha_mult=1.0, ghost=0.0, pos=None):
        if not rendered:
            return
        canvas, left, top = rendered
        if pos is not None:
            left, top = int(pos[0]), int(pos[1])
        alpha = _clamp(int(255 * alpha_mult), 0, 255)
        if alpha <= 0:
            return
        if ghost > 0.01:
            cw, ch = canvas.get_size()
            band = max(8, ch // 40)
            y = 0
            while y < ch:
                bh = min(band, ch - y)
                dx = int(random.uniform(-14, 14) * ghost)
                try:
                    piece = canvas.subsurface((0, y, cw, bh)).copy()
                except ValueError:
                    break
                piece.set_alpha(int(alpha * 0.6))
                screen.blit(piece, (left + dx, top + y))
                y += bh
        else:
            canvas.set_alpha(alpha if alpha < 255 else None)
            screen.blit(canvas, (left, top))

    def draw(self, screen, cx, cy, size, t, *, alpha_mult=1.0, ghost=0.0, **kw):
        rendered = self.render(screen, cx, cy, size, t, **kw)
        self.blit(screen, rendered, alpha_mult=alpha_mult, ghost=ghost)
        return rendered

    # ── components ────────────────────────────────────────────────────────

    def _draw_halo(self, canvas, cx, cy, r, t, anger, shift):
        arcs = (
            (1.20, 0.34, (150, 30, 42), 85),
            (1.42, -0.21, (118, 22, 34), 65),
            (1.66, 0.13, (92, 15, 26), 46),
        )
        width = max(1, int(1 + anger * 2))
        for mul, speed, col, base_a in arcs:
            rr = r * mul
            c = (*self._shift(col, shift), _clamp(int(base_a + anger * 70), 0, 255))
            segs, steps = 9, 5
            gap = math.tau / segs
            span = gap * 0.58
            off = t * speed
            for s in range(segs):
                start = off + s * gap
                pts = [
                    (cx + math.cos(start + span * (k / steps)) * rr,
                     cy + math.sin(start + span * (k / steps)) * rr)
                    for k in range(steps + 1)
                ]
                pygame.draw.lines(canvas, c, False, pts, width)
        gc = (*self._shift((170, 40, 52), shift), _clamp(int(80 + anger * 80), 0, 255))
        rot = t * 0.11
        for i, ga in enumerate(self._glyph_angles):
            aa = ga + rot
            r1 = r * 1.32
            r2 = r1 + r * 0.15 * self._glyph_len[i]
            pygame.draw.line(
                canvas, gc,
                (cx + math.cos(aa) * r1, cy + math.sin(aa) * r1),
                (cx + math.cos(aa) * r2, cy + math.sin(aa) * r2), 2,
            )

    def _draw_tendrils(self, canvas, cx, cy, r, t, moving, anger, shift):
        n = len(self._tendril_phase)
        amp = r * (0.05 + moving * 0.20 + anger * 0.04)
        col = self._shift((56, 10, 18), shift)
        base_w = max(2, int(r * 0.028))
        segs = 9
        for i in range(n):
            frac = (i + 0.5) / n
            base_a = math.pi * (0.30 + 0.40 * frac)
            sx = cx + math.cos(base_a) * r * 0.92
            sy = cy + math.sin(base_a) * r * 0.86
            length = r * 0.62 * self._tendril_len[i]
            sp = self._tendril_speed[i] * (1.0 + moving * 1.4)
            ph = self._tendril_phase[i]
            pts = [(sx, sy)]
            for k in range(1, segs + 1):
                f = k / segs
                sway = math.sin(t * sp + ph + k * 0.55) * amp * f * (0.5 + moving * 1.5)
                pts.append((sx + sway, sy + length * f))
            for k in range(segs):
                ww = max(1, int(base_w * (1.0 - k / segs)) + 1)
                pygame.draw.line(canvas, (*col, 140), pts[k], pts[k + 1], ww)

    def _draw_mass(self, canvas, cx, cy, r, t, anger, shift):
        aura_pts = self._mass_points(cx, cy, r * 1.13, t * 0.7, anger)
        pygame.draw.polygon(canvas, (*self._shift((70, 14, 24), shift), 46), aura_pts)
        for mul, col, a in ((1.0, (16, 5, 10), 235), (0.87, (9, 3, 7), 255)):
            pygame.draw.polygon(
                canvas, (*self._shift(col, shift), a),
                self._mass_points(cx, cy, r * mul, t, anger),
            )
        rim = self._mass_points(cx, cy, r * 1.02, t, anger)
        pygame.draw.lines(canvas, (*self._shift((120, 22, 36), shift), 150), True, rim, 3)

    def _draw_horns(self, canvas, cx, cy, r, t, anger, shift):
        count = 6 + int(anger * 5)
        col = self._shift((26, 6, 12), shift)
        rim = self._shift((190, 40, 50), shift)
        bw = max(2.0, r * 0.05)
        for i in range(count):
            frac = (i + 0.5) / count
            a = math.pi * (1.10 + 0.78 * frac)
            wi = int(i * 2.3) % self._verts
            br = r * 0.97 * self._edge_radius(wi, t, anger)
            bx = cx + math.cos(a) * br
            by = cy + math.sin(a) * br
            ln = r * 0.30 * self._horn_len[i % len(self._horn_len)] * (0.65 + anger * 0.75)
            tipx = cx + math.cos(a) * (br + ln) + math.sin(a * 3 + t * 0.7 + i) * ln * 0.14
            tipy = cy + math.sin(a) * (br + ln)
            px, py = -math.sin(a), math.cos(a)
            tri = [
                (bx + px * bw, by + py * bw),
                (bx - px * bw, by - py * bw),
                (tipx, tipy),
            ]
            pygame.draw.polygon(canvas, (*col, 240), tri)
            pygame.draw.line(canvas, (*rim, 110), tri[1], tri[2], 1)

    def _draw_eye(self, canvas, cx, cy, r, t, angle, anger, hp_ratio,
                  eye_open, extra_eyes, shift):
        ecx, ecy = cx, cy - r * 0.06
        er = r * 0.30
        if er >= 2:
            pygame.draw.circle(canvas, (*self._shift((4, 1, 3), shift), 210),
                               (int(ecx), int(ecy)), int(er * 1.38))
        positions = (
            (-0.60, -0.52), (-0.33, -0.74), (0.33, -0.74), (0.60, -0.50),
            (-0.88, -0.14), (0.88, -0.14),
        )
        n_full = int(extra_eyes)
        frac = extra_eyes - n_full
        for idx in range(min(n_full, len(positions))):
            mx, my = positions[idx]
            self._draw_small_eye(
                canvas, ecx + mx * r, ecy + my * r, max(3.0, er * 0.38),
                t, angle, anger, shift, self._extra_eye_blink[idx], 1.0,
            )
        if frac > 0.06 and n_full < len(positions):
            mx, my = positions[n_full]
            self._draw_small_eye(
                canvas, ecx + mx * r, ecy + my * r, max(3.0, er * 0.38),
                t, angle, anger, shift, self._extra_eye_blink[n_full], frac,
            )
        if er < 2:
            return
        closure = self._blink(t, self._blink_seed)
        openness = _clamp(eye_open * (1.0 - closure), 0.0, 1.0)
        if openness <= 0.02:
            return
        pulse = abs(math.sin(t * (2.0 + anger * 4.0)))
        if hp_ratio > 0.5:
            iris_hi, iris_mid, iris_lo = (225, 60, 48), (150, 30, 34), (90, 16, 22)
        elif hp_ratio > 0.2:
            iris_hi, iris_mid, iris_lo = (240, 145, 40), (195, 85, 30), (125, 42, 20)
        else:
            wv = int(150 + pulse * 105)
            iris_hi = (255, wv, int(120 + pulse * 110))
            iris_mid = (225, int(wv * 0.7), int(95 + pulse * 80))
            iris_lo = (150, 40, 50)
        pygame.draw.circle(canvas, (*self._shift((26, 5, 9), shift), 235),
                           (int(ecx), int(ecy)), int(er))
        for mul, col, a in ((0.94, iris_lo, 230), (0.72, iris_mid, 245), (0.48, iris_hi, 255)):
            pygame.draw.circle(canvas, (*self._shift(col, shift), a),
                               (int(ecx), int(ecy)), int(er * mul))
        va = 70 + int(anger * 60)
        vc = (*self._shift((215, 46, 44), shift), va)
        nv = len(self._vein_wobble)
        for i, wob in enumerate(self._vein_wobble):
            a = math.tau * (i / nv) + wob + math.sin(t * 0.6 + i) * 0.06
            p1 = (ecx + math.cos(a) * er * 0.56, ecy + math.sin(a) * er * 0.56)
            am = a + wob * 0.5
            pm = (ecx + math.cos(am) * er * 0.77, ecy + math.sin(am) * er * 0.77)
            p2 = (ecx + math.cos(a) * er * 0.98, ecy + math.sin(a) * er * 0.98)
            pygame.draw.lines(canvas, vc, False, [p1, pm, p2], max(1, int(er * 0.04)))
        px = ecx + math.cos(angle) * er * 0.20
        py = ecy + math.sin(angle) * er * 0.20
        slit_w = max(2, int(er * (0.14 + (1.0 - anger * 0.5) * 0.10)))
        rect = pygame.Rect(0, 0, slit_w, max(3, int(er * 1.42)))
        rect.center = (int(px), int(py))
        if anger > 0.2:
            rim_rect = rect.inflate(max(2, int(er * 0.10)), max(2, int(er * 0.10)))
            pygame.draw.rect(canvas, (*self._shift((255, 80, 66), shift), 150),
                             rim_rect, width=2, border_radius=rim_rect.w // 2)
        pygame.draw.rect(canvas, (*self._shift((7, 0, 3), shift), 255),
                         rect, border_radius=rect.w // 2)
        glint_r = max(1, int(er * 0.08))
        gx = int(px - slit_w - glint_r * 2)
        gy = int(py - er * 0.42)
        pygame.draw.circle(canvas, (255, 236, 236, 165), (gx, gy), glint_r)
        lid_cov = 1.0 - openness
        if lid_cov > 0.01:
            lc = (*self._shift((11, 4, 8), shift), 255)
            box = int(er * 1.28)
            lh = int(er * 2.4 * lid_cov)
            pygame.draw.ellipse(canvas, lc,
                                pygame.Rect(ecx - box, ecy - int(er * 1.18), box * 2, lh))
            pygame.draw.ellipse(canvas, lc,
                                pygame.Rect(ecx - box, ecy + int(er * 1.18) - lh, box * 2, lh))

    def _draw_small_eye(self, canvas, ex, ey, er, t, angle, anger, shift,
                        blink_off, open_amt):
        clo = self._blink(t * 1.27, blink_off)
        op = _clamp(open_amt * (1.0 - clo), 0.0, 1.0)
        if op <= 0.04 or er < 2:
            return
        ia = _clamp(int(op * 255), 0, 255)
        pygame.draw.circle(canvas, (*self._shift((20, 4, 8), shift), ia),
                           (int(ex), int(ey)), int(er))
        pygame.draw.circle(canvas, (*self._shift((185, 44, 40), shift), ia),
                           (int(ex), int(ey)), int(er * 0.64))
        px = ex + math.cos(angle) * er * 0.22
        py = ey + math.sin(angle) * er * 0.22
        pw = max(1, int(er * 0.22))
        rect = pygame.Rect(0, 0, pw, max(2, int(er * 1.25)))
        rect.center = (int(px), int(py))
        pygame.draw.rect(canvas, (8, 1, 3, ia), rect, border_radius=max(1, pw // 2))
        lid = 1.0 - op
        if lid > 0.02:
            box = int(er * 1.22)
            lh = int(er * 2.2 * lid)
            lc = (*self._shift((11, 4, 8), shift), 255)
            pygame.draw.ellipse(canvas, lc, pygame.Rect(ex - box, ey - box, box * 2, lh))
            pygame.draw.ellipse(canvas, lc, pygame.Rect(ex - box, ey + box - lh, box * 2, lh))

    def _draw_core_cracks(self, canvas, cx, cy, r, t, hp_ratio, shift):
        pulse = abs(math.sin(t * 5.0))
        strength = _clamp((0.35 - hp_ratio) / 0.35, 0.0, 1.0)
        a = int(strength * (120 + pulse * 110))
        c = (*self._shift((255, int(120 + pulse * 90), int(105 + pulse * 100)), shift),
             _clamp(a, 0, 255))
        rng = random.Random(int(t * 3))
        for i in range(6):
            a0 = math.tau * i / 6 + rng.uniform(-0.3, 0.3)
            pts = []
            x = cx + math.cos(a0) * r * 0.15
            y = cy + math.sin(a0) * r * 0.15
            aa = a0
            for _k in range(5):
                aa += rng.uniform(-0.5, 0.5)
                step = r * rng.uniform(0.14, 0.24)
                x += math.cos(aa) * step
                y += math.sin(aa) * step
                pts.append((x, y))
            pygame.draw.lines(canvas, c, False, pts, 2)

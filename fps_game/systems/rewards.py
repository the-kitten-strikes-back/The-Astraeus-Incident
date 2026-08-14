import math
import random

import pygame

from core.settings import WIDTH, HEIGHT

# ── Kill banner ───────────────────────────────────────────────────────────────
KILL_BANNER_LIFE = 9
KILL_PHRASES = [
    "NICE SHOT!",
    "AWESOME TAKEDOWN!",
    "KNOCKOUT!",
    "CRITICAL HIT!",
    "PERFECT TERMINATION!",
]

# ── Sector complete screen ────────────────────────────────────────────────────
REWARD_DURATION = 2.8
REWARD_BAR_W = 900
REWARD_BAR_H = 30
REWARD_BAR_Y = 96
REWARD_BAR_X = (WIDTH - REWARD_BAR_W) // 2

HUD_CYAN = (120, 210, 255)
HUD_GOLD = (255, 215, 90)


# ── shared geometry ────────────────────────────────────────────────────────────

def get_continue_button_rect():
    return pygame.Rect(WIDTH // 2 - 160, 520, 320, 76)


# ── kill banner ───────────────────────────────────────────────────────────────

def _render_thick(text, font, color):
    base = font.render(text, True, color)
    out = pygame.Surface((base.get_width() + 12, base.get_height() + 12), pygame.SRCALPHA)
    dark = font.render(text, True, (4, 8, 16))
    for ox in (-3, 0, 3):
        for oy in (-3, 0, 3):
            out.blit(dark, (6 + ox, 6 + oy))
    out.blit(base, (6, 6))
    return out


def draw_kill_banner(screen, banner):
    text = banner.get("text", "")
    timer = banner.get("timer", 0)
    if not text or timer <= 0:
        return

    age = KILL_BANNER_LIFE - timer
    if age >= KILL_BANNER_LIFE:
        return

    slam_t = min(1.0, age / 8)
    ease = 1.0 - (1.0 - slam_t) ** 2
    scale = 2.3 - 1.3 * ease

    alpha = 255
    if age < 3:
        alpha = int(255 * age / 3)
    out_fade = age - (KILL_BANNER_LIFE - 8)
    if out_fade > 0:
        alpha = int(255 * max(0.0, 1.0 - out_fade / 8))

    font = pygame.font.SysFont("courier", 58, bold=True)
    main = _render_thick(text, font, (245, 248, 255))
    w = max(1, int(main.get_width() * scale))
    h = max(1, int(main.get_height() * scale))
    main = pygame.transform.smoothscale(main, (w, h))
    main.set_alpha(alpha)

    gx, gy = 0, 0
    if age > 1 and random.random() < 0.35:
        gx = random.randint(-4, 4)
        gy = random.randint(-2, 2)

    cx, cy = WIDTH // 2, HEIGHT // 2 - 80

    glow = pygame.Surface((w + 60, h + 60), pygame.SRCALPHA)
    pygame.draw.rect(glow, (*HUD_CYAN, int(60 * alpha / 255)), (30, 30, w, h), border_radius=8)
    screen.blit(glow, (cx - w // 2 - 30, cy - h // 2 - 30))

    red = _render_thick(text, font, (255, 70, 100))
    cyan = _render_thick(text, font, (80, 220, 255))
    red = pygame.transform.smoothscale(red, (w, h))
    cyan = pygame.transform.smoothscale(cyan, (w, h))
    red.set_alpha(int(alpha * 0.7))
    cyan.set_alpha(int(alpha * 0.7))
    screen.blit(cyan, (cx - w // 2 - 5 + gx, cy - h // 2 + gy))
    screen.blit(red, (cx - w // 2 + 5 + gx, cy - h // 2 + gy))

    screen.blit(main, (cx - w // 2 + gx, cy - h // 2 + gy))


# ── sector complete background ────────────────────────────────────────────────

_STARS = None
_GRADIENT = None


def _starfield():
    global _STARS
    if _STARS is None:
        random.seed(7)
        _STARS = [
            {
                "x": random.randint(0, WIDTH),
                "y": random.randint(0, HEIGHT),
                "b": random.randint(60, 210),
                "p": random.uniform(0, math.pi * 2),
                "s": random.uniform(1.2, 4.0),
            }
            for _ in range(160)
        ]
        random.seed()
    return _STARS


def _background():
    global _GRADIENT
    if _GRADIENT is None:
        _GRADIENT = pygame.Surface((WIDTH, HEIGHT))
        top = (5, 8, 16)
        bot = (13, 22, 38)
        for y in range(HEIGHT):
            r = y / HEIGHT
            c = tuple(int(a + (b - a) * r) for a, b in zip(top, bot))
            pygame.draw.line(_GRADIENT, c, (0, y), (WIDTH, y))
    return _GRADIENT


def _draw_background(screen, t):
    screen.blit(_background(), (0, 0))

    for star in _starfield():
        tw = (math.sin(t * star["s"] + star["p"]) + 1) * 0.5
        v = int(star["b"] * (0.4 + 0.6 * tw))
        pygame.draw.circle(screen, (v, v + 4, v + 10), (star["x"], star["y"]), 1)

    grid = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for x in range(0, WIDTH, 90):
        pygame.draw.line(grid, (40, 80, 130, 22), (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, 70):
        pygame.draw.line(grid, (40, 80, 130, 18), (0, y), (WIDTH, y), 1)
    screen.blit(grid, (0, 0))

    core_glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pulse = 0.5 + 0.5 * math.sin(t * 1.4)
    pygame.draw.circle(core_glow, (*HUD_CYAN, int(16 + 10 * pulse)),
                       (WIDTH // 2, HEIGHT // 2), 260, 1)
    pygame.draw.circle(core_glow, (255, 200, 90, int(12 + 8 * pulse)),
                       (WIDTH // 2, HEIGHT // 2), 300, 1)
    screen.blit(core_glow, (0, 0))


def _draw_scanlines(screen, intensity=26):
    over = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 3):
        pygame.draw.line(over, (0, 0, 0, intensity), (0, y), (WIDTH, y), 1)
    screen.blit(over, (0, 0))


def _draw_scan_sweep(screen, t):
    sy = int((t * 55) % (HEIGHT + 120)) - 60
    band = pygame.Surface((WIDTH, 3), pygame.SRCALPHA)
    band.fill((120, 220, 255, 70))
    screen.blit(band, (0, sy))


def _draw_corner_brackets(screen):
    col = (70, 180, 240)
    m = 24
    L = 44
    for x, y, dx, dy in (
        (m, m, 1, 1),
        (WIDTH - m, m, -1, 1),
        (m, HEIGHT - m, 1, -1),
        (WIDTH - m, HEIGHT - m, -1, -1),
    ):
        pygame.draw.line(screen, col, (x, y + dy * 16), (x, y + dy * L), 2)
        pygame.draw.line(screen, col, (x + dx * 16, y), (x + dx * L, y), 2)


def _draw_glitch_text(screen, text, cx, cy, size, color, glow_color, alpha, t, glitch=0.0):
    font = pygame.font.SysFont("courier", size, bold=True)
    main = font.render(text, True, color)
    glow = font.render(text, True, glow_color)
    w = main.get_width()
    h = main.get_height()
    main.set_alpha(alpha)
    glow.set_alpha(max(0, alpha // 2))

    gx, gy = 0, 0
    if glitch > 0 and random.random() < glitch:
        gx = random.randint(-4, 4)
        gy = random.randint(-2, 2)

    x = cx - w // 2
    y = cy - h // 2

    for ox, oy in ((3, 3), (-3, -3)):
        screen.blit(glow, (x + ox, y + oy))

    if glitch > 0.1:
        red = font.render(text, True, (255, 70, 100))
        cyan = font.render(text, True, (80, 220, 255))
        red.set_alpha(max(0, alpha // 3))
        cyan.set_alpha(max(0, alpha // 3))
        screen.blit(cyan, (x - 4 + gx, y + gy))
        screen.blit(red, (x + 4 + gx, y + gy))

    screen.blit(main, (x + gx, y + gy))


# ── points bar ────────────────────────────────────────────────────────────────

def _draw_points_bar(screen, fill_ratio, counter, t):
    bar = pygame.Rect(REWARD_BAR_X, REWARD_BAR_Y, REWARD_BAR_W, REWARD_BAR_H)

    glow = pygame.Surface((bar.w + 40, bar.h + 40), pygame.SRCALPHA)
    pygame.draw.rect(glow, (*HUD_CYAN, 40), (20, 20, bar.w, bar.h), border_radius=8)
    screen.blit(glow, (bar.x - 20, bar.y - 20))

    pygame.draw.rect(screen, (8, 14, 26), bar, border_radius=6)
    pygame.draw.rect(screen, (90, 200, 255), bar, 2, border_radius=6)

    fill_w = int(bar.w * max(0.0, min(1.0, fill_ratio)))
    if fill_w > 0:
        fill = pygame.Rect(bar.x + 2, bar.y + 2, fill_w, bar.h - 4)
        pygame.draw.rect(screen, (28, 104, 196), fill)
        pygame.draw.rect(screen, (110, 224, 255), (fill.x, fill.y, fill.w, 6))
        shimmer_x = int((t * 130) % (bar.w + 60)) - 30
        pygame.draw.rect(screen, (190, 245, 255),
                         (bar.x + 2 + shimmer_x, bar.y + 2, 24, bar.h - 4))

    for i in range(1, 10):
        tx = bar.x + bar.w * i // 10
        pygame.draw.line(screen, (28, 46, 74), (tx, bar.y + 3), (tx, bar.bottom - 3), 1)

    small = pygame.font.SysFont("courier", 18, bold=True)
    left = small.render("POINTS ALLOCATED", True, (120, 200, 255))
    screen.blit(left, (bar.x - left.get_width() - 16, bar.centery - left.get_height() // 2))

    counter_surf = small.render(f"+{counter} PTS", True, HUD_GOLD)
    screen.blit(counter_surf, (bar.right + 16, bar.centery - counter_surf.get_height() // 2))


# ── particles ─────────────────────────────────────────────────────────────────

def _draw_particles(screen, particles, sparks):
    for p in particles:
        size = p["size"]
        col = p["color"]
        cx = p["x"]
        cy = p["y"]
        s = max(2, int(size * (0.7 + 0.5 * math.sin(p["spin"]))))
        surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (*col, 230), [(s, 0), (s * 2, s), (s, s * 2), (0, s)])
        screen.blit(surf, (cx - s, cy - s))

    for spark in sparks:
        life = 1.0 - spark["t"] / 14.0
        r = int(2 + 5 * life)
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*HUD_GOLD, int(200 * life)), (r, r), r)
        screen.blit(surf, (spark["x"] - r, spark["y"] - r))


# ── continue button ───────────────────────────────────────────────────────────

def _draw_continue_button(screen, hover, t):
    rect = get_continue_button_rect()
    pulse = 0.5 + 0.5 * math.sin(t * 2.6)

    glow = pygame.Surface((rect.w + 50, rect.h + 50), pygame.SRCALPHA)
    ga = int(50 + 80 * pulse) if hover else int(30 + 40 * pulse)
    pygame.draw.rect(glow, (*HUD_CYAN, ga), (25, 25, rect.w, rect.h), border_radius=14)
    screen.blit(glow, (rect.x - 25, rect.y - 25))

    pygame.draw.rect(screen, (16, 30, 54) if not hover else (24, 50, 84), rect, border_radius=12)
    border = (150, 235, 255) if hover else (90, 180, 240)
    pygame.draw.rect(screen, border, rect, 2, border_radius=12)
    pygame.draw.line(screen, (140, 230, 255), (rect.x + 14, rect.y + 8),
                     (rect.right - 14, rect.y + 8), 1)

    font = pygame.font.SysFont("courier", 26, bold=True)
    label = font.render("CONTINUE  >>", True, (228, 246, 255))
    screen.blit(label, (rect.centerx - label.get_width() // 2,
                        rect.centery - label.get_height() // 2))

    hint = pygame.font.SysFont("courier", 15).render("[ ENTER ]", True, (90, 130, 170))
    screen.blit(hint, (rect.centerx - hint.get_width() // 2, rect.bottom + 12))


# ── main reward screen ────────────────────────────────────────────────────────

def draw_level_reward(screen, reward, score, kills):
    t = reward["timer"]
    duration = reward["duration"]
    gained = reward["gained"]
    sector = reward["sector"]
    total_points = reward["total"]
    done = reward.get("done", False)

    _draw_background(screen, t)

    eased = min(1.0, t / duration)
    fill_ratio = 1.0 - (1.0 - eased) ** 2
    counter = int(gained * (1.0 - (1.0 - eased) ** 2))

    header = pygame.font.SysFont("courier", 18, bold=True)
    head_surf = header.render(f"ASTRAEUS // SECTOR {sector} CLEARED", True, (110, 190, 240))
    screen.blit(head_surf, (WIDTH // 2 - head_surf.get_width() // 2, 40))

    _draw_points_bar(screen, fill_ratio, counter, t)

    title_alpha = int(255 * min(1.0, max(0.0, t - 0.15) / 0.4))
    if title_alpha > 0:
        glitch = 0.22 if t < duration else 0.06
        _draw_glitch_text(
            screen, "SECTOR COMPLETE", WIDTH // 2, 215, 72,
            (232, 246, 255), HUD_CYAN, title_alpha, t, glitch=glitch,
        )

    sub = pygame.font.SysFont("courier", 20, bold=True)
    sub_alpha = int(255 * min(1.0, max(0.0, t - 0.45) / 0.4))
    if sub_alpha > 0:
        sub_surf = sub.render("ALL HOSTILES NEUTRALIZED", True, (140, 210, 255))
        sub_surf.set_alpha(sub_alpha)
        screen.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, 272))

    stats_font = pygame.font.SysFont("courier", 18)
    stats_alpha = int(255 * min(1.0, max(0.0, t - 0.7) / 0.5))
    if stats_alpha > 0:
        stats = (f"ENEMIES NEUTRALIZED {kills}   •   SCORE {score}   •   "
                 f"POINTS {total_points}")
        st = stats_font.render(stats, True, (150, 190, 230))
        st.set_alpha(stats_alpha)
        pygame.draw.line(screen, (45, 80, 130), (WIDTH // 2 - 260, 320),
                         (WIDTH // 2 + 260, 320), 1)
        screen.blit(st, (WIDTH // 2 - st.get_width() // 2, 330))

    _draw_particles(screen, reward["particles"], reward.get("sparks", []))
    _draw_corner_brackets(screen)
    _draw_scanlines(screen)
    _draw_scan_sweep(screen, t)

    btn_alpha = int(255 * min(1.0, max(0.0, t - 0.8) / 0.4))
    if btn_alpha > 0:
        mx, my = pygame.mouse.get_pos()
        hover = get_continue_button_rect().collidepoint(mx, my) and done
        btn_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        btn_surf.fill((0, 0, 0, 0))
        _draw_continue_button(btn_surf, hover, t)
        btn_surf.set_alpha(btn_alpha)
        screen.blit(btn_surf, (0, 0))

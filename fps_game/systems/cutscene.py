import math
import pygame
import random

from core.settings import WIDTH, HEIGHT
def clamp(val, low=0, high=255):
    return max(low, min(high, val))

def animate_typewriter(text, t, char_delay=0.03):
    return text[:int(t / char_delay)]


def animate_bounce(y, t, frequency=2.0, amplitude=8):
    return y + amplitude * math.sin(t * frequency * 2 * math.pi)


def animate_glitch(t, glitch_chance=0.3):
    if random.random() < glitch_chance:
        return random.randint(-3, 3), random.randint(-2, 2)
    return 0, 0


def _scanlines(surface, intensity, color=(0, 0, 0)):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 3):
        pygame.draw.line(overlay, (*color, int(18 * intensity)), (0, y), (WIDTH, y), 1)
    surface.blit(overlay, (0, 0))


def _glitch_block(surface, intensity):
    if random.random() < intensity:
        gh = random.randint(8, 44)
        gy = random.randint(0, HEIGHT - gh)
        gw = random.randint(40, 220)
        gx = random.randint(0, WIDTH - gw)
        ga = random.randint(25, 100)
        gc = (random.randint(80, 255), random.randint(0, 80), random.randint(80, 255))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (*gc, ga), (gx, gy, gw, gh))
        surface.blit(overlay, (0, 0))


def _draw_opening_glitch_storm(surface, t, intensity=0.3):
    _scanlines(surface, intensity * 1.2, color=(10, 12, 24))

    block_count = 2 + int(12 * intensity)
    for _ in range(block_count):
        if random.random() > min(1.0, intensity + 0.05):
            continue
        gh = random.randint(8, max(12, int(110 * intensity)))
        gy = random.randint(0, max(0, HEIGHT - gh))
        gw = random.randint(80, max(120, int(720 * intensity)))
        gx = random.randint(0, max(0, WIDTH - gw))
        tint = random.choice([
            (70, 170, 220),
            (130, 90, 220),
            (180, 90, 255),
            (60, 230, 255),
        ])
        ga = random.randint(20, max(35, int(95 * intensity)))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (*tint, ga), (gx, gy, gw, gh))
        surface.blit(overlay, (0, 0))

    if intensity > 0.12:
        tear = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 4):
            wobble = int(math.sin(t * 11 + y * 0.07) * (3 + intensity * 8))
            alpha = int(22 * intensity + 10 * (y % 2))
            pygame.draw.line(tear, (80, 190, 255, alpha), (0 + wobble, y), (WIDTH + wobble, y), 1)
        surface.blit(tear, (0, 0))


def _draw_opening_ship(surface, x, y, scale=1.0, angle=0.0, alpha=255):
    ship = pygame.Surface((520, 220), pygame.SRCALPHA)
    hull = [(32, 110), (110, 68), (290, 55), (452, 92), (498, 112), (452, 132), (290, 165), (110, 152)]
    nose = [(28, 110), (92, 86), (92, 134)]
    wing_left = [(120, 82), (42, 48), (12, 56), (62, 100)]
    wing_right = [(120, 138), (42, 172), (12, 164), (62, 120)]
    engine = pygame.Rect(452, 95, 42, 30)

    pygame.draw.polygon(ship, (12, 18, 40), hull)
    pygame.draw.polygon(ship, (80, 180, 255), hull, 3)
    pygame.draw.polygon(ship, (90, 40, 150), nose)
    pygame.draw.polygon(ship, (130, 80, 220), wing_left)
    pygame.draw.polygon(ship, (130, 80, 220), wing_right)
    pygame.draw.rect(ship, (30, 120, 200), engine)

    for i in range(4):
        pygame.draw.line(ship, (70, 220, 255), (122 + i * 58, 92), (122 + i * 58, 128), 2)
        pygame.draw.circle(ship, (60, 240, 255), (170 + i * 40, 111), 4)

    glow = pygame.Surface((520, 220), pygame.SRCALPHA)
    for r in range(8, 90, 10):
        pygame.draw.ellipse(glow, (90, 150, 255, max(0, 80 - r // 2)), pygame.Rect(40 - r // 3, 78 - r // 4, 160 + r, 66 + r // 2), 2)
    ship.blit(glow, (0, 0))

    if angle:
        ship = pygame.transform.rotozoom(ship, angle, scale)
    elif scale != 1.0:
        ship = pygame.transform.smoothscale(
            ship,
            (max(1, int(ship.get_width() * scale)), max(1, int(ship.get_height() * scale))),
        )
    ship.set_alpha(alpha)
    rect = ship.get_rect(center=(x, y))
    surface.blit(ship, rect.topleft)


def _draw_opening_console(surface, t, zoom=1.0):
    panel = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    panel.fill((1, 2, 8))

    cx, cy = WIDTH // 2, HEIGHT // 2
    console = pygame.Rect(cx - 280, cy - 130, 560, 260)
    screen = pygame.Rect(console.x + 48, console.y + 38, console.width - 96, console.height - 88)

    flicker = 0.65 + 0.35 * math.sin(t * 8.0)
    glow_a = int(70 + 110 * max(0.0, flicker))

    pygame.draw.rect(panel, (8, 18, 35), console, border_radius=16)
    pygame.draw.rect(panel, (70, 170, 240), console, 3, border_radius=16)
    pygame.draw.rect(panel, (15, 35, 60), screen, border_radius=8)
    pygame.draw.rect(panel, (100, 220, 255), screen, 2, border_radius=8)

    for i in range(5):
        y = screen.y + 18 + i * 28
        line_alpha = int(20 + 20 * math.sin(t * 4 + i))
        pygame.draw.line(panel, (40, 160, 220, line_alpha), (screen.x + 12, y), (screen.right - 12, y), 1)

    title_font = pygame.font.SysFont("courier", 26, bold=True)
    tiny_font = pygame.font.SysFont("courier", 18)
    title = title_font.render("ASTRAEUS CONSOLE", True, (170, 235, 255))
    title.set_alpha(glow_a)
    panel.blit(title, (console.x + 20, console.y + 16))

    flash = pygame.Surface((screen.width, screen.height), pygame.SRCALPHA)
    flash.fill((70, 180, 255, int(18 + 16 * flicker)))
    panel.blit(flash, (screen.x, screen.y))

    for i in range(8):
        bar_w = int((screen.width - 32) * (0.35 + 0.55 * abs(math.sin(t * 1.4 + i * 0.9))))
        bar_y = screen.y + 16 + i * 22
        pygame.draw.rect(panel, (80, 220, 255), (screen.x + 16, bar_y, bar_w, 6))
        pygame.draw.rect(panel, (180, 80, 255), (screen.x + 16, bar_y + 8, bar_w // 2, 2))

    for i, label in enumerate(["LINK", "POWER", "TEMP", "CORE", "ECHO"]):
        lbl = tiny_font.render(label, True, (120, 190, 230))
        panel.blit(lbl, (console.right - 140, console.y + 18 + i * 22))

    # screen text block
    text = [
        "log. 001. WAKE UP...",
        "",
        "THERES SOMETHING...",
        "SOMETHING INSIDE THE CORE.",
        "I think - i think its keeping the ship alive.",
    ]
    text_font = pygame.font.SysFont("courier", 23, bold=True)
    y = screen.y + 92
    for idx, line in enumerate(text):
        if not line:
            y += 12
            continue
        line_surf = text_font.render(line, True, (205, 240, 255))
        line_surf.set_alpha(int(150 + 80 * math.sin(t * 6 + idx)))
        panel.blit(line_surf, (screen.x + 20, y))
        y += 28

    glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    glow.fill((25, 70, 120, int(14 + 24 * flicker)))
    panel.blit(glow, (0, 0))
    _scanlines(panel, 0.3, color=(70, 100, 140))
    _glitch_block(panel, 0.22)

    if zoom != 1.0:
        new_w = max(1, int(WIDTH * zoom))
        new_h = max(1, int(HEIGHT * zoom))
        panel = pygame.transform.smoothscale(panel, (new_w, new_h))
        surface.fill((0, 0, 0))
        surface.blit(panel, ((WIDTH - new_w) // 2, (HEIGHT - new_h) // 2))
    else:
        surface.blit(panel, (0, 0))


def _draw_opening_word_burst(surface, word, t, duration=0.9):
    surface.fill((0, 0, 0))

    if t < 0.0 or t > duration:
        return

    pop = min(1.0, t / 0.18)
    hold = min(1.0, max(0.0, (t - 0.18) / 0.22))
    collapse = max(0.0, 1.0 - max(0.0, t - 0.66) / 0.24)
    intensity = min(1.0, pop * 0.9 + hold * 0.6)

    base_font_size = {
        "TIME": 240,
        "IS": 280,
        "ON": 280,
        "YOUR": 220,
        "SIDE.": 240,
    }.get(word, 240)
    font = pygame.font.SysFont("courier", max(28, int(base_font_size * (0.38 + 0.75 * pop))), bold=True)
    main = font.render(word, True, (225, 245, 255))
    glow = font.render(word, True, (85, 185, 255))

    # Push the word to near full-screen scale, then let it settle into a hard black reset.
    max_w = int(WIDTH * 0.94)
    max_h = int(HEIGHT * 0.42)
    scale = min(max_w / max(1, main.get_width()), max_h / max(1, main.get_height()))
    scale *= 0.88 + 0.28 * pop
    scaled_main = pygame.transform.smoothscale(main, (max(1, int(main.get_width() * scale)), max(1, int(main.get_height() * scale))))
    scaled_glow = pygame.transform.smoothscale(glow, scaled_main.get_size())

    gx = WIDTH // 2 - scaled_main.get_width() // 2 + int(math.sin(t * 10) * (10 * (1 - hold)))
    gy = HEIGHT // 2 - scaled_main.get_height() // 2 + int(math.cos(t * 8) * (8 * (1 - hold)))

    burst = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    burst.fill((0, 0, 0))
    glow_layer = scaled_glow.copy()
    glow_layer.set_alpha(int(120 + 100 * intensity))
    main_layer = scaled_main.copy()
    main_layer.set_alpha(int(255 * pop * collapse))
    burst.blit(glow_layer, (gx + 8, gy + 8))
    burst.blit(main_layer, (gx, gy))

    if hold > 0.15:
        for _ in range(18):
            rx = random.randint(0, WIDTH)
            ry = random.randint(max(0, gy - 30), min(HEIGHT - 1, gy + scaled_main.get_height() + 30))
            rw = random.randint(24, 140)
            rh = random.randint(2, 8)
            col = random.choice([(70, 190, 255, 45), (140, 90, 255, 38), (240, 80, 255, 26)])
            pygame.draw.rect(burst, col, (rx, ry, rw, rh))

    _scanlines(burst, 0.2 + 0.45 * intensity, color=(8, 10, 18))
    surface.blit(burst, (0, 0))


def _draw_opening_ship_break(surface, t):
    ship_t = max(0.0, t - 4.0)
    ship_x = -180 + (WIDTH + 360) * min(1.0, ship_t / 7.0)
    ship_y = HEIGHT * 0.53 + math.sin(ship_t * 1.1) * 18
    _draw_opening_ship(surface, int(ship_x), int(ship_y), scale=0.92, angle=-3 + math.sin(ship_t * 1.4) * 4, alpha=240)

    # Text fragments get pushed apart as the ship crosses the center.
    frag = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    center = WIDTH * 0.52
    impact = max(0.0, 1.0 - min(1.0, abs(ship_x - center) / 520.0))
    impact = impact ** 1.8
    for i in range(20):
        px = random.randint(0, WIDTH)
        py = random.randint(110, HEIGHT - 80)
        dx = px - ship_x
        dy = py - ship_y
        dist = max(1.0, math.hypot(dx, dy))
        push = impact * max(0.0, 1.0 - dist / 680.0)
        if push > 0:
            box = pygame.Surface((random.randint(24, 60), random.randint(10, 22)), pygame.SRCALPHA)
            box.fill((80, 190, 255, int(90 * push)))
            frag.blit(box, (px + int(dx * 0.18 * push), py + int(dy * 0.10 * push)))
    frag.set_alpha(int(190 * min(1.0, ship_t / 3.0)))
    surface.blit(frag, (0, 0))


def draw_opening_cutscene(screen, t, gun_sprite=None):
    screen.fill((0, 0, 0))

    audio_end = 24.74
    words_start = audio_end + 0.35
    ship_start = words_start + 7.2
    console_start = ship_start + 7.6
    log_start = console_start + 6.8
    final_glitch_start = log_start + 18.8
    end_time = final_glitch_start + 6.2

    glitch_strength = min(1.0, 0.05 + (t / audio_end) ** 1.75)
    _draw_opening_glitch_storm(screen, t, intensity=min(1.0, glitch_strength))

    dull = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pulse = 0.18 + 0.12 * (math.sin(t * 1.3) + 1) * 0.5
    dull.fill((6, 10, 22, int(120 * pulse)))
    screen.blit(dull, (0, 0))

    if t < audio_end:
        if gun_sprite is not None and t > 1.35:
            gun_t = t - 1.35
            angle = -gun_t * 24.0
            scale = 0.82 + 0.04 * math.sin(t * 2.1)
            gun = pygame.transform.rotozoom(gun_sprite, angle, scale)
            gun.set_alpha(int(220 + 35 * math.sin(t * 2.4)))
            rect = gun.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            glow = pygame.Surface((rect.width + 120, rect.height + 120), pygame.SRCALPHA)
            pygame.draw.circle(glow, (90, 170, 255, 60), (glow.get_width() // 2, glow.get_height() // 2), min(glow.get_width(), glow.get_height()) // 3)
            pygame.draw.circle(glow, (180, 90, 255, 30), (glow.get_width() // 2, glow.get_height() // 2), min(glow.get_width(), glow.get_height()) // 2 - 10, 8)
            screen.blit(glow, (rect.centerx - glow.get_width() // 2, rect.centery - glow.get_height() // 2))
            screen.blit(gun, rect.topleft)

    elif t < words_start:
        # Brief beat after the audio chain ends: the weapon is gone, but the screen is still breathing.
        pass

    elif t < ship_start:
        word_times = [
            ("TIME", 0.0, 1.15),
            ("IS", 1.55, 1.00),
            ("ON", 2.90, 1.00),
            ("YOUR", 4.25, 1.05),
            ("SIDE.", 5.65, 1.15),
        ]
        local = t - words_start
        shown = False
        for word, start, duration in word_times:
            if start <= local < start + duration:
                _draw_opening_word_burst(screen, word, local - start, duration=duration)
                shown = True
                break
        if not shown:
            screen.fill((0, 0, 0))

    elif t < console_start:
        _draw_opening_word_burst(screen, "SIDE.", 0.82, duration=1.15)
        _draw_opening_ship_break(screen, t - ship_start + 4.0)
        # As the ship passes, tear the words apart with extra debris and shake.
        drift = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for _ in range(80):
            x = random.randint(0, WIDTH)
            y = random.randint(120, HEIGHT - 60)
            w = random.randint(8, 28)
            h = random.randint(2, 6)
            col = random.choice([(80, 200, 255, 60), (160, 90, 255, 55), (40, 120, 220, 45)])
            pygame.draw.rect(drift, col, (x, y, w, h))
        drift.set_alpha(160)
        screen.blit(drift, (0, 0))

    elif t < log_start:
        zoom = 1.0 + min(1.35, (t - console_start) * 0.13)
        _draw_opening_console(screen, t - console_start, zoom=zoom)

    elif t < log_start + 4.8:
        zoom = 2.35
        _draw_opening_console(screen, t - console_start, zoom=zoom)
        local = t - log_start
        log_font = pygame.font.SysFont("courier", 28, bold=True)
        pause_font = pygame.font.SysFont("courier", 26, bold=True)
        if local < 4.2:
            text = "log. 001. WAKE UP..."
            surf = log_font.render(text, True, (220, 245, 255))
            surf.set_alpha(int(255 * min(1.0, local / 0.5)))
            screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 - 40))
        if local > 1.1:
            line = "THERES SOMETHING... SOMETHING INSIDE THE CORE."
            surf = pause_font.render(line, True, (205, 235, 255))
            surf.set_alpha(int(255 * min(1.0, (local - 1.1) / 0.5)))
            screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 + 8))
        if local > 2.25:
            line = "I think - i think its keeping the ship alive."
            surf = pause_font.render(line, True, (180, 220, 250))
            surf.set_alpha(int(255 * min(1.0, (local - 2.25) / 0.6)))
            screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 + 44))

    elif t < log_start + 8.6:
        screen.fill((0, 0, 0))
        font = pygame.font.SysFont("courier", 34, bold=True)
        local = t - (log_start + 4.8)
        if local < 1.0:
            surf = font.render("FIND THE CORE", True, (215, 240, 255))
            surf.set_alpha(int(255 * min(1.0, local / 0.35)))
            screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 - surf.get_height() // 2))

    elif t < log_start + 12.2:
        screen.fill((0, 0, 0))
        font = pygame.font.SysFont("courier", 34, bold=True)
        local = t - (log_start + 8.6)
        if local < 1.0:
            surf = font.render("FIX THE ASTRAEUS.", True, (215, 240, 255))
            surf.set_alpha(int(255 * min(1.0, local / 0.35)))
            screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 - surf.get_height() // 2))

    elif t < final_glitch_start:
        screen.fill((0, 0, 0))
        font = pygame.font.SysFont("courier", 30, bold=True)
        local = t - (log_start + 12.2)
        if local < 1.8:
            lines = [
                "AND STOP THE ENTITY AT THE HEART OF IT ALL.......",
            ]
            for idx, line in enumerate(lines):
                surf = font.render(line, True, (220, 240, 255))
                surf.set_alpha(int(255 * min(1.0, local / 0.45)))
                screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 - surf.get_height() // 2 + idx * 38))
        _draw_opening_glitch_storm(screen, t, intensity=0.8)

    elif t < end_time:
        _draw_opening_glitch_storm(screen, t, intensity=1.0)
        fade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fade.fill((0, 0, 0, int(255 * min(1.0, (t - final_glitch_start) / 3.0))))
        screen.blit(fade, (0, 0))

    else:
        screen.fill((0, 0, 0))


def draw_corrupted_screen(surface, t, intensity=0.3):
    _scanlines(surface, intensity)
    _glitch_block(surface, intensity)


def _draw_star_field(screen, t, count=120, drift=0.0):
    random.seed(42)
    for _ in range(count):
        sx = random.randint(0, WIDTH)
        sy = random.randint(0, HEIGHT)
        brightness = random.randint(80, 220)
        twinkle = int((math.sin(t * random.uniform(1.5, 4.0) + random.random() * 6) + 1) * 0.5 * 60)
        value = clamp(brightness + twinkle)
        pygame.draw.circle(screen, (value,) * 3,
                           (sx, int(sy + drift * random.uniform(0.1, 0.8)) % HEIGHT), 1)
    random.seed()


def _draw_black_hole(screen, cx, cy, t, radius=140):
    for r in range(radius, 0, -8):
        ratio = r / radius
        alpha = int(200 * (1 - ratio))
        ring_color = (int(20 * ratio), int(10 * ratio), int(60 + 80 * (1 - ratio)))
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*ring_color, alpha), (r, r), r)
        screen.blit(surf, (cx - r, cy - r))

    for i in range(60):
        angle = (i / 60) * math.pi * 2 + t * 0.4
        dist = radius + 30 + math.sin(angle * 3 + t) * 18
        ax = cx + int(math.cos(angle) * dist)
        ay = cy + int(math.sin(angle) * dist * 0.35)
        heat = min(255, 180 + int(75 * math.sin(angle * 2 + t * 2)))
        pygame.draw.circle(screen, (heat, int(heat * 0.4), 40), (ax, ay), 2)

    pygame.draw.circle(screen, (0, 0, 0), (cx, cy), int(radius * 0.55))


def _draw_astraeus_silhouette(screen, cx, cy, t):
    flicker = 0.7 + 0.3 * math.sin(t * 2.3)
    dim = int(60 * flicker)
    hull = [
        (cx - 180, cy - 12), (cx - 80, cy - 22),
        (cx + 60,  cy - 28), (cx + 180, cy - 8),
        (cx + 180, cy + 8),  (cx + 60,  cy + 28),
        (cx - 80,  cy + 22), (cx - 180, cy + 12),
    ]
    pygame.draw.polygon(screen, (dim, dim + 6, dim + 14), hull)
    pygame.draw.polygon(screen, (dim + 20, dim + 26, dim + 40), hull, 2)
    for wx in range(cx - 140, cx + 120, 28):
        wa = int(40 + 60 * abs(math.sin(t * 1.8 + wx * 0.05)))
        pygame.draw.rect(screen, (wa, wa + 30, wa + 60), (wx, cy - 7, 10, 14))


def _draw_arrival(screen, t):
    screen.fill((2, 4, 10))
    _draw_star_field(screen, t, count=160, drift=t * 6)
    _draw_black_hole(screen, int(WIDTH * 0.72), int(HEIGHT * 0.44), t, radius=120)
    _draw_astraeus_silhouette(screen,
                              int(WIDTH * 0.32 + math.sin(t * 0.3) * 8),
                              int(HEIGHT * 0.52 + math.cos(t * 0.22) * 5), t)


def _draw_corridor(screen, t):
    screen.fill((10, 12, 16))
    flicker = (math.sin(t * 3.7) + 1) * 0.5
    cx, cy = WIDTH // 2, HEIGHT // 2
    for i in range(7):
        depth = 0.12 + i * 0.13
        w = int(WIDTH * depth)
        h = int(HEIGHT * depth)
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        brightness = int(22 + 22 * depth + 12 * flicker)
        pygame.draw.rect(screen, (brightness, brightness + 4, brightness + 14), rect, 1)
    for x in range(cx - 160, cx + 180, 80):
        la = int(120 + 80 * flicker)
        pygame.draw.rect(
            screen,
            (clamp(la), clamp(la + 40), clamp(la + 80)),
            (x - 18, 0, 36, 10),
        )
        pygame.draw.rect(
            screen,
            (clamp(la // 3), clamp(la // 3 + 10), clamp(la // 3 + 30)),
            (x - 10, 10, 20, HEIGHT - 10),
        )
    for y in range(40, HEIGHT - 40, HEIGHT - 80):
        pygame.draw.line(screen, (30, 40, 60), (0, y), (WIDTH, y), 2)


def _draw_crew_echo(screen, t):
    _draw_corridor(screen, t)
    for i in range(4):
        phase = t * 0.9 + i * 1.8
        alpha = int((math.sin(phase) + 1) * 0.5 * 130)
        ex = int(WIDTH * (0.22 + i * 0.18) + math.sin(phase * 1.3) * 14)
        ey = int(HEIGHT * 0.38 + math.sin(phase * 0.7) * 10)
        if alpha > 10:
            ghost_surf = pygame.Surface((30, 80), pygame.SRCALPHA)
            ghost_surf.fill((120, 180, 220, alpha))
            screen.blit(ghost_surf, (ex, ey))


def _draw_fracture(screen, t):
    screen.fill((6, 4, 12))
    flicker = int((math.sin(t * 5) + 1) * 50)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((80, 20, 120, 60 + flicker))
    screen.blit(overlay, (0, 0))
    for i in range(0, WIDTH + HEIGHT, 38):
        x1 = max(0, i - HEIGHT)
        y1 = max(0, HEIGHT - i)
        x2 = min(WIDTH, i)
        y2 = min(HEIGHT, HEIGHT - (i - WIDTH))
        go = random.randint(-3, 3)
        pygame.draw.line(screen, (160 + go * 10, 60, 180 + go * 8), (x1 + go, y1), (x2 + go, y2), 1)
    for _ in range(14):
        px = random.randint(0, WIDTH)
        py = random.randint(0, HEIGHT)
        pr = random.randint(1, 4)
        pc = random.choice([(200, 80, 255), (80, 200, 255), (255, 80, 180)])
        pygame.draw.circle(screen, pc, (px, py), pr)


def _draw_core_chamber(screen, t):
    screen.fill((6, 4, 10))
    pulse = (math.sin(t * 1.8) + 1) * 0.5
    cx, cy = WIDTH // 2, HEIGHT // 2
    for r in range(260, 0, -22):
        ratio = r / 260
        alpha = int(160 * (1 - ratio) * (0.6 + 0.4 * pulse))
        cr = int(120 + 100 * pulse * ratio)
        cg = int(20 * ratio)
        cb = int(80 + 60 * (1 - ratio))
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (cr, cg, cb, alpha), (r, r), r, 3)
        screen.blit(surf, (cx - r, cy - r))
    for i in range(24):
        angle = (i / 24) * math.pi * 2 + t * 0.6
        dist = 90 + 30 * math.sin(angle * 3 + t * 1.4)
        ex = cx + int(math.cos(angle) * dist)
        ey = cy + int(math.sin(angle) * dist)
        ea = int(180 + 75 * math.sin(i + t * 2))
        pygame.draw.circle(screen, (ea, int(ea * 0.3), int(ea * 0.6)), (ex, ey), 3)
    pygame.draw.circle(screen, (200, 60, 120), (cx, cy), int(28 + 8 * pulse))
    pygame.draw.circle(screen, (255, 140, 180), (cx, cy), int(14 + 4 * pulse))


def _draw_corridor_into(surf, t, tint):
    surf.fill((0, 0, 0, 0))
    cx, cy = WIDTH // 2, HEIGHT // 2
    for i in range(5):
        depth = 0.1 + i * 0.16
        w = int(WIDTH * depth)
        h = int(HEIGHT * depth)
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(surf, (*tint, 180), rect, 1)


def _draw_all_timelines(screen, t):
    screen.fill((4, 4, 8))
    layers = [
        ((40, 20, 80),  0.18, -0.6),
        ((20, 40, 100), 0.22,  0.4),
        ((80, 20, 60),  0.16, -0.3),
    ]
    for color, alpha_base, drift in layers:
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shift_x = int(math.sin(t * 0.7 + drift * 3) * 30)
        shift_y = int(math.cos(t * 0.5 + drift * 2) * 20)
        _draw_corridor_into(surf, t + drift * 2, color)
        surf.set_alpha(int(alpha_base * 255))
        screen.blit(surf, (shift_x, shift_y))

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(0, WIDTH, 6):
        a = int(30 + 20 * math.sin(i * 0.05 + t * 2))
        pygame.draw.line(overlay, (100, 60, 160, a), (i, 0), (i, HEIGHT), 1)
    screen.blit(overlay, (0, 0))

    for _ in range(6):
        gx = random.randint(0, WIDTH)
        gy = random.randint(0, HEIGHT)
        ga = random.randint(30, 80)
        gw = random.randint(60, 200)
        gh = random.randint(4, 14)
        glitch_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        glitch_surf.fill((random.randint(80, 200), 40, random.randint(80, 200), ga),
                         pygame.Rect(gx, gy, gw, gh))
        screen.blit(glitch_surf, (0, 0))


def _draw_entity_presence(screen, t):
    screen.fill((2, 2, 6))
    cx, cy = WIDTH // 2, HEIGHT // 2
    pulse = (math.sin(t * 1.2) + 1) * 0.5

    for r in range(300, 0, -12):
        ratio = r / 300
        alpha = int(80 * (1 - ratio) * pulse)
        pygame.draw.circle(screen, (int(60 * ratio), 0, int(100 * (1 - ratio))),
                           (cx, cy), r, 1)

    eye_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    eye_alpha = int(80 + 120 * pulse)
    pygame.draw.ellipse(eye_surf, (160, 0, 200, eye_alpha),
                        pygame.Rect(cx - 120, cy - 50, 240, 100), 3)
    pygame.draw.circle(eye_surf, (200, 20, 240, eye_alpha), (cx, cy), int(22 + 8 * pulse))
    pygame.draw.circle(eye_surf, (0, 0, 0, 255), (cx, cy), int(10 + 4 * pulse))
    screen.blit(eye_surf, (0, 0))

    random.seed(int(t * 8))
    for _ in range(18):
        px = random.randint(0, WIDTH)
        py = random.randint(0, HEIGHT)
        pa = random.randint(60, 180)
        pygame.draw.circle(screen, (120, 0, 160, pa), (px, py), random.randint(1, 3))
    random.seed()


def draw_scene_background(screen, scene_type, t):
    if scene_type == "arrival":
        _draw_arrival(screen, t)
    elif scene_type == "ship_corridor":
        _draw_corridor(screen, t)
    elif scene_type == "crew_echo":
        _draw_crew_echo(screen, t)
    elif scene_type == "fracture":
        _draw_fracture(screen, t)
    elif scene_type == "core_chamber":
        _draw_core_chamber(screen, t)
    elif scene_type == "all_timelines":
        _draw_all_timelines(screen, t)
    elif scene_type == "entity_presence":
        _draw_entity_presence(screen, t)
    else:
        screen.fill((8, 8, 12))


def draw_text_with_animation(screen, text, x, y, font, color, animation_type="fade", t=0, duration=1.0):
    if animation_type == "typewriter":
        animated_text = animate_typewriter(text, t, char_delay=0.032)
        surf = font.render(animated_text, True, color)
    elif animation_type == "fade":
        surf = font.render(text, True, color)
        alpha = min(255, int(255 * (t / max(0.01, duration))))
        surf.set_alpha(alpha)
    elif animation_type == "bounce":
        y_new = animate_bounce(y, t, frequency=2.0, amplitude=8)
        surf = font.render(text, True, color)
        screen.blit(surf, (x - surf.get_width() // 2, int(y_new)))
        return
    elif animation_type == "glitch":
        surf = font.render(text, True, color)
        gx, gy = animate_glitch(t, glitch_chance=0.18)
        screen.blit(surf, (x - surf.get_width() // 2 + gx, y + gy))
        return
    else:
        surf = font.render(text, True, color)

    screen.blit(surf, (x - surf.get_width() // 2, y))


def draw_cutscene(screen, title, lines, t, prompt="Press Enter to continue",
                  map_data=None, animation_config=None):
    if animation_config is None:
        animation_config = {}

    scene_type       = animation_config.get("scene", "ship_corridor")
    title_anim       = animation_config.get("title_anim", "fade")
    lines_anim       = animation_config.get("lines_anim", ["typewriter"] * len(lines))
    duration         = animation_config.get("duration", 3.0)
    glitch_intensity = animation_config.get("glitch_intensity", 0.08)

    draw_scene_background(screen, scene_type, t)

    if glitch_intensity > 0:
        draw_corrupted_screen(screen, t, intensity=glitch_intensity)

    panel = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 120))
    screen.blit(panel, (0, 0))

    title_font = pygame.font.SysFont("courier", 30, bold=True)
    body_font  = pygame.font.SysFont("courier", 19)
    sub_font   = pygame.font.SysFont("courier", 15)

    line_start_times = [i * 0.55 for i in range(len(lines))]

    y = 90
    draw_text_with_animation(
        screen, title, WIDTH // 2, y, title_font, (210, 220, 240),
        animation_type=title_anim, t=t, duration=0.8,
    )

    pygame.draw.line(screen, (60, 100, 160),
                     (WIDTH // 2 - 260, y + 38), (WIDTH // 2 + 260, y + 38), 1)

    y += 60

    for i, line in enumerate(lines):
        anim_type = lines_anim[i] if i < len(lines_anim) else "typewriter"
        line_time = max(0.0, t - line_start_times[i])
        if line_time > 0:
            shade = max(170, 210 - i * 8)
            draw_text_with_animation(
                screen, line, WIDTH // 2, y, body_font, (shade, shade + 6, shade + 20),
                animation_type=anim_type, t=line_time, duration=1.5,
            )
        y += 32

    if map_data:
        draw_compound_map(screen, map_data)

    prompt_alpha = int((math.sin(t * 2.8) + 1) * 0.5 * 90) + 140
    prompt_surf  = sub_font.render(prompt, True, (140, 160, 190))
    prompt_surf.set_alpha(prompt_alpha)
    screen.blit(prompt_surf, (WIDTH // 2 - prompt_surf.get_width() // 2, HEIGHT - 64))


def draw_compound_map(screen, map_data):
    box   = pygame.Rect(60, 190, WIDTH - 120, 240)
    panel = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
    panel.fill((8, 14, 24, 210))
    pygame.draw.rect(panel, (70, 110, 160, 200), panel.get_rect(), 2)

    for x in range(0, box.width, 22):
        pygame.draw.line(panel, (30, 50, 80), (x, 0), (x, box.height), 1)
    for y in range(0, box.height, 22):
        pygame.draw.line(panel, (30, 50, 80), (0, y), (box.width, y), 1)

    for link in map_data.get("links", []):
        x1, y1 = link["a"]
        x2, y2 = link["b"]
        pygame.draw.line(panel, (120, 170, 220), (x1, y1), (x2, y2), 2)

    for room in map_data.get("rooms", []):
        rect = pygame.Rect(room["x"], room["y"], room["w"], room["h"])
        pygame.draw.rect(panel, room["color"], rect)
        pygame.draw.rect(panel, (200, 220, 240), rect, 1)
        label = map_data["font"].render(room["name"], True, (230, 240, 250))
        panel.blit(label, (rect.x + 5, rect.y + 4))

    screen.blit(panel, (box.x, box.y))


def _draw_point_text(screen, t, weak=False):
    font = pygame.font.SysFont("courier", 150, bold=True)
    text = random.choice(["ENEMY TERMINATED", "TARGET ELIMINATED", "BOSS DESTROYED", "POINT", "CRITICAL HIT"])
    base = font.render(text, True, (245, 245, 250))

    if weak:
        k    = min(1.0, t / 0.06)
        slam = 2.0 - 1.0 * (k * k * (3 - 2 * k))
        alpha = int(150 + 80 * math.sin(t * 22))
    else:
        k    = min(1.0, t / 0.4)
        slam = 2.0 - 1.0 * (k * k * (3 - 2 * k))
        alpha = int(255 * min(1.0, t / 0.25))

    w = max(1, int(base.get_width() * slam))
    h = max(1, int(base.get_height() * slam))
    surf = pygame.transform.scale(base, (w, h))

    cx, cy = WIDTH // 2, HEIGHT // 2 + 30
    gx, gy = animate_glitch(t, glitch_chance=0.3)

    if not weak:
        red   = surf.copy()
        red.fill((255, 0, 90), special_flags=pygame.BLEND_RGBA_MULT)
        red.set_alpha(int(alpha * 0.85))
        cyan  = surf.copy()
        cyan.fill((0, 200, 255), special_flags=pygame.BLEND_RGBA_MULT)
        cyan.set_alpha(int(alpha * 0.85))
        screen.blit(cyan, (cx - w // 2 - 6 + gx, cy - h // 2 + gy))
        screen.blit(red,  (cx - w // 2 + 6 + gx, cy - h // 2 + gy))
        tear = random.randint(-2, 2)
        if random.random() < 0.35:
            slice_surf = surf.copy()
            slice_surf.set_alpha(int(alpha * 0.9))
            screen.blit(slice_surf, (cx - w // 2 + gx + tear * 14, cy - h // 2 + gy + tear * 8))

    surf.set_alpha(alpha)
    screen.blit(surf, (cx - w // 2 + gx, cy - h // 2 + gy))


def draw_boss_kill(screen, t, boss_sprite, bg=None, duration=4.2):
    t        = max(0.0, t)
    fire_t   = 0.4
    impact_t = 1.6
    fall_t   = 2.6
    text_t   = 1.2

    # --- frozen frame background with slight slow-mo zoom ---
    if bg is not None:
        zoom = 1.0 + 0.04 * min(1.0, t / 2.0)
        z_w  = int(WIDTH * zoom)
        z_h  = int(HEIGHT * zoom)
        zx   = (WIDTH - z_w) // 2
        zy   = (HEIGHT - z_h) // 2
        try:
            scaled = pygame.transform.smoothscale(bg, (z_w, z_h))
            screen.blit(scaled, (zx, zy))
        except Exception:
            screen.blit(bg, (0, 0))
    else:
        screen.fill((4, 6, 12))

    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 130))
    screen.blit(dim, (0, 0))

    slow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    slow.fill((40, 120, 255, int(60 + 30 * math.sin(t * 6))))
    screen.blit(slow, (0, 0))
    _scanlines(screen, 0.5)

    # --- geometry ---
    bx = WIDTH // 2
    by_stand  = int(HEIGHT * 0.40)
    by_ground = int(HEIGHT * 0.70)

    # --- glitchy POINT text (behind the action) ---
    if t >= text_t:
        _draw_point_text(screen, t - text_t)
    elif t > 0.0 and random.random() < 0.4:
        _draw_point_text(screen, 0.02, weak=True)

    # ground shadow
    shadow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 130), (bx - 115, by_ground - 10, 230, 28))
    screen.blit(shadow, (0, 0))

    # --- boss knockdown ---
    boss_angle = 0.0
    by = by_stand
    size_scale = 1.0
    shake = 0
    if t >= impact_t:
        f = min(1.0, (t - impact_t) / (fall_t - impact_t))
        f = 1 - (1 - f) * (1 - f)
        boss_angle = -90 * f
        by = by_stand + int((by_ground - by_stand) * f)
        if f >= 1.0:
            squash = max(0.0, 1 - (t - fall_t) * 2.5)
            size_scale = 1.0 - 0.14 * squash
            by += int(6 * squash)
        if t < impact_t + 0.35:
            shake = random.randint(-3, 3)

    boss_size = int(250 * size_scale)
    if boss_sprite is not None:
        try:
            base_img = pygame.transform.smoothscale(boss_sprite, (boss_size, boss_size))
            img = pygame.transform.rotate(base_img, boss_angle)
        except Exception:
            img = pygame.Surface((boss_size, boss_size), pygame.SRCALPHA)
            img.fill((120, 20, 30))
        screen.blit(img, (bx - img.get_width() // 2 + shake, by - img.get_height() // 2))
    else:
        fallback = pygame.Surface((boss_size, boss_size), pygame.SRCALPHA)
        pygame.draw.rect(fallback, (140, 30, 40), fallback.get_rect(), border_radius=14)
        pygame.draw.rect(fallback, (200, 60, 70), fallback.get_rect(), 3, border_radius=14)
        screen.blit(fallback, (bx - boss_size // 2 + shake, by - boss_size // 2))

    # dust puff at landing
    if t >= fall_t and t < fall_t + 0.6:
        dt = t - fall_t
        for i in range(6):
            ang = math.pi * 0.25 + i * 0.1
            pr = int((dt / 0.6) * (26 + i * 5))
            px = bx + int(math.cos(ang) * pr * 2) - pr
            py = by_ground - int((dt / 0.6) * 18)
            dust = pygame.Surface((pr * 2, pr * 2), pygame.SRCALPHA)
            pygame.draw.circle(dust, (150, 130, 120, max(0, int(90 * (1 - dt / 0.6)))), (pr, pr), pr)
            screen.blit(dust, (px, py))

    # --- slow-motion bullet ---
    if t >= fire_t:
        if t < impact_t:
            s = (t - fire_t) / (impact_t - fire_t)
        else:
            s = 1.0
        ease = s * s * (3 - 2 * s)
        start_y = HEIGHT - 120
        cur_y   = start_y + (by_stand - start_y) * ease
        sway    = math.sin(s * math.pi * 3) * 8
        bp = (bx + int(sway), int(cur_y))

        for k in range(5, 0, -1):
            s_prev = max(0.0, s - k * 0.035)
            p_y = start_y + (by_stand - start_y) * (s_prev * s_prev * (3 - 2 * s_prev))
            p_x = bx + int(math.sin(s_prev * math.pi * 3) * 8)
            a   = max(0, 140 - k * 24)
            tr  = pygame.Surface((12, 12), pygame.SRCALPHA)
            pygame.draw.circle(tr, (255, 230, 120, a), (6, 6), 5)
            screen.blit(tr, (p_x - 6, int(p_y) - 6))

        glow = pygame.Surface((22, 22), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 240, 160, 220), (11, 11), 9)
        screen.blit(glow, (bp[0] - 11, bp[1] - 11))
        pygame.draw.circle(screen, (255, 255, 255), bp, 4)

    # --- impact flash + shockwave ---
    if t >= impact_t and t < impact_t + 0.55:
        ft = t - impact_t
        flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash.fill((255, 255, 255, int(230 * (1 - ft / 0.55))))
        screen.blit(flash, (0, 0))
        ring_r = int(12 + 150 * (ft / 0.55))
        ring   = pygame.Surface((ring_r * 2, ring_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(ring, (255, 220, 120, int(200 * (1 - ft / 0.55))), (ring_r, ring_r), ring_r, 3)
        screen.blit(ring, (bx - ring_r, by_stand - ring_r))

    # --- corruption on top ---
    _glitch_block(screen, 0.10)

    # --- fade out at the end ---
    if t > duration - 0.6:
        out = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        out.fill((0, 0, 0, int(255 * min(1.0, (t - (duration - 0.6)) / 0.6))))
        screen.blit(out, (0, 0))

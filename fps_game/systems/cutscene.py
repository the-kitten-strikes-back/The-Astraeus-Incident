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
        pygame.draw.rect(screen, (la, la + 40, la + 80), (x - 18, 0, 36, 10))
        pygame.draw.rect(screen, (la // 3, la // 3 + 10, la // 3 + 30), (x - 10, 10, 20, HEIGHT - 10))
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
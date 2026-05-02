import math
import pygame

from core.settings import WIDTH, HEIGHT


HUD_PRIMARY   = (120, 210, 255)
HUD_SECONDARY = (60,  140, 190)
HUD_ACCENT    = (90,  255, 210)


def draw_crosshair(screen, hit=False, pulse=0.0):
    cx, cy = WIDTH // 2, HEIGHT // 2
    size   = 10 + int(6 * pulse)
    alpha  = max(0, min(255, 200 + int(55 * pulse)))
    color  = (alpha, alpha, alpha)
    pygame.draw.line(screen, color, (cx - size, cy), (cx + size, cy), 2)
    pygame.draw.line(screen, color, (cx, cy - size), (cx, cy + size), 2)
    if hit:
        color    = (255, 60, 60)
        hit_size = 12 + int(6 * pulse)
        pygame.draw.line(screen, color, (cx - hit_size, cy - hit_size), (cx + hit_size, cy + hit_size), 2)
        pygame.draw.line(screen, color, (cx - hit_size, cy + hit_size), (cx + hit_size, cy - hit_size), 2)


def draw_level_hud(screen, font, level_index, player):
    level_text = f"SECTOR {level_index + 1}"
    surf = font.render(level_text, True, (180, 210, 240))
    screen.blit(surf, (12, 10))

    bar_w = 180
    bar_h = 18
    x, y  = 12, 38
    pygame.draw.rect(screen, (40, 40, 40), (x, y, bar_w, bar_h))
    ratio = max(0, player.health) / player.max_health
    bar_color = (200, 40, 40) if ratio < 0.3 else (60, 180, 80) if ratio > 0.6 else (200, 160, 40)
    pygame.draw.rect(screen, bar_color, (x, y, int(bar_w * ratio), bar_h))
    hp_text = font.render(f"VITALS {max(0, player.health)}%", True, (210, 220, 240))
    screen.blit(hp_text, (x + bar_w + 10, y - 2))


def draw_ammo(screen, font, player):
    weapon  = player.get_weapon()
    text    = f"AMMO  {weapon.ammo} / {weapon.max_ammo}"
    surf    = font.render(text, True, (200, 210, 140))
    screen.blit(surf, (WIDTH - 200, HEIGHT - 30))


def draw_score(screen, font, score, kills, pulse=0.0):
    base  = 255
    glow  = int(140 * pulse)
    color = (base, min(255, base + glow), min(255, base + glow))
    screen.blit(font.render(f"SCORE  {score}", True, color), (WIDTH - 200, 10))
    screen.blit(font.render(f"NEUTRALIZED  {kills}", True, color), (WIDTH - 200, 35))


def draw_overlay_messages(screen, messages, flicker=0.0):
    if not messages:
        return
    font = pygame.font.SysFont("courier", 17, bold=True)
    y    = 70
    for msg in messages:
        alpha = max(0, min(255, msg["timer"] * 18))
        color = (220, 80 + int(60 * flicker), 80 + int(60 * flicker))
        surf  = font.render(msg["text"], True, color)
        surf.set_alpha(alpha)
        rect  = surf.get_rect(center=(WIDTH // 2, y))
        screen.blit(surf, rect)
        y += 24


def draw_room_label(screen, room_name, strength=1.0, flicker=0.0):
    if not room_name:
        return
    font  = pygame.font.SysFont("courier", 22, bold=True)
    alpha = max(0, min(255, int(220 * strength)))
    glow  = int(40 + 40 * flicker)
    color = (min(255, 180 + glow), min(255, 210 + glow), 255)
    surf  = font.render(f"// {room_name.upper()} //", True, color)
    surf.set_alpha(alpha)
    rect  = surf.get_rect(center=(WIDTH // 2, 40))
    screen.blit(surf, rect)


def draw_weapon_info(screen, player):
    font   = pygame.font.SysFont("courier", 18)
    weapon = player.get_weapon()
    text   = f"{weapon.name.upper()}  |  {weapon.ammo} / {weapon.max_ammo}"
    surf   = font.render(text, True, (200, 210, 140))
    screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT - 40))


def draw_hit_flash(screen, amount=90):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((160, 0, 0, amount))
    screen.blit(overlay, (0, 0))


def draw_game_over(screen, font):
    t       = pygame.time.get_ticks() / 1000.0
    pulse   = (math.sin(t * 2.4) + 1) * 0.5

    panel   = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 160))
    screen.blit(panel, (0, 0))

    title_font = pygame.font.SysFont("courier", 44, bold=True)
    body_font  = pygame.font.SysFont("courier", 20)
    tiny_font  = pygame.font.SysFont("courier", 15)

    cy = HEIGHT // 2 - 60

    go_surf = title_font.render("OPERATIVE LOST", True, (220, 60, 60))
    screen.blit(go_surf, (WIDTH // 2 - go_surf.get_width() // 2, cy))

    cy += 56
    sub_surf = body_font.render("Suit telemetry flat. Temporal anchor severed.", True, (180, 190, 210))
    screen.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, cy))

    cy += 28
    sub2 = body_font.render("The Astraeus continues without you.", True, (140, 150, 170))
    screen.blit(sub2, (WIDTH // 2 - sub2.get_width() // 2, cy))

    cy += 48
    restart_a = int(180 + 75 * pulse)
    restart_surf = body_font.render("[ R ]  RE-INITIALIZE OPERATIVE", True, (160, 200, 240))
    restart_surf.set_alpha(restart_a)
    screen.blit(restart_surf, (WIDTH // 2 - restart_surf.get_width() // 2, cy))

    cy += 26
    note = tiny_font.render("All temporal data will be reset. The entity will remember.", True, (80, 100, 130))
    screen.blit(note, (WIDTH // 2 - note.get_width() // 2, cy))


def draw_pause(screen):
    t    = pygame.time.get_ticks() / 1000.0
    panel = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 140))
    screen.blit(panel, (0, 0))

    font     = pygame.font.SysFont("courier", 36, bold=True)
    sub_font = pygame.font.SysFont("courier", 16)

    pulse = (math.sin(t * 1.8) + 1) * 0.5
    a     = int(200 + 55 * pulse)

    pause_surf = font.render("// PAUSED //", True, (180, 210, 240))
    pause_surf.set_alpha(a)
    screen.blit(pause_surf, (WIDTH // 2 - pause_surf.get_width() // 2, HEIGHT // 2 - 30))

    note = sub_font.render("Time continues outside this vessel. Proceed when ready.", True, (90, 120, 160))
    screen.blit(note, (WIDTH // 2 - note.get_width() // 2, HEIGHT // 2 + 20))

    esc_surf = sub_font.render("[ ESC ]  RESUME", True, (100, 140, 180))
    screen.blit(esc_surf, (WIDTH // 2 - esc_surf.get_width() // 2, HEIGHT // 2 + 50))


def draw_scifi_hud(screen, phase=0.0, alert=False):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pulse   = 0.5 + 0.5 * math.sin(phase)
    glow    = int(40 + 40 * pulse)
    frame   = (*HUD_PRIMARY, 170 if not alert else 220)
    grid    = (*HUD_SECONDARY, 22)
    accent  = (*HUD_ACCENT, 160)

    for x in range(0, WIDTH, 90):
        pygame.draw.line(overlay, grid, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, 70):
        pygame.draw.line(overlay, grid, (0, y), (WIDTH, y), 1)



    panel_h = 70
    panel_y = HEIGHT - panel_h - 10
    panel   = pygame.Rect(18, panel_y, WIDTH - 36, panel_h)
    pygame.draw.rect(overlay, (*HUD_SECONDARY, 40), panel, border_radius=10)
    pygame.draw.rect(overlay, frame, panel, 2, border_radius=10)
    pygame.draw.line(overlay, accent, (panel.left + 12, panel_y + 18), (panel.left + 220, panel_y + 18), 2)
    pygame.draw.line(overlay, (*HUD_PRIMARY, 120), (panel.right - 240, panel_y + 18), (panel.right - 14, panel_y + 18), 1)
    for i in range(6):
        x = panel.left + 12 + i * 26
        pygame.draw.line(overlay, (*HUD_PRIMARY, 120), (x, panel_y + 30), (x + 12, panel_y + 30), 2)

    bar_h   = 140
    left_bar  = pygame.Rect(16, HEIGHT - bar_h - 110, 18, bar_h)
    right_bar = pygame.Rect(WIDTH - 34, HEIGHT - bar_h - 110, 18, bar_h)
    for bar in (left_bar, right_bar):
        pygame.draw.rect(overlay, (*HUD_SECONDARY, 30), bar)
        pygame.draw.rect(overlay, frame, bar, 2)
    fill_h = int(bar_h * (0.35 + 0.6 * pulse))
    pygame.draw.rect(overlay, accent, pygame.Rect(left_bar.x + 3,  left_bar.bottom  - fill_h - 3, left_bar.w  - 6, fill_h))
    pygame.draw.rect(overlay, accent, pygame.Rect(right_bar.x + 3, right_bar.bottom - fill_h - 3, right_bar.w - 6, fill_h))

    top_y = 16
    for i in range(0, WIDTH, 60):
        tick_h = 6 + int(6 * (i / 60 % 2))
        pygame.draw.line(overlay, (*HUD_PRIMARY, 140), (i + 10, top_y), (i + 10, top_y + tick_h), 1)
    pygame.draw.line(overlay, (*HUD_ACCENT, 190), (WIDTH // 2 - 50, top_y + 18), (WIDTH // 2 + 50, top_y + 18), 2)

    scan_y = int((phase * 40) % HEIGHT)
    scan_color = (130, 220, 255, 45 if not alert else 75)
    pygame.draw.line(overlay, scan_color, (0, scan_y), (WIDTH, scan_y), 2)
    pygame.draw.line(overlay, scan_color, (0, (scan_y + 2) % HEIGHT), (WIDTH, (scan_y + 2) % HEIGHT), 1)

    for i in range(40):
        x = (i * 73 + int(phase * 120)) % WIDTH
        y = (i * 37 + int(phase * 80))  % HEIGHT
        overlay.set_at((x, y), (HUD_PRIMARY[0], HUD_PRIMARY[1], HUD_PRIMARY[2], 60))

    halo_radius = 28 + int(6 * pulse)
    pygame.draw.circle(overlay, (*HUD_PRIMARY, 60),  (WIDTH // 2, HEIGHT // 2), halo_radius,      1)
    pygame.draw.circle(overlay, (*HUD_ACCENT,  80),  (WIDTH // 2, HEIGHT // 2), halo_radius + 10, 1)

    if alert:
        alert_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        alert_surface.fill((255, 40, 40, 18 + glow))
        overlay.blit(alert_surface, (0, 0))

    screen.blit(overlay, (0, 0))


def draw_sniper_scope(screen, radius=None):
    cx, cy = WIDTH // 2, HEIGHT // 2
    if radius is None:
        radius = int(min(WIDTH, HEIGHT) * 0.42)

    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 235))
    pygame.draw.circle(shade, (0, 0, 0, 0), (cx, cy), radius)
    screen.blit(shade, (0, 0))

    ring_color = (210, 220, 235)
    tick_color = (170, 190, 210)
    pygame.draw.circle(screen, ring_color, (cx, cy), radius, 2)
    pygame.draw.line(screen, ring_color, (cx - radius, cy), (cx + radius, cy), 1)
    pygame.draw.line(screen, ring_color, (cx, cy - radius), (cx, cy + radius), 1)

    tick = 12
    pygame.draw.line(screen, tick_color, (cx - tick, cy - radius + 40), (cx + tick, cy - radius + 40), 1)
    pygame.draw.line(screen, tick_color, (cx - tick, cy + radius - 40), (cx + tick, cy + radius - 40), 1)
    pygame.draw.line(screen, tick_color, (cx - radius + 40, cy - tick), (cx - radius + 40, cy + tick), 1)
    pygame.draw.line(screen, tick_color, (cx + radius - 40, cy - tick), (cx + radius - 40, cy + tick), 1)
    pygame.draw.circle(screen, ring_color, (cx, cy), 3)

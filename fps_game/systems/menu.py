import math
import pygame
from core.settings import WIDTH, HEIGHT


def draw_menu(screen):
    t = pygame.time.get_ticks() / 1000.0

    title_font   = pygame.font.SysFont("courier", 52, bold=True)
    sub_font     = pygame.font.SysFont("courier", 18, bold=True)
    body_font    = pygame.font.SysFont("courier", 15)
    tiny_font    = pygame.font.SysFont("courier", 13)

    pulse = (math.sin(t * 1.6) + 1) * 0.5
    glow_a = int(60 + 80 * pulse)

    title_surf = title_font.render("ASTRAEUS", True, (200, 215, 240))
    glow_surf  = title_font.render("ASTRAEUS", True, (60, 120, 220))
    glow_surf.set_alpha(glow_a)

    tx = WIDTH // 2 - title_surf.get_width() // 2
    ty = HEIGHT // 4 - title_surf.get_height() // 2

    screen.blit(glow_surf, (tx + 3, ty + 3))
    screen.blit(title_surf, (tx, ty))

    sub_surf = sub_font.render("DEEP-SPACE TEMPORAL RESEARCH VESSEL", True, (100, 140, 190))
    screen.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, ty + 64))

    pygame.draw.line(screen, (50, 80, 130),
                     (WIDTH // 2 - 280, ty + 88), (WIDTH // 2 + 280, ty + 88), 1)

    status_lines = [
        "VESSEL STATUS: ACTIVE",
        "CREW STATUS: UNRESPONSIVE",
        "TEMPORAL COHERENCE: 38%",
        "CORE TEMPERATURE: CRITICAL",
    ]
    sy = ty + 106
    for i, line in enumerate(status_lines):
        flicker = 0.6 + 0.4 * math.sin(t * (2.1 + i * 0.7) + i)
        a = int(180 * flicker)
        color = (80, 140, 200) if i < 2 else (220, 80, 80)
        surf = body_font.render(line, True, color)
        surf.set_alpha(a)
        screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, sy + i * 22))

    pygame.draw.line(screen, (50, 80, 130),
                     (WIDTH // 2 - 280, sy + 100), (WIDTH // 2 + 280, sy + 100), 1)

    enter_a = int(160 + 95 * pulse)
    enter_surf = sub_font.render("[ ENTER ]  COMMENCE BOARDING SEQUENCE", True, (180, 200, 240))
    enter_surf.set_alpha(enter_a)
    screen.blit(enter_surf, (WIDTH // 2 - enter_surf.get_width() // 2, sy + 116))

    settings_surf = body_font.render("[ S ]  SUIT CALIBRATION", True, (100, 130, 170))
    screen.blit(settings_surf, (WIDTH // 2 - settings_surf.get_width() // 2, sy + 146))

    quit_surf = body_font.render("[ Q ]  ABORT MISSION", True, (180, 100, 100))
    screen.blit(quit_surf, (WIDTH // 2 - quit_surf.get_width() // 2, sy + 170))

    controls = [
        "WASD: MOVE     MOUSE: AIM     LMB: FIRE     R: RELOAD / REWIND",
        "Q: TIME DILATION     G: TEMPORAL ECHO     E: DOOR",
        "1/2/3: WEAPON     Z/X/C/V: GRENADES     ESC: PAUSE",
        "M: MUTE     [ / ]: VOLUME",
    ]
    cy2 = HEIGHT - 80
    for line in controls:
        cs = tiny_font.render(line, True, (60, 80, 110))
        screen.blit(cs, (WIDTH // 2 - cs.get_width() // 2, cy2))
        cy2 += 18

    warning_a = int(100 + 60 * math.sin(t * 3.4))
    warning = tiny_font.render(
        "WARNING: TEMPORAL ANOMALY DETECTED IN SECTORS 4, 7, 11  —  PROCEED WITH CAUTION",
        True, (180, 60, 60)
    )
    warning.set_alpha(warning_a)
    screen.blit(warning, (WIDTH // 2 - warning.get_width() // 2, HEIGHT - 20))
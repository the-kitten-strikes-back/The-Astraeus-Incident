import math
import pygame
from core.settings import WIDTH, HEIGHT


def draw_settings(screen, settings):
    t = pygame.time.get_ticks() / 1000.0

    title_font = pygame.font.SysFont("courier", 28, bold=True)
    body_font  = pygame.font.SysFont("courier", 18)
    tiny_font  = pygame.font.SysFont("courier", 14)

    title_surf = title_font.render("SUIT CALIBRATION", True, (180, 210, 240))
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, HEIGHT // 3 - 60))

    pygame.draw.line(screen, (50, 80, 130),
                     (WIDTH // 2 - 200, HEIGHT // 3 - 24),
                     (WIDTH // 2 + 200, HEIGHT // 3 - 24), 1)

    sens_val = f"{settings['sensitivity']:.3f}"
    sens_surf = body_font.render(f"AIM SENSITIVITY :  {sens_val}", True, (200, 215, 240))
    screen.blit(sens_surf, (WIDTH // 2 - sens_surf.get_width() // 2, HEIGHT // 3))

    hint_surf = tiny_font.render("UP / DOWN to adjust", True, (90, 120, 160))
    screen.blit(hint_surf, (WIDTH // 2 - hint_surf.get_width() // 2, HEIGHT // 3 + 30))

    pygame.draw.line(screen, (50, 80, 130),
                     (WIDTH // 2 - 200, HEIGHT // 3 + 60),
                     (WIDTH // 2 + 200, HEIGHT // 3 + 60), 1)

    back_a = int(160 + 80 * ((math.sin(t * 2.2) + 1) * 0.5))
    back_surf = body_font.render("[ ESC ]  RETURN TO DOCKING BAY", True, (140, 170, 210))
    back_surf.set_alpha(back_a)
    screen.blit(back_surf, (WIDTH // 2 - back_surf.get_width() // 2, HEIGHT // 3 + 80))

    note_surf = tiny_font.render(
        "Higher sensitivity recommended near the quantum core.", True, (70, 100, 140)
    )
    screen.blit(note_surf, (WIDTH // 2 - note_surf.get_width() // 2, HEIGHT // 3 + 120))
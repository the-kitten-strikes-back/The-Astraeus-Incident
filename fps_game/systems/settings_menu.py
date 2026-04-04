import pygame
from core.settings import WIDTH, HEIGHT


def draw_settings(screen, settings):
    font = pygame.font.SysFont("arial", 30)

    sens = font.render(
        f"Mouse Sensitivity: {settings['sensitivity']:.3f}",
        True,
        (255, 255, 255),
    )
    back = font.render("Press ESC to go back", True, (200, 200, 200))

    screen.blit(sens, (WIDTH // 2 - 200, HEIGHT // 2))
    screen.blit(back, (WIDTH // 2 - 200, HEIGHT // 2 + 50))

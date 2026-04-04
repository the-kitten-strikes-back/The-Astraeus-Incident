import pygame
from core.settings import WIDTH, HEIGHT


def draw_menu(screen):
    font = pygame.font.SysFont("arial", 40)

    title = font.render("FPS GAME", True, (255, 255, 255))
    play = font.render("Press ENTER to Play", True, (200, 200, 200))
    settings = font.render("Press S for Settings", True, (200, 200, 200))

    screen.blit(title, (WIDTH // 2 - 120, HEIGHT // 3))
    screen.blit(play, (WIDTH // 2 - 180, HEIGHT // 2))
    screen.blit(settings, (WIDTH // 2 - 180, HEIGHT // 2 + 50))

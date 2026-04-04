import math
import pygame

from core.settings import WIDTH, HEIGHT


def draw_cutscene(screen, title, lines, t, prompt="Press Enter to continue", map_data=None):
    screen.fill((8, 8, 12))
    flicker = int((math.sin(t * 4) + 1) * 8)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((15 + flicker, 10 + flicker, 25 + flicker, 180))
    screen.blit(overlay, (0, 0))

    title_font = pygame.font.SysFont("arial", 28, bold=True)
    body_font = pygame.font.SysFont("arial", 20)
    sub_font = pygame.font.SysFont("arial", 16)

    y = 80
    title_surf = title_font.render(title, True, (220, 220, 240))
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, y))
    y += 50

    for line in lines:
        surf = body_font.render(line, True, (200, 210, 230))
        screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))
        y += 28

    if map_data:
        draw_compound_map(screen, map_data)

    prompt_surf = sub_font.render(prompt, True, (160, 170, 190))
    screen.blit(prompt_surf, (WIDTH // 2 - prompt_surf.get_width() // 2, HEIGHT - 70))


def draw_compound_map(screen, map_data):
    box = pygame.Rect(60, 180, WIDTH - 120, 250)
    panel = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
    panel.fill((10, 15, 25, 200))
    pygame.draw.rect(panel, (90, 120, 160, 180), panel.get_rect(), 2)

    grid_color = (40, 60, 90)
    for x in range(0, box.width, 24):
        pygame.draw.line(panel, grid_color, (x, 0), (x, box.height), 1)
    for y in range(0, box.height, 24):
        pygame.draw.line(panel, grid_color, (0, y), (box.width, y), 1)

    for link in map_data.get("links", []):
        x1, y1 = link["a"]
        x2, y2 = link["b"]
        pygame.draw.line(panel, (140, 180, 220), (x1, y1), (x2, y2), 2)

    for room in map_data.get("rooms", []):
        rect = pygame.Rect(room["x"], room["y"], room["w"], room["h"])
        pygame.draw.rect(panel, room["color"], rect)
        pygame.draw.rect(panel, (220, 230, 240), rect, 2)
        label = map_data["font"].render(room["name"], True, (230, 240, 250))
        panel.blit(label, (rect.x + 6, rect.y + 4))

    screen.blit(panel, (box.x, box.y))

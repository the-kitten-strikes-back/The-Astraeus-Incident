import pygame

from core.settings import WIDTH, HEIGHT


def draw_crosshair(screen, hit=False, pulse=0.0):
    cx, cy = WIDTH // 2, HEIGHT // 2
    size = 10 + int(6 * pulse)
    alpha = max(0, min(255, 200 + int(55 * pulse)))
    color = (alpha, alpha, alpha)
    pygame.draw.line(screen, color, (cx - size, cy), (cx + size, cy), 2)
    pygame.draw.line(screen, color, (cx, cy - size), (cx, cy + size), 2)
    if hit:
        color = (255, 60, 60)
        hit_size = 12 + int(6 * pulse)
        pygame.draw.line(screen, color, (cx - hit_size, cy - hit_size), (cx + hit_size, cy + hit_size), 2)
        pygame.draw.line(screen, color, (cx - hit_size, cy + hit_size), (cx + hit_size, cy - hit_size), 2)


def draw_level_hud(screen, font, level_index, player):
    level_text = f"Level {level_index + 1}"
    surf = font.render(level_text, True, (230, 230, 230))
    screen.blit(surf, (12, 10))

    bar_w = 180
    bar_h = 18
    x = 12
    y = 38
    pygame.draw.rect(screen, (40, 40, 40), (x, y, bar_w, bar_h))
    ratio = max(0, player.health) / player.max_health
    pygame.draw.rect(screen, (200, 40, 40), (x, y, bar_w * ratio, bar_h))
    hp_text = font.render(f"HP {max(0, player.health)}", True, (230, 230, 230))
    screen.blit(hp_text, (x + bar_w + 10, y - 2))


def draw_ammo(screen, font, player):
    weapon = player.get_weapon()
    text = f"Ammo: {weapon.ammo}/{weapon.max_ammo}"
    surf = font.render(text, True, (255, 255, 0))
    screen.blit(surf, (WIDTH - 160, HEIGHT - 30))


def draw_score(screen, font, score, kills, pulse=0.0):
    base = 255
    glow = int(140 * pulse)
    color = (base, min(255, base + glow), min(255, base + glow))
    s = font.render(f"Score: {score}", True, color)
    k = font.render(f"Kills: {kills}", True, color)
    screen.blit(s, (WIDTH - 160, 10))
    screen.blit(k, (WIDTH - 160, 35))


def draw_overlay_messages(screen, messages, flicker=0.0):
    if not messages:
        return
    font = pygame.font.SysFont("arial", 18, bold=True)
    y = 70
    for msg in messages:
        alpha = max(0, min(255, msg["timer"] * 18))
        color = (220, 80 + int(60 * flicker), 80 + int(60 * flicker))
        surf = font.render(msg["text"], True, color)
        rect = surf.get_rect(center=(WIDTH // 2, y))
        screen.blit(surf, rect)
        y += 24


def draw_room_label(screen, room_name, strength=1.0, flicker=0.0):
    if not room_name:
        return
    font = pygame.font.SysFont("arial", 22, bold=True)
    alpha = max(0, min(255, int(220 * strength)))
    glow = int(40 + 40 * flicker)
    color = (min(255, 200 + glow), min(255, 220 + glow), 255)
    surf = font.render(room_name.upper(), True, color)
    rect = surf.get_rect(center=(WIDTH // 2, 40))
    screen.blit(surf, rect)


def draw_weapon_info(screen, player):
    font = pygame.font.SysFont("arial", 20)
    weapon = player.get_weapon()
    text = f"{weapon.name} | Ammo: {weapon.ammo}/{weapon.max_ammo}"
    surf = font.render(text, True, (255, 255, 0))
    screen.blit(surf, (WIDTH // 2 - 100, HEIGHT - 40))


def draw_hit_flash(screen, amount=90):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((160, 0, 0, amount))
    screen.blit(overlay, (0, 0))


def draw_game_over(screen, font):
    go = font.render("GAME OVER", True, (255, 80, 80))
    sub = font.render("Press R to restart", True, (230, 230, 230))
    screen.blit(go, (WIDTH // 2 - go.get_width() // 2, HEIGHT // 2 - 30))
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 10))


def draw_pause(screen):
    font = pygame.font.SysFont("arial", 40)
    text = font.render("PAUSED", True, (255, 255, 255))
    screen.blit(text, (WIDTH // 2 - 80, HEIGHT // 2))

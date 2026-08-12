import math
import pygame

from core.settings import HALF_FOV, WIDTH, FOV, NUM_RAYS, SCALE, HALF_HEIGHT, WEAPON_PICKUP_RANGE


def draw_weapon_pickups(screen, pickups, player, depth_buffer, anim_time=0.0, sprites=None, font=None):
    for pickup in pickups[:]:
        dx = pickup["x"] - player.x
        dy = pickup["y"] - player.y
        dist = math.hypot(dx, dy)

        theta = math.atan2(dy, dx)
        delta = (theta - player.angle) % (2 * math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi

        if -HALF_FOV < delta < HALF_FOV:
            screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
            size = min(2000 / (dist + 0.0001), 60)
            bob = math.sin(anim_time + (pickup["x"] + pickup["y"]) * 0.01) * 6
            x = screen_x - size // 2
            y = HALF_HEIGHT - size // 2 + bob

            ray_index = max(0, min(NUM_RAYS - 1, int(screen_x * NUM_RAYS / WIDTH)))
            if 0 <= ray_index < len(depth_buffer):
                if dist < depth_buffer[ray_index]:
                    sprite = None
                    if sprites:
                        sprite = sprites.get(pickup["weapon"])
                    if sprite:
                        sw = int(size * 1.4)
                        sh = int(size * 0.9)
                        scaled = pygame.transform.scale(sprite, (sw, sh))
                        screen.blit(scaled, (int(x + size / 2 - sw / 2), int(y + size / 2 - sh / 2)))
                    else:
                        pygame.draw.rect(screen, (255, 200, 80),
                                         (int(x + size / 2 - size / 3), int(y + size / 2 - size / 3),
                                          int(size * 2 / 3), int(size * 2 / 3)))
                        pygame.draw.rect(screen, (120, 80, 30),
                                         (int(x + size / 2 - size / 3), int(y + size / 2 - size / 3),
                                          int(size * 2 / 3), int(size * 2 / 3)), 2)

                    if dist < WEAPON_PICKUP_RANGE and font:
                        label = font.render(f"[E] TAKE {pickup['weapon'].upper()}", True, (255, 220, 120))
                        label_rect = label.get_rect(center=(WIDTH // 2, HALF_HEIGHT + 60))
                        screen.blit(label, label_rect)


def draw_health_packs(screen, health_packs, player, depth_buffer, anim_time=0.0):
    for pack in health_packs[:]:
        dx = pack["x"] - player.x
        dy = pack["y"] - player.y
        dist = math.hypot(dx, dy)

        if dist < 25:
            player.health = min(player.max_health, player.health + 30)
            health_packs.remove(pack)
            continue

        theta = math.atan2(dy, dx)
        delta = (theta - player.angle) % (2 * math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi

        if -HALF_FOV < delta < HALF_FOV:
            screen_x = (delta + HALF_FOV) * (WIDTH / FOV)
            size = min(2000 / (dist + 0.0001), 60)
            bob = math.sin(anim_time + (pack["x"] + pack["y"]) * 0.01) * 6
            x = screen_x - size // 2
            y = HALF_HEIGHT - size // 2 + bob

            ray_index = max(0, min(NUM_RAYS - 1, int(screen_x * NUM_RAYS / WIDTH)))
            if 0 <= ray_index < len(depth_buffer):
                if dist < depth_buffer[ray_index]:
                    pygame.draw.circle(
                        screen,
                        (0, 255, 0),
                        (int(x + size / 2), int(y + size / 2)),
                        max(3, int(size / 6)),
                    )

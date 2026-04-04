import math
import pygame

from core.settings import WIDTH, HALF_HEIGHT, FOV, HALF_FOV, NUM_RAYS, MAX_DEPTH, DELTA_ANGLE, TILE, SCALE


def raycast(world, player, screen, textures=None, doors=None, door_texture=None):
    depth_buffer = []
    cur_angle = player.angle - HALF_FOV

    for ray in range(NUM_RAYS):
        depth_wall = MAX_DEPTH

        for depth in range(1, MAX_DEPTH):
            x = player.x + depth * math.cos(cur_angle)
            y = player.y + depth * math.sin(cur_angle)

            tile_x = int(x // TILE) * TILE
            tile_y = int(y // TILE) * TILE

            door = doors.get((tile_x, tile_y)) if doors else None
            hit_wall = (tile_x, tile_y) in world
            hit_door = door is not None and not door.get("open")
            if hit_wall or hit_door:
                depth *= math.cos(player.angle - cur_angle)
                depth_wall = depth
                proj_height = (TILE * 300) / (depth + 0.0001)
                color = 255 / (1 + depth * depth * 0.0001)
                if hit_door and door_texture is not None:
                    tex = door_texture
                elif textures:
                    key = world.get((tile_x, tile_y), "#")
                    tex = textures.get(key)
                else:
                    tex = None
                if tex is not None:
                    if tex:
                        tex_w = tex.get_width()
                        tex_h = tex.get_height()
                        tex_x = int((x % TILE) / TILE * tex_w)
                        tex_x = max(0, min(tex_w - 1, tex_x))
                        column = tex.subsurface((tex_x, 0, 1, tex_h))
                        column = pygame.transform.scale(column, (SCALE, int(proj_height)))
                        shade = max(40, min(255, int(color)))
                        column.fill((shade, shade, shade), special_flags=pygame.BLEND_MULT)
                        screen.blit(column, (ray * SCALE, HALF_HEIGHT - proj_height // 2))
                else:
                    pygame.draw.rect(
                        screen,
                        (color, color, color),
                        (ray * SCALE, HALF_HEIGHT - proj_height // 2, SCALE, proj_height),
                    )
                break

        depth_buffer.append(depth_wall)
        cur_angle += DELTA_ANGLE

    return depth_buffer

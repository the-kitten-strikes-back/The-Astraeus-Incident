def is_wall(x, y, world, tile_size, doors=None):
    tile_x = int(x // tile_size) * tile_size
    tile_y = int(y // tile_size) * tile_size
    if (tile_x, tile_y) in world:
        return True
    if doors:
        door = doors.get((tile_x, tile_y))
        if door and not door.get("open"):
            return True
    return False

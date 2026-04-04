from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import os
import math
import heapq

# 3D FPS using Ursina FirstPersonController
# Features: doors + interact, enemies, pickups, skybox, minimap, weapon + muzzle flash,
# map loading from text file, basic obstacle avoidance.

app = Ursina()
window.title = 'Ursina 3D FPS'
window.color = color.black

LEVEL_PATH = os.path.join(os.path.dirname(__file__), 'level_map.txt')
TILE_SIZE = 2.0

# HUD state
hp = 100
ammo = 60

# Settings
BULLET_SPEED = 28.0
FIRE_COOLDOWN = 0.15
ENEMY_SPEED = 2.3
ENEMY_HIT_RANGE = 1.2
ENEMY_DAMAGE_COOLDOWN = 0.8
PICKUP_RESPAWN = 12.0

fire_timer = 0.0
hurt_timer = 0.0

# World containers
walls = []
doors = []
door_grid = {}
enemies = []
projectiles = []
pickups = []
map_rows = []

# Sky
sky = Sky(color=color.rgb(60, 80, 120))

# Ground
ground = Entity(
    model='plane',
    texture='white_cube',
    texture_scale=(40, 40),
    scale=80,
    color=color.dark_gray,
    collider='box'
)

# Player
player = FirstPersonController()
player.cursor.visible = True
player.gravity = 1
player.speed = 6
player.position = (0, 2, 0)

# Weapon mesh (simple custom mesh attached to camera)
def make_gun_mesh():
    # Two boxy parts combined into one mesh
    # Base box
    verts = [
        Vec3(-0.5, -0.2, -0.9), Vec3(0.5, -0.2, -0.9), Vec3(0.5, 0.2, -0.9), Vec3(-0.5, 0.2, -0.9),
        Vec3(-0.5, -0.2, 0.1), Vec3(0.5, -0.2, 0.1), Vec3(0.5, 0.2, 0.1), Vec3(-0.5, 0.2, 0.1),
    ]
    # Upper box
    verts += [
        Vec3(-0.3, 0.2, -0.6), Vec3(0.3, 0.2, -0.6), Vec3(0.3, 0.45, -0.6), Vec3(-0.3, 0.45, -0.6),
        Vec3(-0.3, 0.2, 0.0), Vec3(0.3, 0.2, 0.0), Vec3(0.3, 0.45, 0.0), Vec3(-0.3, 0.45, 0.0),
    ]

    def box_tris(offset):
        o = offset
        return [
            o+0, o+1, o+2, o+0, o+2, o+3,  # back
            o+4, o+5, o+6, o+4, o+6, o+7,  # front
            o+0, o+4, o+7, o+0, o+7, o+3,  # left
            o+1, o+5, o+6, o+1, o+6, o+2,  # right
            o+3, o+2, o+6, o+3, o+6, o+7,  # top
            o+0, o+1, o+5, o+0, o+5, o+4,  # bottom
        ]

    tris = box_tris(0) + box_tris(8)
    return Mesh(vertices=verts, triangles=tris, mode='triangle')


weapon_base_pos = Vec3(0.35, -0.28, 0.6)
weapon = Entity(
    model=make_gun_mesh(),
    color=color.rgb(80, 80, 90),
    scale=0.35,
    position=weapon_base_pos,
    rotation=(0, 10, 0),
    parent=camera.ui,
    z=-1
)

muzzle_flash = Entity(
    model='quad',
    color=color.yellow,
    scale=0.15,
    position=(0.42, -0.24, 0.5),
    parent=camera.ui,
    z=-1,
    enabled=False
)

recoil = 0.0
recoil_vel = 0.0

# HUD
hp_text = Text(text=f'HP {hp}', position=(-0.88, 0.46), scale=1.4, color=color.white)
ammo_text = Text(text=f'Ammo {ammo}', position=(-0.88, 0.40), scale=1.2, color=color.white)

# Minimap
minimap = Entity(parent=camera.ui, position=(-0.72, 0.2), scale=(0.22, 0.22), model='quad', color=color.rgba(20, 20, 20, 160))
minimap_walls = []
minimap_enemies = []
minimap_player = Entity(parent=minimap, model='quad', color=color.red, scale=(0.05, 0.05), position=(0, 0, -0.01))


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def load_map(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, 'r', encoding='utf-8') as f:
        return [line.rstrip('\n') for line in f if line.strip()]


def grid_to_world(x, y, rows, cols):
    wx = (x - cols / 2) * TILE_SIZE
    wz = (rows / 2 - y) * TILE_SIZE
    return wx, wz


def world_to_grid(wx, wz, rows, cols):
    gx = int(round(wx / TILE_SIZE + cols / 2))
    gy = int(round(rows / 2 - wz / TILE_SIZE))
    gx = clamp(gx, 0, cols - 1)
    gy = clamp(gy, 0, rows - 1)
    return gx, gy


def is_walkable(gx, gy):
    if gy < 0 or gy >= len(map_rows) or gx < 0 or gx >= len(map_rows[0]):
        return False
    ch = map_rows[gy][gx]
    if ch == '#':
        return False
    if ch == 'D':
        d = door_grid.get((gx, gy))
        return d is not None and d.is_open
    return True


def has_los_world(a, b):
    # Simple stepped LOS check in world space
    steps = int(distance(a, b) / 0.5) + 1
    if steps <= 1:
        return True
    for i in range(1, steps):
        t = i / steps
        p = lerp(a, b, t)
        gx, gy = world_to_grid(p.x, p.z, map_h, map_w)
        if not is_walkable(gx, gy) and (gx, gy) != world_to_grid(a.x, a.z, map_h, map_w):
            return False
    return True


def astar(start, goal):
    if start == goal:
        return [start]
    open_set = []
    heapq.heappush(open_set, (0, start))
    came = {}
    g_score = {start: 0}

    def h(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came:
                current = came[current]
                path.append(current)
            path.reverse()
            return path

        cx, cy = current
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if not is_walkable(nx, ny):
                continue
            tentative = g_score[current] + 1
            if tentative < g_score.get((nx, ny), 1e9):
                came[(nx, ny)] = current
                g_score[(nx, ny)] = tentative
                f = tentative + h((nx, ny), goal)
                heapq.heappush(open_set, (f, (nx, ny)))
    return []


def spawn_level():
    global walls, doors, enemies, pickups, map_rows, door_grid
    rows = load_map(LEVEL_PATH)
    map_rows = rows
    h = len(rows)
    w = len(rows[0])

    for y in range(h):
        for x in range(w):
            ch = rows[y][x]
            wx, wz = grid_to_world(x, y, h, w)

            if ch == '#':
                wall = Entity(
                    model='cube',
                    color=color.gray,
                    scale=(TILE_SIZE, TILE_SIZE * 1.6, TILE_SIZE),
                    position=(wx, TILE_SIZE * 0.8, wz),
                    collider='box'
                )
                walls.append(wall)
                add_minimap_wall(x, y, w, h)

            elif ch == 'D':
                door = Entity(
                    model='cube',
                    color=color.rgb(120, 90, 60),
                    scale=(TILE_SIZE, TILE_SIZE * 1.4, TILE_SIZE * 0.35),
                    position=(wx, TILE_SIZE * 0.7, wz),
                    collider='box'
                )
                door.is_open = False
                door.grid = (x, y)
                doors.append(door)
                door_grid[(x, y)] = door
                add_minimap_wall(x, y, w, h, color=color.rgb(120, 90, 60))

            elif ch == 'P':
                player.position = (wx, 2, wz)

            elif ch == 'E':
                e = Entity(
                    model='cube',
                    color=color.orange,
                    scale=(0.8, 1.6, 0.8),
                    position=(wx, 0.8, wz),
                    collider='box'
                )
                e.health = 3
                e.repath = 0.0
                e.path = []
                e.path_i = 0
                e.avoid_phase = random.uniform(0, math.tau)
                enemies.append(e)
                add_minimap_enemy(e, w, h)

            elif ch == 'H':
                spawn_pickup(wx, wz, 'health')

            elif ch == 'A':
                spawn_pickup(wx, wz, 'ammo')

    return w, h


def add_minimap_wall(x, y, w, h, color=color.rgb(90, 90, 90)):
    fx = (x / (w - 1)) - 0.5
    fy = 0.5 - (y / (h - 1))
    m = Entity(parent=minimap, model='quad', color=color, scale=(0.02, 0.02), position=(fx, fy, -0.02))
    minimap_walls.append(m)


def add_minimap_enemy(e, w, h):
    m = Entity(parent=minimap, model='quad', color=color.orange, scale=(0.03, 0.03), position=(0, 0, -0.01))
    m.track = e
    m.map_w = w
    m.map_h = h
    minimap_enemies.append(m)


def update_minimap(w, h):
    px, pz = player.position.x, player.position.z
    fx = (px / (w * TILE_SIZE)) + 0.5
    fy = 0.5 - (pz / (h * TILE_SIZE))
    minimap_player.position = (fx - 0.5, fy - 0.5, -0.01)

    for m in minimap_enemies:
        if not m.track.enabled:
            m.enabled = False
            continue
        ex, ez = m.track.position.x, m.track.position.z
        fx = (ex / (w * TILE_SIZE)) + 0.5
        fy = 0.5 - (ez / (h * TILE_SIZE))
        m.position = (fx - 0.5, fy - 0.5, -0.01)


def spawn_pickup(x, z, kind):
    if kind == 'health':
        col = color.lime
    else:
        col = color.cyan
    p = Entity(
        model='sphere',
        color=col,
        scale=0.4,
        position=(x, 0.3, z),
        collider='box'
    )
    p.kind = kind
    p.respawn = 0.0
    pickups.append(p)


def toggle_door():
    # Interact with nearby door
    for d in doors:
        if distance(player.position, d.position) < 2.0:
            d.is_open = not d.is_open
            if d.is_open:
                d.y -= TILE_SIZE * 0.6
                d.collider = None
            else:
                d.y += TILE_SIZE * 0.6
                d.collider = 'box'
            return


def shoot():
    global fire_timer, ammo, recoil_vel
    if fire_timer > 0 or ammo <= 0:
        return
    fire_timer = FIRE_COOLDOWN
    ammo -= 1

    muzzle = player.position + player.forward * 1.2 + Vec3(0, 0.6, 0)
    b = Entity(
        model='sphere',
        color=color.yellow,
        scale=0.15,
        position=muzzle,
        collider='box'
    )
    b.velocity = player.forward * BULLET_SPEED
    b.life = 1.4
    projectiles.append(b)

    muzzle_flash.enabled = True
    invoke(setattr, muzzle_flash, 'enabled', False, delay=0.05)
    recoil_vel -= 6.0


def enemy_move_with_avoidance(e, dt):
    # Separation from other enemies
    sep = Vec3(0, 0, 0)
    for other in enemies:
        if other is e or not other.enabled:
            continue
        d = distance(e.position, other.position)
        if d < 1.2 and d > 0.001:
            sep -= (other.position - e.position).normalized() * (1.2 - d)

    to_player = (player.position - e.position)
    dist = to_player.length()
    if dist < 0.01:
        return

    los = has_los_world(e.position, player.position)
    move = Vec3(0, 0, 0)

    if los:
        dir_vec = to_player.normalized()
        strafe = Vec3(-dir_vec.z, 0, dir_vec.x) * math.sin(time.time() * 2.0 + e.avoid_phase) * 0.4
        backoff = Vec3(0, 0, 0)
        if dist < 2.5:
            backoff = -dir_vec * 0.6
        move = (dir_vec + strafe + backoff + sep * 0.6).normalized() * ENEMY_SPEED * dt
    else:
        e.repath -= dt
        if e.repath <= 0 or not e.path or e.path_i >= len(e.path):
            sx, sy = world_to_grid(e.position.x, e.position.z, map_h, map_w)
            gx, gy = world_to_grid(player.position.x, player.position.z, map_h, map_w)
            e.path = astar((sx, sy), (gx, gy))
            e.path_i = 0
            e.repath = 0.6

        if e.path and e.path_i < len(e.path):
            px, py = e.path[e.path_i]
            wx, wz = grid_to_world(px, py, map_h, map_w)
            target = Vec3(wx, e.y, wz)
            dir_vec = (target - e.position)
            if dir_vec.length() < 0.3:
                e.path_i += 1
            else:
                move = (dir_vec.normalized() + sep * 0.6).normalized() * ENEMY_SPEED * dt

    # Try full move, then axis moves as fallback
    def hits_world(ent):
        for w in walls:
            if ent.intersects(w).hit:
                return True
        for d in doors:
            if d.collider and ent.intersects(d).hit:
                return True
        return False

    e.x += move.x
    if hits_world(e):
        e.x -= move.x
    e.z += move.z
    if hits_world(e):
        e.z -= move.z


def update_enemies(dt):
    global hp, hurt_timer
    for e in enemies[:]:
        if e.health <= 0:
            e.disable()
            enemies.remove(e)
            continue

        enemy_move_with_avoidance(e, dt)

        if distance(player.position, e.position) < ENEMY_HIT_RANGE and hurt_timer <= 0:
            hp = max(0, hp - 10)
            hurt_timer = ENEMY_DAMAGE_COOLDOWN


def update_projectiles(dt):
    for b in projectiles[:]:
        b.position += b.velocity * dt
        b.life -= dt

        # Collide with world
        if b.intersects().hit:
            b.disable()
            projectiles.remove(b)
            continue

        # Hit enemies
        hit_enemy = None
        for e in enemies:
            if b.intersects(e).hit:
                hit_enemy = e
                break
        if hit_enemy:
            hit_enemy.health -= 1
            b.disable()
            projectiles.remove(b)
            continue

        if b.life <= 0:
            b.disable()
            projectiles.remove(b)


def update_pickups(dt):
    global hp, ammo
    for p in pickups:
        if p.respawn > 0:
            p.respawn -= dt
            if p.respawn <= 0:
                p.enabled = True
        if not p.enabled:
            continue
        if distance(player.position, p.position) < 1.2:
            if p.kind == 'health':
                hp = clamp(hp + 25, 0, 100)
            else:
                ammo += 20
            p.enabled = False
            p.respawn = PICKUP_RESPAWN


def update_weapon_recoil(dt):
    global recoil, recoil_vel
    # Spring toward zero
    recoil_vel += (-recoil * 25.0 - recoil_vel * 6.0) * dt
    recoil += recoil_vel * dt
    weapon.position = weapon_base_pos + Vec3(0, 0, recoil * 0.12)
    weapon.rotation = Vec3(-recoil * 35.0, 10, 0)


def update():
    global fire_timer, hurt_timer
    dt = time.dt

    update_enemies(dt)
    update_projectiles(dt)
    update_pickups(dt)
    update_weapon_recoil(dt)

    fire_timer = max(0.0, fire_timer - dt)
    hurt_timer = max(0.0, hurt_timer - dt)

    hp_text.text = f'HP {hp}'
    ammo_text.text = f'Ammo {ammo}'

    update_minimap(map_w, map_h)


def input(key):
    if key == 'left mouse down':
        shoot()
    if key == 'e':
        toggle_door()
    if key == 'escape':
        application.quit()


# Build the level from map file
map_w, map_h = spawn_level()

app.run()

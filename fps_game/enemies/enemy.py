import random


def create_enemy(enemy_type, x, y):
    if enemy_type == "fast":
        health = 80
        speed = 4
        radius = 18
        bob_speed = 0.35
        damage = 8
    elif enemy_type == "tank":
        health = 200
        speed = 1.5
        radius = 28
        bob_speed = 0.18
        damage = 15
    elif enemy_type == "ranged":
        health = 90
        speed = 0.7
        radius = 20
        bob_speed = 0.22
        damage = 10
    elif enemy_type == "boss1":
        health = 300
        speed = 2.2
        radius = 36
        bob_speed = 0.2
        damage = 18
    elif enemy_type == "boss2":
        health = 380
        speed = 1.9
        radius = 38
        bob_speed = 0.16
        damage = 20
    elif enemy_type == "boss3":
        health = 450
        speed = 2.1
        radius = 40
        bob_speed = 0.18
        damage = 22
    elif enemy_type == "boss_final":
        health = 600
        speed = 2.4
        radius = 46
        bob_speed = 0.14
        damage = 26
    else:
        enemy_type = "normal"
        health = 100
        speed = 2
        radius = 22
        bob_speed = 0.28
        damage = 10

    return {
        "x": x,
        "y": y,
        "type": enemy_type,
        "health": health,
        "speed": speed,
        "radius": radius,
        "anim_phase": random.random() * 6.28318,
        "bob_speed": bob_speed,
        "hurt_timer": 0,
        "time_bias": random.uniform(-0.5, 0.7),
        "boss": enemy_type.startswith("boss"),
        "boss_kind": enemy_type if enemy_type.startswith("boss") else "",
        "boss_cooldown": random.randint(60, 140),
        "boss_burst": 0,
        "damage": damage,
        "stun_timer": 0,
        "slow_timer": 0,
        "alive": True,
        "death_timer": 0,
        "attack_cooldown": 0,
        "attack_frame": 0,
    }

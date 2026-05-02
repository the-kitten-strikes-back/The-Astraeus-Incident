import random


def create_enemy(enemy_type, x, y):
    base = dict(
        x=x, y=y, type=enemy_type,
        anim_phase=random.random() * 6.28318,
        hurt_timer=0, time_bias=random.uniform(-0.5, 0.7),
        boss=False, boss_kind="", boss_cooldown=random.randint(60, 140),
        boss_burst=0, stun_timer=0, slow_timer=0,
        alive=True, death_timer=0, attack_cooldown=0, attack_frame=0,
        fire_cooldown=random.randint(0, 40),   # stagger initial shots
    )

    if enemy_type == "fast":
        base.update(health=80,  speed=7,   radius=18, bob_speed=0.35, damage=8,
                    fire_range=0)   # fast enemies never shoot

    elif enemy_type == "tank":
        base.update(health=200, speed=3, radius=28, bob_speed=0.18, damage=15,
                    fire_range=0)   # tank is pure melee

    elif enemy_type == "ranged":
        base.update(health=90,  speed=3, radius=20, bob_speed=0.22, damage=6,
                    fire_range=500, fire_cd_max=55,  bullet_speed=10,
                    bullet_damage=10, bullet_spread=0.03,
                    keep_distance=180)

    elif enemy_type == "normal":
        base.update(health=100, speed=4,   radius=22, bob_speed=0.28, damage=10,
                    fire_range=300, fire_cd_max=80,  bullet_speed=8,
                    bullet_damage=8, bullet_spread=0.06,
                    keep_distance=0)

    elif enemy_type == "boss1":
        base.update(health=300, speed=2.2, radius=36, bob_speed=0.20, damage=18,
                    boss=True, boss_kind="boss1",
                    fire_range=550, fire_cd_max=45,  bullet_speed=11,
                    bullet_damage=14, bullet_spread=0.05,
                    keep_distance=120)

    elif enemy_type == "boss2":
        base.update(health=380, speed=1.9, radius=38, bob_speed=0.16, damage=20,
                    boss=True, boss_kind="boss2",
                    fire_range=600, fire_cd_max=35,  bullet_speed=12,
                    bullet_damage=16, bullet_spread=0.04,
                    keep_distance=140)

    elif enemy_type == "boss3":
        base.update(health=450, speed=2.1, radius=40, bob_speed=0.18, damage=22,
                    boss=True, boss_kind="boss3",
                    fire_range=650, fire_cd_max=28,  bullet_speed=13,
                    bullet_damage=18, bullet_spread=0.035,
                    keep_distance=150)

    elif enemy_type == "boss_final":
        base.update(health=600, speed=2.4, radius=46, bob_speed=0.14, damage=26,
                    boss=True, boss_kind="boss_final",
                    fire_range=700, fire_cd_max=22,  bullet_speed=14,
                    bullet_damage=22, bullet_spread=0.025,
                    keep_distance=160)

    else:
        enemy_type = "normal"
        base.update(type="normal", health=100, speed=2, radius=22,
                    bob_speed=0.28, damage=10,
                    fire_range=300, fire_cd_max=80, bullet_speed=8,
                    bullet_damage=8, bullet_spread=0.06,
                    keep_distance=0)
    return base
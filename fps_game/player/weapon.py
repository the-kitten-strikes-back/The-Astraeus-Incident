import random
import math

import os
import pygame

from core.settings import EFFECT_FILES, WIDTH, HEIGHT, DELTA_ANGLE, WEAPON_DEFAULT_IMG, WEAPON_IMAGE_MAP
from systems import audio

ENEMY_HITBOX_SCALE = 0.62
ENEMY_HITBOX_MIN = 10


def _effective_enemy_hit_radius(enemy):
    base = enemy.get("radius", 20)
    return max(ENEMY_HITBOX_MIN, int(base * ENEMY_HITBOX_SCALE))


class Weapon:
    def __init__(self, name, damage, ammo, max_ammo, spread, fire_rate=0.2):
        self.name = name
        self.damage = damage
        self.ammo = ammo
        self.max_ammo = max_ammo
        self.spread = spread
        self.fire_rate = fire_rate


class WeaponSystem:
    def __init__(self, image):
        self.images = {}
        self.image = pygame.transform.scale(image, (300, 200))
        self.recoil_offset = 0
        self.recoil_velocity = 0
        self.bullets = []
        self.sway_x = 0.0
        self.sway_y = 0.0
        self.muzzle_timer = 0
        self.idle_phase = 0.0
        self.kick = 0.0

        self.reloading = False
        self.reload_timer = 0
        self.reload_time = 60

        self.last_shot = 0

        self._load_weapon_images()

    def _load_weapon_images(self):
        for name, path in WEAPON_IMAGE_MAP.items():
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
            else:
                img = pygame.image.load(WEAPON_DEFAULT_IMG).convert_alpha()
            self.images[name] = pygame.transform.scale(img, (300, 200))

    def try_shoot(self, now, player, enemies, depth_buffer):
        weapon = player.get_weapon()
        if self.reloading or weapon.ammo <= 0:
            return 0, 0, False, False
        if now - self.last_shot <= weapon.fire_rate:
            return 0, 0, False, False

        self.last_shot = now
        weapon.ammo -= 1
        self.muzzle_timer = 4
        self.kick = -8
        self.bullets.append({
            "x": player.x,
            "y": player.y,
            "angle": player.angle,
            "speed": 20,
            "life": 60
        })

        score_delta = 0
        kills_delta = 0
        hit_any = False

        center_ray = len(depth_buffer) // 2
        if center_ray >= len(depth_buffer):
            return 0, 0, False, True
        wall_dist = depth_buffer[center_ray]

        for enemy in enemies:
            dx = enemy["x"] - player.x
            dy = enemy["y"] - player.y
            distance = math.hypot(dx, dy)

            theta = math.atan2(dy, dx)
            delta = theta - player.angle
            delta = (delta + math.pi) % (2 * math.pi) - math.pi
            spread = random.uniform(-weapon.spread, weapon.spread)
            delta += spread
            enemy_radius = _effective_enemy_hit_radius(enemy)
            hit_angle = math.atan2(enemy_radius, max(1.0, distance))
            if abs(delta) < max(DELTA_ANGLE * 2, hit_angle):
                if distance < wall_dist and enemy["alive"]:
                    headshot = abs(delta) < (DELTA_ANGLE * 0.5)
                    damage = weapon.damage
                    if headshot:
                        damage *= 2
                        score_delta += 20
                    else:
                        score_delta += 10
                    enemy["health"] -= damage
                    enemy["hurt_timer"] = 6
                    hit_any = True
                    if enemy["health"] <= 0:
                        enemy["alive"] = False
                        enemy["death_timer"] = 0
                        if enemy.get("boss"):
                            enemy["killed_by_bullet"] = True
                        kills_delta += 1

        self.recoil_velocity = -8
        return score_delta, kills_delta, hit_any, True
    def update_bullets(self, world, enemies, time_scale):
        for bullet in self.bullets[:]:
            if time_scale == 0.0:
                continue  # freeze bullets

            bullet["x"] += math.cos(bullet["angle"]) * bullet["speed"] * time_scale
            bullet["y"] += math.sin(bullet["angle"]) * bullet["speed"] * time_scale
            bullet["life"] -= 1

            if bullet["life"] <= 0:
                self.bullets.remove(bullet)
                continue

            # collision with enemies
            for enemy in enemies:
                if enemy["alive"]:
                    dx = bullet["x"] - enemy["x"]
                    dy = bullet["y"] - enemy["y"]
                    if math.hypot(dx, dy) < _effective_enemy_hit_radius(enemy):
                        enemy["health"] -= 50
                        enemy["hurt_timer"] = 6
                        if enemy["health"] <= 0:
                            enemy["alive"] = False
                            if enemy.get("boss"):
                                enemy["killed_by_bullet"] = True
                        if bullet in self.bullets:
                            self.bullets.remove(bullet)
                        break

    def update_sway(self, target_x, target_y):
        self.sway_x += (target_x - self.sway_x) * 0.18
        self.sway_y += (target_y - self.sway_y) * 0.18
        self.idle_phase += 0.05
        self.kick *= 0.78
    def update_reload(self, player):
        weapon = player.get_weapon()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_r] and weapon.ammo < weapon.max_ammo and not self.reloading:
            self.reloading = True
            self.reload_timer = self.reload_time

        if self.reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                weapon.ammo = weapon.max_ammo
                self.reloading = False
                try:
                    if os.path.exists(EFFECT_FILES["reload"]):
                        audio.play_sound(EFFECT_FILES["reload"])
                except (KeyError, pygame.error):
                    pass

    def update_recoil(self):
        self.recoil_offset += self.recoil_velocity
        self.recoil_velocity += 0.8
        self.recoil_offset *= 0.9
        if self.recoil_offset > 0:
            self.recoil_offset = 0
            self.recoil_velocity = 0

    def draw_weapon(self, screen, player, sway_x=0, sway_y=0, bob_y=0):
        weapon = player.get_weapon()
        sprite = self.images.get(weapon.name, self.image)
        reload_t = 0.0
        if self.reloading and self.reload_time > 0:
            reload_t = max(0.0, min(1.0, self.reload_timer / self.reload_time))
        reload_offset = int(35 * math.sin(reload_t * math.pi))
        reload_swing = int(12 * math.sin(reload_t * math.pi * 2))
        idle_x = int(math.sin(self.idle_phase) * 6)
        idle_y = int(math.cos(self.idle_phase * 0.8) * 5)

        x = WIDTH // 2 - sprite.get_width() // 2 + int(self.sway_x + sway_x) + reload_swing + idle_x
        y = HEIGHT - sprite.get_height() + self.recoil_offset + int(self.sway_y + sway_y + bob_y) + reload_offset + idle_y + int(self.kick)
        screen.blit(sprite, (x, y))

        if self.muzzle_timer > 0:
            self.muzzle_timer -= 1
            pygame.draw.circle(screen, (255, 200, 50), (WIDTH // 2, HEIGHT // 2), 18)

    def draw_bullets(self, screen):
        for bullet in self.bullets:
            pygame.draw.circle(
                screen,
                (255, 255, 0),
                (int(bullet["x"]), int(bullet["y"])),
                3
            )

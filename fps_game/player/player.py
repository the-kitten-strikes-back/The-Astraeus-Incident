import math

import pygame

from core.settings import EFFECT_FILES, TILE, WEAPON_SPECS, WEAPON_ORDER
from utils.math_utils import is_wall
from player.weapon import Weapon
from systems import audio


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = 0
        self.speed = 8
        self.current_speed = 0.0
        self.accel = 0.18
        self.move_amount = 0.0
        self.mouse_sensitivity = 0.003
        self.max_health = 100
        self.health = self.max_health
        self.invincibility_frames = 0

        self.weapons = []
        for name in WEAPON_ORDER:
            spec = WEAPON_SPECS[name]
            self.weapons.append(
                Weapon(name, spec["damage"], spec["ammo"], spec["max_ammo"],
                       spec["spread"], fire_rate=spec["fire_rate"])
            )
        self.owned_weapons = {"Pistol"}
        self.temp_weapons = set()
        self.current_weapon_index = 0

    def available_weapons(self):
        return [w for w in self.weapons if w.name in self.owned_weapons or w.name in self.temp_weapons]

    def has_weapon(self, name):
        return name in self.owned_weapons or name in self.temp_weapons

    def owns_weapon(self, name):
        return name in self.owned_weapons

    def own_weapon(self, name):
        weapon = self._get_weapon_by_name(name)
        if weapon:
            self.owned_weapons.add(name)
            weapon.ammo = weapon.max_ammo

    def grant_temp_weapon(self, name):
        weapon = self._get_weapon_by_name(name)
        if weapon:
            self.temp_weapons.add(name)
            weapon.ammo = weapon.max_ammo

    def restock_ammo(self, name):
        weapon = self._get_weapon_by_name(name)
        if weapon:
            weapon.ammo = weapon.max_ammo

    def clear_temp_weapons(self):
        for weapon in self.weapons:
            if weapon.name in self.temp_weapons and weapon.name not in self.owned_weapons:
                weapon.ammo = 0
        self.temp_weapons.clear()

    def refresh_owned_ammo(self):
        for weapon in self.weapons:
            if weapon.name in self.owned_weapons:
                weapon.ammo = weapon.max_ammo
            else:
                weapon.ammo = 0

    def _get_weapon_by_name(self, name):
        for weapon in self.weapons:
            if weapon.name == name:
                return weapon
        return None

    def select_weapon(self, name):
        available = self.available_weapons()
        current = self.get_weapon().name
        for i, weapon in enumerate(available):
            if weapon.name == name:
                if weapon.name != current:
                    audio.play_sound(EFFECT_FILES.get("weapon_switch", ""))
                self.current_weapon_index = i
                return True
        return False

    def switch_weapon(self, direction):
        available = self.available_weapons()
        if not available:
            self.current_weapon_index = 0
            return
        self.current_weapon_index = (self.current_weapon_index + direction) % len(available)

    def get_weapon(self):
        available = self.available_weapons()
        if not available:
            return self.weapons[0]
        if self.current_weapon_index >= len(available):
            self.current_weapon_index = 0
        return available[self.current_weapon_index]

    def move(self, world, mouse_dx, doors=None, speed_scale: float = 1.0):
        keys = pygame.key.get_pressed()

        # Separate forward/back and strafe into two scalar axes.
        forward = 0.0
        strafe  = 0.0
        if keys[pygame.K_w]: forward += 1.0
        if keys[pygame.K_s]: forward -= 1.0
        if keys[pygame.K_a]: strafe  -= 1.0
        if keys[pygame.K_d]: strafe  += 1.0

        # Compose a 2-D wish vector in world space.
        wish_dx = math.cos(self.angle) * forward - math.sin(self.angle) * strafe
        wish_dy = math.sin(self.angle) * forward + math.cos(self.angle) * strafe

        # Normalise so diagonal movement isn't faster.
        mag = math.hypot(wish_dx, wish_dy)
        if mag > 1.0:
            wish_dx /= mag
            wish_dy /= mag

        target_dx = wish_dx * self.speed * speed_scale
        target_dy = wish_dy * self.speed * speed_scale

        # Smooth acceleration on each axis independently.
        self.vel_x = getattr(self, "vel_x", 0.0)
        self.vel_y = getattr(self, "vel_y", 0.0)
        self.vel_x += (target_dx - self.vel_x) * self.accel
        self.vel_y += (target_dy - self.vel_y) * self.accel

        # Per-axis collision so you can slide along walls.
        if abs(self.vel_x) > 0.001:
            nx = self.x + self.vel_x
            if not is_wall(nx, self.y, world, TILE, doors):
                self.x = nx
            else:
                self.vel_x = 0.0

        if abs(self.vel_y) > 0.001:
            ny = self.y + self.vel_y
            if not is_wall(self.x, ny, world, TILE, doors):
                self.y = ny
            else:
                self.vel_y = 0.0

        current_speed = math.hypot(self.vel_x, self.vel_y)
        self.current_speed = current_speed
        self.move_amount = min(1.0, current_speed / self.speed) if self.speed > 0 else 0.0

        if mouse_dx:
            self.angle += mouse_dx * self.mouse_sensitivity
            keys = pygame.key.get_pressed()
            target_speed = 0.0
            if keys[pygame.K_w]:
                target_speed += self.speed
            if keys[pygame.K_s]:
                target_speed -= self.speed
            if keys[pygame.K_a]:
                #strafe left: add speed in the direction 90 degrees counterclockwise from current angle
                target_speed += self.speed * math.cos(self.angle - math.pi / 2)
                target_speed += self.speed * math.sin(self.angle - math.pi / 2)
            if keys[pygame.K_d]:
                #strafe right: add speed in the direction 90 degrees clockwise from current angle
                target_speed += self.speed * math.cos(self.angle + math.pi / 2)
                target_speed += self.speed * math.sin(self.angle + math.pi / 2)
                

                                                        
            scaled_target = target_speed * speed_scale
            self.current_speed += (scaled_target - self.current_speed) * self.accel

            dx = math.cos(self.angle) * self.current_speed
            dy = math.sin(self.angle) * self.current_speed

            if abs(self.current_speed) > 0.001:
                nx = self.x + dx
                ny = self.y + dy
                if not is_wall(nx, self.y, world, TILE, doors):
                    self.x = nx
                if not is_wall(self.x, ny, world, TILE, doors):
                    self.y = ny

            if self.speed > 0:
                self.move_amount = min(1.0, abs(self.current_speed) / self.speed)
            else:
                self.move_amount = 0.0

            if mouse_dx:
                self.angle += mouse_dx * self.mouse_sensitivity

    def apply_damage(self, amount):
        if self.invincibility_frames > 0:
            return False
        self.health -= amount
        self.invincibility_frames = 30
        return True

    def update_invincibility(self):
        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1

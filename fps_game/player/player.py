import math

import pygame

from core.settings import TILE
from utils.math_utils import is_wall
from player.weapon import Weapon


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

        self.weapons = [
            Weapon("Pistol", 50, 10, 10, 0.02),
            Weapon("Shotgun", 25, 5, 5, 0.1),
            Weapon("Sniper", 100, 3, 3, 0.005),
        ]
        self.current_weapon_index = 0

    def switch_weapon(self, direction):
        self.current_weapon_index = (self.current_weapon_index + direction) % len(self.weapons)

    def get_weapon(self):
        return self.weapons[self.current_weapon_index]

    def move(self, world, mouse_dx, doors=None):
        keys = pygame.key.get_pressed()
        target_speed = 0.0
        if keys[pygame.K_w]:
            target_speed += self.speed
        if keys[pygame.K_s]:
            target_speed -= self.speed
        self.current_speed += (target_speed - self.current_speed) * self.accel

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

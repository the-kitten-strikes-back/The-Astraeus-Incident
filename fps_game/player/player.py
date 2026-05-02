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
            Weapon("Pistol",  50, 10, 10, 0.02, fire_rate=0.25),
            Weapon("Shotgun", 25,  5,  5, 0.10, fire_rate=0.7),
            Weapon("Sniper", 100,  3,  3, 0.005, fire_rate=1.0),
            Weapon("Machine Gun", 20, 60, 60, 0.035, fire_rate=0.01),
        ]
        self.current_weapon_index = 0

    def switch_weapon(self, direction):
        self.current_weapon_index = (self.current_weapon_index + direction) % len(self.weapons)

    def get_weapon(self):
        return self.weapons[self.current_weapon_index]

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

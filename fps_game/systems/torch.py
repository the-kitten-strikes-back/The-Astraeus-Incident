import math
import os

import pygame


class Torch:
    def __init__(self, radius=420):
        self.radius = radius
        self._sprite = None
        self._light_surf = None
        self._build_light()

    def load_sprite(self, path):
        try:
            img = pygame.image.load(path).convert_alpha()
            self._sprite = pygame.transform.scale(img, (300, 200))
        except (FileNotFoundError, pygame.error):
            surf = pygame.Surface((300, 200), pygame.SRCALPHA)
            pygame.draw.rect(surf, (160, 100, 40), (130, 80, 40, 100))
            pygame.draw.circle(surf, (255, 200, 50), (150, 80), 30)
            self._sprite = surf

    def _build_light(self):
        r = self.radius
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for i in range(r, 0, -1):
            ratio = i / r
            alpha = int(255 * (1.0 - ratio) ** 0.55)
            green = int(230 + 25 * (1.0 - ratio))
            blue  = int(160 * (1.0 - ratio))
            pygame.draw.circle(surf, (255, min(255, green), blue, alpha), (r, r), i)
        self._light_surf = surf

    def draw_sprite(self, scene, bob_y=0.0, sway_x=0.0, sway_y=0.0):
        if self._sprite is None:
            return
        sw = scene.get_width()
        sh = scene.get_height()
        w  = self._sprite.get_width()
        h  = self._sprite.get_height()
        x  = sw // 2 - w // 2 + int(sway_x)
        y  = sh - h + int(sway_y + bob_y)
        scene.blit(self._sprite, (x, y))

    def draw_light(self, screen, anim_time=0.0):
        sw, sh = screen.get_width(), screen.get_height()
        cx, cy = sw // 2, sh // 2

        flicker = (
            1.0
            + 0.025 * math.sin(anim_time * 8.1)
            + 0.015 * math.sin(anim_time * 17.3)
        )
        r = max(1, int(self.radius * flicker))

        darkness = pygame.Surface((sw, sh), pygame.SRCALPHA)
        darkness.fill((0, 0, 0, 210))

        light = pygame.transform.smoothscale(self._light_surf, (r * 2, r * 2))
        darkness.blit(light, (cx - r, cy - r), special_flags=pygame.BLEND_RGBA_SUB)

        screen.blit(darkness, (0, 0))

        bloom_r = max(1, int(r * 0.14))
        glow = pygame.Surface((bloom_r * 2, bloom_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 235, 160, 55), (bloom_r, bloom_r), bloom_r)
        screen.blit(glow, (cx - bloom_r, cy - bloom_r), special_flags=pygame.BLEND_RGBA_ADD)

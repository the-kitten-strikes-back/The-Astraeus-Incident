import math
import random
import time

import pygame

from core.settings import (
    WIDTH, HEIGHT, ALIEN_RED, ENTITY_AMBIENT_TAUNTS,
)

CX, CY = WIDTH // 2, HEIGHT // 2


class EntityTaunts:
    def __init__(self):
        self.active = False
        self.current_taunt = ""
        self.timer = 0.0
        self.display_timer = 0.0
        self.display_duration = 3.5
        self.shake_x = 0.0
        self.shake_y = 0.0
        self.rage = 0.0
        self.font = None
        self.font_small = None
        self._used_recently = set()
        self._clock = 0.0
        self._next_interval = 10.0

    def _ensure_fonts(self):
        if self.font is None:
            self.font = pygame.font.SysFont("consolas", 48, bold=True)
        if self.font_small is None:
            self.font_small = pygame.font.SysFont("consolas", 16)

    def enter_level(self, level_index):
        if level_index >= 15:
            self.active = True
            self.rage = (level_index - 15) / 4.0
            self._reset_timer()
        else:
            self.active = False
            self.current_taunt = ""

    def _reset_timer(self):
        min_int = 25.0 - self.rage * 19.0
        max_int = 45.0 - self.rage * 33.0
        self._next_interval = random.uniform(min_int, max_int)
        self.timer = self._next_interval

    def _pick_taunt(self):
        available = [t for t in ENTITY_AMBIENT_TAUNTS if t not in self._used_recently]
        if not available:
            self._used_recently.clear()
            available = ENTITY_AMBIENT_TAUNTS[:]
        pick = random.choice(available)
        self._used_recently.add(pick)
        if len(self._used_recently) > len(ENTITY_AMBIENT_TAUNTS) // 2:
            self._used_recently.pop()
        return pick

    def update(self, dt):
        if not self.active:
            return
        self._ensure_fonts()
        self._clock += dt
        if not self.current_taunt:
            self.timer -= dt
            if self.timer <= 0:
                self.current_taunt = self._pick_taunt()
                self.display_timer = 0.0
                self._reset_timer()
        else:
            self.display_timer += dt
            if self.display_timer >= self.display_duration:
                self.current_taunt = ""
                self.display_timer = 0.0
        intensity = 2.0 + self.rage * 6.0
        freq_x = 12.0 + self.rage * 8.0
        freq_y = 15.0 + self.rage * 10.0
        self.shake_x = math.sin(self._clock * freq_x) * intensity
        self.shake_y = math.cos(self._clock * freq_y) * intensity * 0.6

    def draw(self, screen):
        if not self.active or not self.current_taunt:
            return
        self._ensure_fonts()
        dt = self.display_timer
        fade_in = 0.5
        fade_out = 0.8
        if dt < fade_in:
            alpha = dt / fade_in
        elif dt > self.display_duration - fade_out:
            alpha = (self.display_duration - dt) / fade_out
        else:
            alpha = 1.0
        alpha = max(0.0, min(1.0, alpha))
        full_alpha = int(255 * alpha)
        text = self.current_taunt
        x = CX + int(self.shake_x)
        y = CY - 80 + int(self.shake_y)
        shadow_surf = self.font.render(text, True, (120, 0, 0))
        shadow_surf.set_alpha(full_alpha)
        screen.blit(shadow_surf, (x - shadow_surf.get_width() // 2 + 3, y + 3))
        main_surf = self.font.render(text, True, ALIEN_RED)
        main_surf.set_alpha(full_alpha)
        screen.blit(main_surf, (x - main_surf.get_width() // 2, y))
        if self.rage > 0.3:
            flicker = abs(math.sin(self._clock * 20.0))
            vignette_alpha = int(40 * alpha * self.rage * flicker)
            if vignette_alpha > 0:
                vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                vignette.fill((180, 0, 0, vignette_alpha))
                screen.blit(vignette, (0, 0))

import pygame
import math

class Torch:
    def __init__(self, radius=200):
        self.radius = radius
        self.surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        self._generate_light()

    def _generate_light(self):
        """Create radial gradient"""
        for i in range(self.radius):
            alpha = max(0, 255 - (i * 255 // self.radius))
            pygame.draw.circle(
                self.surface,
                (255, 255, 220, alpha),
                (self.radius, self.radius),
                self.radius - i
            )

    def draw(self, screen, player_pos):
        # Create darkness
        darkness = pygame.Surface(screen.get_size())
        darkness.fill((0, 0, 0))

        # Cut out light
        lx = int(player_pos[0] - self.radius)
        ly = int(player_pos[1] - self.radius)

        darkness.blit(self.surface, (lx, ly), special_flags=pygame.BLEND_RGBA_SUB)

        # Apply to screen
        screen.blit(darkness, (0, 0))
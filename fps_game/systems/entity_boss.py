import math
import random
import time

import pygame

from core.settings import (
    WIDTH, HEIGHT, FPS,
    ENTITY_WORD_LIST, ENTITY_TAUNTS,
    ENTITY_ATTACK_INTERVAL_BASE, ENTITY_ATTACK_INTERVAL_MIN,
    ENTITY_ATTACK_INTERVAL_DECAY, ENTITY_PROJECTILE_SPEED,
    ENTITY_DAMAGE_PER_HIT, ENTITY_MAX_RETRIES,
    ENTITY_RETRY_ESCALATION, ENTITY_HEALTH,
    ENTITY_ATTACKS_TO_DEFEAT,
    ALIEN_CYAN, ALIEN_RED, ALIEN_AMBER,
)
from systems.entity_form import EntityForm
from systems.entity_fx import EntityTimeWarpFX
from systems import audio

CX, CY = WIDTH // 2, HEIGHT // 2


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


_PARTICLE_SURFS = {}
_FLASH_SURF = None


class EntityBossFight:
    INTRO = "intro"
    WINDUP = "windup"
    ATTACK = "attack"
    RESOLVE = "resolve"
    PAUSE = "pause"
    DEATH = "death"
    VICTORY = "victory"

    def __init__(self):
        self.active = False
        self.state = self.INTRO
        self.attempt = 0
        self.health = ENTITY_HEALTH
        self.max_health = ENTITY_HEALTH
        self.attacks_survived = 0
        self.total_attacks = ENTITY_ATTACKS_TO_DEFEAT
        self.current_word = ""
        self.typed_text = ""
        self.attack_timer = 0.0
        self.phase_timer = 0.0
        self.intro_timer = 0.0
        self.dot_x = CX
        self.dot_y = CY
        self.dot_radius = 5
        self.dot_pulse = 0.0
        self.glitch_timer = 0.0
        self.glitch_intensity = 0.0
        self.projectiles = []
        self.taunt_text = ""
        self.taunt_timer = 0.0
        self.screen_flash = 0.0
        self.death_timer = 0.0
        self.victory_timer = 0.0
        self.victory = False
        self.retry_failed = False
        self.shake_amount = 0.0
        self.words_used = set()
        self.enemy_silhouettes = []
        self.silhouette_timer = 0.0
        # self.dual_attack = False
        # self.second_word = ""
        # self.second_typed = ""
        self.ambient_particles = []
        self.corruption_lines = []
        for i in range(60):
            self.ambient_particles.append({
                "x": random.uniform(0, WIDTH),
                "y": random.uniform(0, HEIGHT),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.3, 0.3),
                "size": random.randint(1, 3),
                "alpha": random.randint(20, 80),
            })
        self.form = EntityForm(seed=13)
        self.fx = EntityTimeWarpFX()
        self.entity_size = 240.0
        self.eye_open = 0.0
        self.boss_screen_pos = (CX, CY - 170)

    def start(self):
        self.active = True
        self.state = self.INTRO
        self.attempt = 0
        self.health = ENTITY_HEALTH
        self.attacks_survived = 0
        self.current_word = ""
        self.typed_text = ""
        self.projectiles = []
        self.victory = False
        self.retry_failed = False
        self.intro_timer = 0.0
        self.words_used = set()
        self.entity_size = 240.0
        self.eye_open = 0.0
        self.fx.intensity = 0.0
        self._build_enemy_silhouettes()

    def _build_enemy_silhouettes(self):
        self.enemy_silhouettes = [
            {"type": "normal", "timer": 0.0, "duration": 0.15},
            {"type": "fast", "timer": 0.5, "duration": 0.12},
            {"type": "tank", "timer": 1.0, "duration": 0.18},
            {"type": "ranged", "timer": 1.5, "duration": 0.14},
            {"type": "boss1", "timer": 2.0, "duration": 0.2},
            {"type": "boss2", "timer": 2.5, "duration": 0.16},
            {"type": "boss3", "timer": 3.0, "duration": 0.22},
            {"type": "boss_final", "timer": 3.5, "duration": 0.25},
        ]

    def get_attack_interval(self):
        base = ENTITY_ATTACK_INTERVAL_BASE - self.attempt * ENTITY_RETRY_ESCALATION
        scaling = max(0, self.attacks_survived * 0.06)
        return max(ENTITY_ATTACK_INTERVAL_MIN, base - scaling)

    def get_word_difficulty(self):
        min_len = 5 + self.attempt
        max_len = min_len + 2
        candidates = [w for w in ENTITY_WORD_LIST
                      if min_len <= len(w) <= max_len and w not in self.words_used]
        if not candidates:
            candidates = [w for w in ENTITY_WORD_LIST if min_len <= len(w) <= max_len]
        if not candidates:
            candidates = ENTITY_WORD_LIST[:]
        return random.choice(candidates)

    def _pick_word(self):
        word = self.get_word_difficulty()
        self.words_used.add(word)
        return word

    def _start_attack(self):
        self.current_word = self._pick_word()
        self.typed_text = ""
        self.state = self.WINDUP
        self.phase_timer = 0.0
        self.dual_attack = False
        # if self.health <= self.max_health * 0.5 and random.random() < 0.4:
        #     self.dual_attack = True
        #     self.second_word = self._pick_word()
        #     self.second_typed = ""
        #     self.projectiles.append({
        #         "x": CX + random.randint(-100, 100),
        #         "y": CY - 30,
        #         "target_y": HEIGHT + 50,
        #         "speed": ENTITY_PROJECTILE_SPEED + random.uniform(0, 0.3),
        #         "word": self.second_word,
        #         "active": True,
        #         "hit": False,
        #     })

    def _fire_projectile(self):
        px = CX + random.randint(-40, 40)
        py = CY + 20
        self.projectiles.append({
            "x": px,
            "y": py,
            "target_y": HEIGHT - 100,
            "speed": ENTITY_PROJECTILE_SPEED,
            "word": self.current_word,
            "active": True,
            "hit": False,
        })
        self.fx.spike(0.85, boss_pos=self.boss_screen_pos)
        self.fx.trigger_cracks(1, origin=self.boss_screen_pos)
        self._play_sfx_slowed("dilation", rate=0.5, volume=0.6)
        self.state = self.ATTACK
        self.phase_timer = 0.0
        self.typed_text = ""

    def _play_sfx_slowed(self, key, rate=0.6, volume=1.0):
        import os
        from core.settings import EFFECT_FILES
        path = EFFECT_FILES.get(key, "")
        if path and os.path.exists(path):
            try:
                audio.play_sfx_slowed(path, rate=rate, volume=volume)
            except Exception:
                pass

    def handle_event(self, event):
        if not self.active:
            return
        if self.state == self.INTRO:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if self.intro_timer > 2.0:
                    self._start_attack()
            return
        if self.state in (self.DEATH, self.VICTORY):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.typed_text = self.typed_text[:-1]
            elif event.unicode and event.unicode.isalpha():
                if len(self.typed_text) < 20:
                    self.typed_text += event.unicode.upper()
            elif event.key == pygame.K_RETURN:
                self._check_typed()

    def _check_typed(self):
        if self.state != self.ATTACK:
            return
        for proj in self.projectiles:
            if not proj["active"]:
                continue
            if self.typed_text == proj["word"]:
                proj["active"] = False
                self.screen_flash = 0.4
                self.typed_text = ""
                return
        if self.typed_text and not any(
            self.typed_text in p["word"][:len(self.typed_text)]
            for p in self.projectiles if p["active"]
        ):
            self.typed_text = ""

    def update(self, dt):
        if not self.active:
            return
        self.dot_pulse += dt * 3.0
        self.phase_timer += dt

        ambient = 0.0
        if self.state == self.WINDUP:
            grow = min(1.0, self.phase_timer / 1.2)
            ambient = 0.12 + grow * 0.55
            self.entity_size = 400.0 + grow * 95.0
        elif self.state == self.ATTACK:
            near = any(p["active"] and p["y"] > HEIGHT * 0.5 for p in self.projectiles)
            ambient = 0.16 if near else 0.07
            self.entity_size = 430.0 + int(10 * math.sin(self.dot_pulse * 2))
        elif self.state == self.INTRO:
            self.eye_open = _clamp((self.intro_timer - 0.9) / 2.2, 0.0, 1.0)
            self.entity_size = 240.0 + min(1.0, self.intro_timer / 4.0) * 165.0
            ambient = 0.06 * self.eye_open
        elif self.state == self.DEATH:
            self.death_drift = getattr(self, "death_drift", 0.0) + dt * 22.0
            self.entity_size = max(60.0, self.entity_size - dt * 150.0)
            self.eye_open = max(0.0, self.eye_open - dt * 0.9)
        elif self.state == self.PAUSE:
            self.entity_size = max(395.0, self.entity_size - dt * 60.0)
        self.fx.update(dt, ambient=ambient)
        self.fx.boss_screen_pos = self.boss_screen_pos

        for p in self.ambient_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < 0:
                p["x"] = WIDTH
            elif p["x"] > WIDTH:
                p["x"] = 0
            if p["y"] < 0:
                p["y"] = HEIGHT
            elif p["y"] > HEIGHT:
                p["y"] = 0

        if self.screen_flash > 0:
            self.screen_flash = max(0, self.screen_flash - dt * 2.0)
        if self.shake_amount > 0:
            self.shake_amount = max(0, self.shake_amount - dt * 8.0)
        if self.taunt_timer > 0:
            self.taunt_timer -= dt
        if self.glitch_timer > 0:
            self.glitch_timer -= dt
            if random.random() < 0.3:
                self.glitch_intensity = random.uniform(0.3, 1.0)

        if self.state == self.INTRO:
            self.intro_timer += dt
            self._update_silhouettes(dt)
            if self.intro_timer > 5.0:
                self._start_attack()

        elif self.state == self.WINDUP:
            grow = min(1.0, self.phase_timer / 1.2)
            self.dot_radius = 5 + int(grow * 15)
            if self.phase_timer >= 1.4:
                self._fire_projectile()

        elif self.state == self.ATTACK:
            for proj in self.projectiles:
                if proj["active"]:
                    proj["y"] += proj["speed"] * dt * 60
                    if proj["y"] >= proj["target_y"]:
                        self._take_damage()
                        proj["active"] = False
                        break
            all_resolved = all(not p["active"] for p in self.projectiles)
            if all_resolved:
                self.state = self.RESOLVE
                self.phase_timer = 0.0
            if self.current_word:
                prefix_match = self.typed_text == self.current_word[:len(self.typed_text)]
                if not prefix_match and self.typed_text:
                    self.typed_text = ""

        elif self.state == self.RESOLVE:
            self.projectiles = [p for p in self.projectiles if p["active"]]
            if self.phase_timer > 0.4:
                self.attacks_survived += 1
                if self.attacks_survived >= self.total_attacks:
                    self._entity_defeated()
                else:
                    self.state = self.PAUSE
                    self.phase_timer = 0.0

        elif self.state == self.PAUSE:
            self.dot_radius = max(5, self.dot_radius - int(dt * 8))
            interval = self.get_attack_interval()
            if self.phase_timer >= interval:
                self._start_attack()

        elif self.state == self.DEATH:
            self.death_timer += dt
            if self.death_timer > 3.0:
                if self.attempt < ENTITY_MAX_RETRIES:
                    self._retry()
                else:
                    self.retry_failed = True
                    self.active = False

        elif self.state == self.VICTORY:
            self.victory_timer += dt
            if self.victory_timer > 5.0:
                self.victory = True
                self.active = False

    def _update_silhouettes(self, dt):
        for s in self.enemy_silhouettes:
            s["timer"] += dt

    def _take_damage(self):
        self.health -= ENTITY_DAMAGE_PER_HIT
        self.shake_amount = 10.0
        self.screen_flash = 0.8
        self.glitch_timer = 0.5
        self.glitch_intensity = 1.0
        self.fx.trigger_cracks(2)
        self.fx.spike(0.9)
        if self.health <= 0:
            self.health = 0
            self.state = self.DEATH
            self.death_timer = 0.0
            self.death_drift = 0.0
            self.fx.spike(1.8)
            self.fx.trigger_cracks(4)
            self._play_sfx_slowed("death", rate=0.45, volume=0.9)
            self.taunt_text = random.choice(ENTITY_TAUNTS)
            self.taunt_timer = 3.0

    def _retry(self):
        self.attempt += 1
        self.health = ENTITY_HEALTH
        self.attacks_survived = 0
        self.projectiles = []
        self.typed_text = ""
        self.current_word = ""
        self.words_used.clear()
        self.state = self.INTRO
        self.intro_timer = 0.0
        self._build_enemy_silhouettes()
        self.shake_amount = 15.0

    def _entity_defeated(self):
        self.state = self.VICTORY
        self.victory_timer = 0.0
        self.projectiles = []
        self.current_word = ""
        self.typed_text = ""

    def draw(self, screen):
        screen.fill((0, 0, 0))

        for p in self.ambient_particles:
            a = int(p["alpha"] * (0.5 + 0.5 * math.sin(self.dot_pulse + p["x"] * 0.01)))
            key = _clamp(a, 0, 255) >> 3
            ps = _PARTICLE_SURFS.get(key)
            if ps is None:
                ps = pygame.Surface((3, 3), pygame.SRCALPHA)
                ps.fill((180, 30, 30, key << 3))
                _PARTICLE_SURFS[key] = ps
            screen.blit(ps, (int(p["x"]), int(p["y"])))

        if self.state == self.INTRO:
            self._draw_intro(screen)
        elif self.state in (self.WINDUP, self.ATTACK, self.RESOLVE, self.PAUSE):
            self._draw_fight(screen)
        elif self.state == self.DEATH:
            self._draw_death(screen)
        elif self.state == self.VICTORY:
            self._draw_victory(screen)

        self.fx.apply(screen)

        if self.screen_flash > 0:
            global _FLASH_SURF
            if _FLASH_SURF is None:
                fs = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                fs.fill((*ALIEN_RED, 255))
                _FLASH_SURF = fs
            _FLASH_SURF.set_alpha(_clamp(int(120 * self.screen_flash), 0, 255))
            screen.blit(_FLASH_SURF, (0, 0))

        self._draw_entity_hp(screen)

    def _draw_intro(self, screen):
        t = self.intro_timer

        for s in self.enemy_silhouettes:
            show_at = s["timer"]
            if show_at <= t < show_at + s["duration"]:
                self._draw_enemy_silhouette(screen, s["type"], t)

        now = pygame.time.get_ticks() / 1000.0
        alpha = min(1.0, t / 2.2)
        size = self.entity_size
        rendered = self.form.draw(
            screen, CX, CY - 150, size, now,
            angle=math.pi / 2 - 0.15, anger=0.15, hp_ratio=1.0,
            moving=self.fx.intensity * 0.4, alpha_mult=alpha,
            eye_open=self.eye_open, extra_eyes=0,
        )
        self.fx.apply_entity_split(screen, rendered, (CX, CY - 150))

        if t > 2.5:
            text_alpha = min(255, int((t - 2.5) * 200))
            font = pygame.font.SysFont("courier", 72, bold=True)
            txt = font.render("T H E  E N T I T Y", True, ALIEN_RED)
            txt.set_alpha(text_alpha)
            screen.blit(txt, (CX - txt.get_width() // 2, CY + 60))

        if t > 4.0:
            hint_alpha = min(255, int((t - 4.0) * 150))
            font_s = pygame.font.SysFont("courier", 20)
            hint = font_s.render("Press ENTER to begin", True, (120, 120, 120))
            hint.set_alpha(int(hint_alpha * (0.5 + 0.5 * math.sin(self.dot_pulse * 3))))
            screen.blit(hint, (CX - hint.get_width() // 2, CY + 140))

        if self.attempt > 0:
            font_s = pygame.font.SysFont("courier", 18)
            att = font_s.render(f"ATTEMPT {self.attempt + 1}/{ENTITY_MAX_RETRIES + 1}", True, ALIEN_AMBER)
            screen.blit(att, (CX - att.get_width() // 2, 40))

    def _draw_enemy_silhouette(self, screen, enemy_type, t):
        sizes = {
            "normal": 60, "fast": 45, "tank": 80, "ranged": 55,
            "boss1": 100, "boss2": 110, "boss3": 120, "boss_final": 140,
        }
        size = sizes.get(enemy_type, 60)
        glitch_x = CX + random.randint(-30, 30)
        glitch_y = CY + random.randint(-30, 30)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 30, 30, 140), (size // 2, size // 2), size // 2)
        inner_color = (180, 20, 20, 100)
        if "boss" in enemy_type:
            pygame.draw.polygon(surf, inner_color, [
                (size // 2, size // 4), (size * 3 // 4, size * 3 // 4),
                (size // 4, size * 3 // 4),
            ])
        else:
            pygame.draw.circle(surf, inner_color, (size // 2, size // 2), size // 3)
        screen.blit(surf, (glitch_x - size // 2, glitch_y - size // 2))

    def _draw_fight(self, screen):
        now = pygame.time.get_ticks() / 1000.0
        ratio = max(0.0, self.health / self.max_health)
        if self.state == self.WINDUP:
            grow = min(1.0, self.phase_timer / 1.2)
            lean = int(grow * 26)
        elif self.state == self.ATTACK:
            lean = int(6 * math.sin(self.dot_pulse * 1.4))
        else:
            lean = 0
        cy = CY - 150 + lean
        self.boss_screen_pos = (CX, cy)
        anger = max(0.2, 1.0 - ratio)
        if ratio <= 0.25:
            extra_eyes = 4.5
        elif ratio <= 0.45:
            extra_eyes = 3.0
        elif ratio <= 0.70:
            extra_eyes = 1.5
        else:
            extra_eyes = 0.0
        glance = math.pi / 2 - 0.18 + 0.08 * math.sin(self.dot_pulse)
        rendered = self.form.draw(
            screen, CX, cy, self.entity_size, now,
            angle=glance, anger=anger, hp_ratio=ratio,
            moving=min(1.0, self.fx.intensity * 0.6),
            eye_open=1.0, extra_eyes=extra_eyes,
        )
        self.fx.apply_entity_split(screen, rendered, (CX, cy))

        if self.state == self.WINDUP:
            warning_alpha = int(150 + 105 * math.sin(self.dot_pulse * 8))
            font_warn = pygame.font.SysFont("courier", 28, bold=True)
            warn = font_warn.render("/// INCOMING ///", True, (255, warning_alpha, warning_alpha))
            screen.blit(warn, (CX - warn.get_width() // 2, CY - 80))

        if self.state == self.ATTACK:
            self._draw_word_display(screen)
            self._draw_projectiles(screen)
            self._draw_typed_input(screen)

        if self.health <= self.max_health * 0.25:
            for _ in range(3):
                lx = random.randint(0, WIDTH)
                ly = random.randint(0, HEIGHT)
                self.corruption_lines.append({
                    "x": lx, "y": ly,
                    "w": random.randint(20, 200),
                    "h": random.randint(1, 3),
                    "alpha": random.randint(40, 120),
                })
        for line in self.corruption_lines[:]:
            surf = pygame.Surface((line["w"], line["h"]), pygame.SRCALPHA)
            surf.fill((255, 30, 30, line["alpha"]))
            screen.blit(surf, (line["x"], line["y"]))
            line["alpha"] -= 5
            if line["alpha"] <= 0:
                self.corruption_lines.remove(line)

        font_s = pygame.font.SysFont("courier", 16)
        status = font_s.render(f"ATTACKS: {self.attacks_survived}/{self.total_attacks}", True, (80, 100, 120))
        screen.blit(status, (WIDTH - 200, HEIGHT - 30))

    def _draw_word_display(self, screen):
        font = pygame.font.SysFont("consolas", 52, bold=True)
        word = self.current_word
        if not word:
            return
        y_pos = 60
        for i, ch in enumerate(word):
            typed_ch = self.typed_text[i] if i < len(self.typed_text) else ""
            if typed_ch == ch:
                color = ALIEN_CYAN
            elif i < len(self.typed_text):
                color = ALIEN_RED
            else:
                color = ALIEN_AMBER
            t = font.render(ch, True, color)
            x_pos = CX - (len(word) * 30) // 2 + i * 38
            screen.blit(t, (x_pos, y_pos))

        # if self.dual_attack:
        #     word2 = self.second_word
        #     for i, ch in enumerate(word2):
        #         typed_ch = self.second_typed[i] if i < len(self.second_typed) else ""
        #         if typed_ch == ch:
        #             color = ALIEN_CYAN
        #         elif i < len(self.second_typed):
        #             color = ALIEN_RED
        #         else:
        #             color = ALIEN_AMBER
        #         t = font.render(ch, True, color)
        #         x_pos = CX - (len(word2) * 30) // 2 + i * 38
        #         screen.blit(t, (x_pos, y_pos + 70))

    def _draw_projectiles(self, screen):
        for proj in self.projectiles:
            if not proj["active"]:
                continue
            x, y = int(proj["x"]), int(proj["y"])
            r = 12 + int(3 * math.sin(self.dot_pulse * 5))
            glow = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 20, 20, 40), (r * 3, r * 3), r * 3)
            pygame.draw.circle(glow, (255, 50, 50, 220), (r * 3, r * 3), r)
            pygame.draw.circle(glow, (255, 100, 100, 160), (r * 3, r * 3), r // 2)
            screen.blit(glow, (x - r * 3, y - r * 3))
            trail_y = y - 30
            for i in range(5):
                ta = max(0, 100 - i * 25)
                ts = max(1, r - i * 2)
                tsurf = pygame.Surface((ts * 2, ts * 2), pygame.SRCALPHA)
                pygame.draw.circle(tsurf, (255, 40, 40, ta), (ts, ts), ts)
                screen.blit(tsurf, (x - ts, trail_y - i * 12))

    def _draw_typed_input(self, screen):
        font = pygame.font.SysFont("consolas", 36, bold=True)
        display = self.typed_text if self.typed_text else "_"
        t = font.render(display, True, ALIEN_CYAN if self.typed_text else (60, 60, 60))
        screen.blit(t, (CX - t.get_width() // 2, HEIGHT - 160))
        hint_font = pygame.font.SysFont("consolas", 16)
        hint = hint_font.render("TYPE THE WORD TO BLOCK THE ATTACK", True, (60, 80, 100))
        screen.blit(hint, (CX - hint.get_width() // 2, HEIGHT - 120))

    def _draw_death(self, screen):
        t = self.death_timer
        now = pygame.time.get_ticks() / 1000.0
        fade = max(0.0, 1.0 - t / 2.6)
        if fade > 0:
            size = max(60.0, self.entity_size)
            open_e = max(0.0, 1.0 - t / 1.1)
            rendered = self.form.draw(
                screen, CX, CY - 150 + int(t * 22), size, now,
                angle=math.pi / 2, anger=1.0, hp_ratio=0.05,
                moving=0.8, alpha_mult=fade, eye_open=open_e,
                extra_eyes=max(0.0, 3.0 - t),
            )
            self.fx.apply_entity_split(screen, rendered,
                                       (CX, CY - 150 + int(t * 22)))

        if self.death_timer > 1.0:
            font = pygame.font.SysFont("courier", 40, bold=True)
            txt = font.render(self.taunt_text, True, ALIEN_RED)
            alpha = min(255, int((self.death_timer - 1.0) * 150))
            txt.set_alpha(alpha)
            screen.blit(txt, (CX - txt.get_width() // 2, CY + 80))

        if self.death_timer > 2.0:
            font_s = pygame.font.SysFont("courier", 22)
            if self.attempt < ENTITY_MAX_RETRIES:
                msg = f"RETRYING... (Attempt {self.attempt + 2}/{ENTITY_MAX_RETRIES + 1})"
            else:
                msg = "THE ENTITY OVERWHELMS YOU..."
            t = font_s.render(msg, True, (150, 150, 150))
            a = min(255, int((self.death_timer - 2.0) * 200))
            t.set_alpha(a)
            screen.blit(t, (CX - t.get_width() // 2, CY + 140))

    def _draw_victory(self, screen):
        t = self.victory_timer
        now = pygame.time.get_ticks() / 1000.0
        fade = max(0.0, 1.0 - t / 2.2)
        if fade > 0:
            self.form.draw(
                screen, CX, CY - 150, self.entity_size * (0.7 + 0.3 * fade), now,
                angle=math.pi / 2 - 0.15, anger=0.0, hp_ratio=0.02,
                moving=0.2 * fade, alpha_mult=fade,
                eye_open=min(1.0, fade + 0.35), extra_eyes=0,
            )
        r = max(1, int(80 * max(0, 1 - t / 3.0)))
        if t > 1.6 and r > 0:
            glow = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 255, 255, max(0, int(100 * (1 - t / 3.0)))),
                               (r * 3, r * 3), r * 3)
            pygame.draw.circle(glow, (200, 230, 255, max(0, int(200 * (1 - t / 3.0)))),
                               (r * 3, r * 3), r)
            screen.blit(glow, (CX - r * 3, CY - r * 3))

        if t > 1.0:
            font = pygame.font.SysFont("courier", 48, bold=True)
            txt = font.render("THE ENTITY FALLS", True, ALIEN_CYAN)
            alpha = min(255, int((t - 1.0) * 150))
            txt.set_alpha(alpha)
            screen.blit(txt, (CX - txt.get_width() // 2, CY - 30))

        if t > 2.5:
            font_s = pygame.font.SysFont("courier", 20)
            msg = font_s.render("QUANTUM CORE DESTABILIZED", True, ALIEN_AMBER)
            a = min(255, int((t - 2.5) * 120))
            msg.set_alpha(a)
            screen.blit(msg, (CX - msg.get_width() // 2, CY + 40))

        if t > 3.5:
            font_s = pygame.font.SysFont("courier", 18)
            msg = font_s.render("Your choices await...", True, (120, 140, 160))
            a = min(255, int((t - 3.5) * 100))
            msg.set_alpha(a)
            screen.blit(msg, (CX - msg.get_width() // 2, CY + 80))

    def _draw_entity_hp(self, screen):
        if not self.active or self.state in (self.INTRO, self.DEATH, self.VICTORY):
            return
        bar_w = 400
        bar_h = 12
        bar_x = CX - bar_w // 2
        bar_y = HEIGHT - 60
        pygame.draw.rect(screen, (30, 10, 10), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        remaining = max(0, self.attacks_survived / self.total_attacks)
        pygame.draw.rect(screen, ALIEN_RED, (bar_x, bar_y, int(bar_w * remaining), bar_h), border_radius=4)
        pygame.draw.rect(screen, (80, 40, 40), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
        font_s = pygame.font.SysFont("courier", 14)
        txt = font_s.render(f"ATTACKS SURVIVED: {self.attacks_survived}/{self.total_attacks}", True, (180, 180, 180))
        screen.blit(txt, (CX - txt.get_width() // 2, bar_y - 18))

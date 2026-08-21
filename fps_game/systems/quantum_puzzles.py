
import math
import random
import time

import pygame

from core.settings import (
    WIDTH, HEIGHT,
    PUZZLE_TIME_LIMIT, PUZZLE_COUNT,
    ALIEN_CYAN, ALIEN_TEAL, ALIEN_AMBER, ALIEN_RED,
    ALIEN_DARK_BG, ALIEN_PANEL_BG, ALIEN_BORDER, ALIEN_BORDER_BRIGHT,
    ALIEN_TEXT, ALIEN_TEXT_DIM,
)

CX, CY = WIDTH // 2, HEIGHT // 2


def _rotate_edges(edges, times):
    mapping = {"top": "right", "right": "bottom", "bottom": "left", "left": "top"}
    result = set(edges)
    for _ in range(times):
        result = {mapping[e] for e in result}
    return result


PIPE_BASE_EDGES = {
    0: set(),
    1: {"top", "bottom"},
    2: {"top", "right"},
    3: {"top", "right", "bottom"},
    4: {"top", "right", "bottom", "left"},
}

PUZZLE_NAMES = [
    "PIPE NETWORK", "LIGHTS OUT", "SLIDING TILES", "LASER MIRRORS",
    "TIC TAC TOE", "SEQUENCE SOLVER", "MEMORY GRID",
    "WEIGHT BALANCE", "COLOR MIXER", "THE KEYPAD",
]


class QuantumPuzzleSystem:
    def __init__(self):
        self.current_index = 0
        self.solved_count = 0
        self.puzzle_state = None
        self.start_time = 0.0
        self.feedback_text = ""
        self.feedback_timer = 0
        self.feedback_color = ALIEN_CYAN
        self.transition_timer = 0
        self.transition_dir = 0
        self.particle_phase = 0.0
        self.puzzle_order = list(range(PUZZLE_COUNT))
        random.shuffle(self.puzzle_order)

    def start(self):
        self.current_index = 0
        self.solved_count = 0
        self.feedback_text = ""
        self.feedback_timer = 0
        self.transition_timer = 0
        self._generate_current()

    def skip_all(self):
        self.current_index = PUZZLE_COUNT
        self.puzzle_state = None

    def _generate_current(self):
        if self.current_index >= PUZZLE_COUNT:
            self.puzzle_state = None
            return
        puzzle_type = self.puzzle_order[self.current_index]
        generators = [
            self._gen_pipe_network, self._gen_lights_out,
            self._gen_sliding_tiles, self._gen_laser_mirrors,
            self._gen_tictactoe, self._gen_sequence,
            self._gen_memory_grid, self._gen_weight_balance,
            self._gen_color_mixer, self._gen_keypad,
        ]
        self.puzzle_state = generators[puzzle_type]()
        self.puzzle_state["type"] = puzzle_type
        self.start_time = time.time()
        self.feedback_text = ""
        self.feedback_timer = 0

    def is_complete(self):
        return self.current_index >= PUZZLE_COUNT

    def get_time_remaining(self):
        if not self.puzzle_state:
            return 0.0
        return max(0.0, PUZZLE_TIME_LIMIT - (time.time() - self.start_time))

    def handle_event(self, event):
        if self.transition_timer > 0:
            return
        if not self.puzzle_state:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
            self.skip_all()
            return
        pt = self.puzzle_state["type"]
        handlers = [
            self._handle_pipe, self._handle_lights,
            self._handle_sliding, self._handle_laser,
            self._handle_tictactoe, self._handle_sequence,
            self._handle_memory, self._handle_weight,
            self._handle_color, self._handle_keypad,
        ]
        handlers[pt](event)

    def update(self):
        self.particle_phase += 0.03
        if self.feedback_timer > 0:
            self.feedback_timer -= 1
        if self.transition_timer > 0:
            self.transition_timer -= 1
            if self.transition_timer <= 0:
                if self.transition_dir > 0:
                    self.current_index += 1
                    self.solved_count += 1
                    if self.current_index < PUZZLE_COUNT:
                        self._generate_current()
                return
        if self.puzzle_state and self.puzzle_state.get("type") == 6:
            mg = self.puzzle_state
            if mg.get("showing") and time.time() - mg.get("show_start", 0) > mg.get("show_duration", 1.5):
                mg["showing"] = False
        if self.puzzle_state and self.puzzle_state.get("type") == 4:
            ttt = self.puzzle_state
            if ttt.get("ai_think", 0) > 0:
                ttt["ai_think"] -= 1
                if ttt["ai_think"] <= 0:
                    self._ttt_ai_move(ttt)
                    winner, line = self._ttt_check_winner(ttt["board"])
                    if winner == "O":
                        ttt["game_over"] = True
                        ttt["winner"] = "O"
                        ttt["win_line"] = line
                        self._failed()
                    elif winner == "draw":
                        ttt["game_over"] = True
                        ttt["winner"] = "draw"
                        self._failed()
        if self.get_time_remaining() <= 0 and self.puzzle_state and self.transition_timer <= 0:
            self.feedback_text = "TIMEOUT // ACCESS DENIED"
            self.feedback_color = ALIEN_RED
            self.feedback_timer = 60
            self.transition_dir = -1
            self.transition_timer = 50

    def _solved(self):
        self.feedback_text = "ACCESS GRANTED"
        self.feedback_color = ALIEN_CYAN
        self.feedback_timer = 40
        self.transition_dir = 1
        self.transition_timer = 45
        self.puzzle_state = None

    def _failed(self):
        self.feedback_text = "ACCESS DENIED"
        self.feedback_color = ALIEN_RED
        self.feedback_timer = 60
        self.transition_dir = -1
        self.transition_timer = 50

    def draw(self, screen):
        screen.fill(ALIEN_DARK_BG)
        self._draw_particles(screen)
        self._draw_frame(screen)
        if self.transition_timer > 0 and not self.puzzle_state:
            self._draw_transition(screen)
            self._draw_feedback(screen)
            self._draw_header(screen)
            return
        if self.puzzle_state:
            pt = self.puzzle_state["type"]
            draw_fns = [
                self._draw_pipe, self._draw_lights,
                self._draw_sliding, self._draw_laser,
                self._draw_tictactoe, self._draw_sequence,
                self._draw_memory, self._draw_weight,
                self._draw_color, self._draw_keypad,
            ]
            draw_fns[pt](screen)
        self._draw_timer_bar(screen)
        self._draw_header(screen)
        self._draw_feedback(screen)
        if self.transition_timer > 0:
            self._draw_transition(screen)

    def _draw_particles(self, screen):
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(40):
            x = (i * 73 + int(self.particle_phase * 50)) % WIDTH
            y = (i * 47 + int(self.particle_phase * 30)) % HEIGHT
            a = int(30 + 20 * math.sin(self.particle_phase + i))
            surf.set_at((x, y), (*ALIEN_TEAL, a))
        screen.blit(surf, (0, 0))

    def _draw_frame(self, screen):
        pulse = 0.5 + 0.5 * math.sin(self.particle_phase * 2)
        c = tuple(int(ALIEN_BORDER[i] + (ALIEN_BORDER_BRIGHT[i] - ALIEN_BORDER[i]) * pulse * 0.3) for i in range(3))
        pygame.draw.rect(screen, c, (40, 60, WIDTH - 80, HEIGHT - 100), 2, border_radius=8)
        for i in range(4):
            s = 12 + i * 3
            pygame.draw.line(screen, ALIEN_BORDER,
                             (44 + i, 64 + i), (44 + s, 64 + i), 1)
            pygame.draw.line(screen, ALIEN_BORDER,
                             (WIDTH - 44 - i, HEIGHT - 64 - i), (WIDTH - 44 - s - i, HEIGHT - 64 - i), 1)

    def _draw_header(self, screen):
        font = pygame.font.SysFont("consolas", 28, bold=True)
        name = PUZZLE_NAMES[self.puzzle_order[self.current_index]] if self.current_index < PUZZLE_COUNT else "COMPLETE"
        title = font.render(f"QUANTUM LOCK [{self.current_index + 1}/{PUZZLE_COUNT}]  //  {name}", True, ALIEN_CYAN)
        screen.blit(title, (60, 68))

    def _draw_timer_bar(self, screen):
        remaining = self.get_time_remaining()
        ratio = max(0.0, remaining / PUZZLE_TIME_LIMIT)
        bar_x, bar_y, bar_w, bar_h = 60, 104, WIDTH - 120, 10
        pygame.draw.rect(screen, (20, 30, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        color = ALIEN_CYAN if ratio > 0.3 else ALIEN_AMBER if ratio > 0.1 else ALIEN_RED
        pygame.draw.rect(screen, color, (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=4)

    def _draw_feedback(self, screen):
        if self.feedback_timer > 0 and self.feedback_text:
            font = pygame.font.SysFont("consolas", 22, bold=True)
            a = min(255, self.feedback_timer * 8)
            surf = font.render(self.feedback_text, True, self.feedback_color)
            surf.set_alpha(a)
            screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT - 50))

    def _draw_transition(self, screen):
        alpha = int(255 * (self.transition_timer / 50.0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((ALIEN_DARK_BG[0], ALIEN_DARK_BG[1], ALIEN_DARK_BG[2], alpha))
        screen.blit(overlay, (0, 0))

    # ─── PUZZLE 0: PIPE NETWORK ──────────────────────────────────────────
    def _gen_pipe_network(self):
        rows, cols = 6, 8
        grid = [[0] * cols for _ in range(rows)]
        solution = [[0] * cols for _ in range(rows)]
        source_row = random.randint(1, rows - 2)
        output_row = random.randint(1, rows - 2)
        path_cells = set()
        r, c = source_row, 0
        visited = {(r, c)}
        while c < cols - 1:
            options = []
            if c + 1 < cols and (r, c + 1) not in visited:
                options.append((r, c + 1))
            if r + 1 < rows and (r + 1, c) not in visited:
                options.append((r + 1, c))
            if r - 1 >= 0 and (r - 1, c) not in visited:
                options.append((r - 1, c))
            if not options:
                if c + 1 < cols:
                    options.append((r, c + 1))
                else:
                    break
            nr, nc = random.choice(options)
            if nc == c:
                pipe_type = 1
            else:
                pipe_type = 1
            path_cells.add((r, c))
            solution[r][c] = pipe_type
            r, c = nr, nc
            visited.add((r, c))
        path_cells.add((r, c))
        solution[r][c] = 1
        for rr in range(rows):
            for cc in range(cols):
                if (rr, cc) in path_cells:
                    neighbors = set()
                    if (rr - 1, cc) in path_cells:
                        neighbors.add("top")
                    if (rr + 1, cc) in path_cells:
                        neighbors.add("bottom")
                    if (rr, cc - 1) in path_cells:
                        neighbors.add("left")
                    if (rr, cc + 1) in path_cells:
                        neighbors.add("right")
                    if rr == source_row and cc == 0:
                        neighbors.add("left")
                    if rr == output_row and cc == cols - 1:
                        neighbors.add("right")
                    n = len(neighbors)
                    if n >= 4:
                        ptype = 4
                    elif n == 3:
                        ptype = 3
                    elif n == 2:
                        if "top" in neighbors and "bottom" in neighbors:
                            ptype = 1
                        elif "left" in neighbors and "right" in neighbors:
                            ptype = 1
                        else:
                            ptype = 2
                    elif n == 1:
                        ptype = 2
                    else:
                        ptype = 0
                    solution[rr][cc] = ptype
                else:
                    solution[rr][cc] = 0
        for rr in range(rows):
            for cc in range(cols):
                grid[rr][cc] = random.randint(0, 4)
        for rr in range(rows):
            for cc in range(cols):
                if solution[rr][cc] != 0:
                    target_rot = 0
                    sol_edges = PIPE_BASE_EDGES[solution[rr][cc]]
                    best_rot = 0
                    best_score = -1
                    for rot in range(4):
                        rotated = _rotate_edges(PIPE_BASE_EDGES[grid[rr][cc]], rot)
                        score = len(rotated & sol_edges)
                        if score > best_score:
                            best_score = score
                            best_rot = rot
                    grid[rr][cc] = grid[rr][cc]
                    actual_edges = _rotate_edges(PIPE_BASE_EDGES[grid[rr][cc]], best_rot)
                    if actual_edges != sol_edges:
                        grid[rr][cc] = solution[rr][cc]
                else:
                    grid[rr][cc] = 0
        for rr in range(rows):
            for cc in range(cols):
                if (rr, cc) not in path_cells:
                    grid[rr][cc] = random.randint(0, 4)
                    for _ in range(random.randint(0, 3)):
                        grid[rr][cc] = (grid[rr][cc] + 1) % 5
        locked = set()
        for _ in range(max(2, rows * cols // 8)):
            lr, lc = random.randint(0, rows - 1), random.randint(0, cols - 1)
            if (lr, lc) not in path_cells or (lr, lc) == (source_row, 0) or (lr, lc) == (output_row, cols - 1):
                locked.add((lr, lc))
                grid[lr][lc] = solution[lr][lc]
        return {
            "grid": grid, "rows": rows, "cols": cols,
            "source": (source_row, 0), "output": (output_row, cols - 1),
            "locked": locked, "solution_grid": solution,
            "cursor": [0, 0],
        }

    def _handle_pipe(self, event):
        ps = self.puzzle_state
        if event.type == pygame.KEYDOWN:
            cr, cc = ps["cursor"]
            if event.key == pygame.K_UP and cr > 0:
                ps["cursor"][0] -= 1
            elif event.key == pygame.K_DOWN and cr < ps["rows"] - 1:
                ps["cursor"][0] += 1
            elif event.key == pygame.K_LEFT and cc > 0:
                ps["cursor"][1] -= 1
            elif event.key == pygame.K_RIGHT and cc < ps["cols"] - 1:
                ps["cursor"][1] += 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                r, c = ps["cursor"]
                if (r, c) not in ps["locked"]:
                    ps["grid"][r][c] = (ps["grid"][r][c] + 1) % 5
                    self._check_pipe_solution()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            grid_area_x, grid_area_y = 140, 150
            cell_w, cell_h = min(140, (WIDTH - 300) // ps["cols"]), min(110, (HEIGHT - 300) // ps["rows"])
            for r in range(ps["rows"]):
                for c in range(ps["cols"]):
                    rx = grid_area_x + c * cell_w
                    ry = grid_area_y + r * cell_h
                    if rx <= mx < rx + cell_w and ry <= my < ry + cell_h:
                        ps["cursor"] = [r, c]
                        if (r, c) not in ps["locked"]:
                            ps["grid"][r][c] = (ps["grid"][r][c] + 1) % 5
                            self._check_pipe_solution()
                        return

    def _check_pipe_solution(self):
        ps = self.puzzle_state
        sr, sc = ps["source"]
        er, ec = ps["output"]
        grid = ps["grid"]
        rows, cols = ps["rows"], ps["cols"]
        connected = set()
        queue = [(sr, sc)]
        visited = set()
        while queue:
            r, c = queue.pop(0)
            if (r, c) in visited:
                continue
            visited.add((r, c))
            connected.add((r, c))
            edges = _rotate_edges(PIPE_BASE_EDGES[grid[r][c]], 0)
            actual_edges = set()
            if grid[r][c] == 1:
                if r < rows - 1:
                    actual_edges = _rotate_edges(PIPE_BASE_EDGES[grid[r][c]], 0)
                else:
                    actual_edges = {"top", "bottom"}
            actual_edges = _rotate_edges(PIPE_BASE_EDGES[grid[r][c]], 0)
            if "top" in actual_edges and r > 0 and (r - 1, c) not in visited:
                neighbor_edges = _rotate_edges(PIPE_BASE_EDGES[grid[r - 1][c]], 0)
                if "bottom" in neighbor_edges:
                    queue.append((r - 1, c))
            if "bottom" in actual_edges and r < rows - 1 and (r + 1, c) not in visited:
                neighbor_edges = _rotate_edges(PIPE_BASE_EDGES[grid[r + 1][c]], 0)
                if "top" in neighbor_edges:
                    queue.append((r + 1, c))
            if "left" in actual_edges and c > 0 and (r, c - 1) not in visited:
                neighbor_edges = _rotate_edges(PIPE_BASE_EDGES[grid[r][c - 1]], 0)
                if "right" in neighbor_edges:
                    queue.append((r, c - 1))
            if "right" in actual_edges and c < cols - 1 and (r, c + 1) not in visited:
                neighbor_edges = _rotate_edges(PIPE_BASE_EDGES[grid[r][c + 1]], 0)
                if "left" in neighbor_edges:
                    queue.append((r, c + 1))
        if (er, ec) in connected:
            self._solved()

    def _draw_pipe(self, screen):
        ps = self.puzzle_state
        grid_area_x, grid_area_y = 140, 150
        cell_w = min(140, (WIDTH - 300) // ps["cols"])
        cell_h = min(110, (HEIGHT - 300) // ps["rows"])
        cr, cc = ps["cursor"]
        for r in range(ps["rows"]):
            for c in range(ps["cols"]):
                rx = grid_area_x + c * cell_w
                ry = grid_area_y + r * cell_h
                rect = pygame.Rect(rx, ry, cell_w - 4, cell_h - 4)
                is_locked = (r, c) in ps["locked"]
                bg = (25, 40, 55) if not is_locked else (15, 25, 35)
                pygame.draw.rect(screen, bg, rect, border_radius=4)
                border = ALIEN_AMBER if is_locked else ALIEN_BORDER
                pygame.draw.rect(screen, border, rect, 1, border_radius=4)
                if r == cr and c == cc:
                    cursor_rect = pygame.Rect(rx - 2, ry - 2, cell_w, cell_h)
                    pygame.draw.rect(screen, ALIEN_CYAN, cursor_rect, 2, border_radius=6)
                ptype = ps["grid"][r][c]
                edges = _rotate_edges(PIPE_BASE_EDGES[ptype], 0)
                cx_cell = rx + cell_w // 2
                cy_cell = ry + cell_h // 2
                pipe_len = min(cell_w, cell_h) // 2 - 8
                pipe_w = 6
                if ptype == 0:
                    continue
                conns = []
                if "top" in edges:
                    conns.append((cx_cell, cy_cell - pipe_len))
                if "bottom" in edges:
                    conns.append((cx_cell, cy_cell + pipe_len))
                if "left" in edges:
                    conns.append((cx_cell - pipe_len, cy_cell))
                if "right" in edges:
                    conns.append((cx_cell + pipe_len, cy_cell))
                if len(conns) >= 2:
                    for i in range(len(conns)):
                        for j in range(i + 1, len(conns)):
                            pygame.draw.line(screen, ALIEN_TEAL, conns[i], conns[j], pipe_w)
                if len(conns) == 1:
                    pygame.draw.circle(screen, ALIEN_TEAL, conns[0], pipe_w)
                for pt in conns:
                    pygame.draw.circle(screen, ALIEN_CYAN, (int(pt[0]), int(pt[1])), pipe_w + 2, 1)
        sx = grid_area_x - 30
        sy = grid_area_y + ps["source"][0] * cell_h + cell_h // 2
        pygame.draw.circle(screen, ALIEN_AMBER, (sx, sy), 10)
        font_s = pygame.font.SysFont("consolas", 14, bold=True)
        screen.blit(font_s.render("IN", True, ALIEN_AMBER), (sx - 8, sy - 20))
        ox = grid_area_x + ps["cols"] * cell_w + 10
        oy = grid_area_y + ps["output"][0] * cell_h + cell_h // 2
        pygame.draw.circle(screen, ALIEN_AMBER, (ox, oy), 10)
        screen.blit(font_s.render("OUT", True, ALIEN_AMBER), (ox - 12, oy - 20))
        hint_font = pygame.font.SysFont("consolas", 14)
        screen.blit(hint_font.render("ARROWS: move cursor  |  ENTER/SPACE: rotate pipe", True, ALIEN_TEXT_DIM),
                     (60, HEIGHT - 50))

    # ─── PUZZLE 1: LIGHTS OUT ────────────────────────────────────────────
    def _gen_lights_out(self):
        size = 5
        solution_moves = set()
        for _ in range(random.randint(8, 15)):
            r, c = random.randint(0, size - 1), random.randint(0, size - 1)
            if (r, c) in solution_moves:
                solution_moves.remove((r, c))
            else:
                solution_moves.add((r, c))
        grid = [[False] * size for _ in range(size)]
        for mr, mc in solution_moves:
            for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = mr + dr, mc + dc
                if 0 <= nr < size and 0 <= nc < size:
                    grid[nr][nc] = not grid[nr][nc]
        if all(not grid[r][c] for r in range(size) for c in range(size)):
            grid[0][0] = True
            grid[0][1] = True
            grid[1][0] = True
        return {"grid": grid, "size": size, "cursor": [0, 0]}

    def _handle_lights(self, event):
        ps = self.puzzle_state
        size = ps["size"]
        if event.type == pygame.KEYDOWN:
            cr, cc = ps["cursor"]
            if event.key == pygame.K_UP and cr > 0:
                ps["cursor"][0] -= 1
            elif event.key == pygame.K_DOWN and cr < size - 1:
                ps["cursor"][0] += 1
            elif event.key == pygame.K_LEFT and cc > 0:
                ps["cursor"][1] -= 1
            elif event.key == pygame.K_RIGHT and cc < size - 1:
                ps["cursor"][1] += 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                r, c = ps["cursor"]
                for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < size and 0 <= nc < size:
                        ps["grid"][nr][nc] = not ps["grid"][nr][nc]
                if all(not ps["grid"][r][c] for r in range(size) for c in range(size)):
                    self._solved()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            cell_w = min(100, (WIDTH - 300) // size)
            cell_h = min(100, (HEIGHT - 300) // size)
            start_x = CX - (size * cell_w) // 2
            start_y = CY - (size * cell_h) // 2 + 30
            for r in range(size):
                for c in range(size):
                    rx = start_x + c * cell_w
                    ry = start_y + r * cell_h
                    if rx <= mx < rx + cell_w and ry <= my < ry + cell_h:
                        ps["cursor"] = [r, c]
                        for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < size and 0 <= nc < size:
                                ps["grid"][nr][nc] = not ps["grid"][nr][nc]
                        if all(not ps["grid"][r][c] for r in range(size) for c in range(size)):
                            self._solved()
                        return

    def _draw_lights(self, screen):
        ps = self.puzzle_state
        size = ps["size"]
        cell_w = min(100, (WIDTH - 300) // size)
        cell_h = min(100, (HEIGHT - 300) // size)
        start_x = CX - (size * cell_w) // 2
        start_y = CY - (size * cell_h) // 2 + 30
        mx, my = pygame.mouse.get_pos()
        cr, cc = ps["cursor"]
        for r in range(size):
            for c in range(size):
                rx = start_x + c * cell_w
                ry = start_y + r * cell_h
                rect = pygame.Rect(rx, ry, cell_w - 4, cell_h - 4)
                on = ps["grid"][r][c]
                if on:
                    pulse = 0.5 + 0.5 * math.sin(self.particle_phase * 3 + r + c)
                    color = (int(40 + 80 * pulse), int(180 + 60 * pulse), int(160 + 40 * pulse))
                    glow = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
                    glow.fill((*color, 40))
                    screen.blit(glow, (rx, ry))
                else:
                    color = (15, 25, 35)
                pygame.draw.rect(screen, color, rect, border_radius=3)
                border_c = ALIEN_CYAN if on else (40, 60, 70)
                pygame.draw.rect(screen, border_c, rect, 1, border_radius=3)
                if r == cr and c == cc:
                    cursor_rect = pygame.Rect(rx - 2, ry - 2, cell_w, cell_h)
                    pygame.draw.rect(screen, ALIEN_CYAN, cursor_rect, 3, border_radius=5)
                if rx <= mx < rx + cell_w and ry <= my < ry + cell_h:
                    highlight = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
                    highlight.fill((*ALIEN_CYAN, 25))
                    screen.blit(highlight, (rx, ry))
        hint_font = pygame.font.SysFont("consolas", 14)
        screen.blit(hint_font.render("ARROWS: move cursor  |  ENTER/SPACE: toggle cell", True, ALIEN_TEXT_DIM),
                     (60, HEIGHT - 50))

    # ─── PUZZLE 2: SLIDING TILES ─────────────────────────────────────────
    def _gen_sliding_tiles(self):
        size = 4
        tiles = list(range(1, size * size)) + [0]
        for _ in range(200):
            blank = tiles.index(0)
            br, bc = blank // size, blank % size
            moves = []
            if br > 0:
                moves.append((-1, 0))
            if br < size - 1:
                moves.append((1, 0))
            if bc > 0:
                moves.append((0, -1))
            if bc < size - 1:
                moves.append((0, 1))
            dr, dc = random.choice(moves)
            tr, tc = br + dr, bc + dc
            ti = tr * size + tc
            tiles[blank], tiles[ti] = tiles[ti], tiles[blank]
        return {"tiles": tiles, "size": size, "moves": 0}

    def _handle_sliding(self, event):
        ps = self.puzzle_state
        size = ps["size"]
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            cell_w = min(120, (WIDTH - 300) // size)
            cell_h = min(120, (HEIGHT - 300) // size)
            start_x = CX - (size * cell_w) // 2
            start_y = CY - (size * cell_h) // 2 + 30
            for r in range(size):
                for c in range(size):
                    rx = start_x + c * cell_w
                    ry = start_y + r * cell_h
                    if rx <= mx < rx + cell_w and ry <= my < ry + cell_h:
                        idx = r * size + c
                        blank = ps["tiles"].index(0)
                        br, bc = blank // size, blank % size
                        if (abs(br - r) + abs(bc - c)) == 1:
                            ps["tiles"][blank], ps["tiles"][idx] = ps["tiles"][idx], ps["tiles"][blank]
                            ps["moves"] += 1
                            goal = list(range(1, size * size)) + [0]
                            if ps["tiles"] == goal:
                                self._solved()
                        return
        if event.type == pygame.KEYDOWN:
            blank = ps["tiles"].index(0)
            br, bc = blank // size, blank % size
            target = -1
            if event.key == pygame.K_UP and br < size - 1:
                target = (br + 1) * size + bc
            elif event.key == pygame.K_DOWN and br > 0:
                target = (br - 1) * size + bc
            elif event.key == pygame.K_LEFT and bc < size - 1:
                target = br * size + (bc + 1)
            elif event.key == pygame.K_RIGHT and bc > 0:
                target = br * size + (bc - 1)
            if 0 <= target < size * size:
                ps["tiles"][blank], ps["tiles"][target] = ps["tiles"][target], ps["tiles"][blank]
                ps["moves"] += 1
                goal = list(range(1, size * size)) + [0]
                if ps["tiles"] == goal:
                    self._solved()

    def _draw_sliding(self, screen):
        ps = self.puzzle_state
        size = ps["size"]
        cell_w = min(120, (WIDTH - 300) // size)
        cell_h = min(120, (HEIGHT - 300) // size)
        start_x = CX - (size * cell_w) // 2
        start_y = CY - (size * cell_h) // 2 + 30
        goal = list(range(1, size * size)) + [0]
        for r in range(size):
            for c in range(size):
                rx = start_x + c * cell_w
                ry = start_y + r * cell_h
                rect = pygame.Rect(rx, ry, cell_w - 4, cell_h - 4)
                idx = r * size + c
                val = ps["tiles"][idx]
                if val == 0:
                    pygame.draw.rect(screen, (8, 14, 24), rect, border_radius=6)
                    pygame.draw.rect(screen, (30, 50, 60), rect, 1, border_radius=6)
                else:
                    correct = val == idx + 1
                    bg = (20, 55, 50) if correct else (30, 35, 50)
                    pygame.draw.rect(screen, bg, rect, border_radius=6)
                    c_border = ALIEN_CYAN if correct else ALIEN_BORDER
                    pygame.draw.rect(screen, c_border, rect, 2, border_radius=6)
                    font = pygame.font.SysFont("consolas", 32, bold=True)
                    t = font.render(str(val), True, ALIEN_TEXT if correct else ALIEN_AMBER)
                    screen.blit(t, (rx + cell_w // 2 - t.get_width() // 2, ry + cell_h // 2 - t.get_height() // 2))
        hint_font = pygame.font.SysFont("consolas", 16)
        screen.blit(hint_font.render(f"Moves: {ps['moves']}  |  Click adjacent tile or use ARROW KEYS", True, ALIEN_TEXT_DIM),
                     (60, HEIGHT - 50))

    # ─── PUZZLE 3: LASER MIRRORS ─────────────────────────────────────────
    def _gen_laser_mirrors(self):
        size = 7
        grid = [[0] * size for _ in range(size)]
        mirrors = []
        laser_row = random.randint(1, size - 2)
        target_row = random.randint(1, size - 2)
        target_col = size - 1
        r, c = laser_row, 0
        path = [(r, c)]
        while c < size - 1:
            if random.random() < 0.4 and c < size - 2:
                grid[r][c] = 1
                mirrors.append((r, c))
                if random.random() < 0.5:
                    r = min(size - 1, r + 1)
                else:
                    r = max(0, r - 1)
            c += 1
            if 0 <= r < size:
                path.append((r, c))
        if (target_row, target_col) not in [(p[0], p[1]) for p in path]:
            target_row = path[-1][0]
        for mr, mc in mirrors:
            grid[mr][mc] = 1
        extra = random.randint(2, 4)
        for _ in range(extra):
            er = random.randint(0, size - 1)
            ec = random.randint(0, size - 1)
            if grid[er][ec] == 0 and (er, ec) != (laser_row, 0) and (er, ec) != (target_row, target_col):
                grid[er][ec] = 1
        target = (target_row, target_col)
        laser = (laser_row, 0)
        return {"grid": grid, "size": size, "laser": laser, "target": target, "cursor": [0, 0]}

    def _handle_laser(self, event):
        ps = self.puzzle_state
        size = ps["size"]
        if event.type == pygame.KEYDOWN:
            cr, cc = ps["cursor"]
            if event.key == pygame.K_UP and cr > 0:
                ps["cursor"][0] -= 1
            elif event.key == pygame.K_DOWN and cr < size - 1:
                ps["cursor"][0] += 1
            elif event.key == pygame.K_LEFT and cc > 0:
                ps["cursor"][1] -= 1
            elif event.key == pygame.K_RIGHT and cc < size - 1:
                ps["cursor"][1] += 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                r, c = ps["cursor"]
                if ps["grid"][r][c] == 1:
                    ps["grid"][r][c] = 2
                elif ps["grid"][r][c] == 2:
                    ps["grid"][r][c] = 0
                elif ps["grid"][r][c] == 0:
                    ps["grid"][r][c] = 1
                self._check_laser_solution()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            cell_w = min(100, (WIDTH - 300) // size)
            cell_h = min(100, (HEIGHT - 300) // size)
            start_x = CX - (size * cell_w) // 2
            start_y = CY - (size * cell_h) // 2 + 30
            for r in range(size):
                for c in range(size):
                    rx = start_x + c * cell_w
                    ry = start_y + r * cell_h
                    if rx <= mx < rx + cell_w and ry <= my < ry + cell_h:
                        ps["cursor"] = [r, c]
                        if ps["grid"][r][c] == 1:
                            ps["grid"][r][c] = 2
                        elif ps["grid"][r][c] == 2:
                            ps["grid"][r][c] = 0
                        elif ps["grid"][r][c] == 0:
                            ps["grid"][r][c] = 1
                        self._check_laser_solution()
                        return

    def _check_laser_solution(self):
        ps = self.puzzle_state
        size = ps["size"]
        lr, lc = ps["laser"]
        tr, tc = ps["target"]
        direction = (0, 1)
        r, c = lr, lc
        visited = set()
        for _ in range(200):
            if (r, c, direction) in visited:
                break
            visited.add((r, c, direction))
            if r == tr and c == tc:
                self._solved()
                return
            nr, nc = r + direction[0], c + direction[1]
            if nr < 0 or nr >= size or nc < 0 or nc >= size:
                break
            cell = ps["grid"][nr][nc]
            if cell == 1:
                direction = (-direction[1], -direction[0])
                r, c = nr, nc
            elif cell == 2:
                direction = (direction[1], direction[0])
                r, c = nr, nc
            else:
                r, c = nr, nc

    def _draw_laser(self, screen):
        ps = self.puzzle_state
        size = ps["size"]
        cell_w = min(100, (WIDTH - 300) // size)
        cell_h = min(100, (HEIGHT - 300) // size)
        start_x = CX - (size * cell_w) // 2
        start_y = CY - (size * cell_h) // 2 + 30
        cr, cc = ps["cursor"]
        beam_points = []
        lr, lc = ps["laser"]
        direction = (0, 1)
        r, c = lr, lc
        visited_beam = set()
        for _ in range(200):
            if (r, c, direction) in visited_beam:
                break
            visited_beam.add((r, c, direction))
            beam_points.append((start_x + c * cell_w + cell_w // 2, start_y + r * cell_h + cell_h // 2))
            nr, nc = r + direction[0], c + direction[1]
            if nr < 0 or nr >= size or nc < 0 or nc >= size:
                break
            cell = ps["grid"][nr][nc]
            if cell == 1:
                direction = (-direction[1], -direction[0])
                r, c = nr, nc
            elif cell == 2:
                direction = (direction[1], direction[0])
                r, c = nr, nc
            else:
                r, c = nr, nc
        if len(beam_points) > 1:
            glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for i in range(len(beam_points) - 1):
                pygame.draw.line(glow, (*ALIEN_RED, 180), beam_points[i], beam_points[i + 1], 3)
            screen.blit(glow, (0, 0))
            for bp in beam_points:
                pygame.draw.circle(screen, ALIEN_RED, bp, 4)
        for r in range(size):
            for c in range(size):
                rx = start_x + c * cell_w
                ry = start_y + r * cell_h
                rect = pygame.Rect(rx, ry, cell_w - 4, cell_h - 4)
                val = ps["grid"][r][c]
                if (r, c) == ps["laser"]:
                    pygame.draw.rect(screen, (80, 20, 20), rect, border_radius=4)
                    pygame.draw.rect(screen, ALIEN_RED, rect, 2, border_radius=4)
                    font_s = pygame.font.SysFont("consolas", 12, bold=True)
                    screen.blit(font_s.render("LASER", True, ALIEN_RED), (rx + 4, ry + 4))
                elif (r, c) == ps["target"]:
                    pygame.draw.rect(screen, (20, 80, 20), rect, border_radius=4)
                    pygame.draw.rect(screen, (0, 255, 100), rect, 2, border_radius=4)
                    font_s = pygame.font.SysFont("consolas", 12, bold=True)
                    screen.blit(font_s.render("TARGET", True, (0, 255, 100)), (rx + 2, ry + 4))
                else:
                    bg = (20, 30, 45)
                    pygame.draw.rect(screen, bg, rect, border_radius=4)
                    pygame.draw.rect(screen, ALIEN_BORDER, rect, 1, border_radius=4)
                    if val == 1:
                        pygame.draw.line(screen, ALIEN_AMBER, (rx + 8, ry + 8), (rx + cell_w - 12, ry + cell_h - 12), 3)
                        pygame.draw.line(screen, ALIEN_AMBER, (rx + cell_w - 8, ry + 8), (rx + 8, ry + cell_h - 12), 3)
                    elif val == 2:
                        pygame.draw.line(screen, (100, 200, 255), (rx + 8, ry + cell_h // 2), (rx + cell_w - 12, ry + cell_h // 2), 3)
                        pygame.draw.line(screen, (100, 200, 255), (rx + cell_w // 2, ry + 8), (rx + cell_w // 2, ry + cell_h - 12), 3)
                if r == cr and c == cc:
                    cursor_rect = pygame.Rect(rx - 2, ry - 2, cell_w, cell_h)
                    pygame.draw.rect(screen, ALIEN_CYAN, cursor_rect, 3, border_radius=5)
        hint_font = pygame.font.SysFont("consolas", 14)
        screen.blit(hint_font.render("ARROWS: move cursor  |  ENTER/SPACE: cycle mirror  (none/\\ /)", True, ALIEN_TEXT_DIM),
                     (60, HEIGHT - 50))

    # ─── PUZZLE 4: TIC TAC TOE ───────────────────────────────────────────
    _TTT_LINES = [
        [(0,0),(0,1),(0,2)], [(1,0),(1,1),(1,2)], [(2,0),(2,1),(2,2)],
        [(0,0),(1,0),(2,0)], [(0,1),(1,1),(2,1)], [(0,2),(1,2),(2,2)],
        [(0,0),(1,1),(2,2)], [(0,2),(1,1),(2,0)],
    ]

    def _gen_tictactoe(self):
        return {
            "board": [[None]*3 for _ in range(3)],
            "cursor": [1, 1],
            "ai_think": 0,
            "game_over": False,
            "winner": None,
            "win_line": None,
        }

    def _ttt_check_winner(self, board):
        for line in self._TTT_LINES:
            vals = [board[r][c] for r, c in line]
            if vals[0] is not None and vals[0] == vals[1] == vals[2]:
                return vals[0], line
        if all(board[r][c] is not None for r in range(3) for c in range(3)):
            return "draw", None
        return None, None

    def _ttt_ai_move(self, ps):
        board = ps["board"]
        empty = [(r, c) for r in range(3) for c in range(3) if board[r][c] is None]
        if not empty:
            return
        if random.random() < 0.4:
            r, c = random.choice(empty)
            board[r][c] = "O"
            return
        for mark in ["O", "X"]:
            for r, c in empty:
                board[r][c] = mark
                winner, line = self._ttt_check_winner(board)
                if winner == mark:
                    return
                board[r][c] = None
        if (1, 1) in empty:
            board[1][1] = "O"
            return
        corners = [(r, c) for r, c in [(0,0),(0,2),(2,0),(2,2)] if (r, c) in empty]
        if corners:
            r, c = random.choice(corners)
            board[r][c] = "O"
            return
        r, c = random.choice(empty)
        board[r][c] = "O"

    def _handle_tictactoe(self, event):
        ps = self.puzzle_state
        if ps["game_over"]:
            return
        if ps["ai_think"] > 0:
            return
        if event.type == pygame.KEYDOWN:
            cr, cc = ps["cursor"]
            if event.key == pygame.K_UP and cr > 0:
                ps["cursor"][0] -= 1
            elif event.key == pygame.K_DOWN and cr < 2:
                ps["cursor"][0] += 1
            elif event.key == pygame.K_LEFT and cc > 0:
                ps["cursor"][1] -= 1
            elif event.key == pygame.K_RIGHT and cc < 2:
                ps["cursor"][1] += 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                r, c = ps["cursor"]
                if ps["board"][r][c] is None:
                    ps["board"][r][c] = "X"
                    winner, line = self._ttt_check_winner(ps["board"])
                    if winner == "X":
                        ps["game_over"] = True
                        ps["winner"] = "X"
                        ps["win_line"] = line
                        self._solved()
                        return
                    elif winner == "draw":
                        ps["game_over"] = True
                        ps["winner"] = "draw"
                        self._failed()
                        return
                    ps["ai_think"] = 18
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            cell_size = min(160, (WIDTH - 400) // 3)
            start_x = CX - (3 * cell_size) // 2
            start_y = CY - (3 * cell_size) // 2
            for r in range(3):
                for c in range(3):
                    rx = start_x + c * cell_size
                    ry = start_y + r * cell_size
                    if rx <= mx < rx + cell_size and ry <= my < ry + cell_size:
                        ps["cursor"] = [r, c]
                        if ps["board"][r][c] is None:
                            ps["board"][r][c] = "X"
                            winner, line = self._ttt_check_winner(ps["board"])
                            if winner == "X":
                                ps["game_over"] = True
                                ps["winner"] = "X"
                                ps["win_line"] = line
                                self._solved()
                                return
                            elif winner == "draw":
                                ps["game_over"] = True
                                ps["winner"] = "draw"
                                self._failed()
                                return
                            ps["ai_think"] = 18
                        return

    def _draw_tictactoe(self, screen):
        ps = self.puzzle_state
        cell_size = min(160, (WIDTH - 400) // 3)
        start_x = CX - (3 * cell_size) // 2
        start_y = CY - (3 * cell_size) // 2
        cr, cc = ps["cursor"]
        font_s = pygame.font.SysFont("consolas", 16)
        for i in range(1, 3):
            lx = start_x + i * cell_size
            ly = start_y + i * cell_size
            pygame.draw.line(screen, ALIEN_BORDER, (lx, start_y), (lx, start_y + 3 * cell_size), 2)
            pygame.draw.line(screen, ALIEN_BORDER, (start_x, ly), (start_x + 3 * cell_size, ly), 2)
        for r in range(3):
            for c in range(3):
                rx = start_x + c * cell_size
                ry = start_y + r * cell_size
                if r == cr and c == cc and not ps["game_over"]:
                    cursor_rect = pygame.Rect(rx + 2, ry + 2, cell_size - 4, cell_size - 4)
                    pygame.draw.rect(screen, ALIEN_CYAN, cursor_rect, 3, border_radius=5)
                val = ps["board"][r][c]
                if val == "X":
                    margin = cell_size // 5
                    pygame.draw.line(screen, ALIEN_CYAN, (rx + margin, ry + margin),
                                     (rx + cell_size - margin, ry + cell_size - margin), 4)
                    pygame.draw.line(screen, ALIEN_CYAN, (rx + cell_size - margin, ry + margin),
                                     (rx + margin, ry + cell_size - margin), 4)
                elif val == "O":
                    center = (rx + cell_size // 2, ry + cell_size // 2)
                    radius = cell_size // 4
                    pygame.draw.circle(screen, ALIEN_AMBER, center, radius, 4)
        if ps["game_over"] and ps["win_line"]:
            for r, c in ps["win_line"]:
                rx = start_x + c * cell_size
                ry = start_y + r * cell_size
                glow = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
                glow.fill((*ALIEN_CYAN, 40))
                screen.blit(glow, (rx, ry))
        if ps["game_over"]:
            if ps["winner"] == "X":
                msg = "VICTORY // ACCESS GRANTED"
                color = ALIEN_CYAN
            else:
                msg = "DEFEAT // TRY AGAIN"
                color = ALIEN_RED
            t = font_s.render(msg, True, color)
            screen.blit(t, (CX - t.get_width() // 2, HEIGHT - 80))
        hint = font_s.render("ARROWS: move  |  ENTER/SPACE: place X  |  Beat the AI to unlock", True, ALIEN_TEXT_DIM)
        screen.blit(hint, (60, HEIGHT - 50))

    # ─── PUZZLE 5: SEQUENCE SOLVER ───────────────────────────────────────
    def _gen_sequence(self):
        seq_type = random.choice(["linear", "quadratic", "fibonacci", "geometric"])
        if seq_type == "linear":
            start = random.randint(1, 10)
            step = random.randint(2, 8)
            seq = [start + step * i for i in range(5)]
            answer = seq[-1] + step
        elif seq_type == "quadratic":
            a = random.randint(1, 3)
            b = random.randint(1, 5)
            c = random.randint(0, 5)
            seq = [a * i * i + b * i + c for i in range(1, 6)]
            answer = a * 36 + b * 6 + c
        elif seq_type == "fibonacci":
            a, b = random.randint(1, 5), random.randint(1, 5)
            seq = [a, b]
            for _ in range(3):
                seq.append(seq[-1] + seq[-2])
            answer = seq[-1] + seq[-2]
        else:
            start = random.randint(2, 5)
            ratio = random.randint(2, 3)
            seq = [start * (ratio ** i) for i in range(5)]
            answer = start * (ratio ** 5)
        return {"sequence": seq, "answer": answer, "input": "", "rounds_solved": 0, "rounds_needed": 2}

    def _handle_sequence(self, event):
        ps = self.puzzle_state
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                ps["input"] = ps["input"][:-1]
            elif event.key == pygame.K_RETURN:
                try:
                    guess = int(ps["input"])
                    if guess == ps["answer"]:
                        ps["rounds_solved"] += 1
                        if ps["rounds_solved"] >= ps["rounds_needed"]:
                            self._solved()
                        else:
                            self._gen_next_sequence_round()
                    else:
                        ps["input"] = ""
                except ValueError:
                    ps["input"] = ""
            elif event.unicode.isdigit() or (event.unicode == '-' and not ps["input"]):
                if len(ps["input"]) < 8:
                    ps["input"] += event.unicode

    def _gen_next_sequence_round(self):
        seq_type = random.choice(["linear", "quadratic", "fibonacci", "geometric"])
        if seq_type == "linear":
            start = random.randint(5, 20)
            step = random.randint(3, 12)
            seq = [start + step * i for i in range(5)]
            answer = seq[-1] + step
        elif seq_type == "quadratic":
            a = random.randint(1, 4)
            b = random.randint(2, 8)
            c = random.randint(0, 10)
            seq = [a * i * i + b * i + c for i in range(1, 6)]
            answer = a * 36 + b * 6 + c
        elif seq_type == "fibonacci":
            a, b = random.randint(3, 10), random.randint(3, 10)
            seq = [a, b]
            for _ in range(3):
                seq.append(seq[-1] + seq[-2])
            answer = seq[-1] + seq[-2]
        else:
            start = random.randint(3, 7)
            ratio = random.randint(2, 4)
            seq = [start * (ratio ** i) for i in range(5)]
            answer = start * (ratio ** 5)
        self.puzzle_state["sequence"] = seq
        self.puzzle_state["answer"] = answer
        self.puzzle_state["input"] = ""

    def _draw_sequence(self, screen):
        ps = self.puzzle_state
        font_big = pygame.font.SysFont("consolas", 40, bold=True)
        font_med = pygame.font.SysFont("consolas", 24)
        font_s = pygame.font.SysFont("consolas", 18)
        round_text = font_s.render(f"Round {ps['rounds_solved'] + 1}/{ps['rounds_needed']}", True, ALIEN_TEXT_DIM)
        screen.blit(round_text, (CX - round_text.get_width() // 2, 140))
        seq_display = "  →  ".join(str(n) for n in ps["sequence"]) + "  →  ?"
        t = font_big.render(seq_display, True, ALIEN_AMBER)
        screen.blit(t, (CX - t.get_width() // 2, CY - 60))
        input_rect = pygame.Rect(CX - 120, CY + 30, 240, 50)
        pygame.draw.rect(screen, (10, 20, 35), input_rect, border_radius=8)
        pygame.draw.rect(screen, ALIEN_CYAN, input_rect, 2, border_radius=8)
        display = ps["input"] if ps["input"] else "_"
        it = font_big.render(display, True, ALIEN_CYAN)
        screen.blit(it, (CX - it.get_width() // 2, CY + 35))
        hint = font_s.render("Type your answer and press ENTER", True, ALIEN_TEXT_DIM)
        screen.blit(hint, (CX - hint.get_width() // 2, HEIGHT - 50))

    # ─── PUZZLE 6: MEMORY GRID ───────────────────────────────────────────
    def _gen_memory_grid(self):
        size = 5
        target_count = 4
        cells = set()
        while len(cells) < target_count:
            cells.add((random.randint(0, size - 1), random.randint(0, size - 1)))
        return {
            "size": size, "highlighted": cells,
            "showing": True, "show_start": time.time(),
            "show_duration": 2.0, "clicked": set(),
            "round": 1, "max_rounds": 3,
            "target_count": target_count,
            "cursor": [0, 0],
        }

    def _handle_memory(self, event):
        ps = self.puzzle_state
        if ps.get("showing"):
            return
        size = ps["size"]
        if event.type == pygame.KEYDOWN:
            cr, cc = ps["cursor"]
            if event.key == pygame.K_UP and cr > 0:
                ps["cursor"][0] -= 1
            elif event.key == pygame.K_DOWN and cr < size - 1:
                ps["cursor"][0] += 1
            elif event.key == pygame.K_LEFT and cc > 0:
                ps["cursor"][1] -= 1
            elif event.key == pygame.K_RIGHT and cc < size - 1:
                ps["cursor"][1] += 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                r, c = ps["cursor"]
                if (r, c) not in ps["clicked"]:
                    ps["clicked"].add((r, c))
                    if (r, c) in ps["highlighted"]:
                        if ps["clicked"] == ps["highlighted"]:
                            if ps["round"] >= ps["max_rounds"]:
                                self._solved()
                            else:
                                ps["round"] += 1
                                ps["target_count"] += 2
                                cells = set()
                                while len(cells) < ps["target_count"]:
                                    cells.add((random.randint(0, size - 1), random.randint(0, size - 1)))
                                ps["highlighted"] = cells
                                ps["clicked"] = set()
                                ps["showing"] = True
                                ps["show_start"] = time.time()
                    else:
                        ps["clicked"].discard((r, c))
                        self._failed()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            cell_w = min(100, (WIDTH - 300) // size)
            cell_h = min(100, (HEIGHT - 300) // size)
            start_x = CX - (size * cell_w) // 2
            start_y = CY - (size * cell_h) // 2 + 30
            for r in range(size):
                for c in range(size):
                    rx = start_x + c * cell_w
                    ry = start_y + r * cell_h
                    if rx <= mx < rx + cell_w and ry <= my < ry + cell_h:
                        ps["cursor"] = [r, c]
                        if (r, c) not in ps["clicked"]:
                            ps["clicked"].add((r, c))
                            if (r, c) in ps["highlighted"]:
                                if ps["clicked"] == ps["highlighted"]:
                                    if ps["round"] >= ps["max_rounds"]:
                                        self._solved()
                                    else:
                                        ps["round"] += 1
                                        ps["target_count"] += 2
                                        cells = set()
                                        while len(cells) < ps["target_count"]:
                                            cells.add((random.randint(0, size - 1), random.randint(0, size - 1)))
                                        ps["highlighted"] = cells
                                        ps["clicked"] = set()
                                        ps["showing"] = True
                                        ps["show_start"] = time.time()
                            else:
                                ps["clicked"].discard((r, c))
                                self._failed()
                        return

    def _draw_memory(self, screen):
        ps = self.puzzle_state
        size = ps["size"]
        cell_w = min(100, (WIDTH - 300) // size)
        cell_h = min(100, (HEIGHT - 300) // size)
        start_x = CX - (size * cell_w) // 2
        start_y = CY - (size * cell_h) // 2 + 30
        cr, cc = ps["cursor"]
        font_s = pygame.font.SysFont("consolas", 16)
        screen.blit(font_s.render(f"Round {ps['round']}/{ps['max_rounds']}  |  Memorize {ps['target_count']} cells", True, ALIEN_TEXT_DIM),
                     (60, 130))
        for r in range(size):
            for c in range(size):
                rx = start_x + c * cell_w
                ry = start_y + r * cell_h
                rect = pygame.Rect(rx, ry, cell_w - 4, cell_h - 4)
                if ps["showing"]:
                    if (r, c) in ps["highlighted"]:
                        pygame.draw.rect(screen, ALIEN_CYAN, rect, border_radius=4)
                        glow = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
                        glow.fill((*ALIEN_CYAN, 60))
                        screen.blit(glow, (rx, ry))
                    else:
                        pygame.draw.rect(screen, (20, 30, 45), rect, border_radius=4)
                    pygame.draw.rect(screen, ALIEN_BORDER, rect, 1, border_radius=4)
                else:
                    if (r, c) in ps["clicked"]:
                        if (r, c) in ps["highlighted"]:
                            pygame.draw.rect(screen, (20, 80, 60), rect, border_radius=4)
                            pygame.draw.rect(screen, ALIEN_CYAN, rect, 2, border_radius=4)
                        else:
                            pygame.draw.rect(screen, (80, 20, 20), rect, border_radius=4)
                            pygame.draw.rect(screen, ALIEN_RED, rect, 2, border_radius=4)
                    elif (r, c) in ps["highlighted"] and ps["round"] > 1:
                        pygame.draw.rect(screen, (20, 30, 45), rect, border_radius=4)
                        pygame.draw.rect(screen, ALIEN_BORDER, rect, 1, border_radius=4)
                    else:
                        pygame.draw.rect(screen, (20, 30, 45), rect, border_radius=4)
                        pygame.draw.rect(screen, ALIEN_BORDER, rect, 1, border_radius=4)
                if r == cr and c == cc and not ps["showing"]:
                    cursor_rect = pygame.Rect(rx - 2, ry - 2, cell_w, cell_h)
                    pygame.draw.rect(screen, ALIEN_CYAN, cursor_rect, 3, border_radius=5)
        if ps["showing"]:
            remaining = max(0, ps["show_duration"] - (time.time() - ps["show_start"]))
            countdown = font_s.render(f"Memorize... {remaining:.1f}s", True, ALIEN_AMBER)
            screen.blit(countdown, (CX - countdown.get_width() // 2, HEIGHT - 50))
        else:
            hint_font = pygame.font.SysFont("consolas", 14)
            screen.blit(hint_font.render("ARROWS: move cursor  |  ENTER/SPACE: select cell", True, ALIEN_TEXT_DIM),
                         (60, HEIGHT - 50))

    def _gen_weight_balance(self):
        symbols = ["A", "B", "C", "D", "E"]
        num_objects = 5
        weights = {}
        for i in range(num_objects):
            weights[symbols[i]] = random.randint(1, 10)
        clues = []
        all_syms = list(symbols[:num_objects])
        for _ in range(6):
            a, b = random.sample(all_syms, 2)
            wa, wb = weights[a], weights[b]
            if wa > wb:
                clues.append(f"{a} > {b}")
            elif wb > wa:
                clues.append(f"{b} > {a}")
            else:
                clues.append(f"{a} = {b}")
        for _ in range(2):
            triplet = random.sample(all_syms, 3)
            wsum = weights[triplet[0]] + weights[triplet[1]]
            wc = weights[triplet[2]]
            if wsum > wc:
                clues.append(f"{triplet[0]} + {triplet[1]} > {triplet[2]}")
            else:
                clues.append(f"{triplet[0]} + {triplet[1]} < {triplet[2]}")
        max_sym = max(weights, key=weights.get)
        return {
            "symbols": symbols[:num_objects],
            "weights": weights,
            "clues": clues,
            "answer": max_sym,
            "input": "",
        }

    def _handle_weight(self, event):
        ps = self.puzzle_state
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                ps["input"] = ps["input"][:-1]
            elif event.key == pygame.K_RETURN:
                if ps["input"].strip().lower() == ps["answer"].lower():
                    self._solved()
                else:
                    ps["input"] = ""
            elif event.unicode.isalpha():
                if len(ps["input"]) < 3:
                    ps["input"] += event.unicode

    def _draw_weight(self, screen):
        ps = self.puzzle_state
        font = pygame.font.SysFont("consolas", 22, bold=True)
        font_s = pygame.font.SysFont("consolas", 18)
        title = font.render("Determine the HEAVIEST object", True, ALIEN_AMBER)
        screen.blit(title, (CX - title.get_width() // 2, 140))
        clue_y = 190
        for clue in ps["clues"]:
            t = font_s.render(clue, True, ALIEN_TEXT)
            screen.blit(t, (CX - t.get_width() // 2, clue_y))
            clue_y += 28
        scale_y = clue_y + 40
        beam_w = 300
        pygame.draw.line(screen, ALIEN_TEXT_DIM, (CX - beam_w // 2, scale_y), (CX + beam_w // 2, scale_y), 3)
        pygame.draw.polygon(screen, ALIEN_TEXT_DIM, [(CX, scale_y), (CX - 15, scale_y + 25), (CX + 15, scale_y + 25)])
        for i, sym in enumerate(ps["symbols"]):
            x = CX - beam_w // 2 + 30 + i * (beam_w - 60) // (len(ps["symbols"]) - 1)
            pygame.draw.circle(screen, ALIEN_TEAL, (x, scale_y - 25), 18, 2)
            t = font.render(sym, True, ALIEN_TEXT)
            screen.blit(t, (x - t.get_width() // 2, scale_y - 35))
        input_y = scale_y + 70
        input_rect = pygame.Rect(CX - 120, input_y, 240, 45)
        pygame.draw.rect(screen, (10, 20, 35), input_rect, border_radius=8)
        pygame.draw.rect(screen, ALIEN_CYAN, input_rect, 2, border_radius=8)
        display = ps["input"] if ps["input"] else "_"
        it = font.render(display, True, ALIEN_CYAN)
        screen.blit(it, (CX - it.get_width() // 2, input_y + 5))
        hint = font_s.render("Type the symbol of the heaviest object and press ENTER", True, ALIEN_TEXT_DIM)
        screen.blit(hint, (CX - hint.get_width() // 2, HEIGHT - 50))

    # ─── PUZZLE 8: COLOR MIXER ───────────────────────────────────────────
    def _gen_color_mixer(self):
        target_r = random.randint(40, 220)
        target_g = random.randint(40, 220)
        target_b = random.randint(40, 220)
        return {
            "target": (target_r, target_g, target_b),
            "current": [128, 128, 128],
            "tolerance": 30,
            "cursor": 0,
        }

    def _handle_color(self, event):
        ps = self.puzzle_state
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and ps["cursor"] > 0:
                ps["cursor"] -= 1
            elif event.key == pygame.K_DOWN and ps["cursor"] < 2:
                ps["cursor"] += 1
            elif event.key == pygame.K_LEFT:
                idx = ps["cursor"]
                ps["current"][idx] = max(0, ps["current"][idx] - 15)
                self._check_color()
            elif event.key == pygame.K_RIGHT:
                idx = ps["cursor"]
                ps["current"][idx] = min(255, ps["current"][idx] + 15)
                self._check_color()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                idx = ps["cursor"]
                ps["current"][idx] = min(255, ps["current"][idx] + 15)
                self._check_color()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            slider_x = CX - 200
            slider_w = 400
            slider_h = 20
            for i in range(3):
                sy = 320 + i * 70
                if slider_x <= mx <= slider_x + slider_w and sy - 5 <= my <= sy + slider_h + 5:
                    ps["cursor"] = i
                    ratio = max(0.0, min(1.0, (mx - slider_x) / slider_w))
                    ps["current"][i] = int(ratio * 255)
                    self._check_color()
                    return

    def _check_color(self):
        ps = self.puzzle_state
        t = ps["target"]
        c = ps["current"]
        tol = ps["tolerance"]
        if all(abs(t[i] - c[i]) <= tol for i in range(3)):
            self._solved()

    def _draw_color(self, screen):
        ps = self.puzzle_state
        font = pygame.font.SysFont("consolas", 20, bold=True)
        font_s = pygame.font.SysFont("consolas", 16)
        title = font.render("Mix the colors to match the target", True, ALIEN_AMBER)
        screen.blit(title, (CX - title.get_width() // 2, 140))
        target_rect = pygame.Rect(CX - 100, 175, 200, 80)
        pygame.draw.rect(screen, ps["target"], target_rect, border_radius=8)
        pygame.draw.rect(screen, ALIEN_AMBER, target_rect, 2, border_radius=8)
        t = font_s.render(f"TARGET: ({ps['target'][0]}, {ps['target'][1]}, {ps['target'][2]})", True, ALIEN_AMBER)
        screen.blit(t, (CX - t.get_width() // 2, 260))
        labels = ["RED", "GREEN", "BLUE"]
        colors = [(220, 60, 60), (60, 200, 60), (60, 100, 220)]
        slider_x = CX - 200
        slider_w = 400
        for i in range(3):
            sy = 320 + i * 70
            lbl = font_s.render(labels[i], True, colors[i])
            screen.blit(lbl, (slider_x - 60, sy + 2))
            pygame.draw.rect(screen, (30, 40, 55), (slider_x, sy, slider_w, 20), border_radius=10)
            fill = int(slider_w * ps["current"][i] / 255)
            pygame.draw.rect(screen, colors[i], (slider_x, sy, fill, 20), border_radius=10)
            pygame.draw.rect(screen, ALIEN_BORDER, (slider_x, sy, slider_w, 20), 1, border_radius=10)
            val_t = font_s.render(str(ps["current"][i]), True, ALIEN_TEXT)
            screen.blit(val_t, (slider_x + slider_w + 10, sy + 2))
            if i == ps["cursor"]:
                cursor_rect = pygame.Rect(slider_x - 4, sy - 4, slider_w + 8, 28)
                pygame.draw.rect(screen, ALIEN_CYAN, cursor_rect, 2, border_radius=12)
        result_rect = pygame.Rect(CX - 100, 550, 200, 80)
        pygame.draw.rect(screen, tuple(ps["current"]), result_rect, border_radius=8)
        pygame.draw.rect(screen, ALIEN_CYAN, result_rect, 2, border_radius=8)
        t = font_s.render(f"YOUR MIX: ({ps['current'][0]}, {ps['current'][1]}, {ps['current'][2]})", True, ALIEN_CYAN)
        screen.blit(t, (CX - t.get_width() // 2, 635))
        hint = font_s.render("UP/DOWN: select channel  |  LEFT/RIGHT: adjust value  (15 per step)", True, ALIEN_TEXT_DIM)
        screen.blit(hint, (CX - hint.get_width() // 2, HEIGHT - 50))

    # ─── PUZZLE 9: THE KEYPAD ────────────────────────────────────────────
    def _gen_keypad(self):
        digits = [random.randint(0, 9) for _ in range(3)]
        while digits[0] % 2 != 0:
            digits[0] = random.randint(0, 9)
        while digits[1] <= 5:
            digits[1] = random.randint(0, 9)
        digits[2] = abs(digits[0] - digits[1])
        while digits[2] > 9:
            digits[0] = random.randint(0, 8)
            digits[1] = random.randint(6, 9)
            digits[2] = abs(digits[0] - digits[1])
        code = f"{digits[0]}{digits[1]}{digits[2]}"
        clues = [
            f"The first digit is even.",
            f"The second digit is greater than 5.",
            f"The third digit is the difference between the first two.",
        ]
        extra_clues = [
            f"The sum of all digits is {sum(digits)}.",
            f"The product of the first and third is {digits[0] * digits[2]}.",
            f"The digits in order {'increase' if digits[1] > digits[0] else 'decrease'} then {'increase' if digits[2] > digits[1] else 'decrease'}.",
        ]
        random.shuffle(extra_clues)
        clues.append(extra_clues[0])
        return {"code": code, "clues": clues, "input": ""}

    def _handle_keypad(self, event):
        ps = self.puzzle_state
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                ps["input"] = ps["input"][:-1]
            elif event.key == pygame.K_RETURN:
                if ps["input"] == ps["code"]:
                    self._solved()
                else:
                    ps["input"] = ""
            elif event.unicode.isdigit():
                if len(ps["input"]) < 3:
                    ps["input"] += event.unicode

    def _draw_keypad(self, screen):
        ps = self.puzzle_state
        font = pygame.font.SysFont("consolas", 22, bold=True)
        font_s = pygame.font.SysFont("consolas", 18)
        title = font.render("DECRYPT THE 3-DIGIT CODE", True, ALIEN_AMBER)
        screen.blit(title, (CX - title.get_width() // 2, 140))
        clue_y = 190
        for clue in ps["clues"]:
            t = font_s.render(clue, True, ALIEN_TEXT)
            screen.blit(t, (CX - t.get_width() // 2, clue_y))
            clue_y += 30
        input_y = clue_y + 30
        input_rect = pygame.Rect(CX - 100, input_y, 200, 50)
        pygame.draw.rect(screen, (10, 20, 35), input_rect, border_radius=8)
        pygame.draw.rect(screen, ALIEN_CYAN, input_rect, 2, border_radius=8)
        display = ps["input"] if ps["input"] else "___"
        if len(display) < 3:
            display = display + "_" * (3 - len(display))
        it = font.render(display, True, ALIEN_CYAN)
        screen.blit(it, (CX - it.get_width() // 2, input_y + 8))
        for i in range(3):
            sx = CX - 80 + i * 60
            sy = input_y + 70
            digit_rect = pygame.Rect(sx, sy, 45, 45)
            digit = int(ps["input"][i]) if i < len(ps["input"]) else -1
            if digit >= 0:
                pygame.draw.rect(screen, (20, 55, 50), digit_rect, border_radius=6)
                pygame.draw.rect(screen, ALIEN_CYAN, digit_rect, 2, border_radius=6)
                t = font.render(str(digit), True, ALIEN_CYAN)
                screen.blit(t, (sx + 22 - t.get_width() // 2, sy + 10))
            else:
                pygame.draw.rect(screen, (20, 30, 45), digit_rect, border_radius=6)
                pygame.draw.rect(screen, ALIEN_BORDER, digit_rect, 1, border_radius=6)
        hint = font_s.render("Type the 3-digit code and press ENTER", True, ALIEN_TEXT_DIM)
        screen.blit(hint, (CX - hint.get_width() // 2, HEIGHT - 50))

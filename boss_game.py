# ============================================================
#  boss_game.py  —  MODULE C: Boss Battle Arena
#  AL2002 Battle City AI Project
#
#  A separate 12x12 arena game loop for the Boss Level.
#  The Boss Tank uses Minimax + Alpha-Beta Pruning.
#  The game displays:
#    - Boss HP bar with phase indicator
#    - Live Minimax node count stats (for report)
#    - Phase transitions with visual feedback
# ============================================================

import sys
import random

import pygame

from constants import (
    TILE_SIZE, PANEL_W, COLOR,
    EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE
)
from tanks import PlayerTank
from boss_tank import BossTank
from bullet import Bullet

# Direction vectors
UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)

KEY_TO_DIR = {
    pygame.K_UP   : UP,
    pygame.K_w    : UP,
    pygame.K_DOWN : DOWN,
    pygame.K_s    : DOWN,
    pygame.K_LEFT : LEFT,
    pygame.K_a    : LEFT,
    pygame.K_RIGHT: RIGHT,
    pygame.K_d    : RIGHT,
}

TILE_COLOR = {
    EMPTY : (30,  30,  30),
    BRICK : (180, 80,  40),
    STEEL : (130, 140, 150),
    WATER : (40,  80,  180),
    FOREST: (30,  110, 50),
    EAGLE : (220, 200, 50),
}

ARENA_SIZE = 12


# ============================================================
#  ARENA MAP GENERATOR  (12x12, from spec)
# ============================================================

def generate_boss_arena():
    """
    Generate the 12x12 boss arena.
    From spec: mixed terrain — some brick, some steel pillars,
    one water patch. No CSP needed — fixed layout with random variation.
    """
    grid = [[EMPTY] * ARENA_SIZE for _ in range(ARENA_SIZE)]

    # Steel pillars (fixed positions — provide cover)
    steel_positions = [
        (2, 2), (2, 3), (9, 2), (9, 3),
        (2, 8), (2, 9), (9, 8), (9, 9),
        (5, 5), (6, 5),
    ]
    for x, y in steel_positions:
        grid[y][x] = STEEL

    # Brick walls (destructible during fight)
    brick_positions = [
        (4, 2), (5, 2), (6, 2), (7, 2),
        (4, 9), (5, 9), (6, 9), (7, 9),
        (2, 5), (2, 6),
        (9, 5), (9, 6),
    ]
    for x, y in brick_positions:
        grid[y][x] = BRICK

    # One water patch (from spec)
    for x in range(4, 7):
        grid[6][x] = WATER

    return grid


# ============================================================
#  BOSS GAME CLASS
# ============================================================

class BossGame:
    """
    The Boss Level game loop.
    12x12 arena, player vs Boss Tank (Minimax AI).
    """

    CELL = TILE_SIZE

    def __init__(self):
        import pygame
        self.pygame = pygame
        pygame.init()

        win_w = ARENA_SIZE * self.CELL + PANEL_W + 40
        win_h = ARENA_SIZE * self.CELL + 40
        self.screen = pygame.display.set_mode((win_w, win_h))
        pygame.display.set_caption(
            "Battle City AI — Boss Level: Tank Commander (Module C: Minimax)"
        )

        self.font_sm = pygame.font.SysFont('monospace', 11)
        self.font_md = pygame.font.SysFont('monospace', 13, bold=True)
        self.font_lg = pygame.font.SysFont('monospace', 18, bold=True)
        self.clock   = pygame.time.Clock()
        self.FPS     = 30

        self._init_boss_level()

    # ----------------------------------------------------------

    def _init_boss_level(self):
        self.grid    = generate_boss_arena()
        self.player  = PlayerTank(1, 10)
        self.player.direction = UP
        self.player.speed = 3

        self.boss    = BossTank(10, 1, arena_size=ARENA_SIZE)
        self.bullets = []

        self.game_over  = False
        self.victory    = False
        self.reason     = ''
        self.tick       = 0

        # Flash effect on phase change
        self.flash_timer = 0
        self.flash_color = None

        # Node count display (updated live)
        self.last_stats  = {}

    # ----------------------------------------------------------
    #  MAIN LOOP
    # ----------------------------------------------------------

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_r and self.game_over:
                        self._init_boss_level()

            if not self.game_over:
                self._tick()

            self._render()
            self.clock.tick(self.FPS)
            self.tick += 1

        # Print final report stats before quitting
        stats = self.boss.get_report_stats()
        print("\n" + "=" * 55)
        print("  MODULE C — BOSS BATTLE REPORT")
        print("=" * 55)
        print(f"  Minimax decisions made : {stats['decisions_made']}")
        print(f"  Nodes (no pruning)     : {stats['total_nodes_minimax']}")
        print(f"  Nodes (Alpha-Beta)     : {stats['total_nodes_alphabeta']}")
        print(f"  Speedup ratio          : {stats['speedup_ratio']}x")
        print("=" * 55)

        pygame.quit()
        sys.exit()

    # ----------------------------------------------------------
    #  GAME TICK
    # ----------------------------------------------------------

    def _tick(self):
        # ── Step 1: INPUT ─────────────────────────────────────
        keys = pygame.key.get_pressed()
        move_dir   = None
        want_shoot = False
        for k, d in KEY_TO_DIR.items():
            if keys[k]:
                move_dir = d
                break
        if keys[pygame.K_SPACE]:
            want_shoot = True

        # ── Tick timers ───────────────────────────────────────
        self.player.tick_timers()
        self.boss.tick_timers()

        # ── Step 2: AGENT DECISION (Minimax) ──────────────────
        boss_action = self.boss.decide(self.grid, self.player)
        if self.boss.all_stats:
            self.last_stats = self.boss.all_stats[-1]

        # ── Step 3: MOVE ──────────────────────────────────────
        all_tanks = [self.player]

        if move_dir and self.player.move_ready():
            nx = self.player.x + move_dir[0]
            ny = self.player.y + move_dir[1]
            if (0 <= nx < ARENA_SIZE and 0 <= ny < ARENA_SIZE
                    and self.grid[ny][nx] not in {BRICK, STEEL, WATER}
                    and not (nx == self.boss.x and ny == self.boss.y)):
                self.player.x, self.player.y = nx, ny
                self.player.direction  = move_dir
                self.player.move_timer = self.player.speed

        if boss_action.get('move') and self.boss.move_ready():
            self.boss.try_move(boss_action['move'], self.grid, self.player)

        # ── Step 4: SHOOT ─────────────────────────────────────
        if want_shoot and self.player.can_shoot():
            b = self.player.shoot(owner='player')
            if b:
                b.size = ARENA_SIZE
                self.bullets.append(b)

        if boss_action.get('shoot') and self.boss.can_shoot():
            b = self.boss.shoot()
            if b:
                self.bullets.append(b)

        # ── Step 5: BULLET UPDATE ─────────────────────────────
        for b in self.bullets:
            if b.alive:
                b.update(self.grid)

        # ── Step 6 & 7: COLLISION + STATE UPDATE ──────────────
        self._handle_collisions()
        self.bullets = [b for b in self.bullets if b.alive]

        # Flash effect
        if self.flash_timer > 0:
            self.flash_timer -= 1

        # ── Step 10: WIN/LOSE CHECK ───────────────────────────
        self._check_end()

    # ----------------------------------------------------------
    #  COLLISION
    # ----------------------------------------------------------

    def _handle_collisions(self):
        for b in self.bullets:
            if not b.alive:
                continue

            # Boss bullet hits player
            if b.owner == 'boss' and b.x == self.player.x and b.y == self.player.y:
                b.alive = False
                self.player.take_hit()
                if not self.player.alive:
                    if self.player.lives > 0:
                        self.player.respawn(1, 10)
                    else:
                        self._end(False, 'Player defeated!')
                return

            # Player bullet hits boss
            if b.owner == 'player' and b.x == self.boss.x and b.y == self.boss.y:
                b.alive = False
                old_phase = self.boss.current_phase
                self.boss.take_hit()
                if not self.boss.alive:
                    self._end(True, 'Boss destroyed!')
                elif self.boss.current_phase != old_phase:
                    # Phase changed — trigger flash
                    self.flash_timer = 20
                    colors = {2: (255, 200, 50), 3: (255, 80, 80)}
                    self.flash_color = colors.get(self.boss.current_phase, (255,255,255))
                return

            # Bullet vs bullet
            for other in self.bullets:
                if other is not b and other.alive and b.alive:
                    if b.x == other.x and b.y == other.y:
                        b.alive = False
                        other.alive = False

    def _end(self, victory, reason):
        self.game_over = True
        self.victory   = victory
        self.reason    = reason

    def _check_end(self):
        if not self.player.alive and self.player.lives <= 0:
            self._end(False, 'Player defeated!')
        if not self.boss.alive:
            self._end(True, 'Boss destroyed!')

    # ----------------------------------------------------------
    #  RENDER
    # ----------------------------------------------------------

    def _render(self):
        self.screen.fill(COLOR['bg'])
        offset_x = 20
        offset_y = 20

        self._draw_arena(offset_x, offset_y)
        self._draw_tanks(offset_x, offset_y)
        self._draw_bullets(offset_x, offset_y)
        self._draw_panel(offset_x + ARENA_SIZE * self.CELL + 10, 0)

        # Phase flash overlay
        if self.flash_timer > 0 and self.flash_color:
            alpha = int(160 * self.flash_timer / 20)
            flash = pygame.Surface(
                (ARENA_SIZE * self.CELL, ARENA_SIZE * self.CELL), pygame.SRCALPHA
            )
            flash.fill((*self.flash_color, alpha))
            self.screen.blit(flash, (offset_x, offset_y))

        if self.game_over:
            self._draw_game_over(offset_x, offset_y)

        pygame.display.flip()

    def _draw_arena(self, ox, oy):
        cell = self.CELL
        for r, row in enumerate(self.grid):
            for c, tile in enumerate(row):
                color = TILE_COLOR.get(tile, (80, 0, 80))
                rect  = pygame.Rect(ox + c*cell, oy + r*cell, cell, cell)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, COLOR['grid_line'], rect, 1)

                if tile == BRICK:
                    dark = (140, 60, 25)
                    pygame.draw.line(self.screen, dark,
                                     (ox+c*cell, oy+r*cell+cell//2),
                                     (ox+c*cell+cell, oy+r*cell+cell//2), 1)
                elif tile == STEEL:
                    light = (170, 185, 200)
                    pygame.draw.line(self.screen, light,
                                     (ox+c*cell+2, oy+r*cell+2),
                                     (ox+c*cell+cell-2, oy+r*cell+cell-2), 1)
                    pygame.draw.line(self.screen, light,
                                     (ox+c*cell+cell-2, oy+r*cell+2),
                                     (ox+c*cell+2, oy+r*cell+cell-2), 1)

    def _draw_tanks(self, ox, oy):
        cell = self.CELL

        # Player (green)
        if self.player.alive:
            x = ox + self.player.x * cell + 2
            y = oy + self.player.y * cell + 2
            w = cell - 4
            pygame.draw.rect(self.screen, (80, 220, 100), (x, y, w, w))
            pygame.draw.rect(self.screen, (255, 255, 255), (x, y, w, w), 1)
            cx = ox + self.player.x * cell + cell//2
            cy = oy + self.player.y * cell + cell//2
            dx, dy = self.player.direction
            pts = [(cx+dx*7, cy+dy*7), (cx-dy*4, cy+dx*4), (cx+dy*4, cy-dx*4)]
            pygame.draw.polygon(self.screen, (255, 255, 255), pts)

        # Boss — color changes by phase and HP
        if self.boss.alive:
            phase_colors = {1: (220, 60, 60), 2: (220, 130, 40), 3: (200, 40, 200)}
            color = phase_colors.get(self.boss.current_phase, (220, 60, 60))

            # Flash white when taking a hit
            if self.flash_timer > 15:
                color = (255, 255, 255)

            x = ox + self.boss.x * cell + 1
            y = oy + self.boss.y * cell + 1
            w = cell - 2
            pygame.draw.rect(self.screen, color, (x, y, w, w))
            pygame.draw.rect(self.screen, (255, 255, 255), (x, y, w, w), 2)
            cx = ox + self.boss.x * cell + cell//2
            cy = oy + self.boss.y * cell + cell//2
            dx, dy = self.boss.direction
            pts = [(cx+dx*8, cy+dy*8), (cx-dy*5, cy+dx*5), (cx+dy*5, cy-dx*5)]
            pygame.draw.polygon(self.screen, (255, 255, 255), pts)

    def _draw_bullets(self, ox, oy):
        cell = self.CELL
        for b in self.bullets:
            if b.alive:
                color = (255, 255, 100) if b.owner == 'player' else (255, 60, 60)
                cx = ox + b.x * cell + cell//2
                cy = oy + b.y * cell + cell//2
                pygame.draw.rect(self.screen, color, (cx-3, cy-3, 6, 6))

    def _draw_panel(self, px, py):
        pw = PANEL_W + 30
        ph = ARENA_SIZE * self.CELL + 40
        pygame.draw.rect(self.screen, COLOR['panel'], (px, py, pw, ph))

        y = py + 10
        def txt(msg, color=COLOR['text'], f=None):
            nonlocal y
            s = (f or self.font_sm).render(msg, True, color)
            self.screen.blit(s, (px + 8, y))
            y += s.get_height() + 3

        def div():
            nonlocal y
            pygame.draw.line(self.screen, (70,70,70),
                             (px+6, y), (px+pw-6, y), 1)
            y += 6

        txt('MODULE C', COLOR['highlight'], self.font_md)
        txt('Minimax + Alpha-Beta', COLOR['text_dim'])
        div()

        # Boss status
        txt('BOSS: Tank Commander', COLOR['highlight'], self.font_md)
        phase_colors = {1:(220,80,80), 2:(220,160,60), 3:(200,60,200)}
        pc = phase_colors.get(self.boss.current_phase, (220,80,80))
        txt(f"Phase: {self.boss.current_phase} — {self.boss.get_phase_label()}", pc)
        txt(f"Minimax depth: {self.boss.depth}")

        # Boss HP bar
        bar_w = pw - 20
        bar_h = 12
        filled = int(bar_w * self.boss.hp / self.boss.max_hp)
        pygame.draw.rect(self.screen, (60, 20, 20), (px+8, y, bar_w, bar_h))
        pygame.draw.rect(self.screen, pc, (px+8, y, filled, bar_h))
        pygame.draw.rect(self.screen, (180, 180, 180), (px+8, y, bar_w, bar_h), 1)
        hp_lbl = self.font_sm.render(f"{self.boss.hp}/{self.boss.max_hp} HP", True, (255,255,255))
        self.screen.blit(hp_lbl, (px + bar_w//2 - 15, y + 1))
        y += bar_h + 6

        div()

        # Player status
        txt('PLAYER', COLOR['highlight'], self.font_md)
        txt(f"HP:    {self.player.hp}")
        txt(f"Lives: {self.player.lives}")
        div()

        # Live Minimax stats (the report data)
        txt('MINIMAX STATS (live)', COLOR['highlight'], self.font_md)
        if self.last_stats:
            mm  = self.last_stats.get('nodes_minimax', 0)
            ab  = self.last_stats.get('nodes_alphabeta', 0)
            sp  = self.last_stats.get('speedup_ratio', 0)
            pr  = self.last_stats.get('branches_pruned', 0)
            txt(f"Depth:    {self.last_stats.get('depth', '-')}")
            txt(f"No prune: {mm} nodes")
            txt(f"A-Beta:   {ab} nodes")
            txt(f"Pruned:   {pr} branches")
            txt(f"Speedup:  {sp}x", (100, 220, 100))
        else:
            txt("Waiting for boss...", COLOR['text_dim'])

        div()

        # Cumulative stats
        txt('CUMULATIVE REPORT', COLOR['highlight'], self.font_md)
        total_mm = self.boss.total_nodes_mm
        total_ab = self.boss.total_nodes_ab
        ratio = round(total_mm / max(total_ab, 1), 2)
        txt(f"Total (no prune): {total_mm}")
        txt(f"Total (A-Beta):   {total_ab}")
        txt(f"Total speedup:    {ratio}x", (100, 220, 100))
        txt(f"Decisions made:   {len(self.boss.all_stats)}")
        div()

        # Phase legend
        txt('PHASE LEGEND', COLOR['highlight'], self.font_md)
        txt('Ph1 (10-7HP): depth=2', (220, 80, 80))
        txt('Ph2 (6-3HP):  depth=3', (220, 160, 60))
        txt('Ph3 (2-1HP):  depth=4', (200, 60, 200))
        div()

        txt('CONTROLS', COLOR['highlight'], self.font_md)
        txt('WASD/Arrows: Move', COLOR['text_dim'])
        txt('SPACE:       Shoot', COLOR['text_dim'])
        txt('R (over):    Restart', COLOR['text_dim'])
        txt('ESC:         Quit', COLOR['text_dim'])

    def _draw_game_over(self, ox, oy):
        surf = pygame.Surface((ARENA_SIZE*self.CELL, ARENA_SIZE*self.CELL), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 170))
        self.screen.blit(surf, (ox, oy))

        cx = ox + ARENA_SIZE * self.CELL // 2
        cy = oy + ARENA_SIZE * self.CELL // 2

        msg   = 'VICTORY!' if self.victory else 'DEFEATED'
        color = (100, 255, 100) if self.victory else (255, 80, 80)
        s1 = self.font_lg.render(msg, True, color)
        self.screen.blit(s1, (cx - s1.get_width()//2, cy - 30))

        s2 = self.font_sm.render(self.reason, True, (220, 220, 220))
        self.screen.blit(s2, (cx - s2.get_width()//2, cy + 5))

        s3 = self.font_sm.render('R = restart  |  ESC = quit', True, COLOR['text_dim'])
        self.screen.blit(s3, (cx - s3.get_width()//2, cy + 25))

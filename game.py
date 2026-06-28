# ============================================================
#  game.py  —  Full Game Loop (Module B Integration)
#  AL2002 Battle City AI Project
#
#  Implements the 10-step game loop from the spec:
#  1.  INPUT          — Read player keyboard input
#  2.  AGENT DECISIONS— Each enemy runs its AI decision logic
#  3.  MOVE           — All tanks attempt to move
#  4.  SHOOT          — All tanks that chose to shoot fire bullets
#  5.  BULLET UPDATE  — All bullets advance one tile
#  6.  COLLISION      — Bullet vs wall/tank/bullet/Eagle
#  7.  STATE UPDATE   — Destroy walls, reduce HP, remove dead tanks
#  8.  SPAWN CHECK    — Spawn next enemy if < 4 active
#  9.  RENDER         — Draw everything to screen
#  10. WIN/LOSE CHECK — Check end conditions
# ============================================================

import pygame
import sys
import random

from constants import (
    GRID_SIZE, TILE_SIZE, PANEL_W, EAGLE_POS, PLAYER_START,
    ENEMY_SPAWNS, LEVEL_CONFIG, COLOR,
    EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE
)
from map_generator import CSPMapGenerator
from tanks import PlayerTank, BasicTank, FastTank, ArmorTank, spawn_tank
from bullet import Bullet
from search import manhattan

# Direction vectors
UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)

# Key → direction mapping
KEY_TO_DIR = {
    pygame.K_UP    : UP,
    pygame.K_w     : UP,
    pygame.K_DOWN  : DOWN,
    pygame.K_s     : DOWN,
    pygame.K_LEFT  : LEFT,
    pygame.K_a     : LEFT,
    pygame.K_RIGHT : RIGHT,
    pygame.K_d     : RIGHT,
}

# Tile drawing colors (same as renderer.py)
TILE_COLOR = {
    EMPTY : (30, 30, 30),
    BRICK : (180, 80, 40),
    STEEL : (130, 140, 150),
    WATER : (40, 80, 180),
    FOREST: (30, 110, 50),
    EAGLE : (220, 200, 50),
}


# ============================================================
#  LEVEL ENEMY QUEUE DEFINITIONS
# ============================================================

def build_enemy_queue(level):
    """
    Return the ordered list of 20 enemy tank types for this level.
    Based exactly on the spec Level table.
    """
    if level == 1:
        # Level 1 — Brick Maze: 7 Basic + 5 Fast = 12 (spec says 20 total,
        # remainder are basic to pad to 20 for a complete level)
        return (
            ['basic'] * 7 +
            ['fast']  * 5 +
            ['basic'] * 8   # Pad to 20
        )
    elif level == 2:
        # Level 2 — Steel Fortress: 4 Fast + 3 Armor + 2 Power(treat as Fast) + ...
        return (
            ['fast']  * 4 +
            ['armor'] * 3 +
            ['fast']  * 2 +   # Power tanks → Fast placeholder (Utility-based is Module C+)
            ['armor'] * 2 +
            ['basic'] * 9
        )
    return ['basic'] * 20


# ============================================================
#  GAME CLASS
# ============================================================

class BattleCityGame:
    """
    Main game class.
    Call game.run() to start the pygame loop.
    """

    def __init__(self, level=1):
        pygame.init()

        self.level      = level
        self.grid_size  = LEVEL_CONFIG[level].get('arena_size', GRID_SIZE)
        self.cell       = TILE_SIZE

        win_w = self.grid_size * self.cell + PANEL_W
        win_h = self.grid_size * self.cell
        self.screen = pygame.display.set_mode((win_w, win_h))
        pygame.display.set_caption(
            f"Battle City AI — Level {level}: {LEVEL_CONFIG[level]['name']}"
        )

        self.font_sm = pygame.font.SysFont('monospace', 11)
        self.font_md = pygame.font.SysFont('monospace', 13, bold=True)
        self.font_lg = pygame.font.SysFont('monospace', 16, bold=True)
        self.clock   = pygame.time.Clock()
        self.FPS     = 30

        self._init_level(level)

    # ----------------------------------------------------------
    #  INITIALISE / RESET LEVEL
    # ----------------------------------------------------------

    def _init_level(self, level):
        """Generate map, spawn player, set up enemy queue."""
        self.level = level

        # Generate map via Module A (CSP)
        gen        = CSPMapGenerator(level=level)
        self.grid  = gen.generate()

        # Player
        px, py     = PLAYER_START
        self.player = PlayerTank(px, py)

        # Enemy pool (20 tanks per level)
        self.enemy_queue   = build_enemy_queue(level)
        self.enemies_left  = len(self.enemy_queue)
        self.active_enemies= []   # Currently on map (max 4)
        self.spawn_timer   = 60   # Ticks before first spawn
        self.spawn_index   = 0    # Rotation through 3 spawn points

        # Bullets (all active bullets in the game)
        self.all_bullets   = []

        # Game state
        self.game_over     = False
        self.victory       = False
        self.game_over_timer = 0   # Delay before showing game over screen
        self.tick          = 0

    # ----------------------------------------------------------
    #  MAIN RUN LOOP
    # ----------------------------------------------------------

    def run(self):
        """Start the game loop."""
        running = True
        while running:
            # ── Event pump ────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_r and self.game_over:
                        self._init_level(self.level)   # Restart

            if not self.game_over:
                self._game_tick()

            # ── Step 9: RENDER ────────────────────────────────
            self._render()
            self.clock.tick(self.FPS)
            self.tick += 1

        pygame.quit()
        sys.exit()

    # ----------------------------------------------------------
    #  GAME TICK — all 10 steps
    # ----------------------------------------------------------

    def _game_tick(self):

        # ── Step 1: INPUT ──────────────────────────────────────
        keys       = pygame.key.get_pressed()
        move_dir   = None
        want_shoot = False

        for key, direction in KEY_TO_DIR.items():
            if keys[key]:
                move_dir = direction
                break
        if keys[pygame.K_SPACE]:
            want_shoot = True

        # Tick all timers
        self.player.tick_timers()
        for e in self.active_enemies:
            e.tick_timers()

        # ── Step 2: AGENT DECISIONS ────────────────────────────
        enemy_actions = {}
        for enemy in self.active_enemies:
            if enemy.alive:
                action = enemy.decide(self.grid, self.player, self.active_enemies)
                enemy_actions[id(enemy)] = action

        # ── Step 3: MOVE ───────────────────────────────────────
        # Player move
        if move_dir and self.player.move_ready():
            all_tanks = [self.player] + self.active_enemies
            self.player.try_move(move_dir, self.grid, all_tanks)
            self.player.direction  = move_dir
            self.player.move_timer = self.player.speed

        # Enemy moves
        all_tanks = [self.player] + self.active_enemies
        for enemy in self.active_enemies:
            if not enemy.alive:
                continue
            action = enemy_actions.get(id(enemy), {})
            if action.get('move') and enemy.move_ready():
                enemy.try_move(action['move'], self.grid, all_tanks)

        # ── Step 4: SHOOT ──────────────────────────────────────
        # Player shoot
        if want_shoot and self.player.can_shoot():
            bullet = self.player.shoot(owner='player')
            if bullet:
                self.all_bullets.append(bullet)

        # Enemy shoot
        for enemy in self.active_enemies:
            if not enemy.alive:
                continue
            action = enemy_actions.get(id(enemy), {})
            if action.get('shoot') and enemy.can_shoot():
                bullet = enemy.shoot(owner='enemy')
                if bullet:
                    self.all_bullets.append(bullet)

        # ── Step 5: BULLET UPDATE ──────────────────────────────
        for bullet in self.all_bullets:
            if bullet.alive:
                bullet.update(self.grid)

        # ── Step 6: COLLISION DETECTION ────────────────────────
        self._handle_bullet_collisions()

        # ── Step 7: STATE UPDATE ───────────────────────────────
        # Remove dead bullets
        self.all_bullets = [b for b in self.all_bullets if b.alive]
        # Remove dead enemies
        self.active_enemies = [e for e in self.active_enemies if e.alive]

        # ── Step 8: SPAWN CHECK ────────────────────────────────
        self._spawn_check()

        # ── Step 10: WIN / LOSE CHECK ──────────────────────────
        self._check_win_lose()

    # ----------------------------------------------------------
    #  COLLISION HANDLING
    # ----------------------------------------------------------

    def _handle_bullet_collisions(self):
        """
        Handle all bullet collisions in one pass:
          - Bullet vs Eagle   → game over
          - Bullet vs Player  → player takes hit
          - Bullet vs Enemy   → enemy takes hit
          - Bullet vs Bullet  → both destroyed
        """
        bullets = [b for b in self.all_bullets if b.alive]

        for i, b in enumerate(bullets):
            if not b.alive:
                continue

            # Bullet reached Eagle tile (via update returning 'hit_eagle')
            # Check position directly as update() already handled terrain
            if self.grid[b.y][b.x] == EAGLE:
                b.alive = False
                self._trigger_game_over(victory=False, reason='Eagle destroyed!')
                return

            # Bullet vs Player
            if b.owner == 'enemy' and b.alive:
                if b.check_tank_hit(self.player):
                    b.alive = False
                    self.player.take_hit()
                    if not self.player.alive:
                        # Use a life if available
                        if self.player.lives > 0:
                            px, py = PLAYER_START
                            self.player.respawn(px, py)
                        else:
                            self._trigger_game_over(victory=False, reason='Player destroyed!')
                            return

            # Bullet vs Enemies
            if b.owner == 'player' and b.alive:
                for enemy in self.active_enemies:
                    if enemy.alive and b.check_tank_hit(enemy):
                        b.alive = False
                        enemy.take_hit()
                        if not enemy.alive:
                            self.player.score += self._score_for(enemy)
                        break

            # Bullet vs Bullet — both destroyed
            for j, other in enumerate(bullets):
                if i != j and other.alive and b.alive:
                    if b.check_bullet_collision(other):
                        b.alive = False
                        other.alive = False

    def _score_for(self, enemy):
        """Points awarded for destroying each tank type."""
        scores = {BasicTank: 100, FastTank: 200, ArmorTank: 400}
        return scores.get(type(enemy), 100)

    # ----------------------------------------------------------
    #  SPAWN SYSTEM
    # ----------------------------------------------------------

    def _spawn_check(self):
        """
        Spawn next enemy from pool if:
          - Fewer than 4 active enemies on map
          - Enemies still remain in the queue
          - Spawn timer has expired
          - Spawn point is at least 10 tiles from player (Constraint 3)
        """
        if self.spawn_timer > 0:
            self.spawn_timer -= 1
            return

        if not self.enemy_queue:
            return

        if len(self.active_enemies) >= 4:
            return

        # Rotate through spawn points
        for _ in range(3):  # Try all 3 spawn points
            sx, sy = ENEMY_SPAWNS[self.spawn_index % 3]
            self.spawn_index += 1

            # Fairness constraint: spawn ≥ 10 tiles from player
            if manhattan((sx, sy), (self.player.x, self.player.y)) < 10:
                continue

            # Spawn the next tank from queue
            tank_type = self.enemy_queue.pop(0)
            enemy     = spawn_tank(tank_type, sx, sy)
            self.active_enemies.append(enemy)
            self.enemies_left -= 1
            self.spawn_timer   = 45  # Short delay before next spawn
            return

        # All spawn points too close to player — wait longer
        self.spawn_timer = 30

    # ----------------------------------------------------------
    #  WIN / LOSE
    # ----------------------------------------------------------

    def _trigger_game_over(self, victory=False, reason=''):
        """Set game over state."""
        self.game_over  = True
        self.victory    = victory
        self.game_over_reason = reason
        print(f"[GAME] {'VICTORY' if victory else 'GAME OVER'}: {reason}")

    def _check_win_lose(self):
        """
        Win:  All 20 enemies destroyed AND none active on map.
        Lose: Player HP = 0 and no lives left, OR Eagle hit.
        """
        if self.game_over:
            return

        # Win condition
        if not self.enemy_queue and not self.active_enemies:
            self._trigger_game_over(victory=True, reason='All enemies destroyed!')

        # Player dead with no lives
        if not self.player.alive and self.player.lives <= 0:
            self._trigger_game_over(victory=False, reason='No lives remaining!')

    # ----------------------------------------------------------
    #  RENDER  (Step 9)
    # ----------------------------------------------------------

    def _render(self):
        """Draw everything: map, tanks, bullets, UI panel."""
        self.screen.fill(COLOR['bg'])
        self._draw_tiles()
        self._draw_bullets()
        self._draw_tanks()
        self._draw_panel()
        if self.game_over:
            self._draw_game_over()
        pygame.display.flip()

    def _draw_tiles(self):
        """Draw the 26x26 grid with terrain colors and textures."""
        cell = self.cell
        for r, row in enumerate(self.grid):
            for c, tile in enumerate(row):
                color = TILE_COLOR.get(tile, (80, 0, 80))
                rect  = pygame.Rect(c * cell, r * cell, cell, cell)
                pygame.draw.rect(self.screen, color, rect)

                # Grid line
                pygame.draw.rect(self.screen, COLOR['grid_line'], rect, 1)

                # Brick texture
                if tile == BRICK:
                    dark = (140, 60, 25)
                    pygame.draw.line(self.screen, dark,
                                     (c*cell, r*cell + cell//2),
                                     (c*cell + cell, r*cell + cell//2), 1)
                    pygame.draw.line(self.screen, dark,
                                     (c*cell + cell//2, r*cell),
                                     (c*cell + cell//2, r*cell + cell//2), 1)

                # Steel texture
                elif tile == STEEL:
                    light = (170, 185, 200)
                    pygame.draw.line(self.screen, light,
                                     (c*cell+2, r*cell+2),
                                     (c*cell+cell-2, r*cell+cell-2), 1)
                    pygame.draw.line(self.screen, light,
                                     (c*cell+cell-2, r*cell+2),
                                     (c*cell+2, r*cell+cell-2), 1)

                # Eagle symbol
                if tile == EAGLE:
                    lbl = self.font_sm.render('E', True, (30, 30, 30))
                    self.screen.blit(lbl, (c*cell + cell//2 - 4, r*cell + cell//2 - 5))

    def _draw_bullets(self):
        """Draw all active bullets as small bright squares."""
        cell = self.cell
        for b in self.all_bullets:
            if b.alive:
                color = (255, 255, 100) if b.owner == 'player' else (255, 80, 80)
                cx = b.x * cell + cell // 2
                cy = b.y * cell + cell // 2
                pygame.draw.rect(self.screen, color,
                                 (cx - 3, cy - 3, 6, 6))

    def _draw_tanks(self):
        """Draw player and enemy tanks with direction indicator."""
        cell = self.cell

        # Draw player
        if self.player.alive:
            self._draw_tank_sprite(self.player, (80, 220, 100))

        # Draw enemies
        type_colors = {
            BasicTank: (220, 80,  80),
            FastTank:  (220, 180, 60),
            ArmorTank: (80,  120, 220),
        }
        for e in self.active_enemies:
            if e.alive:
                color = type_colors.get(type(e), (200, 200, 200))
                # Armor tank: show damage stages with color shift
                if isinstance(e, ArmorTank):
                    stage = e.hit_count
                    damage_colors = [
                        (80, 120, 220),  # 0 hits - blue
                        (80, 180, 200),  # 1 hit  - cyan
                        (80, 200, 140),  # 2 hits - teal
                        (220, 160, 60),  # 3 hits - amber (retreating!)
                    ]
                    color = damage_colors[min(stage, 3)]
                self._draw_tank_sprite(e, color)

    def _draw_tank_sprite(self, tank, color):
        """Draw a tank as a colored square with direction arrow."""
        cell = self.cell
        x    = tank.x * cell + 2
        y    = tank.y * cell + 2
        w    = cell - 4

        pygame.draw.rect(self.screen, color, (x, y, w, w))
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, w, w), 1)

        # Direction indicator (small triangle)
        cx = tank.x * cell + cell // 2
        cy = tank.y * cell + cell // 2
        dx, dy = tank.direction
        pts = [
            (cx + dx * 7, cy + dy * 7),          # Tip
            (cx - dy * 4, cy + dx * 4),           # Left base
            (cx + dy * 4, cy - dx * 4),           # Right base
        ]
        pygame.draw.polygon(self.screen, (255, 255, 255), pts)

    def _draw_panel(self):
        """Draw right-side UI panel."""
        gw  = self.grid_size * self.cell
        pw  = PANEL_W
        ph  = self.grid_size * self.cell
        pygame.draw.rect(self.screen, COLOR['panel'], (gw, 0, pw, ph))
        pygame.draw.line(self.screen, (80, 80, 80), (gw, 0), (gw, ph), 1)

        y = 12
        def txt(msg, color=COLOR['text'], f=None):
            nonlocal y
            s = (f or self.font_sm).render(msg, True, color)
            self.screen.blit(s, (gw + 8, y))
            y += s.get_height() + 3

        def div():
            nonlocal y
            pygame.draw.line(self.screen, (70, 70, 70),
                             (gw + 6, y), (gw + pw - 6, y), 1)
            y += 6

        txt('MODULE B', COLOR['highlight'], self.font_md)
        txt(f"Level {self.level}: {LEVEL_CONFIG[self.level]['name']}", COLOR['text_dim'])
        div()

        txt('PLAYER', COLOR['highlight'], self.font_md)
        txt(f"Score:  {self.player.score}")
        txt(f"Lives:  {self.player.lives}")
        txt(f"HP:     {self.player.hp}")
        div()

        txt('ENEMIES', COLOR['highlight'], self.font_md)
        txt(f"In queue: {len(self.enemy_queue)}")
        txt(f"Active:   {len(self.active_enemies)}")
        active_types = {}
        for e in self.active_enemies:
            n = type(e).__name__.replace('Tank', '')
            active_types[n] = active_types.get(n, 0) + 1
        for name, cnt in active_types.items():
            txt(f"  {name}: {cnt}")
        div()

        txt('AI LEGEND', COLOR['highlight'], self.font_md)
        legend = [
            ((220, 80, 80),  'Basic  — BFS'),
            ((220, 180, 60), 'Fast   — Greedy'),
            ((80, 120, 220), 'Armor  — A*'),
            ((80, 220, 100), 'Player — You'),
        ]
        for color, label in legend:
            pygame.draw.rect(self.screen, color, (gw + 8, y, 10, 10))
            pygame.draw.rect(self.screen, (100, 100, 100), (gw + 8, y, 10, 10), 1)
            s = self.font_sm.render('  ' + label, True, COLOR['text'])
            self.screen.blit(s, (gw + 20, y - 1))
            y += 13
        div()

        txt('CONTROLS', COLOR['highlight'], self.font_md)
        txt('WASD/Arrows - Move', COLOR['text_dim'])
        txt('SPACE       - Shoot', COLOR['text_dim'])
        txt('R (gameover)- Restart', COLOR['text_dim'])
        txt('ESC         - Quit', COLOR['text_dim'])

    def _draw_game_over(self):
        """Draw game over / victory overlay."""
        overlay = pygame.Surface(
            (self.grid_size * self.cell, self.grid_size * self.cell),
            pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        cx = self.grid_size * self.cell // 2
        cy = self.grid_size * self.cell // 2

        if self.victory:
            msg   = 'VICTORY!'
            color = (100, 255, 100)
        else:
            msg   = 'GAME OVER'
            color = (255, 80, 80)

        s1 = self.font_lg.render(msg, True, color)
        self.screen.blit(s1, (cx - s1.get_width()//2, cy - 30))

        reason = getattr(self, 'game_over_reason', '')
        s2 = self.font_sm.render(reason, True, (220, 220, 220))
        self.screen.blit(s2, (cx - s2.get_width()//2, cy))

        s3 = self.font_sm.render('Press R to restart or ESC to quit',
                                  True, COLOR['text_dim'])
        self.screen.blit(s3, (cx - s3.get_width()//2, cy + 24))

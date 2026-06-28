# ============================================================
#  boss_tank.py  —  MODULE C: Boss Tank (Tank Commander)
#  AL2002 Battle City AI Project
#
#  SYLLABUS MAPPING:
#    Tank       : Boss Tank (Tank Commander)
#    Agent      : Adversarial Agent
#    Algorithm  : Minimax + Alpha-Beta Pruning
#    Arena      : 12x12 tile closed arena
#
#  PHASE SYSTEM (from spec):
#  ┌─────────┬────────────┬───────┬────────────────────────────┐
#  │ Phase   │ HP         │ Depth │ Behaviour                  │
#  ├─────────┼────────────┼───────┼────────────────────────────┤
#  │ Phase 1 │ 10 – 7 HP  │   2   │ Aggressive push to player  │
#  │ Phase 2 │  6 – 3 HP  │   3   │ Balanced attack + cover    │
#  │ Phase 3 │  2 – 1 HP  │   4   │ Desperate maximum aggression│
#  └─────────┴────────────┴───────┴────────────────────────────┘
# ============================================================

from constants import EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE
from minimax import MinimaxEngine, GameState, DIR_MAP
from bullet import Bullet

# Direction constants
UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)


class BossTank:
    """
    The Tank Commander — uses Minimax + Alpha-Beta Pruning.

    Properties (from spec):
      HP        : 10 hits (3 phases)
      Speed     : Variable by phase
      Fire rate : Variable by phase
      Agent     : Adversarial (Minimax)
      Arena     : 12x12 tile closed arena
    """

    # Phase definitions (from spec)
    PHASES = {
        1: {'min_hp': 7,  'depth': 2, 'speed': 5,  'fire_rate': 60,  'label': 'AGGRESSIVE'},
        2: {'min_hp': 3,  'depth': 3, 'speed': 4,  'fire_rate': 45,  'label': 'BALANCED'},
        3: {'min_hp': 0,  'depth': 4, 'speed': 3,  'fire_rate': 25,  'label': 'DESPERATE'},
    }

    def __init__(self, x, y, arena_size=12):
        self.x          = x
        self.y          = y
        self.hp         = 10
        self.max_hp     = 10
        self.alive      = True
        self.direction  = DOWN
        self.arena_size = arena_size

        # Timers
        self.move_timer = 0
        self.fire_timer = 0
        self.bullet     = None

        # Phase tracking
        self.current_phase = 1
        self._update_phase()

        # Minimax engine
        self.engine = MinimaxEngine()

        # Decision every N ticks (not every tick — too expensive)
        self.decide_interval = 6   # Re-run Minimax every 6 ticks
        self.decide_timer    = 0
        self.current_action  = 'SHOOT'

        # Stats for report
        self.all_stats       = []
        self.total_nodes_mm  = 0
        self.total_nodes_ab  = 0

    # ----------------------------------------------------------
    #  PHASE MANAGEMENT
    # ----------------------------------------------------------

    def _update_phase(self):
        """Determine current phase from HP and update speed/fire_rate."""
        if self.hp >= 7:
            self.current_phase = 1
        elif self.hp >= 3:
            self.current_phase = 2
        else:
            self.current_phase = 3

        phase_cfg        = self.PHASES[self.current_phase]
        self.speed       = phase_cfg['speed']
        self.fire_rate   = phase_cfg['fire_rate']
        self.depth       = phase_cfg['depth']

    def get_phase_label(self):
        return self.PHASES[self.current_phase]['label']

    # ----------------------------------------------------------
    #  TAKE HIT
    # ----------------------------------------------------------

    def take_hit(self):
        """Reduce HP and update phase."""
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False
        else:
            old_phase = self.current_phase
            self._update_phase()
            if self.current_phase != old_phase:
                print(f"[BOSS] Phase {old_phase} → Phase {self.current_phase}! "
                      f"(HP={self.hp}, Depth now={self.depth})")

    # ----------------------------------------------------------
    #  TIMER UTILITIES
    # ----------------------------------------------------------

    def tick_timers(self):
        if self.move_timer  > 0: self.move_timer  -= 1
        if self.fire_timer  > 0: self.fire_timer  -= 1
        if self.decide_timer > 0: self.decide_timer -= 1

    def move_ready(self):
        return self.move_timer <= 0

    def can_shoot(self):
        return self.fire_timer <= 0 and (self.bullet is None or not self.bullet.alive)

    # ----------------------------------------------------------
    #  MAIN DECISION — MINIMAX
    # ----------------------------------------------------------

    def decide(self, grid, player):
        """
        Run Minimax to choose the best action.
        Re-runs every decide_interval ticks for performance.

        Returns action dict: {'move': direction_or_None, 'shoot': bool}
        """
        action_dict = {'move': None, 'shoot': False}

        # Only re-run Minimax every N ticks
        if self.decide_timer <= 0:
            state = GameState(
                boss_x   = self.x,
                boss_y   = self.y,
                boss_hp  = self.hp,
                boss_dir = self.direction,
                player_x = player.x,
                player_y = player.y,
                player_hp= player.hp,
                player_dir= player.direction,
                grid     = grid,
                arena_size= self.arena_size,
            )

            # Run Minimax with current phase depth
            best_action, stats = self.engine.get_best_action(state, self.depth)
            self.current_action = best_action
            self.decide_timer   = self.decide_interval

            # Record stats for report
            self.all_stats.append(stats)
            self.total_nodes_mm += stats['nodes_minimax']
            self.total_nodes_ab += stats['nodes_alphabeta']

        # Convert chosen action to move/shoot
        if self.current_action == 'SHOOT':
            action_dict['shoot'] = True
        elif self.current_action in DIR_MAP:
            dx, dy = DIR_MAP[self.current_action]
            action_dict['move'] = (dx, dy)
            self.direction = (dx, dy)

        return action_dict

    # ----------------------------------------------------------
    #  SHOOT
    # ----------------------------------------------------------

    def shoot(self):
        """Fire a bullet in current facing direction."""
        if not self.can_shoot():
            return None
        bx = self.x + self.direction[0]
        by = self.y + self.direction[1]
        if not (0 <= bx < self.arena_size and 0 <= by < self.arena_size):
            return None
        self.bullet     = Bullet(bx, by, self.direction, owner='boss')
        self.bullet.size = self.arena_size
        self.fire_timer = self.fire_rate
        return self.bullet

    # ----------------------------------------------------------
    #  MOVEMENT
    # ----------------------------------------------------------

    def try_move(self, direction, grid, player):
        """Move one tile if not blocked."""
        dx, dy = direction
        nx, ny = self.x + dx, self.y + dy
        self.direction = direction

        if not (0 <= nx < self.arena_size and 0 <= ny < self.arena_size):
            return False
        tile = grid[ny][nx]
        if tile in {BRICK, STEEL, WATER}:
            return False
        if nx == player.x and ny == player.y:
            return False

        self.x, self.y = nx, ny
        self.move_timer = self.speed
        return True

    # ----------------------------------------------------------
    #  REPORT STATS
    # ----------------------------------------------------------

    def get_report_stats(self):
        """
        Return node count data for the project report.
        Required by spec:
          (a) nodes WITHOUT Alpha-Beta
          (b) nodes WITH Alpha-Beta
          (c) speedup ratio
        """
        ab = max(self.total_nodes_ab, 1)
        return {
            'decisions_made'  : len(self.all_stats),
            'total_nodes_minimax'  : self.total_nodes_mm,
            'total_nodes_alphabeta': self.total_nodes_ab,
            'speedup_ratio'        : round(self.total_nodes_mm / ab, 2),
            'per_phase_breakdown'  : self.all_stats[-5:] if self.all_stats else [],
        }

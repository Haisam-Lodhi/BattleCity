# ============================================================
#  minimax.py  —  MODULE C: Adversarial Search
#  AL2002 Battle City AI Project
#
#  SYLLABUS MAPPING:
#    Module : Adversarial Search
#    Agent  : Adversarial Agent (Boss Tank)
#    Method : Minimax + Alpha-Beta Pruning
#
#  HOW MINIMAX WORKS (for viva):
#    - Two players: MAX (Boss) tries to MAXIMISE score
#                   MIN (Player) tries to MINIMISE boss score
#    - Boss simulates: "if I do X, player will do Y, then I do Z..."
#    - Tree depth = how many moves ahead the boss thinks
#    - Alpha-Beta PRUNES branches that cannot affect the result
#      → reduces search from O(b^d) to O(b^(d/2)) in best case
#
#  DEPTH BY PHASE (from spec):
#    Phase 1 (10-7 HP) → depth 2
#    Phase 2 (6-3 HP)  → depth 3
#    Phase 3 (2-1 HP)  → depth 4
#
#  REQUIRED IN REPORT:
#    (a) nodes evaluated WITHOUT Alpha-Beta pruning
#    (b) nodes evaluated WITH Alpha-Beta pruning
#    (c) speedup ratio = a / b
# ============================================================

from constants import EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE, GRID_SIZE

# All possible actions for any tank in the game
ACTIONS = ['UP', 'DOWN', 'LEFT', 'RIGHT', 'SHOOT']

# Direction vectors
DIR_MAP = {
    'UP'   : ( 0, -1),
    'DOWN' : ( 0,  1),
    'LEFT' : (-1,  0),
    'RIGHT': ( 1,  0),
}


# ============================================================
#  GAME STATE  (lightweight snapshot for minimax tree)
# ============================================================

class GameState:
    """
    Lightweight game state for Minimax simulation.
    Only stores what the boss needs to evaluate positions.
    Kept minimal so tree search stays fast.
    """

    def __init__(self, boss_x, boss_y, boss_hp, boss_dir,
                 player_x, player_y, player_hp, player_dir,
                 grid, arena_size=12):
        self.boss_x    = boss_x
        self.boss_y    = boss_y
        self.boss_hp   = boss_hp
        self.boss_dir  = boss_dir      # (dx, dy)

        self.player_x  = player_x
        self.player_y  = player_y
        self.player_hp = player_hp
        self.player_dir= player_dir

        # Grid stored as tuple of tuples (immutable / hashable)
        self.grid      = [row[:] for row in grid]
        self.size      = arena_size

        self.game_over = False
        self.winner    = None   # 'boss' or 'player'

    def clone(self):
        """Deep copy of the state for tree branching."""
        s = GameState(
            self.boss_x, self.boss_y, self.boss_hp, self.boss_dir,
            self.player_x, self.player_y, self.player_hp, self.player_dir,
            self.grid, self.size
        )
        s.game_over = self.game_over
        s.winner    = self.winner
        return s

    def _in_bounds(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size

    def _can_move(self, x, y):
        """Can a tank move to (x, y)?"""
        if not self._in_bounds(x, y):
            return False
        tile = self.grid[y][x]
        return tile in {EMPTY, FOREST, EAGLE}

    # ----------------------------------------------------------
    #  Apply boss action to state
    # ----------------------------------------------------------
    def apply_boss_action(self, action):
        """Apply boss action and return new state."""
        s = self.clone()

        if action == 'SHOOT':
            # Boss fires in its current direction
            bx = s.boss_x + s.boss_dir[0]
            by = s.boss_y + s.boss_dir[1]
            # Trace bullet path
            while s._in_bounds(bx, by):
                tile = s.grid[by][bx]
                if tile == BRICK:
                    s.grid[by][bx] = EMPTY
                    break
                elif tile in {STEEL, WATER}:
                    break
                elif bx == s.player_x and by == s.player_y:
                    s.player_hp -= 1
                    if s.player_hp <= 0:
                        s.game_over = True
                        s.winner = 'boss'
                    break
                elif tile == EAGLE:
                    s.game_over = True
                    s.winner = 'boss'
                    break
                bx += s.boss_dir[0]
                by += s.boss_dir[1]

        elif action in DIR_MAP:
            dx, dy = DIR_MAP[action]
            nx, ny = s.boss_x + dx, s.boss_y + dy
            s.boss_dir = (dx, dy)
            if s._can_move(nx, ny) and not (nx == s.player_x and ny == s.player_y):
                s.boss_x, s.boss_y = nx, ny

        return s

    # ----------------------------------------------------------
    #  Apply player action to state
    # ----------------------------------------------------------
    def apply_player_action(self, action):
        """Apply simulated player action and return new state."""
        s = self.clone()

        if action == 'SHOOT':
            bx = s.player_x + s.player_dir[0]
            by = s.player_y + s.player_dir[1]
            while s._in_bounds(bx, by):
                tile = s.grid[by][bx]
                if tile == BRICK:
                    s.grid[by][bx] = EMPTY
                    break
                elif tile in {STEEL, WATER}:
                    break
                elif bx == s.boss_x and by == s.boss_y:
                    s.boss_hp -= 1
                    if s.boss_hp <= 0:
                        s.game_over = True
                        s.winner = 'player'
                    break
                bx += s.player_dir[0]
                by += s.player_dir[1]

        elif action in DIR_MAP:
            dx, dy = DIR_MAP[action]
            nx, ny = s.player_x + dx, s.player_y + dy
            s.player_dir = (dx, dy)
            if s._can_move(nx, ny) and not (nx == s.boss_x and ny == s.boss_y):
                s.player_x, s.player_y = nx, ny

        return s


# ============================================================
#  EVALUATION HEURISTIC  (from spec — exact scores)
# ============================================================

def evaluate(state):
    """
    Evaluate a game state from the BOSS's perspective.
    Higher score = better for boss.

    Scores (exact from spec):
      Player within 3 tiles    : +60
      Player in line-of-sight  : +50
      Boss adjacent to steel   : +30
      Player HP missing (each) : +20
      Boss HP missing (each)   : -40
      Player in forest tile    : -20
    """
    score = 0

    # Distance to player
    dist = abs(state.boss_x - state.player_x) + abs(state.boss_y - state.player_y)
    if dist <= 3:
        score += 60

    # Line of sight check
    if _has_los(state):
        score += 50

    # Boss adjacent to steel wall (cover)
    for dx, dy in [(0,-1),(0,1),(-1,0),(1,0)]:
        nx, ny = state.boss_x + dx, state.boss_y + dy
        if (0 <= nx < state.size and 0 <= ny < state.size
                and state.grid[ny][nx] == STEEL):
            score += 30
            break  # Count once

    # Player HP missing (player is weakened)
    score += (1 - state.player_hp) * 20   # player starts with hp=1 in boss fight

    # Boss HP missing (boss is losing)
    score -= (10 - state.boss_hp) * 40

    # Player hiding in forest
    if (0 <= state.player_x < state.size and 0 <= state.player_y < state.size):
        if state.grid[state.player_y][state.player_x] == FOREST:
            score -= 20

    return score


def _has_los(state):
    """Check if boss has line-of-sight to player (same row or col, no wall between)."""
    bx, by = state.boss_x, state.boss_y
    px, py = state.player_x, state.player_y
    wall_tiles = {BRICK, STEEL, WATER}

    if bx == px:
        for y in range(min(by, py) + 1, max(by, py)):
            if state.grid[y][bx] in wall_tiles:
                return False
        return True

    if by == py:
        for x in range(min(bx, px) + 1, max(bx, px)):
            if state.grid[by][x] in wall_tiles:
                return False
        return True

    return False


# ============================================================
#  MINIMAX WITH ALPHA-BETA PRUNING
# ============================================================

class MinimaxEngine:
    """
    Minimax search engine with Alpha-Beta pruning.

    Usage:
        engine = MinimaxEngine()
        best_action, stats = engine.get_best_action(state, depth=3)

    stats contains node counts for the project report.
    """

    def __init__(self):
        self.reset_counters()

    def reset_counters(self):
        """Reset node count statistics."""
        self.nodes_minimax      = 0   # Nodes evaluated WITHOUT pruning
        self.nodes_alphabeta    = 0   # Nodes evaluated WITH pruning
        self.branches_pruned    = 0   # How many branches were cut

    # ----------------------------------------------------------
    #  MAIN ENTRY POINT
    # ----------------------------------------------------------

    def get_best_action(self, state, depth):
        """
        Find the best action for the Boss (MAX player).

        Parameters:
            state : GameState — current game state
            depth : int — how many moves ahead to search

        Returns:
            best_action : str — one of ACTIONS
            stats       : dict — node counts for report
        """
        self.reset_counters()

        best_action = 'SHOOT'  # Default fallback
        best_value  = float('-inf')

        # Try each possible boss action
        for action in ACTIONS:
            child_state = state.apply_boss_action(action)
            self.nodes_alphabeta += 1

            # MIN player's turn (simulated player response)
            value = self._min_value(
                child_state,
                depth - 1,
                alpha=float('-inf'),
                beta=float('inf')
            )

            if value > best_value:
                best_value  = value
                best_action = action

        # Also compute nodes WITHOUT pruning (for report)
        self.nodes_minimax = self._count_nodes_no_pruning(state, depth)

        stats = {
            'depth'          : depth,
            'nodes_minimax'  : self.nodes_minimax,
            'nodes_alphabeta': self.nodes_alphabeta,
            'branches_pruned': self.branches_pruned,
            'speedup_ratio'  : round(
                self.nodes_minimax / max(self.nodes_alphabeta, 1), 2
            ),
        }

        return best_action, stats

    # ----------------------------------------------------------
    #  MAX NODE (Boss's turn)
    # ----------------------------------------------------------

    def _max_value(self, state, depth, alpha, beta):
        """
        MAX node: Boss tries to MAXIMISE the evaluation score.
        Alpha: best score MAX (boss) can guarantee so far.
        Beta:  best score MIN (player) can guarantee so far.
        Prune: if value >= beta, stop (MIN would never allow this).
        """
        self.nodes_alphabeta += 1

        # Terminal conditions
        if depth == 0 or state.game_over:
            return evaluate(state)

        value = float('-inf')

        for action in ACTIONS:
            child = state.apply_boss_action(action)
            value = max(value, self._min_value(child, depth - 1, alpha, beta))

            # Alpha-Beta pruning — PRUNE if value >= beta
            if value >= beta:
                self.branches_pruned += 1
                return value   # Beta cut-off

            alpha = max(alpha, value)

        return value

    # ----------------------------------------------------------
    #  MIN NODE (Simulated player's turn)
    # ----------------------------------------------------------

    def _min_value(self, state, depth, alpha, beta):
        """
        MIN node: Player tries to MINIMISE the boss's score.
        Prune: if value <= alpha, stop (MAX would never allow this).
        """
        self.nodes_alphabeta += 1

        # Terminal conditions
        if depth == 0 or state.game_over:
            return evaluate(state)

        value = float('inf')

        for action in ACTIONS:
            child = state.apply_player_action(action)
            value = min(value, self._max_value(child, depth - 1, alpha, beta))

            # Alpha-Beta pruning — PRUNE if value <= alpha
            if value <= alpha:
                self.branches_pruned += 1
                return value   # Alpha cut-off

            beta = min(beta, value)

        return value

    # ----------------------------------------------------------
    #  NODE COUNT WITHOUT PRUNING  (for report comparison)
    # ----------------------------------------------------------

    def _count_nodes_no_pruning(self, state, depth):
        """
        Count how many nodes a pure Minimax (no Alpha-Beta)
        would visit. Used to demonstrate pruning speedup.
        Formula: b^0 + b^1 + ... + b^d  where b = branching factor.
        With b=5 actions and depth d: sum = (5^(d+1) - 1) / 4
        """
        b = len(ACTIONS)  # branching factor = 5
        total = 0
        for i in range(depth + 1):
            total += b ** i
        return total

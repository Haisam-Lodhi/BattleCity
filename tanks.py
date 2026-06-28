# ============================================================
#  tanks.py  —  MODULE B: Tank AI Agents
#  AL2002 Battle City AI Project
#
#  SYLLABUS MAPPING (from spec):
#  ┌─────────────┬─────────────────────┬──────────────────┐
#  │ Tank        │ Agent Model         │ Search Algorithm │
#  ├─────────────┼─────────────────────┼──────────────────┤
#  │ Basic       │ Simple Reflex       │ BFS              │
#  │ Fast        │ Goal-Based          │ Greedy Best-First│
#  │ Armor       │ Model-Based Reflex  │ A*               │
#  │ Player      │ Human-controlled    │ None             │
#  └─────────────┴─────────────────────┴──────────────────┘
# ============================================================

import random
from constants import (
    EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE,
    EAGLE_POS, GRID_SIZE
)
from search import (
    bfs, greedy_step, astar,
    has_line_of_sight, direction_to, nearest_steel, manhattan
)
from bullet import Bullet

# Direction vectors
UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)
ALL_DIRS = [UP, DOWN, LEFT, RIGHT]


def _in_bounds(x, y, size=GRID_SIZE):
    return 0 <= x < size and 0 <= y < size


# ============================================================
#  BASE TANK CLASS
# ============================================================

class Tank:
    """
    Base class for all tanks (player and enemy).
    Holds position, HP, direction, shooting cooldown.
    """

    def __init__(self, x, y, hp=1, speed=4, fire_rate=180):
        self.x         = x
        self.y         = y
        self.hp        = hp
        self.max_hp    = hp
        self.direction = DOWN        # Which way the tank faces
        self.alive     = True

        # Speed: move every N ticks  (lower = faster)
        self.speed         = speed
        self.move_timer    = 0       # Ticks since last move

        # Fire rate: shoot every N ticks
        self.fire_rate     = fire_rate
        self.fire_timer    = 0       # Ticks since last shot
        self.bullet        = None    # Only 1 bullet at a time

        self.size = GRID_SIZE

    # ----------------------------------------------------------
    #  MOVEMENT
    # ----------------------------------------------------------

    def try_move(self, direction, grid, all_tanks):
        """
        Attempt to move one tile in the given direction.
        Returns True if move succeeded, False if blocked.
        Blocked by: Brick, Steel, Water, another tank, out of bounds.
        """
        self.direction = direction
        dx, dy = direction
        nx, ny = self.x + dx, self.y + dy

        if not _in_bounds(nx, ny, self.size):
            return False

        tile = grid[ny][nx]
        if tile in {BRICK, STEEL, WATER}:
            return False

        # Check collision with other tanks
        for tank in all_tanks:
            if tank is not self and tank.alive and tank.x == nx and tank.y == ny:
                return False

        self.x, self.y = nx, ny
        return True

    # ----------------------------------------------------------
    #  SHOOTING
    # ----------------------------------------------------------

    def can_shoot(self):
        """True if fire_timer has expired and no bullet is active."""
        return self.fire_timer <= 0 and (self.bullet is None or not self.bullet.alive)

    def shoot(self, owner='enemy'):
        """
        Fire a bullet in the current facing direction.
        Bullet starts one tile ahead of the tank.
        """
        if not self.can_shoot():
            return None
        bx = self.x + self.direction[0]
        by = self.y + self.direction[1]
        if not _in_bounds(bx, by, self.size):
            return None
        self.bullet     = Bullet(bx, by, self.direction, owner=owner)
        self.fire_timer = self.fire_rate
        return self.bullet

    # ----------------------------------------------------------
    #  TAKE DAMAGE
    # ----------------------------------------------------------

    def take_hit(self):
        """Reduce HP by 1. Mark dead if HP reaches 0."""
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False

    # ----------------------------------------------------------
    #  TICK TIMERS
    # ----------------------------------------------------------

    def tick_timers(self):
        """Decrement timers each game tick."""
        if self.move_timer  > 0: self.move_timer  -= 1
        if self.fire_timer  > 0: self.fire_timer  -= 1

    def move_ready(self):
        """True when movement cooldown has expired."""
        return self.move_timer <= 0


# ============================================================
#  PLAYER TANK
# ============================================================

class PlayerTank(Tank):
    """
    Human-controlled tank.
    Moves on keyboard input; shoots on SPACE.
    """

    def __init__(self, x, y):
        super().__init__(x, y, hp=1, speed=3, fire_rate=20)
        self.direction = UP
        self.lives     = 3       # Extra lives
        self.score     = 0

    def respawn(self, x, y):
        """Reset position and HP after death (uses one life)."""
        if self.lives > 0:
            self.lives -= 1
            self.x     = x
            self.y     = y
            self.hp    = 1
            self.alive = True
            self.bullet = None
            self.fire_timer = 0


# ============================================================
#  TANK TYPE 1 — BASIC TANK
#  Agent Model : Simple Reflex
#  Search      : BFS
# ============================================================

class BasicTank(Tank):
    """
    SIMPLE REFLEX AGENT — reacts to percepts only, no memory.

    Rules (from spec):
      PRIMARY : IF player in same row/column AND clear line-of-sight
                THEN face player and shoot
      MOVEMENT: Follow BFS path toward Eagle.
                Re-plan: at spawn, every 5s, when path blocked.
      WALL    : IF next tile is Brick THEN shoot to clear it.
    """

    def __init__(self, x, y):
        super().__init__(x, y, hp=1, speed=4, fire_rate=90)  # 1 bullet/~3s at 30fps
        self.direction = DOWN

        # BFS state
        self.path          = []    # Current planned path
        self.replan_timer  = 150   # Ticks between forced re-plans (5s @ 30fps)

    # ----------------------------------------------------------
    def decide(self, grid, player, all_tanks):
        """
        Run ONE decision cycle. Returns action dict:
          { 'move': direction_or_None, 'shoot': True/False }
        This is called EVERY tick from the game loop.
        """
        action = {'move': None, 'shoot': False}

        # ── PERCEPT: check if player is in line of sight ──────
        player_visible = (
            player.alive and
            has_line_of_sight(grid, (self.x, self.y), (player.x, player.y))
        )

        # ── RULE 1 (Primary): Shoot player if visible ─────────
        if player_visible:
            shoot_dir = direction_to((self.x, self.y), (player.x, player.y))
            self.direction = shoot_dir
            action['shoot'] = True

        # ── BFS RE-PLANNING ───────────────────────────────────
        self.replan_timer -= 1
        needs_replan = (
            self.replan_timer <= 0 or
            not self.path or
            not self._path_still_valid(grid)
        )
        if needs_replan:
            self.path         = bfs(grid, (self.x, self.y), EAGLE_POS, self.size)
            self.replan_timer = 150  # Reset 5-second timer

        # ── RULE 2 (Movement): Follow BFS path to Eagle ───────
        if self.move_ready() and self.path and len(self.path) > 1:
            next_tile = self.path[1]  # path[0] is current position
            nx, ny    = next_tile
            tile      = grid[ny][nx]
            move_dir  = direction_to((self.x, self.y), next_tile)
            self.direction = move_dir

            # ── RULE 3 (Wall): Shoot brick blocking the path ──
            if tile == BRICK:
                action['shoot'] = True  # Shoot to clear it
            else:
                action['move'] = move_dir
                self.path.pop(0)  # Advance along path
                self.move_timer = self.speed

        # ── FALLBACK: Random direction if totally stuck ────────
        elif self.move_ready() and not self.path:
            free_dirs = [
                d for d in ALL_DIRS
                if _in_bounds(self.x + d[0], self.y + d[1], self.size)
                and grid[self.y + d[1]][self.x + d[0]] in {EMPTY, FOREST}
            ]
            if free_dirs:
                action['move'] = random.choice(free_dirs)
                self.move_timer = self.speed

        return action

    def _path_still_valid(self, grid):
        """Check if the next step on the current path is still passable."""
        if len(self.path) < 2:
            return False
        nx, ny = self.path[1]
        return grid[ny][nx] in {EMPTY, FOREST, EAGLE, BRICK}


# ============================================================
#  TANK TYPE 2 — FAST TANK
#  Agent Model : Goal-Based
#  Search      : Greedy Best-First
# ============================================================

class FastTank(Tank):
    """
    GOAL-BASED AGENT — has one explicit goal: destroy the Eagle.
    Completely ignores the player. Rushes in a straight line.

    Rules (from spec):
      GOAL    : Destroy the Eagle. All actions serve this goal.
      MOVEMENT: Greedy step toward Eagle (min Manhattan distance).
                Re-computed every tick — no caching.
      WALL    : IF next tile is Brick THEN shoot straight through.
                NEVER detours — pushes forward regardless.
    """

    def __init__(self, x, y):
        super().__init__(x, y, hp=1, speed=2, fire_rate=45)  # Twice as fast
        self.direction = DOWN

    # ----------------------------------------------------------
    def decide(self, grid, player, all_tanks):
        """
        Goal-Based decision: always move/shoot toward Eagle.
        Player is completely ignored.
        """
        action = {'move': None, 'shoot': False}

        if not self.move_ready():
            return action

        # ── Greedy step: pick neighbour closest to Eagle ──────
        next_pos = greedy_step(grid, (self.x, self.y), EAGLE_POS, self.size)

        if next_pos:
            nx, ny   = next_pos
            tile     = grid[ny][nx]
            move_dir = direction_to((self.x, self.y), next_pos)
            self.direction = move_dir

            # ── WALL RULE: Shoot brick, never detour ──────────
            if tile == BRICK:
                action['shoot'] = True
                # Stay in place this tick — wait for brick to clear
            else:
                action['move'] = move_dir
                self.move_timer = self.speed
        else:
            # Completely stuck in local minima — shoot forward
            action['shoot'] = True

        return action


# ============================================================
#  TANK TYPE 3 — ARMOR TANK
#  Agent Model : Model-Based Reflex
#  Search      : A*
# ============================================================

class ArmorTank(Tank):
    """
    MODEL-BASED REFLEX AGENT — maintains internal state (hitCount).
    Behavior changes based on how many times it has been hit.

    State variable:
        hitCount (0–3): tracks damage received. Persists across ticks.

    Rules (from spec):
      Rule 1 (0–2 hits): Navigate to Eagle via A*.
                          Shoot player if in line-of-sight.
      Rule 2 (3rd hit) : RETREAT — find nearest steel wall via BFS.
      Rule 3 (retreat) : Wait 2 seconds behind cover, then resume A*.

    A* tile costs: empty=1, forest=1, brick=3, steel=∞, water=∞
    A* discovers: shoot through thin brick (cost 3) < long detour (cost 6+)
    """

    def __init__(self, x, y):
        super().__init__(x, y, hp=4, speed=3, fire_rate=60)
        self.direction = DOWN
        self.hit_count = 0      # Model state variable (persists!)

        # A* state
        self.path     = []
        self.retreating   = False
        self.retreat_pos  = None
        self.retreat_timer = 0   # Wait 2s behind cover before resuming

    # ----------------------------------------------------------
    def take_hit(self):
        """Override: track hitCount and trigger retreat at 3rd hit."""
        self.hit_count += 1
        super().take_hit()

        # ── RULE 2: Trigger retreat on 3rd hit ────────────────
        if self.hit_count == 3 and self.alive:
            self.retreating    = True
            self.path          = []   # Abandon current A* path
            self.retreat_timer = 60   # 2 seconds @ 30fps

    # ----------------------------------------------------------
    def decide(self, grid, player, all_tanks):
        """
        Model-Based decision: behaviour depends on hitCount state.
        """
        action = {'move': None, 'shoot': False}

        # ── RULE 2: Retreating to steel cover ─────────────────
        if self.retreating:
            return self._retreat_decision(grid, action)

        # ── RULE 1: Normal attack mode (0–2 hits) ─────────────

        # Check line-of-sight to player → shoot if visible
        if (player.alive and
                has_line_of_sight(grid, (self.x, self.y), (player.x, player.y))):
            shoot_dir = direction_to((self.x, self.y), (player.x, player.y))
            self.direction  = shoot_dir
            action['shoot'] = True

        # A* navigation to Eagle
        if not self.path or not self._path_valid(grid):
            self.path = astar(grid, (self.x, self.y), EAGLE_POS, self.size)

        if self.move_ready() and self.path and len(self.path) > 1:
            next_tile = self.path[1]
            nx, ny    = next_tile
            tile      = grid[ny][nx]
            move_dir  = direction_to((self.x, self.y), next_tile)
            self.direction = move_dir

            if tile == BRICK:
                # A* assigned cost 3 to brick — shoot to clear it
                action['shoot'] = True
            else:
                action['move'] = move_dir
                self.path.pop(0)
                self.move_timer = self.speed

        return action

    # ----------------------------------------------------------
    def _retreat_decision(self, grid, action):
        """
        RULE 2 + 3: Retreat to nearest steel tile, then wait.
        """
        if self.retreat_timer > 0:
            # Already at cover — count down wait timer
            self.retreat_timer -= 1
            if self.retreat_timer <= 0:
                # ── RULE 3: Resume attack after waiting ───────
                self.retreating = False
                self.path = astar(grid, (self.x, self.y), EAGLE_POS, self.size)
            return action  # Stay put while waiting

        # Find nearest steel cover position
        if self.retreat_pos is None:
            self.retreat_pos = nearest_steel(grid, (self.x, self.y), self.size)

        if self.retreat_pos and self.move_ready():
            # Move one step toward retreat position
            # Use BFS to find path to cover
            cover_path = bfs(grid, (self.x, self.y), self.retreat_pos, self.size)
            if cover_path and len(cover_path) > 1:
                move_dir = direction_to((self.x, self.y), cover_path[1])
                action['move'] = move_dir
                self.direction = move_dir
                self.move_timer = self.speed

                # Reached cover position
                if (self.x, self.y) == self.retreat_pos:
                    self.retreat_pos  = None
                    self.retreat_timer = 60  # Start 2-second wait
            else:
                # Can't reach cover — just wait
                self.retreat_timer = 60

        return action

    # ----------------------------------------------------------
    def _path_valid(self, grid):
        """Check if the next A* step is still traversable."""
        if len(self.path) < 2:
            return False
        nx, ny = self.path[1]
        tile = grid[ny][nx]
        return tile not in {STEEL, WATER}


# ============================================================
#  TANK FACTORY  (convenience function)
# ============================================================

def spawn_tank(tank_type, x, y):
    """
    Spawn the correct tank class based on type string.
    Called by the spawn system in game.py.
    """
    factories = {
        'basic'  : BasicTank,
        'fast'   : FastTank,
        'armor'  : ArmorTank,
        'player' : PlayerTank,
    }
    cls = factories.get(tank_type.lower())
    if cls is None:
        raise ValueError(f"Unknown tank type: '{tank_type}'")
    return cls(x, y)

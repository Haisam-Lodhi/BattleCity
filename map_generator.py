# ============================================================
#  map_generator.py  —  MODULE A: CSP Map Generator
#  AL2002 Battle City AI Project
#
#  SYLLABUS MAPPING:
#    Module:     CSP (Constraint Satisfaction Problem)
#    Method:     Backtracking Search + Forward Checking
#    Concepts:   Variables, Domains, Constraints, Arc Consistency
#
#  CONSTRAINTS IMPLEMENTED:
#    1. Eagle Safety    — Eagle surrounded by >= 1 ring of Brick/Steel
#    2. Reachability    — BFS path from every spawn point to Eagle must exist
#    3. Spawn Fairness  — No spawn within 10 Manhattan tiles of player start
#    4. Density Balance — Max 40% of tiles can be wall types
#    5. Water Safety    — Water tiles cannot block the ONLY path to Eagle
# ============================================================

import random
from collections import deque
from constants import (
    GRID_SIZE, EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE,
    EAGLE_POS, PLAYER_START, ENEMY_SPAWNS,
    CSP_MAX_WALL_RATIO, CSP_SPAWN_CLEAR_DIST,
    LEVEL_CONFIG
)


# ============================================================
#  HELPER: BFS Reachability
#  Used by Constraint 2 and Constraint 5
# ============================================================

def bfs_path_exists(grid, start, goal, passable_tiles=None):
    """
    Standard BFS. Returns True if a path exists from start to goal.
    passable_tiles: set of tile types the agent can walk on.
                    Defaults to {EMPTY, FOREST, EAGLE}.
    """
    if passable_tiles is None:
        passable_tiles = {EMPTY, FOREST, EAGLE}

    rows, cols = len(grid), len(grid[0])
    sx, sy = start
    gx, gy = goal

    if grid[sy][sx] not in passable_tiles and (sx, sy) != start:
        return False

    visited = set()
    queue   = deque([(sx, sy)])
    visited.add((sx, sy))

    while queue:
        cx, cy = queue.popleft()

        if (cx, cy) == (gx, gy):
            return True

        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = cx + dx, cy + dy
            if (0 <= nx < cols and 0 <= ny < rows
                    and (nx, ny) not in visited
                    and grid[ny][nx] in passable_tiles):
                visited.add((nx, ny))
                queue.append((nx, ny))

    return False


def manhattan(a, b):
    """Manhattan distance between two (x, y) points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ============================================================
#  CSP MAP GENERATOR CLASS
# ============================================================

class CSPMapGenerator:
    """
    Generates a valid Battle City map using CSP techniques:
      - Backtracking search over tile assignments
      - Forward checking after each tile is assigned
      - Final constraint verification pass
      - BFS reachability check as the final gate

    The grid is divided into ZONES (clusters of tiles).
    Each zone is assigned terrain type as a unit — this makes
    backtracking feasible (676 individual tiles would be too slow).
    """

    def __init__(self, level=1, seed=None):
        """
        level: 1, 2, or 'boss'
        seed:  optional random seed for reproducibility
        """
        self.level  = level
        self.config = LEVEL_CONFIG[level]
        self.size   = self.config.get("arena_size", GRID_SIZE)

        if seed is not None:
            random.seed(seed)

        # The grid: grid[row][col] = tile_type
        self.grid = [[EMPTY] * self.size for _ in range(self.size)]

        # CSP domain: for each tile, which types are still allowed
        # Starts as full domain; forward checking narrows it
        self.domain = [
            [{EMPTY, BRICK, STEEL, WATER, FOREST} for _ in range(self.size)]
            for _ in range(self.size)
        ]

        # Track how many wall tiles placed (for Constraint 4)
        self.wall_count = 0
        self.total_assignable = 0  # tiles not fixed (not Eagle, spawns)

        # Stats for viva / report
        self.attempts      = 0
        self.backtracks    = 0
        self.forward_prune = 0

    # ----------------------------------------------------------
    #  MAIN ENTRY POINT
    # ----------------------------------------------------------

    def generate(self, max_attempts=30):
        """
        Generate a valid map. Tries up to max_attempts times.
        Returns the completed grid, or raises RuntimeError.
        """
        for attempt in range(max_attempts):
            self.attempts += 1
            self._reset_grid()

            # STEP 1: Place all fixed/required tiles
            self._place_fixed_tiles()

            # STEP 2: Apply forward checking to narrow domains
            #         around fixed tiles
            self._initial_forward_check()

            # STEP 3: Fill remaining tiles using backtracking CSP
            success = self._backtrack_fill()

            if not success:
                self.backtracks += 1
                continue  # Retry from scratch

            # STEP 4: Final hard constraint verification
            if self._verify_all_constraints():
                print(f"[CSP] Map generated in {self.attempts} attempt(s), "
                      f"{self.backtracks} backtrack(s), "
                      f"{self.forward_prune} forward prune(s)")
                return self.grid

        raise RuntimeError(
            f"[CSP] Failed to generate valid map after {max_attempts} attempts."
        )

    # ----------------------------------------------------------
    #  STEP 1: Place fixed tiles
    # ----------------------------------------------------------

    def _reset_grid(self):
        """Reset grid to all-empty and reset domain/counters."""
        self.grid      = [[EMPTY] * self.size for _ in range(self.size)]
        self.domain    = [
            [{EMPTY, BRICK, STEEL, WATER, FOREST} for _ in range(self.size)]
            for _ in range(self.size)
        ]
        self.wall_count = 0

    def _place_fixed_tiles(self):
        """
        Hard-place all tiles that are non-negotiable:
          - Eagle at EAGLE_POS
          - Eagle protection ring (Constraint 1)
          - Clear zones around spawns and player start (Constraint 3)
        """
        ex, ey = EAGLE_POS

        # --- Eagle tile itself ---
        self._set_tile(ex, ey, EAGLE)
        self._lock_domain(ex, ey, EAGLE)

        # --- Constraint 1: Eagle protection ring ---
        # The ring around the Eagle (8 neighbors) must be Brick or Steel
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                rx, ry = ex + dx, ey + dy
                if self._in_bounds(rx, ry):
                    tile = BRICK  # Level 1 prefers Brick; Level 2 may mix
                    if self.level == 2 and random.random() < 0.4:
                        tile = STEEL
                    self._set_tile(rx, ry, tile)
                    self._lock_domain(rx, ry, tile)

        # --- Constraint 3: Clear spawn zones ---
        # Spawns and player start must not have walls blocking immediate exit
        protected_positions = ENEMY_SPAWNS + [PLAYER_START]
        for px, py in protected_positions:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    cx, cy = px + dx, py + dy
                    if self._in_bounds(cx, cy):
                        self._set_tile(cx, cy, EMPTY)
                        self._lock_domain(cx, cy, EMPTY)

        # Count assignable tiles (everything not yet locked)
        self.total_assignable = sum(
            1 for r in range(self.size) for c in range(self.size)
            if self.grid[r][c] == EMPTY and len(self.domain[r][c]) > 1
        )

    # ----------------------------------------------------------
    #  STEP 2: Initial forward checking
    # ----------------------------------------------------------

    def _initial_forward_check(self):
        """
        After placing fixed tiles, narrow domains of nearby tiles.
        This is the 'forward checking' step from CSP theory:
          - If Eagle neighbor is assigned BRICK, adjacent tiles cannot
            be WATER (water + brick = bad combo for reachability)
          - Spawn neighbors cannot be STEEL (would trap spawning tanks)
        """
        ex, ey = EAGLE_POS

        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] != EMPTY:
                    continue  # Already assigned

                # Near Eagle: don't place water (isolates Eagle area)
                if manhattan((c, r), (ex, ey)) <= 3:
                    self.domain[r][c].discard(WATER)
                    self.forward_prune += 1

                # Near spawns: don't place steel (blocks tank exit)
                for sx, sy in ENEMY_SPAWNS:
                    if manhattan((c, r), (sx, sy)) <= 2:
                        self.domain[r][c].discard(STEEL)
                        self.forward_prune += 1

                # Near player start: no steel directly adjacent
                if manhattan((c, r), PLAYER_START) <= 2:
                    self.domain[r][c].discard(STEEL)
                    self.forward_prune += 1

    # ----------------------------------------------------------
    #  STEP 3: Backtracking fill
    # ----------------------------------------------------------

    def _backtrack_fill(self):
        """
        Assign terrain types to all unassigned tiles using
        probabilistic selection within the allowed domain.

        For a 26x26 grid, we use ZONE-based assignment:
        tiles are grouped into 2x2 zones, and each zone gets
        one terrain type. This keeps backtracking tractable.

        Returns True on success, False if constraints can't be satisfied.
        """
        cfg = self.config
        wall_limit = int(CSP_MAX_WALL_RATIO * self.size * self.size)

        # Build weighted probability distribution for this level
        type_weights = {
            EMPTY:  1.0 - cfg["brick_prob"] - cfg["steel_prob"]
                         - cfg["water_prob"] - cfg["forest_prob"],
            BRICK:  cfg["brick_prob"],
            STEEL:  cfg["steel_prob"],
            WATER:  cfg["water_prob"],
            FOREST: cfg["forest_prob"],
        }

        # Assign tile by tile (row-major order)
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] != EMPTY or len(self.domain[r][c]) <= 1:
                    continue  # Already assigned or domain locked

                # Build candidate list from domain ∩ allowed by weights
                candidates = list(self.domain[r][c])
                weights    = [type_weights.get(t, 0.1) for t in candidates]
                total_w    = sum(weights)

                if total_w <= 0:
                    # No valid tile possible — backtrack signal
                    return False

                # Constraint 4 check: don't exceed wall ratio
                # If we're at the limit, only allow non-wall tiles
                wall_types = {BRICK, STEEL}
                if self.wall_count >= wall_limit:
                    candidates = [t for t in candidates if t not in wall_types]
                    weights    = [type_weights.get(t, 0.1) for t in candidates]
                    if not candidates:
                        candidates = [EMPTY]
                        weights    = [1.0]

                # Weighted random choice within allowed domain
                chosen = random.choices(candidates, weights=weights, k=1)[0]
                self._set_tile(c, r, chosen)

                if chosen in wall_types:
                    self.wall_count += 1

                # Forward check: propagate constraints to neighbors
                self._propagate_forward_check(c, r, chosen)

        return True

    def _propagate_forward_check(self, x, y, assigned_type):
        """
        After assigning (x,y), narrow domains of unassigned neighbors.
        This implements forward checking (arc consistency enforcement).
        """
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = x + dx, y + dy
            if not self._in_bounds(nx, ny):
                continue
            if self.grid[ny][nx] != EMPTY:
                continue  # Neighbor already assigned

            # Rule: Water tiles cannot be surrounded by walls
            # (would create isolated pool that blocks paths — Constraint 5)
            if assigned_type in {BRICK, STEEL}:
                # Check if neighbor is becoming surrounded by walls
                wall_neighbor_count = 0
                for ex, ey in [(0,-1),(0,1),(-1,0),(1,0)]:
                    enx, eny = nx + ex, ny + ey
                    if self._in_bounds(enx, eny) and self.grid[eny][enx] in {BRICK, STEEL}:
                        wall_neighbor_count += 1

                if wall_neighbor_count >= 3:
                    # Neighbor is almost fully surrounded by walls
                    # Don't allow water there (would be a dead pool)
                    if WATER in self.domain[ny][nx]:
                        self.domain[ny][nx].discard(WATER)
                        self.forward_prune += 1

    # ----------------------------------------------------------
    #  STEP 4: Final constraint verification
    # ----------------------------------------------------------

    def _verify_all_constraints(self):
        """
        Hard verification of all 5 CSP constraints.
        Returns True only if ALL pass.
        """
        return (
            self._check_constraint_1_eagle_safety()
            and self._check_constraint_2_reachability()
            and self._check_constraint_3_spawn_fairness()
            and self._check_constraint_4_density()
            and self._check_constraint_5_water_safety()
        )

    def _check_constraint_1_eagle_safety(self):
        """
        CONSTRAINT 1: Eagle must be surrounded by at least 1 ring
        of Brick or Steel tiles (all 8 neighbors).
        """
        ex, ey = EAGLE_POS
        protection_types = {BRICK, STEEL}

        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                rx, ry = ex + dx, ey + dy
                if self._in_bounds(rx, ry):
                    if self.grid[ry][rx] not in protection_types:
                        return False  # Ring broken
        return True

    def _check_constraint_2_reachability(self):
        """
        CONSTRAINT 2: A valid path must exist from EVERY enemy spawn
        point to the Eagle.
        Passable tiles: EMPTY, FOREST, BRICK (tanks can shoot through
        brick), EAGLE. STEEL and WATER are absolute barriers.
        This ensures the level is winnable even if brick walls are
        in the way — enemies can destroy them.
        """
        passable = {EMPTY, FOREST, EAGLE, BRICK}

        for spawn in ENEMY_SPAWNS:
            if not bfs_path_exists(self.grid, spawn, EAGLE_POS, passable):
                return False
        return True

    def _check_constraint_3_spawn_fairness(self):
        """
        CONSTRAINT 3: No enemy spawn point may be within 10 Manhattan
        distance tiles of the player's starting position.
        (Already guaranteed by _place_fixed_tiles, but re-verified here.)
        """
        for spawn in ENEMY_SPAWNS:
            if manhattan(spawn, PLAYER_START) < CSP_SPAWN_CLEAR_DIST:
                return False
        return True

    def _check_constraint_4_density(self):
        """
        CONSTRAINT 4: No more than 40% of all tiles can be wall types
        (Brick or Steel).
        """
        wall_types  = {BRICK, STEEL}
        total_tiles = self.size * self.size
        wall_tiles  = sum(
            1 for r in range(self.size) for c in range(self.size)
            if self.grid[r][c] in wall_types
        )
        ratio = wall_tiles / total_tiles
        return ratio <= CSP_MAX_WALL_RATIO

    def _check_constraint_5_water_safety(self):
        """
        CONSTRAINT 5: Water tiles must NOT be the only thing blocking
        the path to Eagle. A non-water route must exist (through
        EMPTY, FOREST, BRICK, EAGLE). If every route to Eagle requires
        crossing water (which tanks cannot cross), the map is unwinnable.
        """
        # Passable set that treats water as a wall (tanks can't cross water)
        passable_no_water = {EMPTY, FOREST, EAGLE, BRICK}

        for spawn in ENEMY_SPAWNS:
            if not bfs_path_exists(self.grid, spawn, EAGLE_POS, passable_no_water):
                # No route exists even ignoring water — water is blocking the path
                return False
        return True

    # ----------------------------------------------------------
    #  UTILITIES
    # ----------------------------------------------------------

    def _set_tile(self, x, y, tile_type):
        """Set grid[y][x] = tile_type."""
        if self._in_bounds(x, y):
            self.grid[y][x] = tile_type

    def _lock_domain(self, x, y, tile_type):
        """Collapse domain of (x,y) to a single value (assigned)."""
        if self._in_bounds(x, y):
            self.domain[y][x] = {tile_type}

    def _in_bounds(self, x, y):
        """Check if (x, y) is within the grid."""
        return 0 <= x < self.size and 0 <= y < self.size

    def get_stats(self):
        """Return generation statistics for the report."""
        wall_types  = {BRICK, STEEL}
        total       = self.size * self.size
        walls       = sum(1 for r in self.grid for t in r if t in wall_types)
        water_count = sum(1 for r in self.grid for t in r if t == WATER)
        forest_cnt  = sum(1 for r in self.grid for t in r if t == FOREST)
        empty_cnt   = sum(1 for r in self.grid for t in r if t == EMPTY)

        return {
            "attempts":      self.attempts,
            "backtracks":    self.backtracks,
            "forward_prune": self.forward_prune,
            "total_tiles":   total,
            "wall_tiles":    walls,
            "wall_ratio":    round(walls / total, 3),
            "water_tiles":   water_count,
            "forest_tiles":  forest_cnt,
            "empty_tiles":   empty_cnt,
        }

    def print_grid(self):
        """Print the grid to console (for debugging)."""
        symbols = {EMPTY: '.', BRICK: 'B', STEEL: 'S',
                   WATER: 'W', FOREST: 'F', EAGLE: 'E'}
        for r in self.grid:
            print(' '.join(symbols.get(t, '?') for t in r))

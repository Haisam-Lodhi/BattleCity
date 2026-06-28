# ============================================================
#  search.py  —  MODULE B: Search Algorithms
#  AL2002 Battle City AI Project
#
#  THREE ALGORITHMS — each assigned to a specific tank type:
#
#  1. BFS  (Breadth-First Search)  →  Basic Tank
#     - Finds SHORTEST-HOP path (ignores tile cost)
#     - Optimal for hop count; NOT optimal for cost
#     - Takes the long detour around a brick wall
#
#  2. Greedy Best-First  →  Fast Tank
#     - Picks neighbour closest to goal (Manhattan heuristic)
#     - NOT optimal — can get stuck in local minima
#     - Rushes forward; may walk into a dead end
#
#  3. A*  →  Armor Tank
#     - Cost-aware: g(n) + h(n)
#     - Tile costs: empty=1, forest=1, brick=3, steel=∞, water=∞
#     - Discovers it's cheaper to SHOOT through thin brick (cost 3)
#       than walk 6+ tiles around (cost 6+)
#
#  KEY DEMO (from spec):
#    Place a 1-tile-wide brick wall across the direct path,
#    with a 6-tile empty detour available.
#      BFS   → takes the long detour (cost-blind, hop count = 8)
#      A*    → shoots through the brick wall (cost 3 < 6)
#      Greedy → may get stuck trying to push straight through
# ============================================================

import heapq
from collections import deque
from constants import EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE, GRID_SIZE, ASTAR_COST

# ─── Direction vectors ────────────────────────────────────────
UP    = (0, -1)
DOWN  = (0,  1)
LEFT  = (-1, 0)
RIGHT = (1,  0)
ALL_DIRS = [UP, DOWN, LEFT, RIGHT]


def _in_bounds(x, y, size=GRID_SIZE):
    return 0 <= x < size and 0 <= y < size


def _reconstruct(came_from, start, goal):
    """Walk the came_from map backwards to build the full path."""
    path = []
    node = goal
    while node != start:
        path.append(node)
        node = came_from[node]
    path.append(start)
    path.reverse()
    return path


# ============================================================
#  ALGORITHM 1 — BFS  (Basic Tank)
# ============================================================

def bfs(grid, start, goal, size=GRID_SIZE):
    """
    Breadth-First Search — finds the shortest-HOP path.

    Passable tiles: EMPTY (0) and FOREST (4) only.
    BFS does NOT consider shooting through bricks — it detours.

    Parameters:
        grid  : 2D list, grid[row][col] = tile type
        start : (x, y) starting position
        goal  : (x, y) target position (usually Eagle)
        size  : grid dimension

    Returns:
        List of (x, y) tuples from start → goal (inclusive).
        Empty list if no path found.

    Time complexity : O(V + E) = O(N²) for an N×N grid
    Space complexity: O(N²)
    """
    if start == goal:
        return [start]

    passable = {EMPTY, FOREST, EAGLE}

    visited  = {start}
    queue    = deque([start])
    came_from = {start: None}

    while queue:
        cx, cy = queue.popleft()

        for dx, dy in ALL_DIRS:
            nx, ny = cx + dx, cy + dy
            if not _in_bounds(nx, ny, size):
                continue
            if (nx, ny) in visited:
                continue
            if grid[ny][nx] not in passable:
                continue

            visited.add((nx, ny))
            came_from[(nx, ny)] = (cx, cy)
            queue.append((nx, ny))

            if (nx, ny) == goal:
                return _reconstruct(came_from, start, goal)

    return []  # No path found


# ============================================================
#  ALGORITHM 2 — Greedy Best-First  (Fast Tank)
# ============================================================

def greedy_step(grid, current, goal, size=GRID_SIZE):
    """
    Greedy Best-First — single-step decision (NOT a full path).

    The Fast Tank re-computes this EVERY tick — it just picks the
    neighbour tile with the lowest Manhattan distance to the goal.
    No caching, no full path, no cost awareness.

    Parameters:
        grid    : 2D list
        current : (x, y) tank's current position
        goal    : (x, y) target (Eagle)
        size    : grid dimension

    Returns:
        (x, y) of the best next step, or None if completely stuck.

    Why this fails: if the lowest-distance neighbour is blocked,
    the tank gets stuck — classic local minima problem.
    This is INTENTIONAL — it shows why greedy is not optimal.
    """
    cx, cy = current
    best_step = None
    best_dist = float('inf')

    # Passable tiles for movement (can't walk through steel/water)
    passable = {EMPTY, FOREST, EAGLE}

    for dx, dy in ALL_DIRS:
        nx, ny = cx + dx, cy + dy
        if not _in_bounds(nx, ny, size):
            continue

        tile = grid[ny][nx]

        # Greedy allows moving into BRICK — it will shoot to clear it
        # (unlike BFS which detours around brick)
        if tile in passable or tile == BRICK:
            dist = abs(nx - goal[0]) + abs(ny - goal[1])
            if dist < best_dist:
                best_dist = dist
                best_step = (nx, ny)

    return best_step


def manhattan(a, b):
    """Manhattan distance between two (x, y) points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ============================================================
#  ALGORITHM 3 — A*  (Armor Tank)
# ============================================================

def astar(grid, start, goal, size=GRID_SIZE):
    """
    A* Search — cost-optimal pathfinding with tile weights.

    Tile costs (from spec):
        Empty  = 1  (standard movement)
        Forest = 1  (same as empty, but hides tank)
        Brick  = 3  (shoot + wait penalty — but cheaper than long detour)
        Steel  = ∞  (absolute barrier — cannot pass)
        Water  = ∞  (absolute barrier — tanks cannot cross water)

    Heuristic h(n): Manhattan distance to goal.
    Admissible: never overestimates (since min tile cost = 1).

    Parameters:
        grid  : 2D list
        start : (x, y) starting position
        goal  : (x, y) target (Eagle)
        size  : grid dimension

    Returns:
        List of (x, y) tuples from start → goal (inclusive).
        Empty list if no path found.

    Key insight for viva:
        If there's a 1-tile brick wall across the direct path
        and a 6-tile empty detour, A* chooses to shoot through
        the brick (cost 3) NOT take the detour (cost 6).
        BFS would take the detour — it can't see costs.

    Time complexity : O((V + E) log V) = O(N² log N)
    Space complexity: O(N²)
    """
    if start == goal:
        return [start]

    # Priority queue: (f_cost, g_cost, x, y)
    # f = g + h, where g = actual cost so far, h = heuristic
    open_set = []
    heapq.heappush(open_set, (0 + manhattan(start, goal), 0, start[0], start[1]))

    came_from  = {start: None}
    g_cost     = {start: 0}

    while open_set:
        f, g, cx, cy = heapq.heappop(open_set)

        if (cx, cy) == goal:
            return _reconstruct(came_from, start, goal)

        # Skip if we've already found a better path here
        if g > g_cost.get((cx, cy), float('inf')):
            continue

        for dx, dy in ALL_DIRS:
            nx, ny = cx + dx, cy + dy
            if not _in_bounds(nx, ny, size):
                continue

            tile      = grid[ny][nx]
            tile_cost = ASTAR_COST.get(tile, float('inf'))

            if tile_cost == float('inf'):
                continue  # Steel or water — skip

            new_g = g + tile_cost
            if new_g < g_cost.get((nx, ny), float('inf')):
                g_cost[(nx, ny)]    = new_g
                came_from[(nx, ny)] = (cx, cy)
                h = manhattan((nx, ny), goal)
                heapq.heappush(open_set, (new_g + h, new_g, nx, ny))

    return []  # No path found


# ============================================================
#  UTILITY FUNCTIONS  (used by tanks)
# ============================================================

def has_line_of_sight(grid, pos1, pos2, size=GRID_SIZE):
    """
    Returns True if pos1 and pos2 share a row or column
    with no wall tiles (BRICK, STEEL, WATER) between them.

    Used by Basic Tank (Rule 1) and Armor Tank to decide when to shoot.
    """
    x1, y1 = pos1
    x2, y2 = pos2
    wall_tiles = {BRICK, STEEL, WATER}

    if x1 == x2:  # Same column
        for y in range(min(y1, y2) + 1, max(y1, y2)):
            if grid[y][x1] in wall_tiles:
                return False
        return True

    if y1 == y2:  # Same row
        for x in range(min(x1, x2) + 1, max(x1, x2)):
            if grid[y1][x] in wall_tiles:
                return False
        return True

    return False  # Not aligned


def direction_to(src, dst):
    """
    Return the direction vector from src to dst.
    Only works correctly when they are aligned (same row or column).
    """
    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    if dx != 0:
        return (1, 0) if dx > 0 else (-1, 0)
    if dy != 0:
        return (0, 1) if dy > 0 else (0, -1)
    return DOWN  # Fallback


def nearest_steel(grid, pos, size=GRID_SIZE):
    """
    BFS to find the nearest STEEL tile — used by Armor Tank
    when retreating to cover after taking 3 hits.

    Returns (x, y) of nearest steel tile, or None if none found.
    """
    sx, sy = pos
    visited = {(sx, sy)}
    queue   = deque([(sx, sy)])

    passable_search = {EMPTY, FOREST, BRICK}  # Can walk/shoot through these

    while queue:
        cx, cy = queue.popleft()
        for dx, dy in ALL_DIRS:
            nx, ny = cx + dx, cy + dy
            if not _in_bounds(nx, ny, size) or (nx, ny) in visited:
                continue
            tile = grid[ny][nx]
            if tile == STEEL:
                # Return the adjacent tile next to the steel (cover position)
                return (cx, cy)
            if tile in passable_search:
                visited.add((nx, ny))
                queue.append((nx, ny))

    return None  # No steel found


def get_path_cost(grid, path):
    """
    Calculate total cost of a given path.
    Used for reporting/comparison in the project report.
    """
    total = 0
    for x, y in path[1:]:  # Skip starting tile
        total += ASTAR_COST.get(grid[y][x], 1)
    return total

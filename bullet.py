# ============================================================
#  bullet.py  —  Bullet System
#  AL2002 Battle City AI Project
#
#  Bullets are fired by any tank. They travel in a straight line
#  until they hit something. Per the spec:
#    - Bullet hits Brick  → wall destroyed (tile becomes Empty)
#    - Bullet hits Steel  → bullet destroyed, steel stays
#    - Bullet hits Tank   → tank takes 1 hit damage
#    - Bullet hits Eagle  → GAME OVER immediately
#    - Bullet vs Bullet   → both destroyed
#    - Bullets pass through Forest tiles without stopping
# ============================================================

from constants import EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE, GRID_SIZE


class Bullet:
    """
    A single bullet travelling across the grid.

    Attributes:
        x, y      : current tile position
        dx, dy    : direction vector (one of the 4 cardinal dirs)
        owner     : 'player' or 'enemy' (for hit detection)
        alive     : False when bullet should be removed
    """

    def __init__(self, x, y, direction, owner='enemy'):
        self.x     = x
        self.y     = y
        self.dx    = direction[0]
        self.dy    = direction[1]
        self.owner = owner     # 'player' or 'enemy'
        self.alive = True
        self.size  = GRID_SIZE

    # ----------------------------------------------------------
    #  UPDATE — move bullet one tile and check terrain collision
    # ----------------------------------------------------------

    def update(self, grid):
        """
        Advance bullet one tile in its direction.
        Check terrain collision and update the grid if a wall is hit.

        Returns a string indicating what happened:
          'moved'        — bullet moved to empty/forest tile
          'hit_brick'    — brick wall destroyed
          'hit_steel'    — bullet destroyed by steel
          'hit_water'    — bullet destroyed by water
          'hit_eagle'    — Eagle hit (game over trigger)
          'out_of_bounds'— bullet left the grid
        """
        if not self.alive:
            return 'dead'

        # Advance position
        self.x += self.dx
        self.y += self.dy

        # Out of bounds check
        if not (0 <= self.x < self.size and 0 <= self.y < self.size):
            self.alive = False
            return 'out_of_bounds'

        tile = grid[self.y][self.x]

        # Forest: bullet passes through (does NOT stop)
        if tile == FOREST:
            return 'moved'

        # Empty: bullet continues
        if tile == EMPTY:
            return 'moved'

        # Brick: destroy the wall permanently, bullet is consumed
        if tile == BRICK:
            grid[self.y][self.x] = EMPTY  # Permanent map change
            self.alive = False
            return 'hit_brick'

        # Steel: bullet is destroyed, steel wall stays
        if tile == STEEL:
            self.alive = False
            return 'hit_steel'

        # Water: bullet is destroyed (can't travel through water)
        if tile == WATER:
            self.alive = False
            return 'hit_water'

        # Eagle: immediate game over trigger
        if tile == EAGLE:
            self.alive = False
            return 'hit_eagle'

        # Unknown tile: destroy bullet to be safe
        self.alive = False
        return 'hit_unknown'

    # ----------------------------------------------------------
    #  COLLISION WITH TANKS
    # ----------------------------------------------------------

    def check_tank_hit(self, tank):
        """
        Returns True if this bullet is at the same tile as the tank.
        The caller is responsible for applying damage.
        """
        return self.alive and self.x == tank.x and self.y == tank.y

    def check_bullet_collision(self, other):
        """
        Returns True if two bullets are at the same tile.
        When bullets collide, both are destroyed.
        """
        return (self.alive and other.alive and
                self.x == other.x and self.y == other.y)

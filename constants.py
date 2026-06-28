# ============================================================
#  constants.py  —  Battle City AI Project
#  All fixed values used across the entire game
# ============================================================

# ---------- Grid ----------
GRID_SIZE   = 26          # 26x26 tile grid
TILE_SIZE   = 24          # pixels per tile (for rendering)
PANEL_W     = 160         # right-side UI panel width in pixels

# ---------- Tile type codes ----------
EMPTY  = 0
BRICK  = 1
STEEL  = 2
WATER  = 3
FOREST = 4
EAGLE  = 5

TILE_NAMES = {
    EMPTY:  "Empty",
    BRICK:  "Brick",
    STEEL:  "Steel",
    WATER:  "Water",
    FOREST: "Forest",
    EAGLE:  "Eagle",
}

# ---------- Fixed map positions ----------
EAGLE_POS        = (12, 24)          # Eagle (base) tile — always fixed
PLAYER_START     = (4,  24)          # Player spawn tile
ENEMY_SPAWNS     = [(0, 0), (12, 0), (24, 0)]  # Top-left, top-center, top-right

# ---------- A* movement costs ----------
ASTAR_COST = {
    EMPTY:  1,
    FOREST: 1,
    BRICK:  3,    # Shoot + wait penalty
    STEEL:  float('inf'),   # Absolute barrier
    WATER:  float('inf'),   # Tanks cannot cross water
    EAGLE:  1,
}

# ---------- Colors (R, G, B) ----------
COLOR = {
    EMPTY:  (30,  30,  30),     # Dark background
    BRICK:  (180, 80,  40),     # Orange-brown
    STEEL:  (130, 140, 150),    # Metallic gray
    WATER:  (40,  80,  180),    # Blue
    FOREST: (30,  110, 50),     # Dark green
    EAGLE:  (220, 200, 50),     # Gold
    "bg":           (20,  20,  20),
    "panel":        (40,  40,  40),
    "grid_line":    (50,  50,  50),
    "spawn_mark":   (200, 50,  50),
    "player_mark":  (50,  200, 100),
    "text":         (220, 220, 220),
    "text_dim":     (140, 140, 140),
    "highlight":    (255, 220, 50),
}

# ---------- CSP constraint parameters ----------
CSP_MAX_WALL_RATIO   = 0.40   # Constraint 4: max 40% of tiles can be walls
CSP_SPAWN_CLEAR_DIST = 10     # Constraint 3: no spawn within 10 Manhattan tiles of player
CSP_EAGLE_RING       = 1      # Constraint 1: Eagle must have at least 1 ring of brick/steel

# ---------- Level configs for CSP generator ----------
# Each level adjusts density of terrain types
LEVEL_CONFIG = {
    1: {
        "name":         "Brick Maze",
        "brick_prob":   0.35,
        "steel_prob":   0.05,
        "water_prob":   0.03,
        "forest_prob":  0.08,
        "description":  "Dense brick maze — walls get destroyed, paths open up mid-game",
    },
    2: {
        "name":         "Steel Fortress",
        "brick_prob":   0.20,
        "steel_prob":   0.18,
        "water_prob":   0.04,
        "forest_prob":  0.06,
        "description":  "Mix of brick and steel — steel walls form permanent barriers",
    },
    "boss": {
        "name":         "Boss Arena",
        "brick_prob":   0.10,
        "steel_prob":   0.20,
        "water_prob":   0.05,
        "forest_prob":  0.05,
        "description":  "Tight 12x12 arena — mixed terrain for strategic cover",
        "arena_size":   12,  # Boss level uses a sub-grid
    },
}

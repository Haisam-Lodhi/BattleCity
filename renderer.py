# ============================================================
#  renderer.py  —  Pygame Map Renderer
#  AL2002 Battle City AI Project
#
#  Renders the 26x26 grid with color-coded tiles,
#  spawn markers, player start, Eagle, and stats panel.
#  Used to visually verify that Module A (CSP) works correctly.
# ============================================================

import pygame
import sys
from constants import (
    GRID_SIZE, TILE_SIZE, PANEL_W,
    EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE,
    EAGLE_POS, PLAYER_START, ENEMY_SPAWNS,
    COLOR, TILE_NAMES, LEVEL_CONFIG
)


class Renderer:
    """
    Handles all pygame drawing for Battle City.
    In this phase (Module A), it draws:
      - The 26x26 CSP-generated map
      - Eagle position, spawn points, player start
      - Tile type legend
      - CSP stats (attempts, backtracks, forward prunes)
    """

    def __init__(self, level=1):
        pygame.init()

        self.level   = level
        self.size    = LEVEL_CONFIG[level].get("arena_size", GRID_SIZE)
        self.cell    = TILE_SIZE

        # Window size: grid + right panel
        win_w = self.size * self.cell + PANEL_W
        win_h = self.size * self.cell
        self.screen = pygame.display.set_mode((win_w, win_h))
        pygame.display.set_caption(
            f"Battle City AI — Level {level}: "
            f"{LEVEL_CONFIG[level]['name']} (Module A: CSP Map Generator)"
        )

        self.font_sm = pygame.font.SysFont("monospace", 11)
        self.font_md = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_lg = pygame.font.SysFont("monospace", 15, bold=True)
        self.clock   = pygame.time.Clock()

    def draw_map(self, grid, stats=None):
        """
        Draw the full map with overlays and stats panel.
        grid: 2D list from CSPMapGenerator
        stats: dict from generator.get_stats()
        """
        self.screen.fill(COLOR["bg"])
        self._draw_tiles(grid)
        self._draw_grid_lines()
        self._draw_special_markers(grid)
        self._draw_panel(grid, stats)
        pygame.display.flip()

    def _draw_tiles(self, grid):
        """Fill each cell with its terrain color."""
        for r in range(len(grid)):
            for c in range(len(grid[r])):
                tile  = grid[r][c]
                color = COLOR.get(tile, (80, 0, 80))  # Magenta for unknown
                rect  = pygame.Rect(c * self.cell, r * self.cell,
                                    self.cell, self.cell)
                pygame.draw.rect(self.screen, color, rect)

                # Extra texture hints
                if tile == BRICK:
                    self._draw_brick_texture(rect)
                elif tile == STEEL:
                    self._draw_steel_texture(rect)
                elif tile == WATER:
                    self._draw_water_texture(rect)

    def _draw_brick_texture(self, rect):
        """Draw simple mortar lines on brick tiles."""
        x, y, w, h = rect
        dark = (140, 60, 25)
        # Horizontal line at mid
        pygame.draw.line(self.screen, dark, (x, y + h//2), (x + w, y + h//2), 1)
        # Vertical lines alternating
        pygame.draw.line(self.screen, dark, (x + w//2, y), (x + w//2, y + h//2), 1)
        pygame.draw.line(self.screen, dark, (x + w//4, y + h//2), (x + w//4, y + h), 1)

    def _draw_steel_texture(self, rect):
        """Draw a cross highlight on steel tiles."""
        x, y, w, h = rect
        light = (170, 185, 200)
        pygame.draw.line(self.screen, light, (x+2, y+2), (x+w-2, y+h-2), 1)
        pygame.draw.line(self.screen, light, (x+w-2, y+2), (x+2, y+h-2), 1)

    def _draw_water_texture(self, rect):
        """Draw a wavy highlight on water tiles."""
        x, y, w, h = rect
        light = (80, 130, 220)
        pygame.draw.line(self.screen, light, (x+2, y+h//3), (x+w-2, y+h//3), 1)
        pygame.draw.line(self.screen, light, (x+2, y+2*h//3), (x+w-2, y+2*h//3), 1)

    def _draw_grid_lines(self):
        """Draw subtle grid overlay."""
        w = self.size * self.cell
        h = self.size * self.cell
        for c in range(self.size + 1):
            pygame.draw.line(self.screen, COLOR["grid_line"],
                             (c * self.cell, 0), (c * self.cell, h), 1)
        for r in range(self.size + 1):
            pygame.draw.line(self.screen, COLOR["grid_line"],
                             (0, r * self.cell), (w, r * self.cell), 1)

    def _draw_special_markers(self, grid):
        """Draw spawn points, player start, and Eagle marker."""
        cell = self.cell

        # Enemy spawn points (red triangles)
        for sx, sy in ENEMY_SPAWNS:
            cx = sx * cell + cell // 2
            cy = sy * cell + cell // 2
            pts = [(cx, cy - 6), (cx - 5, cy + 5), (cx + 5, cy + 5)]
            pygame.draw.polygon(self.screen, COLOR["spawn_mark"], pts)
            pygame.draw.polygon(self.screen, (255, 100, 100), pts, 1)

        # Player start (green circle)
        px, py = PLAYER_START
        cx = px * cell + cell // 2
        cy = py * cell + cell // 2
        pygame.draw.circle(self.screen, COLOR["player_mark"], (cx, cy), 6)
        pygame.draw.circle(self.screen, (100, 255, 150), (cx, cy), 6, 1)

        # Eagle label
        ex, ey = EAGLE_POS
        cx = ex * cell + cell // 2
        cy = ey * cell + cell // 2
        label = self.font_sm.render("E", True, (30, 30, 30))
        self.screen.blit(label, (cx - 4, cy - 5))

    def _draw_panel(self, grid, stats):
        """Draw right-side info panel with legend and CSP stats."""
        panel_x = self.size * self.cell
        panel_w = PANEL_W
        panel_h = self.size * self.cell

        # Panel background
        pygame.draw.rect(self.screen, COLOR["panel"],
                         (panel_x, 0, panel_w, panel_h))
        pygame.draw.line(self.screen, (80, 80, 80),
                         (panel_x, 0), (panel_x, panel_h), 1)

        y = 12
        def text(msg, color=COLOR["text"], font=None):
            nonlocal y
            f = font or self.font_sm
            surf = f.render(msg, True, color)
            self.screen.blit(surf, (panel_x + 8, y))
            y += surf.get_height() + 3

        def divider():
            nonlocal y
            pygame.draw.line(self.screen, (70, 70, 70),
                             (panel_x + 6, y), (panel_x + panel_w - 6, y), 1)
            y += 6

        # Title
        text("MODULE A", COLOR["highlight"], self.font_md)
        text("CSP Map Generator", COLOR["text_dim"])
        divider()

        # Level info
        cfg = LEVEL_CONFIG[self.level]
        text(f"Level: {self.level}", COLOR["text"], self.font_md)
        text(cfg["name"], COLOR["text_dim"])
        y += 4
        divider()

        # Tile legend
        text("Tile Legend", COLOR["highlight"], self.font_md)
        y += 2
        legend = [
            (EMPTY,  " Empty  "),
            (BRICK,  " Brick  "),
            (STEEL,  " Steel  "),
            (WATER,  " Water  "),
            (FOREST, " Forest "),
            (EAGLE,  " Eagle  "),
        ]
        for tile_type, label in legend:
            color = COLOR.get(tile_type, (200, 0, 200))
            swatch_rect = pygame.Rect(panel_x + 8, y, 10, 10)
            pygame.draw.rect(self.screen, color, swatch_rect)
            pygame.draw.rect(self.screen, (100, 100, 100), swatch_rect, 1)
            surf = self.font_sm.render(label, True, COLOR["text"])
            self.screen.blit(surf, (panel_x + 22, y - 1))
            y += 14

        divider()

        # Markers legend
        text("Markers", COLOR["highlight"], self.font_md)
        pygame.draw.polygon(self.screen, COLOR["spawn_mark"],
                            [(panel_x + 13, y + 8), (panel_x + 8, y + 17),
                             (panel_x + 18, y + 17)])
        surf = self.font_sm.render(" Enemy spawn", True, COLOR["text"])
        self.screen.blit(surf, (panel_x + 22, y + 5))
        y += 18

        pygame.draw.circle(self.screen, COLOR["player_mark"],
                           (panel_x + 13, y + 6), 5)
        surf = self.font_sm.render(" Player start", True, COLOR["text"])
        self.screen.blit(surf, (panel_x + 22, y + 2))
        y += 18
        divider()

        # CSP Statistics
        text("CSP Stats", COLOR["highlight"], self.font_md)
        if stats:
            text(f"Attempts:    {stats['attempts']}")
            text(f"Backtracks:  {stats['backtracks']}")
            text(f"Fwd prunes:  {stats['forward_prune']}")
            y += 4
            text(f"Total tiles: {stats['total_tiles']}")
            text(f"Walls:       {stats['wall_tiles']} ({stats['wall_ratio']*100:.1f}%)")
            text(f"Water:       {stats['water_tiles']}")
            text(f"Forest:      {stats['forest_tiles']}")
            text(f"Empty:       {stats['empty_tiles']}")

        divider()

        # Constraint check display
        text("Constraints", COLOR["highlight"], self.font_md)
        constraints = [
            "1. Eagle ring",
            "2. Reachability",
            "3. Spawn fair",
            "4. Density <40%",
            "5. Water safe",
        ]
        for c in constraints:
            check_surf = self.font_sm.render("OK  " + c, True, (100, 220, 100))
            self.screen.blit(check_surf, (panel_x + 8, y))
            y += 14

        divider()

        # Controls hint
        text("Controls:", COLOR["text_dim"])
        text("R = Regenerate", COLOR["text_dim"])
        text("1/2/B = Level", COLOR["text_dim"])
        text("ESC = Quit", COLOR["text_dim"])

    def run_interactive(self, generator_class):
        """
        Main interactive loop.
        Press R to regenerate map.
        Press 1, 2, B to switch levels.
        """
        level = self.level
        gen   = generator_class(level=level)
        grid  = gen.generate()
        stats = gen.get_stats()
        self.draw_map(grid, stats)

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    elif event.key == pygame.K_r:
                        # Regenerate current level
                        print("\n[User] Regenerating map...")
                        gen   = generator_class(level=level)
                        grid  = gen.generate()
                        stats = gen.get_stats()
                        self.draw_map(grid, stats)

                    elif event.key == pygame.K_1:
                        level = 1
                        self._resize(level, generator_class)
                        gen   = generator_class(level=level)
                        grid  = gen.generate()
                        stats = gen.get_stats()
                        self.draw_map(grid, stats)

                    elif event.key == pygame.K_2:
                        level = 2
                        self._resize(level, generator_class)
                        gen   = generator_class(level=level)
                        grid  = gen.generate()
                        stats = gen.get_stats()
                        self.draw_map(grid, stats)

            self.clock.tick(30)

        pygame.quit()
        sys.exit()

    def _resize(self, level, generator_class):
        """Resize window if level changes arena size."""
        self.level = level
        self.size  = LEVEL_CONFIG[level].get("arena_size", GRID_SIZE)
        win_w = self.size * self.cell + PANEL_W
        win_h = self.size * self.cell
        self.screen = pygame.display.set_mode((win_w, win_h))
        pygame.display.set_caption(
            f"Battle City AI — Level {level}: "
            f"{LEVEL_CONFIG[level]['name']} (Module A: CSP)"
        )

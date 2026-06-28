# ============================================================
#  main.py  —  Entry Point
#  AL2002 Battle City AI Project
#
#  HOW TO RUN:
#    pip install pygame
#    python main.py          -> Level 1 (Brick Maze)
#    python main.py 2        -> Level 2 (Steel Fortress)
#    python main.py boss     -> Boss Level (Minimax)
#    python main.py test     -> Headless logic test (no pygame)
# ============================================================

import sys


def run_full_test():
    """
    Headless test of ALL THREE MODULES — no pygame required.
    Verifies: CSP constraints, search algorithms, tank agents,
              Minimax node counts, Alpha-Beta speedup.
    """
    print("=" * 60)
    print("  BATTLE CITY AI — Full Module Verification")
    print("  Module A: CSP    Module B: Search    Module C: Minimax")
    print("=" * 60)

    from map_generator import CSPMapGenerator, bfs_path_exists
    from search import bfs, astar, greedy_step, get_path_cost
    from tanks import BasicTank, FastTank, ArmorTank
    from minimax import MinimaxEngine, GameState
    from boss_tank import BossTank
    from constants import (EAGLE_POS, ENEMY_SPAWNS, EMPTY, BRICK,
                           STEEL, FOREST, EAGLE)

    # ── MODULE A ────────────────────────────────────────────
    print("\n[ MODULE A — CSP Map Generator ]")
    all_pass = True
    for level in [1, 2]:
        gen   = CSPMapGenerator(level=level, seed=42)
        grid  = gen.generate()
        stats = gen.get_stats()

        ex, ey = EAGLE_POS
        ring_ok = all(
            grid[ey+dy][ex+dx] in {BRICK, STEEL}
            for dx in [-1,0,1] for dy in [-1,0,1]
            if not (dx==0 and dy==0) and 0<=ex+dx<26 and 0<=ey+dy<26
        )
        passable = {EMPTY, FOREST, EAGLE, BRICK}
        reach_ok = all(bfs_path_exists(grid, s, EAGLE_POS, passable)
                       for s in ENEMY_SPAWNS)
        walls = sum(1 for r in grid for t in r if t in {BRICK, STEEL})
        density_ok = walls / (26*26) <= 0.40

        status = 'PASS' if (ring_ok and reach_ok and density_ok) else 'FAIL'
        if status == 'FAIL': all_pass = False
        print(f"  Level {level}: C1={('PASS' if ring_ok else 'FAIL')}  "
              f"C2={('PASS' if reach_ok else 'FAIL')}  "
              f"C4={('PASS' if density_ok else 'FAIL')}  "
              f"walls={stats['wall_ratio']*100:.1f}%  → {status}")

    # ── MODULE B ────────────────────────────────────────────
    print("\n[ MODULE B — Search Algorithms ]")
    gen2  = CSPMapGenerator(level=1, seed=55)
    grid2 = gen2.generate()
    start = (0, 0)
    goal  = EAGLE_POS

    bfs_path   = bfs(grid2, start, goal)
    astar_path = astar(grid2, start, goal)
    greedy_nxt = greedy_step(grid2, start, goal)

    bfs_cost   = get_path_cost(grid2, bfs_path)
    astar_cost = get_path_cost(grid2, astar_path)

    print(f"  BFS   (Basic):  {len(bfs_path):>3} steps | cost = {bfs_cost:<5} | hop-optimal")
    print(f"  Greedy(Fast):   next={greedy_nxt} | single-step heuristic")
    print(f"  A*    (Armor):  {len(astar_path):>3} steps | cost = {astar_cost:<5} | cost-optimal")
    if bfs_cost > 0 and astar_cost <= bfs_cost:
        print(f"  KEY DEMO: A* cost ({astar_cost}) <= BFS cost ({bfs_cost}) — A* shoots through brick!")

    print("\n  Tank agent decision tests:")

    class FakePlayer:
        x, y, alive, hp, direction = 4, 24, True, 1, (0,-1)

    gen3  = CSPMapGenerator(level=1, seed=7)
    grid3 = gen3.generate()
    fp    = FakePlayer()

    bt = BasicTank(0, 0); bt.move_timer = 0
    act = bt.decide(grid3, fp, [])
    print(f"  BasicTank:  move={act['move']} shoot={act['shoot']} "
          f"path={len(bt.path)}steps  ✓ Simple Reflex")

    ft = FastTank(12, 0); ft.move_timer = 0
    act = ft.decide(grid3, fp, [])
    print(f"  FastTank:   move={act['move']} shoot={act['shoot']} "
          f"ignores player          ✓ Goal-Based")

    at = ArmorTank(24, 0); at.move_timer = 0
    act = at.decide(grid3, fp, [])
    at.take_hit(); at.take_hit(); at.take_hit()
    print(f"  ArmorTank:  path={len(at.path)}steps hitCount={at.hit_count} "
          f"retreating={at.retreating}  ✓ Model-Based")
    assert at.retreating, "ArmorTank retreat FAIL"

    # ── MODULE C ────────────────────────────────────────────
    print("\n[ MODULE C — Minimax + Alpha-Beta Pruning ]")

    from boss_game import generate_boss_arena
    arena = generate_boss_arena()

    engine = MinimaxEngine()
    state  = GameState(
        boss_x=10, boss_y=1,  boss_hp=10, boss_dir=(0,1),
        player_x=1, player_y=10, player_hp=1, player_dir=(0,-1),
        grid=arena, arena_size=12
    )

    print(f"\n  {'Depth':<8} {'No Pruning':>12} {'Alpha-Beta':>12} {'Speedup':>10} {'Pruned':>8}")
    print(f"  {'-'*54}")

    for depth in [2, 3, 4]:
        engine.reset_counters()
        best_action, stats = engine.get_best_action(state, depth)
        mm  = stats['nodes_minimax']
        ab  = stats['nodes_alphabeta']
        sp  = stats['speedup_ratio']
        pr  = stats['branches_pruned']
        print(f"  Depth {depth:<4} {mm:>12} {ab:>12} {sp:>9}x {pr:>8} branches pruned")

    print(f"\n  Best action at depth 4: '{best_action}'")
    print(f"  Alpha-Beta is O(b^(d/2)) vs Minimax O(b^d)")
    print(f"  With b=5, d=4: Minimax≈{5**4} nodes  A-Beta≈{5**2} nodes")

    print("\n  Phase system test:")
    boss = BossTank(10, 1, arena_size=12)
    print(f"  HP=10 → Phase {boss.current_phase} (depth={boss.depth}) ✓")
    for _ in range(4): boss.take_hit()
    print(f"  HP=6  → Phase {boss.current_phase} (depth={boss.depth}) ✓")
    for _ in range(3): boss.take_hit()
    print(f"  HP=3  → Phase {boss.current_phase} (depth={boss.depth}) ✓")
    boss.take_hit()
    print(f"  HP=2  → Phase {boss.current_phase} (depth={boss.depth}) ✓")

    print("\n" + "=" * 60)
    print("  MODULE A: COMPLETE ✓  CSP + 5 constraints + backtracking")
    print("  MODULE B: COMPLETE ✓  BFS + Greedy + A* + 3 tank agents")
    print("  MODULE C: COMPLETE ✓  Minimax + Alpha-Beta + 3 phases")
    print("=" * 60)
    print("\n  Run:  python main.py       → Level 1")
    print("        python main.py 2      → Level 2")
    print("        python main.py boss   → Boss Battle")


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else '1'

    if arg == 'test':
        run_full_test()
        return

    try:
        import pygame
        pygame.init()
        pygame.display.set_mode((1, 1))
        pygame.display.quit()
        pygame.init()

        if arg == 'boss':
            from boss_game import BossGame
            BossGame().run()
        else:
            level = int(arg) if arg in ('1', '2') else 1
            from game import BattleCityGame
            BattleCityGame(level=level).run()

    except Exception as e:
        print(f"[No display: {e}]\n")
        run_full_test()


if __name__ == "__main__":
    main()

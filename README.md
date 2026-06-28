# 🎮 Battle City AI

A Python/Pygame recreation of the classic Battle City game with a fully AI-driven enemy system, built as part of the AL2002 Artificial Intelligence course at NUCES FAST.

## 🤖 AI Modules Implemented

### Module A — CSP Map Generator
- Procedurally generates game maps using **Constraint Satisfaction Problem (CSP)** with Backtracking Search + Forward Checking
- Constraints: Eagle safety, spawn reachability (BFS), spawn fairness, density balance, water safety

### Module B — Search Algorithms (3 Tank Types)
| Tank | Algorithm | Behaviour |
|------|-----------|-----------|
| Basic Tank | BFS (Breadth-First Search) | Finds shortest hop path |
| Fast Tank | Greedy Best-First | Rushes toward goal using Manhattan heuristic |
| Armor Tank | A* Search | Cost-aware pathing; shoots through thin brick walls |

### Module C — Adversarial AI (Boss Fight)
- Boss tank uses **Minimax with Alpha-Beta Pruning**
- Search depth increases with boss HP phases (depth 2 → 3 → 4)
- Alpha-Beta reduces search from O(b^d) to O(b^(d/2))

## 🛠️ Tech Stack
- Python 3.13
- Pygame
- AI: CSP, BFS, Greedy Best-First, A*, Minimax + Alpha-Beta Pruning

## 🚀 How to Run

```bash
pip install pygame
python main.py          # Level 1 (Brick Maze)
python main.py 2        # Level 2 (Steel Fortress)
python main.py boss     # Boss Level (Minimax AI)
python main.py test     # Headless logic test (no pygame)
```

## 📁 Project Structure
```
BattleCity/
├── main.py           # Entry point
├── game.py           # Main game loop
├── map_generator.py  # Module A: CSP map generation
├── search.py         # Module B: BFS, Greedy, A* algorithms
├── minimax.py        # Module C: Minimax + Alpha-Beta pruning
├── tanks.py          # Tank types and agent logic
├── boss_tank.py      # Boss tank AI
├── bullet.py         # Bullet physics
├── renderer.py       # Pygame rendering
└── constants.py      # Game constants and config
```

"""
╔═══════════════════════════════════════════════════════════════╗
║            SERPENT — Configuration & Constants                ║
║         All game settings, colors, modes, and presets        ║
╚═══════════════════════════════════════════════════════════════╝
"""

import os

# ══════════════════════════════════════════════════════════════
#  WINDOW SETTINGS
# ══════════════════════════════════════════════════════════════
WINDOW_WIDTH  = 1000
WINDOW_HEIGHT = 750
FPS = 60
TITLE = "SERPENT — Modern Snake"

# ══════════════════════════════════════════════════════════════
#  GRID SETTINGS
# ══════════════════════════════════════════════════════════════
CELL_SIZE     = 25
GRID_OFFSET_X = 25
GRID_OFFSET_Y = 80
GRID_COLS     = (WINDOW_WIDTH  - 2 * GRID_OFFSET_X) // CELL_SIZE   # 38
GRID_ROWS     = (WINDOW_HEIGHT - GRID_OFFSET_Y - 20) // CELL_SIZE  # 26

PLAY_X = GRID_OFFSET_X
PLAY_Y = GRID_OFFSET_Y
PLAY_W = GRID_COLS * CELL_SIZE
PLAY_H = GRID_ROWS * CELL_SIZE

# ══════════════════════════════════════════════════════════════
#  COLOR PALETTE
# ══════════════════════════════════════════════════════════════
class C:
    """Centralised colour constants (dark-theme palette)."""
    # Backgrounds
    BG           = (8,   8,  18)
    BG_PANEL     = (14, 14,  28)
    BG_GRID      = (10, 10,  20)
    GRID_LINE    = (20, 20,  36)
    GRID_CHECKER = (13, 13,  25)

    # Text
    WHITE = (240, 240, 252)
    GRAY  = (140, 140, 165)
    DIM   = (70,  70,  95)

    # Accents
    BLUE   = (60,  130, 255)
    CYAN   = (0,   210, 255)
    GREEN  = (50,  230, 100)
    RED    = (255, 55,  55)
    GOLD   = (255, 195, 40)
    PURPLE = (155, 70,  255)
    PINK   = (255, 60,  140)
    ORANGE = (255, 130, 20)

    # Food
    FOOD       = (255, 65,  65)
    FOOD_GLOW  = (255, 30,  30)
    BONUS      = (255, 210, 0)
    BONUS_GLOW = (255, 180, 0)

    # UI
    BTN          = (28, 28, 52)
    BTN_HOVER    = (42, 42, 72)
    BTN_BORDER   = (55, 55, 90)
    BTN_ACTIVE   = (60, 130, 255)
    OBSTACLE     = (50, 50, 75)
    OBS_BORDER   = (70, 70, 100)

# ══════════════════════════════════════════════════════════════
#  SNAKE COLOUR PRESETS
# ══════════════════════════════════════════════════════════════
SNAKE_PRESETS = [
    {"name": "Neon Green",    "head": (57,  255, 20),  "body": (35,  185, 12),  "glow": (57,  255, 20)},
    {"name": "Cyber Blue",    "head": (0,   195, 255), "body": (0,   130, 200), "glow": (0,   195, 255)},
    {"name": "Flame Red",     "head": (255, 55,  45),  "body": (195, 35,  30),  "glow": (255, 55,  45)},
    {"name": "Purple Haze",   "head": (175, 75,  255), "body": (120, 45,  195), "glow": (175, 75,  255)},
    {"name": "Solar Gold",    "head": (255, 195, 0),   "body": (215, 155, 0),   "glow": (255, 195, 0)},
    {"name": "Hot Pink",      "head": (255, 45,  145), "body": (195, 30,  115), "glow": (255, 45,  145)},
    {"name": "Toxic Orange",  "head": (255, 135, 0),   "body": (215, 95,  0),   "glow": (255, 135, 0)},
    {"name": "Arctic White",  "head": (215, 230, 255), "body": (175, 190, 215), "glow": (200, 215, 255)},
    {"name": "Emerald",       "head": (0,   195, 115), "body": (0,   150, 85),  "glow": (0,   195, 115)},
    {"name": "Coral",         "head": (255, 110, 97),  "body": (215, 80,  70),  "glow": (255, 110, 97)},
    {"name": "Teal",          "head": (0,   210, 190), "body": (0,   160, 145), "glow": (0,   210, 190)},
    {"name": "Lavender",      "head": (180, 140, 255), "body": (140, 100, 215), "glow": (180, 140, 255)},
]

# ══════════════════════════════════════════════════════════════
#  GAME MODES
# ══════════════════════════════════════════════════════════════
GAME_MODES = [
    {
        "id": "classic",     "name": "Classic",
        "desc": "Traditional snake. Walls and self-collision end the game.",
        "walls_kill": True,  "speed_up": False,
        "obstacles": False,  "wrap": False,  "immortal": False,
    },
    {
        "id": "borderless",  "name": "Borderless",
        "desc": "No walls — snake wraps around screen edges seamlessly.",
        "walls_kill": False, "speed_up": False,
        "obstacles": False,  "wrap": True,   "immortal": False,
    },
    {
        "id": "speed_rush",  "name": "Speed Rush",
        "desc": "Speed increases with every food. How fast can you survive?",
        "walls_kill": True,  "speed_up": True,
        "obstacles": False,  "wrap": False,  "immortal": False,
    },
    {
        "id": "maze",        "name": "Maze Runner",
        "desc": "Navigate through obstacles. Plan your moves carefully!",
        "walls_kill": True,  "speed_up": False,
        "obstacles": True,   "wrap": False,  "immortal": False,
    },
    {
        "id": "zen",         "name": "Zen Mode",
        "desc": "No death, no pressure. Relax and enjoy the experience.",
        "walls_kill": False, "speed_up": False,
        "obstacles": False,  "wrap": True,   "immortal": True,
    },
]

# ══════════════════════════════════════════════════════════════
#  GAMEPLAY CONSTANTS
# ══════════════════════════════════════════════════════════════
BASE_MOVE_INTERVAL       = 115     # ms between moves
MIN_MOVE_INTERVAL        = 42
SPEED_DECREASE_PER_FOOD  = 2.5    # ms faster per food in Speed Rush
INITIAL_SNAKE_LENGTH     = 4

# ══════════════════════════════════════════════════════════════
#  FIELD SIZE PRESETS
# ══════════════════════════════════════════════════════════════
FIELD_PRESETS = [
    {"name": "Compact",  "cols": 20, "rows": 14, "desc": "Small field, big cells"},
    {"name": "Standard", "cols": 30, "rows": 20, "desc": "Balanced play area"},
    {"name": "Large",    "cols": 38, "rows": 26, "desc": "Default experience"},
    {"name": "Ultra",    "cols": 50, "rows": 34, "desc": "Massive playground"},
]
DEFAULT_FIELD_IDX = 2   # "Large"

FIELD_MIN_COLS, FIELD_MAX_COLS = 10, 60
FIELD_MIN_ROWS, FIELD_MAX_ROWS = 8,  40

# Directions  (dx, dy)
DIR_UP    = ( 0, -1)
DIR_DOWN  = ( 0,  1)
DIR_LEFT  = (-1,  0)
DIR_RIGHT = ( 1,  0)

# ══════════════════════════════════════════════════════════════
#  FILE PATHS
# ══════════════════════════════════════════════════════════════
_DIR = os.path.dirname(os.path.abspath(__file__))
SCORES_FILE = os.path.join(_DIR, "high_scores.json")

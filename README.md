# 🐍 SERPENT — Modern Snake Game

A professional, feature-rich Snake game built with **Python** and **Pygame**, featuring multiple game modes, full colour customisation, dynamic field sizing, particle effects, and procedurally generated audio.

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Pygame 2.5+](https://img.shields.io/badge/Pygame-2.5%2B-green?logo=pygame)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
[![CI](https://github.com/nishchaysharma/serpent-snake-game/actions/workflows/ci.yml/badge.svg)](https://github.com/nishchaysharma/serpent-snake-game/actions/workflows/ci.yml)

---

## ✨ Features

### 🎮 Five Game Modes
| Mode | Description |
|------|-------------|
| **Classic** | Traditional snake — walls and self-collision end the game |
| **Borderless** | No walls — snake wraps around screen edges seamlessly |
| **Speed Rush** | Speed increases with every food eaten. How fast can you go? |
| **Maze Runner** | Navigate through procedurally generated obstacles |
| **Zen Mode** | Immortal, no-pressure gameplay — just relax |

### 🎨 Full Snake Customisation
- **12 built-in colour presets** — Neon Green, Cyber Blue, Flame Red, Purple Haze, Solar Gold, Hot Pink, Toxic Orange, Arctic White, Emerald, Coral, Teal, Lavender
- **Custom RGB colour picker** with interactive sliders
- Live animated snake preview

### 📐 Dynamic Field Size
- **4 presets**: Compact (20×14), Standard (30×20), Large (38×26), Ultra (50×34)
- **Custom dimensions** via sliders: Width 10–60, Height 8–40
- Cell size auto-scales to fit the window
- Live mini-preview of the grid proportions

### 🎆 Visual Effects
- Particle burst on food collection (colour-matched glow)
- Head trail particles while moving
- Screen shake on death with 40-particle explosion
- Pulsating food with glow halos
- Snake gradient body with animated eyes tracking direction
- Background star field with twinkling animation
- Hover-reactive buttons with scale/glow transitions
- Smooth fade-in screen transitions

### 🔊 Procedural Audio
- Synthesised sound effects (eat, bonus, death, UI select/hover) generated at runtime via **NumPy** — no external audio files needed

### 💾 Persistent High Scores
- Per-mode high score tracking saved to `high_scores.json`

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** ([download](https://www.python.org/downloads/))

### Installation

```bash
# Clone the repository
git clone https://github.com/nishchaysharma/serpent-snake-game.git
cd serpent-snake-game

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Windows (Command Prompt):
venv\Scripts\activate.bat

# macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Game

```bash
python main.py
```

### 🧪 Run Tests

Run the headless unit test suite without needing a display or soundcard:

```bash
python -m unittest discover -s tests
```

---

## 🎮 Controls

| Key | Action |
|-----|--------|
| `↑` `↓` `←` `→` / `W` `A` `S` `D` | Move snake |
| `SPACE` / `ESC` | Pause / Resume |
| `R` | Restart (on game-over screen) |
| Mouse | Navigate menus, pick colours, adjust sliders |

---

## 📁 Project Structure

```
snake_game/
├── .github/
│   ├── workflows/
│   │   └── ci.yml               # GitHub Actions CI workflow
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md        # GitHub bug report template
│       └── feature_request.md   # GitHub feature request template
├── tests/
│   ├── __init__.py
│   └── test_game.py             # Headless unit test suite
├── main.py                      # Game application — engine, rendering, UI, effects, audio
├── config.py                    # All constants — window, grid, colours, modes, presets
├── pyproject.toml               # Package configuration & metadata
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git exclusions
├── CONTRIBUTING.md              # Contribution guidelines
├── LICENSE                      # MIT License
└── README.md                    # Project documentation
```

---

## 🛠️ Tech Stack

| Library | Purpose |
|---------|---------|
| [Pygame](https://www.pygame.org/) | Game engine — rendering, input, window management |
| [NumPy](https://numpy.org/) | Procedural audio synthesis, math operations |
| `colorsys` | HSV/RGB colour space conversions |
| `json` | High-score persistence |
| `enum` | State machine for game screens |

---

## 📸 Screens

1. **Main Menu** — Animated title with glow bloom, mode/skin/field info
2. **Game Modes** — 5 selectable modes with descriptions
3. **Field Size** — 4 presets + custom slider with live preview
4. **Snake Skin** — 12 colour swatches + custom RGB picker with preview
5. **Gameplay** — HUD with score, best, mode, length, timer
6. **Pause** — Overlay with resume, restart, quit options
7. **Game Over** — Score, stats, new high-score celebration

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

<p align="center">
  Made with 🐍 and ❤️
</p>

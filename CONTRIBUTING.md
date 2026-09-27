# Contributing to SERPENT 🐍

Thank you for considering contributing to **SERPENT**! Contributions from the community help keep this game polished, fun, and bug-free.

---

## 🛠️ Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/nishchaysharma/serpent-snake-game.git
   cd serpent-snake-game
   ```

2. **Create and activate a virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt):**
     ```cmd
     python -m venv venv
     venv\Scripts\activate.bat
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the game locally:**
   ```bash
   python main.py
   ```

---

## 🧪 Running Tests

SERPENT includes headless unit tests that don't require an attached monitor or audio device:

```bash
# Run tests using Python's built-in test runner
python -m unittest discover -s tests
```

Ensure all tests pass before submitting a pull request.

---

## 🌿 Contribution Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-cool-feature
   ```
2. Make your improvements with clear code comments and PEP 8 formatting.
3. Test your changes manually and run `python -m unittest discover -s tests`.
4. Commit your changes with descriptive commit messages:
   ```bash
   git commit -m "Add new game mode: Time Attack"
   ```
5. Push to your fork:
   ```bash
   git push origin feature/my-cool-feature
   ```
6. Open a Pull Request against the `main` branch.

---

## 📜 Code of Conduct

Please be respectful and constructive in all issue discussions and pull request reviews.

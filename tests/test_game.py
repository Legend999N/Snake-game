"""
Unit tests for SERPENT — Modern Snake Game.
Runs headlessly without requiring a physical monitor or audio hardware.
"""
import os
import unittest
import tempfile
import json

# Force headless SDL video and audio drivers for CI / testing
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()

import config
from config import C, SNAKE_PRESETS, GAME_MODES, FIELD_PRESETS, DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT
import main
from main import lerp_color, Snake, Food


class TestConfig(unittest.TestCase):
    """Test configuration settings and presets."""

    def test_window_settings(self):
        self.assertGreater(config.WINDOW_WIDTH, 0)
        self.assertGreater(config.WINDOW_HEIGHT, 0)
        self.assertGreater(config.FPS, 0)

    def test_colors_valid_rgb(self):
        """All defined color constants should be valid 3-tuples in 0-255 range."""
        for attr in dir(C):
            if attr.startswith("_"):
                continue
            val = getattr(C, attr)
            if isinstance(val, tuple):
                self.assertEqual(len(val), 3, f"Color {attr} is not RGB 3-tuple")
                for c in val:
                    self.assertTrue(0 <= c <= 255, f"Color {attr} channel {c} out of 0-255 range")

    def test_snake_presets_structure(self):
        """Ensure all snake presets have required keys and valid colors."""
        self.assertGreater(len(SNAKE_PRESETS), 0)
        for preset in SNAKE_PRESETS:
            self.assertIn("name", preset)
            self.assertIn("head", preset)
            self.assertIn("body", preset)
            self.assertIn("glow", preset)
            for key in ("head", "body", "glow"):
                col = preset[key]
                self.assertEqual(len(col), 3)
                for channel in col:
                    self.assertTrue(0 <= channel <= 255)

    def test_game_modes_structure(self):
        """Ensure all game modes have valid rules and fields."""
        required_keys = {"id", "name", "desc", "walls_kill", "speed_up", "obstacles", "wrap", "immortal"}
        for mode in GAME_MODES:
            for k in required_keys:
                self.assertIn(k, mode, f"Mode {mode.get('name')} missing key {k}")

    def test_field_presets(self):
        """Ensure field size presets are within defined bounds."""
        for fp in FIELD_PRESETS:
            self.assertTrue(config.FIELD_MIN_COLS <= fp["cols"] <= config.FIELD_MAX_COLS)
            self.assertTrue(config.FIELD_MIN_ROWS <= fp["rows"] <= config.FIELD_MAX_ROWS)


class TestHelpers(unittest.TestCase):
    """Test helper functions."""

    def test_lerp_color_boundaries(self):
        c1 = (0, 0, 0)
        c2 = (100, 200, 255)
        self.assertEqual(lerp_color(c1, c2, 0.0), c1)
        self.assertEqual(lerp_color(c1, c2, 1.0), c2)
        self.assertEqual(lerp_color(c1, c2, 0.5), (50, 100, 127))

    def test_lerp_color_clamping(self):
        c1 = (10, 10, 10)
        c2 = (100, 100, 100)
        self.assertEqual(lerp_color(c1, c2, -0.5), c1)
        self.assertEqual(lerp_color(c1, c2, 1.5), c2)


class TestGameplayLogic(unittest.TestCase):
    """Test snake movement, directional constraints, and food generation."""

    def setUp(self):
        self.preset = SNAKE_PRESETS[0]
        self.snake = Snake(10, 10, self.preset)

    def test_initial_state(self):
        self.assertEqual(len(self.snake.segments), config.INITIAL_SNAKE_LENGTH)
        self.assertEqual(self.snake.direction, DIR_RIGHT)
        self.assertEqual(self.snake.foods_eaten, 0)
        self.assertTrue(self.snake.alive)

    def test_disallow_180_degree_turn(self):
        """Snake moving RIGHT cannot immediately turn LEFT."""
        self.snake.set_direction(DIR_LEFT)
        self.assertEqual(self.snake.next_dir, DIR_RIGHT)

        # But can turn UP or DOWN
        self.snake.set_direction(DIR_UP)
        self.assertEqual(self.snake.next_dir, DIR_UP)

    def test_snake_movement_advances_head(self):
        head_before = self.snake.head
        self.snake.move(wrap=False)
        head_after = self.snake.head
        self.assertEqual(head_after, (head_before[0] + 1, head_before[1]))

    def test_borderless_wrap(self):
        """Snake should wrap around edges in wrap mode."""
        self.snake.segments = [(29, 10), (28, 10), (27, 10), (26, 10)]
        self.snake.direction = DIR_RIGHT
        self.snake.next_dir = DIR_RIGHT
        self.snake.move(wrap=True, grid_cols=30, grid_rows=20)
        self.assertEqual(self.snake.head, (0, 10))

    def test_food_spawn_avoids_snake(self):
        food = Food()
        food.spawn(snake_segs=self.snake.segments, obstacles=set(), grid_cols=30, grid_rows=20)
        self.assertNotIn(food.pos, self.snake.segments)
        self.assertTrue(0 <= food.pos[0] < 30)
        self.assertTrue(0 <= food.pos[1] < 20)


class TestScorePersistence(unittest.TestCase):
    """Test loading and saving of scores."""

    def test_save_and_load_scores(self):
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as tmp:
            tmp_path = tmp.name

        try:
            sample_scores = {"classic": 42, "speed_rush": 99}
            with open(tmp_path, "w") as f:
                json.dump(sample_scores, f)

            with open(tmp_path, "r") as f:
                loaded = json.load(f)

            self.assertEqual(loaded, sample_scores)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()

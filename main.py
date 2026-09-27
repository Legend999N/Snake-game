#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║                 SERPENT — Modern Snake Game                   ║
║                                                               ║
║   A professional, feature-rich snake game built with Pygame.  ║
║   Features: 5 game modes · 12+ colour presets · custom RGB   ║
║   colour picker · particle effects · procedural audio ·      ║
║   screen-shake · animated menus · persistent high-scores     ║
╚═══════════════════════════════════════════════════════════════╝

Controls:
    Arrow Keys / WASD  —  Move snake
    SPACE / ESC        —  Pause
    R                  —  Restart (game-over screen)
    ENTER              —  Confirm / Select
"""

# ═══════════════════════════════════════════════════════════════
#  IMPORTS
# ═══════════════════════════════════════════════════════════════
import warnings
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")

import pygame
import sys
import math
import random
import json
import colorsys
from enum import Enum, auto

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, TITLE,
    CELL_SIZE, GRID_OFFSET_X, GRID_OFFSET_Y, GRID_COLS, GRID_ROWS,
    PLAY_X, PLAY_Y, PLAY_W, PLAY_H,
    C, SNAKE_PRESETS, GAME_MODES,
    BASE_MOVE_INTERVAL, MIN_MOVE_INTERVAL, SPEED_DECREASE_PER_FOOD,
    INITIAL_SNAKE_LENGTH,
    DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT,
    SCORES_FILE,
    FIELD_PRESETS, DEFAULT_FIELD_IDX,
    FIELD_MIN_COLS, FIELD_MAX_COLS, FIELD_MIN_ROWS, FIELD_MAX_ROWS,
)

# Optional: numpy for procedural audio
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════
def lerp_color(c1, c2, t):
    """Linearly interpolate between two RGB colours."""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_rounded_rect(surface, color, rect, radius, alpha=255):
    """Draw a rounded rectangle, optionally semi-transparent."""
    if alpha >= 255:
        pygame.draw.rect(surface, color, rect, border_radius=radius)
    else:
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color[:3], alpha), s.get_rect(), border_radius=radius)
        surface.blit(s, rect.topleft)


def draw_text_centered(surface, text, font, color, y, x=None):
    """Render centred text; returns the Rect."""
    ts = font.render(text, True, color)
    cx = x if x is not None else WINDOW_WIDTH // 2
    r = ts.get_rect(center=(cx, y))
    surface.blit(ts, r)
    return r


# ═══════════════════════════════════════════════════════════════
#  PROCEDURAL AUDIO
# ═══════════════════════════════════════════════════════════════
class Audio:
    """Procedurally-generated sound effects (no external files)."""

    def __init__(self):
        self.enabled = False
        self.sounds = {}
        if not HAS_NUMPY:
            return
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._generate_sounds()
            self.enabled = True
        except Exception:
            pass

    def _synth(self, freq, dur, vol=0.25, wave="sine", sweep_to=None):
        sr = 44100
        n = int(sr * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        if sweep_to:
            freqs = np.linspace(freq, sweep_to, n)
            phase = 2 * np.pi * np.cumsum(freqs) / sr
        else:
            phase = 2 * np.pi * freq * t
        if wave == "sine":
            w = np.sin(phase)
        elif wave == "square":
            w = np.sign(np.sin(phase))
        elif wave == "saw":
            w = 2 * (phase / (2 * np.pi) % 1) - 1
        else:
            w = np.sin(phase)
        # Envelope: quick attack, smooth release
        env = np.ones(n)
        atk = min(int(0.008 * sr), n)
        rel = min(int(0.4 * dur * sr), n)
        if atk > 0:
            env[:atk] = np.linspace(0, 1, atk)
        if rel > 0:
            env[-rel:] = np.linspace(1, 0, rel)
        w = (w * env * vol * 32767).astype(np.int16)
        stereo = np.column_stack((w, w))
        return pygame.sndarray.make_sound(stereo)

    def _generate_sounds(self):
        self.sounds["eat"]     = self._synth(660, 0.08, 0.20, "sine", 880)
        self.sounds["bonus"]   = self._synth(880, 0.15, 0.22, "sine", 1320)
        self.sounds["die"]     = self._synth(220, 0.35, 0.25, "saw",  80)
        self.sounds["move"]    = self._synth(200, 0.02, 0.04, "square")
        self.sounds["select"]  = self._synth(520, 0.06, 0.12, "sine", 620)
        self.sounds["hover"]   = self._synth(400, 0.03, 0.06, "sine")

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()


# ═══════════════════════════════════════════════════════════════
#  PARTICLE SYSTEM
# ═══════════════════════════════════════════════════════════════
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "color", "life", "max_life",
                 "size", "orig_size", "gravity", "alive")

    def __init__(self, x, y, color, vx, vy, life, size, gravity=0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = self.max_life = life
        self.size = self.orig_size = size
        self.gravity = gravity
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vy += self.gravity * dt * 60
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return
        p = self.life / self.max_life
        self.size = self.orig_size * p

    def draw(self, surface):
        if not self.alive or self.size < 0.5:
            return
        a = int(255 * (self.life / self.max_life))
        sz = max(1, int(self.size))
        d = sz * 2 + 2
        s = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], a), (sz + 1, sz + 1), sz)
        surface.blit(s, (int(self.x - sz - 1), int(self.y - sz - 1)))


class ParticleSystem:
    MAX = 300

    def __init__(self):
        self.particles: list[Particle] = []

    def burst(self, x, y, color, count=12, speed=3.5, life=0.7, size=3.5, gravity=0):
        for _ in range(count):
            a = random.uniform(0, math.tau)
            sp = random.uniform(speed * 0.25, speed)
            self.particles.append(Particle(
                x, y, color,
                math.cos(a) * sp, math.sin(a) * sp,
                random.uniform(life * 0.4, life),
                random.uniform(size * 0.4, size),
                gravity,
            ))
        if len(self.particles) > self.MAX:
            self.particles = self.particles[-self.MAX:]

    def trail(self, x, y, color, count=2, size=2):
        for _ in range(count):
            self.particles.append(Particle(
                x + random.uniform(-3, 3), y + random.uniform(-3, 3), color,
                random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3),
                random.uniform(0.15, 0.35),
                random.uniform(size * 0.3, size),
            ))

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)

    def clear(self):
        self.particles.clear()


# ═══════════════════════════════════════════════════════════════
#  SCREEN SHAKE
# ═══════════════════════════════════════════════════════════════
class ScreenShake:
    def __init__(self):
        self.intensity = 0
        self.duration = 0
        self.timer = 0

    def trigger(self, intensity=10, duration=0.35):
        self.intensity, self.duration, self.timer = intensity, duration, duration

    def update(self, dt):
        if self.timer > 0:
            self.timer = max(0, self.timer - dt)

    def offset(self):
        if self.timer <= 0:
            return 0, 0
        p = self.timer / self.duration
        m = self.intensity * p
        return random.uniform(-m, m), random.uniform(-m, m)


# ═══════════════════════════════════════════════════════════════
#  FLOATING SCORE TEXT
# ═══════════════════════════════════════════════════════════════
class FloatingText:
    def __init__(self, x, y, text, color, font, dur=0.9):
        self.x, self.y = x, y
        self.text, self.color, self.font = text, color, font
        self.dur = self.timer = dur
        self.alive = True

    def update(self, dt):
        self.y -= 50 * dt
        self.timer -= dt
        if self.timer <= 0:
            self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        a = int(255 * (self.timer / self.dur))
        ts = self.font.render(self.text, True, self.color)
        ts.set_alpha(a)
        surface.blit(ts, (self.x - ts.get_width() // 2, int(self.y)))


# ═══════════════════════════════════════════════════════════════
#  SNAKE ENTITY
# ═══════════════════════════════════════════════════════════════
class Snake:
    def __init__(self, sx, sy, preset):
        self.segments = [(sx - i, sy) for i in range(INITIAL_SNAKE_LENGTH)]
        self.direction = DIR_RIGHT
        self.next_dir = DIR_RIGHT
        self.color = preset
        self.alive = True
        self.grow_pending = 0
        self.score = 0
        self.foods_eaten = 0

    @property
    def head(self):
        return self.segments[0]

    # ── movement ───────────────────────────────────────────────
    def set_direction(self, d):
        if (d[0] + self.direction[0], d[1] + self.direction[1]) != (0, 0):
            self.next_dir = d

    def move(self, wrap=False, grid_cols=GRID_COLS, grid_rows=GRID_ROWS):
        self.direction = self.next_dir
        hx, hy = self.head
        nx, ny = hx + self.direction[0], hy + self.direction[1]
        if wrap:
            nx %= grid_cols
            ny %= grid_rows
        self.segments.insert(0, (nx, ny))
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.segments.pop()

    def grow(self, n=1):
        self.grow_pending += n

    # ── collisions ─────────────────────────────────────────────
    def hit_self(self):
        return self.head in self.segments[1:]

    def hit_wall(self, grid_cols=GRID_COLS, grid_rows=GRID_ROWS):
        hx, hy = self.head
        return hx < 0 or hx >= grid_cols or hy < 0 or hy >= grid_rows

    def hit_obstacles(self, obs):
        return self.head in obs

    # ── rendering ──────────────────────────────────────────────
    def draw(self, surface, ox, oy, cs):
        n = max(len(self.segments) - 1, 1)
        for i in range(len(self.segments) - 1, -1, -1):
            sx, sy = self.segments[i]
            px, py = ox + sx * cs, oy + sy * cs
            t = 1.0 - i / n
            col = lerp_color(self.color["body"], self.color["head"], t)
            m = 1
            rect = pygame.Rect(px + m, py + m, cs - 2 * m, cs - 2 * m)
            r = 7 if i == 0 else (5 if i < 3 else 3)
            pygame.draw.rect(surface, col, rect, border_radius=r)
            # Subtle highlight on top edge
            highlight = lerp_color(col, (255, 255, 255), 0.15)
            hr = pygame.Rect(px + m + 2, py + m, cs - 2 * m - 4, max(1, cs // 6))
            draw_rounded_rect(surface, highlight, hr, 2, alpha=40)

        # Head glow
        hx, hy = self.head
        gpx, gpy = ox + hx * cs + cs // 2, oy + hy * cs + cs // 2
        gs = int(cs * 1.8)
        gsf = pygame.Surface((gs * 2, gs * 2), pygame.SRCALPHA)
        pygame.draw.circle(gsf, (*self.color["glow"][:3], 22), (gs, gs), gs)
        surface.blit(gsf, (gpx - gs, gpy - gs))

        # Eyes
        self._draw_eyes(surface, ox + hx * cs, oy + hy * cs, cs)

    def _draw_eyes(self, surface, px, py, cs):
        eye_w, pupil_w = max(3, cs // 5), max(1, cs // 10)
        cx, cy = px + cs // 2, py + cs // 2
        off = cs // 4
        dx, dy = self.direction
        positions = {
            DIR_RIGHT: ((cx + off, cy - off), (cx + off, cy + off)),
            DIR_LEFT:  ((cx - off, cy - off), (cx - off, cy + off)),
            DIR_UP:    ((cx - off, cy - off), (cx + off, cy - off)),
            DIR_DOWN:  ((cx - off, cy + off), (cx + off, cy + off)),
        }
        e1, e2 = positions.get(self.direction, positions[DIR_RIGHT])
        pd = (dx * pupil_w, dy * pupil_w)
        for ex, ey in (e1, e2):
            pygame.draw.circle(surface, (255, 255, 255), (ex, ey), eye_w)
            pygame.draw.circle(surface, (15, 15, 25), (ex + pd[0], ey + pd[1]), pupil_w)


# ═══════════════════════════════════════════════════════════════
#  FOOD ENTITY
# ═══════════════════════════════════════════════════════════════
class Food:
    def __init__(self):
        self.pos = (0, 0)
        self.is_bonus = False
        self.pulse = 0.0
        self.spawn_t = 0.0
        self.sparkle_timer = 0.0

    def spawn(self, snake_segs, obstacles=None, grid_cols=GRID_COLS, grid_rows=GRID_ROWS):
        occupied = set(snake_segs)
        if obstacles:
            occupied |= obstacles
        avail = [(x, y) for x in range(grid_cols)
                 for y in range(grid_rows) if (x, y) not in occupied]
        if avail:
            self.pos = random.choice(avail)
        self.is_bonus = random.random() < 0.12
        self.spawn_t = 0.0

    def update(self, dt):
        self.pulse += dt * 3.5
        self.spawn_t = min(1.0, self.spawn_t + dt * 5)
        self.sparkle_timer += dt

    def draw(self, surface, ox, oy, cs):
        fx, fy = ox + self.pos[0] * cs + cs // 2, oy + self.pos[1] * cs + cs // 2
        s = self.spawn_t
        p = 1 + math.sin(self.pulse) * 0.12
        radius = max(1, int((cs // 2 - 2) * s * p))
        col  = C.BONUS if self.is_bonus else C.FOOD
        glow = C.BONUS_GLOW if self.is_bonus else C.FOOD_GLOW
        # Glow
        gs = int(radius * 2.8)
        gsf = pygame.Surface((gs * 2, gs * 2), pygame.SRCALPHA)
        ga = int(35 + 18 * math.sin(self.pulse))
        pygame.draw.circle(gsf, (*glow[:3], ga), (gs, gs), gs)
        surface.blit(gsf, (fx - gs, fy - gs))
        # Body
        pygame.draw.circle(surface, col, (fx, fy), radius)
        # Highlight
        hl = tuple(min(255, c + 70) for c in col)
        hr = max(1, int(radius * 0.35))
        pygame.draw.circle(surface, hl, (fx - radius // 3, fy - radius // 3), hr)


# ═══════════════════════════════════════════════════════════════
#  OBSTACLE / MAZE GENERATION
# ═══════════════════════════════════════════════════════════════
def generate_obstacles(snake_start, level=1, grid_cols=GRID_COLS, grid_rows=GRID_ROWS):
    """Create maze obstacles ensuring clear area around the snake start."""
    obs = set()
    sx, sy = snake_start
    clear = {(sx + dx, sy + dy) for dx in range(-6, 7) for dy in range(-4, 5)}

    patterns = [
        lambda x, y: [(x + i, y) for i in range(random.randint(3, 7))],
        lambda x, y: [(x, y + i) for i in range(random.randint(3, 7))],
        lambda x, y: [(x + i, y) for i in range(4)] + [(x, y + i) for i in range(1, 4)],
        lambda x, y: [(x + i, y) for i in range(3)] + [(x + 2, y + i) for i in range(1, 3)],
        lambda x, y: [(x + dx, y + dy) for dx in range(2) for dy in range(2)],
    ]
    count = 8 + level * 4
    for _ in range(count):
        pat = random.choice(patterns)
        px = random.randint(1, max(2, grid_cols - 8))
        py = random.randint(1, max(2, grid_rows - 8))
        cells = pat(px, py)
        if any(c in clear for c in cells):
            continue
        for c in cells:
            if 0 <= c[0] < grid_cols and 0 <= c[1] < grid_rows:
                obs.add(c)
    return obs


# ═══════════════════════════════════════════════════════════════
#  UI: BUTTON
# ═══════════════════════════════════════════════════════════════
class Button:
    def __init__(self, x, y, w, h, text, font, *, 
                 bg=C.BTN, hover_bg=C.BTN_HOVER, border=C.BTN_BORDER,
                 text_col=C.WHITE, active_border=C.BTN_ACTIVE, radius=12):
        self.rect = pygame.Rect(x, y, w, h)
        self.text, self.font = text, font
        self.bg, self.hover_bg, self.border = bg, hover_bg, border
        self.text_col, self.active_border = text_col, active_border
        self.radius = radius
        self.hover_t = 0.0
        self.click_t = 0.0

    def update(self, mpos, dt):
        target = 1.0 if self.rect.collidepoint(mpos) else 0.0
        self.hover_t += (target - self.hover_t) * min(1, dt * 12)
        self.click_t = max(0, self.click_t - dt * 6)

    def draw(self, surface):
        t = self.hover_t
        bg = lerp_color(self.bg, self.hover_bg, t)
        sc = 1 + t * 0.018 - self.click_t * 0.04
        w, h = int(self.rect.w * sc), int(self.rect.h * sc)
        x = self.rect.centerx - w // 2
        y = self.rect.centery - h // 2
        dr = pygame.Rect(x, y, w, h)
        # Shadow
        ss = pygame.Surface((w + 4, h + 6), pygame.SRCALPHA)
        pygame.draw.rect(ss, (0, 0, 0, 35), (2, 4, w, h), border_radius=self.radius)
        surface.blit(ss, (x - 2, y - 2))
        # BG
        pygame.draw.rect(surface, bg, dr, border_radius=self.radius)
        # Border
        ba = int(70 + 60 * t)
        bs = pygame.Surface((w, h), pygame.SRCALPHA)
        bc = self.active_border if t > 0.5 else self.border
        pygame.draw.rect(bs, (*bc[:3], ba), (0, 0, w, h), width=1, border_radius=self.radius)
        surface.blit(bs, dr.topleft)
        # Text
        ts = self.font.render(self.text, True, self.text_col)
        surface.blit(ts, (dr.centerx - ts.get_width() // 2,
                          dr.centery - ts.get_height() // 2))

    def clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.click_t = 1.0
                return True
        return False


# ═══════════════════════════════════════════════════════════════
#  UI: COLOUR SWATCH
# ═══════════════════════════════════════════════════════════════
class ColorSwatch:
    def __init__(self, cx, cy, r, preset, idx):
        self.cx, self.cy, self.r = cx, cy, r
        self.preset, self.idx = preset, idx
        self.rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        self.hover_t = 0.0
        self.selected = False

    def update(self, mpos, dt):
        hovered = self.rect.collidepoint(mpos)
        target = 1.0 if (hovered or self.selected) else 0.0
        self.hover_t += (target - self.hover_t) * min(1, dt * 10)

    def draw(self, surface):
        t = self.hover_t
        sz = int(self.r * (1 + t * 0.12))
        # Glow
        if t > 0.05 or self.selected:
            gs = int(sz * 1.8)
            gsf = pygame.Surface((gs * 2, gs * 2), pygame.SRCALPHA)
            ga = int(40 * t)
            pygame.draw.circle(gsf, (*self.preset["glow"][:3], ga), (gs, gs), gs)
            surface.blit(gsf, (self.cx - gs, self.cy - gs))
        # Outer
        pygame.draw.circle(surface, self.preset["head"], (self.cx, self.cy), sz)
        # Inner
        pygame.draw.circle(surface, self.preset["body"], (self.cx, self.cy), int(sz * 0.55))
        # Ring
        if self.selected:
            pygame.draw.circle(surface, (255, 255, 255), (self.cx, self.cy), sz + 3, width=2)

    def clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


# ═══════════════════════════════════════════════════════════════
#  UI: RGB SLIDER (Custom Colour)
# ═══════════════════════════════════════════════════════════════
class RGBSlider:
    """Simple horizontal slider for an R, G, or B channel."""
    def __init__(self, x, y, w, label, channel_color, value=128):
        self.rect = pygame.Rect(x, y, w, 22)
        self.label = label
        self.channel_color = channel_color
        self.value = value
        self.dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])

    def _set_from_x(self, mx):
        t = (mx - self.rect.x) / self.rect.w
        self.value = int(max(0, min(255, t * 255)))

    def draw(self, surface, font):
        # Track
        pygame.draw.rect(surface, (30, 30, 50), self.rect, border_radius=4)
        # Filled portion
        fw = int(self.rect.w * self.value / 255)
        fr = pygame.Rect(self.rect.x, self.rect.y, fw, self.rect.h)
        pygame.draw.rect(surface, self.channel_color, fr, border_radius=4)
        # Thumb
        tx = self.rect.x + fw
        pygame.draw.circle(surface, (255, 255, 255), (tx, self.rect.centery), 8)
        pygame.draw.circle(surface, self.channel_color, (tx, self.rect.centery), 5)
        # Label
        ls = font.render(f"{self.label}: {self.value}", True, C.WHITE)
        surface.blit(ls, (self.rect.x, self.rect.y - 18))


# ═══════════════════════════════════════════════════════════════
#  UI: INTEGER SLIDER  (for field-size customisation)
# ═══════════════════════════════════════════════════════════════
class IntSlider:
    """Horizontal slider that maps to an integer range [lo, hi]."""
    def __init__(self, x, y, w, label, lo, hi, value, bar_color=C.CYAN):
        self.rect = pygame.Rect(x, y, w, 22)
        self.label = label
        self.lo, self.hi = lo, hi
        self.value = max(lo, min(hi, value))
        self.bar_color = bar_color
        self.dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = self.rect.inflate(0, 16)
            if hit.collidepoint(event.pos):
                self.dragging = True
                self._set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])

    def _set_from_x(self, mx):
        t = (mx - self.rect.x) / max(1, self.rect.w)
        t = max(0.0, min(1.0, t))
        self.value = int(self.lo + t * (self.hi - self.lo))

    def draw(self, surface, font):
        # Track bg
        pygame.draw.rect(surface, (30, 30, 50), self.rect, border_radius=4)
        # Filled
        frac = (self.value - self.lo) / max(1, self.hi - self.lo)
        fw = int(self.rect.w * frac)
        fr = pygame.Rect(self.rect.x, self.rect.y, fw, self.rect.h)
        pygame.draw.rect(surface, self.bar_color, fr, border_radius=4)
        # Thumb
        tx = self.rect.x + fw
        pygame.draw.circle(surface, (255, 255, 255), (tx, self.rect.centery), 9)
        pygame.draw.circle(surface, self.bar_color, (tx, self.rect.centery), 6)
        # Label
        ls = font.render(f"{self.label}: {self.value}", True, C.WHITE)
        surface.blit(ls, (self.rect.x, self.rect.y - 18))


# ═══════════════════════════════════════════════════════════════
#  GAME STATES
# ═══════════════════════════════════════════════════════════════
class State(Enum):
    MENU         = auto()
    MODE_SELECT  = auto()
    FIELD_SIZE   = auto()
    COLOR_SELECT = auto()
    PLAYING      = auto()
    PAUSED       = auto()
    GAME_OVER    = auto()


# ═══════════════════════════════════════════════════════════════
#  ★  MAIN APPLICATION  ★
# ═══════════════════════════════════════════════════════════════
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        # Fonts
        self._load_fonts()

        # Audio
        self.audio = Audio()

        # Systems
        self.particles = ParticleSystem()
        self.shake = ScreenShake()
        self.floats: list[FloatingText] = []

        # State
        self.state = State.MENU
        self.selected_mode = GAME_MODES[0]
        self.selected_color = SNAKE_PRESETS[0]
        self.custom_color_active = False

        # ── Dynamic grid dimensions ────────────────────────────
        default = FIELD_PRESETS[DEFAULT_FIELD_IDX]
        self.grid_cols = default["cols"]
        self.grid_rows = default["rows"]
        self.field_preset_idx = DEFAULT_FIELD_IDX
        self.field_custom = False          # True when using custom sliders
        self._recalc_grid()                # sets cell_size, play_x/y/w/h

        # Game objects (created on play)
        self.snake: Snake | None = None
        self.food: Food | None = None
        self.obstacles: set = set()
        self.move_timer = 0.0
        self.move_interval = BASE_MOVE_INTERVAL
        self.game_time = 0.0

        # Background decoration
        self.bg_stars = [(random.randint(0, WINDOW_WIDTH),
                          random.randint(0, WINDOW_HEIGHT),
                          random.uniform(0.3, 1.5),
                          random.uniform(0.5, 2.0)) for _ in range(80)]

        # Grid surface (cached)
        self._grid_surface = None
        self._build_grid_surface()

        # High scores
        self.high_scores = self._load_scores()

        # UI elements (built per-screen)
        self._build_menu_ui()
        self._build_mode_ui()
        self._build_color_ui()
        self._build_field_ui()

        # Custom colour sliders
        sx = WINDOW_WIDTH // 2 + 120
        self.rgb_sliders = [
            RGBSlider(sx, 340, 200, "R", (220, 50, 50), 0),
            RGBSlider(sx, 400, 200, "G", (50, 200, 50), 200),
            RGBSlider(sx, 460, 200, "B", (50, 100, 220), 255),
        ]

        # Transition overlay
        self.fade_alpha = 255
        self.fading_in = True

    # ── fonts ──────────────────────────────────────────────────
    def _load_fonts(self):
        names = ["segoeui", "Segoe UI", "arial", "verdana", None]
        for n in names:
            try:
                self.font_title  = pygame.font.SysFont(n, 54, bold=True)
                self.font_large  = pygame.font.SysFont(n, 30, bold=True)
                self.font_medium = pygame.font.SysFont(n, 20)
                self.font_small  = pygame.font.SysFont(n, 15)
                self.font_tiny   = pygame.font.SysFont(n, 12)
                return
            except Exception:
                continue
        # Fallback
        self.font_title  = pygame.font.Font(None, 58)
        self.font_large  = pygame.font.Font(None, 34)
        self.font_medium = pygame.font.Font(None, 22)
        self.font_small  = pygame.font.Font(None, 17)
        self.font_tiny   = pygame.font.Font(None, 14)

    # ── dynamic grid recalculation ─────────────────────────────
    def _recalc_grid(self):
        """Compute cell_size and play-area rect from current grid_cols/grid_rows."""
        avail_w = WINDOW_WIDTH  - 2 * GRID_OFFSET_X
        avail_h = WINDOW_HEIGHT - GRID_OFFSET_Y - 20
        self.cell_size = min(avail_w // self.grid_cols, avail_h // self.grid_rows)
        self.cell_size = max(8, self.cell_size)      # floor at 8 px
        self.play_w = self.grid_cols * self.cell_size
        self.play_h = self.grid_rows * self.cell_size
        self.play_x = (WINDOW_WIDTH  - self.play_w) // 2
        self.play_y = GRID_OFFSET_Y + (avail_h - self.play_h) // 2

    # ── cached grid ────────────────────────────────────────────
    def _build_grid_surface(self):
        cs = self.cell_size
        pw, ph = self.play_w, self.play_h
        self._grid_surface = pygame.Surface((pw, ph))
        self._grid_surface.fill(C.BG_GRID)
        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                if (r + c) % 2 == 0:
                    rect = pygame.Rect(c * cs, r * cs, cs, cs)
                    pygame.draw.rect(self._grid_surface, C.GRID_CHECKER, rect)
        for x in range(0, pw + 1, cs):
            pygame.draw.line(self._grid_surface, C.GRID_LINE, (x, 0), (x, ph))
        for y in range(0, ph + 1, cs):
            pygame.draw.line(self._grid_surface, C.GRID_LINE, (0, y), (pw, ph if y > ph else y))
            pygame.draw.line(self._grid_surface, C.GRID_LINE, (0, y), (pw, y))

    # ── high scores ────────────────────────────────────────────
    def _load_scores(self):
        try:
            with open(SCORES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_scores(self):
        try:
            with open(SCORES_FILE, "w") as f:
                json.dump(self.high_scores, f, indent=2)
        except Exception:
            pass

    def _get_high(self):
        return self.high_scores.get(self.selected_mode["id"], 0)

    def _set_high(self, score):
        mode_id = self.selected_mode["id"]
        if score > self.high_scores.get(mode_id, 0):
            self.high_scores[mode_id] = score
            self._save_scores()
            return True
        return False

    # ══════════════════════════════════════════════════════════
    #  UI BUILDERS
    # ══════════════════════════════════════════════════════════
    def _build_menu_ui(self):
        cx = WINDOW_WIDTH // 2
        bw, bh, gap = 260, 48, 12
        start_y = 320
        self.menu_buttons = [
            Button(cx - bw // 2, start_y,              bw, bh, "Play",       self.font_large),
            Button(cx - bw // 2, start_y + bh + gap,   bw, bh, "Game Modes", self.font_medium),
            Button(cx - bw // 2, start_y + 2*(bh+gap), bw, bh, "Field Size", self.font_medium),
            Button(cx - bw // 2, start_y + 3*(bh+gap), bw, bh, "Snake Skin", self.font_medium),
            Button(cx - bw // 2, start_y + 4*(bh+gap), bw, bh, "Quit",       self.font_medium,
                   border=C.RED),
        ]

    def _build_mode_ui(self):
        self.mode_buttons = []
        cx = WINDOW_WIDTH // 2
        bw, bh, gap = 420, 54, 10
        y = 160
        for i, mode in enumerate(GAME_MODES):
            b = Button(cx - bw // 2, y + i * (bh + gap), bw, bh,
                       f"{mode['name']}  —  {mode['desc'][:42]}",
                       self.font_small)
            self.mode_buttons.append(b)
        by = y + len(GAME_MODES) * (bh + gap) + 20
        self.mode_back_btn = Button(cx - 100, by, 200, 46, "Back", self.font_medium)

    def _build_color_ui(self):
        self.color_swatches = []
        cols_per_row = 6
        swatch_r = 26
        gap = 18
        total_w = cols_per_row * (swatch_r * 2 + gap) - gap
        start_x = WINDOW_WIDTH // 2 - total_w // 2 + swatch_r - 120
        start_y = 200
        for i, preset in enumerate(SNAKE_PRESETS):
            row, col = divmod(i, cols_per_row)
            cx = start_x + col * (swatch_r * 2 + gap) + swatch_r
            cy = start_y + row * (swatch_r * 2 + gap) + swatch_r
            sw = ColorSwatch(cx, cy, swatch_r, preset, i)
            if i == 0:
                sw.selected = True
            self.color_swatches.append(sw)

        self.custom_swatch = Button(
            start_x - swatch_r, start_y + ((len(SNAKE_PRESETS) - 1) // cols_per_row + 1) * (swatch_r * 2 + gap) + 10,
            200, 40, "Custom Color", self.font_small,
        )
        bx = WINDOW_WIDTH // 2 - 100
        self.color_play_btn = Button(bx, WINDOW_HEIGHT - 110, 200, 50, "Start Game", self.font_large,
                                     bg=(20, 60, 20), hover_bg=(30, 90, 30), active_border=C.GREEN)
        self.color_back_btn = Button(bx, WINDOW_HEIGHT - 55, 200, 40, "Back", self.font_medium)

    def _build_field_ui(self):
        cx = WINDOW_WIDTH // 2
        bw, bh, gap = 320, 50, 10
        y0 = 180
        self.field_preset_btns = []
        for i, fp in enumerate(FIELD_PRESETS):
            label = f"{fp['name']}  ({fp['cols']}×{fp['rows']})  —  {fp['desc']}"
            b = Button(cx - bw // 2, y0 + i * (bh + gap), bw, bh, label, self.font_small)
            self.field_preset_btns.append(b)

        # Custom toggle
        cust_y = y0 + len(FIELD_PRESETS) * (bh + gap) + 10
        self.field_custom_btn = Button(cx - bw // 2, cust_y, bw, bh,
                                       "Custom Size", self.font_medium)

        # Sliders (below custom button)
        sl_x = cx - 120
        sl_y = cust_y + bh + 40
        self.field_col_slider = IntSlider(sl_x, sl_y, 240, "Width (cols)",
                                          FIELD_MIN_COLS, FIELD_MAX_COLS,
                                          self.grid_cols, bar_color=C.CYAN)
        self.field_row_slider = IntSlider(sl_x, sl_y + 60, 240, "Height (rows)",
                                          FIELD_MIN_ROWS, FIELD_MAX_ROWS,
                                          self.grid_rows, bar_color=C.PURPLE)

        self.field_back_btn = Button(cx - 100, WINDOW_HEIGHT - 70, 200, 46,
                                     "Back", self.font_medium)

    # ══════════════════════════════════════════════════════════
    #  GAME INITIALISATION
    # ══════════════════════════════════════════════════════════
    def _start_game(self):
        # Rebuild grid for the chosen dimensions
        self._recalc_grid()
        self._build_grid_surface()

        sx, sy = self.grid_cols // 2, self.grid_rows // 2

        # Resolve colour
        if self.custom_color_active:
            r = self.rgb_sliders[0].value
            g = self.rgb_sliders[1].value
            b = self.rgb_sliders[2].value
            head = (r, g, b)
            body = (max(0, r - 50), max(0, g - 50), max(0, b - 50))
            preset = {"name": "Custom", "head": head, "body": body, "glow": head}
        else:
            preset = self.selected_color

        self.snake = Snake(sx, sy, preset)
        self.food = Food()
        self.obstacles = set()
        self.move_timer = 0.0
        self.move_interval = BASE_MOVE_INTERVAL
        self.game_time = 0.0
        self.particles.clear()
        self.floats.clear()
        self.shake = ScreenShake()

        if self.selected_mode.get("obstacles"):
            self.obstacles = generate_obstacles((sx, sy),
                                               grid_cols=self.grid_cols,
                                               grid_rows=self.grid_rows)

        self.food.spawn(self.snake.segments, self.obstacles,
                        grid_cols=self.grid_cols, grid_rows=self.grid_rows)
        self.state = State.PLAYING

    # ══════════════════════════════════════════════════════════
    #  MAIN LOOP
    # ══════════════════════════════════════════════════════════
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)

            self._handle_events()
            self._update(dt)
            self._render()

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    # ── events ─────────────────────────────────────────────────
    def _handle_events(self):
        mpos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            # Delegate to state handler
            if self.state == State.MENU:
                self._event_menu(event)
            elif self.state == State.MODE_SELECT:
                self._event_modes(event)
            elif self.state == State.FIELD_SIZE:
                self._event_field_size(event)
            elif self.state == State.COLOR_SELECT:
                self._event_colors(event)
            elif self.state == State.PLAYING:
                self._event_playing(event)
            elif self.state == State.PAUSED:
                self._event_paused(event)
            elif self.state == State.GAME_OVER:
                self._event_gameover(event)

    def _event_menu(self, event):
        for i, btn in enumerate(self.menu_buttons):
            if btn.clicked(event):
                self.audio.play("select")
                if i == 0:   # Play
                    self.state = State.COLOR_SELECT
                elif i == 1: # Modes
                    self.state = State.MODE_SELECT
                elif i == 2: # Field Size
                    self.state = State.FIELD_SIZE
                elif i == 3: # Skin
                    self.state = State.COLOR_SELECT
                elif i == 4: # Quit
                    self.running = False

    def _event_modes(self, event):
        if self.mode_back_btn.clicked(event):
            self.audio.play("select")
            self.state = State.MENU
            return
        for i, btn in enumerate(self.mode_buttons):
            if btn.clicked(event):
                self.audio.play("select")
                self.selected_mode = GAME_MODES[i]
                self.state = State.MENU

    def _event_colors(self, event):
        if self.color_back_btn.clicked(event):
            self.audio.play("select")
            self.state = State.MENU
            return
        if self.color_play_btn.clicked(event):
            self.audio.play("select")
            self._start_game()
            return
        if self.custom_swatch.clicked(event):
            self.audio.play("select")
            self.custom_color_active = not self.custom_color_active
            if self.custom_color_active:
                for sw in self.color_swatches:
                    sw.selected = False
            return
        for slider in self.rgb_sliders:
            slider.handle_event(event)
        for sw in self.color_swatches:
            if sw.clicked(event):
                self.audio.play("select")
                self.custom_color_active = False
                self.selected_color = sw.preset
                for s in self.color_swatches:
                    s.selected = False
                sw.selected = True

    def _event_field_size(self, event):
        if self.field_back_btn.clicked(event):
            self.audio.play("select")
            self.state = State.MENU
            return
        # Preset buttons
        for i, btn in enumerate(self.field_preset_btns):
            if btn.clicked(event):
                self.audio.play("select")
                fp = FIELD_PRESETS[i]
                self.grid_cols = fp["cols"]
                self.grid_rows = fp["rows"]
                self.field_preset_idx = i
                self.field_custom = False
                self._recalc_grid()
                self._build_grid_surface()
                # Sync sliders
                self.field_col_slider.value = self.grid_cols
                self.field_row_slider.value = self.grid_rows
                return
        # Custom toggle
        if self.field_custom_btn.clicked(event):
            self.audio.play("select")
            self.field_custom = True
            self.field_preset_idx = -1
            return
        # Custom sliders
        if self.field_custom:
            self.field_col_slider.handle_event(event)
            self.field_row_slider.handle_event(event)
            new_c = self.field_col_slider.value
            new_r = self.field_row_slider.value
            if new_c != self.grid_cols or new_r != self.grid_rows:
                self.grid_cols = new_c
                self.grid_rows = new_r
                self._recalc_grid()
                self._build_grid_surface()

    def _event_playing(self, event):
        if event.type == pygame.KEYDOWN:
            key = event.key
            if key in (pygame.K_UP, pygame.K_w):
                self.snake.set_direction(DIR_UP)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.snake.set_direction(DIR_DOWN)
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.snake.set_direction(DIR_LEFT)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.snake.set_direction(DIR_RIGHT)
            elif key in (pygame.K_SPACE, pygame.K_ESCAPE):
                self.state = State.PAUSED

    def _event_paused(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_RETURN):
                self.state = State.PLAYING
        # Pause overlay buttons
        for attr, target in [("_pause_resume", State.PLAYING),
                             ("_pause_restart", "restart"),
                             ("_pause_menu", State.MENU)]:
            btn = getattr(self, attr, None)
            if btn and btn.clicked(event):
                self.audio.play("select")
                if target == "restart":
                    self._start_game()
                else:
                    self.state = target

    def _event_gameover(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self._start_game()
                return
            if event.key == pygame.K_ESCAPE:
                self.state = State.MENU
                return
        for attr, action in [("_go_retry", "restart"),
                             ("_go_mode", State.MODE_SELECT),
                             ("_go_menu", State.MENU)]:
            btn = getattr(self, attr, None)
            if btn and btn.clicked(event):
                self.audio.play("select")
                if action == "restart":
                    self._start_game()
                else:
                    self.state = action

    # ── update ─────────────────────────────────────────────────
    def _update(self, dt):
        mpos = pygame.mouse.get_pos()

        # Fade-in
        if self.fading_in:
            self.fade_alpha = max(0, self.fade_alpha - int(600 * dt))
            if self.fade_alpha <= 0:
                self.fading_in = False

        # Background stars twinkle
        # (visual only, no logic needed)

        if self.state == State.MENU:
            for b in self.menu_buttons:
                b.update(mpos, dt)
        elif self.state == State.MODE_SELECT:
            for b in self.mode_buttons:
                b.update(mpos, dt)
            self.mode_back_btn.update(mpos, dt)
        elif self.state == State.FIELD_SIZE:
            for b in self.field_preset_btns:
                b.update(mpos, dt)
            self.field_custom_btn.update(mpos, dt)
            self.field_back_btn.update(mpos, dt)
        elif self.state == State.COLOR_SELECT:
            for sw in self.color_swatches:
                sw.update(mpos, dt)
            self.custom_swatch.update(mpos, dt)
            self.color_play_btn.update(mpos, dt)
            self.color_back_btn.update(mpos, dt)
        elif self.state == State.PLAYING:
            self._update_game(dt)
        elif self.state == State.PAUSED:
            for attr in ("_pause_resume", "_pause_restart", "_pause_menu"):
                btn = getattr(self, attr, None)
                if btn:
                    btn.update(mpos, dt)
        elif self.state == State.GAME_OVER:
            for attr in ("_go_retry", "_go_mode", "_go_menu"):
                btn = getattr(self, attr, None)
                if btn:
                    btn.update(mpos, dt)
            self.particles.update(dt)

        # Floating texts
        for ft in self.floats:
            ft.update(dt)
        self.floats = [ft for ft in self.floats if ft.alive]

    def _update_game(self, dt):
        self.game_time += dt
        self.food.update(dt)
        self.shake.update(dt)
        self.particles.update(dt)

        # Head trail
        if self.snake and self.snake.alive:
            hx, hy = self.snake.head
            px = self.play_x + hx * self.cell_size + self.cell_size // 2
            py = self.play_y + hy * self.cell_size + self.cell_size // 2
            self.particles.trail(px, py, self.snake.color["glow"], count=1, size=2)

        # Movement timer
        self.move_timer += dt * 1000
        if self.move_timer >= self.move_interval:
            self.move_timer -= self.move_interval
            self._tick_snake()

    def _tick_snake(self):
        mode = self.selected_mode
        self.snake.move(wrap=mode.get("wrap", False),
                        grid_cols=self.grid_cols, grid_rows=self.grid_rows)

        # ─ collisions ─
        dead = False

        # Wall
        if mode["walls_kill"] and self.snake.hit_wall(self.grid_cols, self.grid_rows):
            dead = True
        elif not mode.get("wrap") and self.snake.hit_wall(self.grid_cols, self.grid_rows):
            dead = True

        # Self
        if self.snake.hit_self() and not mode.get("immortal"):
            dead = True

        # Obstacles
        if self.obstacles and self.snake.hit_obstacles(self.obstacles):
            dead = True

        if dead and not mode.get("immortal"):
            self._die()
            return

        # If immortal and hit self, just ignore (no growth loss)
        if mode.get("immortal") and self.snake.hit_self():
            # Trim the overlapping tail segment
            head = self.snake.head
            while self.snake.segments.count(head) > 1:
                self.snake.segments.pop()

        # ─ food collision ─
        if self.snake.head == self.food.pos:
            pts = 5 if self.food.is_bonus else 1
            self.snake.score += pts
            self.snake.foods_eaten += 1
            self.snake.grow(3 if self.food.is_bonus else 1)

            # Effects
            fx = self.play_x + self.food.pos[0] * self.cell_size + self.cell_size // 2
            fy = self.play_y + self.food.pos[1] * self.cell_size + self.cell_size // 2
            col = C.BONUS if self.food.is_bonus else C.FOOD
            self.particles.burst(fx, fy, col, count=18, speed=4, life=0.6, size=4)
            self.floats.append(FloatingText(
                fx, fy, f"+{pts}", col, self.font_large))
            self.audio.play("bonus" if self.food.is_bonus else "eat")

            # Speed Rush: increase speed
            if mode.get("speed_up"):
                self.move_interval = max(MIN_MOVE_INTERVAL,
                                         self.move_interval - SPEED_DECREASE_PER_FOOD)

            self.food.spawn(self.snake.segments, self.obstacles,
                            grid_cols=self.grid_cols, grid_rows=self.grid_rows)

    def _die(self):
        self.snake.alive = False
        # Explosion
        hx, hy = self.snake.head
        px = self.play_x + hx * self.cell_size + self.cell_size // 2
        py = self.play_y + hy * self.cell_size + self.cell_size // 2
        self.particles.burst(px, py, C.RED, count=40, speed=6, life=1.0, size=5, gravity=0.15)
        self.shake.trigger(14, 0.4)
        self.audio.play("die")

        # High score
        self.new_high = self._set_high(self.snake.score)

        # Build game-over UI
        cx = WINDOW_WIDTH // 2
        bw, bh = 220, 48
        self._go_retry = Button(cx - bw // 2, 460, bw, bh, "Play Again (R)",
                                self.font_medium, active_border=C.GREEN)
        self._go_mode  = Button(cx - bw // 2, 520, bw, bh, "Change Mode",
                                self.font_medium)
        self._go_menu  = Button(cx - bw // 2, 580, bw, bh, "Main Menu",
                                self.font_medium, border=C.RED)

        self.state = State.GAME_OVER

    # ══════════════════════════════════════════════════════════
    #  RENDERING
    # ══════════════════════════════════════════════════════════
    def _render(self):
        self.screen.fill(C.BG)
        self._draw_bg_stars()

        if self.state == State.MENU:
            self._draw_menu()
        elif self.state == State.MODE_SELECT:
            self._draw_modes()
        elif self.state == State.FIELD_SIZE:
            self._draw_field_size()
        elif self.state == State.COLOR_SELECT:
            self._draw_colors()
        elif self.state == State.PLAYING:
            self._draw_game()
        elif self.state == State.PAUSED:
            self._draw_game()
            self._draw_pause_overlay()
        elif self.state == State.GAME_OVER:
            self._draw_game()
            self._draw_gameover_overlay()

        # Fade-in overlay
        if self.fade_alpha > 0:
            fo = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            fo.fill((0, 0, 0, self.fade_alpha))
            self.screen.blit(fo, (0, 0))

    # ── background stars ───────────────────────────────────────
    def _draw_bg_stars(self):
        t = pygame.time.get_ticks() / 1000
        for sx, sy, sz, sp in self.bg_stars:
            a = int(50 + 40 * math.sin(t * sp + sx))
            r = max(1, int(sz))
            s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (180, 190, 220, a), (r + 1, r + 1), r)
            self.screen.blit(s, (sx - r, sy - r))

    # ── menu ───────────────────────────────────────────────────
    def _draw_menu(self):
        # Title glow
        t = pygame.time.get_ticks() / 1000
        title = "SERPENT"
        # Glow (render multiple times offset for bloom)
        glow_col = lerp_color(C.BLUE, C.CYAN, (math.sin(t * 1.5) + 1) / 2)
        ts = self.font_title.render(title, True, glow_col)
        tw = ts.get_width()
        tx = WINDOW_WIDTH // 2 - tw // 2
        ty = 120
        # Bloom layers
        for offset in range(4, 0, -1):
            gs = self.font_title.render(title, True, glow_col)
            gs.set_alpha(int(18 / offset))
            for dx in (-offset, 0, offset):
                for dy in (-offset, 0, offset):
                    self.screen.blit(gs, (tx + dx, ty + dy))
        self.screen.blit(ts, (tx, ty))

        # Subtitle
        draw_text_centered(self.screen, "A Modern Snake Experience",
                           self.font_medium, C.GRAY, 195)

        # Selected mode tag
        mode_text = f"Mode: {self.selected_mode['name']}"
        draw_text_centered(self.screen, mode_text, self.font_small, C.DIM, 225)

        # Colour preview
        col_text = f"Skin: {self.selected_color['name']}"
        draw_text_centered(self.screen, col_text, self.font_small,
                           self.selected_color["head"], 245)

        # Field size info
        fsz = f"Field: {self.grid_cols}×{self.grid_rows}"
        draw_text_centered(self.screen, fsz, self.font_small, C.DIM, 265)

        # High score
        hs = self._get_high()
        if hs > 0:
            draw_text_centered(self.screen, f"High Score ({self.selected_mode['name']}): {hs}",
                               self.font_small, C.GOLD, 290)

        # Buttons
        for btn in self.menu_buttons:
            btn.draw(self.screen)

        # Footer
        draw_text_centered(self.screen, "Arrow Keys / WASD to move  |  SPACE to pause",
                           self.font_tiny, C.DIM, WINDOW_HEIGHT - 30)

    # ── mode select ────────────────────────────────────────────
    def _draw_modes(self):
        draw_text_centered(self.screen, "Select Game Mode",
                           self.font_large, C.WHITE, 80)
        draw_text_centered(self.screen, "Choose your challenge",
                           self.font_small, C.GRAY, 120)

        for i, btn in enumerate(self.mode_buttons):
            # Highlight selected
            if GAME_MODES[i]["id"] == self.selected_mode["id"]:
                r = btn.rect.inflate(6, 6)
                pygame.draw.rect(self.screen, C.BLUE, r, width=2, border_radius=14)
            btn.draw(self.screen)

        self.mode_back_btn.draw(self.screen)

    # ── field size select ──────────────────────────────────────
    def _draw_field_size(self):
        draw_text_centered(self.screen, "Field Size",
                           self.font_large, C.WHITE, 70)
        draw_text_centered(self.screen, "Choose play-area dimensions",
                           self.font_small, C.GRAY, 110)

        # Preset buttons
        for i, btn in enumerate(self.field_preset_btns):
            # Highlight active preset
            if not self.field_custom and i == self.field_preset_idx:
                r = btn.rect.inflate(6, 6)
                pygame.draw.rect(self.screen, C.CYAN, r, width=2, border_radius=14)
            btn.draw(self.screen)

        # Custom button
        if self.field_custom:
            r = self.field_custom_btn.rect.inflate(6, 6)
            pygame.draw.rect(self.screen, C.PURPLE, r, width=2, border_radius=14)
        self.field_custom_btn.draw(self.screen)

        # Custom sliders
        if self.field_custom:
            self.field_col_slider.draw(self.screen, self.font_small)
            self.field_row_slider.draw(self.screen, self.font_small)

        # Live preview: mini grid outline
        prev_label = f"Preview  ({self.grid_cols}×{self.grid_rows})"
        draw_text_centered(self.screen, prev_label,
                           self.font_small, C.GRAY, WINDOW_HEIGHT - 140)
        max_prev_w, max_prev_h = 260, 120
        scale = min(max_prev_w / self.grid_cols, max_prev_h / self.grid_rows)
        pw = int(self.grid_cols * scale)
        ph = int(self.grid_rows * scale)
        px = WINDOW_WIDTH // 2 - pw // 2
        py = WINDOW_HEIGHT - 125
        pygame.draw.rect(self.screen, C.BG_GRID, (px, py, pw, ph))
        pygame.draw.rect(self.screen, C.CYAN, (px, py, pw, ph), width=1, border_radius=2)
        # Mini grid lines
        for c in range(1, self.grid_cols):
            lx = px + int(c * scale)
            pygame.draw.line(self.screen, (*C.GRID_LINE[:3],), (lx, py), (lx, py + ph))
        for r in range(1, self.grid_rows):
            ly = py + int(r * scale)
            pygame.draw.line(self.screen, (*C.GRID_LINE[:3],), (px, ly), (px + pw, ly))

        self.field_back_btn.draw(self.screen)

    # ── colour select ──────────────────────────────────────────
    def _draw_colors(self):
        draw_text_centered(self.screen, "Choose Your Snake",
                           self.font_large, C.WHITE, 60)
        draw_text_centered(self.screen, f"Mode: {self.selected_mode['name']}",
                           self.font_small, C.GRAY, 100)

        # Preset label
        ts = self.font_medium.render("Presets", True, C.GRAY)
        self.screen.blit(ts, (self.color_swatches[0].cx - self.color_swatches[0].r - 5,
                              self.color_swatches[0].cy - self.color_swatches[0].r - 35))

        for sw in self.color_swatches:
            sw.draw(self.screen)

        self.custom_swatch.draw(self.screen)

        # Custom colour UI
        if self.custom_color_active:
            # Panel background
            px = WINDOW_WIDTH // 2 + 90
            panel = pygame.Rect(px, 180, 260, 330)
            draw_rounded_rect(self.screen, C.BG_PANEL, panel, 12, alpha=220)
            pygame.draw.rect(self.screen, C.BTN_BORDER, panel, width=1, border_radius=12)

            ts = self.font_medium.render("Custom Color", True, C.WHITE)
            self.screen.blit(ts, (px + 15, 195))

            for sl in self.rgb_sliders:
                sl.draw(self.screen, self.font_small)

            # Preview
            r = self.rgb_sliders[0].value
            g = self.rgb_sliders[1].value
            b = self.rgb_sliders[2].value
            preview_y = 520
            pygame.draw.circle(self.screen, (r, g, b),
                             (px + 130, preview_y), 28)
            ts = self.font_small.render(f"({r}, {g}, {b})", True, C.GRAY)
            self.screen.blit(ts, (px + 130 - ts.get_width() // 2, preview_y + 38))

        # Snake preview (bottom area)
        self._draw_snake_preview()

        self.color_play_btn.draw(self.screen)
        self.color_back_btn.draw(self.screen)

    def _draw_snake_preview(self):
        """Animate a small snake preview with the selected colour."""
        t = pygame.time.get_ticks() / 1000
        if self.custom_color_active:
            r = self.rgb_sliders[0].value
            g = self.rgb_sliders[1].value
            b = self.rgb_sliders[2].value
            head = (r, g, b)
            body = (max(0, r - 50), max(0, g - 50), max(0, b - 50))
        else:
            head = self.selected_color["head"]
            body = self.selected_color["body"]

        cx = WINDOW_WIDTH // 2 - 50
        cy = WINDOW_HEIGHT - 170
        seg_size = 18
        gap = 2
        # Draw 8 segments in a wave
        for i in range(8):
            frac = 1 - i / 7
            col = lerp_color(body, head, frac)
            sx = cx - i * (seg_size + gap)
            sy = cy + int(math.sin(t * 3 + i * 0.6) * 8)
            r_val = 6 if i == 0 else 4
            rect = pygame.Rect(sx, sy, seg_size, seg_size)
            pygame.draw.rect(self.screen, col, rect, border_radius=r_val)

        label = self.font_small.render("Preview", True, C.DIM)
        self.screen.blit(label, (cx - 80, cy - 25))

    # ── game board ─────────────────────────────────────────────
    def _draw_game(self):
        ox, oy = self.shake.offset()
        cs = self.cell_size
        gx, gy = self.play_x, self.play_y
        # Grid
        self.screen.blit(self._grid_surface, (gx + ox, gy + oy))
        # Border
        border_rect = pygame.Rect(gx + ox - 1, gy + oy - 1,
                                  self.play_w + 2, self.play_h + 2)
        pygame.draw.rect(self.screen, C.GRID_LINE, border_rect, width=2, border_radius=2)

        # Obstacles
        for (bx, by) in self.obstacles:
            px = gx + ox + bx * cs
            py = gy + oy + by * cs
            r = pygame.Rect(px + 1, py + 1, cs - 2, cs - 2)
            pygame.draw.rect(self.screen, C.OBSTACLE, r, border_radius=3)
            pygame.draw.rect(self.screen, C.OBS_BORDER, r, width=1, border_radius=3)

        # Food
        if self.food:
            self.food.draw(self.screen, gx + ox, gy + oy, cs)

        # Snake
        if self.snake:
            self.snake.draw(self.screen, gx + ox, gy + oy, cs)

        # Particles
        self.particles.draw(self.screen)

        # Floating texts
        for ft in self.floats:
            ft.draw(self.screen)

        # HUD
        self._draw_hud()

    def _draw_hud(self):
        if not self.snake:
            return
        # Top bar
        hud_rect = pygame.Rect(0, 0, WINDOW_WIDTH, 70)
        draw_rounded_rect(self.screen, C.BG_PANEL, hud_rect, 0, alpha=200)
        # Separator
        pygame.draw.line(self.screen, C.GRID_LINE, (0, 70), (WINDOW_WIDTH, 70))

        # Score
        score_text = f"Score: {self.snake.score}"
        ts = self.font_large.render(score_text, True, C.WHITE)
        self.screen.blit(ts, (20, 18))

        # High score
        hs = self._get_high()
        hs_text = f"Best: {hs}"
        ts2 = self.font_medium.render(hs_text, True, C.GOLD)
        self.screen.blit(ts2, (20, 48))

        # Mode badge
        mode_text = self.selected_mode["name"]
        ts3 = self.font_medium.render(mode_text, True, C.CYAN)
        mx = WINDOW_WIDTH // 2 - ts3.get_width() // 2
        self.screen.blit(ts3, (mx, 10))

        # Speed (if speed rush)
        if self.selected_mode.get("speed_up"):
            speed_pct = int((1 - (self.move_interval - MIN_MOVE_INTERVAL) /
                             (BASE_MOVE_INTERVAL - MIN_MOVE_INTERVAL)) * 100)
            speed_pct = max(0, min(100, speed_pct))
            sp_text = f"Speed: {speed_pct}%"
            sp_col = lerp_color(C.GREEN, C.RED, speed_pct / 100)
            ts4 = self.font_medium.render(sp_text, True, sp_col)
            self.screen.blit(ts4, (mx - 5, 38))

        # Length
        length_text = f"Length: {len(self.snake.segments)}"
        ts5 = self.font_medium.render(length_text, True, C.GRAY)
        self.screen.blit(ts5, (WINDOW_WIDTH - ts5.get_width() - 20, 18))

        # Time
        mins = int(self.game_time) // 60
        secs = int(self.game_time) % 60
        time_text = f"Time: {mins:02d}:{secs:02d}"
        ts6 = self.font_medium.render(time_text, True, C.GRAY)
        self.screen.blit(ts6, (WINDOW_WIDTH - ts6.get_width() - 20, 44))

    # ── pause overlay ──────────────────────────────────────────
    def _draw_pause_overlay(self):
        # Dim
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        self.screen.blit(dim, (0, 0))

        # Panel
        pw, ph = 320, 280
        px = WINDOW_WIDTH // 2 - pw // 2
        py = WINDOW_HEIGHT // 2 - ph // 2
        panel = pygame.Rect(px, py, pw, ph)
        draw_rounded_rect(self.screen, C.BG_PANEL, panel, 16, alpha=240)
        pygame.draw.rect(self.screen, C.BTN_BORDER, panel, width=1, border_radius=16)

        draw_text_centered(self.screen, "PAUSED", self.font_large, C.WHITE, py + 40)
        draw_text_centered(self.screen, f"Score: {self.snake.score}",
                           self.font_medium, C.GRAY, py + 80)

        # Buttons
        bw, bh = 200, 44
        bx = WINDOW_WIDTH // 2 - bw // 2
        if not hasattr(self, "_pause_resume") or self._pause_resume is None:
            self._pause_resume  = Button(bx, py + 115, bw, bh, "Resume", self.font_medium,
                                         active_border=C.GREEN)
            self._pause_restart = Button(bx, py + 168, bw, bh, "Restart", self.font_medium)
            self._pause_menu    = Button(bx, py + 221, bw, bh, "Main Menu", self.font_medium,
                                         border=C.RED)

        self._pause_resume.draw(self.screen)
        self._pause_restart.draw(self.screen)
        self._pause_menu.draw(self.screen)

    # ── game-over overlay ──────────────────────────────────────
    def _draw_gameover_overlay(self):
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        self.screen.blit(dim, (0, 0))

        # Panel
        pw, ph = 380, 380
        px = WINDOW_WIDTH // 2 - pw // 2
        py = 140
        panel = pygame.Rect(px, py, pw, ph)
        draw_rounded_rect(self.screen, C.BG_PANEL, panel, 16, alpha=240)
        pygame.draw.rect(self.screen, C.RED, panel, width=2, border_radius=16)

        draw_text_centered(self.screen, "GAME OVER", self.font_large, C.RED, py + 40)

        score = self.snake.score if self.snake else 0
        draw_text_centered(self.screen, f"Score: {score}",
                           self.font_large, C.WHITE, py + 90)

        hs = self._get_high()
        if getattr(self, "new_high", False):
            # Pulsing new high score text
            t = pygame.time.get_ticks() / 1000
            a = int(200 + 55 * math.sin(t * 4))
            nhs = self.font_medium.render("NEW HIGH SCORE!", True, C.GOLD)
            nhs.set_alpha(a)
            r = nhs.get_rect(center=(WINDOW_WIDTH // 2, py + 130))
            self.screen.blit(nhs, r)
        else:
            draw_text_centered(self.screen, f"Best: {hs}",
                               self.font_medium, C.GRAY, py + 130)

        # Stats
        if self.snake:
            length = len(self.snake.segments)
            foods = self.snake.foods_eaten
            mins = int(self.game_time) // 60
            secs = int(self.game_time) % 60
            stats = f"Length: {length}   |   Food: {foods}   |   Time: {mins:02d}:{secs:02d}"
            draw_text_centered(self.screen, stats, self.font_small, C.DIM, py + 165)

        # Buttons
        if hasattr(self, "_go_retry") and self._go_retry:
            self._go_retry.draw(self.screen)
            self._go_mode.draw(self.screen)
            self._go_menu.draw(self.screen)

        # Particles (death explosion continues)
        self.particles.draw(self.screen)


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════
def main():
    """Main entry point for the game."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()

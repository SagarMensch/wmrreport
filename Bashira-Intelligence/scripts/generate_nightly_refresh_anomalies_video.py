from __future__ import annotations

import gc
import math
import subprocess
import time
import wave
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "web" / "public" / "demo-videos"
OUTPUT_FILE = OUTPUT_DIR / "nightly-refresh-anomalies-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 24
SCENE_GAP_SECONDS = 0.24
MIN_SCENE_SECONDS = 10.2

ACTIVE_WELLS = [
    ("Falcon-12", 0.42),
    ("Rigel-09", 0.66),
    ("Sahara-31", 0.28),
    ("Nour-18", 0.84),
    ("Delta-07", 0.51),
]

STACK_STEPS = [
    "58-feature frame",
    "4-week forecast",
    "survival window",
    "risk score",
    "risk tier",
]

ANOMALIES = [
    ("Falcon-12", "WATCH", "HIGH_RISK", "P2", +16.4),
    ("Sahara-31", "WATCH", "CRITICAL", "P1", +28.9),
    ("Delta-07", "HIGH_RISK", "WATCH", "P3", -11.7),
]

STATE_ROWS = [
    ("Falcon-12", "HIGH_RISK", 68.2),
    ("Rigel-09", "HEALTHY", 29.4),
    ("Sahara-31", "CRITICAL", 82.1),
    ("Nour-18", "WATCH", 41.0),
    ("Delta-07", "WATCH", 44.9),
]

SCENES = [
    {
        "title": "Why Bashira Runs A Nightly Refresh",
        "subtitle": "Every unfinished well is rechecked overnight so the portfolio can move with the latest field reality.",
        "code": "predict_service.py:317-323",
        "accent": "#EF4444",
        "narration": "This nightly refresh exists so Bashira does not become a stale dashboard. Every unfinished well is re-evaluated after the latest field snapshot lands. That means the next morning view is not yesterday's guess. It is a fresh predictive pass over the active portfolio.",
    },
    {
        "title": "Only Active Wells Enter The Night Pass",
        "subtitle": "The service fetches snapshot rows where progress is below one hundred percent and not null.",
        "code": "predict_service.py:150-162, 330-337",
        "accent": "#F97316",
        "narration": "The first filter is operationally simple. Bashira selects only active wells. In code that means progress must be present and still below one hundred percent. Completed wells do not enter the night pass, because the refresh is only for work that can still drift.",
    },
    {
        "title": "Each Well Runs Through The Predictive Stack",
        "subtitle": "For every active well, Bashira engineers features, forecasts progress, estimates timing, and computes a fresh risk tier.",
        "code": "feature_engine.py:646-711, 723-736",
        "accent": "#FB7185",
        "narration": "Now the overnight loop begins. For each active well, Bashira rebuilds the engineered feature row, runs the four week progress forecast, runs the survival logic for timing, computes the weighted risk score, and assigns the latest risk tier. So the nightly pass is not one shortcut number. It is the full predictive stack applied again well by well.",
    },
    {
        "title": "The Tracker Remembers Yesterday",
        "subtitle": "Before writing anything new, Bashira looks up the stored tier and score for that same well.",
        "code": "anomaly_tracker.py:199-223, 262-268",
        "accent": "#F43F5E",
        "narration": "The anomaly tracker acts like memory. Before Bashira decides whether something changed, it checks the last stored state for that well. That old state holds the previous tier and score. Without that memory, the system could show today's risk but it could not tell you whether the well actually moved.",
    },
    {
        "title": "A Tier Change Becomes An Anomaly Event",
        "subtitle": "If old tier and new tier differ, Bashira inserts an anomaly row with the jump and score delta.",
        "code": "anomaly_tracker.py:223-247, 270-286, 311-327",
        "accent": "#DC2626",
        "narration": "The anomaly rule is precise. If the old tier and the new tier are different, Bashira creates an anomaly event. That event stores the well name, old tier, new tier, severity, score delta, and timestamp. So an anomaly here does not mean vague weirdness. It specifically means the risk band moved.",
    },
    {
        "title": "Severity Comes From Jump Size",
        "subtitle": "A two-level upward jump becomes P1, a one-level rise becomes P2, and de-escalation becomes P3.",
        "code": "anomaly_tracker.py:183-197",
        "accent": "#B91C1C",
        "narration": "Severity is not guessed by a person. It is calculated from the size and direction of the tier jump. If a well rises by two levels, that is a P1. If it rises by one level, that is a P2. If the risk band moves downward, Bashira still records the change, but marks it as P3 because the movement is easing rather than escalating.",
    },
    {
        "title": "The State Table Is Updated Either Way",
        "subtitle": "Even when there is no anomaly, the stored well state is overwritten with the latest tier, score, and update time.",
        "code": "anomaly_tracker.py:248-260, 287-304, 329-333",
        "accent": "#E11D48",
        "narration": "This part matters. Even if a tier does not change, Bashira still updates the well state table with the newest score, newest tier, and newest timestamp. That means tomorrow's comparison starts from the right baseline. The anomaly feed only captures transitions, but the state table preserves the latest truth for every active well.",
    },
    {
        "title": "Morning Feeds Read The Overnight Changes",
        "subtitle": "The refreshed state powers portfolio views, and the anomaly endpoint serves the newest tier-change events.",
        "code": "predict_service.py:356-362, 393-399, 441-448",
        "accent": "#F87171",
        "narration": "By morning, Bashira has two useful products. First, the refreshed portfolio state with updated tiers across active wells. Second, a live anomaly feed that returns the most recent tier changes. So the overnight refresh is the bridge between raw field drift and an action ready morning watch list.",
    },
]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ease(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


def pop(progress: float, delay: float, duration: float = 0.18) -> float:
    return ease((progress - delay) / duration)


def blend(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def rgba(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], int(255 * clamp(alpha))


@lru_cache(maxsize=None)
def load_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if mono:
        candidates = [
            "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/courbd.ttf" if bold else "C:/Windows/Fonts/cour.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/trebucbd.ttf" if bold else "C:/Windows/Fonts/trebuc.ttf",
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


FONT_TAG = load_font(16, bold=True, mono=True)
FONT_TITLE = load_font(37, bold=True)
FONT_SUB = load_font(22)
FONT_PANEL = load_font(27, bold=True)
FONT_BODY = load_font(19)
FONT_SMALL = load_font(15)
FONT_MONO = load_font(18, mono=True)
FONT_MONO_SMALL = load_font(15, mono=True)
FONT_NUMBER = load_font(54, bold=True, mono=True)
FONT_BIG = load_font(68, bold=True)


def rounded(draw: ImageDraw.ImageDraw, box, fill, outline=None, radius: int = 20, width: int = 1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_text_block(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_lines: int, max_size: int, min_size: int, *, bold: bool = False, mono: bool = False):
    for size in range(max_size, min_size - 1, -1):
        font = load_font(size, bold=bold, mono=mono)
        lines = wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
    font = load_font(min_size, bold=bold, mono=mono)
    return font, wrap_text(draw, text, font, max_width)[:max_lines]


def draw_lines(draw: ImageDraw.ImageDraw, x: int, y: int, lines: list[str], font, fill, line_gap: int = 3) -> int:
    cursor = y
    for line in lines:
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += font.size + line_gap
    return cursor


def panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, accent, fill_alpha: float = 0.88):
    rounded(draw, (x + 10, y + 12, x + w + 10, y + h + 12), (7, 16, 23, 115), radius=26)
    rounded(draw, (x, y, x + w, y + h), rgba((10, 18, 28), fill_alpha), outline=rgba(accent, 0.84), radius=26, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    width = draw.textbbox((0, 0), text, font=FONT_TAG)[2] + 28
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.16), outline=rgba(accent, 0.66), radius=999, width=2)
    draw.text((x + 14, y + 7), text, font=FONT_TAG, fill=(*accent, 255))


def tier_color(tier: str) -> tuple[int, int, int]:
    palette = {
        "HEALTHY": rgb("#22C55E"),
        "WATCH": rgb("#EAB308"),
        "HIGH_RISK": rgb("#F97316"),
        "CRITICAL": rgb("#DC2626"),
        "UNKNOWN": rgb("#94A3B8"),
    }
    return palette.get(tier, palette["UNKNOWN"])


def draw_background(draw: ImageDraw.ImageDraw, accent):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(5, 10, 18))
    draw.ellipse((WIDTH - 310, -80, WIDTH + 70, 300), fill=rgba(accent, 0.10))
    draw.ellipse((-140, 520, 250, 900), fill=(70, 18, 22, 95))
    for y in range(178, 610, 36):
        draw.line((82, y, WIDTH - 82, y), fill=(21, 35, 49, 52), width=1)
    for x in range(100, WIDTH - 100, 98):
        draw.line((x, 178, x, 606), fill=(21, 35, 49, 34), width=1)


def draw_radar(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, accent, progress: float):
    for ring in [radius, radius * 0.72, radius * 0.45]:
        draw.ellipse((cx - ring, cy - ring, cx + ring, cy + ring), outline=rgba(accent, 0.20), width=2)
    draw.line((cx - radius, cy, cx + radius, cy), fill=(35, 60, 78), width=2)
    draw.line((cx, cy - radius, cx, cy + radius), fill=(35, 60, 78), width=2)
    sweep_angle = -math.pi / 2 + progress * math.pi * 1.8
    sx = cx + math.cos(sweep_angle) * radius
    sy = cy + math.sin(sweep_angle) * radius
    draw.line((cx, cy, sx, sy), fill=rgba(accent, 0.82), width=4)
    draw.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=(*accent, 255))


def draw_header(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    scene = SCENES[scene_index]
    draw_chip(draw, 92, 24, f"NIGHT OPS 07 / PASS {scene_index + 1:02d}", accent)
    draw.text((92, 84), scene["title"], font=FONT_TITLE, fill=(241, 244, 248))
    draw.text((92, 130), scene["subtitle"], font=FONT_SUB, fill=(214, 223, 232))
    for i in range(len(SCENES)):
        dot_x = 28 + i * 28
        dot_color = accent if i == scene_index else (52, 67, 82)
        draw.ellipse((dot_x, 150, dot_x + 18, 168), fill=dot_color)
    code_text = scene["code"]
    box_width = max(300, draw.textbbox((0, 0), code_text, font=FONT_MONO_SMALL)[2] + 42)
    panel(draw, WIDTH - box_width - 64, 22, box_width, 56, accent, fill_alpha=0.94)
    draw.text((WIDTH - box_width - 42, 40), code_text, font=FONT_MONO_SMALL, fill=(236, 240, 245))


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    panel(draw, 86, HEIGHT - 84, WIDTH - 172, 46, accent, fill_alpha=0.95)
    label = "NIGHT REFRESH"
    label_width = draw.textbbox((0, 0), label, font=FONT_TAG)[2]
    footer_font, lines = fit_text_block(
        draw,
        text,
        WIDTH - 280 - label_width,
        1,
        22,
        18,
    )
    draw_lines(draw, 112, HEIGHT - 72, lines, footer_font, (240, 243, 247), line_gap=0)
    draw.text((WIDTH - 118 - label_width, HEIGHT - 69), label, font=FONT_TAG, fill=(*accent, 255))


def scene_why(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 100, 216, 428, 300, accent)
    draw.text((132, 246), "Need", font=FONT_PANEL, fill=(241, 244, 248))
    bullets = [
        "field status can drift overnight",
        "unfinished wells need a fresh pass",
        "morning portfolio must reflect latest risk",
    ]
    for idx, bullet in enumerate(bullets):
        local = pop(progress, 0.08 + idx * 0.10)
        y = 304 + idx * 64
        draw.ellipse((136, y + 6, 154, y + 24), fill=rgba(accent, 0.70 + 0.30 * local))
        font, lines = fit_text_block(draw, bullet, 320, 2, 21, 17)
        draw_lines(draw, 168, y, lines, font, (222, 230, 238), line_gap=4)

    draw_radar(draw, 832, 362, 138, accent, progress)
    draw.text((760, 532), "00:45 refresh window", font=FONT_MONO, fill=(220, 228, 237))

    panel(draw, 956, 232, 222, 246, accent)
    draw.text((982, 260), "Morning goal", font=FONT_BODY, fill=(240, 244, 249))
    draw.text((982, 318), "fresh", font=FONT_BIG, fill=(*accent, 255))
    draw.text((982, 394), "tiers", font=FONT_BIG, fill=(241, 244, 248))


def scene_active(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 214, 506, 324, accent)
    draw.text((122, 246), "Active-well intake", font=FONT_PANEL, fill=(241, 244, 248))
    draw.text((122, 286), "over_all_progress_percentages < 1.0", font=FONT_MONO, fill=(*accent, 255))
    draw.text((122, 316), "and not null", font=FONT_MONO, fill=(220, 228, 237))
    for idx, (well, progress_value) in enumerate(ACTIVE_WELLS):
        local = pop(progress, 0.06 + idx * 0.08)
        y = 362 + idx * 34
        rounded(draw, (122, y, 554, y + 26), rgba(accent, 0.10 + 0.14 * local), outline=rgba(accent, 0.72), radius=13, width=2)
        draw.text((140, y + 4), well, font=FONT_BODY, fill=(241, 244, 248))
        draw.text((448, y + 4), f"{int(progress_value * 100)}%", font=FONT_MONO_SMALL, fill=(220, 228, 237))

    panel(draw, 652, 214, 528, 324, accent)
    draw.text((684, 246), "What stays out", font=FONT_PANEL, fill=(241, 244, 248))
    exclusions = [
        ("completed wells", "100%"),
        ("missing progress rows", "null"),
        ("closed work", "no further drift"),
    ]
    for idx, (name, flag) in enumerate(exclusions):
        y = 314 + idx * 76
        rounded(draw, (684, y, 1148, y + 52), (21, 31, 43), outline=(78, 98, 116), radius=18, width=2)
        draw.text((712, y + 13), name, font=FONT_BODY, fill=(220, 228, 237))
        draw.text((1038, y + 13), flag, font=FONT_MONO, fill=(154, 168, 183))


def scene_stack(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((124, 246), "Per-well night loop", font=FONT_PANEL, fill=(241, 244, 248))
    draw.text((124, 286), "predict_batch -> predict_well -> refreshed tier", font=FONT_MONO, fill=(*accent, 255))
    step_w = 180
    start_x = 120
    y = 360
    for idx, label in enumerate(STACK_STEPS):
        local = pop(progress, 0.06 + idx * 0.10)
        x = start_x + idx * 204
        rounded(draw, (x, y, x + step_w, y + 96), rgba(accent, 0.10 + 0.18 * local), outline=rgba(accent, 0.76), radius=24, width=2)
        font, lines = fit_text_block(draw, label, step_w - 32, 2, 24, 18, bold=True)
        draw_lines(draw, x + 16, y + 24, lines, font, (241, 244, 248), line_gap=4)
        if idx < len(STACK_STEPS) - 1:
            line_local = pop(progress, 0.12 + idx * 0.10)
            x1 = x + step_w
            x2 = x + 204
            draw.line((x1, y + 48, blend(x1, x2, line_local), y + 48), fill=rgba(accent, 0.80), width=6)
            draw.polygon(
                [
                    (blend(x1, x2, line_local), y + 48),
                    (blend(x1, x2, line_local) - 18, y + 38),
                    (blend(x1, x2, line_local) - 18, y + 58),
                ],
                fill=rgba(accent, 0.95),
            )


def scene_memory(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 488, 322, accent)
    draw.text((126, 246), "Stored state lookup", font=FONT_PANEL, fill=(241, 244, 248))
    draw.text((126, 286), "well -> current_tier, last_score", font=FONT_MONO, fill=(*accent, 255))
    rows = [
        ("Falcon-12", "WATCH", "51.8"),
        ("Rigel-09", "HEALTHY", "29.4"),
        ("Sahara-31", "WATCH", "53.2"),
        ("Delta-07", "HIGH_RISK", "56.6"),
    ]
    for idx, (well, tier, score) in enumerate(rows):
        y = 340 + idx * 40
        rounded(draw, (126, y, 548, y + 28), (17, 28, 38), outline=(61, 78, 92), radius=14, width=1)
        draw.text((142, y + 6), well, font=FONT_BODY, fill=(228, 235, 242))
        draw.text((336, y + 6), tier, font=FONT_MONO_SMALL, fill=tier_color(tier))
        draw.text((466, y + 6), score, font=FONT_MONO_SMALL, fill=(210, 220, 230))

    draw_radar(draw, 860, 372, 146, accent, progress)
    draw.text((730, 250), "yesterday", font=FONT_BIG, fill=(236, 240, 245))
    draw.text((768, 320), "vs", font=FONT_NUMBER, fill=(*accent, 255))
    draw.text((730, 392), "today", font=FONT_BIG, fill=(236, 240, 245))


def scene_anomaly(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Tier-drift ledger", font=FONT_PANEL, fill=(241, 244, 248))
    headers = ["Well", "Old", "New", "Severity", "Delta"]
    x_positions = [132, 422, 560, 712, 908]
    for x, header in zip(x_positions, headers):
        draw.text((x, 300), header, font=FONT_SMALL, fill=(170, 183, 197))
    for idx, row in enumerate(ANOMALIES):
        local = pop(progress, 0.08 + idx * 0.12)
        y = 336 + idx * 70
        rounded(draw, (122, y, 1144, y + 54), rgba(accent, 0.08 + 0.16 * local), outline=rgba(accent, 0.78), radius=18, width=2)
        well, old_tier, new_tier, severity, delta = row
        draw.text((144, y + 15), well, font=FONT_BODY, fill=(241, 244, 248))
        draw.text((422, y + 15), old_tier, font=FONT_MONO_SMALL, fill=tier_color(old_tier))
        draw.text((560, y + 15), new_tier, font=FONT_MONO_SMALL, fill=tier_color(new_tier))
        draw.text((716, y + 15), severity, font=FONT_MONO_SMALL, fill=(*accent, 255))
        draw.text((908, y + 15), f"{delta:+.1f}", font=FONT_MONO_SMALL, fill=(241, 244, 248))


def scene_severity(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 1088, 324, accent)
    draw.text((126, 246), "Severity ladder", font=FONT_PANEL, fill=(241, 244, 248))
    ladder = [
        ("HEALTHY", 0, 232),
        ("WATCH", 1, 380),
        ("HIGH_RISK", 2, 528),
        ("CRITICAL", 3, 676),
    ]
    for label, _, x in ladder:
        draw.ellipse((x, 382, x + 44, 426), fill=tier_color(label))
        draw.text((x - 12, 442), label.replace("_", " "), font=FONT_SMALL, fill=(228, 235, 242))
    draw.line((254, 404, 830, 404), fill=(88, 105, 120), width=8)
    draw.line((402, 404, 550, 404), fill=rgb("#F97316"), width=12)
    draw.line((402, 404, 698, 404), fill=rgb("#DC2626"), width=12)
    draw.text((372, 334), "one-step rise -> P2", font=FONT_MONO, fill=(253, 204, 162))
    draw.text((356, 476), "two-step rise -> P1", font=FONT_MONO, fill=(252, 174, 174))
    draw.text((612, 520), "downward move -> P3", font=FONT_MONO_SMALL, fill=(216, 223, 231))

    panel(draw, 874, 246, 256, 212, accent)
    draw.text((902, 278), "Code rule", font=FONT_BODY, fill=(241, 244, 248))
    draw.text((902, 326), "new_idx > old_idx", font=FONT_MONO_SMALL, fill=(241, 244, 248))
    draw.text((902, 356), "jump >= 2 -> P1", font=FONT_MONO_SMALL, fill=(255, 187, 187))
    draw.text((902, 386), "jump = 1 -> P2", font=FONT_MONO_SMALL, fill=(253, 204, 162))
    draw.text((902, 416), "else -> P3", font=FONT_MONO_SMALL, fill=(216, 223, 231))


def scene_state(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 536, 324, accent)
    draw.text((126, 246), "Well state table", font=FONT_PANEL, fill=(241, 244, 248))
    draw.text((126, 286), "always overwritten with latest truth", font=FONT_MONO, fill=(*accent, 255))
    for idx, (well, tier, score) in enumerate(STATE_ROWS):
        local = pop(progress, 0.06 + idx * 0.08)
        y = 334 + idx * 38
        rounded(draw, (126, y, 602, y + 28), rgba(accent, 0.07 + 0.12 * local), outline=rgba(accent, 0.66), radius=14, width=1)
        draw.text((140, y + 6), well, font=FONT_BODY, fill=(228, 235, 242))
        draw.text((352, y + 6), tier, font=FONT_MONO_SMALL, fill=tier_color(tier))
        draw.text((520, y + 6), f"{score:.1f}", font=FONT_MONO_SMALL, fill=(210, 220, 230))

    panel(draw, 700, 214, 470, 324, accent)
    draw.text((730, 246), "Why update even without anomaly", font=FONT_PANEL, fill=(241, 244, 248))
    bullets = [
        "tomorrow compares against the right baseline",
        "latest score is preserved even if tier stays same",
        "portfolio view can show current state for every active well",
    ]
    for idx, bullet in enumerate(bullets):
        y = 314 + idx * 70
        draw.ellipse((734, y + 8, 750, y + 24), fill=(*accent, 255))
        font, lines = fit_text_block(draw, bullet, 360, 2, 20, 17)
        draw_lines(draw, 768, y, lines, font, (222, 230, 238), line_gap=4)


def scene_morning(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 214, 500, 324, accent)
    draw.text((122, 246), "Morning anomaly feed", font=FONT_PANEL, fill=(241, 244, 248))
    draw.text((122, 286), "GET /predict/anomalies", font=FONT_MONO, fill=(*accent, 255))
    for idx, (well, old_tier, new_tier, severity, _) in enumerate(ANOMALIES):
        local = pop(progress, 0.06 + idx * 0.10)
        y = 336 + idx * 64
        rounded(draw, (122, y, 560, y + 46), rgba(accent, 0.08 + 0.12 * local), outline=rgba(accent, 0.72), radius=18, width=2)
        draw.text((144, y + 12), well, font=FONT_BODY, fill=(241, 244, 248))
        draw.text((306, y + 12), f"{old_tier}->{new_tier}", font=FONT_MONO_SMALL, fill=(219, 227, 236))
        draw.text((498, y + 12), severity, font=FONT_MONO_SMALL, fill=(*accent, 255))

    panel(draw, 660, 214, 520, 324, accent)
    draw.text((690, 246), "Portfolio after refresh", font=FONT_PANEL, fill=(241, 244, 248))
    bands = [("HEALTHY", 1), ("WATCH", 2), ("HIGH_RISK", 1), ("CRITICAL", 1)]
    for idx, (tier, count) in enumerate(bands):
        y = 316 + idx * 56
        color = tier_color(tier)
        rounded(draw, (692, y, 1148, y + 40), (16, 25, 35), outline=rgba(color, 0.78), radius=18, width=2)
        draw.text((718, y + 9), tier.replace("_", " "), font=FONT_BODY, fill=color)
        draw.text((1098, y + 8), str(count), font=FONT_NUMBER, fill=(241, 244, 248))


DRAWERS = [
    scene_why,
    scene_active,
    scene_stack,
    scene_memory,
    scene_anomaly,
    scene_severity,
    scene_state,
    scene_morning,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (5, 10, 18))
    draw = ImageDraw.Draw(image, "RGBA")
    draw_background(draw, accent)
    draw_header(draw, scene_index, accent)
    DRAWERS[scene_index](draw, local_progress, accent)
    draw_footer(draw, SCENES[scene_index]["subtitle"], accent)
    frame = np.asarray(image, dtype=np.uint8).copy()
    del draw
    image.close()
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def make_audio(text: str, output_path: Path) -> None:
    safe = text.replace("'", "''")
    command = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.Rate = -1; "
        "$s.Volume = 100; "
        f"$out = '{str(output_path)}'; "
        "$s.SetOutputToWaveFile($out); "
        f"$s.Speak('{safe}'); "
        "$s.Dispose()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
    )


def concat_wavs(paths: list[Path], output_path: Path, gap_seconds: float) -> list[float]:
    params = None
    silence_frames = None
    durations: list[float] = []
    with wave.open(str(output_path), "wb") as out_handle:
        for index, path in enumerate(paths):
            with wave.open(str(path), "rb") as in_handle:
                if params is None:
                    params = in_handle.getparams()
                    out_handle.setparams(params)
                    silence_frames = b"\x00" * int(params.framerate * gap_seconds) * params.sampwidth * params.nchannels
                frames = in_handle.readframes(in_handle.getnframes())
                out_handle.writeframes(frames)
                duration = in_handle.getnframes() / float(in_handle.getframerate())
                total = max(duration + gap_seconds, MIN_SCENE_SECONDS)
                durations.append(total)
                padding = total - duration - gap_seconds
                if padding > 0:
                    extra = b"\x00" * int(params.framerate * padding) * params.sampwidth * params.nchannels
                    out_handle.writeframes(extra)
                if index < len(paths) - 1 and silence_frames is not None:
                    out_handle.writeframes(silence_frames)
    return durations


def build_silent_video(scene_durations: list[float], output_path: Path) -> None:
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open writer for {output_path}")
    try:
        for scene_index, duration in enumerate(scene_durations):
            frames = max(1, int(round(duration * FPS)))
            for frame in range(frames):
                progress = frame / max(frames - 1, 1)
                writer.write(render_frame(scene_index, progress))
                if frame % 30 == 0:
                    gc.collect()
    finally:
        writer.release()


def mux_video(video_path: Path, audio_path: Path, output_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "medium",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    run_dir = TEMP_DIR / f"run_{int(time.time())}"
    run_dir.mkdir(parents=True, exist_ok=True)

    audio_parts: list[Path] = []
    for index, scene in enumerate(SCENES, start=1):
        audio_path = run_dir / f"scene_{index:02d}.wav"
        make_audio(scene["narration"], audio_path)
        audio_parts.append(audio_path)

    combined_audio = run_dir / "nightly_refresh_anomalies_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "nightly_refresh_anomalies_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

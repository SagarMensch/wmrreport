from __future__ import annotations

import gc
import math
import shutil
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
OUTPUT_FILE = OUTPUT_DIR / "scenario-feature-dimensions-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 24
SCENE_GAP_SECONDS = 0.22
MIN_SCENE_SECONDS = 9.5

SCENES = [
    {
        "title": "Why Bashira Needs Feature Cards",
        "subtitle": "The model cannot think from raw chaos.",
        "code": "cpu_ml_orchestrator.py:233-264",
        "accent": "#F97316",
        "narration": "Before Bashira can score delay risk, it has to choose which clues matter. Those chosen clues are called features. In this topic we are not explaining the risk score itself. We are explaining the ten feature dimensions Bashira builds first, because those are the cards the model and the explainer both read.",
    },
    {
        "title": "Where The List Lives",
        "subtitle": "The ten feature names are written directly in code.",
        "code": "cpu_ml_orchestrator.py:233-264, 771-775",
        "accent": "#0EA5E9",
        "narration": "Bashira writes the feature list directly inside scenario feature cols. That code block defines the exact ten dimensions the system will use for the live delay model. So this list is not random and it is not changing per click. It is the contract for the live feature row.",
    },
    {
        "title": "Progress And Pace Features",
        "subtitle": "These clues tell the model how work is moving.",
        "code": "cpu_ml_orchestrator.py:233-264",
        "accent": "#2563EB",
        "narration": "The first family is progress and pace. Bashira measures current progress, recent momentum over three windows, and rig efficiency by week. These clues tell the model whether work is moving strongly, weakly, or falling behind.",
    },
    {
        "title": "Readiness Features",
        "subtitle": "These clues show whether the job is truly ready to move.",
        "code": "cpu_ml_orchestrator.py:233-264",
        "accent": "#8B5CF6",
        "narration": "The second family is readiness. Bashira checks material lead days, whether engineering has started, whether location work has started, and whether the rig is on. These clues matter because a well can look fine on paper but still be blocked in the real world.",
    },
    {
        "title": "Pressure And Timing Features",
        "subtitle": "These clues tell the model how crowded and time-tight the work is.",
        "code": "cpu_ml_orchestrator.py:233-264",
        "accent": "#EC4899",
        "narration": "The third family is pressure and timing. Bashira tracks cluster density, days to expected rig off, and schedule pressure. These clues tell the model whether the well is surrounded by congestion or running too tight against the plan.",
    },
    {
        "title": "How One Well Becomes X Live",
        "subtitle": "A well context is converted into one ordered feature row.",
        "code": "cpu_ml_orchestrator.py:771-775, 1270-1279",
        "accent": "#F43F5E",
        "narration": "When Bashira receives one well, it builds a context object and then turns that context into a feature row called X live. That row contains the ten feature dimensions in a fixed order. So the well is translated from business facts into model inputs.",
    },
    {
        "title": "Why Fixed Order Matters",
        "subtitle": "The same feature order feeds the risk model and SHAP.",
        "code": "cpu_ml_orchestrator.py:264, 771-775, 1273-1286",
        "accent": "#10B981",
        "narration": "After Bashira defines scenario feature cols, it copies that list into feature cols. That matters because the risk model and the SHAP explainer both read the same ordered columns. If the order changed, the model would read the wrong clue in the wrong slot.",
    },
    {
        "title": "The Big Picture",
        "subtitle": "These ten features are the live clue row behind the delay model.",
        "code": "cpu_ml_orchestrator.py:233-264, 771-775",
        "accent": "#F59E0B",
        "narration": "So this second topic is about structure, not prediction. Bashira first defines the ten feature dimensions, then turns a live well into one ordered row, and then sends that row into the risk model and SHAP. If you understand these ten cards, you understand what the live delay model is actually reading.",
    },
]

FEATURES = [
    ("progress", "Progress", "Overall work done"),
    ("recent_momentum_3w", "Recent momentum", "Recent weekly pace"),
    ("rig_efficiency_weekly", "Rig efficiency", "Typical rig pace"),
    ("cluster_density", "Cluster density", "Nearby work crowding"),
    ("material_lead_days", "Material lead days", "Waiting days for materials"),
    ("has_engineering_started", "Engineering started", "Readiness switch"),
    ("has_location_started", "Location started", "Site-readiness switch"),
    ("is_rig_on", "Rig on", "Rig already present"),
    ("days_to_expected_rig_off", "Days to rig off", "Time remaining"),
    ("schedule_pressure", "Schedule pressure", "Tightness versus plan"),
]

FEATURE_VALUES = {
    "progress": "0.62",
    "recent_momentum_3w": "0.04",
    "rig_efficiency_weekly": "0.05",
    "cluster_density": "4.0",
    "material_lead_days": "12",
    "has_engineering_started": "1",
    "has_location_started": "1",
    "is_rig_on": "0",
    "days_to_expected_rig_off": "9",
    "schedule_pressure": "0.78",
}

FEATURE_FAMILIES = [
    ("Progress And Pace", ["progress", "recent_momentum_3w", "rig_efficiency_weekly"]),
    ("Readiness", ["material_lead_days", "has_engineering_started", "has_location_started", "is_rig_on"]),
    ("Pressure And Timing", ["cluster_density", "days_to_expected_rig_off", "schedule_pressure"]),
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
def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/georgiab.ttf" if bold else "C:/Windows/Fonts/georgia.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


FONT_TAG = load_font(15, bold=True)
FONT_TITLE = load_font(44, bold=True)
FONT_SUB = load_font(22)
FONT_CARD = load_font(24, bold=True)
FONT_BODY = load_font(19)
FONT_SMALL = load_font(16)
FONT_CODE = load_font(15)


def rounded(draw: ImageDraw.ImageDraw, box, fill, outline=None, radius: int = 24, width: int = 1):
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


def text_block(draw: ImageDraw.ImageDraw, xy, text: str, font, fill, max_width: int, line_gap: int = 6) -> int:
    x, y = xy
    cursor = y
    for line in wrap_text(draw, text, font, max_width):
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += font.size + line_gap
    return cursor


def fit_text_block(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_lines: int, max_size: int, min_size: int, bold: bool) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str]]:
    for size in range(max_size, min_size - 1, -1):
        font = load_font(size, bold=bold)
        lines = wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
    font = load_font(min_size, bold=bold)
    lines = wrap_text(draw, text, font, max_width)
    return font, lines[:max_lines]


def draw_lines(draw: ImageDraw.ImageDraw, x: int, y: int, lines: list[str], font, fill, line_gap: int = 2) -> int:
    cursor = y
    for line in lines:
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += font.size + line_gap
    return cursor


def shadow_card(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, fill, outline, radius: int = 28):
    rounded(draw, (x + 8, y + 10, x + w + 8, y + h + 10), (8, 15, 28, 70), radius=radius)
    rounded(draw, (x, y, x + w, y + h), fill, outline=outline, radius=radius, width=2)


def draw_arrow(draw: ImageDraw.ImageDraw, start, end, color, width: int = 6):
    draw.line([start, end], fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = 16
    left = (
        end[0] - size * math.cos(angle - math.pi / 6),
        end[1] - size * math.sin(angle - math.pi / 6),
    )
    right = (
        end[0] - size * math.cos(angle + math.pi / 6),
        end[1] - size * math.sin(angle + math.pi / 6),
    )
    draw.polygon([end, left, right], fill=color)


def draw_card(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str, sub: str, accent, alpha: float = 1.0):
    shadow_card(draw, x, y, w, h, rgba((255, 255, 255), 0.95 * alpha), rgba(accent, 0.85 * alpha), radius=24)
    title_font, title_lines = fit_text_block(draw, title, w - 36, 2, 24, 15, True)
    title_bottom = draw_lines(draw, x + 18, y + 16, title_lines, title_font, rgba((15, 23, 42), alpha), line_gap=0)
    sub_font, sub_lines = fit_text_block(draw, sub, w - 36, 2, 19, 13, False)
    draw_lines(draw, x + 18, title_bottom + 8, sub_lines, sub_font, rgba((71, 85, 105), alpha), line_gap=2)


def draw_label(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    rounded(draw, (x, y, x + 180, y + 34), rgba(accent, 0.16), outline=rgba(accent, 0.45), radius=999, width=2)
    draw.text((x + 16, y + 8), text, font=FONT_TAG, fill=(*accent, 255))


def draw_meter(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, accent, value: float):
    rounded(draw, (x, y, x + w, y + 24), (226, 232, 240, 255), radius=999)
    rounded(draw, (x, y, x + int(w * clamp(value)), y + 24), (*accent, 255), radius=999)


def draw_code_panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, lines: list[str], accent):
    shadow_card(draw, x, y, w, h, (15, 23, 42, 245), rgba(accent, 0.52), radius=28)
    cursor = y + 20
    for line in lines:
        font, fitted = fit_text_block(draw, line, w - 36, 2, 17, 12, False)
        cursor = draw_lines(draw, x + 18, cursor, fitted, font, (224, 231, 255, 255), line_gap=1)
        cursor += 4


def draw_value_pill(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    rounded(draw, (x, y, x + 84, y + 30), rgba(accent, 0.14), outline=rgba(accent, 0.42), radius=999, width=2)
    font, lines = fit_text_block(draw, text, 64, 1, 15, 12, True)
    draw_lines(draw, x + 14, y + 7, lines, font, (*accent, 255), line_gap=0)


def draw_feature_row(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, label: str, key: str, value: str, accent, alpha: float = 1.0):
    shadow_card(draw, x, y, w, 46, rgba((255, 255, 255), 0.95 * alpha), rgba(accent, 0.55 * alpha), radius=18)
    draw_value_pill(draw, x + 12, y + 8, value, accent)
    title_font, title_lines = fit_text_block(draw, label, w - 160, 1, 19, 14, True)
    key_font, key_lines = fit_text_block(draw, key, w - 160, 1, 14, 11, False)
    draw_lines(draw, x + 112, y + 8, title_lines, title_font, rgba((15, 23, 42), alpha), line_gap=0)
    draw_lines(draw, x + 112, y + 26, key_lines, key_font, rgba((71, 85, 105), alpha), line_gap=0)


def background(draw: ImageDraw.ImageDraw, accent, progress: float, scene_index: int):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(9, 15, 31, 255))
    draw.rectangle((0, 0, WIDTH, 110), fill=(10, 16, 34, 255))
    orb_1_x = int(blend(980, 1130, progress))
    orb_2_x = int(blend(180, 110, progress))
    draw.ellipse((orb_1_x - 180, -80, orb_1_x + 180, 280), fill=rgba(accent, 0.12))
    draw.ellipse((orb_2_x - 140, 450, orb_2_x + 140, 730), fill=rgba((56, 189, 248), 0.10))
    for idx in range(18):
        px = 70 + idx * 64 + int(math.sin(progress * 3 + idx) * 12)
        py = 110 + (idx % 3) * 14 + int(math.cos(progress * 2 + idx) * 6)
        draw.ellipse((px, py, px + 4, py + 4), fill=(148, 163, 184, 90))
    draw.text((72, 58), SCENES[scene_index]["title"], font=FONT_TITLE, fill=(248, 250, 252, 255))
    draw.text((74, 112), SCENES[scene_index]["subtitle"], font=FONT_SUB, fill=(191, 219, 254, 255))
    draw_label(draw, 72, 24, "Animated Code Lesson", accent)
    shadow_card(draw, 860, 22, 356, 52, (15, 23, 42, 240), (51, 65, 85, 255), radius=18)
    code_font, code_lines = fit_text_block(draw, SCENES[scene_index]["code"], 326, 2, 15, 12, False)
    draw_lines(draw, 882, 31, code_lines, code_font, (148, 163, 184, 255), line_gap=0)
    start_x = 940
    for idx in range(len(SCENES)):
        fill = accent if idx == scene_index else (71, 85, 105)
        draw.ellipse((start_x + idx * 28, 84, start_x + idx * 28 + 12, 96), fill=(*fill, 255))


def footer(draw: ImageDraw.ImageDraw, text: str, accent):
    shadow_card(draw, 74, 626, 1132, 56, (12, 20, 36, 238), (30, 41, 59, 255), radius=24)
    draw.text((102, 643), text, font=FONT_SUB, fill=(241, 245, 249, 255))
    draw.text((1086, 643), "FEATURES", font=FONT_TAG, fill=(*accent, 255))


def scene_problem(draw: ImageDraw.ImageDraw, progress: float, accent):
    p = ease(progress)
    raw_x = int(blend(-280, 88, pop(p, 0.02, 0.24)))
    draw_card(draw, raw_x, 208, 260, 296, "Raw well facts", "Dates, crews, rig state, materials, and progress all arrive in different shapes.", accent)
    fact_lines = [
        "progress = 62%",
        "materials wait = 12 days",
        "rig off in 9 days",
        "engineering started = yes",
        "location started = yes",
    ]
    for idx, line in enumerate(fact_lines):
        show = pop(p, 0.10 + idx * 0.05, 0.18)
        shadow_card(draw, raw_x + 20, 292 + idx * 38, 214, 28, rgba(accent, 0.12 * show), rgba(accent, max(0.2, show)), radius=14)
        draw.text((raw_x + 34, 300 + idx * 38), line, font=FONT_SMALL, fill=rgba((15, 23, 42), max(0.35, show)))

    board_x = int(blend(1280, 420, pop(p, 0.18, 0.28)))
    shadow_card(draw, board_x, 228, 420, 246, (255, 255, 255, 252), rgba(accent, 0.55), radius=38)
    draw.text((board_x + 28, 260), "10 feature cards", font=FONT_CARD, fill=(*accent, 255))
    draw.text((board_x + 28, 298), "One fixed list the model can always read.", font=FONT_SUB, fill=(71, 85, 105, 255))
    sample_cards = [
        ("Progress", "work done", 0.36, 0, 0),
        ("Rig efficiency", "rig pace", 0.44, 1, 0),
        ("Material lead days", "wait time", 0.52, 0, 1),
        ("Schedule pressure", "plan tightness", 0.60, 1, 1),
    ]
    for label, key, delay, col, row in sample_cards:
        appear = pop(p, delay, 0.18)
        card_x = board_x + 28 + col * 188
        card_y = 334 + row * 92 - int((1 - appear) * 40)
        shadow_card(draw, card_x, card_y, 168, 84, rgba((255, 255, 255), 0.95 * max(0.18, appear)), rgba(accent, 0.55 * max(0.18, appear)), radius=24)
        label_font, label_lines = fit_text_block(draw, label, 128, 2, 22, 16, True)
        draw_lines(draw, card_x + 18, card_y + 18, label_lines, label_font, rgba((15, 23, 42), max(0.18, appear)), line_gap=0)

    if p > 0.32:
        draw_arrow(draw, (raw_x + 260, 354), (board_x, 354), (*accent, 255), width=6)

    model_x = int(blend(1380, 930, pop(p, 0.48, 0.24)))
    shadow_card(draw, model_x, 252, 222, 178, (14, 22, 40, 252), rgba(accent, 0.6), radius=32)
    draw.text((model_x + 32, 304), "Model", font=FONT_CARD, fill=(248, 250, 252, 255))
    draw.text((model_x + 32, 342), "and SHAP", font=FONT_CARD, fill=(248, 250, 252, 255))
    draw.text((model_x + 32, 392), "read the same feature cards", font=FONT_SMALL, fill=(148, 163, 184, 255))
    if p > 0.60:
        draw_arrow(draw, (board_x + 420, 354), (model_x, 354), (*accent, 255), width=6)


def scene_clues(draw: ImageDraw.ImageDraw, progress: float, accent):
    code_lines = ["_scenario_feature_cols = ["]
    for key, _, _ in FEATURES:
        code_lines.append(f"    '{key}',")
    code_lines.append("]")
    draw_code_panel(draw, 92, 182, 468, 376, code_lines, accent)

    grid = [
        (630, 186), (910, 186),
        (630, 266), (910, 266),
        (630, 346), (910, 346),
        (630, 426), (910, 426),
        (630, 506), (910, 506),
    ]
    for idx, ((key, label, sub), (x, y)) in enumerate(zip(FEATURES, grid)):
        show = pop(progress, 0.08 + idx * 0.05, 0.18)
        card_y = y - int((1 - show) * 26)
        shadow_card(draw, x, card_y, 248, 70, rgba((255, 255, 255), 0.95 * max(0.18, show)), rgba(accent, 0.55 * max(0.18, show)), radius=24)
        label_font, label_lines = fit_text_block(draw, label, 206, 2, 22, 15, True)
        draw_lines(draw, x + 18, card_y + 16, label_lines, label_font, rgba((15, 23, 42), max(0.18, show)), line_gap=0)


def scene_model(draw: ImageDraw.ImageDraw, progress: float, accent):
    family_keys = FEATURE_FAMILIES[0][1]
    y_positions = [194, 308, 422]
    for idx, key in enumerate(family_keys):
        label = next(label for feature_key, label, _ in FEATURES if feature_key == key)
        value = FEATURE_VALUES[key]
        show = pop(progress, 0.08 + idx * 0.08, 0.18)
        shadow_card(draw, 92, y_positions[idx], 286, 104, rgba((255, 255, 255), 0.95 * max(0.2, show)), rgba(accent, 0.55 * max(0.2, show)), radius=24)
        draw.text((114, y_positions[idx] + 16), label, font=FONT_CARD, fill=rgba((15, 23, 42), max(0.2, show)))
        draw.text((114, y_positions[idx] + 48), key, font=FONT_SMALL, fill=rgba((71, 85, 105), max(0.2, show)))
        draw_meter(draw, 114, y_positions[idx] + 72, 146, accent, min(1.0, float(value) if key == "progress" else float(value) * 8))
        draw_value_pill(draw, 276, y_positions[idx] + 68, value, accent)
        if show > 0.25:
            draw_arrow(draw, (378, y_positions[idx] + 54), (520, 360), rgba(accent, 0.90), width=5)

    draw.ellipse((500, 216, 826, 504), fill=rgba(accent, 0.14), outline=(*accent, 255), width=6)
    draw.text((560, 286), "How fast", font=FONT_CARD, fill=(248, 250, 252, 255))
    draw.text((552, 326), "is work moving?", font=FONT_CARD, fill=(248, 250, 252, 255))
    draw.text((580, 384), "pace family", font=FONT_SUB, fill=(191, 219, 254, 255))
    draw.arc((566, 260, 760, 454), start=210, end=330, fill=(248, 250, 252, 255), width=8)
    needle = int(blend(620, 722, pop(progress, 0.42, 0.24)))
    draw.line([(662, 356), (needle, 318)], fill=(248, 250, 252, 255), width=7)
    draw.ellipse((644, 338, 680, 374), fill=(248, 250, 252, 255))

    shadow_card(draw, 900, 266, 250, 170, (240, 249, 255, 255), rgba(accent, 0.55), radius=30)
    draw.text((928, 302), "Model learns", font=FONT_CARD, fill=(*accent, 255))
    text_block(draw, (928, 344), "If progress is slow, momentum is fading, and rig pace is weak, risk can rise quickly.", FONT_BODY, (51, 65, 85, 255), 194, line_gap=3)


def scene_shap(draw: ImageDraw.ImageDraw, progress: float, accent):
    cards = [
        ("Material lead days", "12 days waiting", 108, 210, 0.08),
        ("Engineering started", "Yes", 662, 210, 0.18),
        ("Location started", "Yes", 108, 386, 0.28),
        ("Rig on", "No", 662, 386, 0.38),
    ]
    for title, sub, x, y, delay in cards:
        show = pop(progress, delay, 0.18)
        draw_card(draw, x, y - int((1 - show) * 24), 264, 104, title, sub, accent, alpha=max(0.18, show))

    gate_p = pop(progress, 0.30, 0.24)
    shadow_card(draw, 440, 240, 392, 246, (255, 255, 255, 252), rgba(accent, 0.55), radius=42)
    draw.text((532, 280), "Ready to move?", font=FONT_CARD, fill=(*accent, 255))
    door_left = 474
    door_right = 666
    split = int(60 * gate_p)
    rounded(draw, (door_left - split, 334, 602 - split, 470), rgba(accent, 0.10), outline=rgba(accent, 0.45), radius=12, width=3)
    rounded(draw, (602 + split, 334, door_right + split, 470), rgba(accent, 0.10), outline=rgba(accent, 0.45), radius=12, width=3)
    draw.text((520, 506), "Readiness features tell the model whether work is truly unblocked.", font=FONT_BODY, fill=(248, 250, 252, 255))


def scene_class_one(draw: ImageDraw.ImageDraw, progress: float, accent):
    top_cards = [
        ("Cluster density", "4 nearby wells", 110, 196, 0.08),
        ("Days to rig off", "9 days left", 460, 196, 0.18),
        ("Schedule pressure", "0.78 tight", 810, 196, 0.28),
    ]
    for title, sub, x, y, delay in top_cards:
        show = pop(progress, delay, 0.18)
        draw_card(draw, x, y - int((1 - show) * 24), 250, 96, title, sub, accent, alpha=max(0.18, show))

    shadow_card(draw, 164, 356, 308, 154, (255, 255, 255, 252), rgba(accent, 0.55), radius=34)
    draw.text((202, 390), "Crowding", font=FONT_CARD, fill=(*accent, 255))
    cluster_points = [(250, 446), (312, 410), (358, 466), (408, 424), (438, 472)]
    for idx, (cx, cy) in enumerate(cluster_points):
        radius = 16 if idx == 0 else 12
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=rgba(accent, 0.24 + idx * 0.08), outline=(*accent, 255), width=3)

    shadow_card(draw, 512, 356, 260, 154, (255, 255, 255, 252), rgba(accent, 0.55), radius=34)
    draw.text((546, 390), "Clock", font=FONT_CARD, fill=(*accent, 255))
    draw.ellipse((580, 412, 704, 536), outline=(*accent, 255), width=6)
    draw.line([(642, 474), (642, 432)], fill=(*accent, 255), width=5)
    draw.line([(642, 474), (686, 494)], fill=(*accent, 255), width=5)

    shadow_card(draw, 814, 356, 280, 154, (255, 246, 246, 252), rgba(accent, 0.65), radius=34)
    draw.text((846, 390), "Pressure meter", font=FONT_CARD, fill=(*accent, 255))
    meter_show = pop(progress, 0.42, 0.22)
    draw_meter(draw, 846, 446, 196, accent, 0.78 * meter_show)
    draw.text((1060, 438), "78%", font=FONT_BODY, fill=(15, 23, 42, 255))


def scene_ranking(draw: ImageDraw.ImageDraw, progress: float, accent):
    shadow_card(draw, 92, 182, 292, 360, (255, 255, 255, 252), rgba(accent, 0.55), radius=36)
    draw.text((124, 214), "Well context", font=FONT_CARD, fill=(*accent, 255))
    context_lines = [
        "progress = 62%",
        "momentum = 0.04",
        "rig pace = 0.05",
        "materials = 12 days",
        "rig off = 9 days",
    ]
    for idx, line in enumerate(context_lines):
        shadow_card(draw, 120, 264 + idx * 50, 232, 34, rgba(accent, 0.10), rgba(accent, 0.35), radius=16)
        draw.text((138, 274 + idx * 50), line, font=FONT_SMALL, fill=(15, 23, 42, 255))

    draw_arrow(draw, (394, 360), (524, 360), (*accent, 255), width=6)
    shadow_card(draw, 520, 304, 172, 108, (15, 23, 42, 245), rgba(accent, 0.55), radius=26)
    draw.text((548, 334), "_build_", font=FONT_BODY, fill=(191, 219, 254, 255))
    draw.text((548, 364), "feature_frame", font=FONT_BODY, fill=(191, 219, 254, 255))

    shadow_card(draw, 728, 168, 460, 388, (15, 23, 42, 248), rgba(accent, 0.55), radius=34)
    draw.text((762, 202), "X_live", font=FONT_CARD, fill=(*accent, 255))
    for idx, (key, label, _) in enumerate(FEATURES):
        show = pop(progress, 0.10 + idx * 0.05, 0.16)
        y = 240 + idx * 30
        draw_feature_row(draw, 756, y, 404, f"{idx + 1}. {label}", key, FEATURE_VALUES[key], accent, alpha=max(0.2, show))


def scene_translation(draw: ImageDraw.ImageDraw, progress: float, accent):
    left_lines = [
        "_scenario_feature_cols",
        "[progress, recent_momentum_3w,",
        " rig_efficiency_weekly, ... ]",
    ]
    center_lines = [
        "_feature_cols =",
        "list(_scenario_feature_cols)",
    ]
    right_top = [
        "X_live[_feature_cols]",
        "_lgb_model.predict_proba(...)",
    ]
    right_bottom = [
        "X_live[_feature_cols]",
        "_explainer.shap_values(...)",
    ]
    draw_code_panel(draw, 104, 214, 282, 148, left_lines, accent)
    draw_code_panel(draw, 474, 254, 324, 104, center_lines, accent)
    draw_code_panel(draw, 876, 188, 286, 122, right_top, accent)
    draw_code_panel(draw, 876, 376, 286, 122, right_bottom, accent)
    draw_arrow(draw, (386, 288), (474, 306), (*accent, 255), width=6)
    draw_arrow(draw, (798, 306), (876, 248), (*accent, 255), width=6)
    draw_arrow(draw, (798, 306), (876, 436), (*accent, 255), width=6)
    draw.text((922, 324), "same order", font=FONT_SMALL, fill=(191, 219, 254, 255))
    draw.text((922, 512), "same order", font=FONT_SMALL, fill=(191, 219, 254, 255))

    ribbon_x = 146
    for idx in range(10):
        x = ribbon_x + idx * 88
        shadow_card(draw, x, 526, 74, 48, (248, 250, 252, 255), rgba(accent, 0.42), radius=16)
        draw.text((x + 26, 540), str(idx + 1), font=FONT_BODY, fill=(15, 23, 42, 255))
    draw.text((332, 592), "If the order changed, the model and SHAP would read the wrong clue in the wrong slot.", font=FONT_SUB, fill=(248, 250, 252, 255))


def scene_final(draw: ImageDraw.ImageDraw, progress: float, accent):
    columns = [
        ("Progress And Pace", ["Progress", "Recent momentum", "Rig efficiency"], 110),
        ("Readiness", ["Material lead days", "Engineering started", "Location started", "Rig on"], 430),
        ("Pressure And Timing", ["Cluster density", "Days to rig off", "Schedule pressure"], 790),
    ]
    for title, items, x in columns:
        shadow_card(draw, x, 186, 280, 328, (255, 255, 255, 252), rgba(accent, 0.55), radius=34)
        title_font, title_lines = fit_text_block(draw, title, 232, 2, 24, 17, True)
        draw_lines(draw, x + 24, 216, title_lines, title_font, (*accent, 255), line_gap=0)
        for idx, item in enumerate(items):
            shadow_card(draw, x + 18, 270 + idx * 58, 244, 44, (248, 250, 252, 255), rgba(accent, 0.40), radius=18)
            item_font, item_lines = fit_text_block(draw, item, 210, 1, 18, 13, True)
            draw_lines(draw, x + 34, 282 + idx * 58, item_lines, item_font, (15, 23, 42, 255), line_gap=0)

    shadow_card(draw, 244, 538, 792, 54, (15, 23, 42, 245), rgba(accent, 0.55), radius=24)
    draw.text((284, 556), "10 ordered feature cards -> one X_live row -> model prediction -> SHAP explanation", font=FONT_SUB, fill=(248, 250, 252, 255))


DRAWERS = [
    scene_problem,
    scene_clues,
    scene_model,
    scene_shap,
    scene_class_one,
    scene_ranking,
    scene_translation,
    scene_final,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    scene = SCENES[scene_index]
    accent = rgb(scene["accent"])
    image = Image.new("RGBA", (WIDTH, HEIGHT), (9, 15, 31, 255))
    draw = ImageDraw.Draw(image)
    background(draw, accent, local_progress, scene_index)
    DRAWERS[scene_index](draw, local_progress, accent)
    footer(draw, scene["subtitle"], accent)
    rgb_image = image.convert("RGB")
    frame = np.asarray(rgb_image, dtype=np.uint8).copy()
    rgb_image.close()
    image.close()
    del draw
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
                if frame % 120 == 0:
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

    combined_audio = run_dir / "scenario_feature_dimensions_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "scenario_feature_dimensions_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

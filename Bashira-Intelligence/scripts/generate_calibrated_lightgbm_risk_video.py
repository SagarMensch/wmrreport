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
OUTPUT_FILE = OUTPUT_DIR / "calibrated-lightgbm-risk-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 20
SCENE_GAP_SECONDS = 0.24
MIN_SCENE_SECONDS = 10.0

FEATURES = [
    "progress",
    "recent_momentum_3w",
    "rig_efficiency_weekly",
    "cluster_density",
    "material_lead_days",
    "has_engineering_started",
    "has_location_started",
    "is_rig_on",
    "days_to_expected_rig_off",
    "schedule_pressure",
]

RAW_POINTS = [(0.12, 0.07), (0.25, 0.21), (0.38, 0.33), (0.52, 0.49), (0.68, 0.71), (0.82, 0.88)]
CAL_POINTS = [(0.12, 0.10), (0.25, 0.24), (0.38, 0.38), (0.52, 0.53), (0.68, 0.69), (0.82, 0.82)]

SCENES = [
    {
        "title": "Why Bashira Trains A Delay Probability Model",
        "subtitle": "This model estimates the chance that a well will miss its expected rig-off date, not just whether it looks risky.",
        "code": "cpu_ml_orchestrator.py:246-289",
        "accent": "#3B82F6",
        "narration": "This model answers a very specific question. Will this well miss the expected rig off date? That is different from a generic risk label. Bashira builds a probability model so planners can reason in percentages, compare wells consistently, and later explain those percentages with SHAP.",
    },
    {
        "title": "Historical Wells Become Labeled Examples",
        "subtitle": "Rows are kept only when expected rig-off is known, the timing window is near the deadline, and the final actual date can define miss_target.",
        "code": "cpu_ml_orchestrator.py:266-289",
        "accent": "#2563EB",
        "narration": "Bashira turns historical wells into supervised examples. It keeps rows where the expected rig off date is known, and where days to expected rig off stays inside a focused minus fourteen to plus twenty eight day window. Then it defines miss target. If the final actual rig off date lands after the expected rig off date, the label is one. Otherwise it is zero.",
    },
    {
        "title": "The Model Reads Ten Live Delay Signals",
        "subtitle": "The probability engine reads ten live signals covering progress, momentum, readiness, timing, and schedule pressure.",
        "code": "cpu_ml_orchestrator.py:233-264",
        "accent": "#1D4ED8",
        "narration": "The calibrated risk model reads ten features. They mix current progress, recent momentum, historical rig efficiency, cluster density, material lead time, engineering start state, location start state, rig on state, days to expected rig off, and schedule pressure. This is the compact feature contract that the probability engine learns from.",
    },
    {
        "title": "Training Uses A Clean Stratified Split",
        "subtitle": "Bashira sends the labeled panel into an eighty-twenty train-test split while preserving the target mix.",
        "code": "cpu_ml_orchestrator.py:291-299",
        "accent": "#0EA5E9",
        "narration": "Next comes the train test split. Bashira uses an eighty twenty split with a fixed random state, and it stratifies on the miss target. That means the training side and the testing side keep a similar balance of missed and not missed cases. This matters because probability quality can look falsely good if the split is careless.",
    },
    {
        "title": "LightGBM Learns Nonlinear Delay Patterns",
        "subtitle": "A two-hundred-sixty-tree boosted classifier learns nonlinear interactions among progress, momentum, and schedule context.",
        "code": "cpu_ml_orchestrator.py:301-317",
        "accent": "#38BDF8",
        "narration": "Inside the calibrator sits a LightGBM classifier. Bashira gives it two hundred sixty trees, a point zero four learning rate, depth six, minimum child samples twenty five, and row and column subsampling. This is where the nonlinear learning happens. The trees discover combinations such as low progress plus high schedule pressure or weak momentum plus material drag.",
    },
    {
        "title": "Sigmoid Calibration Turns Scores Into Honest Probabilities",
        "subtitle": "A three-fold calibrator reshapes raw model confidence so predicted percentages align better with actual outcome frequency.",
        "code": "cpu_ml_orchestrator.py:301-316, 333-337",
        "accent": "#06B6D4",
        "narration": "Raw gradient boosting scores are not automatically trustworthy probabilities. So Bashira wraps the LightGBM classifier in a sigmoid calibrator with three fold cross validation. Calibration is the honesty layer. It reshapes raw confidence so that a predicted probability behaves more like a real frequency when you compare many wells.",
    },
    {
        "title": "AUC And Brier Audit The Model",
        "subtitle": "Bashira records ranking quality with AUC and probability honesty with Brier score on the held-out test set.",
        "code": "cpu_ml_orchestrator.py:333-337, 1351-1357",
        "accent": "#0891B2",
        "narration": "After prediction on the held out test set, Bashira records two health signals. AUC tells whether higher risk wells are ranked above lower risk wells. Brier tells whether the actual percentages are honest. A strong risk model needs both. Good ranking alone is not enough if the probabilities themselves are distorted.",
    },
    {
        "title": "Live Wells Are Scored With predict_proba",
        "subtitle": "Latest feature frames go through predict_proba, and the same columns then feed SHAP explanations.",
        "code": "cpu_ml_orchestrator.py:555-571, 1271-1288",
        "accent": "#0284C7",
        "narration": "Once trained, the model scores the latest feature frame using predict proba and takes the class one probability as delay risk percent. The same happens for one live well row in the detailed endpoint. Then SHAP reads the same feature columns to explain why that probability moved up or down. So this topic is the actual probability engine behind the explanations you already approved.",
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
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


FONT_TAG = load_font(16, bold=True, mono=True)
FONT_TITLE = load_font(38, bold=True)
FONT_SUB = load_font(22)
FONT_PANEL = load_font(27, bold=True)
FONT_BODY = load_font(19)
FONT_SMALL = load_font(15)
FONT_MONO = load_font(18, mono=True)
FONT_MONO_SMALL = load_font(15, mono=True)
FONT_NUMBER = load_font(56, bold=True, mono=True)
FONT_HUGE = load_font(70, bold=True, mono=True)
FONT_BIG = load_font(32, bold=True)
FONT_PROBA = load_font(42, bold=True, mono=True)


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


def panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, accent, fill_alpha: float = 0.9):
    rounded(draw, (x + 10, y + 12, x + w + 10, y + h + 12), (6, 18, 34, 112), radius=26)
    rounded(draw, (x, y, x + w, y + h), rgba((8, 18, 34), fill_alpha), outline=rgba(accent, 0.84), radius=26, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    width = draw.textbbox((0, 0), text, font=FONT_TAG)[2] + 28
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.15), outline=rgba(accent, 0.66), radius=999, width=2)
    draw.text((x + 14, y + 7), text, font=FONT_TAG, fill=(*accent, 255))


def draw_background(draw: ImageDraw.ImageDraw, accent):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(5, 12, 24))
    draw.ellipse((WIDTH - 290, -90, WIDTH + 80, 280), fill=rgba(accent, 0.12))
    draw.ellipse((-150, 500, 260, 920), fill=(12, 42, 82, 96))
    for y in range(180, 610, 38):
        draw.line((82, y, WIDTH - 82, y), fill=(24, 40, 62, 52), width=1)
    for x in range(110, WIDTH - 100, 96):
        draw.line((x, 182, x, 606), fill=(24, 40, 62, 34), width=1)


def draw_header(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    scene = SCENES[scene_index]
    draw_chip(draw, 92, 24, f"ML LAB 08 / STAGE {scene_index + 1:02d}", accent)
    draw.text((92, 84), scene["title"], font=FONT_TITLE, fill=(239, 244, 249))
    subtitle_font, subtitle_lines = fit_text_block(draw, scene["subtitle"], 1090, 2, 22, 18)
    draw_lines(draw, 92, 132, subtitle_lines, subtitle_font, (212, 224, 236), line_gap=2)
    for i in range(len(SCENES)):
        dot_x = 28 + i * 28
        dot_color = accent if i == scene_index else (47, 69, 92)
        draw.ellipse((dot_x, 152, dot_x + 18, 170), fill=dot_color)
    code_text = scene["code"]
    box_width = max(315, draw.textbbox((0, 0), code_text, font=FONT_MONO_SMALL)[2] + 42)
    panel(draw, WIDTH - box_width - 64, 22, box_width, 56, accent, fill_alpha=0.95)
    draw.text((WIDTH - box_width - 42, 40), code_text, font=FONT_MONO_SMALL, fill=(234, 241, 248))


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    panel(draw, 86, HEIGHT - 84, WIDTH - 172, 46, accent, fill_alpha=0.95)
    label = "LIGHTGBM RISK"
    label_width = draw.textbbox((0, 0), label, font=FONT_TAG)[2]
    footer_font, lines = fit_text_block(draw, text, WIDTH - 290 - label_width, 1, 22, 18)
    draw_lines(draw, 112, HEIGHT - 72, lines, footer_font, (239, 243, 248), line_gap=0)
    draw.text((WIDTH - 118 - label_width, HEIGHT - 69), label, font=FONT_TAG, fill=(*accent, 255))


def draw_curve(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], x: int, y: int, w: int, h: int, color, width: int = 4):
    px = []
    for rx, ry in points:
        px.append((x + rx * w, y + h - ry * h))
    if len(px) >= 2:
        draw.line(px, fill=color, width=width)
    for cx, cy in px:
        draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=color)


def scene_why(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 216, 414, 300, accent)
    draw.text((126, 246), "Question", font=FONT_PANEL, fill=(239, 244, 249))
    lines = [
        "Will this well miss",
        "its expected rig-off",
        "date?",
    ]
    draw_lines(draw, 126, 306, lines, FONT_BIG, (239, 244, 249), line_gap=0)
    draw.text((126, 446), "class 1 = miss target", font=FONT_MONO, fill=(*accent, 255))

    cx, cy = 802, 366
    for ring, alpha in [(150, 0.12), (115, 0.18), (82, 0.25)]:
        draw.ellipse((cx - ring, cy - ring, cx + ring, cy + ring), outline=rgba(accent, alpha), width=3)
    probability = blend(0, 73.4, pop(progress, 0.18))
    draw.text((708, 320), "delay risk", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((684, 372), f"{probability:04.1f}%", font=FONT_HUGE, fill=(*accent, 255))
    draw.text((734, 452), "probability, not just a label", font=FONT_BODY, fill=(214, 224, 236))


def scene_labels(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Supervised label factory", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((122, 286), "keep rows near deadline, then compare final actual rig-off against expected rig-off", font=FONT_MONO_SMALL, fill=(*accent, 255))

    gates = [
        ("expected rig-off known", "required"),
        ("days_to_expected_rig_off", "-14 to +28"),
        ("final actual rig-off", "defines label"),
    ]
    for idx, (label, note) in enumerate(gates):
        x = 122 + idx * 242
        local = pop(progress, 0.06 + idx * 0.08)
        rounded(draw, (x, 340, x + 200, 88 + 340), rgba(accent, 0.08 + 0.14 * local), outline=rgba(accent, 0.76), radius=20, width=2)
        font, lines = fit_text_block(draw, label, 164, 2, 22, 18, bold=True)
        draw_lines(draw, x + 18, 362, lines, font, (239, 244, 249), line_gap=4)
        draw.text((x + 18, 426), note, font=FONT_MONO_SMALL, fill=(212, 224, 236))

    panel(draw, 872, 320, 264, 180, accent)
    draw.text((900, 346), "miss_target", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((900, 392), "actual > expected -> 1", font=FONT_MONO, fill=(250, 190, 190))
    draw.text((900, 430), "actual <= expected -> 0", font=FONT_MONO, fill=(186, 233, 202))


def scene_features(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Ten-feature assay tray", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((122, 286), "this exact feature contract becomes both the live scoring frame and the SHAP frame", font=FONT_MONO_SMALL, fill=(*accent, 255))
    for idx, feature in enumerate(FEATURES):
        row = idx % 5
        col = idx // 5
        x = 126 + col * 510
        y = 332 + row * 42
        local = pop(progress, 0.05 + idx * 0.05)
        rounded(draw, (x, y, x + 440, y + 30), rgba(accent, 0.08 + 0.10 * local), outline=rgba(accent, 0.72), radius=15, width=2)
        draw.text((x + 16, y + 7), feature, font=FONT_MONO_SMALL, fill=(239, 244, 249))


def scene_split(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 520, 324, accent)
    draw.text((126, 246), "train_test_split", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((126, 286), "test_size = 0.2, stratify = miss_target", font=FONT_MONO_SMALL, fill=(*accent, 255))
    rounded(draw, (136, 350, 518, 402), (16, 36, 58), radius=20)
    split_x = int(blend(136, 136 + 382 * 0.8, pop(progress, 0.10)))
    rounded(draw, (136, 350, split_x, 402), rgba(accent, 0.90), radius=20)
    draw.text((216, 362), "train 80%", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((450, 362), "test 20%", font=FONT_MONO_SMALL, fill=(214, 224, 236))
    draw.text((142, 444), "same class balance on both sides", font=FONT_BODY, fill=(214, 224, 236))

    panel(draw, 682, 214, 496, 324, accent)
    draw.text((712, 246), "Why stratify matters", font=FONT_PANEL, fill=(239, 244, 249))
    bullets = [
        "miss and non-miss cases stay balanced",
        "held-out metrics reflect real ranking quality",
        "calibration is tested on a fair slice",
    ]
    for idx, bullet in enumerate(bullets):
        y = 322 + idx * 68
        draw.ellipse((714, y + 7, 730, y + 23), fill=(*accent, 255))
        font, lines = fit_text_block(draw, bullet, 404, 2, 20, 17)
        draw_lines(draw, 748, y, lines, font, (214, 224, 236), line_gap=4)


def scene_lgbm(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 214, 500, 324, accent)
    draw.text((122, 246), "LightGBM core", font=FONT_PANEL, fill=(239, 244, 249))
    params = [
        "n_estimators = 260",
        "learning_rate = 0.04",
        "max_depth = 6",
        "min_child_samples = 25",
        "subsample = 0.9",
        "colsample_bytree = 0.85",
    ]
    for idx, line in enumerate(params):
        y = 304 + idx * 32
        draw.text((126, y), line, font=FONT_MONO_SMALL, fill=(214, 224, 236))

    cx, cy = 874, 378
    panel(draw, 660, 214, 520, 324, accent)
    draw.text((690, 246), "Tree interactions", font=FONT_PANEL, fill=(239, 244, 249))
    for idx in range(6):
        x = 718 + (idx % 3) * 138
        y = 318 + (idx // 3) * 118
        local = pop(progress, 0.06 + idx * 0.07)
        draw.line((x, y, x, y + 50), fill=rgba(accent, 0.80), width=4)
        draw.line((x, y + 18, x - 20, y), fill=rgba(accent, 0.80), width=4)
        draw.line((x, y + 18, x + 20, y), fill=rgba(accent, 0.80), width=4)
        draw.line((x, y + 42, x - 18, y + 26), fill=rgba(accent, 0.65 + 0.25 * local), width=3)
        draw.line((x, y + 42, x + 18, y + 26), fill=rgba(accent, 0.65 + 0.25 * local), width=3)
    draw.text((752, 482), "progress + momentum + schedule", font=FONT_BODY, fill=(214, 224, 236))


def scene_calibration(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Calibration deck", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((122, 286), "CalibratedClassifierCV(method='sigmoid', cv=3)", font=FONT_MONO, fill=(*accent, 255))

    chart_x, chart_y, chart_w, chart_h = 136, 330, 526, 180
    draw.line((chart_x, chart_y + chart_h, chart_x + chart_w, chart_y + chart_h), fill=(194, 209, 224), width=3)
    draw.line((chart_x, chart_y + chart_h, chart_x, chart_y), fill=(194, 209, 224), width=3)
    draw.line((chart_x, chart_y + chart_h, chart_x + chart_w, chart_y), fill=(98, 119, 142), width=2)
    draw_curve(draw, RAW_POINTS, chart_x, chart_y, chart_w, chart_h, rgb("#F97316"))
    draw_curve(draw, CAL_POINTS, chart_x, chart_y, chart_w, chart_h, rgb("#38BDF8"))
    draw.text((420, 328), "raw", font=FONT_MONO_SMALL, fill=rgb("#F97316"))
    draw.text((470, 348), "calibrated", font=FONT_MONO_SMALL, fill=rgb("#38BDF8"))
    draw.text((180, 528), "predicted probability", font=FONT_SMALL, fill=(214, 224, 236))
    draw.text((28, 382), "observed", font=FONT_SMALL, fill=(214, 224, 236))

    panel(draw, 744, 300, 398, 210, accent)
    draw.text((774, 332), "What calibration fixes", font=FONT_PANEL, fill=(239, 244, 249))
    bullets = [
        "raw model confidence can be too sharp",
        "sigmoid layer bends it toward real frequencies",
        "reported percentages become more trustworthy",
    ]
    for idx, bullet in enumerate(bullets):
        y = 386 + idx * 38
        font, lines = fit_text_block(draw, bullet, 336, 2, 18, 16)
        draw_lines(draw, 774, y, lines, font, (214, 224, 236), line_gap=2)


def scene_metrics(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 1088, 324, accent)
    draw.text((126, 246), "Held-out model audit", font=FONT_PANEL, fill=(239, 244, 249))
    cards = [
        ("AUC", "ranking quality", "higher-risk wells should score above lower-risk wells"),
        ("Brier", "probability honesty", "predicted percentages should match actual frequencies"),
    ]
    for idx, (title, label, note) in enumerate(cards):
        x = 148 + idx * 486
        panel(draw, x, 302, 380, 186, accent)
        draw.text((x + 30, 330), title, font=FONT_HUGE, fill=(*accent, 255))
        draw.text((x + 30, 404), label, font=FONT_PANEL, fill=(239, 244, 249))
        font, lines = fit_text_block(draw, note, 320, 3, 18, 16)
        draw_lines(draw, x + 30, 444, lines, font, (214, 224, 236), line_gap=3)


def scene_live(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Live scoring path", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((122, 286), "latest[_feature_cols] -> predict_proba -> class 1 probability -> SHAP on same frame", font=FONT_MONO_SMALL, fill=(*accent, 255))

    panel(draw, 120, 332, 290, 146, accent)
    draw.text((148, 362), "X_live", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((148, 404), "10-feature row", font=FONT_MONO, fill=(214, 224, 236))

    panel(draw, 478, 320, 320, 172, accent)
    draw.text((508, 348), "predict_proba", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((508, 396), "[class 0, class 1]", font=FONT_MONO, fill=(214, 224, 236))
    draw.text((508, 432), "[0.31, 0.69]", font=FONT_PROBA, fill=(*accent, 255))

    panel(draw, 872, 320, 274, 172, accent)
    draw.text((902, 348), "delay risk", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((902, 398), "69.0%", font=FONT_NUMBER, fill=(239, 244, 249))
    draw.text((902, 452), "same frame -> SHAP", font=FONT_MONO_SMALL, fill=(*accent, 255))

    for idx in range(2):
        x1 = 410 + idx * 388
        x2 = 478 + idx * 394
        y = 404
        local = pop(progress, 0.08 + idx * 0.12)
        draw.line((x1, y, blend(x1, x2, local), y), fill=rgba(accent, 0.85), width=7)
        draw.polygon(
            [
                (blend(x1, x2, local), y),
                (blend(x1, x2, local) - 18, y - 10),
                (blend(x1, x2, local) - 18, y + 10),
            ],
            fill=rgba(accent, 0.95),
        )


DRAWERS = [
    scene_why,
    scene_labels,
    scene_features,
    scene_split,
    scene_lgbm,
    scene_calibration,
    scene_metrics,
    scene_live,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (5, 12, 24))
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
                image = render_frame(scene_index, progress)
                writer.write(image)
                del image
                if frame % 5 == 0:
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

    combined_audio = run_dir / "calibrated_lightgbm_delay_risk_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "calibrated_lightgbm_delay_risk_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

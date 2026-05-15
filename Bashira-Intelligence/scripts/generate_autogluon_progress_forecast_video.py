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
OUTPUT_FILE = OUTPUT_DIR / "autogluon-progress-forecast-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 24
SCENE_GAP_SECONDS = 0.22
MIN_SCENE_SECONDS = 10.0

SCENES = [
    {
        "title": "What This Model Predicts",
        "subtitle": "AutoGluon forecasts progress four weeks ahead, not the final finish date.",
        "code": "feature_engine.py:35-37, 491-508, 651-678",
        "accent": "#14B8A6",
        "narration": "This third topic is about the AutoGluon forecast engine. Bashira is not asking this model for a final completion date. It is asking a narrower question. If we look four weeks ahead, what progress percentage should this well reach?",
    },
    {
        "title": "Open The Saved Brain",
        "subtitle": "The predictor is loaded from the saved ag_model artifact on disk.",
        "code": "feature_engine.py:156-172",
        "accent": "#22C55E",
        "narration": "At startup Bashira opens the saved AutoGluon model from the ag model folder. The code calls TabularPredictor load, keeps the predictor in memory, and records the best trained member inside that saved bundle.",
    },
    {
        "title": "Build The 58-Feature Frame",
        "subtitle": "The predictor only accepts the exact engineered columns it was trained on.",
        "code": "feature_engine.py:58-82, 325-337, 474-487",
        "accent": "#06B6D4",
        "narration": "Before Bashira can forecast, it must build the exact fifty eight feature columns listed in feature names. Raw well facts are transformed into one engineered row. Missing values are filled from training medians so the model always receives a complete table.",
    },
    {
        "title": "History Becomes Motion Signals",
        "subtitle": "Lag, velocity, acceleration, and rolling pace are derived from ordered weekly history.",
        "code": "feature_engine.py:401-449",
        "accent": "#3B82F6",
        "narration": "One important part of the frame is motion. Bashira sorts historical weekly progress, then builds lag one, lag two, lag four, one week velocity, two week velocity, acceleration, rolling pace, remaining work, and momentum score. This is how the model sees movement, not just one frozen snapshot.",
    },
    {
        "title": "Call The Predictor",
        "subtitle": "The 58-column frame is passed into AutoGluon and clipped to the safe 0-to-1 scale.",
        "code": "feature_engine.py:491-508",
        "accent": "#8B5CF6",
        "narration": "Once the feature frame is ready, Bashira calls self ag predictor predict on that dataframe. The returned values are clipped between zero and one, because progress is a percentage scale and the forecast should stay inside valid bounds.",
    },
    {
        "title": "Project Four Weeks Forward",
        "subtitle": "The output is translated from 0-to-1 model scale into percent progress at week plus four.",
        "code": "feature_engine.py:671-678",
        "accent": "#F59E0B",
        "narration": "Inside predict well, Bashira converts the AutoGluon output into percent progress. In this lesson example, the well is at sixty two percent now and the forecast says seventy four percent after four weeks. That means the predicted delta is plus twelve progress points.",
    },
    {
        "title": "Write It Into The Result",
        "subtitle": "The forecast is stored as predicted_progress_4w and predicted_delta_4w in the well response.",
        "code": "feature_engine.py:657-678",
        "accent": "#F97316",
        "narration": "The forecast is not left inside the model call. Bashira writes it back into the result packet as predicted progress four w and predicted delta four w. That lets the rest of the system display near term movement in plain business language.",
    },
    {
        "title": "Why This Forecast Matters",
        "subtitle": "The four-week forecast becomes a near-term movement signal before the rest of the stack acts.",
        "code": "feature_engine.py:646-711",
        "accent": "#FB7185",
        "narration": "So the AutoGluon path is simple but important. Load the saved predictor, engineer the exact fifty eight feature row, forecast progress four weeks ahead, convert it into percent and delta, and attach it to the live well output. That is how Bashira turns raw monitoring rows into a near term progress view.",
    },
]

FEATURE_BUNDLES = [
    ("Calendar", ["days_since_start", "start_month", "rig_duration_days"]),
    ("Geography", ["northing", "easting", "dist_from_centroid"]),
    ("Location Prep", ["access_road_5", "loc_prep_composite", "ohl_progress"]),
    ("Motion", ["progress_lag1", "progress_velocity_1w", "momentum_score"]),
    ("Encodings", ["rig_no_te", "week_hist_mean", "well_type_enc"]),
]

WEEKLY_PROGRESS = [0.36, 0.44, 0.51, 0.58, 0.62]
FORECAST_CURVE = [0.62, 0.66, 0.69, 0.72, 0.74]
RESULT_LINES = [
    '"well_name": "Well-A17",',
    '"current_progress_pct": 62.0,',
    '"predicted_progress_4w": 74.0,',
    '"predicted_delta_4w": 12.0,',
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


FONT_TRACK = load_font(16, bold=True, mono=True)
FONT_TITLE = load_font(40, bold=True)
FONT_SUB = load_font(23)
FONT_PANEL = load_font(30, bold=True)
FONT_BODY = load_font(20)
FONT_SMALL = load_font(16)
FONT_CODE = load_font(16, mono=True)
FONT_MONO = load_font(20, mono=True)
FONT_MONO_SMALL = load_font(16, mono=True)
FONT_NUMBER = load_font(42, bold=True, mono=True)


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


def fit_text_block(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_lines: int, max_size: int, min_size: int, *, bold: bool = False, mono: bool = False):
    for size in range(max_size, min_size - 1, -1):
        font = load_font(size, bold=bold, mono=mono)
        lines = wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
    font = load_font(min_size, bold=bold, mono=mono)
    return font, wrap_text(draw, text, font, max_width)[:max_lines]


def draw_lines(draw: ImageDraw.ImageDraw, x: int, y: int, lines: list[str], font, fill, line_gap: int = 2) -> int:
    cursor = y
    for line in lines:
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += font.size + line_gap
    return cursor


def text_block(draw: ImageDraw.ImageDraw, xy, text: str, font, fill, max_width: int, line_gap: int = 4) -> int:
    x, y = xy
    cursor = y
    for line in wrap_text(draw, text, font, max_width):
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += font.size + line_gap
    return cursor


def neon_panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, accent, radius: int = 24, fill_alpha: float = 0.92):
    rounded(draw, (x + 8, y + 10, x + w + 8, y + h + 10), (3, 8, 18, 110), radius=radius)
    rounded(draw, (x, y, x + w, y + h), rgba((11, 18, 32), fill_alpha), outline=rgba(accent, 0.82), radius=radius, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent, *, mono: bool = False):
    font = FONT_TRACK if mono else FONT_SMALL
    width = draw.textbbox((0, 0), text, font=font)[2] + 28
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.14), outline=rgba(accent, 0.58), radius=999, width=2)
    draw.text((x + 14, y + 7), text, font=font, fill=(*accent, 255))


def draw_arrow(draw: ImageDraw.ImageDraw, start, end, color, width: int = 5):
    draw.line([start, end], fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = 14
    left = (
        end[0] - size * math.cos(angle - math.pi / 6),
        end[1] - size * math.sin(angle - math.pi / 6),
    )
    right = (
        end[0] - size * math.cos(angle + math.pi / 6),
        end[1] - size * math.sin(angle + math.pi / 6),
    )
    draw.polygon([end, left, right], fill=color)


def draw_header(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    scene = SCENES[scene_index]
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(6, 12, 24, 255))
    for x in range(80, WIDTH, 64):
        draw.line([(x, 0), (x, HEIGHT)], fill=(14, 24, 42, 160), width=1)
    for y in range(110, HEIGHT, 56):
        draw.line([(72, y), (WIDTH - 48, y)], fill=(14, 24, 42, 120), width=1)
    draw.rectangle((0, 0, 72, HEIGHT), fill=(4, 9, 18, 255))
    for idx in range(len(SCENES)):
        fill = rgba(accent, 0.9 if idx == scene_index else 0.18)
        rounded(draw, (22, 144 + idx * 48, 50, 170 + idx * 48), fill, radius=8)
    draw_chip(draw, 94, 28, f"TRACK 03 / SCENE {scene_index + 1:02d}", accent, mono=True)
    draw.text((94, 78), scene["title"], font=FONT_TITLE, fill=(241, 245, 249, 255))
    draw.text((96, 126), scene["subtitle"], font=FONT_SUB, fill=(165, 243, 252, 255))
    neon_panel(draw, 862, 26, 360, 56, accent, radius=20, fill_alpha=0.82)
    code_font, code_lines = fit_text_block(draw, scene["code"], 320, 2, 16, 13, mono=True)
    draw_lines(draw, 886, 38, code_lines, code_font, (148, 163, 184, 255), line_gap=0)
    draw.ellipse((948, -84, 1286, 254), fill=rgba(accent, 0.10))
    draw.ellipse((12, 480, 332, 800), fill=rgba((59, 130, 246), 0.08))


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    neon_panel(draw, 92, 638, 1100, 46, accent, radius=22, fill_alpha=0.88)
    draw.text((118, 652), text, font=FONT_BODY, fill=(226, 232, 240, 255))
    draw.text((1046, 652), "AUTOGLUON", font=FONT_TRACK, fill=(*accent, 255))


def draw_spark_track(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, weeks: list[str], current_idx: int, future_idx: int, accent):
    draw.line([(x, y), (x + w, y)], fill=(71, 85, 105, 255), width=6)
    step = w / (len(weeks) - 1)
    for idx, label in enumerate(weeks):
        px = x + idx * step
        fill = (*accent, 255) if idx <= future_idx else (51, 65, 85, 255)
        draw.ellipse((px - 10, y - 10, px + 10, y + 10), fill=fill)
        draw.text((px - 18, y + 24), label, font=FONT_SMALL, fill=(148, 163, 184, 255))
    cx = x + current_idx * step
    fx = x + future_idx * step
    draw.line([(cx, y), (fx, y)], fill=(*accent, 255), width=8)


def draw_forecast_chart(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, values: list[float], accent, future_start: int = 1):
    neon_panel(draw, x, y, w, h, accent, radius=30, fill_alpha=0.78)
    chart_x0 = x + 62
    chart_y0 = y + h - 58
    chart_x1 = x + w - 42
    chart_y1 = y + 50
    for idx in range(5):
        gy = chart_y0 - idx * ((chart_y0 - chart_y1) / 4)
        draw.line([(chart_x0, gy), (chart_x1, gy)], fill=(30, 41, 59, 255), width=1)
        label = f"{int(idx * 25)}%"
        draw.text((x + 14, gy - 10), label, font=FONT_SMALL, fill=(148, 163, 184, 255))
    draw.line([(chart_x0, chart_y0), (chart_x1, chart_y0)], fill=(71, 85, 105, 255), width=2)
    draw.line([(chart_x0, chart_y0), (chart_x0, chart_y1)], fill=(71, 85, 105, 255), width=2)
    points = []
    for idx, value in enumerate(values):
        px = chart_x0 + idx * ((chart_x1 - chart_x0) / (len(values) - 1))
        py = chart_y0 - value * (chart_y0 - chart_y1)
        points.append((px, py))
        label = f"W+{idx}" if idx else "Now"
        draw.text((px - 18, chart_y0 + 18), label, font=FONT_SMALL, fill=(148, 163, 184, 255))
    for start, end in zip(points, points[1:]):
        draw.line([start, end], fill=(*accent, 255), width=6)
    for idx, (px, py) in enumerate(points):
        fill = (*accent, 255) if idx >= future_start else (241, 245, 249, 255)
        draw.ellipse((px - 8, py - 8, px + 8, py + 8), fill=fill, outline=(241, 245, 249, 255), width=2)
        draw.text((px - 18, py - 34), f"{int(values[idx] * 100)}", font=FONT_SMALL, fill=(241, 245, 249, 255))


def scene_question(draw: ImageDraw.ImageDraw, progress: float, accent):
    p = ease(progress)
    neon_panel(draw, 96, 192, 274, 204, accent, radius=28)
    draw.text((122, 224), "Live well", font=FONT_PANEL, fill=(241, 245, 249, 255))
    draw.text((122, 272), "Week 18 snapshot", font=FONT_BODY, fill=(148, 163, 184, 255))
    draw.text((122, 322), "Current progress", font=FONT_SMALL, fill=(148, 163, 184, 255))
    draw.text((122, 346), "62%", font=FONT_NUMBER, fill=(*accent, 255))
    neon_panel(draw, 412, 206, 314, 130, accent, radius=26, fill_alpha=0.76)
    draw_chip(draw, 436, 226, "TARGET_COL", accent, mono=True)
    draw.text((436, 270), "target_lead_4w", font=FONT_MONO, fill=(241, 245, 249, 255))
    draw.text((436, 304), "Progress percentage after 4 weeks", font=FONT_BODY, fill=(148, 163, 184, 255))
    neon_panel(draw, 816, 192, 368, 204, accent, radius=28)
    draw.text((842, 224), "Forecast question", font=FONT_PANEL, fill=(241, 245, 249, 255))
    text_block(draw, (842, 276), "Where should progress land four weeks from now if the trained AutoGluon model reads the latest engineered row?", FONT_BODY, (201, 210, 222, 255), 308)
    draw_spark_track(draw, 170, 488, 900, ["Now", "+1w", "+2w", "+3w", "+4w"], 0, int(blend(0, 4, pop(p, 0.34, 0.34))), accent)
    glow_x = int(blend(170, 1070, pop(p, 0.34, 0.34)))
    draw.ellipse((glow_x - 14, 474, glow_x + 14, 502), fill=(*accent, 255))
    draw.text((996, 532), "74% target zone", font=FONT_BODY, fill=(241, 245, 249, 255))


def scene_model_load(draw: ImageDraw.ImageDraw, progress: float, accent):
    neon_panel(draw, 92, 184, 336, 364, accent, radius=28)
    draw.text((120, 216), "wmr_results/", font=FONT_MONO, fill=(241, 245, 249, 255))
    entries = [
        ("ag_model/", True),
        ("features_train.csv", False),
        ("priority_wells_final.csv", False),
        ("survival_predictions.csv", False),
        ("feature_importance.csv", False),
    ]
    for idx, (label, hot) in enumerate(entries):
        y = 270 + idx * 48
        fill = rgba(accent, 0.14) if hot else (0, 0, 0, 0)
        rounded(draw, (116, y - 6, 394, y + 28), fill, outline=rgba(accent, 0.60 if hot else 0.18), radius=14, width=2)
        draw.text((136, y), label, font=FONT_MONO_SMALL, fill=(*accent, 255) if hot else (201, 210, 222, 255))
    draw_arrow(draw, (432, 364), (560, 364), (*accent, 255), width=6)
    neon_panel(draw, 540, 222, 260, 276, accent, radius=32, fill_alpha=0.72)
    draw.text((576, 262), "Tabular", font=FONT_PANEL, fill=(241, 245, 249, 255))
    draw.text((576, 304), "Predictor", font=FONT_PANEL, fill=(241, 245, 249, 255))
    draw.text((576, 350), "load(ag_path)", font=FONT_MONO, fill=(*accent, 255))
    draw.text((576, 392), "Saved AutoGluon bundle", font=FONT_BODY, fill=(148, 163, 184, 255))
    neon_panel(draw, 858, 250, 296, 188, accent, radius=28)
    draw.text((886, 286), "After load", font=FONT_PANEL, fill=(241, 245, 249, 255))
    draw.text((886, 336), "self.ag_predictor", font=FONT_MONO, fill=(*accent, 255))
    draw.text((886, 378), "best trained member", font=FONT_BODY, fill=(148, 163, 184, 255))
    draw_chip(draw, 886, 414, "get_model_best()", accent, mono=True)


def scene_feature_frame(draw: ImageDraw.ImageDraw, progress: float, accent):
    for idx, (title, feats) in enumerate(FEATURE_BUNDLES):
        x = 90
        y = 170 + idx * 92
        show = pop(progress, 0.06 + idx * 0.08, 0.18)
        neon_panel(draw, x, y, 270, 72, accent, radius=22, fill_alpha=0.74)
        draw.text((116, y + 12), title, font=FONT_BODY, fill=(*accent, 255))
        feat_text = "   ".join(feats[:2]) if idx != 2 else "   ".join(feats)
        text_block(draw, (116, y + 38), feat_text, FONT_MONO_SMALL, (226, 232, 240, 255), 230, line_gap=0)
        if show > 0.2:
            draw_arrow(draw, (364, y + 36), (520, 360), rgba(accent, 0.88), width=5)
    neon_panel(draw, 480, 212, 316, 304, accent, radius=34, fill_alpha=0.72)
    draw.text((544, 250), "58", font=load_font(82, bold=True, mono=True), fill=(*accent, 255))
    draw.text((536, 332), "engineered", font=FONT_PANEL, fill=(241, 245, 249, 255))
    draw.text((530, 372), "feature columns", font=FONT_PANEL, fill=(241, 245, 249, 255))
    for idx in range(12):
        px = 524 + (idx % 4) * 56
        py = 430 + (idx // 4) * 32
        rounded(draw, (px, py, px + 40, py + 18), rgba(accent, 0.18), outline=rgba(accent, 0.52), radius=8, width=2)
    draw_arrow(draw, (802, 360), (920, 360), (*accent, 255), width=6)
    neon_panel(draw, 902, 222, 286, 276, accent, radius=28)
    draw.text((930, 256), "features_df", font=FONT_MONO, fill=(241, 245, 249, 255))
    draw.text((930, 300), "shape: [1, 58]", font=FONT_MONO, fill=(*accent, 255))
    sample_lines = [
        "northing  easting  days_since_start",
        "progress_lag1  progress_velocity_1w",
        "momentum_score  week_hist_mean",
        "rig_no_te  well_type_enc  ...",
    ]
    cursor = 352
    for line in sample_lines:
        draw.text((930, cursor), line, font=FONT_MONO_SMALL, fill=(201, 210, 222, 255))
        cursor += 34


def scene_motion(draw: ImageDraw.ImageDraw, progress: float, accent):
    draw_forecast_chart(draw, 86, 190, 710, 332, WEEKLY_PROGRESS, accent, future_start=0)
    points = []
    chart_x0 = 148
    chart_y0 = 464
    chart_x1 = 754
    chart_y1 = 240
    for idx, value in enumerate(WEEKLY_PROGRESS):
        px = chart_x0 + idx * ((chart_x1 - chart_x0) / (len(WEEKLY_PROGRESS) - 1))
        py = chart_y0 - value * (chart_y0 - chart_y1)
        points.append((px, py))
    labels = [("lag4", 0), ("lag2", 2), ("lag1", 3), ("now", 4)]
    for text, idx in labels:
        px, py = points[idx]
        draw_chip(draw, int(px - 30), int(py - 74), text, accent, mono=True)
        draw_arrow(draw, (px, py - 32), (px, py - 10), rgba(accent, 0.90), width=4)
    neon_panel(draw, 842, 204, 346, 308, accent, radius=30)
    draw.text((872, 236), "Motion signals", font=FONT_PANEL, fill=(241, 245, 249, 255))
    metrics = [
        ("velocity_1w", "+0.04"),
        ("velocity_2w", "+0.11"),
        ("acceleration", "+0.01"),
        ("rolling3w", "0.51"),
        ("momentum_score", "0.05"),
    ]
    for idx, (label, value) in enumerate(metrics):
        y = 294 + idx * 42
        draw.text((876, y), label, font=FONT_MONO_SMALL, fill=(165, 243, 252, 255))
        draw.text((1078, y), value, font=FONT_MONO_SMALL, fill=(241, 245, 249, 255))
    draw.text((872, 506), "History is converted into motion clues.", font=FONT_BODY, fill=(201, 210, 222, 255))


def scene_predictor_call(draw: ImageDraw.ImageDraw, progress: float, accent):
    neon_panel(draw, 102, 236, 392, 188, accent, radius=30)
    code_lines = [
        "preds = self.ag_predictor.predict(features_df)",
        "return np.clip(preds.values, 0, 1)",
    ]
    cursor = 272
    for line in code_lines:
        font, fitted = fit_text_block(draw, line, 344, 2, 20, 15, mono=True)
        cursor = draw_lines(draw, 126, cursor, fitted, font, (241, 245, 249, 255), line_gap=1)
        cursor += 18
    draw_arrow(draw, (500, 330), (622, 330), (*accent, 255), width=6)
    neon_panel(draw, 606, 228, 214, 208, accent, radius=34, fill_alpha=0.74)
    draw.text((646, 276), "AG", font=load_font(64, bold=True, mono=True), fill=(*accent, 255))
    draw.text((640, 346), "predictor", font=FONT_PANEL, fill=(241, 245, 249, 255))
    draw_arrow(draw, (826, 330), (946, 330), (*accent, 255), width=6)
    neon_panel(draw, 930, 184, 238, 316, accent, radius=34)
    draw.text((968, 224), "Output scale", font=FONT_PANEL, fill=(241, 245, 249, 255))
    draw.line([(1078, 282), (1078, 458)], fill=(71, 85, 105, 255), width=8)
    for idx, label in enumerate(["1.0", "0.5", "0.0"]):
        y = 282 + idx * 88
        draw.text((1008, y - 12), label, font=FONT_MONO_SMALL, fill=(148, 163, 184, 255))
    dot_y = int(blend(458, 328, pop(progress, 0.28, 0.32)))
    draw.ellipse((1062, dot_y - 14, 1094, dot_y + 18), fill=(*accent, 255))
    draw.text((968, 486), "forecast = 0.74", font=FONT_MONO, fill=(241, 245, 249, 255))


def scene_projection(draw: ImageDraw.ImageDraw, progress: float, accent):
    draw_forecast_chart(draw, 88, 174, 828, 376, FORECAST_CURVE, accent, future_start=1)
    neon_panel(draw, 956, 196, 232, 152, accent, radius=28)
    draw.text((986, 228), "predicted", font=FONT_BODY, fill=(148, 163, 184, 255))
    draw.text((986, 258), "progress_4w", font=FONT_MONO_SMALL, fill=(165, 243, 252, 255))
    draw.text((986, 296), "74.0%", font=FONT_NUMBER, fill=(*accent, 255))
    neon_panel(draw, 956, 380, 232, 152, accent, radius=28)
    draw.text((986, 412), "predicted", font=FONT_BODY, fill=(148, 163, 184, 255))
    draw.text((986, 442), "delta_4w", font=FONT_MONO_SMALL, fill=(165, 243, 252, 255))
    draw.text((986, 480), "+12.0", font=FONT_NUMBER, fill=(*accent, 255))
    draw_chip(draw, 170, 560, "62% now", accent, mono=True)
    draw_chip(draw, 420, 560, "74% at +4w", accent, mono=True)
    draw_chip(draw, 720, 560, "near-term movement signal", accent, mono=True)


def scene_result_packet(draw: ImageDraw.ImageDraw, progress: float, accent):
    neon_panel(draw, 98, 214, 250, 268, accent, radius=28)
    draw.text((126, 248), "Well packet", font=FONT_PANEL, fill=(241, 245, 249, 255))
    draw.text((126, 306), "Well-A17", font=FONT_MONO, fill=(*accent, 255))
    draw.text((126, 350), "rig_no: R-14", font=FONT_MONO_SMALL, fill=(201, 210, 222, 255))
    draw.text((126, 384), "well_type: DEV", font=FONT_MONO_SMALL, fill=(201, 210, 222, 255))
    draw.text((126, 418), "progress: 62.0", font=FONT_MONO_SMALL, fill=(201, 210, 222, 255))
    draw_arrow(draw, (354, 348), (520, 348), (*accent, 255), width=6)
    neon_panel(draw, 500, 220, 256, 256, accent, radius=32)
    draw.text((540, 274), "predict_well", font=FONT_MONO, fill=(241, 245, 249, 255))
    draw.text((552, 328), "updates", font=FONT_BODY, fill=(148, 163, 184, 255))
    draw.text((542, 364), "the response", font=FONT_BODY, fill=(148, 163, 184, 255))
    draw_arrow(draw, (764, 348), (932, 348), (*accent, 255), width=6)
    neon_panel(draw, 904, 168, 288, 356, accent, radius=30)
    draw.text((936, 202), "Result JSON", font=FONT_PANEL, fill=(241, 245, 249, 255))
    cursor = 252
    for line in RESULT_LINES:
        draw.text((936, cursor), line, font=FONT_MONO_SMALL, fill=(201, 210, 222, 255))
        cursor += 42
    draw.text((936, 454), '"survival": { ... }', font=FONT_MONO_SMALL, fill=(148, 163, 184, 255))
    draw.text((936, 488), '"risk_score": ...', font=FONT_MONO_SMALL, fill=(148, 163, 184, 255))


def scene_final(draw: ImageDraw.ImageDraw, progress: float, accent):
    stations = [
        (120, 230, "1", "Load saved", "ag_model"),
        (390, 172, "2", "Engineer", "58 features"),
        (690, 230, "3", "Forecast", "week +4"),
        (960, 172, "4", "Write back", "result"),
    ]
    for x, y, num, title, sub in stations:
        neon_panel(draw, x, y, 208, 184, accent, radius=28, fill_alpha=0.76)
        draw.text((x + 26, y + 24), num, font=FONT_NUMBER, fill=(*accent, 255))
        draw.text((x + 78, y + 34), title, font=FONT_BODY, fill=(241, 245, 249, 255))
        draw.text((x + 78, y + 72), sub, font=FONT_MONO_SMALL, fill=(165, 243, 252, 255))
    for start, end in [((328, 322), (390, 264)), ((598, 264), (690, 322)), ((898, 322), (960, 264))]:
        draw_arrow(draw, start, end, (*accent, 255), width=6)
    neon_panel(draw, 236, 468, 812, 112, accent, radius=28, fill_alpha=0.82)
    draw.text((272, 504), "AutoGluon gives Bashira a near-term progress forecast before the rest of the predictive stack acts.", font=FONT_BODY, fill=(241, 245, 249, 255))


DRAWERS = [
    scene_question,
    scene_model_load,
    scene_feature_frame,
    scene_motion,
    scene_predictor_call,
    scene_projection,
    scene_result_packet,
    scene_final,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (6, 12, 24))
    draw = ImageDraw.Draw(image, "RGBA")
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

    combined_audio = run_dir / "autogluon_progress_forecast_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "autogluon_progress_forecast_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

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
OUTPUT_FILE = OUTPUT_DIR / "feature-engineering-58-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 24
SCENE_GAP_SECONDS = 0.22
MIN_SCENE_SECONDS = 10.0

SCENES = [
    {
        "title": "Why Feature Engineering Exists",
        "subtitle": "Bashira turns messy weekly field records into signals a learning system can compare.",
        "code": "feature_engine.py:325-337, 474-487",
        "accent": "#D97706",
        "narration": "Feature engineering is where Bashira earns its intelligence. Raw weekly field records are noisy, incomplete, and inconsistent. So before any forecast or risk model can reason, we convert those records into a stable, comparable fifty eight feature frame.",
    },
    {
        "title": "Raw Weekly Records Are Uneven",
        "subtitle": "Dates, progress, rig events, geography, and preparation tasks arrive in different shapes.",
        "code": "feature_engine.py:341-357",
        "accent": "#DC2626",
        "narration": "The raw inputs do not arrive in one clean mathematical form. Some values are dates, some are percentages, some are coordinates, some are task completions, and some may be blank. Bashira first standardizes these different raw pieces so they can enter the same analytical line.",
    },
    {
        "title": "Calendar And Geography Become Signals",
        "subtitle": "We convert raw operational dates and coordinates into timing and spatial features.",
        "code": "feature_engine.py:359-392",
        "accent": "#2563EB",
        "narration": "Once the rows are standardized, Bashira creates timing and geography signals. It derives days since start, start month, start quarter, rig duration, days to expected rig off, week index, distance from centroid, quadrant, and angle. This gives the model time context and location context instead of raw dates and coordinates alone.",
    },
    {
        "title": "Preparation Work Becomes One Composite",
        "subtitle": "Many location-preparation tasks are blended into a weighted readiness score.",
        "code": "feature_engine.py:394-399, 42-56",
        "accent": "#0F766E",
        "narration": "Bashira also compresses many field-preparation activities into one location preparation composite. Access road, earth work, cellar, liner, welding, pulling, hydro test, and mechanical completion are all weighted and combined. This is important because the model needs one interpretable readiness signal rather than a long scattered checklist.",
    },
    {
        "title": "History Becomes Motion",
        "subtitle": "Ordered weekly progress is transformed into lag, velocity, acceleration, rolling pace, and remaining work.",
        "code": "feature_engine.py:401-448",
        "accent": "#7C3AED",
        "narration": "The most important transformation is motion. Bashira sorts historical weekly progress and then creates lag one, lag two, lag four, one week velocity, two week velocity, acceleration, rolling pace, remaining work, and momentum score. This is how the model sees trend and direction instead of just one frozen status point.",
    },
    {
        "title": "Identity And Weekly Priors Add Context",
        "subtitle": "Rig, project, well type, and week-level patterns become learned context features.",
        "code": "feature_engine.py:450-472, 195-213",
        "accent": "#0891B2",
        "narration": "Bashira then adds context from rig history, project identity, well type, and weekly behavior. Target encodings, label encodings, and weekly history aggregates turn known operational patterns into reusable context. This helps the system compare a well not only to itself, but also to similar histories.",
    },
    {
        "title": "Missing Pieces Are Repaired",
        "subtitle": "The frame is backfilled with training medians so no feature slot is left empty.",
        "code": "feature_engine.py:474-487, 191-213",
        "accent": "#EA580C",
        "narration": "Real field data is never perfectly complete, so Bashira fills missing feature slots with training medians or fallback context. This is not decoration. It is what keeps the learning system stable by ensuring the same fifty eight positions are always populated, even when live records are imperfect.",
    },
    {
        "title": "The 58-Column Contract",
        "subtitle": "The final output is one frozen machine-learning row that every downstream model can trust.",
        "code": "feature_engine.py:58-82, 474-487, 646-678",
        "accent": "#F59E0B",
        "narration": "The result is a frozen fifty eight column frame. That engineered row is what the forecast model, survival model, and risk logic actually read. So topic four is not about prediction yet. It is about how Bashira manufactures high quality signal from raw operations history before any model makes a decision.",
    },
]

RAW_STREAM = [
    "actual_start_date",
    "actual_rig_on_date",
    "Week_Number",
    "over_all_progress_percentages",
    "northing / easting",
    "access_road_5",
    "earth_work_60",
    "rig_no / well_type",
]

FACTORY_STATIONS = [
    "Parse dates",
    "Coerce numerics",
    "Calendar features",
    "Geo features",
    "Prep composite",
    "Lag and motion",
    "Encodings",
    "Impute and freeze",
]

FEATURE_FAMILIES = [
    ("Time", ["days_since_start", "rig_duration_days", "days_to_rig_off_exp"]),
    ("Space", ["dist_from_centroid", "geo_quadrant", "geo_angle"]),
    ("Prep", ["loc_prep_composite", "ohl_progress", "engg_kpi_after_rig-off_days"]),
    ("Motion", ["progress_lag1", "progress_velocity_1w", "momentum_score"]),
    ("Context", ["rig_no_te", "week_hist_mean", "well_type_enc"]),
]

MOTION_SERIES = [0.34, 0.41, 0.48, 0.54, 0.61]
MOTION_LABELS = ["lag4", "lag2", "lag1", "velocity", "now"]
FINAL_SAMPLE = [
    "days_since_start",
    "rig_duration_days",
    "dist_from_centroid",
    "loc_prep_composite",
    "progress_lag1",
    "progress_velocity_1w",
    "momentum_score",
    "rig_no_te",
    "week_hist_mean",
    "well_type_enc",
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
FONT_NUMBER = load_font(58, bold=True, mono=True)


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


def draw_lines(draw: ImageDraw.ImageDraw, x: int, y: int, lines: list[str], font, fill, line_gap: int = 2) -> int:
    cursor = y
    for line in lines:
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += font.size + line_gap
    return cursor


def text_block(draw: ImageDraw.ImageDraw, xy, text: str, font, fill, max_width: int, line_gap: int = 3) -> int:
    x, y = xy
    cursor = y
    for line in wrap_text(draw, text, font, max_width):
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += font.size + line_gap
    return cursor


def metal_panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, accent, radius: int = 22, fill_alpha: float = 0.92):
    rounded(draw, (x + 8, y + 10, x + w + 8, y + h + 10), (10, 14, 20, 120), radius=radius)
    rounded(draw, (x, y, x + w, y + h), rgba((22, 28, 36), fill_alpha), outline=rgba(accent, 0.82), radius=radius, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    width = draw.textbbox((0, 0), text, font=FONT_TAG)[2] + 26
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.15), outline=rgba(accent, 0.62), radius=999, width=2)
    draw.text((x + 13, y + 7), text, font=FONT_TAG, fill=(*accent, 255))


def draw_arrow(draw: ImageDraw.ImageDraw, start, end, color, width: int = 5):
    draw.line([start, end], fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = 14
    left = (end[0] - size * math.cos(angle - math.pi / 6), end[1] - size * math.sin(angle - math.pi / 6))
    right = (end[0] - size * math.cos(angle + math.pi / 6), end[1] - size * math.sin(angle + math.pi / 6))
    draw.polygon([end, left, right], fill=color)


def draw_background(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(18, 19, 22, 255))
    draw.rectangle((0, 0, WIDTH, 116), fill=(24, 25, 29, 255))
    for x in range(84, WIDTH, 72):
        draw.line([(x, 132), (x, HEIGHT)], fill=(36, 37, 42, 140), width=1)
    draw.ellipse((948, -90, 1270, 232), fill=rgba(accent, 0.08))
    draw.ellipse((-80, 470, 260, 810), fill=rgba((59, 130, 246), 0.06))
    scene = SCENES[scene_index]
    draw_chip(draw, 94, 28, f"FACTORY 04 / STAGE {scene_index + 1:02d}", accent)
    draw.text((94, 74), scene["title"], font=FONT_TITLE, fill=(245, 245, 245, 255))
    draw.text((96, 118), scene["subtitle"], font=FONT_SUB, fill=(254, 215, 170, 255))
    metal_panel(draw, 860, 22, 356, 54, accent, radius=18, fill_alpha=0.76)
    code_font, code_lines = fit_text_block(draw, scene["code"], 316, 2, 15, 12, mono=True)
    draw_lines(draw, 884, 34, code_lines, code_font, (186, 186, 186, 255), line_gap=0)
    for idx in range(len(SCENES)):
        fill = rgba(accent, 0.90 if idx == scene_index else 0.18)
        rounded(draw, (24 + idx * 28, 150, 40 + idx * 28, 166), fill, radius=6)


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    metal_panel(draw, 92, 638, 1100, 46, accent, radius=22, fill_alpha=0.86)
    draw.text((118, 651), text, font=FONT_BODY, fill=(236, 236, 236, 255))
    draw.text((1000, 651), "FEATURE ENGINEERING", font=FONT_TAG, fill=(*accent, 255))


def draw_conveyor(draw: ImageDraw.ImageDraw, x0: int, y: int, x1: int, accent):
    draw.line([(x0, y), (x1, y)], fill=(94, 94, 101, 255), width=16)
    for x in range(x0 + 20, x1, 54):
        rounded(draw, (x, y - 12, x + 24, y + 12), rgba(accent, 0.16), outline=rgba(accent, 0.42), radius=8, width=2)


def draw_station(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str, sub: str, accent):
    metal_panel(draw, x, y, w, h, accent, radius=24, fill_alpha=0.78)
    draw.text((x + 18, y + 16), title, font=FONT_BODY, fill=(*accent, 255))
    text_block(draw, (x + 18, y + 48), sub, FONT_SMALL, (225, 225, 225, 255), w - 36)


def draw_hist_chart(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, values: list[float], accent):
    metal_panel(draw, x, y, w, h, accent, radius=28, fill_alpha=0.74)
    x0 = x + 56
    y0 = y + h - 48
    x1 = x + w - 34
    y1 = y + 44
    draw.line([(x0, y0), (x1, y0)], fill=(102, 102, 112, 255), width=2)
    draw.line([(x0, y0), (x0, y1)], fill=(102, 102, 112, 255), width=2)
    for idx in range(4):
        gy = y0 - idx * ((y0 - y1) / 3)
        draw.line([(x0, gy), (x1, gy)], fill=(48, 48, 54, 255), width=1)
    points = []
    for idx, value in enumerate(values):
        px = x0 + idx * ((x1 - x0) / (len(values) - 1))
        py = y0 - value * (y0 - y1)
        points.append((px, py))
        draw.text((px - 18, y0 + 14), f"W{idx+1}", font=FONT_SMALL, fill=(170, 170, 170, 255))
    for start, end in zip(points, points[1:]):
        draw.line([start, end], fill=(*accent, 255), width=5)
    for idx, (px, py) in enumerate(points):
        draw.ellipse((px - 8, py - 8, px + 8, py + 8), fill=(*accent, 255), outline=(250, 250, 250, 255), width=2)
        draw.text((px - 14, py - 32), str(int(values[idx] * 100)), font=FONT_SMALL, fill=(245, 245, 245, 255))


def scene_intro(draw: ImageDraw.ImageDraw, progress: float, accent):
    draw_station(draw, 92, 190, 260, 222, "Raw WMR rows", "Weekly records arrive with dates, geography, progress, readiness tasks, and identifiers mixed together.", accent)
    draw_station(draw, 510, 190, 260, 222, "Signal factory", "Bashira engineers structure before any learning system reasons.", accent)
    draw_station(draw, 928, 190, 260, 222, "58-feature frame", "One stable machine-learning row comes out of the line.", accent)
    draw_conveyor(draw, 348, 302, 930, accent)
    draw_arrow(draw, (352, 302), (510, 302), (*accent, 255), width=6)
    draw_arrow(draw, (770, 302), (928, 302), (*accent, 255), width=6)
    draw.text((536, 456), "messy operations -> engineered signal quality", font=FONT_BODY, fill=(245, 245, 245, 255))


def scene_raw(draw: ImageDraw.ImageDraw, progress: float, accent):
    metal_panel(draw, 92, 182, 296, 348, accent, radius=28, fill_alpha=0.76)
    draw.text((122, 214), "Incoming record parts", font=FONT_PANEL, fill=(245, 245, 245, 255))
    for idx, label in enumerate(RAW_STREAM):
        y = 270 + idx * 34
        rounded(draw, (118, y, 358, y + 24), rgba(accent, 0.12), outline=rgba(accent, 0.42), radius=12, width=2)
        draw.text((134, y + 4), label, font=FONT_MONO_SMALL, fill=(235, 235, 235, 255))
    draw_arrow(draw, (394, 354), (540, 354), (*accent, 255), width=6)
    draw_station(draw, 534, 210, 240, 120, "Parse dates", "Convert date text into time values that can be measured.", accent)
    draw_station(draw, 534, 380, 240, 120, "Coerce numerics", "Turn strings into real numbers for progress, coordinates, and field tasks.", accent)
    draw_arrow(draw, (776, 270), (930, 270), (*accent, 255), width=5)
    draw_arrow(draw, (776, 440), (930, 440), (*accent, 255), width=5)
    metal_panel(draw, 918, 196, 272, 320, accent, radius=26, fill_alpha=0.78)
    draw.text((946, 230), "Standardized row", font=FONT_PANEL, fill=(245, 245, 245, 255))
    draw.text((946, 284), "dates -> timestamps", font=FONT_MONO_SMALL, fill=(254, 215, 170, 255))
    draw.text((946, 324), "text -> numerics", font=FONT_MONO_SMALL, fill=(254, 215, 170, 255))
    draw.text((946, 364), "blanks -> NaN", font=FONT_MONO_SMALL, fill=(254, 215, 170, 255))
    draw.text((946, 404), "ready for transforms", font=FONT_MONO_SMALL, fill=(254, 215, 170, 255))


def scene_calendar_geo(draw: ImageDraw.ImageDraw, progress: float, accent):
    draw_station(draw, 98, 194, 290, 146, "Calendar transforms", "days_since_start, start_month, start_quarter, rig_duration_days, days_to_rig_off_exp, week_index", accent)
    draw_station(draw, 98, 374, 290, 146, "Geography transforms", "dist_from_centroid, geo_quadrant, geo_angle from northing and easting relative to the training centroid", accent)
    draw_arrow(draw, (404, 268), (548, 268), (*accent, 255), width=6)
    draw_arrow(draw, (404, 448), (548, 448), (*accent, 255), width=6)
    metal_panel(draw, 520, 180, 308, 360, accent, radius=28, fill_alpha=0.78)
    draw.text((550, 214), "Signal drawers", font=FONT_PANEL, fill=(245, 245, 245, 255))
    drawers = [
        "days_since_start",
        "start_month",
        "rig_duration_days",
        "dist_from_centroid",
        "geo_quadrant",
        "geo_angle",
    ]
    for idx, label in enumerate(drawers):
        y = 262 + idx * 42
        rounded(draw, (548, y, 798, y + 28), rgba(accent, 0.10), outline=rgba(accent, 0.38), radius=12, width=2)
        draw.text((564, y + 5), label, font=FONT_MONO_SMALL, fill=(235, 235, 235, 255))
    metal_panel(draw, 890, 210, 282, 292, accent, radius=26, fill_alpha=0.76)
    draw.text((920, 246), "Why it matters", font=FONT_PANEL, fill=(245, 245, 245, 255))
    text_block(draw, (920, 300), "We stop feeding raw dates and raw coordinates directly. Instead, Bashira creates timing and spatial signals the model can compare across wells.", FONT_BODY, (230, 230, 230, 255), 222)


def scene_prep(draw: ImageDraw.ImageDraw, progress: float, accent):
    metal_panel(draw, 88, 176, 396, 370, accent, radius=28, fill_alpha=0.78)
    draw.text((118, 212), "Location-preparation checklist", font=FONT_PANEL, fill=(245, 245, 245, 255))
    prep_lines = [
        "access_road_5",
        "earth_work_60",
        "cellar_20",
        "hdpe_liner_instalat_4",
        "cs_pipe_welding_ndt_10_rt_for_op_100_for_60",
        "final_hydro_t_3",
        "mechani_60",
    ]
    for idx, label in enumerate(prep_lines):
        y = 266 + idx * 34
        rounded(draw, (116, y, 448, y + 24), rgba(accent, 0.10), outline=rgba(accent, 0.34), radius=12, width=2)
        draw.text((132, y + 5), label, font=FONT_MONO_SMALL, fill=(235, 235, 235, 255))
    draw_arrow(draw, (500, 360), (642, 360), (*accent, 255), width=6)
    metal_panel(draw, 622, 212, 224, 284, accent, radius=28, fill_alpha=0.74)
    draw.text((658, 248), "Weighted", font=FONT_PANEL, fill=(245, 245, 245, 255))
    draw.text((650, 292), "readiness", font=FONT_PANEL, fill=(245, 245, 245, 255))
    draw.text((676, 360), "=", font=FONT_NUMBER, fill=(*accent, 255))
    draw.text((662, 430), "loc_prep_composite", font=FONT_MONO_SMALL, fill=(254, 215, 170, 255))
    metal_panel(draw, 904, 230, 286, 242, accent, radius=26, fill_alpha=0.78)
    draw.text((932, 266), "Engineering logic", font=FONT_PANEL, fill=(245, 245, 245, 255))
    text_block(draw, (932, 320), "Many field tasks are collapsed into one readiness signal so the model can read preparation maturity without scanning a long checklist.", FONT_BODY, (230, 230, 230, 255), 226)


def scene_motion(draw: ImageDraw.ImageDraw, progress: float, accent):
    draw_hist_chart(draw, 86, 184, 686, 360, MOTION_SERIES, accent)
    chart_x0 = 142
    chart_y0 = 496
    chart_x1 = 738
    chart_y1 = 228
    points = []
    for idx, value in enumerate(MOTION_SERIES):
        px = chart_x0 + idx * ((chart_x1 - chart_x0) / (len(MOTION_SERIES) - 1))
        py = chart_y0 - value * (chart_y0 - chart_y1)
        points.append((px, py))
    for idx, tag in enumerate(MOTION_LABELS):
        px, py = points[idx]
        draw_chip(draw, int(px - 28), int(py - 74), tag, accent)
        draw_arrow(draw, (px, py - 28), (px, py - 10), rgba(accent, 0.90), width=4)
    metal_panel(draw, 820, 192, 370, 352, accent, radius=28, fill_alpha=0.78)
    draw.text((850, 228), "Motion outputs", font=FONT_PANEL, fill=(245, 245, 245, 255))
    metrics = [
        "progress_lag1",
        "progress_lag2",
        "progress_lag4",
        "progress_velocity_1w",
        "progress_velocity_2w",
        "progress_accel",
        "progress_rolling3w",
        "remaining_to_complete",
        "momentum_score",
    ]
    for idx, label in enumerate(metrics):
        y = 278 + idx * 26
        draw.text((856, y), label, font=FONT_MONO_SMALL, fill=(254, 215, 170, 255))
    draw.text((850, 516), "History is converted into trend, direction, and pace.", font=FONT_BODY, fill=(235, 235, 235, 255))


def scene_context(draw: ImageDraw.ImageDraw, progress: float, accent):
    draw_station(draw, 96, 206, 286, 118, "Target encodings", "rig_no_te, project_id_te, project_code_te, well_type_te and counts supply learned historical context.", accent)
    draw_station(draw, 96, 356, 286, 118, "Weekly priors", "week_hist_mean and week_hist_std add cohort memory from prior training behavior.", accent)
    draw_station(draw, 96, 506, 286, 98, "Label encodings", "rig_no_enc, well_type_enc, project_code_enc and other categorical mappings add identity structure.", accent)
    draw_arrow(draw, (400, 340), (556, 340), (*accent, 255), width=6)
    metal_panel(draw, 536, 190, 300, 312, accent, radius=28, fill_alpha=0.78)
    draw.text((566, 226), "Context bank", font=FONT_PANEL, fill=(245, 245, 245, 255))
    context_lines = [
        "rig_no_te",
        "project_id_te",
        "well_type_te",
        "week_hist_mean",
        "week_hist_std",
        "rig_no_enc",
        "well_type_enc",
    ]
    for idx, label in enumerate(context_lines):
        y = 276 + idx * 30
        rounded(draw, (564, y, 800, y + 22), rgba(accent, 0.10), outline=rgba(accent, 0.34), radius=10, width=2)
        draw.text((580, y + 3), label, font=FONT_MONO_SMALL, fill=(235, 235, 235, 255))
    metal_panel(draw, 892, 226, 294, 238, accent, radius=26, fill_alpha=0.76)
    draw.text((920, 262), "Business meaning", font=FONT_PANEL, fill=(245, 245, 245, 255))
    text_block(draw, (920, 316), "Bashira is not only reading the current well. It is also injecting learned context about rigs, projects, categories, and weekly behavior patterns.", FONT_BODY, (230, 230, 230, 255), 234)


def scene_impute(draw: ImageDraw.ImageDraw, progress: float, accent):
    metal_panel(draw, 94, 190, 340, 318, accent, radius=28, fill_alpha=0.78)
    draw.text((124, 226), "Before repair", font=FONT_PANEL, fill=(245, 245, 245, 255))
    before = [
        "dist_from_centroid = 118.2",
        "progress_velocity_1w = NaN",
        "week_hist_mean = NaN",
        "rig_no_te = 0.61",
        "momentum_score = NaN",
    ]
    for idx, line in enumerate(before):
        y = 286 + idx * 38
        rounded(draw, (120, y, 402, y + 24), rgba(accent, 0.10), outline=rgba(accent, 0.34), radius=10, width=2)
        draw.text((136, y + 5), line, font=FONT_MONO_SMALL, fill=(235, 235, 235, 255))
    draw_arrow(draw, (450, 346), (602, 346), (*accent, 255), width=6)
    metal_panel(draw, 582, 236, 188, 220, accent, radius=28, fill_alpha=0.74)
    draw.text((618, 278), "Fill", font=FONT_PANEL, fill=(245, 245, 245, 255))
    draw.text((610, 322), "with", font=FONT_BODY, fill=(210, 210, 210, 255))
    draw.text((614, 356), "medians", font=FONT_PANEL, fill=(245, 245, 245, 255))
    metal_panel(draw, 828, 190, 362, 318, accent, radius=28, fill_alpha=0.78)
    draw.text((858, 226), "After repair", font=FONT_PANEL, fill=(245, 245, 245, 255))
    after = [
        "dist_from_centroid = 118.2",
        "progress_velocity_1w = 0.00",
        "week_hist_mean = 0.47",
        "rig_no_te = 0.61",
        "momentum_score = 0.00",
    ]
    for idx, line in enumerate(after):
        y = 286 + idx * 38
        rounded(draw, (854, y, 1158, y + 24), rgba(accent, 0.10), outline=rgba(accent, 0.34), radius=10, width=2)
        draw.text((870, y + 5), line, font=FONT_MONO_SMALL, fill=(235, 235, 235, 255))
    draw.text((372, 556), "Every slot must be populated so downstream learning stays stable.", font=FONT_BODY, fill=(245, 245, 245, 255))


def scene_final(draw: ImageDraw.ImageDraw, progress: float, accent):
    metal_panel(draw, 92, 184, 332, 360, accent, radius=28, fill_alpha=0.78)
    draw.text((122, 220), "58-column contract", font=FONT_PANEL, fill=(245, 245, 245, 255))
    draw.text((132, 272), "FEATURE_NAMES", font=FONT_MONO, fill=(*accent, 255))
    draw.text((124, 324), "Every downstream model", font=FONT_BODY, fill=(230, 230, 230, 255))
    draw.text((124, 356), "expects the same column", font=FONT_BODY, fill=(230, 230, 230, 255))
    draw.text((124, 388), "order and same feature", font=FONT_BODY, fill=(230, 230, 230, 255))
    draw.text((124, 420), "meaning.", font=FONT_BODY, fill=(230, 230, 230, 255))
    draw_arrow(draw, (432, 366), (560, 366), (*accent, 255), width=6)
    metal_panel(draw, 540, 166, 650, 388, accent, radius=30, fill_alpha=0.76)
    draw.text((570, 202), "Sample of the final engineered row", font=FONT_PANEL, fill=(245, 245, 245, 255))
    for idx, label in enumerate(FINAL_SAMPLE):
        col = idx % 2
        row = idx // 2
        x = 568 + col * 294
        y = 254 + row * 54
        rounded(draw, (x, y, x + 260, y + 34), rgba(accent, 0.10), outline=rgba(accent, 0.34), radius=12, width=2)
        draw.text((x + 16, y + 7), label, font=FONT_MONO_SMALL, fill=(235, 235, 235, 255))
    draw.text((378, 592), "Raw weekly operations history -> engineered signal quality -> one trusted machine-learning row", font=FONT_BODY, fill=(245, 245, 245, 255))


DRAWERS = [
    scene_intro,
    scene_raw,
    scene_calendar_geo,
    scene_prep,
    scene_motion,
    scene_context,
    scene_impute,
    scene_final,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (18, 19, 22))
    draw = ImageDraw.Draw(image, "RGBA")
    draw_background(draw, scene_index, accent)
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
    subprocess.run(["powershell", "-NoProfile", "-Command", command], check=True, capture_output=True, text=True)


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

    combined_audio = run_dir / "feature_engineering_58_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "feature_engineering_58_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

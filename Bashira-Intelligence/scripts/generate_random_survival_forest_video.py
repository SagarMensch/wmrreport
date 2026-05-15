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
OUTPUT_FILE = OUTPUT_DIR / "random-survival-forest-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 24
SCENE_GAP_SECONDS = 0.22
MIN_SCENE_SECONDS = 10.0

SCENES = [
    {
        "title": "Why Survival Logic Is Different",
        "subtitle": "Bashira estimates when completion happens, not just whether risk is high or low.",
        "code": "feature_engine.py:510-518, 646-705",
        "accent": "#22C55E",
        "narration": "Random Survival Forest answers a different question from the other models. Instead of asking only how risky a well looks, Bashira asks when completion is likely to happen. That means we need time-to-event logic, not just a single class or score.",
    },
    {
        "title": "Build A Time-To-Event Dataset",
        "subtitle": "Each historical well becomes an event flag, a duration, and six survival features.",
        "code": "feature_engine.py:237-283",
        "accent": "#16A34A",
        "narration": "To make a survival dataset, Bashira turns each historical well into three things. First, an event flag that says whether progress reached one hundred percent. Second, a duration that represents how long the well has been observed. Third, a compact survival feature row with progress, velocity, remaining work, location preparation, construction progress, and engineering KPI.",
    },
    {
        "title": "Event And Duration Matter Together",
        "subtitle": "Completion is learned as an event over time, not as one static label.",
        "code": "feature_engine.py:255-265, 283-294",
        "accent": "#10B981",
        "narration": "The key survival idea is this. A well is not just positive or negative. It is a process moving through time. Bashira marks whether completion happened, then pairs that with how long the well has been moving. That is what lets the forest learn timing patterns instead of just category boundaries.",
    },
    {
        "title": "The Forest Learns Timing Patterns",
        "subtitle": "Three hundred trees learn how feature combinations change completion timing.",
        "code": "feature_engine.py:285-311",
        "accent": "#84CC16",
        "narration": "Bashira then fits a Random Survival Forest with three hundred trees. Each tree learns different timing relationships between progress state, pace, remaining work, readiness, and engineering condition. The result is not one hard date. It is a learned distribution of completion timing.",
    },
    {
        "title": "One Live Well Enters The Survival Frame",
        "subtitle": "The current well is converted into the six-value RSF input row.",
        "code": "feature_engine.py:522-524, 683-692",
        "accent": "#65A30D",
        "narration": "When Bashira scores one live well, it builds a six-value survival row. That row contains current progress, current velocity, remaining work, location preparation, construction progress, and engineering KPI. The live well is then compared against the timing patterns learned by the forest.",
    },
    {
        "title": "The Survival Curve Is The Core Output",
        "subtitle": "The forest returns a curve showing how completion probability changes across time.",
        "code": "feature_engine.py:526-533",
        "accent": "#4D7C0F",
        "narration": "The central output is the survival curve. This curve tells Bashira how much unfinished probability is still left at each future time point. As the curve drops, the chance of completion by that time grows. This is the real heart of the RSF method.",
    },
    {
        "title": "Median And Timing Band Are Read From The Curve",
        "subtitle": "Bashira reads the fifty percent, seventy five percent, and twenty five percent crossings.",
        "code": "feature_engine.py:530-559",
        "accent": "#A3E635",
        "narration": "Bashira reads concrete timing windows directly from the curve. The fifty percent crossing becomes the median completion week. The seventy five percent crossing becomes an earlier estimate. The twenty five percent crossing becomes a later estimate. That creates an uncertainty band instead of a fake single certainty point.",
    },
    {
        "title": "Why RSF Matters In Bashira",
        "subtitle": "The platform gets a completion week estimate, an early window, and a late window for action planning.",
        "code": "feature_engine.py:543-562, 687-693",
        "accent": "#BEF264",
        "narration": "So the Random Survival Forest gives Bashira timing intelligence. It produces a median completion estimate, an early window, and a late window. That means Bashira can speak about timing uncertainty honestly, which is much more useful for planning than pretending every well has one exact finish date.",
    },
]

SURV_FEATURES = [
    ("progress", "0.62"),
    ("velocity", "0.04"),
    ("remaining", "0.38"),
    ("loc_prep", "0.71"),
    ("const_progress", "0.58"),
    ("engg_kpi", "12"),
]

TIMELINE_WEEKS = [4, 8, 12, 16, 20, 24]
SURVIVAL_VALUES = [0.97, 0.86, 0.72, 0.50, 0.27, 0.12]
WINDOW_VALUES = [
    ("early_completion_weeks", "12"),
    ("median_completion_weeks", "16"),
    ("late_completion_weeks", "20"),
]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ease(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


def pop(progress: float, delay: float, duration: float = 0.18) -> float:
    return ease((progress - delay) / duration)


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
FONT_TITLE = load_font(40, bold=True)
FONT_SUB = load_font(22)
FONT_PANEL = load_font(28, bold=True)
FONT_BODY = load_font(19)
FONT_SMALL = load_font(15)
FONT_MONO = load_font(18, mono=True)
FONT_MONO_SMALL = load_font(15, mono=True)
FONT_NUMBER = load_font(52, bold=True, mono=True)


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


def tunnel_panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, accent, radius: int = 22, fill_alpha: float = 0.84):
    rounded(draw, (x + 8, y + 10, x + w + 8, y + h + 10), (6, 14, 8, 110), radius=radius)
    rounded(draw, (x, y, x + w, y + h), rgba((14, 26, 18), fill_alpha), outline=rgba(accent, 0.82), radius=radius, width=2)


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
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(10, 18, 12, 255))
    draw.rectangle((0, 0, WIDTH, 116), fill=(12, 24, 16, 255))
    for idx in range(12):
        inset = idx * 30
        draw.line([(120 + inset, 160 + inset * 0.42), (WIDTH - 120 - inset, 160 + inset * 0.42)], fill=rgba(accent, 0.06), width=1)
    scene = SCENES[scene_index]
    draw_chip(draw, 94, 28, f"SURVIVAL 05 / PHASE {scene_index + 1:02d}", accent)
    draw.text((94, 74), scene["title"], font=FONT_TITLE, fill=(244, 250, 244, 255))
    draw.text((96, 120), scene["subtitle"], font=FONT_SUB, fill=(220, 252, 231, 255))
    tunnel_panel(draw, 860, 22, 356, 54, accent, radius=18, fill_alpha=0.74)
    code_font, code_lines = fit_text_block(draw, scene["code"], 316, 2, 15, 12, mono=True)
    draw_lines(draw, 884, 34, code_lines, code_font, (187, 247, 208, 255), line_gap=0)
    draw.ellipse((936, -90, 1260, 234), fill=rgba(accent, 0.08))
    for idx in range(len(SCENES)):
        fill = rgba(accent, 0.90 if idx == scene_index else 0.18)
        rounded(draw, (24 + idx * 28, 150, 40 + idx * 28, 166), fill, radius=6)


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    tunnel_panel(draw, 92, 638, 1100, 46, accent, radius=22, fill_alpha=0.82)
    draw.text((118, 651), text, font=FONT_BODY, fill=(235, 255, 240, 255))
    draw.text((1022, 651), "SURVIVAL", font=FONT_TAG, fill=(*accent, 255))


def draw_curve_panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, accent):
    tunnel_panel(draw, x, y, w, h, accent, radius=28, fill_alpha=0.78)
    x0 = x + 62
    y0 = y + h - 52
    x1 = x + w - 34
    y1 = y + 38
    draw.line([(x0, y0), (x1, y0)], fill=(98, 112, 102, 255), width=2)
    draw.line([(x0, y0), (x0, y1)], fill=(98, 112, 102, 255), width=2)
    for idx in range(5):
        gy = y0 - idx * ((y0 - y1) / 4)
        draw.line([(x0, gy), (x1, gy)], fill=(38, 52, 42, 255), width=1)
        draw.text((x + 12, gy - 10), f"{100 - idx*25}%", font=FONT_SMALL, fill=(187, 247, 208, 255))
    points = []
    for idx, value in enumerate(SURVIVAL_VALUES):
        px = x0 + idx * ((x1 - x0) / (len(SURVIVAL_VALUES) - 1))
        py = y0 - value * (y0 - y1)
        points.append((px, py))
        draw.text((px - 12, y0 + 14), str(TIMELINE_WEEKS[idx]), font=FONT_SMALL, fill=(187, 247, 208, 255))
    for start, end in zip(points, points[1:]):
        draw.line([start, end], fill=(*accent, 255), width=5)
    for px, py in points:
        draw.ellipse((px - 7, py - 7, px + 7, py + 7), fill=(*accent, 255), outline=(250, 250, 250, 255), width=2)
    return points


def scene_intro(draw: ImageDraw.ImageDraw, progress: float, accent):
    tunnel_panel(draw, 92, 186, 320, 270, accent, radius=28)
    draw.text((122, 224), "Question", font=FONT_PANEL, fill=(244, 250, 244, 255))
    text_block(draw, (122, 280), "When is this well likely to finish, and how wide is the timing uncertainty?", FONT_BODY, (223, 240, 228, 255), 250)
    draw_arrow(draw, (426, 320), (576, 320), (*accent, 255), width=6)
    tunnel_panel(draw, 548, 188, 256, 264, accent, radius=32)
    draw.text((586, 230), "Time-to-event", font=FONT_PANEL, fill=(244, 250, 244, 255))
    draw.text((610, 304), "not", font=FONT_BODY, fill=(187, 247, 208, 255))
    draw.text((592, 340), "just a score", font=FONT_PANEL, fill=(244, 250, 244, 255))
    draw_arrow(draw, (820, 320), (948, 320), (*accent, 255), width=6)
    tunnel_panel(draw, 922, 190, 268, 260, accent, radius=28)
    draw.text((954, 226), "Output", font=FONT_PANEL, fill=(244, 250, 244, 255))
    draw.text((954, 280), "early week", font=FONT_MONO_SMALL, fill=(187, 247, 208, 255))
    draw.text((954, 320), "median week", font=FONT_MONO_SMALL, fill=(187, 247, 208, 255))
    draw.text((954, 360), "late week", font=FONT_MONO_SMALL, fill=(187, 247, 208, 255))


def scene_dataset(draw: ImageDraw.ImageDraw, progress: float, accent):
    tunnel_panel(draw, 88, 178, 300, 360, accent, radius=28)
    draw.text((118, 214), "Per-well survival row", font=FONT_PANEL, fill=(244, 250, 244, 255))
    lines = [
        "progress >= 1.0 -> event",
        "week_number_ord -> duration",
        "progress",
        "velocity",
        "remaining",
        "loc_prep",
        "const_progress",
        "engg_kpi",
    ]
    for idx, line in enumerate(lines):
        y = 268 + idx * 32
        rounded(draw, (116, y, 356, y + 22), rgba(accent, 0.10), outline=rgba(accent, 0.34), radius=10, width=2)
        draw.text((132, y + 3), line, font=FONT_MONO_SMALL, fill=(235, 255, 240, 255))
    draw_arrow(draw, (406, 350), (548, 350), (*accent, 255), width=6)
    tunnel_panel(draw, 526, 216, 290, 266, accent, radius=28)
    draw.text((558, 250), "Structured for survival", font=FONT_PANEL, fill=(244, 250, 244, 255))
    text_block(draw, (558, 306), "Bashira pairs each completion event with a duration and a compact feature row. That is the basic survival learning format.", FONT_BODY, (223, 240, 228, 255), 226)
    tunnel_panel(draw, 878, 212, 310, 272, accent, radius=28)
    draw.text((910, 248), "Why this matters", font=FONT_PANEL, fill=(244, 250, 244, 255))
    text_block(draw, (910, 304), "A static label would hide timing. Survival rows preserve both whether completion happened and how long it took.", FONT_BODY, (223, 240, 228, 255), 246)


def scene_event_time(draw: ImageDraw.ImageDraw, progress: float, accent):
    tunnel_panel(draw, 88, 184, 480, 330, accent, radius=28)
    draw.text((118, 220), "Event gate", font=FONT_PANEL, fill=(244, 250, 244, 255))
    draw.text((118, 274), "progress >= 1.0", font=FONT_MONO, fill=(187, 247, 208, 255))
    draw.text((118, 318), "event = completed", font=FONT_MONO, fill=(244, 250, 244, 255))
    draw.text((118, 368), "duration = week count observed", font=FONT_MONO_SMALL, fill=(223, 240, 228, 255))
    draw_arrow(draw, (592, 350), (732, 350), (*accent, 255), width=6)
    tunnel_panel(draw, 712, 184, 476, 330, accent, radius=28)
    draw.text((742, 220), "Time axis", font=FONT_PANEL, fill=(244, 250, 244, 255))
    timeline_y = 358
    draw.line([(760, timeline_y), (1128, timeline_y)], fill=(88, 102, 92, 255), width=8)
    for idx, week in enumerate(TIMELINE_WEEKS):
        px = 760 + idx * ((1128 - 760) / (len(TIMELINE_WEEKS) - 1))
        draw.ellipse((px - 10, timeline_y - 10, px + 10, timeline_y + 10), fill=(*accent, 255))
        draw.text((px - 10, timeline_y + 18), str(week), font=FONT_SMALL, fill=(187, 247, 208, 255))
    draw.text((774, 430), "The forest learns events as a function of time.", font=FONT_BODY, fill=(223, 240, 228, 255))


def scene_forest(draw: ImageDraw.ImageDraw, progress: float, accent):
    tunnel_panel(draw, 86, 178, 330, 360, accent, radius=28)
    draw.text((118, 214), "Input families", font=FONT_PANEL, fill=(244, 250, 244, 255))
    labels = ["progress", "velocity", "remaining", "loc_prep", "const_progress", "engg_kpi"]
    for idx, label in enumerate(labels):
        y = 270 + idx * 38
        rounded(draw, (116, y, 362, y + 24), rgba(accent, 0.10), outline=rgba(accent, 0.34), radius=10, width=2)
        draw.text((132, y + 4), label, font=FONT_MONO_SMALL, fill=(235, 255, 240, 255))
    draw_arrow(draw, (430, 358), (570, 358), (*accent, 255), width=6)
    tunnel_panel(draw, 548, 184, 260, 352, accent, radius=28)
    draw.text((592, 220), "300", font=FONT_NUMBER, fill=(*accent, 255))
    draw.text((582, 296), "timing trees", font=FONT_PANEL, fill=(244, 250, 244, 255))
    for idx in range(6):
        base_x = 590 + (idx % 3) * 58
        base_y = 372 + (idx // 3) * 68
        draw.line([(base_x, base_y), (base_x, base_y - 34)], fill=(*accent, 255), width=3)
        draw.line([(base_x, base_y - 22), (base_x - 18, base_y - 42)], fill=(*accent, 255), width=3)
        draw.line([(base_x, base_y - 22), (base_x + 18, base_y - 42)], fill=(*accent, 255), width=3)
    draw_arrow(draw, (826, 358), (954, 358), (*accent, 255), width=6)
    tunnel_panel(draw, 930, 228, 260, 264, accent, radius=28)
    draw.text((960, 264), "Learns a timing", font=FONT_PANEL, fill=(244, 250, 244, 255))
    draw.text((998, 304), "distribution", font=FONT_PANEL, fill=(244, 250, 244, 255))
    text_block(draw, (960, 362), "Not one forced finish date. A timing pattern with uncertainty.", FONT_BODY, (223, 240, 228, 255), 200)


def scene_live_row(draw: ImageDraw.ImageDraw, progress: float, accent):
    tunnel_panel(draw, 90, 184, 410, 340, accent, radius=28)
    draw.text((122, 220), "Live survival row", font=FONT_PANEL, fill=(244, 250, 244, 255))
    for idx, (label, value) in enumerate(SURV_FEATURES):
        y = 274 + idx * 40
        rounded(draw, (118, y, 468, y + 26), rgba(accent, 0.10), outline=rgba(accent, 0.34), radius=10, width=2)
        draw.text((136, y + 5), label, font=FONT_MONO_SMALL, fill=(187, 247, 208, 255))
        draw.text((392, y + 5), value, font=FONT_MONO_SMALL, fill=(244, 250, 244, 255))
    draw_arrow(draw, (514, 352), (666, 352), (*accent, 255), width=6)
    tunnel_panel(draw, 646, 208, 230, 288, accent, radius=28)
    draw.text((688, 250), "X", font=FONT_NUMBER, fill=(*accent, 255))
    draw.text((724, 248), "survival", font=FONT_MONO_SMALL, fill=(187, 247, 208, 255))
    draw.text((688, 326), "6 features", font=FONT_PANEL, fill=(244, 250, 244, 255))
    draw_arrow(draw, (890, 352), (1034, 352), (*accent, 255), width=6)
    tunnel_panel(draw, 1012, 228, 180, 246, accent, radius=28)
    draw.text((1048, 266), "compare", font=FONT_PANEL, fill=(244, 250, 244, 255))
    draw.text((1060, 312), "to learned", font=FONT_BODY, fill=(223, 240, 228, 255))
    draw.text((1066, 346), "timing", font=FONT_BODY, fill=(223, 240, 228, 255))
    draw.text((1050, 380), "patterns", font=FONT_BODY, fill=(223, 240, 228, 255))


def scene_curve(draw: ImageDraw.ImageDraw, progress: float, accent):
    points = draw_curve_panel(draw, 92, 182, 760, 360, accent)
    draw.text((122, 218), "Survival curve", font=FONT_PANEL, fill=(244, 250, 244, 255))
    draw.text((122, 256), "unfinished probability remaining", font=FONT_BODY, fill=(223, 240, 228, 255))
    tunnel_panel(draw, 902, 208, 286, 304, accent, radius=28)
    draw.text((934, 244), "Interpretation", font=FONT_PANEL, fill=(244, 250, 244, 255))
    text_block(draw, (934, 300), "As the curve falls, more completion probability has accumulated by that future week.", FONT_BODY, (223, 240, 228, 255), 226)
    for label, target, offset in [("50%", 0.50, 0), ("75%", 0.75, -38), ("25%", 0.25, 38)]:
        idx = min(range(len(SURVIVAL_VALUES)), key=lambda i: abs(SURVIVAL_VALUES[i] - target))
        px, py = points[idx]
        draw_chip(draw, int(px - 24), int(py + offset - 20), label, accent)


def scene_windows(draw: ImageDraw.ImageDraw, progress: float, accent):
    points = draw_curve_panel(draw, 92, 180, 712, 366, accent)
    thresholds = [0.75, 0.50, 0.25]
    for idx, thr in enumerate(thresholds):
        curve_idx = min(range(len(SURVIVAL_VALUES)), key=lambda i: abs(SURVIVAL_VALUES[i] - thr))
        px, py = points[curve_idx]
        draw.line([(px, py), (px, 560)], fill=rgba(accent, 0.65), width=3)
    tunnel_panel(draw, 850, 194, 340, 338, accent, radius=28)
    draw.text((882, 230), "Timing window outputs", font=FONT_PANEL, fill=(244, 250, 244, 255))
    for idx, (label, value) in enumerate(WINDOW_VALUES):
        y = 292 + idx * 74
        rounded(draw, (878, y, 1162, y + 46), rgba(accent, 0.10), outline=rgba(accent, 0.34), radius=12, width=2)
        draw.text((896, y + 8), label, font=FONT_MONO_SMALL, fill=(187, 247, 208, 255))
        draw.text((1088, y + 6), value, font=FONT_NUMBER, fill=(244, 250, 244, 255))
    draw.text((296, 584), "The curve becomes an early, median, and late timing band.", font=FONT_BODY, fill=(244, 250, 244, 255))


def scene_final(draw: ImageDraw.ImageDraw, progress: float, accent):
    blocks = [
        (110, 214, "1", "Build event + duration"),
        (392, 170, "2", "Learn timing forest"),
        (694, 214, "3", "Generate survival curve"),
        (972, 170, "4", "Read timing window"),
    ]
    for x, y, num, title in blocks:
        tunnel_panel(draw, x, y, 210, 172, accent, radius=28)
        draw.text((x + 24, y + 22), num, font=FONT_NUMBER, fill=(*accent, 255))
        text_block(draw, (x + 86, y + 36), title, FONT_BODY, (244, 250, 244, 255), 100)
    for start, end in [((320, 300), (392, 256)), ((602, 256), (694, 300)), ((904, 300), (972, 256))]:
        draw_arrow(draw, start, end, (*accent, 255), width=6)
    tunnel_panel(draw, 236, 468, 808, 110, accent, radius=28)
    draw.text((270, 505), "RSF lets Bashira speak honestly about completion timing and uncertainty instead of pretending one exact finish date exists.", font=FONT_BODY, fill=(244, 250, 244, 255))


DRAWERS = [
    scene_intro,
    scene_dataset,
    scene_event_time,
    scene_forest,
    scene_live_row,
    scene_curve,
    scene_windows,
    scene_final,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (10, 18, 12))
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

    combined_audio = run_dir / "random_survival_forest_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "random_survival_forest_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

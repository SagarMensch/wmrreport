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
OUTPUT_FILE = OUTPUT_DIR / "kaggle-risk-formula-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 24
SCENE_GAP_SECONDS = 0.24
MIN_SCENE_SECONDS = 10.5

EXAMPLE = {
    "progress": 0.45,
    "velocity": 0.02,
    "days_to_exp": -30,
    "week_ordinal": 16,
}
EXAMPLE["expected_progress"] = min(max(EXAMPLE["week_ordinal"] / 26.0, 0.0), 1.0)
EXAMPLE["progress_risk"] = 1.0 - EXAMPLE["progress"]
EXAMPLE["velocity_risk"] = 1.0 - min(max(EXAMPLE["velocity"], 0.0), 0.1) / 0.1
EXAMPLE["schedule_risk"] = 1.0 - (min(max(EXAMPLE["days_to_exp"], -100), 100) + 100) / 200
EXAMPLE["gap_risk"] = max(EXAMPLE["expected_progress"] - EXAMPLE["progress"], 0.0)

WEIGHTS = [
    ("Progress", 0.35, EXAMPLE["progress_risk"], "#F97316"),
    ("Velocity", 0.25, EXAMPLE["velocity_risk"], "#FB7185"),
    ("Schedule", 0.20, EXAMPLE["schedule_risk"], "#F59E0B"),
    ("Gap", 0.20, EXAMPLE["gap_risk"], "#FACC15"),
]

RISK_SCORE = round(
    sum(weight * component for _, weight, component, _ in WEIGHTS) * 100,
    1,
)
if RISK_SCORE >= 75:
    RISK_TIER = "CRITICAL"
elif RISK_SCORE >= 55:
    RISK_TIER = "HIGH_RISK"
elif RISK_SCORE >= 35:
    RISK_TIER = "WATCH"
else:
    RISK_TIER = "HEALTHY"

SCENES = [
    {
        "title": "Why Bashira Uses A Formula Risk Score",
        "subtitle": "Four different failure signals are combined into one readable number instead of one vague opinion.",
        "code": "feature_engine.py:84-89, 574-603",
        "accent": "#F97316",
        "narration": "This risk score exists because one well can look dangerous for different reasons. Maybe completion is low. Maybe weekly motion has slowed down. Maybe the schedule is already slipping. Maybe the well should be further ahead by this week. Bashira does not hide those reasons. It measures all four and blends them with explicit weights into one score.",
    },
    {
        "title": "Progress Risk Starts With Incompletion",
        "subtitle": "The first component is simple: unfinished work becomes progress risk.",
        "code": "feature_engine.py:582-585",
        "accent": "#FB923C",
        "narration": "The first component is progress risk. In code, it is one minus progress. So if a well is forty five percent complete, fifty five percent is still not complete, and that unfinished share becomes the progress risk. This is intuitive for non technical users. More completion means less risk. Less completion means more risk.",
    },
    {
        "title": "Velocity Risk Penalizes Slow Weekly Motion",
        "subtitle": "Bashira compares the current pace against a healthy weekly movement target of point one.",
        "code": "feature_engine.py:587-588",
        "accent": "#FB7185",
        "narration": "The second component is velocity risk. Bashira takes the current weekly movement, clamps it between zero and point one, then asks how far below the healthy point one pace the well is. In this example the well moves only point zero two, so most of the velocity budget is missing, and that turns into a high velocity risk.",
    },
    {
        "title": "Schedule Risk Measures Time Pressure",
        "subtitle": "Days to expected rig off are normalized from minus one hundred to plus one hundred into a risk band.",
        "code": "feature_engine.py:590-591",
        "accent": "#F59E0B",
        "narration": "The third component is schedule risk. Bashira looks at days to expected rig off. A positive number means there is schedule room left. A negative number means the well is overdue. Then the code normalizes that value inside a fixed minus one hundred to plus one hundred window. In this example, minus thirty days becomes a meaningful schedule pressure signal, but it still stays inside a bounded formula.",
    },
    {
        "title": "Gap Risk Compares Expected Versus Actual",
        "subtitle": "The fourth component asks whether this week number should already have produced more completion.",
        "code": "feature_engine.py:593-595",
        "accent": "#FACC15",
        "narration": "The fourth component is gap risk. Bashira builds a simple expected schedule by dividing the current week index by twenty six. At week sixteen, the expected progress is a little above sixty one percent. But the actual progress in our example is only forty five percent. That shortfall becomes gap risk. If the well is ahead of expectation, the gap risk is clipped back to zero.",
    },
    {
        "title": "The Four Risks Are Weighted, Not Treated Equally",
        "subtitle": "Progress gets thirty five percent, velocity twenty five, schedule twenty, and gap twenty.",
        "code": "feature_engine.py:84-89, 598-603",
        "accent": "#FDBA74",
        "narration": "Now Bashira mixes the components. But it does not treat them all equally. Progress carries thirty five percent of the final score. Velocity carries twenty five percent. Schedule and gap each carry twenty percent. So the formula is saying something very specific. Incompletion matters most, weekly pace matters next, and the two schedule style pressures complete the picture.",
    },
    {
        "title": "The Weighted Total Becomes A Zero To One Hundred Score",
        "subtitle": "The raw weighted sum is multiplied by one hundred, clipped to the range, and rounded.",
        "code": "feature_engine.py:598-603",
        "accent": "#F97316",
        "narration": "After weighting, Bashira adds the four contributions, multiplies by one hundred, clips the result so it cannot fall below zero or above one hundred, and rounds to one decimal place. In our example, the contributions add up to fifty five point five five, which rounds to fifty five point six. This is where the formula becomes a dashboard number.",
    },
    {
        "title": "Tier Gates Turn Math Into Action Language",
        "subtitle": "Thresholds convert the numeric score into healthy, watch, high risk, or critical.",
        "code": "feature_engine.py:606-615",
        "accent": "#EA580C",
        "narration": "A number alone is still not enough for an operator, so Bashira maps the score into one of four tiers. Seventy five and above becomes critical. Fifty five and above becomes high risk. Thirty five and above becomes watch. Anything lower is healthy. Because our example lands at fifty five point six, it crosses directly into high risk. That gives the system a fast action label without hiding the formula underneath.",
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
            "C:/Windows/Fonts/georgiab.ttf" if bold else "C:/Windows/Fonts/georgia.ttf",
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
FONT_SUB = load_font(23)
FONT_PANEL = load_font(27, bold=True)
FONT_BODY = load_font(19)
FONT_SMALL = load_font(15)
FONT_MONO = load_font(18, mono=True)
FONT_MONO_SMALL = load_font(15, mono=True)
FONT_NUMBER = load_font(56, bold=True, mono=True)
FONT_HUGE = load_font(78, bold=True, mono=True)


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


def fit_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_lines: int,
    max_size: int,
    min_size: int,
    *,
    bold: bool = False,
    mono: bool = False,
):
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


def metric_panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, accent, fill_alpha: float = 0.9):
    rounded(draw, (x + 8, y + 10, x + w + 8, y + h + 10), (25, 12, 4, 120), radius=26)
    rounded(draw, (x, y, x + w, y + h), rgba((28, 16, 8), fill_alpha), outline=rgba(accent, 0.78), radius=26, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    width = draw.textbbox((0, 0), text, font=FONT_TAG)[2] + 26
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.18), outline=rgba(accent, 0.66), radius=999, width=2)
    draw.text((x + 13, y + 7), text, font=FONT_TAG, fill=(*accent, 255))


def draw_header(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    scene = SCENES[scene_index]
    draw_chip(draw, 92, 24, f"RISK 06 / STAGE {scene_index + 1:02d}", accent)
    draw.text((92, 86), scene["title"], font=FONT_TITLE, fill=(246, 241, 232))
    draw.text((92, 134), scene["subtitle"], font=FONT_SUB, fill=(221, 212, 200))

    for i in range(len(SCENES)):
        dot_x = 28 + i * 28
        dot_color = accent if i == scene_index else (72, 48, 32)
        draw.ellipse((dot_x, 152, dot_x + 18, 170), fill=dot_color)

    code_text = scene["code"]
    box_width = max(310, draw.textbbox((0, 0), code_text, font=FONT_MONO_SMALL)[2] + 42)
    metric_panel(draw, WIDTH - box_width - 64, 22, box_width, 56, accent, fill_alpha=0.95)
    draw.text((WIDTH - box_width - 40, 40), code_text, font=FONT_MONO_SMALL, fill=(244, 234, 219))


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    metric_panel(draw, 86, HEIGHT - 84, WIDTH - 172, 46, accent, fill_alpha=0.95)
    draw.text((112, HEIGHT - 72), text, font=FONT_SUB, fill=(246, 239, 230))
    label = "RISK FORMULA"
    label_width = draw.textbbox((0, 0), label, font=FONT_TAG)[2]
    draw.text((WIDTH - 118 - label_width, HEIGHT - 70), label, font=FONT_TAG, fill=(*accent, 255))


def draw_backdrop(draw: ImageDraw.ImageDraw, accent):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(17, 10, 7))
    draw.ellipse((WIDTH - 350, -90, WIDTH + 60, 310), fill=rgba(accent, 0.10))
    draw.ellipse((-120, 520, 260, 900), fill=(95, 36, 16, 95))
    for x in range(80, WIDTH - 70, 90):
        draw.line((x, 176, x, 604), fill=(45, 27, 18, 70), width=1)
    for y in range(196, 606, 54):
        draw.line((88, y, WIDTH - 88, y), fill=(45, 27, 18, 65), width=1)


def draw_value_bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, ratio: float, accent, bg=(49, 31, 18)):
    rounded(draw, (x, y, x + w, y + h), bg, radius=h // 2)
    fill_w = max(12, int(w * clamp(ratio)))
    rounded(draw, (x, y, x + fill_w, y + h), rgba(accent, 0.95), radius=h // 2)


def draw_formula_card(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str, formula: str, note: str, accent):
    metric_panel(draw, x, y, w, h, accent)
    draw.text((x + 28, y + 24), title, font=FONT_PANEL, fill=(248, 240, 229))
    formula_lines = formula.splitlines() if "\n" in formula else wrap_text(draw, formula, FONT_MONO, w - 56)
    formula_y = y + 74
    for line in formula_lines:
        draw.text((x + 28, formula_y), line, font=FONT_MONO, fill=(*accent, 255))
        formula_y += FONT_MONO.size + 4
    note_font, lines = fit_text_block(draw, note, w - 56, 5, 20, 15)
    draw_lines(draw, x + 28, formula_y + 10, lines, note_font, (224, 214, 198), line_gap=4)


def scene_overview(draw: ImageDraw.ImageDraw, progress: float, accent):
    metric_panel(draw, 104, 214, 268, 304, accent)
    draw.text((132, 244), "Signals", font=FONT_PANEL, fill=(248, 240, 229))
    cards = [
        ("Progress", "completion still missing", "#F97316"),
        ("Velocity", "weekly motion too slow", "#FB7185"),
        ("Schedule", "days to rig-off shrinking", "#F59E0B"),
        ("Gap", "actual behind expected", "#FACC15"),
    ]
    for idx, (label, note, color_hex) in enumerate(cards):
        local = pop(progress, 0.08 + idx * 0.08)
        y = 290 + idx * 54
        card_color = rgb(color_hex)
        rounded(draw, (132, y, 344, y + 42), rgba(card_color, 0.18 + 0.30 * local), outline=rgba(card_color, 0.85), radius=16, width=2)
        draw.text((150, y + 8), label, font=FONT_BODY, fill=(248, 242, 234))
        draw.text((250, y + 10), note, font=FONT_SMALL, fill=(220, 209, 192))

    mixer_local = pop(progress, 0.30)
    cx, cy = 640, 366
    for radius, alpha in [(150, 0.12), (114, 0.18), (82, 0.25)]:
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=rgba(accent, alpha + mixer_local * 0.18), width=3)
    draw.text((564, 312), "Risk", font=FONT_PANEL, fill=(250, 242, 230))
    draw.text((548, 352), "mixer", font=FONT_HUGE, fill=(*accent, int(160 + 95 * mixer_local)))

    metric_panel(draw, 870, 214, 304, 304, accent)
    draw.text((900, 244), "Outputs", font=FONT_PANEL, fill=(248, 240, 229))
    outputs = [
        ("0-100", "bounded score"),
        (RISK_TIER.replace("_", " "), "action tier"),
        ("components", "still readable"),
    ]
    for idx, (value, note) in enumerate(outputs):
        y = 302 + idx * 72
        local = pop(progress, 0.44 + idx * 0.08)
        rounded(draw, (900, y, 1144, y + 54), rgba(accent, 0.10 + 0.18 * local), outline=rgba(accent, 0.72), radius=18, width=2)
        if idx == 0:
            draw.text((922, y + 1), value, font=FONT_NUMBER, fill=(248, 241, 232))
            draw.text((1080, y + 20), note, font=FONT_SMALL, fill=(224, 214, 198))
        else:
            draw.text((922, y + 6), value, font=FONT_PANEL, fill=(248, 241, 232))
            draw.text((922, y + 32), note, font=FONT_SMALL, fill=(224, 214, 198))

    for idx in range(4):
        local = pop(progress, 0.16 + idx * 0.06)
        x1 = 372
        x2 = 492 + idx * 18
        y1 = 311 + idx * 54
        y2 = 331 + idx * 8
        draw.line((x1, y1, blend(x1, x2, local), blend(y1, y2, local)), fill=rgba(accent, 0.5 + local * 0.5), width=5)
        draw.polygon(
            [
                (blend(x1, x2, local), blend(y1, y2, local)),
                (blend(x1, x2, local) - 14, blend(y1, y2, local) - 8),
                (blend(x1, x2, local) - 14, blend(y1, y2, local) + 8),
            ],
            fill=rgba(accent, 0.82),
        )


def scene_progress(draw: ImageDraw.ImageDraw, progress: float, accent):
    metric_panel(draw, 96, 214, 700, 316, accent)
    draw.text((128, 244), "Completion bar", font=FONT_PANEL, fill=(247, 240, 229))
    ratio = blend(0.12, EXAMPLE["progress"], pop(progress, 0.06))
    draw_value_bar(draw, 128, 310, 636, 52, ratio, accent)
    draw.text((128, 382), "actual progress", font=FONT_SMALL, fill=(219, 209, 192))
    draw.text((664, 382), f"{int(EXAMPLE['progress'] * 100)}%", font=FONT_NUMBER, fill=(248, 240, 229))

    risk_ratio = EXAMPLE["progress_risk"]
    rounded(draw, (128, 430, 764, 472), (52, 26, 17), radius=20)
    draw.text((154, 440), "unfinished share becomes progress risk", font=FONT_BODY, fill=(226, 216, 200))
    draw.text((632, 434), f"{risk_ratio * 100:.0f} risk", font=FONT_MONO, fill=(255, 207, 168))

    draw_formula_card(
        draw,
        832,
        228,
        348,
        286,
        "Code rule",
        "risk_prog = 1.0 - progress",
        "If forty five percent is complete, fifty five percent is still missing. Bashira uses that unfinished share as the progress risk.",
        accent,
    )


def scene_velocity(draw: ImageDraw.ImageDraw, progress: float, accent):
    metric_panel(draw, 96, 214, 532, 332, accent)
    cx, cy = 362, 390
    radius = 142
    draw.arc((cx - radius, cy - radius, cx + radius, cy + radius), start=200, end=340, fill=(82, 46, 56), width=18)
    for tick in range(6):
        angle = math.radians(200 + tick * 28)
        x1 = cx + math.cos(angle) * (radius - 22)
        y1 = cy + math.sin(angle) * (radius - 22)
        x2 = cx + math.cos(angle) * (radius + 10)
        y2 = cy + math.sin(angle) * (radius + 10)
        draw.line((x1, y1, x2, y2), fill=(226, 208, 212), width=3)
        label = f"{tick * 0.02:.2f}"
        lx = cx + math.cos(angle) * (radius + 30)
        ly = cy + math.sin(angle) * (radius + 30)
        bbox = draw.textbbox((0, 0), label, font=FONT_MONO_SMALL)
        draw.text((lx - (bbox[2] - bbox[0]) / 2, ly - 8), label, font=FONT_MONO_SMALL, fill=(228, 216, 221))
    pointer_value = blend(0.0, EXAMPLE["velocity"] / 0.1, pop(progress, 0.12))
    pointer_angle = math.radians(200 + 140 * pointer_value)
    px = cx + math.cos(pointer_angle) * (radius - 36)
    py = cy + math.sin(pointer_angle) * (radius - 36)
    draw.line((cx, cy, px, py), fill=rgb("#FB7185"), width=8)
    draw.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=(247, 238, 230))
    draw.text((300, 474), f"velocity = {EXAMPLE['velocity']:.2f}", font=FONT_MONO, fill=(247, 240, 232))
    rounded(draw, (218, 506, 520, 560), rgba(rgb("#FB7185"), 0.16), outline=rgba(rgb("#FB7185"), 0.82), radius=18, width=2)
    draw.text((248, 518), f"velocity risk = {EXAMPLE['velocity_risk'] * 100:.0f}", font=FONT_PANEL, fill=(255, 193, 207))

    draw_formula_card(
        draw,
        676,
        228,
        504,
        286,
        "Code rule",
        "risk_vel = 1 - clamp(velocity, 0, 0.1) / 0.1",
        "The code assumes point one is the healthy pace ceiling. A well moving at point zero two uses only one fifth of that pace, so the missing four fifths becomes velocity risk.",
        accent,
    )


def scene_schedule(draw: ImageDraw.ImageDraw, progress: float, accent):
    metric_panel(draw, 96, 214, 1088, 324, accent)
    draw.text((132, 246), "Normalization rail", font=FONT_PANEL, fill=(248, 240, 230))
    rail_x1, rail_x2, rail_y = 164, 1112, 384
    draw.line((rail_x1, rail_y, rail_x2, rail_y), fill=(93, 56, 30), width=8)
    for idx, label in enumerate([-100, -50, 0, 50, 100]):
        x = rail_x1 + idx * (rail_x2 - rail_x1) / 4
        draw.line((x, rail_y - 20, x, rail_y + 20), fill=(236, 216, 193), width=3)
        text = f"{label:+d}"
        bbox = draw.textbbox((0, 0), text, font=FONT_MONO_SMALL)
        draw.text((x - (bbox[2] - bbox[0]) / 2, rail_y + 34), text, font=FONT_MONO_SMALL, fill=(226, 214, 197))
    marker_ratio = (min(max(EXAMPLE["days_to_exp"], -100), 100) + 100) / 200
    marker_x = rail_x1 + (rail_x2 - rail_x1) * marker_ratio
    draw.line((marker_x, rail_y - 80, marker_x, rail_y + 82), fill=rgb("#F59E0B"), width=6)
    draw.ellipse((marker_x - 18, rail_y - 18, marker_x + 18, rail_y + 18), fill=rgb("#F59E0B"))
    draw.text((marker_x - 74, rail_y - 128), f"{EXAMPLE['days_to_exp']} days", font=FONT_MONO, fill=(253, 218, 159))

    draw_formula_card(
        draw,
        154,
        438,
        480,
        128,
        "Code rule",
        "risk_schedule = 1 - ((clamped_days + 100) / 200)",
        "Negative days mean overdue. Positive days mean breathing room.",
        accent,
    )
    draw_formula_card(
        draw,
        666,
        438,
        430,
        128,
        "Example result",
        f"-30 days -> {EXAMPLE['schedule_risk'] * 100:.0f} risk",
        "The formula keeps schedule pressure bounded instead of letting it explode.",
        accent,
    )


def scene_gap(draw: ImageDraw.ImageDraw, progress: float, accent):
    metric_panel(draw, 96, 214, 1088, 324, accent)
    draw.text((128, 246), "Expected-versus-actual ladder", font=FONT_PANEL, fill=(248, 240, 230))
    chart_x, chart_y = 170, 486
    chart_w, chart_h = 700, 186
    draw.line((chart_x, chart_y - chart_h, chart_x, chart_y), fill=(214, 201, 185), width=3)
    draw.line((chart_x, chart_y, chart_x + chart_w, chart_y), fill=(214, 201, 185), width=3)
    for pct in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = chart_y - chart_h * pct
        draw.line((chart_x - 10, y, chart_x + chart_w, y), fill=(66, 42, 22), width=1)
        draw.text((102, y - 10), f"{int(pct * 100)}%", font=FONT_MONO_SMALL, fill=(226, 212, 194))

    exp_h = chart_h * EXAMPLE["expected_progress"]
    act_h = chart_h * EXAMPLE["progress"]
    bar_w = 160
    rounded(draw, (344, chart_y - exp_h, 344 + bar_w, chart_y), rgba(rgb("#FACC15"), 0.86), radius=18)
    rounded(draw, (590, chart_y - act_h, 590 + bar_w, chart_y), rgba(rgb("#F59E0B"), 0.92), radius=18)
    draw.text((378, chart_y - exp_h - 42), f"expected {EXAMPLE['expected_progress'] * 100:.1f}%", font=FONT_MONO, fill=(252, 234, 136))
    draw.text((626, chart_y - act_h - 42), f"actual {EXAMPLE['progress'] * 100:.0f}%", font=FONT_MONO, fill=(252, 214, 164))

    gap_top = chart_y - exp_h
    gap_bottom = chart_y - act_h
    gap_x = 760
    draw.line((gap_x, gap_top, gap_x, gap_bottom), fill=(248, 239, 231), width=4)
    draw.polygon([(gap_x, gap_top), (gap_x - 10, gap_top + 16), (gap_x + 10, gap_top + 16)], fill=(248, 239, 231))
    draw.polygon([(gap_x, gap_bottom), (gap_x - 10, gap_bottom - 16), (gap_x + 10, gap_bottom - 16)], fill=(248, 239, 231))
    draw.text((784, (gap_top + gap_bottom) / 2 - 14), f"gap {EXAMPLE['gap_risk'] * 100:.1f}", font=FONT_MONO_SMALL, fill=(248, 239, 231))

    draw_formula_card(
        draw,
        910,
        248,
        234,
        188,
        "Code rule",
        "expected = week / 26\nrisk_gap = max(expected - progress, 0)",
        "Only being behind schedule counts. Being ahead does not create negative risk.",
        accent,
    )


def scene_weights(draw: ImageDraw.ImageDraw, progress: float, accent):
    metric_panel(draw, 86, 214, 1108, 334, accent)
    draw.text((120, 244), "Weighted mixer", font=FONT_PANEL, fill=(248, 240, 230))
    left_x = 136
    for idx, (label, weight, component, color_hex) in enumerate(WEIGHTS):
        y = 296 + idx * 58
        local = pop(progress, 0.08 + idx * 0.08)
        bar_color = rgb(color_hex)
        draw.text((left_x, y - 8), label, font=FONT_BODY, fill=(248, 240, 230))
        draw.text((left_x + 120, y - 8), f"{component * 100:.1f}", font=FONT_MONO, fill=(235, 223, 203))
        draw.text((left_x + 250, y - 8), f"x {weight:.2f}", font=FONT_MONO, fill=(235, 223, 203))
        draw_value_bar(draw, left_x + 360, y, 270, 26, component * local, bar_color, bg=(58, 34, 21))
        contribution = component * weight * 100
        draw.text((left_x + 664, y - 8), f"{contribution:.1f}", font=FONT_MONO, fill=(*bar_color, 255))

    mixer_x, mixer_y = 940, 378
    for radius, alpha in [(120, 0.12), (92, 0.18), (64, 0.25)]:
        draw.ellipse((mixer_x - radius, mixer_y - radius, mixer_x + radius, mixer_y + radius), outline=rgba(accent, alpha + 0.16), width=3)
    score_local = pop(progress, 0.48)
    draw.text((900, 310), f"{blend(0, RISK_SCORE, score_local):04.1f}", font=FONT_HUGE, fill=(255, 232, 208))
    draw.text((972, 402), "final score", font=FONT_BODY, fill=(231, 218, 200))
    formula = "0.35P + 0.25V + 0.20S + 0.20G"
    bbox = draw.textbbox((0, 0), formula, font=FONT_MONO)
    draw.text((mixer_x - (bbox[2] - bbox[0]) / 2, 462), formula, font=FONT_MONO, fill=(*accent, 255))


def scene_score(draw: ImageDraw.ImageDraw, progress: float, accent):
    metric_panel(draw, 96, 214, 660, 324, accent)
    draw.text((128, 246), "Score rail", font=FONT_PANEL, fill=(248, 240, 230))
    rail_x1, rail_x2, rail_y = 162, 704, 392
    draw.line((rail_x1, rail_y, rail_x2, rail_y), fill=(98, 58, 31), width=10)
    bands = [
        ("HEALTHY", 0, 35, "#22C55E"),
        ("WATCH", 35, 55, "#EAB308"),
        ("HIGH_RISK", 55, 75, "#F97316"),
        ("CRITICAL", 75, 100, "#DC2626"),
    ]
    for label, lo, hi, color_hex in bands:
        x1 = rail_x1 + (rail_x2 - rail_x1) * (lo / 100)
        x2 = rail_x1 + (rail_x2 - rail_x1) * (hi / 100)
        draw.line((x1, rail_y, x2, rail_y), fill=rgb(color_hex), width=14)
        draw.text((x1 + 8, rail_y - 46), label.replace("_", " "), font=FONT_SMALL, fill=rgb(color_hex))
    score_x = rail_x1 + (rail_x2 - rail_x1) * (blend(0, RISK_SCORE, pop(progress, 0.16)) / 100)
    draw.line((score_x, rail_y - 92, score_x, rail_y + 94), fill=(249, 244, 236), width=6)
    draw.ellipse((score_x - 22, rail_y - 22, score_x + 22, rail_y + 22), fill=rgb("#F97316"))
    draw.text((score_x - 56, rail_y + 112), f"{RISK_SCORE:.1f}", font=FONT_MONO, fill=(249, 241, 232))

    draw_formula_card(
        draw,
        800,
        228,
        380,
        286,
        "Tier gate",
        "75+ = CRITICAL\n55+ = HIGH_RISK\n35+ = WATCH\nelse = HEALTHY",
        f"Because {RISK_SCORE:.1f} is above 55 but below 75, Bashira marks this well as {RISK_TIER.replace('_', ' ')}.",
        accent,
    )


def scene_final(draw: ImageDraw.ImageDraw, progress: float, accent):
    metric_panel(draw, 90, 214, 1100, 334, accent)
    draw.text((122, 244), "One formula, still explainable", font=FONT_PANEL, fill=(248, 240, 230))

    left_local = pop(progress, 0.05)
    metric_panel(draw, 126, 288, 276, 196, accent)
    draw.text((154, 316), "Inputs", font=FONT_PANEL, fill=(248, 240, 230))
    inputs = [
        f"progress = {EXAMPLE['progress']:.2f}",
        f"velocity = {EXAMPLE['velocity']:.2f}",
        f"days_to_exp = {EXAMPLE['days_to_exp']}",
        f"week_ordinal = {EXAMPLE['week_ordinal']}",
    ]
    for idx, line in enumerate(inputs):
        draw.text((154, 366 + idx * 30), line, font=FONT_MONO, fill=(248, 233, 210, int(180 + 75 * left_local)))

    center_local = pop(progress, 0.20)
    metric_panel(draw, 472, 270, 334, 232, accent)
    draw.text((500, 302), "Blend", font=FONT_PANEL, fill=(248, 240, 230))
    blend_lines = [
        "P = 55.0",
        "V = 80.0",
        "S = 65.0",
        "G = 16.5",
        "-> 55.6",
    ]
    for idx, line in enumerate(blend_lines):
        draw.text((520, 352 + idx * 28), line, font=FONT_MONO, fill=(255, 230, 197, int(170 + 85 * center_local)))

    right_local = pop(progress, 0.36)
    metric_panel(draw, 876, 288, 272, 196, accent)
    draw.text((906, 316), "Decision", font=FONT_PANEL, fill=(248, 240, 230))
    draw.text((930, 372), f"{RISK_SCORE:.1f}", font=FONT_HUGE, fill=(255, 224, 189, int(170 + 85 * right_local)))
    draw.text((930, 448), RISK_TIER.replace("_", " "), font=FONT_MONO, fill=(*accent, int(170 + 85 * right_local)))

    for idx in range(2):
        local = pop(progress, 0.16 + idx * 0.18)
        x1 = 402 + idx * 404
        x2 = 472 + idx * 404
        y = 386
        draw.line((x1, y, blend(x1, x2, local), y), fill=rgba(accent, 0.58 + 0.32 * local), width=7)
        draw.polygon(
            [
                (blend(x1, x2, local), y),
                (blend(x1, x2, local) - 18, y - 10),
                (blend(x1, x2, local) - 18, y + 10),
            ],
            fill=rgba(accent, 0.92),
        )


DRAWERS = [
    scene_overview,
    scene_progress,
    scene_velocity,
    scene_schedule,
    scene_gap,
    scene_weights,
    scene_score,
    scene_final,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (17, 10, 7))
    draw = ImageDraw.Draw(image, "RGBA")
    draw_backdrop(draw, accent)
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

    combined_audio = run_dir / "kaggle_risk_formula_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "kaggle_risk_formula_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

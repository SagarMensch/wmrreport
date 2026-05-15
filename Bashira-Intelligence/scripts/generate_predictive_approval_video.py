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
OUTPUT_FILE = OUTPUT_DIR / "shap-driver-attribution-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 24
SCENE_GAP_SECONDS = 0.22
MIN_SCENE_SECONDS = 9.5

SCENES = [
    {
        "title": "The Mystery",
        "subtitle": "Will this well land in class 0 or class 1?",
        "code": "cpu_ml_orchestrator.py:1273-1286",
        "accent": "#F97316",
        "narration": "Imagine Bashira is helping us judge one well. The model asks a simple question. Does this well look more like class zero, which means lower delay risk, or class one, which means higher delay risk? The machine first chooses the class. Then SHAP explains why.",
    },
    {
        "title": "Meet The Clue Cards",
        "subtitle": "A feature is just one clue the model can read.",
        "code": "cpu_ml_orchestrator.py:233-264, 771-775",
        "accent": "#0EA5E9",
        "narration": "The model does not look at everything at once. It reads clue cards called features. Bashira builds ten live features for this risk model, including progress, recent pace, rig pace, material wait, and schedule pressure. These clue cards become one feature row called X live.",
    },
    {
        "title": "The Guessing Machine",
        "subtitle": "A classifier returns the chance of each class.",
        "code": "cpu_ml_orchestrator.py:291-345",
        "accent": "#2563EB",
        "narration": "Now the guessing machine runs. Bashira uses a Light G B M classifier. A classifier means a model that chooses between classes. When Bashira calls predict proba, the model returns percentages for class zero and class one. In this example, class one gets the bigger share, so delay risk looks higher.",
    },
    {
        "title": "SHAP The Detective",
        "subtitle": "SHAP measures how much each clue pushed the answer.",
        "code": "cpu_ml_orchestrator.py:319-331, 1284-1289",
        "accent": "#8B5CF6",
        "narration": "After the model makes its guess, SHAP plays detective. SHAP asks how strongly each clue pushed the answer. Some clues push toward class one, which means more delay risk. Other clues pull back toward class zero, which means less delay risk. That is why SHAP is useful. It turns a model answer into visible pushes.",
    },
    {
        "title": "Why Bashira Picks Class 1",
        "subtitle": "The code explains the delayed class on purpose.",
        "code": "cpu_ml_orchestrator.py:1284-1289",
        "accent": "#EC4899",
        "narration": "In the code, SHAP can return more than one explanation vector. Bashira deliberately picks class one. That matters because class one is the delayed class. So the system is not explaining the safer side. It is explaining why the model leaned toward delay.",
    },
    {
        "title": "Big Pushes First",
        "subtitle": "The biggest clue pushes become the top reasons.",
        "code": "cpu_ml_orchestrator.py:1288-1313",
        "accent": "#F43F5E",
        "narration": "Next Bashira sorts the clue pushes by size. The biggest pushes rise to the top. Weak pushes are ignored. The strongest few become the main reasons. In simple words, Bashira is asking: which clues mattered most for this delayed answer?",
    },
    {
        "title": "From Code Words To Human Words",
        "subtitle": "Technical feature names become simple sentences.",
        "code": "cpu_ml_orchestrator.py:626-666, 1298-1313",
        "accent": "#10B981",
        "narration": "The app does not show strange code names to the user. Bashira translates them. For example, schedule pressure becomes behind plan. Material lead days becomes material delay. Recent momentum becomes recent pace is weak. This is the step that makes the explanation understandable for normal people, not just engineers.",
    },
    {
        "title": "What The User Finally Sees",
        "subtitle": "Model says what. SHAP says why.",
        "code": "cpu_ml_orchestrator.py:1298-1313",
        "accent": "#F59E0B",
        "narration": "The final screen is simple. Bashira shows the risk percentage and a few plain language reasons, such as low progress, weak recent pace, and material delay. So the machine learning model still does the heavy math, but the user receives a short explanation that feels human and actionable.",
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
    draw_label(draw, 72, 24, "Creative Lesson Video", accent)
    shadow_card(draw, 930, 26, 280, 44, (15, 23, 42, 240), (51, 65, 85, 255), radius=18)
    draw.text((952, 39), SCENES[scene_index]["code"], font=FONT_CODE, fill=(148, 163, 184, 255))
    start_x = 968
    for idx in range(len(SCENES)):
        fill = accent if idx == scene_index else (71, 85, 105)
        draw.ellipse((start_x + idx * 28, 84, start_x + idx * 28 + 12, 96), fill=(*fill, 255))


def footer(draw: ImageDraw.ImageDraw, text: str, accent):
    shadow_card(draw, 74, 626, 1132, 56, (12, 20, 36, 238), (30, 41, 59, 255), radius=24)
    draw.text((102, 643), text, font=FONT_SUB, fill=(241, 245, 249, 255))
    draw.text((1120, 643), "SHAP", font=FONT_TAG, fill=(*accent, 255))


def scene_problem(draw: ImageDraw.ImageDraw, progress: float, accent):
    p = ease(progress)
    well_x = int(blend(-240, 130, pop(p, 0.02, 0.28)))
    draw_card(draw, well_x, 250, 240, 220, "Well A", "One live well is turned into a prediction example.", accent)
    draw.text((well_x + 30, 420), "Question:", font=FONT_TAG, fill=(*accent, 255))
    draw.text((well_x + 30, 448), "On time or delayed?", font=FONT_BODY, fill=(51, 65, 85, 255))

    class0_y = int(blend(120, 220, pop(p, 0.16, 0.22)))
    class1_y = int(blend(620, 430, pop(p, 0.24, 0.22)))
    shadow_card(draw, 860, class0_y, 250, 120, (236, 253, 245, 255), (34, 197, 94, 255), radius=26)
    draw.text((890, class0_y + 26), "Class 0", font=FONT_CARD, fill=(22, 101, 52, 255))
    draw.text((890, class0_y + 64), "Lower delay risk", font=FONT_BODY, fill=(22, 101, 52, 255))
    shadow_card(draw, 860, class1_y, 250, 120, (254, 242, 242, 255), (239, 68, 68, 255), radius=26)
    draw.text((890, class1_y + 26), "Class 1", font=FONT_CARD, fill=(153, 27, 27, 255))
    draw.text((890, class1_y + 64), "Higher delay risk", font=FONT_BODY, fill=(153, 27, 27, 255))

    if p > 0.28:
        draw_arrow(draw, (well_x + 240, 360), (860, 360), (*accent, 255), width=7)
        token_x = int(blend(well_x + 270, 826, pop(p, 0.30, 0.40)))
        token_y = int(blend(360, 490, pop(p, 0.55, 0.25)))
        draw.ellipse((token_x - 18, token_y - 18, token_x + 18, token_y + 18), fill=(*accent, 255))
        if p > 0.6:
            draw.text((1130, class0_y + 44), "31%", font=FONT_CARD, fill=(22, 101, 52, 255))
            draw.text((1130, class1_y + 44), "69%", font=FONT_CARD, fill=(153, 27, 27, 255))


def scene_clues(draw: ImageDraw.ImageDraw, progress: float, accent):
    shadow_card(draw, 430, 190, 420, 340, (255, 255, 255, 255), (226, 232, 240, 255), radius=46)
    draw.ellipse((520, 250, 760, 490), fill=rgba(accent, 0.10), outline=(*accent, 255), width=4)
    draw.text((575, 340), "10", font=FONT_TITLE, fill=(15, 23, 42, 255))
    draw.text((545, 392), "clue cards", font=FONT_SUB, fill=(71, 85, 105, 255))

    cards = [
        ("Progress", 120, 220, 0.06),
        ("Recent pace", 160, 468, 0.14),
        ("Rig pace", 888, 210, 0.22),
        ("Material wait", 862, 468, 0.30),
        ("Schedule pressure", 500, 500, 0.38),
    ]
    for title, x, y, delay in cards:
        appear = pop(progress, delay, 0.20)
        card_x = int(blend(x - 120, x, appear))
        width = 250 if title == "Schedule pressure" else 220
        draw_card(draw, card_x, y, width, 100, title, "One input clue", accent, alpha=max(0.15, appear))
    bubble = pop(progress, 0.50, 0.22)
    shadow_card(draw, 948, 108, 140, 72, rgba(accent, 0.18 * bubble), rgba(accent, max(0.2, bubble)), radius=999)
    draw.text((985, 132), "+ 5 more", font=FONT_CARD, fill=rgba((248, 250, 252), bubble))


def scene_model(draw: ImageDraw.ImageDraw, progress: float, accent):
    for idx, title in enumerate(["Progress", "Pace", "Materials"]):
        draw_card(draw, 110, 220 + idx * 120, 190, 84, title, "Feature", accent, alpha=0.95)
        draw_arrow(draw, (300, 262 + idx * 120), (438, 350), rgba(accent, 0.90), width=5)
    draw.ellipse((438, 220, 720, 500), fill=rgba(accent, 0.16), outline=(*accent, 255), width=5)
    draw.text((502, 320), "LightGBM", font=FONT_TITLE, fill=(248, 250, 252, 255))
    draw.text((520, 380), "classifier", font=FONT_SUB, fill=(224, 231, 255, 255))
    draw.text((474, 526), "predict_proba", font=FONT_TAG, fill=(*accent, 255))

    draw_arrow(draw, (720, 320), (920, 280), (*accent, 255), width=7)
    draw_arrow(draw, (720, 400), (920, 460), (*accent, 255), width=7)
    shadow_card(draw, 920, 220, 250, 120, (236, 253, 245, 255), (34, 197, 94, 255), radius=26)
    shadow_card(draw, 920, 400, 250, 120, (254, 242, 242, 255), (239, 68, 68, 255), radius=26)
    draw.text((952, 248), "Class 0", font=FONT_CARD, fill=(22, 101, 52, 255))
    draw.text((952, 428), "Class 1", font=FONT_CARD, fill=(153, 27, 27, 255))
    meter_p = pop(progress, 0.35, 0.35)
    draw_meter(draw, 952, 292, 180, (34, 197, 94), 0.31 * meter_p)
    draw_meter(draw, 952, 472, 180, (239, 68, 68), 0.69 * meter_p)
    if meter_p > 0.4:
        draw.text((1146, 284), "31%", font=FONT_BODY, fill=(22, 101, 52, 255))
        draw.text((1146, 464), "69%", font=FONT_BODY, fill=(153, 27, 27, 255))


def scene_shap(draw: ImageDraw.ImageDraw, progress: float, accent):
    draw.text((188, 198), "Class 0", font=FONT_CARD, fill=(22, 101, 52, 255))
    draw.text((966, 198), "Class 1", font=FONT_CARD, fill=(153, 27, 27, 255))
    draw.line([(280, 360), (1000, 360)], fill=(203, 213, 225, 255), width=10)
    draw.ellipse((626, 330, 654, 358), fill=(255, 255, 255, 255), outline=(148, 163, 184, 255), width=3)
    draw.text((560, 390), "SHAP measures how much each clue pushes the answer.", font=FONT_SUB, fill=(226, 232, 240, 255))

    pushes = [
        ("Schedule pressure", 740, 255, 0.16, 140),
        ("Material wait", 860, 470, 0.28, 110),
        ("Low progress", 430, 255, 0.40, -70),
    ]
    for label, x, y, delay, delta in pushes:
        show = pop(progress, delay, 0.20)
        draw_card(draw, x, y, 220, 86, label, "Clue push", accent, alpha=max(0.2, show))
        end_x = 640 + int(delta * show)
        draw_arrow(draw, (x + 110, y + 86 if y < 360 else y), (end_x, 360), rgba(accent, 0.90), width=6)

    needle = int(blend(640, 780, pop(progress, 0.58, 0.26)))
    draw.ellipse((needle - 18, 342, needle + 18, 378), fill=(239, 68, 68, 255))


def scene_class_one(draw: ImageDraw.ImageDraw, progress: float, accent):
    shadow_card(draw, 220, 170, 360, 92, (255, 255, 255, 255), (226, 232, 240, 255), radius=30)
    shadow_card(draw, 628, 170, 430, 92, (254, 242, 242, 255), (239, 68, 68, 255), radius=30)
    draw.text((258, 204), "Explain class 0", font=FONT_CARD, fill=(71, 85, 105, 255))
    draw.text((666, 204), "Explain class 1", font=FONT_CARD, fill=(153, 27, 27, 255))
    draw.text((468, 312), "Bashira picks", font=FONT_SUB, fill=(226, 232, 240, 255))
    shadow_card(draw, 416, 350, 460, 86, (18, 24, 39, 255), (99, 102, 241, 255), radius=24)
    draw.text((446, 378), "shap_values[1][0]", font=FONT_TITLE, fill=(224, 231, 255, 255))
    draw.text((320, 490), "That means: explain the delayed class.", font=FONT_SUB, fill=(248, 250, 252, 255))

    bar_p = pop(progress, 0.42, 0.28)
    draw_meter(draw, 320, 548, 580, accent, 0.86 * bar_p)
    draw.text((924, 540), "class 1 push", font=FONT_BODY, fill=(248, 250, 252, 255))


def scene_ranking(draw: ImageDraw.ImageDraw, progress: float, accent):
    podium = [
        (505, 320, 280, 220, "1", "Schedule pressure", "28%"),
        (220, 388, 250, 152, "2", "Material wait", "23%"),
        (820, 418, 250, 122, "3", "Recent pace", "18%"),
    ]
    for idx, (x, y, w, h, rank, label, pct) in enumerate(podium):
        appear = pop(progress, 0.12 + idx * 0.14, 0.22)
        shown_y = int(blend(y + 80, y, appear))
        fill = (255, 255, 255, 255) if idx else rgba(accent, 0.18)
        outline = rgba(accent, 0.85 if idx == 0 else 0.55)
        shadow_card(draw, x, shown_y, w, h, fill, outline, radius=28)
        draw.text((x + 26, shown_y + 22), rank, font=FONT_TITLE, fill=(*accent, 255))
        label_font, label_lines = fit_text_block(draw, label, w - 108, 2, 24, 15, True)
        label_bottom = draw_lines(draw, x + 84, shown_y + 34, label_lines, label_font, (15, 23, 42, 255), line_gap=0)
        draw.text((x + 84, label_bottom + 10), pct, font=FONT_SUB, fill=(71, 85, 105, 255))
    draw.text((354, 590), "The biggest SHAP pushes become the top reasons.", font=FONT_SUB, fill=(248, 250, 252, 255))


def scene_translation(draw: ImageDraw.ImageDraw, progress: float, accent):
    pairs = [
        ("schedule_pressure", "We are behind plan."),
        ("material_lead_days", "Materials are arriving late."),
        ("recent_momentum_3w", "Recent work is moving slowly."),
    ]
    for idx, (raw, plain) in enumerate(pairs):
        y = 210 + idx * 132
        show = pop(progress, 0.10 + idx * 0.16, 0.22)
        raw_x = int(blend(-140, 120, show))
        plain_x = int(blend(1280, 760, show))
        shadow_card(draw, raw_x, y, 310, 82, (18, 24, 39, 255), (99, 102, 241, 255), radius=22)
        draw.text((raw_x + 22, y + 28), raw, font=FONT_BODY, fill=(224, 231, 255, 255))
        draw_arrow(draw, (raw_x + 310, y + 42), (plain_x, y + 42), rgba(accent, 0.92), width=5)
        shadow_card(draw, plain_x, y, 360, 82, (240, 253, 244, 255), (16, 185, 129, 255), radius=22)
        draw.text((plain_x + 22, y + 28), plain, font=FONT_BODY, fill=(22, 101, 52, 255))
    draw.text((330, 630), "Bashira converts code words into simple classroom language.", font=FONT_SUB, fill=(248, 250, 252, 255))


def scene_final(draw: ImageDraw.ImageDraw, progress: float, accent):
    shadow_card(draw, 250, 166, 780, 390, (255, 255, 255, 255), (226, 232, 240, 255), radius=40)
    draw.text((320, 216), "Final answer for one well", font=FONT_CARD, fill=(*accent, 255))
    draw.text((320, 272), "Delay risk", font=FONT_SUB, fill=(71, 85, 105, 255))
    draw.text((320, 320), "69%", font=FONT_TITLE, fill=(15, 23, 42, 255))
    draw_meter(draw, 320, 392, 360, accent, 0.69)

    speech = [
        "Low progress is pushing risk up.",
        "Recent pace is weaker than similar wells.",
        "Material delay is adding pressure.",
    ]
    for idx, line in enumerate(speech):
        y = 250 + idx * 92
        shadow_card(draw, 710, y, 250, 68, (254, 249, 195, 255), (245, 158, 11, 255), radius=26)
        text_block(draw, (732, y + 18), line, FONT_SMALL, (113, 63, 18, 255), 206, line_gap=2)

    draw.text((350, 594), "The model says what. SHAP says why.", font=FONT_SUB, fill=(248, 250, 252, 255))


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

    combined_audio = run_dir / "shap_creative_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "shap_creative_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

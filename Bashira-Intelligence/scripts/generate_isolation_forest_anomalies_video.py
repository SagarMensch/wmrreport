from __future__ import annotations

import gc
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
OUTPUT_FILE = OUTPUT_DIR / "isolation-forest-anomalies-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 20
SCENE_GAP_SECONDS = 0.24
MIN_SCENE_SECONDS = 12.0

RED = "#DC2626"
AMBER = "#F59E0B"
ORANGE = "#FB7185"
SLATE = "#94A3B8"
ICE = "#E2E8F0"

FEATURES = [
    ("progress_pct", "42.0"),
    ("delay_days", "18"),
    ("rig_on_delay_days", "11"),
    ("current_gap_pct", "19.4"),
    ("avg_gap_pct", "14.1"),
    ("negative_velocity_pct", "6.8"),
    ("stage_gap_avg", "22.7"),
    ("stage_imbalance", "0.41"),
    ("risk_score", "71.0"),
    ("queue_exposure", "3"),
    ("missing_fields", "2"),
]

SCORES = [
    ("WELL-118", 91.2, True),
    ("WELL-203", 74.8, True),
    ("WELL-044", 62.3, False),
    ("WELL-087", 28.6, False),
]

SCENES = [
    {
        "title": "Why Bashira Uses Anomaly Logic",
        "subtitle": "Some execution failures have no clean label yet, so Bashira watches for wells that behave unlike the current fleet pattern.",
        "code": "command_center_service.py:339-356",
        "accent": RED,
        "narration": "This topic is about pattern break, not a predefined class label. In real operations, some bad behavior has not been named yet. Bashira still needs to notice it. So the service uses anomaly logic to ask a different question. Which wells look unlike the current fleet execution pattern, even before someone has formally labeled the problem?",
    },
    {
        "title": "A Live Outlier Row Is Built For Each Active Well",
        "subtitle": "Only active wells enter the anomaly frame, and each row carries progress, delay, queue, stage, and data-gap signals.",
        "code": "command_center_service.py:1541-1557",
        "accent": ORANGE,
        "narration": "The anomaly detector does not read a vague story. It reads a concrete feature row for each active well. Bashira collects progress percent, delay days, rig on delay, current and average gap, negative velocity, stage gap average, stage imbalance, prior risk score, queue exposure, and missing fields. This row describes how one well is behaving right now compared with the fleet around it.",
    },
    {
        "title": "Guardrails Decide Whether IsolationForest Should Run",
        "subtitle": "The service skips scoring if sklearn is unavailable, if fewer than 16 rows exist, or if the feature table is empty or nearly constant.",
        "code": "command_center_service.py:340-353",
        "accent": AMBER,
        "narration": "Bashira does not force anomaly math onto bad input. The service checks a few guardrails first. If the Isolation Forest library is unavailable, if there are too few active wells, if the table is empty, or if almost every feature is constant, it simply returns no anomaly scores. That prevents fake precision from a dataset that is too small or too flat to separate unusual behavior from normal variation.",
    },
    {
        "title": "The Forest Uses 240 Trees And Adaptive Contamination",
        "subtitle": "Bashira sizes the contamination rate from fleet size, keeps it between 8 and 18 percent, and fits a 240-tree IsolationForest.",
        "code": "command_center_service.py:354-363",
        "accent": RED,
        "narration": "Once the guardrails pass, Bashira fits the anomaly model. It does not hard code one outlier rate for every fleet size. Instead, it computes contamination from the number of active wells, then clamps that value between eight and eighteen percent. The model itself uses two hundred forty trees. That gives the service enough random partitions to estimate whether a well is easy to isolate from the rest.",
    },
    {
        "title": "Unusual Wells Are Isolated Faster",
        "subtitle": "A well that differs sharply on delay, queue pressure, stage imbalance, or missing data gets separated in fewer random splits than a normal well.",
        "code": "command_center_service.py:361-364",
        "accent": ORANGE,
        "narration": "The logic inside Isolation Forest is simple once you picture it. Each tree makes random cuts through the feature space. Normal wells live inside dense neighborhoods, so it takes more cuts to isolate them. Strange wells sit away from the crowd, so they get isolated quickly. In this Bashira flow, a well can look strange because its delay, queue exposure, stage imbalance, missing data, or negative velocity pattern no longer matches the fleet's usual shape.",
    },
    {
        "title": "Raw Outlier Energy Is Normalized To 0 Through 100",
        "subtitle": "Bashira negates `score_samples`, rescales the spread to a 0-100 anomaly score, and flags a well if prediction is -1 or score is at least 67.",
        "code": "command_center_service.py:368-384",
        "accent": AMBER,
        "narration": "After fitting the forest, Bashira pulls raw outlier energy from score samples, flips the sign so larger means stranger, then rescales the spread to a zero through one hundred score. That makes the output easier to read across the product. A well is flagged if the forest prediction is negative one, or if the normalized score is at least sixty seven. So Bashira has both a model flag and a human-readable severity number.",
    },
    {
        "title": "The Outlier Signal Feeds Ops Risk And Confidence Gaps",
        "subtitle": "The anomaly score contributes 8 percent of the operations risk blend and also strengthens the confidence-gap component in the score breakdown.",
        "code": "command_center_service.py:1592-1623",
        "accent": RED,
        "narration": "The anomaly score does not stay isolated in a side panel. Bashira feeds it into the live operations risk blend. The score contributes eight percent of the operations risk formula, and it also strengthens the confidence gap component in the breakdown panel. That means unusual behavior can raise urgency even when the well has not yet crossed a simple delay threshold.",
    },
    {
        "title": "Flagged Wells Produce Plain Action And Evidence",
        "subtitle": "When a well is flagged, Bashira adds an outlier review action, anomaly evidence text, and an Operational Outlier badge for the monitoring surfaces.",
        "code": "command_center_service.py:1633-1689",
        "accent": ORANGE,
        "narration": "The final step turns the anomaly into operational language. If a well is flagged, Bashira inserts a review execution outlier action, adds evidence text that includes the anomaly score, and stamps an Operational Outlier badge into the monitoring record. This is the handoff from machine learning to decision support. The forest is not there just to admire the score. It is there to make unusual wells impossible to ignore.",
    },
]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ease(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


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
FONT_PANEL = load_font(28, bold=True)
FONT_BODY = load_font(19)
FONT_SMALL = load_font(15)
FONT_MONO = load_font(18, mono=True)
FONT_MONO_SMALL = load_font(15, mono=True)
FONT_NUMBER = load_font(56, bold=True, mono=True)
FONT_HUGE = load_font(62, bold=True, mono=True)


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


def panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, accent, fill_alpha: float = 0.92):
    rounded(draw, (x + 10, y + 12, x + w + 10, y + h + 12), (22, 10, 10, 124), radius=26)
    rounded(draw, (x, y, x + w, y + h), rgba((14, 10, 10), fill_alpha), outline=rgba(accent, 0.82), radius=26, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    width = draw.textbbox((0, 0), text, font=FONT_TAG)[2] + 28
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.16), outline=rgba(accent, 0.72), radius=999, width=2)
    draw.text((x + 14, y + 7), text, font=FONT_TAG, fill=(*accent, 255))


def draw_background(draw: ImageDraw.ImageDraw, accent, progress: float):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(11, 8, 8))
    draw.ellipse((WIDTH - 330, -90, WIDTH + 70, 300), fill=rgba(accent, 0.12))
    draw.ellipse((-180, 520, 250, 900), fill=rgba(rgb(AMBER), 0.12))
    for y in range(176, 620, 36):
        draw.line((76, y, WIDTH - 76, y), fill=(64, 26, 26, 30), width=1)
    for x in range(96, WIDTH - 80, 84):
        draw.line((x, 176, x, 620), fill=(64, 26, 26, 18), width=1)
    center = (980, 390)
    max_radius = 220
    pulse = 0.85 + 0.15 * np.sin(progress * np.pi)
    for radius in range(56, max_radius, 36):
        alpha = 0.14 if radius % 72 == 0 else 0.08
        draw.arc(
            (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
            start=-30,
            end=230,
            fill=rgba(accent, alpha * pulse),
            width=2,
        )
    beam_end = (
        int(center[0] + np.cos(-0.8 + progress * 1.7) * 210),
        int(center[1] + np.sin(-0.8 + progress * 1.7) * 210),
    )
    draw.line((center[0], center[1], beam_end[0], beam_end[1]), fill=rgba(accent, 0.28), width=4)


def draw_header(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    scene = SCENES[scene_index]
    draw_chip(draw, 88, 24, f"OPS WATCH / STAGE {scene_index + 1:02d}", accent)
    draw.text((88, 82), scene["title"], font=FONT_TITLE, fill=(244, 238, 238))
    subtitle_font, subtitle_lines = fit_text_block(draw, scene["subtitle"], 1080, 2, 22, 18)
    draw_lines(draw, 88, 132, subtitle_lines, subtitle_font, (225, 214, 214), line_gap=2)
    for idx in range(len(SCENES)):
        dot_x = 28 + idx * 28
        dot_color = accent if idx == scene_index else (92, 48, 48)
        draw.ellipse((dot_x, 150, dot_x + 18, 168), fill=dot_color)
    code_text = scene["code"]
    box_width = max(340, draw.textbbox((0, 0), code_text, font=FONT_MONO_SMALL)[2] + 42)
    panel(draw, WIDTH - box_width - 60, 22, box_width, 58, accent, fill_alpha=0.96)
    draw.text((WIDTH - box_width - 38, 41), code_text, font=FONT_MONO_SMALL, fill=(242, 236, 236))


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    panel(draw, 82, HEIGHT - 84, WIDTH - 164, 48, accent, fill_alpha=0.96)
    label = "ISOLATIONFOREST"
    label_width = draw.textbbox((0, 0), label, font=FONT_TAG)[2]
    footer_font, lines = fit_text_block(draw, text, WIDTH - 320 - label_width, 1, 22, 18)
    draw_lines(draw, 108, HEIGHT - 72, lines, footer_font, (244, 238, 238), line_gap=0)
    draw.text((WIDTH - 118 - label_width, HEIGHT - 69), label, font=FONT_TAG, fill=(*accent, 255))


def metric_bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, ratio: float, accent):
    rounded(draw, (x, y, x + w, y + 16), (34, 18, 18), radius=8)
    fill_w = max(8, int(w * clamp(ratio)))
    rounded(draw, (x, y, x + fill_w, y + 16), rgba(accent, 0.95), radius=8)


def scene_why(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 94, 210, 470, 330, accent)
    draw.text((126, 242), "Why not wait for labels?", font=FONT_PANEL, fill=(244, 238, 238))
    bullets = [
        "some failures have no formal tag yet",
        "pattern break can appear before threshold breach",
        "outlier logic catches unusual wells early",
    ]
    for idx, bullet in enumerate(bullets):
        y = 316 + idx * 58
        draw.ellipse((128, y + 10, 144, y + 26), fill=(*accent, 255))
        font, lines = fit_text_block(draw, bullet, 360, 2, 20, 17)
        draw_lines(draw, 158, y, lines, font, (225, 214, 214), line_gap=2)
    panel(draw, 640, 212, 544, 328, accent)
    draw.text((674, 242), "fleet pattern monitor", font=FONT_PANEL, fill=(244, 238, 238))
    draw.text((720, 346), "normal wells cluster", font=FONT_BODY, fill=(225, 214, 214))
    draw.text((884, 462), "one well sits far away", font=FONT_BODY, fill=(*accent, 255))
    normal_points = [(760, 376), (796, 420), (842, 388), (818, 346), (864, 430), (914, 378)]
    for px, py in normal_points:
        draw.ellipse((px, py, px + 14, py + 14), fill=rgba(rgb(SLATE), 0.9))
    draw.ellipse((1016, 470, 1036, 490), fill=rgba(accent, 1.0))


def scene_rows(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    draw.text((122, 240), "Active-well anomaly row", font=FONT_PANEL, fill=(244, 238, 238))
    for idx, (label, value) in enumerate(FEATURES):
        x = 128 + (idx % 4) * 260
        y = 302 + (idx // 4) * 80
        rounded(draw, (x, y, x + 226, y + 56), rgba(accent, 0.06), outline=rgba(accent, 0.72), radius=18, width=2)
        font, lines = fit_text_block(draw, label, 160, 2, 17, 14, mono=True)
        draw_lines(draw, x + 14, y + 10, lines, font, (225, 214, 214), line_gap=1)
        draw.text((x + 160, y + 18), value, font=FONT_MONO_SMALL, fill=(*accent, 255))


def scene_guardrails(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 94, 210, 520, 330, accent)
    draw.text((126, 242), "Run only when the data is trustworthy", font=FONT_PANEL, fill=(244, 238, 238))
    rules = [
        "sklearn IsolationForest exists",
        "at least 16 active wells",
        "feature frame is not empty",
        "table has real variability",
    ]
    for idx, rule in enumerate(rules):
        y = 304 + idx * 50
        draw.ellipse((130, y + 8, 146, y + 24), fill=(*accent, 255))
        font, lines = fit_text_block(draw, rule, 410, 2, 19, 16)
        draw_lines(draw, 160, y, lines, font, (225, 214, 214), line_gap=2)
    panel(draw, 676, 210, 512, 330, accent)
    draw.text((708, 242), "Why these checks matter", font=FONT_PANEL, fill=(244, 238, 238))
    note = "Bashira would rather return no anomaly score than pretend a tiny or flat dataset can separate unusual wells correctly."
    font, lines = fit_text_block(draw, note, 442, 6, 21, 17)
    draw_lines(draw, 710, 318, lines, font, (225, 214, 214), line_gap=4)


def scene_forest(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    draw.text((122, 240), "Adaptive forest setup", font=FONT_PANEL, fill=(244, 238, 238))
    cards = [
        ("n_estimators", "240 trees"),
        ("contamination", "8% to 18%"),
        ("random_state", "42"),
    ]
    for idx, (label, value) in enumerate(cards):
        x = 136 + idx * 318
        rounded(draw, (x, 308, x + 250, 438), rgba(accent, 0.08), outline=rgba(accent, 0.76), radius=22, width=2)
        draw.text((x + 18, 334), label, font=FONT_MONO_SMALL, fill=(225, 214, 214))
        draw.text((x + 18, 382), value, font=FONT_PANEL, fill=(*accent, 255))
    draw.text((216, 490), "contamination = min(0.18, max(0.08, 14 / row_count))", font=FONT_MONO, fill=(244, 238, 238))


def scene_isolate(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    draw.text((122, 240), "How an unusual well gets isolated faster", font=FONT_PANEL, fill=(244, 238, 238))
    draw.text((122, 286), "random cuts through feature space", font=FONT_MONO_SMALL, fill=(*accent, 255))
    boxes = [
        (156, 332, 326, 500),
        (388, 332, 604, 500),
        (634, 332, 838, 500),
        (866, 332, 1094, 500),
    ]
    for idx, box in enumerate(boxes):
        x1, y1, x2, y2 = box
        rounded(draw, box, rgba(accent, 0.04), outline=rgba(accent, 0.5), radius=14, width=2)
        draw.line((x1 + 40, y1 + 60, x2 - 28, y2 - 46), fill=rgba(accent, 0.38), width=2)
        draw.line((x1 + 24, y2 - 66, x2 - 54, y1 + 40), fill=rgba(rgb(AMBER), 0.28), width=2)
        for px, py in [(x1 + 54, y1 + 108), (x1 + 88, y1 + 136), (x1 + 120, y1 + 92), (x1 + 146, y1 + 150)]:
            draw.ellipse((px, py, px + 12, py + 12), fill=rgba(rgb(SLATE), 0.95))
        danger_x = int(x2 - 54 + idx * 2)
        danger_y = int(y2 - 72 - idx * 5)
        draw.ellipse((danger_x, danger_y, danger_x + 16, danger_y + 16), fill=rgba(accent, 1.0))
    draw.text((392, 522), "odd wells separate in fewer splits than dense-cluster wells", font=FONT_BODY, fill=(225, 214, 214))


def scene_scores(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    draw.text((122, 240), "Normalized anomaly board", font=FONT_PANEL, fill=(244, 238, 238))
    draw.text((122, 286), "flag if predict == -1 or normalized score >= 67", font=FONT_MONO_SMALL, fill=(*accent, 255))
    headers = ["well", "score /100", "flag"]
    xs = [144, 564, 944]
    for x, header in zip(xs, headers):
        draw.text((x, 320), header, font=FONT_MONO_SMALL, fill=(176, 158, 158))
    for idx, (well_id, score, flagged) in enumerate(SCORES):
        y = 356 + idx * 44
        rounded(draw, (132, y, 1138, y + 34), rgba(accent, 0.06), outline=rgba(accent, 0.68), radius=16, width=2)
        draw.text((148, y + 9), well_id, font=FONT_MONO_SMALL, fill=(244, 238, 238))
        metric_bar(draw, 528, y + 8, 280, score / 100.0, accent if flagged else rgb(SLATE))
        draw.text((824, y + 9), f"{score:.1f}", font=FONT_MONO_SMALL, fill=(*accent, 255) if flagged else (225, 214, 214))
        draw.text((946, y + 9), "Operational outlier" if flagged else "Normal range", font=FONT_MONO_SMALL, fill=(*accent, 255) if flagged else (225, 214, 214))


def scene_blend(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 94, 210, 520, 330, accent)
    draw.text((126, 242), "Ops risk blend", font=FONT_PANEL, fill=(244, 238, 238))
    parts = [
        ("base_score", 0.78, rgb(AMBER)),
        ("queue_component", 0.14, rgb(SLATE)),
        ("anomaly_score", 0.08, accent),
    ]
    for idx, (label, weight, color) in enumerate(parts):
        y = 316 + idx * 66
        draw.text((126, y), f"{label} x {weight:.2f}", font=FONT_MONO_SMALL, fill=(225, 214, 214))
        metric_bar(draw, 126, y + 24, 380, weight, color)
    panel(draw, 676, 210, 512, 330, accent)
    draw.text((708, 242), "Downstream effect", font=FONT_PANEL, fill=(244, 238, 238))
    bullets = [
        "raises ops_risk_score",
        "strengthens confidence gaps",
        "can lift urgency before hard delay escalation",
    ]
    for idx, bullet in enumerate(bullets):
        y = 316 + idx * 56
        draw.ellipse((708, y + 8, 724, y + 24), fill=(*accent, 255))
        font, lines = fit_text_block(draw, bullet, 400, 2, 19, 16)
        draw_lines(draw, 738, y, lines, font, (225, 214, 214), line_gap=2)


def scene_actions(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 94, 210, 520, 330, accent)
    draw.text((126, 242), "Action inserted by Bashira", font=FONT_PANEL, fill=(244, 238, 238))
    rounded(draw, (126, 306, 574, 370), rgba(accent, 0.08), outline=rgba(accent, 0.76), radius=18, width=2)
    draw.text((146, 328), "Review execution outlier", font=FONT_PANEL, fill=(*accent, 255))
    draw.text((146, 382), "owner: Operations Control", font=FONT_MONO_SMALL, fill=(225, 214, 214))
    draw.text((146, 412), "impact_days: 2", font=FONT_MONO_SMALL, fill=(225, 214, 214))
    panel(draw, 676, 210, 512, 330, accent)
    draw.text((708, 242), "Evidence and badge", font=FONT_PANEL, fill=(244, 238, 238))
    evidence = [
        "Isolation forest anomaly score is 91.2 / 100 versus fleet pattern.",
        "badge: Operational Outlier",
        "record now stands out in monitoring surfaces",
    ]
    for idx, line in enumerate(evidence):
        y = 316 + idx * 56
        font, lines = fit_text_block(draw, line, 432, 2, 19, 16)
        draw_lines(draw, 708, y, lines, font, (225, 214, 214), line_gap=2)


DRAWERS = [
    scene_why,
    scene_rows,
    scene_guardrails,
    scene_forest,
    scene_isolate,
    scene_scores,
    scene_blend,
    scene_actions,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (11, 8, 8))
    draw = ImageDraw.Draw(image, "RGBA")
    draw_background(draw, accent, local_progress)
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

    combined_audio = run_dir / "isolation_forest_anomalies_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "isolation_forest_anomalies_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

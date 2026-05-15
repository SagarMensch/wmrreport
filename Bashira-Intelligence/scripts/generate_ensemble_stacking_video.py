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
OUTPUT_FILE = OUTPUT_DIR / "ensemble-stacking-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 20
SCENE_GAP_SECONDS = 0.24
MIN_SCENE_SECONDS = 10.0

BASE_MODELS = [
    ("lightgbm_risk", 68.0, 0.35, "#2563EB"),
    ("statsforecast_arima", 22.0, 0.20, "#06B6D4"),
    ("stan_bayesian", 41.0, 0.25, "#F97316"),
    ("s_learner_cate", 57.0, 0.20, "#A855F7"),
]
STACKED_RAW = round(sum(risk * weight for _, risk, weight, _ in BASE_MODELS), 2)
CALIBRATED = 51.6
CONFORMAL_LOWER = 38.4
CONFORMAL_UPPER = 64.9
AGREEMENT = 71.3
UPDATED_WEIGHTS = [
    ("lightgbm_risk", 0.39),
    ("statsforecast_arima", 0.17),
    ("stan_bayesian", 0.24),
    ("s_learner_cate", 0.20),
]

SCENES = [
    {
        "title": "Why Bashira Uses Ensemble Stacking",
        "subtitle": "No single model sees the entire problem, so Bashira fuses several predictive views into one governed output.",
        "code": "ensemble_stacker.py:123-147",
        "accent": "#7C3AED",
        "narration": "Ensemble stacking exists because the Bashira problem is too wide for one model family. LightGBM sees structured delay probability. StatsForecast sees time series trajectory. Stan sees causal pressure through posterior drivers. The S learner sees intervention opportunity. The stacker turns those different views into one governed risk output instead of forcing one model to pretend it knows everything.",
    },
    {
        "title": "Each Base Model Enters As A Separate Signal",
        "subtitle": "The stacker accepts calibrated LightGBM risk, AutoARIMA trajectory, Stan posterior pressure, and S-Learner momentum logic.",
        "code": "ensemble_stacker.py:149-218",
        "accent": "#8B5CF6",
        "narration": "The first stack step is collection. Each base model contributes a signal in its own language. LightGBM contributes a direct delay probability. StatsForecast contributes a progress trajectory that Bashira converts into implied risk. Stan contributes a driver based delay pressure signal. S learner contributes momentum based intervention context. The stacker records each contribution separately before mixing anything.",
    },
    {
        "title": "Different Outputs Are Converted Into Comparable Risk Signals",
        "subtitle": "Trajectory, posterior impact, and momentum are normalized into zero-to-one risk so they can sit beside LightGBM probability.",
        "code": "ensemble_stacker.py:176-218",
        "accent": "#A855F7",
        "narration": "The base models do not naturally speak the same numeric language, so Bashira normalizes them. StatsForecast converts low predicted progress into higher implied risk. Stan converts top impact days into a bounded risk value. S learner converts weak factual momentum into higher risk. Only after those translations do all model signals live on the same comparable zero to one scale.",
    },
    {
        "title": "Active Weights Produce The Raw Stacked Risk",
        "subtitle": "The stacker multiplies each active risk estimate by its weight, sums them, and divides by the active total weight only.",
        "code": "ensemble_stacker.py:227-238",
        "accent": "#C084FC",
        "narration": "Now the fusion step happens. Bashira multiplies each active model risk by its assigned weight, then divides by the sum of active weights only. That active only part matters. If a member is missing for a well, the stacker does not leave dead weight in the denominator. It renormalizes around the members that actually fired.",
    },
    {
        "title": "Isotonic Calibration Rechecks The Combined Probability",
        "subtitle": "If historical calibration succeeded, the raw stacked risk is passed through isotonic regression before it is trusted as the final percent.",
        "code": "ensemble_stacker.py:149-175, 240-249",
        "accent": "#D8B4FE",
        "narration": "The weighted average is still not final. If Bashira has enough historical calibration data, the raw stacked risk goes through isotonic regression. This is the ensemble honesty layer. It adjusts the combined probability so the final percent better matches observed outcome frequency instead of staying as a raw fusion score.",
    },
    {
        "title": "Conformal Logic Wraps The Stack With A Defensible Interval",
        "subtitle": "The stacker uses the conformal risk calibrator to return a ninety percent interval around the fused prediction.",
        "code": "ensemble_stacker.py:72-111, 264-273",
        "accent": "#E9D5FF",
        "narration": "Bashira also wraps the fused risk with a conformal interval. The conformal predictor stores residuals from calibration history, estimates a quantile width, and then adds that width around the stacked prediction. That means the output is not only a point estimate. It also carries a statistically defensible band around that point.",
    },
    {
        "title": "Model Agreement Becomes An Explicit Signal",
        "subtitle": "The stacker measures dispersion across model risks and raises a flag when agreement falls below fifty percent.",
        "code": "ensemble_stacker.py:251-285",
        "accent": "#C026D3",
        "narration": "A strong stacker should not hide disagreement. Bashira computes agreement from the spread of member risks using the coefficient of variation. High agreement means the models tell a similar story. Low agreement means they disagree materially. If agreement falls below fifty percent, the stacker raises a high disagreement flag instead of quietly burying that uncertainty.",
    },
    {
        "title": "Weights Can Move As Real Outcomes Arrive",
        "subtitle": "Bashira stores prediction history, compares model estimates against actual delayed outcomes, and updates weights inversely to mean error.",
        "code": "ensemble_stacker.py:288-371",
        "accent": "#6D28D9",
        "narration": "The last institutional piece is weight adaptation. Bashira stores prediction history by well, watches the real outcomes later, computes each model's mean error, and then shifts the weights inversely to that error. Lower error earns more weight. Higher error loses influence. So the stack does not stay frozen forever. It can reallocate trust as reality comes back in.",
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
FONT_NUMBER = load_font(54, bold=True, mono=True)
FONT_BIG = load_font(32, bold=True)
FONT_HUGE = load_font(68, bold=True, mono=True)


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
    rounded(draw, (x + 10, y + 12, x + w + 10, y + h + 12), (20, 10, 34, 115), radius=26)
    rounded(draw, (x, y, x + w, y + h), rgba((16, 10, 28), fill_alpha), outline=rgba(accent, 0.84), radius=26, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    width = draw.textbbox((0, 0), text, font=FONT_TAG)[2] + 28
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.15), outline=rgba(accent, 0.66), radius=999, width=2)
    draw.text((x + 14, y + 7), text, font=FONT_TAG, fill=(*accent, 255))


def draw_background(draw: ImageDraw.ImageDraw, accent):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(12, 8, 24))
    draw.ellipse((WIDTH - 300, -90, WIDTH + 70, 290), fill=rgba(accent, 0.12))
    draw.ellipse((-160, 520, 260, 900), fill=(38, 16, 72, 98))
    for y in range(180, 610, 38):
        draw.line((82, y, WIDTH - 82, y), fill=(38, 28, 64, 46), width=1)
    for x in range(104, WIDTH - 100, 96):
        draw.line((x, 182, x, 606), fill=(38, 28, 64, 30), width=1)


def draw_header(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    scene = SCENES[scene_index]
    draw_chip(draw, 92, 24, f"FUSION LAB 10 / STAGE {scene_index + 1:02d}", accent)
    draw.text((92, 84), scene["title"], font=FONT_TITLE, fill=(243, 241, 248))
    subtitle_font, subtitle_lines = fit_text_block(draw, scene["subtitle"], 1090, 2, 22, 18)
    draw_lines(draw, 92, 132, subtitle_lines, subtitle_font, (222, 218, 236), line_gap=2)
    for i in range(len(SCENES)):
        dot_x = 28 + i * 28
        dot_color = accent if i == scene_index else (70, 55, 92)
        draw.ellipse((dot_x, 152, dot_x + 18, 170), fill=dot_color)
    code_text = scene["code"]
    box_width = max(340, draw.textbbox((0, 0), code_text, font=FONT_MONO_SMALL)[2] + 42)
    panel(draw, WIDTH - box_width - 64, 22, box_width, 56, accent, fill_alpha=0.95)
    draw.text((WIDTH - box_width - 42, 40), code_text, font=FONT_MONO_SMALL, fill=(241, 238, 248))


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    panel(draw, 86, HEIGHT - 84, WIDTH - 172, 46, accent, fill_alpha=0.95)
    label = "ENSEMBLE STACK"
    label_width = draw.textbbox((0, 0), label, font=FONT_TAG)[2]
    footer_font, lines = fit_text_block(draw, text, WIDTH - 300 - label_width, 1, 22, 18)
    draw_lines(draw, 112, HEIGHT - 72, lines, footer_font, (243, 241, 248), line_gap=0)
    draw.text((WIDTH - 118 - label_width, HEIGHT - 69), label, font=FONT_TAG, fill=(*accent, 255))


def draw_value_bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, ratio: float, color):
    rounded(draw, (x, y, x + w, y + h), (44, 28, 62), radius=h // 2)
    fill_w = max(12, int(w * clamp(ratio)))
    rounded(draw, (x, y, x + fill_w, y + h), rgba(color, 0.95), radius=h // 2)


def scene_why(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 216, 442, 300, accent)
    draw.text((126, 246), "Problem", font=FONT_PANEL, fill=(243, 241, 248))
    lines = [
        "different models",
        "see different",
        "parts of risk",
    ]
    draw_lines(draw, 126, 304, lines, FONT_BIG, (243, 241, 248), line_gap=0)
    draw.text((126, 440), "one fused output", font=FONT_MONO, fill=(*accent, 255))

    panel(draw, 650, 226, 500, 280, accent)
    draw.text((680, 258), "Fusion desk", font=FONT_PANEL, fill=(243, 241, 248))
    for idx, (name, _, _, color_hex) in enumerate(BASE_MODELS):
        color = rgb(color_hex)
        x = 690 + (idx % 2) * 210
        y = 318 + (idx // 2) * 88
        rounded(draw, (x, y, x + 180, y + 56), rgba(color, 0.14), outline=rgba(color, 0.82), radius=18, width=2)
        font, lines = fit_text_block(draw, name, 148, 2, 20, 15, mono=True)
        draw_lines(draw, x + 14, y + 10, lines, font, (243, 241, 248), line_gap=2)


def scene_members(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Base model channels", font=FONT_PANEL, fill=(243, 241, 248))
    draw.text((122, 286), "each member contributes its own signal before fusion", font=FONT_MONO_SMALL, fill=(*accent, 255))
    for idx, (name, risk, weight, color_hex) in enumerate(BASE_MODELS):
        x = 126 + idx * 250
        color = rgb(color_hex)
        local = pop(progress, 0.06 + idx * 0.08)
        rounded(draw, (x, 336, x + 210, 472), rgba(color, 0.10 + 0.10 * local), outline=rgba(color, 0.80), radius=22, width=2)
        font, lines = fit_text_block(draw, name, 170, 3, 20, 15, mono=True)
        draw_lines(draw, x + 18, 356, lines, font, (243, 241, 248), line_gap=2)
        draw.text((x + 18, 426), f"risk {risk:.1f}%", font=FONT_MONO, fill=(*color, 255))
        draw.text((x + 18, 452), f"weight {weight:.2f}", font=FONT_MONO_SMALL, fill=(228, 222, 238))


def scene_normalize(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 1088, 324, accent)
    draw.text((126, 246), "Risk translation layer", font=FONT_PANEL, fill=(243, 241, 248))
    rows = [
        ("LightGBM", "direct delay probability", "68.0%"),
        ("StatsForecast", "100 - predicted progress", "22.0%"),
        ("Stan", "top impact days -> normalized risk", "41.0%"),
        ("S-Learner", "low momentum -> higher risk", "57.0%"),
    ]
    for idx, (name, rule, value) in enumerate(rows):
        y = 318 + idx * 54
        rounded(draw, (132, y, 1136, y + 38), rgba(accent, 0.06), outline=rgba(accent, 0.70), radius=18, width=2)
        draw.text((150, y + 10), name, font=FONT_PANEL, fill=(243, 241, 248))
        draw.text((346, y + 12), rule, font=FONT_MONO_SMALL, fill=(228, 222, 238))
        draw.text((1016, y + 10), value, font=FONT_MONO, fill=(*accent, 255))


def scene_weighted(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Weighted average over active models", font=FONT_PANEL, fill=(243, 241, 248))
    for idx, (name, risk, weight, color_hex) in enumerate(BASE_MODELS):
        color = rgb(color_hex)
        y = 316 + idx * 48
        contribution = risk * weight
        draw.text((132, y + 8), name, font=FONT_MONO_SMALL, fill=(243, 241, 248))
        draw.text((386, y + 8), f"{risk:.1f} x {weight:.2f}", font=FONT_MONO_SMALL, fill=(228, 222, 238))
        draw_value_bar(draw, 596, y + 8, 230, 20, contribution / 35.0, color)
        draw.text((854, y + 8), f"{contribution:.2f}", font=FONT_MONO_SMALL, fill=(*color, 255))
    panel(draw, 922, 306, 220, 180, accent)
    draw.text((952, 336), "raw stack", font=FONT_PANEL, fill=(243, 241, 248))
    draw.text((946, 396), f"{STACKED_RAW:04.1f}", font=FONT_HUGE, fill=(*accent, 255))
    draw.text((974, 462), "active weights only", font=FONT_MONO_SMALL, fill=(228, 222, 238))


def scene_isotonic(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 520, 324, accent)
    draw.text((126, 246), "Isotonic recalibration", font=FONT_PANEL, fill=(243, 241, 248))
    draw.line((156, 470, 520, 300), fill=(108, 94, 130), width=3)
    curve = [(160, 466), (230, 430), (300, 410), (390, 360), (520, 316)]
    draw.line(curve, fill=(*accent, 255), width=5)
    for px, py in curve:
        draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=(*accent, 255))
    draw.text((162, 496), "raw stack", font=FONT_SMALL, fill=(228, 222, 238))
    draw.text((506, 286), "calibrated", font=FONT_SMALL, fill=(228, 222, 238))

    panel(draw, 680, 214, 500, 324, accent)
    draw.text((710, 246), "Calibration effect", font=FONT_PANEL, fill=(243, 241, 248))
    draw.text((724, 332), f"raw = {STACKED_RAW:.1f}%", font=FONT_MONO, fill=(228, 222, 238))
    draw.text((724, 386), f"calibrated = {CALIBRATED:.1f}%", font=FONT_NUMBER, fill=(*accent, 255))
    draw.text((724, 454), "final percent becomes more honest", font=FONT_BODY, fill=(228, 222, 238))


def scene_conformal(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Conformal shield around the fused point", font=FONT_PANEL, fill=(243, 241, 248))
    x1, x2, y = 170, 1070, 390
    draw.line((x1, y, x2, y), fill=(92, 76, 122), width=10)
    for value in [0, 25, 50, 75, 100]:
        x = x1 + (x2 - x1) * value / 100.0
        draw.line((x, y - 16, x, y + 16), fill=(214, 205, 232), width=3)
        draw.text((x - 10, y + 24), str(value), font=FONT_SMALL, fill=(228, 222, 238))
    lower_x = x1 + (x2 - x1) * CONFORMAL_LOWER / 100.0
    upper_x = x1 + (x2 - x1) * CONFORMAL_UPPER / 100.0
    point_x = x1 + (x2 - x1) * CALIBRATED / 100.0
    draw.line((lower_x, y, upper_x, y), fill=(*accent, 255), width=18)
    draw.ellipse((point_x - 18, y - 18, point_x + 18, y + 18), fill=(243, 241, 248))
    draw.text((lower_x - 22, y - 54), f"{CONFORMAL_LOWER:.1f}", font=FONT_MONO_SMALL, fill=(243, 241, 248))
    draw.text((upper_x - 18, y - 54), f"{CONFORMAL_UPPER:.1f}", font=FONT_MONO_SMALL, fill=(243, 241, 248))
    draw.text((point_x - 20, y + 42), f"{CALIBRATED:.1f}", font=FONT_MONO_SMALL, fill=(243, 241, 248))


def scene_agreement(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 520, 324, accent)
    draw.text((126, 246), "Model agreement monitor", font=FONT_PANEL, fill=(243, 241, 248))
    for idx, (_, risk, _, color_hex) in enumerate(BASE_MODELS):
        color = rgb(color_hex)
        y = 320 + idx * 42
        draw_value_bar(draw, 146, y, 330, 18, risk / 100.0, color)
        draw.text((492, y - 2), f"{risk:.1f}", font=FONT_MONO_SMALL, fill=(*color, 255))
    draw.text((146, 500), "agreement = 1 - coefficient of variation", font=FONT_MONO_SMALL, fill=(228, 222, 238))

    panel(draw, 680, 214, 500, 324, accent)
    draw.text((710, 246), "Agreement score", font=FONT_PANEL, fill=(243, 241, 248))
    draw.text((730, 340), f"{AGREEMENT:.1f}%", font=FONT_HUGE, fill=(*accent, 255))
    draw.text((730, 416), "above 50 -> no disagreement flag", font=FONT_BODY, fill=(228, 222, 238))
    draw.text((730, 456), "below 50 -> explicit high-disagreement warning", font=FONT_BODY, fill=(228, 222, 238))


def scene_update(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Online weight update from real outcomes", font=FONT_PANEL, fill=(243, 241, 248))
    draw.text((122, 286), "lower mean error -> higher inverse-error weight", font=FONT_MONO_SMALL, fill=(*accent, 255))
    for idx, ((name, old_risk, old_weight, color_hex), (_, new_weight)) in enumerate(zip(BASE_MODELS, UPDATED_WEIGHTS)):
        color = rgb(color_hex)
        y = 332 + idx * 48
        rounded(draw, (132, y, 1138, y + 36), rgba(accent, 0.06), outline=rgba(accent, 0.68), radius=18, width=2)
        draw.text((150, y + 10), name, font=FONT_MONO_SMALL, fill=(243, 241, 248))
        draw.text((480, y + 10), f"old {old_weight:.2f}", font=FONT_MONO_SMALL, fill=(228, 222, 238))
        draw.text((640, y + 10), "->", font=FONT_MONO_SMALL, fill=(*accent, 255))
        draw.text((698, y + 10), f"new {new_weight:.2f}", font=FONT_MONO_SMALL, fill=(*color, 255))
    draw.text((420, 530), "stored prediction history lets the stack reallocate trust over time", font=FONT_BODY, fill=(228, 222, 238))


DRAWERS = [
    scene_why,
    scene_members,
    scene_normalize,
    scene_weighted,
    scene_isotonic,
    scene_conformal,
    scene_agreement,
    scene_update,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (12, 8, 24))
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

    combined_audio = run_dir / "ensemble_stacking_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "ensemble_stacking_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

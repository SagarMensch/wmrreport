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
OUTPUT_FILE = OUTPUT_DIR / "conformal-intervals-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 20
SCENE_GAP_SECONDS = 0.24
MIN_SCENE_SECONDS = 10.0

RESIDUALS = [1.2, 2.1, 1.8, 2.7, 3.4, 2.0, 1.6, 2.9, 3.1, 2.4, 1.9, 2.6]
Q_HAT = 3.1
POINT_PRED = 51.6
LOWER = 48.5
UPPER = 54.7

SCENES = [
    {
        "title": "Why Bashira Wraps Predictions With Conformal Intervals",
        "subtitle": "A point estimate alone looks precise, but the stack also needs a defensible uncertainty band around it.",
        "code": "ensemble_stacker.py:38-50",
        "accent": "#9333EA",
        "narration": "Conformal prediction exists because a single number can look more certain than it really is. Bashira already has a fused point prediction, but planners also need an uncertainty band around that number. The conformal wrapper provides that band without assuming a fancy probability distribution underneath.",
    },
    {
        "title": "Calibration Residuals Are Stored First",
        "subtitle": "The conformal predictor keeps absolute residuals from held-out calibration data and only turns on when at least five are available.",
        "code": "ensemble_stacker.py:52-60",
        "accent": "#A855F7",
        "narration": "The first step is calibration. Bashira stores absolute residuals, which means the size of the miss between what the model predicted and what really happened. If there are fewer than five such residuals, the conformal predictor does not claim to be fitted yet. That guardrail matters because intervals built on too little evidence would be misleading.",
    },
    {
        "title": "The Last Slice Of History Is Reserved For Interval Calibration",
        "subtitle": "The ensemble calibrator uses the last thirty percent of available history to fit conformal width after the earlier portion handled prediction.",
        "code": "ensemble_stacker.py:149-175",
        "accent": "#C084FC",
        "narration": "Inside the ensemble stack, conformal calibration does not use the whole history in one lump. Bashira reserves the later thirty percent of the available sequence for interval calibration. The earlier part can support the main prediction path, while the reserved residual slice teaches the interval wrapper how wide uncertainty should be.",
    },
    {
        "title": "Coverage Chooses The Quantile Width",
        "subtitle": "For a requested coverage like ninety percent, Bashira computes the conformal quantile level and reads q-hat from the stored residuals.",
        "code": "ensemble_stacker.py:80-92",
        "accent": "#D8B4FE",
        "narration": "Now Bashira converts desired coverage into an empirical width. For ninety percent coverage, the code computes a conformal quantile level from the residual count, then reads q hat from that residual distribution. Q hat is the learned safety margin. It is not guessed and it is not hand tuned. It comes directly from past miss sizes.",
    },
    {
        "title": "The Interval Is Built Around The Point Prediction",
        "subtitle": "Once q-hat is known, the wrapper subtracts it from the point forecast for the lower bound and adds it for the upper bound.",
        "code": "ensemble_stacker.py:93-111",
        "accent": "#E9D5FF",
        "narration": "After q hat is available, the interval construction is simple. Bashira takes the point prediction, subtracts q hat to get the lower bound, and adds q hat to get the upper bound. This creates a prediction band centered on the point estimate, but its width comes from real historical error rather than wishful confidence.",
    },
    {
        "title": "The Wrapper Falls Back Gracefully When Uncalibrated",
        "subtitle": "If too little residual history exists, Bashira returns a heuristic band instead of pretending split conformal is already fitted.",
        "code": "ensemble_stacker.py:67-78",
        "accent": "#C026D3",
        "narration": "Bashira also has a fallback path. If the conformal predictor is not fitted, it does not fake a calibrated interval. Instead it returns a heuristic margin around the point estimate and marks the method as heuristic fallback. That honesty is important. The system tells you when you are looking at a provisional band instead of a real conformal one.",
    },
    {
        "title": "The Interval Carries Method Metadata Too",
        "subtitle": "The response includes coverage, calibrated flag, method name, calibration count, and quantile width alongside the numeric bounds.",
        "code": "ensemble_stacker.py:93-111, 264-273",
        "accent": "#7E22CE",
        "narration": "The output is more than just lower and upper numbers. Bashira also returns the requested coverage level, whether the interval is calibrated, the method name, the number of calibration residuals, and the quantile width. That metadata matters because it tells the client how much evidence stands behind the interval.",
    },
    {
        "title": "Why This Band Is More Useful Than A Naked Score",
        "subtitle": "Conformal intervals make the ensemble output safer to act on because they show the range of plausible outcomes, not just the center point.",
        "code": "ensemble_stacker.py:10-16, 264-285",
        "accent": "#6D28D9",
        "narration": "This is why the conformal layer matters. A naked score can encourage overconfidence. The interval shows the plausible range around that score, which is much more honest for operational planning. Bashira still gives the point estimate, but the conformal band tells decision makers how much room there is around that center line.",
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
FONT_HUGE = load_font(70, bold=True, mono=True)


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
    rounded(draw, (x + 10, y + 12, x + w + 10, y + h + 12), (26, 10, 34, 118), radius=26)
    rounded(draw, (x, y, x + w, y + h), rgba((20, 8, 30), fill_alpha), outline=rgba(accent, 0.84), radius=26, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    width = draw.textbbox((0, 0), text, font=FONT_TAG)[2] + 28
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.15), outline=rgba(accent, 0.66), radius=999, width=2)
    draw.text((x + 14, y + 7), text, font=FONT_TAG, fill=(*accent, 255))


def draw_background(draw: ImageDraw.ImageDraw, accent):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(18, 8, 24))
    draw.ellipse((WIDTH - 300, -90, WIDTH + 70, 290), fill=rgba(accent, 0.12))
    draw.ellipse((-160, 520, 260, 920), fill=(58, 12, 82, 96))
    for y in range(180, 610, 38):
        draw.line((82, y, WIDTH - 82, y), fill=(54, 28, 64, 44), width=1)
    for x in range(104, WIDTH - 100, 96):
        draw.line((x, 182, x, 606), fill=(54, 28, 64, 28), width=1)


def draw_header(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    scene = SCENES[scene_index]
    draw_chip(draw, 92, 24, f"UNCERTAINTY 11 / STAGE {scene_index + 1:02d}", accent)
    draw.text((92, 84), scene["title"], font=FONT_TITLE, fill=(246, 241, 248))
    subtitle_font, subtitle_lines = fit_text_block(draw, scene["subtitle"], 1090, 2, 22, 18)
    draw_lines(draw, 92, 132, subtitle_lines, subtitle_font, (230, 220, 236), line_gap=2)
    for i in range(len(SCENES)):
        dot_x = 28 + i * 28
        dot_color = accent if i == scene_index else (82, 62, 92)
        draw.ellipse((dot_x, 152, dot_x + 18, 170), fill=dot_color)
    code_text = scene["code"]
    box_width = max(300, draw.textbbox((0, 0), code_text, font=FONT_MONO_SMALL)[2] + 42)
    panel(draw, WIDTH - box_width - 64, 22, box_width, 56, accent, fill_alpha=0.95)
    draw.text((WIDTH - box_width - 42, 40), code_text, font=FONT_MONO_SMALL, fill=(244, 239, 248))


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    panel(draw, 86, HEIGHT - 84, WIDTH - 172, 46, accent, fill_alpha=0.95)
    label = "CONFORMAL"
    label_width = draw.textbbox((0, 0), label, font=FONT_TAG)[2]
    footer_font, lines = fit_text_block(draw, text, WIDTH - 280 - label_width, 1, 22, 18)
    draw_lines(draw, 112, HEIGHT - 72, lines, footer_font, (246, 241, 248), line_gap=0)
    draw.text((WIDTH - 118 - label_width, HEIGHT - 69), label, font=FONT_TAG, fill=(*accent, 255))


def draw_value_bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, ratio: float, color):
    rounded(draw, (x, y, x + w, y + h), (58, 34, 68), radius=h // 2)
    fill_w = max(12, int(w * clamp(ratio)))
    rounded(draw, (x, y, x + fill_w, y + h), rgba(color, 0.95), radius=h // 2)


def scene_why(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 216, 430, 300, accent)
    draw.text((126, 246), "Point score", font=FONT_PANEL, fill=(246, 241, 248))
    draw.text((136, 330), f"{POINT_PRED:.1f}%", font=FONT_HUGE, fill=(*accent, 255))
    draw.text((136, 424), "looks exact", font=FONT_BODY, fill=(230, 220, 236))
    panel(draw, 646, 226, 500, 280, accent)
    draw.text((676, 258), "Conformal band", font=FONT_PANEL, fill=(246, 241, 248))
    draw.line((714, 386, 1074, 386), fill=(100, 78, 118), width=12)
    draw.line((834, 386, 986, 386), fill=(*accent, 255), width=18)
    draw.ellipse((886, 366, 922, 402), fill=(246, 241, 248))
    draw.text((810, 442), "plausible range around the center point", font=FONT_BODY, fill=(230, 220, 236))


def scene_residuals(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Residual vault", font=FONT_PANEL, fill=(246, 241, 248))
    draw.text((122, 286), "calibrate() stores absolute residuals and only fits when count >= 5", font=FONT_MONO_SMALL, fill=(*accent, 255))
    for idx, residual in enumerate(RESIDUALS):
        x = 132 + (idx % 6) * 168
        y = 336 + (idx // 6) * 90
        local = pop(progress, 0.05 + idx * 0.05)
        rounded(draw, (x, y, x + 132, y + 54), rgba(accent, 0.08 + 0.08 * local), outline=rgba(accent, 0.74), radius=18, width=2)
        draw.text((x + 24, y + 12), f"|e| = {residual:.1f}", font=FONT_MONO, fill=(246, 241, 248))


def scene_split(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 1088, 324, accent)
    draw.text((126, 246), "Reserved calibration slice", font=FONT_PANEL, fill=(246, 241, 248))
    draw.text((126, 286), "ensemble calibrator uses the last 30% of history for conformal residuals", font=FONT_MONO_SMALL, fill=(*accent, 255))
    rounded(draw, (150, 354, 1090, 414), (58, 34, 68), radius=28)
    split_x = 150 + int(940 * 0.70)
    rounded(draw, (150, 354, split_x, 414), rgba(accent, 0.88), radius=28)
    draw.text((330, 366), "prediction side 70%", font=FONT_PANEL, fill=(246, 241, 248))
    draw.text((836, 366), "conformal side 30%", font=FONT_MONO_SMALL, fill=(246, 241, 248))
    draw.text((382, 464), "keep a later slice for interval width", font=FONT_BODY, fill=(230, 220, 236))


def scene_quantile(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 520, 324, accent)
    draw.text((126, 246), "Coverage -> q-hat", font=FONT_PANEL, fill=(246, 241, 248))
    draw.text((126, 298), "coverage = 0.90", font=FONT_MONO, fill=(*accent, 255))
    draw.text((126, 338), "q_level = ceil((n+1)*coverage)/n", font=FONT_MONO_SMALL, fill=(230, 220, 236))
    draw.text((126, 388), f"n = {len(RESIDUALS)}", font=FONT_MONO_SMALL, fill=(230, 220, 236))
    draw.text((126, 432), f"q_hat = {Q_HAT:.1f}", font=FONT_NUMBER, fill=(246, 241, 248))
    panel(draw, 680, 214, 500, 324, accent)
    draw.text((710, 246), "Residual gauge", font=FONT_PANEL, fill=(246, 241, 248))
    for idx, residual in enumerate(sorted(RESIDUALS)):
        y = 308 + idx * 24
        draw_value_bar(draw, 734, y, 310, 14, residual / 4.0, accent)
        draw.text((1060, y - 2), f"{residual:.1f}", font=FONT_MONO_SMALL, fill=(246, 241, 248))


def scene_build(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Interval built around the point", font=FONT_PANEL, fill=(246, 241, 248))
    x1, x2, y = 170, 1080, 388
    draw.line((x1, y, x2, y), fill=(102, 80, 118), width=10)
    for value in [40, 45, 50, 55, 60]:
        x = x1 + (x2 - x1) * ((value - 40) / 20.0)
        draw.line((x, y - 16, x, y + 16), fill=(224, 214, 236), width=3)
        draw.text((x - 10, y + 24), str(value), font=FONT_SMALL, fill=(230, 220, 236))
    lower_x = x1 + (x2 - x1) * ((LOWER - 40) / 20.0)
    upper_x = x1 + (x2 - x1) * ((UPPER - 40) / 20.0)
    point_x = x1 + (x2 - x1) * ((POINT_PRED - 40) / 20.0)
    draw.line((lower_x, y, upper_x, y), fill=(*accent, 255), width=18)
    draw.ellipse((point_x - 18, y - 18, point_x + 18, y + 18), fill=(246, 241, 248))
    draw.text((lower_x - 18, y - 54), f"{LOWER:.1f}", font=FONT_MONO_SMALL, fill=(246, 241, 248))
    draw.text((upper_x - 18, y - 54), f"{UPPER:.1f}", font=FONT_MONO_SMALL, fill=(246, 241, 248))
    draw.text((point_x - 22, y + 42), f"{POINT_PRED:.1f}", font=FONT_MONO_SMALL, fill=(246, 241, 248))


def scene_fallback(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 520, 324, accent)
    draw.text((126, 246), "Uncalibrated fallback", font=FONT_PANEL, fill=(246, 241, 248))
    draw.text((126, 294), "if residual count < 5", font=FONT_MONO, fill=(*accent, 255))
    draw.text((126, 336), "margin = max(|pred| * 0.15, 2.0)", font=FONT_MONO_SMALL, fill=(230, 220, 236))
    draw.text((126, 398), "method = heuristic_fallback", font=FONT_MONO_SMALL, fill=(230, 220, 236))
    panel(draw, 680, 214, 500, 324, accent)
    draw.text((710, 246), "Why this matters", font=FONT_PANEL, fill=(246, 241, 248))
    bullets = [
        "no fake conformal claim before enough evidence exists",
        "still returns a usable guardrail band",
        "client can see calibrated = false in metadata",
    ]
    for idx, bullet in enumerate(bullets):
        y = 322 + idx * 66
        draw.ellipse((714, y + 7, 730, y + 23), fill=(*accent, 255))
        font, lines = fit_text_block(draw, bullet, 396, 2, 19, 16)
        draw_lines(draw, 746, y, lines, font, (230, 220, 236), line_gap=4)


def scene_metadata(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Returned interval metadata", font=FONT_PANEL, fill=(246, 241, 248))
    rows = [
        ("lower", f"{LOWER:.1f}"),
        ("upper", f"{UPPER:.1f}"),
        ("coverage", "0.90"),
        ("calibrated", "true"),
        ("method", "split_conformal"),
        ("n_calibration", str(len(RESIDUALS))),
        ("quantile_width", f"{Q_HAT:.1f}"),
    ]
    for idx, (key, value) in enumerate(rows):
        x = 136 + (idx % 2) * 454
        y = 320 + (idx // 2) * 56
        rounded(draw, (x, y, x + 400, y + 38), rgba(accent, 0.08), outline=rgba(accent, 0.72), radius=18, width=2)
        draw.text((x + 18, y + 10), key, font=FONT_MONO_SMALL, fill=(230, 220, 236))
        draw.text((x + 240, y + 10), value, font=FONT_MONO_SMALL, fill=(*accent, 255))


def scene_why_band(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 1088, 324, accent)
    draw.text((126, 246), "Why the band matters", font=FONT_PANEL, fill=(246, 241, 248))
    panel(draw, 132, 314, 316, 170, accent)
    draw.text((162, 344), "point only", font=FONT_PANEL, fill=(246, 241, 248))
    draw.text((176, 404), f"{POINT_PRED:.1f}%", font=FONT_HUGE, fill=(*accent, 255))
    panel(draw, 488, 314, 580, 170, accent)
    draw.text((518, 344), "point + interval", font=FONT_PANEL, fill=(246, 241, 248))
    draw.text((546, 404), f"{LOWER:.1f}%  -  {UPPER:.1f}%", font=FONT_NUMBER, fill=(*accent, 255))
    draw.text((522, 454), "shows the plausible range around the center estimate", font=FONT_BODY, fill=(230, 220, 236))


DRAWERS = [
    scene_why,
    scene_residuals,
    scene_split,
    scene_quantile,
    scene_build,
    scene_fallback,
    scene_metadata,
    scene_why_band,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (18, 8, 24))
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

    combined_audio = run_dir / "conformal_intervals_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "conformal_intervals_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

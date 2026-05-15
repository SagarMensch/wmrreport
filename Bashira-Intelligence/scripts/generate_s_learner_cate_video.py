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
OUTPUT_FILE = OUTPUT_DIR / "s-learner-cate-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 20
SCENE_GAP_SECONDS = 0.24
MIN_SCENE_SECONDS = 10.0

FACTUAL = {
    "well_id": "PDO-417",
    "progress": 0.46,
    "cluster_density": 0.62,
    "material_lead_days": 18,
    "current_rig": "RIG-04",
    "location": "WEST_PAD",
    "factual_momentum_pct": 1.84,
}

RIG_EFFECTS = [
    ("RIG-07", 2.31, 0.47, False),
    ("RIG-12", 2.12, 0.28, False),
    ("RIG-04", 1.84, 0.00, True),
    ("RIG-02", 1.63, -0.21, False),
]

SCENES = [
    {
        "title": "Why Bashira Uses S-Learner CATE",
        "subtitle": "This topic shifts from prediction into intervention effect: what changes if the well were assigned a different rig.",
        "code": "cpu_ml_orchestrator.py:389-435, 1068-1075",
        "accent": "#0F766E",
        "narration": "The S learner topic is different from the earlier risk videos. Those videos asked what is likely to happen. This one asks what would change if Bashira took a different action. In this implementation, the action is rig assignment. So the model estimates intervention effect, not just passive prediction.",
    },
    {
        "title": "The Training Panel Starts As A Weekly Causal Table",
        "subtitle": "Bashira sorts the well history by well and week, then creates a next-week momentum target from the progress change.",
        "code": "cpu_ml_orchestrator.py:393-401",
        "accent": "#0D9488",
        "narration": "Training begins with a temporal panel. Bashira sorts rows by well and week, then creates a next progress column. The target for the S learner is causal momentum, which is the next week's progress minus the current week's progress. That means the model learns how much weekly forward movement is expected under different contexts.",
    },
    {
        "title": "Only Plausible Causal Rows Are Kept",
        "subtitle": "Rows without a next week are dropped, and extreme anomalies are filtered so the treatment-effect model learns from realistic momentum behavior.",
        "code": "cpu_ml_orchestrator.py:402-405",
        "accent": "#14B8A6",
        "narration": "Not every row is usable. Bashira drops rows that do not have a next week to compare against, and it removes extreme momentum anomalies. That keeps the causal panel focused on realistic operational movement instead of teaching the S learner from broken or explosive records.",
    },
    {
        "title": "Treatment And Confounders Enter One Model Together",
        "subtitle": "The S-Learner uses progress, density, material lead time, rig code, and location code inside one LightGBM regressor.",
        "code": "cpu_ml_orchestrator.py:407-435",
        "accent": "#115E59",
        "narration": "The defining idea of an S learner is that the treatment and the background context enter the same supervised model. Bashira encodes rig and location with label encoders, then combines them with progress, cluster density, and material lead days. A LightGBM regressor learns weekly momentum directly from that combined feature frame.",
    },
    {
        "title": "The Factual World Is Scored First",
        "subtitle": "For one live well, Bashira builds the factual feature row using the current rig and predicts the expected weekly momentum under today's assignment.",
        "code": "cpu_ml_orchestrator.py:1080-1104",
        "accent": "#0F766E",
        "narration": "When Bashira computes CATE for one well, it first scores the factual world. That means it builds a feature row with the current progress, density, material situation, encoded current rig, and encoded location. The model predicts the expected weekly momentum for the well under the rig it is using right now.",
    },
    {
        "title": "Counterfactual Rigs Are Substituted One By One",
        "subtitle": "Bashira loops through all known rigs, swaps only the rig code, and recomputes the momentum for each alternative world.",
        "code": "cpu_ml_orchestrator.py:1106-1118",
        "accent": "#0F766E",
        "narration": "Now the counterfactual part begins. Bashira does not change everything at once. It holds the well context fixed and swaps only the rig code. Then it runs the same S learner again for each possible rig. Each rerun answers a separate question: what weekly momentum would this same well get if that rig were assigned instead.",
    },
    {
        "title": "CATE Is The Difference Between Counterfactual And Factual",
        "subtitle": "For each candidate rig, Bashira subtracts the factual momentum from the counterfactual momentum to get context-specific treatment lift.",
        "code": "cpu_ml_orchestrator.py:1114-1123",
        "accent": "#0D9488",
        "narration": "The actual CATE number is simple once the two predictions exist. Bashira subtracts the factual momentum from the counterfactual momentum. A positive CATE means the alternative rig is predicted to improve progress. A negative CATE means it would make the well slower. This is why it is called conditional average treatment effect. The effect is specific to this well's context.",
    },
    {
        "title": "The Best Alternative Becomes An Action Ranking",
        "subtitle": "Rig effects are sorted by CATE, the current rig is marked explicitly, and the top non-current rig becomes the recommendation.",
        "code": "cpu_ml_orchestrator.py:1124-1141",
        "accent": "#0F766E",
        "narration": "After all rig effects are computed, Bashira sorts them by CATE from best to worst. The current rig is clearly marked, and the best non current rig becomes the preferred alternative. This is where the causal layer becomes operational. The output is not just a probability anymore. It is a ranked intervention opportunity.",
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
    rounded(draw, (x + 10, y + 12, x + w + 10, y + h + 12), (8, 22, 18, 112), radius=26)
    rounded(draw, (x, y, x + w, y + h), rgba((8, 22, 18), fill_alpha), outline=rgba(accent, 0.84), radius=26, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    width = draw.textbbox((0, 0), text, font=FONT_TAG)[2] + 28
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.15), outline=rgba(accent, 0.66), radius=999, width=2)
    draw.text((x + 14, y + 7), text, font=FONT_TAG, fill=(*accent, 255))


def draw_background(draw: ImageDraw.ImageDraw, accent):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(6, 18, 18))
    draw.ellipse((WIDTH - 300, -90, WIDTH + 70, 290), fill=rgba(accent, 0.12))
    draw.ellipse((-160, 520, 260, 900), fill=(10, 78, 62, 96))
    for y in range(180, 610, 38):
        draw.line((82, y, WIDTH - 82, y), fill=(20, 54, 48, 44), width=1)
    for x in range(104, WIDTH - 100, 96):
        draw.line((x, 182, x, 606), fill=(20, 54, 48, 28), width=1)


def draw_header(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    scene = SCENES[scene_index]
    draw_chip(draw, 92, 24, f"CAUSAL LAB 12 / STAGE {scene_index + 1:02d}", accent)
    draw.text((92, 84), scene["title"], font=FONT_TITLE, fill=(240, 246, 244))
    subtitle_font, subtitle_lines = fit_text_block(draw, scene["subtitle"], 1090, 2, 22, 18)
    draw_lines(draw, 92, 132, subtitle_lines, subtitle_font, (219, 232, 228), line_gap=2)
    for i in range(len(SCENES)):
        dot_x = 28 + i * 28
        dot_color = accent if i == scene_index else (54, 86, 80)
        draw.ellipse((dot_x, 152, dot_x + 18, 170), fill=dot_color)
    code_text = scene["code"]
    box_width = max(320, draw.textbbox((0, 0), code_text, font=FONT_MONO_SMALL)[2] + 42)
    panel(draw, WIDTH - box_width - 64, 22, box_width, 56, accent, fill_alpha=0.95)
    draw.text((WIDTH - box_width - 42, 40), code_text, font=FONT_MONO_SMALL, fill=(240, 246, 244))


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    panel(draw, 86, HEIGHT - 84, WIDTH - 172, 46, accent, fill_alpha=0.95)
    label = "S-LEARNER CATE"
    label_width = draw.textbbox((0, 0), label, font=FONT_TAG)[2]
    footer_font, lines = fit_text_block(draw, text, WIDTH - 300 - label_width, 1, 22, 18)
    draw_lines(draw, 112, HEIGHT - 72, lines, footer_font, (240, 246, 244), line_gap=0)
    draw.text((WIDTH - 118 - label_width, HEIGHT - 69), label, font=FONT_TAG, fill=(*accent, 255))


def draw_value_bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, ratio: float, color):
    rounded(draw, (x, y, x + w, y + h), (24, 58, 50), radius=h // 2)
    fill_w = max(12, int(w * clamp(ratio)))
    rounded(draw, (x, y, x + fill_w, y + h), rgba(color, 0.95), radius=h // 2)


def scene_why(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 216, 430, 300, accent)
    draw.text((126, 246), "Shift in question", font=FONT_PANEL, fill=(240, 246, 244))
    lines = [
        "not just",
        "what will happen,",
        "but what changes",
        "under action",
    ]
    draw_lines(draw, 126, 296, lines, FONT_BIG, (240, 246, 244), line_gap=2)
    panel(draw, 646, 226, 500, 280, accent)
    draw.text((676, 258), "Treatment lens", font=FONT_PANEL, fill=(240, 246, 244))
    draw.text((694, 342), "current rig", font=FONT_MONO_SMALL, fill=(219, 232, 228))
    draw.text((920, 342), "alternative rig", font=FONT_MONO_SMALL, fill=(219, 232, 228))
    draw.text((698, 394), "1.84%", font=FONT_HUGE, fill=(*accent, 255))
    draw.text((920, 394), "2.31%", font=FONT_HUGE, fill=(240, 246, 244))


def scene_panel(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Weekly causal panel", font=FONT_PANEL, fill=(240, 246, 244))
    draw.text((122, 286), "next_progress - current_progress = causal_momentum", font=FONT_MONO, fill=(*accent, 255))
    weeks = ["w1", "w2", "w3", "w4", "w5"]
    progress_vals = [24, 29, 35, 41, 48]
    next_vals = [29, 35, 41, 48, 54]
    for idx, wk in enumerate(weeks):
        x = 136 + idx * 198
        rounded(draw, (x, 336, x + 156, 464), rgba(accent, 0.08), outline=rgba(accent, 0.72), radius=20, width=2)
        draw.text((x + 18, 356), wk, font=FONT_MONO_SMALL, fill=(240, 246, 244))
        draw.text((x + 18, 392), f"p={progress_vals[idx]}", font=FONT_MONO_SMALL, fill=(219, 232, 228))
        draw.text((x + 18, 424), f"next={next_vals[idx]}", font=FONT_MONO_SMALL, fill=(219, 232, 228))
        draw.text((x + 88, 392), f"y={next_vals[idx]-progress_vals[idx]}", font=FONT_MONO_SMALL, fill=(*accent, 255))


def scene_filter(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 520, 324, accent)
    draw.text((126, 246), "Keep valid causal rows", font=FONT_PANEL, fill=(240, 246, 244))
    rules = [
        "drop rows without next_progress",
        "remove momentum < 0",
        "remove momentum >= 0.6",
    ]
    for idx, rule in enumerate(rules):
        y = 324 + idx * 64
        draw.ellipse((130, y + 7, 146, y + 23), fill=(*accent, 255))
        font, lines = fit_text_block(draw, rule, 360, 2, 20, 17)
        draw_lines(draw, 160, y, lines, font, (219, 232, 228), line_gap=4)
    panel(draw, 680, 214, 500, 324, accent)
    draw.text((710, 246), "Reason", font=FONT_PANEL, fill=(240, 246, 244))
    note = "the intervention model should learn from realistic weekly movement, not missing rows or impossible jumps."
    font, lines = fit_text_block(draw, note, 420, 5, 21, 17)
    draw_lines(draw, 712, 324, lines, font, (219, 232, 228), line_gap=4)


def scene_features(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "One model reads treatment plus context", font=FONT_PANEL, fill=(240, 246, 244))
    feats = [
        "over_all_progress_percentages",
        "cluster_density",
        "material_lead_days",
        "rig_encoded",
        "loc_encoded",
    ]
    for idx, feat in enumerate(feats):
        x = 132 + idx * 210
        rounded(draw, (x, 342, x + 180, 454), rgba(accent, 0.08), outline=rgba(accent, 0.72), radius=22, width=2)
        font, lines = fit_text_block(draw, feat, 150, 3, 18, 14, mono=True)
        draw_lines(draw, x + 14, 370, lines, font, (240, 246, 244), line_gap=2)
    draw.text((402, 500), "treatment and confounders live inside one LightGBM regressor", font=FONT_BODY, fill=(219, 232, 228))


def scene_factual(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 520, 324, accent)
    draw.text((126, 246), "Factual row", font=FONT_PANEL, fill=(240, 246, 244))
    factual_rows = [
        ("progress", f"{FACTUAL['progress']:.2f}"),
        ("cluster_density", f"{FACTUAL['cluster_density']:.2f}"),
        ("material_lead_days", str(FACTUAL["material_lead_days"])),
        ("rig_encoded", "current rig code"),
        ("loc_encoded", "current location code"),
    ]
    for idx, (k, v) in enumerate(factual_rows):
        y = 316 + idx * 38
        rounded(draw, (126, y, 564, y + 28), rgba(accent, 0.06), outline=rgba(accent, 0.70), radius=14, width=1)
        draw.text((142, y + 6), k, font=FONT_MONO_SMALL, fill=(219, 232, 228))
        draw.text((374, y + 6), v, font=FONT_MONO_SMALL, fill=(*accent, 255))
    panel(draw, 680, 214, 500, 324, accent)
    draw.text((710, 246), "Factual prediction", font=FONT_PANEL, fill=(240, 246, 244))
    draw.text((744, 366), f"{FACTUAL['factual_momentum_pct']:.2f}%", font=FONT_HUGE, fill=(*accent, 255))
    draw.text((744, 446), "expected weekly momentum with current rig", font=FONT_BODY, fill=(219, 232, 228))


def scene_counterfactual(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Counterfactual rig substitution", font=FONT_PANEL, fill=(240, 246, 244))
    draw.text((122, 286), "hold the well context fixed, swap only rig_encoded, rerun the same S-Learner", font=FONT_MONO_SMALL, fill=(*accent, 255))
    for idx, (rig, cf, cate, is_current) in enumerate(RIG_EFFECTS):
        x = 132 + idx * 242
        color = rgb("#0F766E") if is_current else rgb("#14B8A6")
        rounded(draw, (x, 338, x + 200, 474), rgba(color, 0.08), outline=rgba(color, 0.78), radius=22, width=2)
        draw.text((x + 18, 360), rig, font=FONT_PANEL, fill=(240, 246, 244))
        draw.text((x + 18, 408), f"cf={cf:.2f}%", font=FONT_MONO, fill=(219, 232, 228))
        draw.text((x + 18, 440), f"cate={cate:+.2f}%", font=FONT_MONO, fill=(*color, 255))
        if is_current:
            draw.text((x + 108, 360), "current", font=FONT_MONO_SMALL, fill=(*accent, 255))


def scene_cate(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 1088, 324, accent)
    draw.text((126, 246), "CATE = counterfactual - factual", font=FONT_PANEL, fill=(240, 246, 244))
    draw.text((126, 308), "2.31% - 1.84% = +0.47%", font=FONT_HUGE, fill=(*accent, 255))
    draw.text((126, 402), "positive CATE means this well improves under that rig assignment", font=FONT_BODY, fill=(219, 232, 228))
    draw.text((126, 446), "negative CATE means the alternative rig would make it slower", font=FONT_BODY, fill=(219, 232, 228))


def scene_rank(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Ranked intervention board", font=FONT_PANEL, fill=(240, 246, 244))
    headers = ["Rig", "Counterfactual Momentum", "CATE", "Status"]
    xs = [144, 392, 760, 964]
    for x, header in zip(xs, headers):
        draw.text((x, 300), header, font=FONT_MONO_SMALL, fill=(170, 194, 188))
    for idx, (rig, cf, cate, is_current) in enumerate(RIG_EFFECTS):
        y = 336 + idx * 48
        rounded(draw, (132, y, 1138, y + 34), rgba(accent, 0.06), outline=rgba(accent, 0.70), radius=18, width=2)
        draw.text((150, y + 9), rig, font=FONT_MONO_SMALL, fill=(240, 246, 244))
        draw.text((392, y + 9), f"{cf:.2f}%", font=FONT_MONO_SMALL, fill=(240, 246, 244))
        draw.text((760, y + 9), f"{cate:+.2f}%", font=FONT_MONO_SMALL, fill=(*accent, 255))
        draw.text((964, y + 9), "current" if is_current else ("best alt" if idx == 0 else "alternative"), font=FONT_MONO_SMALL, fill=(219, 232, 228))
    draw.text((410, 530), "top non-current rig becomes the recommended intervention", font=FONT_BODY, fill=(219, 232, 228))


DRAWERS = [
    scene_why,
    scene_panel,
    scene_filter,
    scene_features,
    scene_factual,
    scene_counterfactual,
    scene_cate,
    scene_rank,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (6, 18, 18))
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

    combined_audio = run_dir / "s_learner_cate_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "s_learner_cate_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

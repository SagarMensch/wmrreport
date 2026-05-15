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
OUTPUT_FILE = OUTPUT_DIR / "statsforecast-trajectory-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 20
SCENE_GAP_SECONDS = 0.24
MIN_SCENE_SECONDS = 10.0

HISTORY = [18, 24, 31, 37, 44, 52, 59, 66]
FORECAST = [72, 78, 84, 89]
LOWER = [68, 72, 76, 80]
UPPER = [76, 84, 92, 97]
WEEKS = ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"]
FUTURE_WEEKS = ["+1", "+2", "+3", "+4"]

SCENES = [
    {
        "title": "Why Bashira Adds A Time-Series Forecast",
        "subtitle": "Some questions are about where a well is going next, not just what its current snapshot looks like.",
        "code": "cpu_ml_orchestrator.py:1191-1219",
        "accent": "#06B6D4",
        "narration": "The tabular models tell Bashira what a well looks like right now. But the StatsForecast path answers a different question. Where is the progress curve likely to go next? That is why Bashira adds a genuine time series member instead of relying only on snapshot features.",
    },
    {
        "title": "Well History Is Fetched And Ordered",
        "subtitle": "The forecast starts only when Bashira finds at least two historical progress points for the requested well and sorts them by week number.",
        "code": "cpu_ml_orchestrator.py:1221-1227",
        "accent": "#0891B2",
        "narration": "The first requirement is history. Bashira finds all rows for the requested well, removes blanks, and sorts the sequence by week number. If there are not at least two usable points, no time series forecast is attempted. This topic starts with ordered history, not with a one row feature frame.",
    },
    {
        "title": "History Is Repacked For StatsForecast",
        "subtitle": "The sequence is converted into unique_id, ds, and y, where y is progress multiplied by one hundred.",
        "code": "cpu_ml_orchestrator.py:1229-1237",
        "accent": "#0EA5E9",
        "narration": "StatsForecast expects a standard layout. So Bashira repacks the well history into three columns. Unique id marks which well the series belongs to. D s holds the ordered week index. Y holds the progress values, scaled into percentage points. That repacked frame is the time series object the forecaster actually reads.",
    },
    {
        "title": "AutoARIMA Is Configured For Weekly Structure",
        "subtitle": "Bashira uses StatsForecast with AutoARIMA, season length four, and weekly frequency.",
        "code": "cpu_ml_orchestrator.py:1242-1247",
        "accent": "#22D3EE",
        "narration": "Once the series is ready, Bashira builds a StatsForecast engine with one AutoARIMA model. The frequency is weekly, because the source signal is tracked by week. The season length is four, which gives the model a short repeating horizon to search for useful autocorrelation and local weekly rhythm.",
    },
    {
        "title": "The Forecast Projects Four Weeks Ahead",
        "subtitle": "Bashira asks for a four-step horizon and ninety-five percent confidence intervals around the point forecast.",
        "code": "cpu_ml_orchestrator.py:1248-1254",
        "accent": "#67E8F9",
        "narration": "The actual forecast request is short and operational. Bashira asks for the next four weeks, and it also asks for ninety five percent intervals. That means the system does not return only one forward line. It also returns an uncertainty corridor around that projected path.",
    },
    {
        "title": "The Output Is Parsed Into A Forecast Track",
        "subtitle": "AutoARIMA, lower ninety-five, and upper ninety-five are converted into predicted, lower, and upper progress for each future week.",
        "code": "cpu_ml_orchestrator.py:1255-1262",
        "accent": "#22C55E",
        "narration": "The StatsForecast output arrives in raw column form. Bashira parses that result into a cleaner structure for the API. Each future row keeps the forecast week, the AutoARIMA prediction, the lower bound, and the upper bound. So the advanced forecast endpoint returns a usable trajectory packet instead of an internal library object.",
    },
    {
        "title": "Why The Trajectory Member Matters",
        "subtitle": "This path captures motion and autocorrelation directly from the progress curve, which snapshot models cannot do by themselves.",
        "code": "cpu_ml_orchestrator.py:1194-1198; ml-algorithms-and-terms-master.html:137-145",
        "accent": "#10B981",
        "narration": "This trajectory member matters because time series models read the actual curve shape. They see acceleration, flattening, and repeat structure directly from history. A snapshot model can infer some of that through engineered momentum features, but StatsForecast models the sequence itself. That is why it extends the stack rather than repeating it.",
    },
    {
        "title": "StatsForecast Feeds The Deeper Stack",
        "subtitle": "The trajectory forecast sits beside LightGBM, Stan, and S-Learner inside Bashira's broader ensemble architecture.",
        "code": "ensemble_stacker.py:6-15",
        "accent": "#14B8A6",
        "narration": "In the broader Bashira architecture, this forecast is not alone. The ensemble description lists StatsForecast AutoARIMA beside the calibrated LightGBM classifier, the Stan Bayesian member, and the S learner CATE path. So this topic is the temporal evidence member in a larger institutional stack.",
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
    rounded(draw, (x + 10, y + 12, x + w + 10, y + h + 12), (6, 16, 24, 112), radius=26)
    rounded(draw, (x, y, x + w, y + h), rgba((6, 18, 28), fill_alpha), outline=rgba(accent, 0.84), radius=26, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    width = draw.textbbox((0, 0), text, font=FONT_TAG)[2] + 28
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.15), outline=rgba(accent, 0.66), radius=999, width=2)
    draw.text((x + 14, y + 7), text, font=FONT_TAG, fill=(*accent, 255))


def draw_background(draw: ImageDraw.ImageDraw, accent):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(4, 14, 24))
    draw.ellipse((WIDTH - 290, -80, WIDTH + 70, 280), fill=rgba(accent, 0.12))
    draw.ellipse((-150, 520, 280, 920), fill=(6, 60, 82, 96))
    for y in range(180, 610, 40):
        draw.line((82, y, WIDTH - 82, y), fill=(19, 39, 54, 48), width=1)
    for x in range(110, WIDTH - 100, 96):
        draw.line((x, 182, x, 606), fill=(19, 39, 54, 30), width=1)


def draw_header(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    scene = SCENES[scene_index]
    draw_chip(draw, 92, 24, f"TS LAB 09 / STAGE {scene_index + 1:02d}", accent)
    draw.text((92, 84), scene["title"], font=FONT_TITLE, fill=(238, 244, 249))
    subtitle_font, subtitle_lines = fit_text_block(draw, scene["subtitle"], 1090, 2, 22, 18)
    draw_lines(draw, 92, 132, subtitle_lines, subtitle_font, (211, 224, 236), line_gap=2)
    for i in range(len(SCENES)):
        dot_x = 28 + i * 28
        dot_color = accent if i == scene_index else (44, 72, 90)
        draw.ellipse((dot_x, 152, dot_x + 18, 170), fill=dot_color)
    code_text = scene["code"]
    box_width = max(320, draw.textbbox((0, 0), code_text, font=FONT_MONO_SMALL)[2] + 42)
    panel(draw, WIDTH - box_width - 64, 22, box_width, 56, accent, fill_alpha=0.95)
    draw.text((WIDTH - box_width - 42, 40), code_text, font=FONT_MONO_SMALL, fill=(234, 241, 248))


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    panel(draw, 86, HEIGHT - 84, WIDTH - 172, 46, accent, fill_alpha=0.95)
    label = "STATSFORECAST"
    label_width = draw.textbbox((0, 0), label, font=FONT_TAG)[2]
    footer_font, lines = fit_text_block(draw, text, WIDTH - 290 - label_width, 1, 22, 18)
    draw_lines(draw, 112, HEIGHT - 72, lines, footer_font, (239, 243, 248), line_gap=0)
    draw.text((WIDTH - 118 - label_width, HEIGHT - 69), label, font=FONT_TAG, fill=(*accent, 255))


def draw_series(draw: ImageDraw.ImageDraw, values: list[float], x: int, y: int, w: int, h: int, color, labels: list[str] | None = None, width: int = 4):
    points = []
    for idx, value in enumerate(values):
        px = x + idx * (w / max(len(values) - 1, 1))
        py = y + h - (value / 100.0) * h
        points.append((px, py))
    if len(points) >= 2:
        draw.line(points, fill=color, width=width)
    for idx, (px, py) in enumerate(points):
        draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=color)
        if labels:
            draw.text((px - 12, y + h + 18), labels[idx], font=FONT_SMALL, fill=(212, 224, 236))


def scene_why(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 216, 430, 300, accent)
    draw.text((126, 246), "Need", font=FONT_PANEL, fill=(239, 244, 249))
    bullets = [
        "snapshot models read now",
        "time-series asks what comes next",
        "weekly planning needs a short horizon curve",
    ]
    for idx, bullet in enumerate(bullets):
        y = 308 + idx * 64
        draw.ellipse((130, y + 7, 146, y + 23), fill=(*accent, 255))
        font, lines = fit_text_block(draw, bullet, 340, 2, 20, 17)
        draw_lines(draw, 160, y, lines, font, (211, 224, 236), line_gap=4)

    panel(draw, 646, 226, 502, 280, accent)
    draw.text((676, 258), "Trajectory screen", font=FONT_PANEL, fill=(239, 244, 249))
    draw_series(draw, HISTORY, 694, 314, 380, 126, accent, labels=WEEKS)
    draw.text((724, 470), "history becomes a forward curve", font=FONT_BODY, fill=(211, 224, 236))


def scene_history(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Ordered well history", font=FONT_PANEL, fill=(239, 244, 249))
    draw.text((122, 286), "need at least two non-null progress points, sorted by Week_Number", font=FONT_MONO_SMALL, fill=(*accent, 255))
    draw_series(draw, HISTORY, 150, 332, 820, 150, accent, labels=WEEKS)
    for idx, value in enumerate(HISTORY):
        local = pop(progress, 0.06 + idx * 0.05)
        px = 150 + idx * (820 / max(len(HISTORY) - 1, 1))
        py = 332 + 150 - (value / 100.0) * 150
        draw.ellipse((px - 12, py - 12, px + 12, py + 12), outline=rgba(accent, 0.8), width=2)
        draw.text((px - 12, py - 40), str(value), font=FONT_MONO_SMALL, fill=(239, 244, 249, int(170 + 85 * local)))


def scene_prep(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 510, 324, accent)
    draw.text((126, 246), "StatsForecast input frame", font=FONT_PANEL, fill=(239, 244, 249))
    cols = [
        ("unique_id", "well_id"),
        ("ds", "Week_Number"),
        ("y", "progress * 100"),
    ]
    for idx, (name, meaning) in enumerate(cols):
        y = 328 + idx * 74
        rounded(draw, (126, y, 566, y + 48), rgba(accent, 0.08), outline=rgba(accent, 0.72), radius=18, width=2)
        draw.text((150, y + 13), name, font=FONT_MONO, fill=(*accent, 255))
        draw.text((306, y + 13), meaning, font=FONT_BODY, fill=(211, 224, 236))

    panel(draw, 672, 214, 508, 324, accent)
    draw.text((704, 246), "Why y is scaled", font=FONT_PANEL, fill=(239, 244, 249))
    bullets = [
        "source progress is stored in zero-to-one form",
        "trajectory output is easier to read in percentages",
        "forecast packet returns progress on a 0 to 100 scale",
    ]
    for idx, bullet in enumerate(bullets):
        y = 320 + idx * 70
        draw.ellipse((708, y + 7, 724, y + 23), fill=(*accent, 255))
        font, lines = fit_text_block(draw, bullet, 392, 2, 20, 17)
        draw_lines(draw, 740, y, lines, font, (211, 224, 236), line_gap=4)


def scene_model(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 520, 324, accent)
    draw.text((126, 246), "Model config", font=FONT_PANEL, fill=(239, 244, 249))
    config = [
        "StatsForecast(",
        "  models=[AutoARIMA(season_length=4)],",
        "  freq='W'",
        ")",
    ]
    for idx, line in enumerate(config):
        draw.text((130, 320 + idx * 40), line, font=FONT_MONO, fill=(211, 224, 236))

    panel(draw, 676, 214, 504, 324, accent)
    draw.text((706, 246), "Weekly rhythm lens", font=FONT_PANEL, fill=(239, 244, 249))
    for idx in range(4):
        x = 732 + idx * 94
        rounded(draw, (x, 334, x + 66, 120 + 334), rgba(accent, 0.10), outline=rgba(accent, 0.72), radius=18, width=2)
        draw.text((x + 21, 368), f"{idx + 1}", font=FONT_NUMBER, fill=(*accent, 255))
    draw.text((758, 484), "season_length = 4", font=FONT_MONO, fill=(211, 224, 236))


def scene_forecast(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Four-week horizon with interval band", font=FONT_PANEL, fill=(239, 244, 249))
    chart_x, chart_y, chart_w, chart_h = 150, 318, 860, 170
    draw.line((chart_x, chart_y + chart_h, chart_x + chart_w, chart_y + chart_h), fill=(194, 209, 224), width=3)
    draw.line((chart_x, chart_y + chart_h, chart_x, chart_y), fill=(194, 209, 224), width=3)
    draw_series(draw, HISTORY, chart_x, chart_y, 540, chart_h, rgb("#38BDF8"))
    future_x = chart_x + 540
    hist_last = HISTORY[-1]
    future_points = [hist_last] + FORECAST
    lower_points = [hist_last] + LOWER
    upper_points = [hist_last] + UPPER
    fp = []
    lp = []
    up = []
    for idx, value in enumerate(future_points):
        px = future_x + idx * (320 / 4)
        fp.append((px, chart_y + chart_h - (value / 100.0) * chart_h))
    for idx, value in enumerate(lower_points):
        px = future_x + idx * (320 / 4)
        lp.append((px, chart_y + chart_h - (value / 100.0) * chart_h))
    for idx, value in enumerate(upper_points):
        px = future_x + idx * (320 / 4)
        up.append((px, chart_y + chart_h - (value / 100.0) * chart_h))
    draw.polygon(up + list(reversed(lp)), fill=rgba(accent, 0.16))
    draw.line(fp, fill=rgb("#22C55E"), width=4)
    for px, py in fp:
        draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=rgb("#22C55E"))
    draw.text((900, 518), "AutoARIMA + 95% interval", font=FONT_MONO_SMALL, fill=(211, 224, 236))


def scene_parse(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 1088, 324, accent)
    draw.text((126, 246), "Parsed forecast packet", font=FONT_PANEL, fill=(239, 244, 249))
    headers = ["week", "predicted", "lower", "upper"]
    xs = [144, 410, 640, 840]
    for x, header in zip(xs, headers):
        draw.text((x, 304), header, font=FONT_MONO_SMALL, fill=(162, 183, 199))
    for idx, (wk, pred, low, up) in enumerate(zip(FUTURE_WEEKS, FORECAST, LOWER, UPPER)):
        y = 340 + idx * 48
        rounded(draw, (132, y, 1118, y + 34), rgba(accent, 0.08), outline=rgba(accent, 0.72), radius=16, width=2)
        draw.text((150, y + 9), wk, font=FONT_MONO_SMALL, fill=(239, 244, 249))
        draw.text((410, y + 9), f"{pred:.1f}", font=FONT_MONO_SMALL, fill=(239, 244, 249))
        draw.text((640, y + 9), f"{low:.1f}", font=FONT_MONO_SMALL, fill=(239, 244, 249))
        draw.text((840, y + 9), f"{up:.1f}", font=FONT_MONO_SMALL, fill=(239, 244, 249))


def scene_why_member(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 96, 214, 530, 324, accent)
    draw.text((126, 246), "What this member sees", font=FONT_PANEL, fill=(239, 244, 249))
    bullets = [
        "curve shape",
        "autocorrelation",
        "recent acceleration or flattening",
        "short-horizon weekly rhythm",
    ]
    for idx, bullet in enumerate(bullets):
        y = 316 + idx * 46
        draw.ellipse((130, y + 7, 146, y + 23), fill=(*accent, 255))
        draw.text((160, y + 2), bullet, font=FONT_BODY, fill=(211, 224, 236))

    panel(draw, 690, 214, 490, 324, accent)
    draw.text((720, 246), "Why snapshot models cannot replace it", font=FONT_PANEL, fill=(239, 244, 249))
    note = "momentum features can hint at motion, but StatsForecast models the ordered sequence itself."
    font, lines = fit_text_block(draw, note, 420, 5, 21, 17)
    draw_lines(draw, 722, 324, lines, font, (211, 224, 236), line_gap=4)


def scene_ensemble(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 90, 214, 1100, 324, accent)
    draw.text((122, 246), "Trajectory member inside the ensemble", font=FONT_PANEL, fill=(239, 244, 249))
    members = [
        "LightGBM delay risk",
        "StatsForecast AutoARIMA",
        "Stan posterior mean",
        "S-Learner CATE",
    ]
    for idx, label in enumerate(members):
        x = 130 + idx * 250
        local = pop(progress, 0.06 + idx * 0.08)
        rounded(draw, (x, 336, x + 190, 430), rgba(accent, 0.08 + 0.08 * local), outline=rgba(accent, 0.76), radius=22, width=2)
        font, lines = fit_text_block(draw, label, 154, 3, 22, 18, bold=True)
        draw_lines(draw, x + 18, 360, lines, font, (239, 244, 249), line_gap=4)
    draw.text((462, 472), "temporal evidence joins the broader institutional stack", font=FONT_BODY, fill=(211, 224, 236))


DRAWERS = [
    scene_why,
    scene_history,
    scene_prep,
    scene_model,
    scene_forecast,
    scene_parse,
    scene_why_member,
    scene_ensemble,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (4, 14, 24))
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

    combined_audio = run_dir / "statsforecast_trajectory_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "statsforecast_trajectory_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

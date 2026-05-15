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
OUTPUT_FILE = OUTPUT_DIR / "spatial-pressure-clusters-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 20
SCENE_GAP_SECONDS = 0.24
MIN_SCENE_SECONDS = 12.0

BLUE = "#0EA5E9"
CYAN = "#22D3EE"
NAVY = "#0F172A"
MINT = "#34D399"
GOLD = "#FBBF24"
SLATE = "#CBD5E1"

WELLS = [
    ("W-101", 238, 214, 72.4, True),
    ("W-102", 316, 272, 64.2, False),
    ("W-103", 404, 246, 58.9, False),
    ("W-104", 732, 206, 67.8, True),
    ("W-105", 796, 272, 55.7, False),
    ("W-106", 864, 236, 48.3, False),
    ("W-107", 564, 438, 61.4, False),
    ("W-108", 652, 498, 76.2, True),
    ("W-109", 760, 454, 59.6, False),
]

ZONE_ROWS = [
    ("Z01", "Execution", 5, 71.2),
    ("Z02", "Rig Arrival", 3, 64.7),
    ("C-Delta", "Construction", 4, 58.5),
]

CORRIDORS = [
    ("RIG-08", "W-108", "W-104", 1, 74.3, "Pressure Relay"),
    ("RIG-03", "W-101", "W-102", -2, 69.1, "Sequence Clash"),
    ("RIG-11", "W-105", "W-109", 3, 51.6, "Transition Corridor"),
]

SCENES = [
    {
        "title": "Why Bashira Needs A Spatial Lens",
        "subtitle": "Operational pressure is not only inside one well. Nearby wells, shared pads, and rig movement create geographic pressure patterns.",
        "code": "command_center_service.py:1983-2065",
        "accent": BLUE,
        "narration": "This final topic shows why Bashira does not stop at single-well scoring. Two wells can look similar on paper, but their geographic context can be completely different. Nearby critical wells, shared queue exposure, and rig handover routes create local pressure. The atlas layer turns that geographic context into a measurable signal instead of leaving it as intuition.",
    },
    {
        "title": "Coordinates Are Repaired Before The Atlas Is Built",
        "subtitle": "Bashira starts from the operating frame, keeps actual easting and northing when present, and imputes missing coordinates from the cluster centroid when needed.",
        "code": "command_center_service.py:2005-2060",
        "accent": CYAN,
        "narration": "The map cannot begin with missing positions. Bashira first separates wells that already have coordinates from those that do not. Then it computes a centroid for each cluster. If a well is missing easting or northing, the service can borrow the cluster centroid and mark that coordinate source as imputed. That lets the atlas stay spatially useful without pretending the imputed point is the same as a surveyed location.",
    },
    {
        "title": "Neighborhood Radius Is Learned From The Field Layout",
        "subtitle": "Bashira uses nearest-neighbor distances from actual wells and calibrates a working radius between 1,200 and 4,200 meters.",
        "code": "command_center_service.py:2117-2128",
        "accent": BLUE,
        "narration": "The atlas does not use one fixed neighborhood size for every field. Bashira measures the actual spacing between real wells with nearest neighbors. Then it takes the upper quartile distance and inflates it slightly to get a working neighborhood radius. That radius is clamped between twelve hundred and forty two hundred meters. So the field itself teaches the model how wide a local neighborhood should be.",
    },
    {
        "title": "Local Pressure Comes From Weighted Nearby Risk",
        "subtitle": "For each well, Bashira finds all neighbors inside the radius, weights them by distance, counts nearby critical wells, and forms a neighborhood pressure score.",
        "code": "command_center_service.py:2130-2168",
        "accent": MINT,
        "narration": "Now the geometric pressure calculation begins. Bashira asks which wells fall inside the local radius around each point. Closer wells get higher weight, farther wells get lower weight, but every valid neighbor contributes. The service also counts how many of those neighbors are already high risk or critical. From those ingredients it builds neighborhood pressure, local density, and nearby critical counts. This is where raw geography becomes operational context.",
    },
    {
        "title": "Spatial Signal Blends Geography With Operational Stress",
        "subtitle": "The final per-well spatial signal mixes ops risk, neighborhood pressure, local density, queue exposure, nearby critical wells, and anomaly flags.",
        "code": "command_center_service.py:2169-2176",
        "accent": GOLD,
        "narration": "Bashira does not let geography override everything else. Instead it blends spatial and operational evidence into one spatial signal score. Ops risk carries the biggest share, then neighborhood pressure, then local density. Queue exposure adds more pressure, nearby critical wells add more pressure, and anomaly flags add another boost. The result is a number that says not only how risky the well is, but how exposed it is inside the surrounding field pattern.",
    },
    {
        "title": "DBSCAN Forms Zones Without Pre-Choosing A Count",
        "subtitle": "When enough actual wells exist, Bashira uses DBSCAN with adaptive `eps` and `min_samples=3` to form spatial zones from the field geometry.",
        "code": "command_center_service.py:2178-2235",
        "accent": CYAN,
        "narration": "After per well pressure is known, Bashira groups the map into zones. It uses DBSCAN because oilfield geography is irregular. The system does not want to guess a fixed number of clusters ahead of time. Instead it uses an adaptive epsilon based on neighborhood radius and requires at least three samples to form a zone. If no stable DBSCAN zones appear, Bashira falls back to cluster based labels so the atlas still has a usable spatial grouping.",
    },
    {
        "title": "Zones Summarize Local Pressure Stories",
        "subtitle": "Each zone receives a center, radii, well count, critical and delayed counts, average signal, rig mix, and dominant bottleneck story.",
        "code": "command_center_service.py:2238-2279",
        "accent": BLUE,
        "narration": "A zone is more than a shape on a map. Bashira summarizes each zone so the team can read it quickly. The service computes the zone center and radii, counts wells and rigs, counts critical and delayed wells, averages the spatial signal, and accumulates bottleneck pressure. Then it names the dominant bottleneck in that zone. This is the moment where many wells collapse into one area level operational story.",
    },
    {
        "title": "Rig Corridors Reveal Pressure Relay Between Wells",
        "subtitle": "Bashira sorts wells by expected rig sequence, measures travel distance and handover gap, and scores each corridor as a sequence clash, pressure relay, or transition corridor.",
        "code": "command_center_service.py:2335-2396",
        "accent": MINT,
        "narration": "The atlas finishes with rig corridors. Bashira groups wells by rig, orders them by expected rig sequence, and then examines each handoff. It measures distance between wells, the gap or overlap in dates, local queue exposure, and the strongest spatial signal on the pair. From that it scores a corridor. Some corridors are normal transitions, some are pressure relays, and some are sequence clashes. That final layer shows how pressure can travel through the rig schedule itself.",
    },
]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


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
FONT_HUGE = load_font(58, bold=True, mono=True)


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


def panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, accent, fill_alpha: float = 0.93):
    rounded(draw, (x + 10, y + 12, x + w + 10, y + h + 12), (8, 22, 34, 120), radius=26)
    rounded(draw, (x, y, x + w, y + h), rgba((8, 22, 34), fill_alpha), outline=rgba(accent, 0.82), radius=26, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    width = draw.textbbox((0, 0), text, font=FONT_TAG)[2] + 28
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.16), outline=rgba(accent, 0.72), radius=999, width=2)
    draw.text((x + 14, y + 7), text, font=FONT_TAG, fill=(*accent, 255))


def draw_background(draw: ImageDraw.ImageDraw, accent):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(5, 16, 28))
    draw.ellipse((WIDTH - 320, -88, WIDTH + 60, 292), fill=rgba(accent, 0.12))
    draw.ellipse((-180, 522, 252, 920), fill=rgba(rgb(CYAN), 0.10))
    for x in range(88, WIDTH - 80, 72):
        draw.line((x, 172, x, 620), fill=(24, 60, 84, 22), width=1)
    for y in range(180, 620, 38):
        draw.line((76, y, WIDTH - 76, y), fill=(24, 60, 84, 28), width=1)


def draw_header(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    scene = SCENES[scene_index]
    draw_chip(draw, 88, 24, f"FIELD ATLAS / STAGE {scene_index + 1:02d}", accent)
    draw.text((88, 82), scene["title"], font=FONT_TITLE, fill=(240, 247, 252))
    subtitle_font, subtitle_lines = fit_text_block(draw, scene["subtitle"], 1080, 2, 22, 18)
    draw_lines(draw, 88, 132, subtitle_lines, subtitle_font, (213, 229, 238), line_gap=2)
    for idx in range(len(SCENES)):
        dot_x = 28 + idx * 28
        dot_color = accent if idx == scene_index else (48, 78, 100)
        draw.ellipse((dot_x, 150, dot_x + 18, 168), fill=dot_color)
    code_text = scene["code"]
    box_width = max(360, draw.textbbox((0, 0), code_text, font=FONT_MONO_SMALL)[2] + 42)
    panel(draw, WIDTH - box_width - 60, 22, box_width, 58, accent, fill_alpha=0.96)
    draw.text((WIDTH - box_width - 38, 41), code_text, font=FONT_MONO_SMALL, fill=(240, 247, 252))


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    panel(draw, 82, HEIGHT - 84, WIDTH - 164, 48, accent, fill_alpha=0.96)
    label = "SPATIAL PRESSURE"
    label_width = draw.textbbox((0, 0), label, font=FONT_TAG)[2]
    footer_font, lines = fit_text_block(draw, text, WIDTH - 320 - label_width, 1, 22, 18)
    draw_lines(draw, 108, HEIGHT - 72, lines, footer_font, (240, 247, 252), line_gap=0)
    draw.text((WIDTH - 118 - label_width, HEIGHT - 69), label, font=FONT_TAG, fill=(*accent, 255))


def map_frame(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, accent):
    rounded(draw, (x, y, x + w, y + h), rgba((6, 26, 38), 0.95), outline=rgba(accent, 0.68), radius=28, width=2)
    for gx in range(x + 24, x + w, 66):
        draw.line((gx, y + 20, gx, y + h - 20), fill=(22, 82, 116, 28), width=1)
    for gy in range(y + 20, y + h, 54):
        draw.line((x + 20, gy, x + w - 20, gy), fill=(22, 82, 116, 28), width=1)


def draw_wells(draw: ImageDraw.ImageDraw, offset_x: int, offset_y: int, highlight_zone: int | None = None):
    for idx, (label, px, py, score, critical) in enumerate(WELLS):
        x = offset_x + px
        y = offset_y + py
        base = rgb(BLUE if not critical else GOLD)
        radius = 10 if not critical else 13
        if highlight_zone is not None:
            zone_members = {0, 1, 2} if highlight_zone == 0 else {3, 4, 5} if highlight_zone == 1 else {6, 7, 8}
            alpha = 1.0 if idx in zone_members else 0.32
        else:
            alpha = 1.0
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=rgba(base, alpha))
        draw.text((x + 14, y - 10), label, font=FONT_SMALL, fill=rgba(rgb(SLATE), alpha))


def scene_why(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    map_frame(draw, 122, 248, 1036, 240, accent)
    draw_wells(draw, 0, 0)
    draw.text((136, 506), "geography changes exposure: nearby critical wells and rig movement create local pressure", font=FONT_BODY, fill=(213, 229, 238))


def scene_coords(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 536, 334, accent)
    draw.text((122, 240), "Coordinate repair", font=FONT_PANEL, fill=(240, 247, 252))
    rows = [
        ("actual point", "keep surveyed easting/northing"),
        ("missing point", "borrow cluster centroid"),
        ("coord_source", "actual or cluster_imputed"),
    ]
    for idx, (label, value) in enumerate(rows):
        y = 312 + idx * 58
        rounded(draw, (122, y, 588, y + 40), rgba(accent, 0.06), outline=rgba(accent, 0.68), radius=18, width=2)
        draw.text((142, y + 11), label, font=FONT_MONO_SMALL, fill=(213, 229, 238))
        draw.text((286, y + 11), value, font=FONT_MONO_SMALL, fill=(*accent, 255))
    panel(draw, 674, 208, 514, 334, accent)
    map_frame(draw, 704, 248, 454, 240, accent)
    draw.ellipse((820, 324, 842, 346), fill=rgba(rgb(CYAN), 1.0))
    draw.ellipse((918, 372, 940, 394), fill=rgba(rgb(CYAN), 1.0))
    draw.ellipse((1004, 316, 1026, 338), fill=rgba(rgb(CYAN), 1.0))
    draw.ellipse((910, 324, 934, 348), outline=rgba(rgb(GOLD), 0.9), width=3)
    draw.text((760, 506), "missing wells inherit their cluster center instead of disappearing from the atlas", font=FONT_BODY, fill=(213, 229, 238))


def scene_radius(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    map_frame(draw, 122, 248, 620, 240, accent)
    center_x, center_y = 428, 362
    draw_wells(draw, 0, 0)
    for radius in [72, 124, 186]:
        draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), outline=rgba(accent, 0.38), width=2)
    panel(draw, 786, 248, 340, 240, accent)
    draw.text((816, 276), "neighbor radius", font=FONT_PANEL, fill=(240, 247, 252))
    draw.text((816, 340), "1800 m", font=FONT_HUGE, fill=(*accent, 255))
    draw.text((816, 424), "learned from nearest-neighbor spacing", font=FONT_BODY, fill=(213, 229, 238))


def scene_pressure(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    map_frame(draw, 122, 248, 620, 240, accent)
    draw_wells(draw, 0, 0)
    hub = (652, 498)
    neighbors = [(564, 438), (760, 454), (732, 206)]
    for nx, ny in neighbors:
        draw.line((hub[0], hub[1], nx, ny), fill=rgba(accent, 0.56), width=3)
    panel(draw, 786, 248, 340, 240, accent)
    draw.text((816, 276), "per-well spatial build", font=FONT_PANEL, fill=(240, 247, 252))
    points = [
        "weighted nearby risk",
        "local neighbor count",
        "nearby critical count",
        "neighborhood pressure score",
    ]
    for idx, text in enumerate(points):
        y = 326 + idx * 38
        draw.ellipse((818, y + 8, 832, y + 22), fill=(*accent, 255))
        draw.text((846, y), text, font=FONT_SMALL, fill=(213, 229, 238))


def scene_signal(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    draw.text((122, 240), "Spatial signal blend", font=FONT_PANEL, fill=(240, 247, 252))
    rows = [
        ("ops_risk_score", "0.52"),
        ("neighborhood_pressure_score", "0.23"),
        ("local_density_score", "0.10"),
        ("queue_exposure", "2.2 x"),
        ("nearby_critical_count", "2.4 x"),
        ("anomaly_flag", "+6"),
    ]
    for idx, (label, value) in enumerate(rows):
        x = 128 + (idx % 3) * 314
        y = 306 + (idx // 3) * 92
        rounded(draw, (x, y, x + 272, y + 62), rgba(accent, 0.06), outline=rgba(accent, 0.72), radius=18, width=2)
        draw.text((146, y + 12), label, font=FONT_MONO_SMALL, fill=(213, 229, 238))
        draw.text((324, y + 12), value, font=FONT_MONO_SMALL, fill=(*accent, 255))
    draw.text((430, 514), "the atlas caps the final spatial signal at 99 and keeps it aligned with operational reality", font=FONT_BODY, fill=(213, 229, 238))


def scene_dbscan(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    map_frame(draw, 122, 248, 620, 240, accent)
    zone_specs = [
        (332, 262, 170, 112, rgb(BLUE)),
        (736, 250, 172, 118, rgb(CYAN)),
        (612, 434, 188, 122, rgb(MINT)),
    ]
    for cx, cy, rx, ry, color in zone_specs:
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=rgba(color, 0.52), width=3)
    draw_wells(draw, 0, 0)
    panel(draw, 786, 248, 340, 240, accent)
    draw.text((816, 276), "adaptive zoning", font=FONT_PANEL, fill=(240, 247, 252))
    draw.text((816, 336), "DBSCAN", font=FONT_HUGE, fill=(*accent, 255))
    draw.text((816, 408), "eps = neighbor_radius x 1.28", font=FONT_MONO_SMALL, fill=(213, 229, 238))
    draw.text((816, 438), "min_samples = 3", font=FONT_MONO_SMALL, fill=(213, 229, 238))


def scene_zones(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    map_frame(draw, 122, 248, 460, 240, accent)
    draw_wells(draw, 0, 0, highlight_zone=1)
    headers = ["zone", "bottleneck", "wells", "avg signal"]
    xs = [636, 778, 928, 1032]
    for x, header in zip(xs, headers):
        draw.text((x, 272), header, font=FONT_MONO_SMALL, fill=(170, 204, 220))
    for idx, (zone, bottleneck, wells, avg_signal) in enumerate(ZONE_ROWS):
        y = 318 + idx * 58
        rounded(draw, (622, y, 1144, y + 42), rgba(accent, 0.06), outline=rgba(accent, 0.70), radius=18, width=2)
        draw.text((640, y + 12), zone, font=FONT_MONO_SMALL, fill=(240, 247, 252))
        draw.text((774, y + 12), bottleneck, font=FONT_MONO_SMALL, fill=(213, 229, 238))
        draw.text((940, y + 12), str(wells), font=FONT_MONO_SMALL, fill=(213, 229, 238))
        draw.text((1032, y + 12), f"{avg_signal:.1f}", font=FONT_MONO_SMALL, fill=(*accent, 255))


def scene_corridors(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    map_frame(draw, 122, 248, 460, 240, accent)
    points = {label: (x, y) for label, x, y, _, _ in WELLS}
    draw_wells(draw, 0, 0)
    for idx, (_, src, dst, _, _, _) in enumerate(CORRIDORS):
        sx, sy = points[src]
        dx, dy = points[dst]
        color = rgb(MINT if idx != 1 else GOLD)
        draw.line((sx, sy, dx, dy), fill=rgba(color, 0.72), width=4)
    headers = ["rig", "path", "gap", "pressure", "type"]
    xs = [622, 712, 842, 930, 1030]
    for x, header in zip(xs, headers):
        draw.text((x, 272), header, font=FONT_MONO_SMALL, fill=(170, 204, 220))
    for idx, (rig, src, dst, gap, pressure, kind) in enumerate(CORRIDORS):
        y = 318 + idx * 58
        rounded(draw, (608, y, 1150, y + 42), rgba(accent, 0.06), outline=rgba(accent, 0.70), radius=18, width=2)
        draw.text((624, y + 12), rig, font=FONT_MONO_SMALL, fill=(240, 247, 252))
        draw.text((710, y + 12), f"{src}->{dst}", font=FONT_MONO_SMALL, fill=(213, 229, 238))
        draw.text((846, y + 12), f"{gap:+d}d", font=FONT_MONO_SMALL, fill=(213, 229, 238))
        draw.text((934, y + 12), f"{pressure:.1f}", font=FONT_MONO_SMALL, fill=(*accent, 255))
        draw.text((1028, y + 12), kind, font=FONT_SMALL, fill=(213, 229, 238))


DRAWERS = [
    scene_why,
    scene_coords,
    scene_radius,
    scene_pressure,
    scene_signal,
    scene_dbscan,
    scene_zones,
    scene_corridors,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (5, 16, 28))
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

    combined_audio = run_dir / "spatial_pressure_clusters_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "spatial_pressure_clusters_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

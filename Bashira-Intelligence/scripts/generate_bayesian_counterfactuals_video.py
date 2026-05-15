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
OUTPUT_FILE = OUTPUT_DIR / "bayesian-counterfactuals-approval.mp4"
TEMP_DIR = ROOT / "_predictive_video_build"

WIDTH = 1280
HEIGHT = 720
FPS = 20
SCENE_GAP_SECONDS = 0.24
MIN_SCENE_SECONDS = 12.0

DEEP_PURPLE = "#9333EA"
ORCHID = "#C084FC"
PINK = "#F472B6"
GOLD = "#FBBF24"
MINT = "#34D399"
SLATE = "#94A3B8"

DRIVER_ROWS = [
    ("schedule_pressure", +2.4, 1.6, 3.1, 0.93),
    ("material_wait_days", +1.8, 1.1, 2.4, 0.89),
    ("recent_pace", -1.2, -1.8, -0.7, 0.84),
    ("crew_load", +0.9, 0.3, 1.4, 0.71),
]

GROUP_COUNTS = [
    ("rig_no", 14),
    ("cluster", 9),
    ("well_type", 4),
    ("progress_band", 6),
]

SCENES = [
    {
        "title": "Why Bashira Goes Bayesian",
        "subtitle": "Instead of one hard answer, Bashira measures many plausible answers and keeps the uncertainty attached to each scenario.",
        "code": "causal_stan_service.py:78-90, 149-190",
        "accent": DEEP_PURPLE,
        "narration": "This causal layer is different from the faster predictive layers. Bashira is not trying to squeeze everything into one fixed answer. It wants to ask a deeper question. If we imagine different intervention scenarios, what effect is plausible, and how certain are we about it? That is why this service is Bayesian. It keeps a distribution of believable answers, not just one number.",
    },
    {
        "title": "The Data Is Standardized And Grouped",
        "subtitle": "The service turns the well table into standardized feature columns, target delay days, and four hierarchy keys: rig, cluster, well type, and progress band.",
        "code": "causal_stan_service.py:428-446",
        "accent": ORCHID,
        "narration": "Before any Bayesian sampling begins, Bashira prepares the evidence table. The feature matrix X and the target delay days y are standardized so the model can compare signals on a common scale. Then four group identities are encoded. Each row belongs to one rig number, one cluster, one well type, and one progress band. These group keys let the model learn shared structure instead of treating every row as isolated.",
    },
    {
        "title": "Four Chains Explore The Posterior",
        "subtitle": "When CmdStan is available, Bashira runs four chains with 500 warmup steps and 500 sampling steps to explore many plausible coefficient worlds.",
        "code": "causal_stan_service.py:448-468",
        "accent": PINK,
        "narration": "On the deep path, Bashira sends the prepared data into Stan. Stan does not return one quick formula answer. It explores the posterior. In this implementation, four chains run in parallel. Each chain warms up for five hundred steps, then samples for five hundred more. So Bashira gathers two thousand posterior draws. Each draw is one believable world of coefficients and group effects that could explain the data.",
    },
    {
        "title": "Hierarchy Shrinks Noisy Groups Toward Reality",
        "subtitle": "Rig, cluster, well type, and progress-band effects are learned as grouped effects so thin data does not create wild, unstable stories.",
        "code": "causal_stan_service.py:493-521",
        "accent": GOLD,
        "narration": "The hierarchy is one of the most important ideas here. Bashira does not let every rig or cluster invent its own extreme story from a few noisy rows. Instead, grouped effects are learned together. Strong groups can still stand out, but weak groups get gently pulled toward the shared center. That shrinkage makes the counterfactual story more honest, especially when some groups have much less history than others.",
    },
    {
        "title": "Diagnostics Check Whether The Posterior Can Be Trusted",
        "subtitle": "The service records R-hat, effective sample size, divergence text, and LOO-CV so Bashira can judge whether the sampled story is stable and useful.",
        "code": "causal_stan_service.py:460-491",
        "accent": MINT,
        "narration": "After sampling, Bashira does not blindly trust the draws. It checks convergence and model quality. R hat asks whether the chains mixed well. Effective sample size asks how much real information the draws contain. Divergence text warns about geometry problems. Then LOO cross validation estimates out of sample quality. These checks act like a quality gate. If the posterior looks shaky, the team knows not to overstate the scenario story.",
    },
    {
        "title": "Laplace Fallback Still Computes Uncertainty",
        "subtitle": "If MCMC is unavailable, Bashira finds a MAP solution, tunes lambda with GCV, builds Hessian covariance, and still returns uncertainty-aware effects.",
        "code": "causal_stan_service.py:544-654",
        "accent": SLATE,
        "narration": "Sometimes the full Stan path is not available. Bashira still does not collapse into a naive point estimate. It runs a Laplace approximation. First it searches a lambda grid and uses general cross validation to pick the shrinkage strength. Then it computes a maximum a posteriori estimate and uses the Hessian to approximate posterior covariance. That means even the fallback path still carries uncertainty and adaptive shrinkage.",
    },
    {
        "title": "Posterior Drivers Become Credible Intervals",
        "subtitle": "The service converts posterior coefficients into day-level impacts, credible ranges, inclusion probabilities, and ranked driver shares.",
        "code": "causal_stan_service.py:755-791",
        "accent": DEEP_PURPLE,
        "narration": "Once the posterior is ready, Bashira turns coefficient draws into driver evidence people can read. Each feature gets a mean effect in delay days, a low and high credible boundary, and an inclusion score that says how strongly that feature belongs in the story. Then the effects are ranked by absolute size. This is how the Bayesian layer explains not only what pushes delay pressure, but how confident it is about each push.",
    },
    {
        "title": "Counterfactual Stories Are Aggregated For Action",
        "subtitle": "The posterior drivers, grouped effects, and root-cause summaries are packaged into scenario options that explain where pressure comes from and what could change it.",
        "code": "causal_stan_service.py:793-835",
        "accent": ORCHID,
        "narration": "The last step is not just math for math's sake. Bashira combines the posterior drivers with grouped effects and root cause logic, then packages them into counterfactual options. The result is a scenario summary the team can discuss. It tells them which forces are increasing delay pressure, which ones are reducing it, what uncertainty remains, and which intervention stories deserve attention first.",
    },
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
FONT_TITLE = load_font(39, bold=True)
FONT_SUB = load_font(22)
FONT_PANEL = load_font(28, bold=True)
FONT_BODY = load_font(19)
FONT_SMALL = load_font(15)
FONT_MONO = load_font(18, mono=True)
FONT_MONO_SMALL = load_font(15, mono=True)
FONT_NUMBER = load_font(54, bold=True, mono=True)
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
    rounded(draw, (x + 10, y + 14, x + w + 10, y + h + 14), (14, 10, 28, 112), radius=28)
    rounded(draw, (x, y, x + w, y + h), rgba((14, 10, 28), fill_alpha), outline=rgba(accent, 0.82), radius=28, width=2)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, accent):
    width = draw.textbbox((0, 0), text, font=FONT_TAG)[2] + 30
    rounded(draw, (x, y, x + width, y + 30), rgba(accent, 0.18), outline=rgba(accent, 0.72), radius=999, width=2)
    draw.text((x + 14, y + 7), text, font=FONT_TAG, fill=(*accent, 255))


def draw_background(draw: ImageDraw.ImageDraw, accent, progress: float):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(7, 8, 20))
    draw.ellipse((WIDTH - 340, -80, WIDTH + 80, 340), fill=rgba(accent, 0.14))
    draw.ellipse((-180, 500, 290, 920), fill=rgba(rgb(PINK), 0.11))
    for x in range(70, WIDTH, 78):
        alpha = 24 if x % 156 == 0 else 14
        draw.line((x, 170, x, HEIGHT - 110), fill=(55, 59, 90, alpha), width=1)
    for y in range(182, HEIGHT - 110, 42):
        draw.line((70, y, WIDTH - 70, y), fill=(46, 50, 82, 24), width=1)
    rng = np.random.default_rng(42)
    pulse = 0.65 + 0.35 * np.sin(progress * np.pi)
    for idx in range(48):
        px = 100 + (idx * 97) % 1100
        py = 190 + (idx * 53) % 360
        radius = 2 + (idx % 3)
        dot_alpha = 90 if idx % 7 == 0 else 55
        if idx % 5 == 0:
            px += int(8 * pulse)
        if idx % 4 == 0:
            py += int(6 * pulse)
        color = accent if idx % 6 == 0 else rgb(ORCHID if idx % 2 == 0 else SLATE)
        draw.ellipse((px, py, px + radius * 2, py + radius * 2), fill=rgba(color, dot_alpha / 255))


def draw_header(draw: ImageDraw.ImageDraw, scene_index: int, accent):
    scene = SCENES[scene_index]
    draw_chip(draw, 88, 24, f"CAUSAL DEEP LAYER / STAGE {scene_index + 1:02d}", accent)
    draw.text((88, 82), scene["title"], font=FONT_TITLE, fill=(245, 244, 251))
    subtitle_font, subtitle_lines = fit_text_block(draw, scene["subtitle"], 1080, 2, 22, 18)
    draw_lines(draw, 88, 132, subtitle_lines, subtitle_font, (219, 216, 233), line_gap=2)
    for idx in range(len(SCENES)):
        dot_x = 28 + idx * 28
        dot_color = accent if idx == scene_index else (68, 63, 92)
        draw.ellipse((dot_x, 150, dot_x + 18, 168), fill=dot_color)
    code_text = scene["code"]
    box_width = max(340, draw.textbbox((0, 0), code_text, font=FONT_MONO_SMALL)[2] + 40)
    panel(draw, WIDTH - box_width - 60, 22, box_width, 58, accent, fill_alpha=0.96)
    draw.text((WIDTH - box_width - 38, 41), code_text, font=FONT_MONO_SMALL, fill=(239, 236, 248))


def draw_footer(draw: ImageDraw.ImageDraw, text: str, accent):
    panel(draw, 82, HEIGHT - 84, WIDTH - 164, 48, accent, fill_alpha=0.96)
    label = "BAYESIAN COUNTERFACTUALS"
    label_width = draw.textbbox((0, 0), label, font=FONT_TAG)[2]
    footer_font, lines = fit_text_block(draw, text, WIDTH - 340 - label_width, 1, 22, 18)
    draw_lines(draw, 108, HEIGHT - 72, lines, footer_font, (245, 244, 251), line_gap=0)
    draw.text((WIDTH - 118 - label_width, HEIGHT - 69), label, font=FONT_TAG, fill=(*accent, 255))


def vertical_meter(draw: ImageDraw.ImageDraw, x: int, y: int, h: int, ratio: float, accent):
    rounded(draw, (x, y, x + 34, y + h), (20, 18, 37), outline=rgba(accent, 0.6), radius=18, width=2)
    fill_h = max(20, int(h * clamp(ratio)))
    rounded(draw, (x + 4, y + h - fill_h - 4, x + 30, y + h - 4), rgba(accent, 0.95), radius=14)


def scene_bayesian(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 94, 208, 458, 330, accent)
    draw.text((126, 240), "One number or many believable worlds?", font=FONT_PANEL, fill=(245, 244, 251))
    draw.text((130, 322), "single answer", font=FONT_MONO_SMALL, fill=(177, 170, 195))
    draw.text((128, 356), "3.2 days", font=FONT_HUGE, fill=(255, 255, 255))
    draw.text((128, 438), "Bayesian service keeps a spread", font=FONT_BODY, fill=(221, 218, 234))
    panel(draw, 620, 210, 562, 328, accent)
    draw.text((652, 240), "posterior cloud", font=FONT_PANEL, fill=(245, 244, 251))
    cx, cy = 900, 386
    for idx in range(46):
        angle = idx * 0.37
        radius = 30 + idx * 3
        px = int(cx + np.cos(angle) * radius * (0.6 + 0.3 * progress))
        py = int(cy + np.sin(angle) * radius * 0.48)
        alpha = 0.35 + 0.5 * ((idx % 5) / 4)
        color = rgb(PINK if idx % 3 == 0 else ORCHID if idx % 3 == 1 else DEEP_PURPLE)
        draw.ellipse((px, py, px + 10, py + 10), fill=rgba(color, alpha))
    draw.text((790, 468), "many plausible effect values", font=FONT_BODY, fill=(221, 218, 234))


def scene_prepare(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    draw.text((122, 240), "Prepared evidence frame", font=FONT_PANEL, fill=(245, 244, 251))
    labels = ["standardized X", "target y", "rig_id", "cluster_id", "well_type_id", "progress_band_id"]
    values = ["58 cols", "delay days", "14 groups", "9 groups", "4 groups", "6 groups"]
    for idx, (label, value) in enumerate(zip(labels, values)):
        x = 126 + (idx % 3) * 318
        y = 304 + (idx // 3) * 116
        rounded(draw, (x, y, x + 272, y + 82), rgba(accent, 0.08), outline=rgba(accent, 0.72), radius=22, width=2)
        draw.text((x + 18, y + 18), label, font=FONT_MONO_SMALL, fill=(221, 218, 234))
        draw.text((x + 18, y + 46), value, font=FONT_PANEL, fill=(*accent, 255))
    draw.text((818, 468), "rows keep both feature values and hierarchy membership", font=FONT_BODY, fill=(221, 218, 234))


def scene_chains(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    draw.text((122, 240), "Posterior exploration chamber", font=FONT_PANEL, fill=(245, 244, 251))
    chain_colors = [rgb(DEEP_PURPLE), rgb(ORCHID), rgb(PINK), rgb(GOLD)]
    for idx, chain_color in enumerate(chain_colors):
        x = 130 + idx * 268
        rounded(draw, (x, 300, x + 224, 470), rgba(chain_color, 0.08), outline=rgba(chain_color, 0.76), radius=22, width=2)
        draw.text((x + 18, 324), f"chain {idx + 1}", font=FONT_PANEL, fill=(245, 244, 251))
        draw.text((x + 18, 366), "warmup 500", font=FONT_MONO_SMALL, fill=(221, 218, 234))
        draw.text((x + 18, 394), "sample 500", font=FONT_MONO_SMALL, fill=(221, 218, 234))
        draw.text((x + 18, 436), "500 draws", font=FONT_NUMBER, fill=(*chain_color, 255))
    draw.text((488, 494), "4 chains x 500 posterior draws = 2000 plausible coefficient worlds", font=FONT_BODY, fill=(221, 218, 234))


def scene_hierarchy(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    draw.text((122, 240), "Hierarchy prevents noisy overreaction", font=FONT_PANEL, fill=(245, 244, 251))
    base_x = 150
    for idx, (label, count) in enumerate(GROUP_COUNTS):
        x = base_x + idx * 254
        color = rgb([DEEP_PURPLE, ORCHID, GOLD, MINT][idx])
        rounded(draw, (x, 310, x + 188, 478), rgba(color, 0.08), outline=rgba(color, 0.78), radius=26, width=2)
        draw.text((x + 18, 336), label, font=FONT_MONO_SMALL, fill=(221, 218, 234))
        draw.text((x + 18, 382), str(count), font=FONT_HUGE, fill=(*color, 255))
        draw.text((x + 18, 450), "levels", font=FONT_BODY, fill=(221, 218, 234))
    draw.text((318, 506), "small groups get partial pooling so weak evidence does not become a dramatic false story", font=FONT_BODY, fill=(221, 218, 234))


def scene_diag(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 530, 334, accent)
    draw.text((122, 240), "MCMC quality gate", font=FONT_PANEL, fill=(245, 244, 251))
    stats = [
        ("R-hat max", 0.97, "1.01"),
        ("ESS bulk", 0.82, "1487"),
        ("divergences", 0.10, "0"),
    ]
    for idx, (label, ratio, value) in enumerate(stats):
        x = 136 + idx * 148
        vertical_meter(draw, x, 318, 140, ratio, accent)
        draw.text((x - 6, 470), label, font=FONT_SMALL, fill=(221, 218, 234))
        draw.text((x - 2, 500), value, font=FONT_MONO_SMALL, fill=(*accent, 255))
    panel(draw, 664, 208, 524, 334, accent)
    draw.text((694, 240), "LOO-CV and diagnostics text", font=FONT_PANEL, fill=(245, 244, 251))
    loo_rows = [
        ("elpd_loo", "-812.4"),
        ("p_loo", "37.2"),
        ("warning", "False"),
    ]
    for idx, (label, value) in enumerate(loo_rows):
        y = 314 + idx * 58
        rounded(draw, (694, y, 1146, y + 38), rgba(accent, 0.06), outline=rgba(accent, 0.68), radius=18, width=2)
        draw.text((714, y + 10), label, font=FONT_MONO_SMALL, fill=(221, 218, 234))
        draw.text((936, y + 10), value, font=FONT_MONO_SMALL, fill=(*accent, 255))
    draw.text((694, 492), "the service measures whether the posterior story is stable enough to trust", font=FONT_BODY, fill=(221, 218, 234))


def scene_laplace(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    draw.text((122, 240), "Fallback path still carries Bayesian structure", font=FONT_PANEL, fill=(245, 244, 251))
    steps = [
        "search lambda grid",
        "pick best GCV score",
        "solve MAP coefficients",
        "build Hessian covariance",
        "derive credible ranges",
    ]
    for idx, step in enumerate(steps):
        x = 126 + idx * 206
        color = rgb(SLATE if idx < 3 else ORCHID)
        rounded(draw, (x, 336, x + 176, 440), rgba(color, 0.08), outline=rgba(color, 0.76), radius=24, width=2)
        font, lines = fit_text_block(draw, step, 144, 3, 20, 16)
        draw_lines(draw, x + 16, 362, lines, font, (245, 244, 251), line_gap=2)
    draw.text((244, 488), "if MCMC is unavailable, Bashira still returns uncertainty-aware effects instead of a bare point estimate", font=FONT_BODY, fill=(221, 218, 234))


def scene_drivers(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 1096, 334, accent)
    draw.text((122, 240), "Posterior effects become ranked drivers", font=FONT_PANEL, fill=(245, 244, 251))
    headers = ["feature", "mean days", "credible interval", "inclusion"]
    xs = [132, 470, 658, 988]
    for x, header in zip(xs, headers):
        draw.text((x, 294), header, font=FONT_MONO_SMALL, fill=(177, 170, 195))
    for idx, (feature, mean, low, high, inc) in enumerate(DRIVER_ROWS):
        y = 332 + idx * 48
        rounded(draw, (124, y, 1150, y + 36), rgba(accent, 0.06), outline=rgba(accent, 0.68), radius=18, width=2)
        draw.text((144, y + 10), feature, font=FONT_MONO_SMALL, fill=(245, 244, 251))
        draw.text((470, y + 10), f"{mean:+.1f}", font=FONT_MONO_SMALL, fill=(*accent, 255))
        draw.text((658, y + 10), f"[{low:.1f}, {high:.1f}]", font=FONT_MONO_SMALL, fill=(221, 218, 234))
        draw.text((988, y + 10), f"{inc:.2f}", font=FONT_MONO_SMALL, fill=(221, 218, 234))
    draw.text((310, 522), "credible ranges tell the team how wide the believable effect window is, not just the center point", font=FONT_BODY, fill=(221, 218, 234))


def scene_payload(draw: ImageDraw.ImageDraw, progress: float, accent):
    panel(draw, 92, 208, 530, 334, accent)
    draw.text((122, 240), "Bayesian payload summary", font=FONT_PANEL, fill=(245, 244, 251))
    rows = [
        ("rows", "2,416"),
        ("features", "58"),
        ("top_driver", "schedule_pressure"),
        ("counterfactual_options", "6"),
    ]
    for idx, (label, value) in enumerate(rows):
        y = 304 + idx * 54
        rounded(draw, (124, y, 586, y + 36), rgba(accent, 0.05), outline=rgba(accent, 0.64), radius=18, width=2)
        draw.text((146, y + 10), label, font=FONT_MONO_SMALL, fill=(221, 218, 234))
        draw.text((356, y + 10), value, font=FONT_MONO_SMALL, fill=(*accent, 255))
    panel(draw, 664, 208, 524, 334, accent)
    draw.text((694, 240), "What the client-facing scenario gets", font=FONT_PANEL, fill=(245, 244, 251))
    bullets = [
        "ranked drivers with uncertainty",
        "root-cause summary for each row",
        "group-aware scenario pressure",
        "counterfactual options for action",
    ]
    for idx, bullet in enumerate(bullets):
        y = 322 + idx * 52
        draw.ellipse((694, y + 8, 710, y + 24), fill=(*accent, 255))
        font, lines = fit_text_block(draw, bullet, 430, 2, 20, 17)
        draw_lines(draw, 724, y, lines, font, (221, 218, 234), line_gap=2)


DRAWERS = [
    scene_bayesian,
    scene_prepare,
    scene_chains,
    scene_hierarchy,
    scene_diag,
    scene_laplace,
    scene_drivers,
    scene_payload,
]


def render_frame(scene_index: int, local_progress: float) -> np.ndarray:
    accent = rgb(SCENES[scene_index]["accent"])
    image = Image.new("RGB", (WIDTH, HEIGHT), (7, 8, 20))
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

    combined_audio = run_dir / "bayesian_counterfactuals_lesson.wav"
    scene_durations = concat_wavs(audio_parts, combined_audio, SCENE_GAP_SECONDS)
    silent_video = run_dir / "bayesian_counterfactuals_lesson_silent.mp4"
    build_silent_video(scene_durations, silent_video)
    mux_video(silent_video, combined_audio, OUTPUT_FILE)
    print(f"Generated approval video: {OUTPUT_FILE}")
    print(f"Approx duration: {sum(scene_durations):.1f} seconds")


if __name__ == "__main__":
    main()

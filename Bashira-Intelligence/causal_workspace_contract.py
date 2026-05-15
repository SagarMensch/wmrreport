"""
Workspace contract helpers for Causal Command.

The frontend should read stable product-safe language regardless of whether the
deep analysis is currently powered by a legacy adapter or a future Stan service.
"""

from __future__ import annotations

import datetime as dt
from typing import Any


def build_analysis_status(
    deep_status: str,
    refresh_in_progress: bool,
    started_at: dt.datetime | None,
    completed_at: dt.datetime | None,
) -> dict[str, Any]:
    if deep_status == "ok":
        headline = "Operational deck ready with Bayesian counterfactuals"
        detail = "Live SQL joins, CPU decision ranking, and posterior counterfactual summaries are all available."
        mode = "cpu_plus_bayesian"
    elif deep_status in {"warming", "pending"} or refresh_in_progress:
        headline = "Operational deck ready; Bayesian summaries refreshing"
        detail = "Live SQL joins and CPU decision ranking are ready now. Posterior counterfactual summaries are refreshing in the background."
        mode = "cpu_operational_only"
    else:
        headline = "Operational deck ready; posterior layer unavailable"
        detail = "Live SQL joins and CPU decision ranking are active. Posterior counterfactual summaries are currently unavailable, so the tab is using the governed CPU layer only."
        mode = "cpu_operational_only"

    return {
        "headline": headline,
        "detail": detail,
        "mode": mode,
        "cache_age_seconds": 0,
        "refresh_in_progress": refresh_in_progress,
        "last_bayesian_started_at": started_at.isoformat() if started_at else None,
        "last_bayesian_completed_at": completed_at.isoformat() if completed_at else None,
    }


def build_data_health(
    *,
    live_wells: int,
    historical_wells: int,
    mean_progress_pct: float,
    delayed_wells: int,
    bayesian_runtime: str,
    analysis_mode: str,
    cpu_model_status: str,
) -> dict[str, Any]:
    return {
        "live_wells": live_wells,
        "historical_wells": historical_wells,
        "mean_progress_pct": mean_progress_pct,
        "delayed_wells": delayed_wells,
        "bayesian_runtime": bayesian_runtime,
        "analysis_mode": analysis_mode,
        "cpu_model_status": cpu_model_status,
    }

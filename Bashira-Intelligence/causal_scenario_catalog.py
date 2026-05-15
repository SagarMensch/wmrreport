"""
Causal Command scenario catalog.

This module defines the governed intervention vocabulary that the product
should expose, independent of whichever model engine is providing uplift
estimates underneath.
"""

from __future__ import annotations

from typing import Any


DEFAULT_SCENARIO_CATALOG: dict[str, dict[str, Any]] = {
    "peer_pace_recovery": {
        "label": "Recover to Peer Execution Pace",
        "description": "Lift execution pace toward comparable peers at the same stage and pressure band.",
    },
    "higher_efficiency_rig": {
        "label": "Reassign Higher-Efficiency Rig",
        "description": "Test whether a stronger comparable rig profile would reduce baseline delay pressure.",
    },
    "expedite_material_readiness": {
        "label": "Expedite Material Readiness",
        "description": "Reduce material lead-time drag and estimate the resulting time recovery.",
    },
    "decongest_parallel_workfronts": {
        "label": "Decongest Parallel Workfronts",
        "description": "Release workfront congestion so the well can move at a cleaner execution pace.",
    },
    "reduce_overdue_daily_backlog": {
        "label": "Reduce Overdue Daily Backlog",
        "description": "Close overdue unfinished daily tasks to reduce near-term execution drag.",
    },
    "lift_daily_completion_rate": {
        "label": "Lift Daily Task Completion Rate",
        "description": "Improve daily task close-out performance against comparable execution peers.",
    },
    "improve_linked_productivity": {
        "label": "Improve Linked Productivity",
        "description": "Raise linked productivity signals toward peer performance to improve delivery pace.",
    },
}


def merge_scenario_catalog(existing: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """
    Merge the current model-emitted scenario catalog with the governed default
    catalog so the frontend always receives stable labels and descriptions.
    """

    merged = {key: value.copy() for key, value in DEFAULT_SCENARIO_CATALOG.items()}
    if not existing:
        return merged

    for code, payload in existing.items():
        if not isinstance(payload, dict):
            continue
        entry = merged.setdefault(code, {})
        entry.update(payload)
        entry.setdefault("label", code.replace("_", " ").title())
        entry.setdefault("description", "Governed operational intervention scenario.")
    return merged

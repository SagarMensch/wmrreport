"""
Confidence helpers for Causal Command.

These helpers provide a first-pass confidence layer that can later be extended
with posterior interval width, integrity penalties, and support pooling logic.
"""

from __future__ import annotations


def compose_confidence_label(
    support_cases: int,
    signal_quality: str,
    delta_days: float,
    integrity_penalty: float = 0.0,
) -> str:
    if delta_days >= 0:
        return "Weak Support"

    support_score = 0
    if support_cases >= 25:
        support_score = 2
    elif support_cases >= 10:
        support_score = 1

    quality_score = {"high": 2, "medium": 1, "limited": 0}.get(signal_quality, 0)
    total = support_score + quality_score - int(round(max(integrity_penalty, 0.0)))

    if total >= 4:
        return "High"
    if total >= 2:
        return "Moderate"
    if total >= 1:
        return "Cautious"
    return "Weak Support"


def compose_action_status(support_cases: int, delta_days: float) -> str:
    if delta_days <= -5 and support_cases >= 10:
        return "Act Now"
    if delta_days < 0 and support_cases >= 5:
        return "Candidate"
    return "Observe"

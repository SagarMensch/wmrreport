"""
Question Classifier - routes questions to sql_only or predictive mode.

This classifier is intentionally conservative. Business KPI questions that can
be answered deterministically from SQL should stay on the SQL path. Predictive
mode is reserved for explicit forecasting, root-cause, intervention, or
counterfactual requests that genuinely need Julia/ML services.
"""

import logging
import re

log = logging.getLogger("bashira.classifier")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


SQL_ONLY_OVERRIDES = [
    # Deterministic KPI metric: current-quarter revenue forecast proxy.
    re.compile(
        r"\b(what is|show|give me)?\s*(the\s+)?(forecasted|projected)\s+revenue\s+for\s+(this|the current)\s+quarter\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(current|this)\s+quarter\s+revenue\s+forecast\b",
        re.IGNORECASE,
    ),
    # Deterministic KPI metric: annual target status from Revenue YTD vs full-year plan.
    re.compile(
        r"\b(are we\s+)?on\s+track\s+to\s+meet\s+(our\s+)?(annual|yearly)\s+targets?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(annual|yearly)\s+target\s+status\b",
        re.IGNORECASE,
    ),
    # Keep safety/incident questions on the SQL/limitation path rather than the predictive root-cause path.
    re.compile(
        r"\b(trir|incident(s)?|near[- ]?miss|permit\s+to\s+work|ptw|safety\s+violations?|safety\s+training|audit|inspection|corrective\s+actions?)\b",
        re.IGNORECASE,
    ),
    # Performance KPI trend/deviation questions are deterministic SQL or clarification-first.
    re.compile(
        r"\b(trend\s+analysis\s+of\s+performance\s+kpis?|performance\s+kpi\s+trend|kpi\s+trend\s+analysis)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(which\s+kpis?\s+are\s+deviating\s+from\s+thresholds?\s+today|kpis?\s+deviating\s+from\s+thresholds?)\b",
        re.IGNORECASE,
    ),
    # These require proxy/limitation handling before any predictive branch.
    re.compile(
        r"\b(cost\s+overrun\s+forecast|forecast\s+cost\s+overrun)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(scenarios?\s+improve\s+project\s+margin|improve\s+project\s+margin)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhat\s+happens?\s+if\s+manpower\s+increases?\s+by\s+\d+%?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(top\s*10\s+risks?\s+impacting\s+delivery|risks?\s+impacting\s+delivery)\b",
        re.IGNORECASE,
    ),
]


PREDICTIVE_PATTERNS = [
    # Forecasting that genuinely implies a model/scenario request.
    re.compile(r"\b(cash\s+flow\s+forecast|cost\s+overrun\s+forecast|forecast\s+completion\s+date)\b", re.IGNORECASE),
    re.compile(r"\b(baseline\s+vs\s+forecast|forecast\s+scenario)\b", re.IGNORECASE),
    # Root cause / drivers.
    re.compile(r"\b(key\s+drivers?|root\s+causes?|what\s+(is|are)\s+(the\s+)?(key\s+drivers?|root\s+causes?)|what\s+(is\s+)?caus(ing|es?)|driv(ers?|ing)\s+of\s+delay)\b", re.IGNORECASE),
    # Probability / likelihood.
    re.compile(r"\b(probability\s+of\s+delay|likelihood|risk\s+score|delay\s+probability)\b", re.IGNORECASE),
    # Counterfactual / scenario.
    re.compile(r"\b(scenario|what\s+(if|happens?\s+if)|counterfactual|simula(te|tion))\b", re.IGNORECASE),
    re.compile(r"\b(improve\s+(project\s+)?margin|increase.*by\s+\d+%)\b", re.IGNORECASE),
    # Trend analysis.
    re.compile(r"\b(trend\s+analysis|performance\s+trend|erosion\s+trend|kpi\s+trend)\b", re.IGNORECASE),
    # Intervention / action recommendations.
    re.compile(r"\b(immediate\s+intervention|action.*today|management\s+(should|take|action))\b", re.IGNORECASE),
    re.compile(r"\b(need\s+immediate|intervention\s+ranking|priority\s+action)\b", re.IGNORECASE),
    # Predictive insights from past data.
    re.compile(r"\b(predictive\s+insights?|hidden\s+patterns?|past\s+project.*insights?)\b", re.IGNORECASE),
    re.compile(r"\b(actions?\s+should\s+management\s+take\s+today|management\s+take\s+today)\b", re.IGNORECASE),
]


def classify_question(question: str) -> str:
    """
    Classify a question as 'sql_only' or 'predictive'.

    sql_only:
        Deterministic KPI/aggregation/drilldown questions answerable from the
        SQL path.

    predictive:
        Questions that explicitly require forecasting models, root-cause
        analysis, intervention ranking, or counterfactual simulation.
    """
    text = question.strip()
    normalized = _normalize(text)

    for pattern in SQL_ONLY_OVERRIDES:
        if pattern.search(normalized):
            log.info("   * CLASSIFIER: sql_only override matched")
            return "sql_only"

    for pattern in PREDICTIVE_PATTERNS:
        if pattern.search(normalized):
            log.info("   * CLASSIFIER: predictive match - pattern: %s", pattern.pattern[:60])
            return "predictive"

    log.info("   * CLASSIFIER: sql_only (no predictive patterns matched)")
    return "sql_only"


if __name__ == "__main__":
    test_questions = [
        # sql_only overrides
        "What is the forecasted revenue for this quarter?",
        "Are we on track to meet annual targets?",
        "What is the annual target status?",
        # predictive
        "What are the key drivers of delay?",
        "What is the probability of delay for each project?",
        "What scenarios improve project margin?",
        "What happens if manpower increases by 10%?",
        "Which projects need immediate intervention?",
        "What actions should management take today?",
        "What is the cost overrun forecast?",
        "What is the forecast completion date vs baseline?",
        # sql_only defaults
        "How many wells are there?",
        "Which wells are in Nimr cluster?",
        "What is total manpower deployed?",
        "Show cost vs budget by project",
        "What is the SPI for each project?",
        "Which POs are overdue?",
        "What is equipment utilization rate?",
        "How many safety incidents this month?",
        "What is current profit margin per project?",
        "Show me all Marmul wells with progress below 50%",
    ]

    for question in test_questions:
        mode = classify_question(question)
        print(f"[{mode:10s}] {question}")

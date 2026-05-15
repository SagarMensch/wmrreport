"""
Chart Agent — Bloomberg-level advanced visualization engine
==========================================================
NOT just a chart type selector — this is a full decision engine that:

1. Recommends optimal chart type with axis configuration
2. Generates DRILL-DOWN queries (click a bar → go deeper)
3. Produces chart config for the frontend rendering engine
4. Supports hierarchical data exploration (Cluster → Wells → Well Detail)

Designed for a Decision Studio UI where every chart is clickable
and leads to deeper data exploration — alien-tech tier.
"""

import dspy
import logging
from dataclasses import dataclass, field

from config import settings

log = logging.getLogger("bashira.chart_agent")


# ── Data Classes ─────────────────────────────────────────────────────────

ALLOWED_CHARTS = [
    "bar", "line", "horizontal_bar", "scatter", "data_table",
    "area", "donut", "stacked_bar", "grouped_bar", "heatmap", "gauge",
    "treemap", "funnel", "waterfall", "radar", "kpi_card",
    "3d_scatter", "3d_bar", "3d_surface", "3d_kpi", "glass_kpi"
]

DRILL_DOWN_TEMPLATES = {
    # When user sees aggregated data → drill into individual items
    "cluster_to_wells": {
        "trigger": "Click on a cluster bar",
        "template": "SELECT well_name_after_spud, over_all_progress_percentages * 100 AS progress_pct, rig_no, spud_date FROM WellMonitoringReport_Latest WHERE Cluster = '{clicked_value}' ORDER BY progress_pct DESC",
        "chart_type": "horizontal_bar",
    },
    "well_to_detail": {
        "trigger": "Click on a well name",
        "template": "SELECT * FROM WellMonitoringReport_Latest WHERE well_name_after_spud = '{clicked_value}'",
        "chart_type": "data_table",
    },
    "rig_to_wells": {
        "trigger": "Click on a rig",
        "template": "SELECT well_name_after_spud, over_all_progress_percentages * 100 AS progress_pct, Cluster, well_status FROM WellMonitoringReport_Latest WHERE rig_no = '{clicked_value}' ORDER BY progress_pct DESC",
        "chart_type": "horizontal_bar",
    },
    "ph_to_tasks": {
        "trigger": "Click on a project holder",
        "template": "SELECT * FROM PH_PRODUCTIVITY_WEEKLY_REPORT WHERE [PH Name] = '{clicked_value}'",
        "chart_type": "data_table",
    },
}


@dataclass
class DrillDownAction:
    """Defines what happens when user clicks on a chart element."""
    level: int              # 1 = first drill, 2 = second drill, etc.
    trigger_column: str     # which column value triggers the drill
    label: str              # human-readable label for the action
    sql_template: str       # SQL with {clicked_value} placeholder
    chart_type: str         # chart type for drill-down result
    description: str        # what this drill-down shows


@dataclass
class ChartConfig:
    """Complete chart configuration for the frontend renderer."""
    # Primary chart
    chart_type: str
    title: str
    subtitle: str = ""

    # Axis mapping
    x_axis: str = ""
    y_axis: str = ""
    x_label: str = ""
    y_label: str = ""

    # Multi-series support
    series: list[str] = field(default_factory=list)
    group_by: str = ""

    # Visual options
    color_scheme: str = "bloomberg_dark"  # bloomberg_dark, palantir, aurora, neon
    show_values: bool = True
    show_legend: bool = True
    animate: bool = True
    gradient: bool = True
    glass_effect: bool = True

    # Drill-down actions
    drill_downs: list[DrillDownAction] = field(default_factory=list)

    # KPI cards (for gauge/kpi_card types)
    kpi_value: str = ""
    kpi_unit: str = ""
    kpi_trend: str = ""  # up, down, stable

    reasoning: str = ""


# ── DSPy Signature ───────────────────────────────────────────────────────

class ChartSignature(dspy.Signature):
    """You are a Palantir Foundry / Bloomberg Terminal-level data visualization expert 
    working for an oil & gas well monitoring company. You MUST analyze column names 
    and data shape to recommend the most analytically impactful visualization.

    CRITICAL COLUMN TYPE RULES:
    - Columns ending in _id, _uid, _no (e.g., pdo_well_id, scr_no, crew_uid): 
      → These are IDENTIFIERS, never suitable for numeric axes
    - Columns like well_name, cluster, well_type, rig_no, contractor, status:
      → These are CATEGORICAL labels for axis labeling
    - Columns with progress, pct, percent, completion:
      → These are PERCENTAGES (0-1 scale or 0-100 scale)
    - Columns with count, total, sum, avg, revenue, cost, budget:
      → These are NUMERIC VALUES suitable for bar heights/values
    - Columns with date, time, week, month, year:
      → These are TIME DIMENSIONS for line/area charts

    CHART SELECTION RULES:
    1. Single row + single value column → glass_kpi
    2. Single row + multiple value columns (e.g., planned vs actual) → bar (transposed)
    3. Count by category (e.g., wells per cluster) → donut (≤8 items) or horizontal_bar
    4. Rankings, top/bottom → horizontal_bar
    5. Time series → area or line
    6. Plan vs Actual comparisons → grouped_bar
    7. Progress/completion data → horizontal_bar with progress coloring
    8. Many rows (>50) or many columns (>5) → data_table
    9. ALL text columns with NO numeric values → data_table (ALWAYS)
    10. Distribution/proportion → donut

    EXAMPLES:
    - "Compare nimr cluster planned vs actual" → columns: cluster_name, well_count, 
      total_planned_value, total_actual_value → chart_type: bar (1 row = transposed bar)
    - "How many wells in each cluster?" → columns: Cluster, well_count 
      → chart_type: donut (count by category)
    - "Which wells have zero progress?" → columns: pdo_well_id, well_name, Cluster 
      → chart_type: data_table (all text, no numeric)
    - "Show rig progress comparison" → columns: rig_no, avg_progress 
      → chart_type: horizontal_bar
    - "What is the average progress?" → columns: avg_progress (1 row, 1 value) 
      → chart_type: glass_kpi
    - "Show weekly progress trend" → columns: week, avg_progress 
      → chart_type: area

    NEVER put pdo_well_id, scr_no, or any _id column on a numeric axis.
    ALWAYS default to data_table if unsure — bad chart is worse than good table.
    """

    user_question = dspy.InputField()
    sql_query = dspy.InputField()
    result_columns = dspy.InputField(desc="Comma-separated column names from SQL result.")
    row_count = dspy.InputField()

    chart_type = dspy.OutputField(
        desc="One of: bar, line, horizontal_bar, grouped_bar, scatter, area, donut, "
             "stacked_bar, heatmap, gauge, treemap, funnel, waterfall, "
             "radar, kpi_card, data_table, 3d_scatter, 3d_bar, 3d_kpi, glass_kpi. "
             "If ALL columns are text/identifiers with NO numeric values, MUST return data_table."
    )
    x_axis = dspy.OutputField(desc="Column for X/category axis. Must be a categorical/label column, NEVER an _id column.")
    y_axis = dspy.OutputField(desc="Column for Y/value axis. Must be a numeric value column like count, total, progress.")
    title = dspy.OutputField(desc="Professional chart title (max 8 words).")
    color_scheme = dspy.OutputField(
        desc="One of: bloomberg_dark, palantir, aurora, neon. "
             "bloomberg_dark for financial, palantir for operational, "
             "aurora for progress, neon for creative."
    )


# ── Chart Agent ──────────────────────────────────────────────────────────

class ChartAgent(dspy.Module):
    """
    Bloomberg-level chart recommendation engine with drill-down generation.
    
    Not just "pick a chart" — this agent:
    1. Analyzes query semantics + data shape
    2. Picks the most impactful visualization
    3. Generates drill-down actions for interactive exploration
    4. Configures axis, series, colors, animations
    """

    def __init__(self, api_key: str = None):
        super().__init__()
        # Use provided key or fallback to settings
        key = api_key or settings.GROQ_API_KEY_2 or settings.GROQ_API_KEY
        self.recommend = dspy.ChainOfThought(ChartSignature)

    def forward(
        self,
        user_question: str,
        sql_query: str,
        result_columns: list[str],
        row_count: int,
    ) -> ChartConfig:
        """Generate complete chart configuration with drill-down actions."""

        try:
            pred = self.recommend(
                user_question=user_question,
                sql_query=sql_query,
                result_columns=", ".join(result_columns),
                row_count=str(row_count),
            )

            chart_type = pred.chart_type.strip().lower()
            if chart_type not in ALLOWED_CHARTS:
                chart_type = self._heuristic_chart(
                    user_question, result_columns, row_count
                )

            color_scheme = getattr(pred, 'color_scheme', 'bloomberg_dark')
            valid_schemes = {'bloomberg_dark', 'palantir', 'aurora', 'neon'}
            if color_scheme not in valid_schemes:
                color_scheme = 'bloomberg_dark'

            x_axis = getattr(pred, 'x_axis', result_columns[0] if result_columns else '')
            y_axis = getattr(pred, 'y_axis', result_columns[1] if len(result_columns) > 1 else '')
            title = getattr(pred, 'title', 'Query Results')

        except Exception as e:
            log.warning("Chart DSPy failed: %s. Using heuristics.", e)
            chart_type = self._heuristic_chart(user_question, result_columns, row_count)
            x_axis = result_columns[0] if result_columns else ''
            y_axis = result_columns[1] if len(result_columns) > 1 else ''
            title = 'Query Results'
            color_scheme = 'bloomberg_dark'

        # ── Generate drill-down actions ──────────────────────────────────
        drill_downs = self._generate_drill_downs(
            user_question, sql_query, result_columns, chart_type
        )

        # ── Detect KPI scenarios — ONLY for truly single-value results ──
        kpi_value = ""
        kpi_unit = ""
        
        # Only force glass_kpi for genuinely single-value results (1-2 columns)
        # Multi-metric rows (e.g., planned vs actual with 5 columns) should NOT be KPI
        if row_count <= 1 and len(result_columns) <= 2:
            chart_type = "glass_kpi"
            if row_count == 1 and result_columns:
                kpi_value = "DATA"
            elif row_count == 0:
                kpi_value = "0"
            kpi_unit = self._guess_unit(result_columns)
        
        # Ensure it never falls back to an empty chart if data exists
        if chart_type not in ALLOWED_CHARTS:
            chart_type = "3d_bar" if len(result_columns) >= 2 else "glass_kpi"

        # ── Multi-series detection ───────────────────────────────────────
        series = []
        if len(result_columns) > 2:
            series = [c for c in result_columns[1:] if c != x_axis]

        return ChartConfig(
            chart_type=chart_type,
            title=title,
            subtitle=f"Based on {row_count} records",
            x_axis=x_axis,
            y_axis=y_axis,
            x_label=self._humanize(x_axis),
            y_label=self._humanize(y_axis),
            series=series,
            color_scheme=color_scheme,
            show_values=row_count <= 20,
            show_legend=len(series) > 0,
            animate=True,
            gradient=True,
            glass_effect=True,
            drill_downs=drill_downs,
            kpi_value=kpi_value,
            kpi_unit=kpi_unit,
            reasoning=getattr(pred, 'rationale', '') if 'pred' in dir() else '',
        )

    def _generate_drill_downs(
        self,
        question: str,
        sql: str,
        columns: list[str],
        chart_type: str,
    ) -> list[DrillDownAction]:
        """
        Generate drill-down actions based on the data context.
        
        Hierarchy:
          Level 0: Aggregated view (e.g., count per cluster)
          Level 1: Click cluster → see wells in that cluster
          Level 2: Click well → see full well detail
        """
        drill_downs = []
        q_lower = question.lower()
        sql_lower = sql.lower()

        # ── Cluster-level → Well-level drill ─────────────────────────────
        cluster_cols = [c for c in columns if 'cluster' in c.lower()]
        if cluster_cols:
            drill_downs.append(DrillDownAction(
                level=1,
                trigger_column=cluster_cols[0],
                label="Explore wells in this cluster",
                sql_template=(
                    "SELECT well_name_after_spud, "
                    "(over_all_progress_percentages * 100) AS progress_pct, "
                    "rig_no, well_status, spud_date "
                    "FROM WellMonitoringReport_Latest "
                    "WHERE Cluster = '{clicked_value}' "
                    "ORDER BY progress_pct DESC"
                ),
                chart_type="horizontal_bar",
                description="Shows all wells in the selected cluster with progress",
            ))

        # ── Well-name → Full detail drill ────────────────────────────────
        well_cols = [c for c in columns if 'well' in c.lower() and 'name' in c.lower()]
        if well_cols or 'well_name_after_spud' in sql_lower:
            trigger = well_cols[0] if well_cols else 'well_name_after_spud'
            drill_downs.append(DrillDownAction(
                level=2,
                trigger_column=trigger,
                label="View complete well profile",
                sql_template=(
                    "SELECT well_name_after_spud, Cluster, rig_no, "
                    "well_status, spud_date, scr_no, "
                    "(over_all_progress_percentages * 100) AS progress_pct, "
                    "(cum_progress_for_this_week * 100) AS weekly_progress, "
                    "contractor, operator_rep "
                    "FROM WellMonitoringReport_Latest "
                    "WHERE well_name_after_spud = '{clicked_value}'"
                ),
                chart_type="data_table",
                description="Full profile of the selected well",
            ))

        # ── Rig-level drill ──────────────────────────────────────────────
        rig_cols = [c for c in columns if 'rig' in c.lower()]
        if rig_cols:
            drill_downs.append(DrillDownAction(
                level=1,
                trigger_column=rig_cols[0],
                label="View wells on this rig",
                sql_template=(
                    "SELECT well_name_after_spud, "
                    "(over_all_progress_percentages * 100) AS progress_pct, "
                    "Cluster, well_status "
                    "FROM WellMonitoringReport_Latest "
                    "WHERE rig_no = '{clicked_value}' "
                    "ORDER BY progress_pct DESC"
                ),
                chart_type="horizontal_bar",
                description="All wells assigned to the selected rig",
            ))

        # ── Project Holder drill ─────────────────────────────────────────
        ph_cols = [c for c in columns if 'ph' in c.lower() and 'name' in c.lower()]
        if ph_cols:
            drill_downs.append(DrillDownAction(
                level=1,
                trigger_column=ph_cols[0],
                label="View project holder details",
                sql_template=(
                    "SELECT * FROM PH_PRODUCTIVITY_WEEKLY_REPORT "
                    "WHERE [PH Name] = '{clicked_value}'"
                ),
                chart_type="radar",
                description="Complete productivity profile for the selected PH",
            ))

        # ── Revenue drill ────────────────────────────────────────────────
        rev_cols = [c for c in columns if 'revenue' in c.lower()]
        if rev_cols:
            drill_downs.append(DrillDownAction(
                level=1,
                trigger_column=columns[0],
                label="View revenue breakdown",
                sql_template=(
                    "SELECT * FROM Job_Progress_Report_GB "
                    "WHERE [Well Name / Project Name] = '{clicked_value}'"
                ),
                chart_type="waterfall",
                description="Detailed revenue breakdown for the selected entity",
            ))

        return drill_downs

    @staticmethod
    def _heuristic_chart(question: str, columns: list[str], row_count: int) -> str:
        """
        Intelligent chart selection - Think like Bloomberg Terminal.
        Analyze DATA structure first, then choose BEST visualization.
        
        Philosophy:
        - Don't force one chart type - let data dictate
        - Every chart should be instantly readable
        - Use advanced 3D effects sparingly but powerfully
        """
        q = question.lower()
        cols_lower = [c.lower() for c in columns]
        
        # === ANALYZE DATA STRUCTURE ===
        has_count = any('count' in c or 'wells' in c or 'total' in c for c in cols_lower)
        has_plan_actual = any('plan' in c and 'actual' in q for c in cols_lower)
        has_progress = any('progress' in c or 'pct' in c or 'percent' in c for c in cols_lower)
        is_single_value = row_count <= 1
        is_many_categories = row_count > 15
        has_time = any('week' in c or 'month' in c or 'date' in c or 'time' in c for c in cols_lower)
        
        # ID/text column patterns — these are NOT chartable on numeric axes
        id_patterns = {'pdo_well_id', 'well_id', 'id', 'uid', 'crew_uid', 'well_location',
                       'project_id', 'employee_id', 'scr_no'}
        name_patterns = {'well_name', 'project_name', 'ph_name', 'crew_name', 'name',
                         'description', 'cluster', 'well_type', 'category', 'rig_no',
                         'well_name_after_spud', 'contractor', 'operator', 'status',
                         'risk_tier', 'well_status'}
        
        # Detect if there are ANY numeric-axis-worthy columns
        has_numeric = any(
            c not in id_patterns and c not in name_patterns
            and not c.endswith('_id') and not c.endswith('_uid')
            and ('count' in c or 'total' in c or 'progress' in c or 'pct' in c
                 or 'percent' in c or 'score' in c or 'avg' in c or 'sum' in c
                 or 'revenue' in c or 'cost' in c or 'budget' in c or 'days' in c
                 or 'duration' in c or 'weeks' in c or 'number' in c or 'amount' in c)
            for c in cols_lower
        )
        
        # ═══ CRITICAL: If ALL columns are text/identifiers, ALWAYS table ═══
        if not has_numeric and not has_count and not has_progress:
            return "data_table"
        
        # === INTELLIGENT SELECTION ===
        
        # Single metric/card → sleek 3D KPI
        if is_single_value and len(columns) <= 2:
            return "glass_kpi"
        
        # "How many X in each Y" (count by category) → Treemap or Donut
        if has_count and row_count >= 3:
            return "treemap" if row_count > 8 else "donut"
        
        # Rankings (top/bottom) → Horizontal bars with animation
        if any(kw in q for kw in ['rank', 'top', 'bottom', 'best', 'worst', 'highest', 'lowest']):
            return "horizontal_bar"
        
        # Time series → Area
        if has_time or any(kw in q for kw in ['trend', 'over time', 'weekly', 'monthly', 'timeline']):
            return "area"
        
        # Progress/percentage data → 3D bars for visual impact
        if has_progress:
            return "gauge" if row_count <= 5 else "3d_bar"
        
        # Comparison (A vs B) → Grouped bars
        if has_plan_actual or any(kw in q for kw in ['compare', 'vs', 'versus', 'actual', 'plan']):
            return "grouped_bar"
        
        # Many categories → Data table (better than illegible chart)
        if is_many_categories:
            return "data_table" if row_count > 50 else "horizontal_bar"
        
        # Distribution → Donut/Pie
        if any(kw in q for kw in ['distribution', 'proportion', 'share', 'breakdown']):
            return "donut"
        
        # Correlation → Scatter
        if any(kw in q for kw in ['correlation', 'relationship', 'vs']):
            return "scatter"
        
        # Default: Clean data table for large datasets, bar for small
        if row_count > 50 or len(columns) > 5:
            return "data_table"
        
        # Fallback: horizontal_bar is the most universally readable chart
        return "horizontal_bar"

    @staticmethod
    def _humanize(col_name: str) -> str:
        """Convert column_name to Human Name."""
        return col_name.replace("_", " ").replace("[", "").replace("]", "").title()

    @staticmethod
    def _guess_unit(columns: list[str]) -> str:
        """Guess the unit for KPI display."""
        for c in columns:
            cl = c.lower()
            if 'pct' in cl or 'percent' in cl or 'progress' in cl:
                return "%"
            if 'revenue' in cl or 'cost' in cl or 'budget' in cl:
                return "OMR"
            if 'count' in cl or 'total' in cl:
                return ""
            if 'days' in cl or 'duration' in cl:
                return "days"
        return ""

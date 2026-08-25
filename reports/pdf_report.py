"""Builds the workforce simulation PDF report with ReportLab.

Pure Python, in-memory only — no FastAPI dependency and no disk writes (the
`outputs/` directory is for CSV artifacts only, per CLAUDE.md). All text here
is already translated client-side before it reaches this module (see
`ReportPdfInput` in api_models.py); this file only lays it out.

Replaces the old client-side html2canvas/html2pdf.js flow, which screenshotted
the DOM and faked pagination — that approach produced blank charts, missing
page margins on overflow, and a duplicated-content bug from its page-break
spacer-injection hack. ReportLab's flowable model (SimpleDocTemplate +
KeepTogether) handles pagination and margins correctly and natively instead.

Charts are drawn natively with ReportLab's own charting module
(reportlab.graphics.charts) from the same raw data the dashboard's Chart.js
charts use — not a captured screenshot of the on-screen canvas. A canvas's
pixel size/aspect ratio depends on the browser's layout at the moment of
capture (window width, sidebar collapsed or not), which made captured charts
come out inconsistently sized; drawing them from data instead means they're
always sized correctly for the page, every time.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Plain hex colors, matching the values already used for the KPI cards in
# styles.css (kept in sync manually — there is no shared source of truth
# between CSS custom properties and this Python module).
COLOR_NAVY = colors.HexColor("#0A1628")
COLOR_TEAL = colors.HexColor("#0CC8A8")
COLOR_AMBER = colors.HexColor("#E8A04A")
COLOR_GREEN = colors.HexColor("#2DD4A0")
COLOR_RED = colors.HexColor("#FF6B6B")
COLOR_POSITIVE_TEXT = colors.HexColor("#1a7f5a")
COLOR_NEGATIVE_TEXT = colors.HexColor("#b91d1d")
COLOR_MUTED = colors.HexColor("#666666")
COLOR_BORDER = colors.HexColor("#eaeaea")
COLOR_CARD_BG = colors.HexColor("#fafafa")

_KPI_ACCENTS = {
    "default": COLOR_NAVY,
    "teal": COLOR_TEAL,
    "amber": COLOR_AMBER,
    "green": COLOR_GREEN,
    "red": COLOR_RED,
}

# Chart series colors, matching the exact rgba() values the dashboard's
# Chart.js charts use (renderComparisonChart/renderSubjectChart/
# renderRiskRankingChart in app.js) — kept in sync manually, same as the KPI
# accent colors above.
_CHART_COMPARISON_COLORS = [
    colors.Color(35 / 255, 86 / 255, 160 / 255, alpha=0.85),
    colors.Color(15 / 255, 124 / 255, 124 / 255, alpha=0.85),
]
_CHART_SUBJECT_COLORS = [
    colors.Color(185 / 255, 32 / 255, 32 / 255, alpha=0.85),
    colors.Color(232 / 255, 160 / 255, 32 / 255, alpha=0.85),
]
_CHART_RISK_COLOR = colors.Color(232 / 255, 160 / 255, 32 / 255, alpha=0.9)

PAGE_MARGIN = 1 * inch
_PAGE_WIDTH, _PAGE_HEIGHT = A4
CONTENT_WIDTH = _PAGE_WIDTH - 2 * PAGE_MARGIN
_KPI_COLUMNS = 3


@dataclass
class KpiCardData:
    label: str
    value: str
    sub_label: str = ""
    color: str = "default"
    value_style: str = "default"


@dataclass
class ChartDatasetData:
    label: str
    data: list[float]


@dataclass
class ChartSpecData:
    labels: list[str] = field(default_factory=list)
    datasets: list[ChartDatasetData] = field(default_factory=list)


@dataclass
class ReportData:
    generated_date: str
    scope_rows: list[tuple[str, str]]
    policy_rows: list[tuple[str, str]]
    explanation_text: str
    explanation_source_label: str
    kpi_cards: list[KpiCardData] = field(default_factory=list)
    chart_comparison: ChartSpecData = field(default_factory=ChartSpecData)
    chart_subject: ChartSpecData = field(default_factory=ChartSpecData)
    chart_risk: ChartSpecData = field(default_factory=ChartSpecData)
    section_titles: dict[str, str] = field(default_factory=dict)


def build_report_pdf(data: ReportData) -> bytes:
    styles = _build_styles()
    titles = data.section_titles

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        title=titles.get("title", "Simulation Report"),
        author="Education Workforce Policy Simulation Agent",
    )

    story: list[Flowable] = []

    story.append(Paragraph(escape(titles.get("title", "")), styles["PdfTitle"]))
    story.append(Paragraph(escape(data.generated_date), styles["PdfDate"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph(escape(titles.get("params_title", "")), styles["PdfSectionHeading"]))
    story.append(
        _params_table(
            data.scope_rows,
            data.policy_rows,
            titles.get("params_scope_subtitle", "Analysis Scope"),
            titles.get("params_policy_subtitle", "Policy Settings"),
            styles,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph(escape(titles.get("summary_title", "")), styles["PdfSectionHeading"]))
    story.extend(_markdown_to_flowables(data.explanation_text, styles))
    if data.explanation_source_label:
        story.append(Spacer(1, 8))
        story.append(Paragraph(escape(data.explanation_source_label), styles["PdfSource"]))
    story.append(PageBreak())

    story.append(Paragraph(escape(titles.get("kpi_title", "")), styles["PdfSectionHeading"]))
    story.append(_kpi_grid_table(data.kpi_cards, styles))
    story.append(PageBreak())

    story.append(Paragraph(escape(titles.get("charts_title", "")), styles["PdfSectionHeading"]))
    chart_sections = [
        (data.chart_comparison, titles.get("chart_comparison", ""), _CHART_COMPARISON_COLORS, "vertical"),
        (data.chart_subject, titles.get("chart_subject", ""), _CHART_SUBJECT_COLORS, "vertical"),
        (data.chart_risk, titles.get("chart_risk", ""), [_CHART_RISK_COLOR], "horizontal"),
    ]
    for spec, caption, series_colors, orientation in chart_sections:
        flowables = _chart_section(spec, caption, series_colors, orientation, styles)
        if flowables:
            story.append(KeepTogether(flowables))

    story.append(Spacer(1, 16))
    story.append(Paragraph(escape(titles.get("footer", "")), styles["PdfFooter"]))

    doc.build(story)
    return buffer.getvalue()


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        # Every style below sets `leading` explicitly, even ones that look
        # like they'd inherit a safe value from `parent`. Overriding
        # `fontSize` via `parent=` WITHOUT also overriding `leading` is a
        # real ReportLab trap: the inherited (smaller) leading silently
        # stays in effect, and text overlaps the line below it — reproduced
        # here with the 18pt KPI value overlapping its sub-label under the
        # sample stylesheet's default leading=12. Always pair the two.
        "PdfTitle": ParagraphStyle(
            "PdfTitle", parent=base["Title"], fontName="Times-Bold", fontSize=22,
            leading=26, textColor=COLOR_NAVY, alignment=TA_CENTER, spaceAfter=6,
        ),
        "PdfDate": ParagraphStyle(
            "PdfDate", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10,
            leading=13, textColor=COLOR_MUTED, alignment=TA_CENTER,
        ),
        "PdfSectionHeading": ParagraphStyle(
            "PdfSectionHeading", parent=base["Heading2"], fontName="Times-Bold", fontSize=16,
            leading=20, textColor=COLOR_NAVY, spaceBefore=0, spaceAfter=12,
        ),
        "PdfSubheading": ParagraphStyle(
            "PdfSubheading", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=12,
            leading=15, textColor=COLOR_NAVY, spaceBefore=10, spaceAfter=6,
        ),
        "PdfBody": ParagraphStyle(
            "PdfBody", parent=base["Normal"], fontName="Helvetica", fontSize=10,
            leading=15, textColor=colors.black, spaceAfter=8, alignment=TA_JUSTIFY,
        ),
        "PdfBullet": ParagraphStyle(
            "PdfBullet", parent=base["Normal"], fontName="Helvetica", fontSize=10,
            leading=15, textColor=colors.black,
        ),
        "PdfSource": ParagraphStyle(
            "PdfSource", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=8,
            leading=11, textColor=COLOR_MUTED,
        ),
        "PdfParamSubtitle": ParagraphStyle(
            "PdfParamSubtitle", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=11,
            leading=14, textColor=COLOR_NAVY,
        ),
        "PdfParamLabel": ParagraphStyle(
            "PdfParamLabel", parent=base["Normal"], fontName="Helvetica", fontSize=9.5,
            leading=13, textColor=COLOR_MUTED,
        ),
        "PdfParamValue": ParagraphStyle(
            "PdfParamValue", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9.5,
            leading=13, textColor=COLOR_NAVY, alignment=TA_RIGHT,
        ),
        "PdfKpiLabel": ParagraphStyle(
            "PdfKpiLabel", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8,
            leading=11, textColor=COLOR_MUTED, alignment=TA_CENTER,
        ),
        "PdfKpiValue": ParagraphStyle(
            "PdfKpiValue", parent=base["Normal"], fontName="Times-Bold", fontSize=18,
            leading=22, textColor=colors.black, alignment=TA_CENTER, spaceBefore=4, spaceAfter=4,
        ),
        "PdfKpiValuePositive": ParagraphStyle(
            "PdfKpiValuePositive", parent=base["Normal"], fontName="Times-Bold", fontSize=18,
            leading=22, textColor=COLOR_POSITIVE_TEXT, alignment=TA_CENTER, spaceBefore=4, spaceAfter=4,
        ),
        "PdfKpiValueNegative": ParagraphStyle(
            "PdfKpiValueNegative", parent=base["Normal"], fontName="Times-Bold", fontSize=18,
            leading=22, textColor=COLOR_NEGATIVE_TEXT, alignment=TA_CENTER, spaceBefore=4, spaceAfter=4,
        ),
        "PdfKpiSub": ParagraphStyle(
            "PdfKpiSub", parent=base["Normal"], fontName="Helvetica", fontSize=7.5,
            leading=10, textColor=COLOR_MUTED, alignment=TA_CENTER,
        ),
        "PdfCaption": ParagraphStyle(
            "PdfCaption", parent=base["Normal"], fontName="Times-Bold", fontSize=12,
            leading=15, textColor=COLOR_NAVY, alignment=TA_CENTER, spaceAfter=8,
        ),
        "PdfFooter": ParagraphStyle(
            "PdfFooter", parent=base["Normal"], fontName="Helvetica", fontSize=8,
            leading=11, textColor=COLOR_MUTED, alignment=TA_CENTER,
        ),
    }


def _params_table(
    scope_rows: list[tuple[str, str]],
    policy_rows: list[tuple[str, str]],
    scope_subtitle: str,
    policy_subtitle: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    table_data: list[list] = []
    commands: list[tuple] = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]

    def add_subtitle(text: str, is_first: bool) -> None:
        row_index = len(table_data)
        table_data.append([Paragraph(escape(text), styles["PdfParamSubtitle"]), ""])
        commands.append(("SPAN", (0, row_index), (1, row_index)))
        commands.append(("TOPPADDING", (0, row_index), (-1, row_index), 0 if is_first else 14))
        commands.append(("BOTTOMPADDING", (0, row_index), (-1, row_index), 6))

    def add_row(label: str, value: str) -> None:
        row_index = len(table_data)
        table_data.append([
            Paragraph(escape(label), styles["PdfParamLabel"]),
            Paragraph(escape(value), styles["PdfParamValue"]),
        ])
        commands.append(("LINEBELOW", (0, row_index), (-1, row_index), 0.5, COLOR_BORDER))
        commands.append(("TOPPADDING", (0, row_index), (-1, row_index), 4))
        commands.append(("BOTTOMPADDING", (0, row_index), (-1, row_index), 4))

    add_subtitle(scope_subtitle, is_first=True)
    for label, value in scope_rows:
        add_row(label, value)
    add_subtitle(policy_subtitle, is_first=False)
    for label, value in policy_rows:
        add_row(label, value)

    table = Table(table_data, colWidths=[CONTENT_WIDTH * 0.5, CONTENT_WIDTH * 0.5])
    table.setStyle(TableStyle(commands))
    return table


def _kpi_card_cell(card: KpiCardData, styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    value_style_key = {
        "positive": "PdfKpiValuePositive",
        "negative": "PdfKpiValueNegative",
    }.get(card.value_style, "PdfKpiValue")

    cell: list[Flowable] = [
        Paragraph(escape(card.label.upper()), styles["PdfKpiLabel"]),
        Paragraph(escape(card.value), styles[value_style_key]),
    ]
    if card.sub_label:
        cell.append(Paragraph(escape(card.sub_label), styles["PdfKpiSub"]))
    return cell


def _kpi_grid_table(cards: list[KpiCardData], styles: dict[str, ParagraphStyle]) -> Table:
    row_count = -(-len(cards) // _KPI_COLUMNS) if cards else 0  # ceil division, 0 rows if no cards
    table_data: list[list] = []
    commands: list[tuple] = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]

    for row_index in range(row_count):
        row_cells: list = []
        for col_index in range(_KPI_COLUMNS):
            card_index = row_index * _KPI_COLUMNS + col_index
            if card_index < len(cards):
                card = cards[card_index]
                row_cells.append(_kpi_card_cell(card, styles))
                accent = _KPI_ACCENTS.get(card.color, COLOR_NAVY)
                commands.append(("LINEABOVE", (col_index, row_index), (col_index, row_index), 3, accent))
                commands.append(("BOX", (col_index, row_index), (col_index, row_index), 0.5, COLOR_BORDER))
                commands.append(
                    ("BACKGROUND", (col_index, row_index), (col_index, row_index), COLOR_CARD_BG)
                )
            else:
                row_cells.append("")
        table_data.append(row_cells)

    col_width = CONTENT_WIDTH / _KPI_COLUMNS
    table = Table(table_data or [["", "", ""]], colWidths=[col_width] * _KPI_COLUMNS)
    table.setStyle(TableStyle(commands))
    return table


_HEADING_RE = re.compile(r"^#{1,3}\s+(.*)$")
_BULLET_RE = re.compile(r"^[-*]\s+(.*)$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"\*(.+?)\*")


def _inline_markup(text: str) -> str:
    """Escapes raw text for ReportLab's mini-XML, then converts the small
    markdown subset (**bold**, *italic*) into ReportLab's <b>/<i> tags.
    Escaping MUST happen first — otherwise literal '&'/'<'/'>' in
    AI-generated text would corrupt the tags this function itself inserts.
    """
    escaped = escape(text)
    escaped = _BOLD_RE.sub(r"<b>\1</b>", escaped)
    escaped = _ITALIC_RE.sub(r"<i>\1</i>", escaped)
    return escaped


def _markdown_to_flowables(text: str, styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    """Converts the lightweight markdown subset actually seen in real AI
    explanation output (### headings, **bold**, - bullets) into flowables.
    Deliberately not a full CommonMark parser — no nested lists, tables, or
    links — scoped to exactly what's been observed in practice.
    """
    flowables: list[Flowable] = []
    bullet_buffer: list[str] = []

    def flush_bullets() -> None:
        if not bullet_buffer:
            return
        items = [
            ListItem(Paragraph(_inline_markup(item), styles["PdfBullet"]), leftIndent=6)
            for item in bullet_buffer
        ]
        flowables.append(
            ListFlowable(items, bulletType="bullet", start="circle", leftIndent=18, spaceAfter=8)
        )
        bullet_buffer.clear()

    for raw_line in (text or "").split("\n"):
        line = raw_line.strip()
        if not line:
            flush_bullets()
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            flush_bullets()
            flowables.append(Paragraph(_inline_markup(heading_match.group(1)), styles["PdfSubheading"]))
            continue

        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            bullet_buffer.append(bullet_match.group(1))
            continue

        flush_bullets()
        flowables.append(Paragraph(_inline_markup(line), styles["PdfBody"]))

    flush_bullets()
    if not flowables:
        flowables.append(Paragraph("", styles["PdfBody"]))
    return flowables


def _configure_value_axis(value_axis) -> None:
    value_axis.valueMin = 0
    value_axis.labels.fontName = "Helvetica"
    value_axis.labels.fontSize = 8
    # Thousands-separator, matching the dashboard's .toLocaleString('en-MY')
    # axis-tick formatting (chart.js `ticks.callback` in app.js).
    value_axis.labelTextFormat = lambda v: format(int(round(v)), ",")


def _configure_category_axis(category_axis, labels: list[str]) -> None:
    # Plain strings, not ReportLab mini-XML — chart/legend text is drawn
    # directly (unlike Paragraph), so no escape() here.
    category_axis.categoryNames = list(labels)
    category_axis.labels.fontName = "Helvetica"
    category_axis.labels.fontSize = 8


def _chart_legend(datasets: list[ChartDatasetData], series_colors, width: float, y: float) -> Legend:
    legend = Legend()
    legend.y = y
    legend.dx = 8
    legend.dy = 8
    legend.dxTextSpace = 4
    legend.fontName = "Helvetica"
    legend.fontSize = 8
    legend.alignment = "right"
    # 1 item per column forces the legend to lay out horizontally (one swatch
    # next to the next) rather than stacking vertically — matches the
    # dashboard's `legend: { position: 'bottom' }` single-row look.
    legend.columnMaximum = 1
    legend.colorNamePairs = [(series_colors[i], ds.label) for i, ds in enumerate(datasets)]

    # deltax (column spacing) defaults to a fixed value regardless of label
    # length, which clips longer real-world labels (e.g. "Kekurangan Guru
    # Opsyen Mata Pelajaran" ran off the edge with a fixed spacing).
    # Measuring each label's actual rendered width and using the widest one
    # (plus a gap) as the column spacing guarantees nothing gets clipped,
    # then centers the whole row using that same measurement.
    item_gap = 14
    item_widths = [
        legend.dx + legend.dxTextSpace + stringWidth(ds.label, legend.fontName, legend.fontSize)
        for ds in datasets
    ]
    legend.deltax = (max(item_widths) if item_widths else 0) + item_gap
    total_width = legend.deltax * (len(datasets) - 1) + (item_widths[-1] if item_widths else 0)
    legend.x = max(4, (width - total_width) / 2)
    return legend


def _vertical_bar_chart_drawing(spec: ChartSpecData, series_colors: list, width: float, height: float) -> Drawing:
    """Grouped vertical bar chart (up to 2 series) — used for the Comparison
    and Subject-breakdown charts, matching renderComparisonChart/
    renderSubjectChart's Chart.js config in app.js."""
    drawing = Drawing(width, height)
    has_legend = len(spec.datasets) > 1
    legend_reserved = 26 if has_legend else 6

    chart = VerticalBarChart()
    chart.x = 45
    chart.y = legend_reserved
    chart.width = width - 60
    chart.height = height - legend_reserved - 8
    chart.data = [ds.data for ds in spec.datasets]
    _configure_category_axis(chart.categoryAxis, spec.labels)
    _configure_value_axis(chart.valueAxis)
    chart.groupSpacing = 14
    chart.barSpacing = 2
    for i in range(len(spec.datasets)):
        chart.bars[i].fillColor = series_colors[i]
        chart.bars[i].strokeColor = None
    drawing.add(chart)

    if has_legend:
        drawing.add(_chart_legend(spec.datasets, series_colors, width, 6))

    return drawing


def _horizontal_bar_chart_drawing(spec: ChartSpecData, color, width: float, height: float) -> Drawing:
    """Single-series horizontal bar chart — used for the state Risk Ranking
    chart, matching renderRiskRankingChart's `indexAxis: 'y'` Chart.js config."""
    drawing = Drawing(width, height)
    chart = HorizontalBarChart()
    chart.x = 90
    chart.y = 10
    chart.width = width - 110
    chart.height = height - 25
    chart.data = [spec.datasets[0].data] if spec.datasets else [[]]
    _configure_category_axis(chart.categoryAxis, spec.labels)
    _configure_value_axis(chart.valueAxis)
    chart.barSpacing = 4
    chart.bars[0].fillColor = color
    chart.bars[0].strokeColor = None
    drawing.add(chart)
    return drawing


def _chart_section(
    spec: ChartSpecData,
    caption: str,
    series_colors: list,
    orientation: str,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    if not spec.labels or not spec.datasets:
        return []

    if orientation == "vertical":
        height = 230
        drawing = _vertical_bar_chart_drawing(spec, series_colors, CONTENT_WIDTH, height)
    else:
        # Height scales with bar count (up to the top-8 states the dashboard
        # already limits itself to) so each state gets a legible row, same
        # spirit as the on-screen chart's own height accommodating its data.
        bar_count = len(spec.labels)
        height = max(140, min(300, 30 * bar_count + 40))
        drawing = _horizontal_bar_chart_drawing(spec, series_colors[0], CONTENT_WIDTH, height)

    return [
        Paragraph(escape(caption), styles["PdfCaption"]),
        drawing,
        Spacer(1, 20),
    ]

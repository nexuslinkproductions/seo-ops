"""Loopback-only local dashboard (stdlib http.server).

Every route lives under `/clients/<client_id>/...` and resolves exactly one
client store; there is no global data view. The server binds to 127.0.0.1
only and performs no outbound network calls.
"""

from __future__ import annotations

import html
import json
import re
import string
import tempfile
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from . import changeflow, scorecard as scorecard_mod
from .backlog import add_item as backlog_add
from .clients import (
    ClientError,
    create_client,
    list_clients,
    open_client_store,
)
from .evidence import capture_evidence, verify_evidence
from .ingest import IngestError, import_file
from .metrics import (
    all_families_summary,
    default_metric_definitions,
    family_metrics,
    period_values,
)
from .models import AuditFinding, MeasurementWindow
from .ids import new_id, utc_now

TEMPLATES = Path(__file__).parent / "templates"
STATIC = Path(__file__).parent / "static"

VIEWS = ("overview", "trends", "evidence", "audits", "changes", "scorecards", "backlog")

# Visual severity scale used by the audits donut. Colors match style.css.
SEVERITY_ORDER = ("critical", "high", "medium", "low")
SEVERITY_COLORS = {
    "critical": "#b3362b",
    "high": "#c2571b",
    "medium": "#b08a1e",
    "low": "#4a7fb5",
}
SEVERITY_LABELS = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}

# Change lifecycle stages shown in the changes pipeline graphic.
PIPELINE_STAGES = ("proposed", "approved", "deployed", "verified")


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


# ---------- presentation helpers (markup only) ----------

_RATE_METRIC_HINTS = ("pct", "rate", "share_of_answer")


def _metric_display(metric: str, value) -> str:
    """Format a metric value; known rate metrics render as percentages."""
    if value is None:
        return "n/a"
    if any(hint in metric for hint in _RATE_METRIC_HINTS):
        try:
            return f"{float(value) * 100:.1f}%"
        except (TypeError, ValueError):
            return str(value)
    return _fmt(value)


def _metric_caption(metric: str, fallback: str) -> str:
    for definition in default_metric_definitions():
        if definition.id == metric:
            return definition.name
    return fallback.replace("_", " ")


def _spark_bar(rel) -> str:
    """Inline diverging bar for a relative delta in the -1..+1 range."""
    if rel is None:
        return (
            '<div class="spark" aria-hidden="true">'
            '<span class="spark-track"><span class="spark-fill spark-neutral" '
            'style="width:0"></span></span></div>'
        )
    width = min(abs(rel), 1.0) * 50.0
    side = "spark-pos" if rel >= 0 else "spark-neg"
    edge = "left:50%" if rel >= 0 else f"right:50%"
    return (
        f'<div class="spark" title="delta {rel * 100:+.1f}%">'
        f'<span class="spark-track"><span class="spark-fill {side}" '
        f'style="{edge};width:{width:.1f}%"></span></span></div>'
    )


def _delta_chip(rel) -> str:
    if rel is None:
        return '<span class="chip chip-muted">n/a</span>'
    tone = "chip-pos" if rel >= 0 else "chip-neg"
    sign = "+" if rel >= 0 else ""
    return (
        f'<span class="chip {tone}"><span class="chip-arrow" aria-hidden="true">'
        f'{"&#9650;" if rel >= 0 else "&#9660;"}</span>'
        f'<span class="sr-only">{"up" if rel >= 0 else "down"} </span>'
        f"{sign}{rel * 100:.1f}%</span>"
    )


def _severity_donut(findings) -> str:
    """SVG donut of findings by severity with an accessible fallback table."""
    counts = {s: 0 for s in SEVERITY_ORDER}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    total = sum(counts.values())
    caption = "Findings by severity"
    if total == 0:
        return (
            '<div class="donut-wrap donut-empty">'
            '<svg class="donut" viewBox="0 0 42 42" role="img" '
            f'aria-label="{caption}: no findings recorded">'
            '<circle class="donut-hole" cx="21" cy="21" r="15.9155"></circle>'
            '<circle class="donut-ring donut-ring-empty" cx="21" cy="21" r="15.9155"></circle>'
            '<text class="donut-total" x="21" y="20.5">0</text>'
            '<text class="donut-sub" x="21" y="25.5">findings</text></svg>'
            '<ul class="legend"><li><span class="swatch swatch-none"></span>'
            "No findings recorded</li></ul></div>"
        )
    offset = 25.0
    segments = []
    legend_items = []
    for severity in SEVERITY_ORDER:
        count = counts.get(severity, 0)
        if count:
            dash = count / total * 100.0
            segments.append(
                f'<circle class="donut-seg" cx="21" cy="21" r="15.9155" '
                f'stroke="{SEVERITY_COLORS[severity]}" '
                f'stroke-dasharray="{dash:.3f} {100.0 - dash:.3f}" '
                f'stroke-dashoffset="{offset:.3f}">'
                f"<title>{SEVERITY_LABELS[severity]}: {count}</title></circle>"
            )
            offset -= dash
        legend_items.append(
            f'<li><span class="swatch" style="background:{SEVERITY_COLORS[severity]}"></span>'
            f"{SEVERITY_LABELS[severity]}: {count}</li>"
        )
    svg = (
        '<svg class="donut" viewBox="0 0 42 42" role="img" '
        f'aria-label="{caption}: {total} findings">'
        '<circle class="donut-hole" cx="21" cy="21" r="15.9155"></circle>'
        '<circle class="donut-ring" cx="21" cy="21" r="15.9155"></circle>'
        + "".join(segments)
        + f'<text class="donut-total" x="21" y="20.5">{total}</text>'
        '<text class="donut-sub" x="21" y="25.5">findings</text></svg>'
    )
    fallback_rows = "".join(
        f"<tr><td>{SEVERITY_LABELS[s]}</td><td>{counts.get(s, 0)}</td></tr>"
        for s in SEVERITY_ORDER
    )
    fallback = (
        f'<table class="sr-only"><caption>{caption}</caption>'
        f"<thead><tr><th>Severity</th><th>Count</th></tr></thead>"
        f"<tbody>{fallback_rows}</tbody></table>"
    )
    return (
        f'<div class="donut-wrap">{svg}<ul class="legend">{"".join(legend_items)}</ul>'
        f"{fallback}</div>"
    )


def _pipeline_figure(changes) -> str:
    """Stage funnel for the change lifecycle with an accessible fallback table."""
    counts = {stage: 0 for stage in PIPELINE_STAGES}
    other = 0
    for change in changes:
        if change.status in counts:
            counts[change.status] += 1
        else:
            other += 1
    total = sum(counts.values()) + other
    caption = "Changes by lifecycle stage"
    if total == 0:
        return (
            '<div class="pipeline pipeline-empty" role="img" '
            f'aria-label="{caption}: no changes recorded">'
            + "".join(
                f'<span class="stage"><span class="stage-count">0</span>'
                f'<span class="stage-label">{stage}</span></span>'
                for stage in PIPELINE_STAGES
            )
            + "</div>"
        )
    stages = []
    for stage in PIPELINE_STAGES:
        count = counts[stage]
        pct = count / total * 100.0
        stages.append(
            f'<span class="stage"><span class="stage-count">{count}</span>'
            f'<span class="stage-label">{stage}</span>'
            f'<span class="stage-bar" aria-hidden="true">'
            f'<span class="stage-fill" style="width:{max(pct, 4.0):.1f}%"></span></span>'
            f"</span>"
        )
    if other:
        stages.append(
            f'<span class="stage stage-other"><span class="stage-count">{other}</span>'
            f'<span class="stage-label">rejected or reverted</span></span>'
        )
    fallback_rows = "".join(
        f"<tr><td>{stage}</td><td>{counts[stage]}</td></tr>" for stage in PIPELINE_STAGES
    )
    if other:
        fallback_rows += f"<tr><td>rejected or reverted</td><td>{other}</td></tr>"
    fallback = (
        f'<table class="sr-only"><caption>{caption}</caption>'
        f"<thead><tr><th>Stage</th><th>Count</th></tr></thead>"
        f"<tbody>{fallback_rows}</tbody></table>"
    )
    return (
        f'<div class="pipeline" role="img" aria-label="{caption}: {total} changes">'
        + '<span class="stage-sep" aria-hidden="true"></span>'.join(stages)
        + f"</div>{fallback}"
    )


def _quadrant_figure(items) -> str:
    """Impact/effort quadrant scatter with an accessible fallback table."""
    caption = "Backlog impact versus effort"
    dots = []
    fallback_rows = []
    for index, item in enumerate(items):
        impact = min(max(float(item.impact), 0.0), 5.0)
        effort = min(max(float(item.effort), 0.0), 5.0)
        if impact >= 3.0 and effort < 3.0:
            tone = "dot-quick"
        elif impact >= 3.0:
            tone = "dot-major"
        elif effort < 3.0:
            tone = "dot-fill"
        else:
            tone = "dot-low"
        left = 10.0 + (impact / 5.0) * 80.0
        bottom = 12.0 + ((5.0 - effort) / 5.0) * 76.0
        dots.append(
            f'<span class="dot {tone}" style="left:{left:.1f}%;bottom:{bottom:.1f}%" '
            f'title="{esc(item.title)}: impact {_fmt(item.impact)}, effort {_fmt(item.effort)}">'
            f"{index + 1}</span>"
        )
        fallback_rows.append(
            f"<tr><td>{esc(item.title)}</td><td>{_fmt(item.impact)}</td>"
            f"<td>{_fmt(item.effort)}</td></tr>"
        )
    labels = (
        '<span class="quad-tag quad-tag-tl" aria-hidden="true">Fill ins</span>'
        '<span class="quad-tag quad-tag-tr" aria-hidden="true">Quick wins</span>'
        '<span class="quad-tag quad-tag-bl" aria-hidden="true">Low priority</span>'
        '<span class="quad-tag quad-tag-br" aria-hidden="true">Major projects</span>'
    )
    axes = (
        '<span class="quad-axis quad-axis-x" aria-hidden="true">Impact</span>'
        '<span class="quad-axis quad-axis-y" aria-hidden="true">Effort</span>'
    )
    fallback = (
        f'<table class="sr-only"><caption>{caption}</caption>'
        f"<thead><tr><th>Opportunity</th><th>Impact</th><th>Effort</th></tr></thead>"
        f"<tbody>{fallback_rows}</tbody></table>"
    )
    return (
        f'<figure class="quadrant" role="img" aria-label="{caption}: {len(items)} items">'
        f"{labels}{axes}{''.join(dots)}</figure>{fallback}"
    )


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "seo-ops/0.1"

    @property
    def data_root(self) -> Path:
        return self.server.data_root  # type: ignore[attr-defined]

    def log_message(self, fmt, *args) -> None:
        return

    # ---------- helpers ----------

    def _send(self, status: int, body: str, content_type: str = "text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, location: str):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def _body(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        return {k: v for k, v in urllib.parse.parse_qsl(raw)}

    def _client_store(self, client_id: str):
        try:
            return open_client_store(self.data_root, client_id)
        except ClientError:
            return None

    def _nav(self, client_id: Optional[str]) -> str:
        links = [
            ("/", "Clients"),
        ]
        if client_id:
            links += [
                (f"/clients/{client_id}/overview", "Overview"),
                (f"/clients/{client_id}/trends", "Trends"),
                (f"/clients/{client_id}/evidence", "Evidence"),
                (f"/clients/{client_id}/audits", "Audits"),
                (f"/clients/{client_id}/changes", "Changes"),
                (f"/clients/{client_id}/scorecards", "Scorecards"),
                (f"/clients/{client_id}/backlog", "Backlog"),
            ]
        return "".join(
            f'<a class="nav-link" href="{esc(href)}">{esc(label)}</a>' for href, label in links
        )

    def _page(self, title: str, client_id: Optional[str], body: str) -> str:
        template = string.Template((TEMPLATES / "base.html").read_text(encoding="utf-8"))
        return template.substitute(
            title=esc(title),
            nav=self._nav(client_id),
            body=body,
        )

    # ---------- routes ----------

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/":
            return self._clients_index()
        if path == "/static/style.css":
            css = (STATIC / "style.css").read_text(encoding="utf-8")
            return self._send(200, css, "text/css; charset=utf-8")
        match = re.fullmatch(r"/clients/([a-z0-9-]+)/([a-z0-9]+)", path)
        if not match:
            return self._send(404, "not found")
        client_id, view = match.groups()
        if view not in VIEWS:
            return self._send(404, "not found")
        store = self._client_store(client_id)
        if store is None:
            return self._send(404, "unknown client")
        handler = getattr(self, f"_view_{view}")
        return handler(client_id, store)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        form = self._body()
        if path == "/clients/add":
            name = form.get("name", "").strip()
            if not name:
                return self._redirect("/")
            create_client(self.data_root, name)
            return self._redirect("/")
        match = re.fullmatch(r"/clients/([a-z0-9-]+)/([a-z0-9_]+)", path)
        if not match:
            return self._send(404, "not found")
        client_id, action = match.groups()
        store = self._client_store(client_id)
        if store is None:
            return self._send(404, "unknown client")
        try:
            result = self._action(client_id, store, action, form)
        except (ValueError, IngestError, changeflow.ChangeFlowError, ClientError) as exc:
            return self._send(400, esc(str(exc)))
        if result:
            return self._send(200, result)
        return self._redirect(f"/clients/{client_id}/{form.get('back', 'overview')}")

    # ---------- index ----------

    def _clients_index(self):
        clients = list_clients(self.data_root)
        rows = "".join(
            f'<tr><td><a href="/clients/{esc(c.id)}/overview">{esc(c.name)}</a></td>'
            f"<td>{esc(c.id)}</td><td>{esc(', '.join(c.domains))}</td></tr>"
            for c in clients
        )
        table = (
            '<div class="panel"><table><thead><tr><th scope="col">Name</th>'
            '<th scope="col">ID</th><th scope="col">Domains</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>"
            if rows
            else '<div class="empty-state"><p class="empty-title">No clients yet</p>'
            "<p>Create the first client workspace below. All data stays local to "
            "this machine.</p></div>"
        )
        body = (
            '<div class="page-head"><h1>Clients</h1>'
            '<p class="page-sub">One isolated workspace per client. Select a client '
            "to review progress.</p></div>"
            f"{table}"
            '<form method="post" action="/clients/add" class="inline-form panel">'
            '<label class="field"><span class="field-label">New client</span>'
            '<input name="name" placeholder="Client name" required></label>'
            '<button type="submit">Create client</button></form>'
        )
        return self._send(200, self._page("Clients", None, body))

    # ---------- views ----------

    def _view_overview(self, client_id: str, store):
        summary = all_families_summary(
            store, "2026-06-01", "2026-06-30", "2026-07-01", "2026-07-31"
        )
        cards = ""
        for family in ("seo", "aeo", "geo", "analytics"):
            metrics = summary[family]
            headline = next(
                (m for m in family_metrics(family) if metrics[m]["post"] is not None),
                family_metrics(family)[0],
            )
            entry = metrics[headline]
            rel = entry.get("rel_delta")
            cards += (
                f'<div class="card metric-card"><h3>{esc(family.upper())}</h3>'
                f'<div class="metric">{esc(_metric_display(headline, entry.get("post")))}</div>'
                f'<div class="metric-name">{esc(_metric_caption(headline, headline))}</div>'
                f'<div class="metric-foot">{_spark_bar(rel)}'
                f'<span class="delta">{_delta_chip(rel)} vs Jun</span></div></div>'
            )
        body = (
            f'<div class="page-head"><h1>Overview</h1>'
            f'<p class="page-sub">Client: {esc(client_id)}</p></div>'
            f'<div class="cards">{cards}</div>'
            '<p class="note">Period: 2026-07-01 to 2026-07-31 vs 2026-06-01 to '
            "2026-06-30 (sample windows; ingest dated data to replace them).</p>"
        )
        return self._send(200, self._page("Overview", client_id, body))

    def _view_trends(self, client_id: str, store):
        blocks = ""
        for family in ("seo", "aeo", "geo", "analytics"):
            values = period_values(store, family, "2026-01-01", "2026-12-31")
            rows = "".join(
                f"<tr><th scope=\"row\">{esc(_metric_caption(metric, metric))}</th>"
                f"<td>{esc(_metric_display(metric, value))}</td></tr>"
                for metric, value in values.items()
            )
            blocks += (
                f'<section class="panel trend-panel"><h2>{esc(family.upper())}</h2>'
                f"<table><tbody>{rows}</tbody></table></section>"
            )
        body = (
            f'<div class="page-head"><h1>Trends</h1>'
            f'<p class="page-sub">Client: {esc(client_id)}. Year to date 2026 '
            "totals and rates by metric family.</p></div>"
            f'<div class="trend-grid">{blocks}</div>'
        )
        return self._send(200, self._page("Trends", client_id, body))

    def _view_evidence(self, client_id: str, store):
        items = store.list_evidence()
        rows = "".join(
            f"<tr><td>{esc(i.kind)}</td><td>{esc(i.sha256 or '')}</td>"
            f"<td>{esc(i.path or '(inline)')}</td><td>{esc(i.captured_by)}</td>"
            f"<td>{esc(i.captured_at)}</td></tr>"
            for i in items
        )
        report = verify_evidence(store, open_client_store(self.data_root, client_id).db_path.parent)
        badge = (
            '<span class="badge badge-ok">CLEAN</span>'
            if report.clean
            else '<span class="badge badge-bad">ISSUES FOUND</span>'
        )
        table = (
            '<div class="panel"><table><thead><tr><th scope="col">Kind</th>'
            '<th scope="col">SHA-256</th><th scope="col">Path</th>'
            '<th scope="col">By</th><th scope="col">Captured</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>"
            if rows
            else '<div class="empty-state"><p class="empty-title">No evidence yet</p>'
            "<p>Capture a screenshot, export, or note below. Every item is hashed "
            "and verified on each visit.</p></div>"
        )
        body = (
            f'<div class="page-head"><h1>Evidence</h1>'
            f'<p class="page-sub">Client: {esc(client_id)}. Immutable capture log '
            "with integrity verification.</p></div>"
            f'<div class="panel integrity-panel">{badge}'
            f'<span class="integrity-meta">{report.checked} items checked, '
            f"tool {esc(report.tool)}</span></div>"
            f"{table}"
            '<form method="post" action="/clients/{}/evidence/add" class="inline-form panel">'.format(client_id)
            + '<label class="field"><span class="field-label">Kind</span>'
            + '<input name="kind" value="screenshot"></label>'
            + '<label class="field"><span class="field-label">File path</span>'
            + '<input name="file_path" placeholder="/absolute/path/or-empty"></label>'
            + '<label class="field"><span class="field-label">Inline text</span>'
            + '<input name="inline_text" placeholder="or inline text"></label>'
            + '<label class="field"><span class="field-label">Source</span>'
            + '<input name="source_description" placeholder="source description"></label>'
            + '<button type="submit">Capture</button></form>'
        )
        return self._send(200, self._page("Evidence", client_id, body))

    def _view_audits(self, client_id: str, store):
        findings = store.list_findings()
        rows = "".join(
            f'<tr><td><span class="chip sev-{esc(f.severity)}">{esc(f.severity)}</span></td>'
            f"<td>{esc(f.category)}</td>"
            f"<td>{esc(f.title)}</td><td>{esc(f.status)}</td></tr>"
            for f in findings
        )
        table = (
            '<div class="panel"><table><thead><tr><th scope="col">Severity</th>'
            '<th scope="col">Category</th><th scope="col">Finding</th>'
            '<th scope="col">Status</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>"
            if rows
            else '<div class="empty-state"><p class="empty-title">No findings</p>'
            "<p>Audit findings recorded for this client will appear here, grouped "
            "by severity in the chart above.</p></div>"
        )
        body = (
            f'<div class="page-head"><h1>Audits</h1>'
            f'<p class="page-sub">Client: {esc(client_id)}. Findings by severity '
            "and category.</p></div>"
            f'<section class="panel"><h2>Severity mix</h2>{_severity_donut(findings)}</section>'
            f"{table}"
        )
        return self._send(200, self._page("Audits", client_id, body))

    def _view_changes(self, client_id: str, store):
        changes = store.list_changes()
        rows = ""
        for c in changes:
            summary = c.result_summary
            delta = (
                f"{_fmt(summary.pre_value)} -> {_fmt(summary.post_value)} "
                f"({_fmt(summary.rel_delta)})"
                if summary
                else "pending measurement"
            )
            rows += (
                f"<tr><td>{esc(c.title)}</td><td>{esc(c.status)}</td>"
                f"<td>{esc(c.proposed_by)}</td><td>{esc(c.approved_by or '')}</td>"
                f"<td>{esc(delta)}</td><td>{esc(c.id)}</td></tr>"
            )
        table = (
            '<div class="panel"><table><thead><tr><th scope="col">Change</th>'
            '<th scope="col">Status</th><th scope="col">Proposed by</th>'
            '<th scope="col">Approved by</th><th scope="col">Result</th>'
            '<th scope="col">ID</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>"
            if rows
            else '<div class="empty-state"><p class="empty-title">No changes yet</p>'
            "<p>Propose a change below. It moves through approval, deployment, "
            "and verified measurement in the pipeline above.</p></div>"
        )
        body = (
            f'<div class="page-head"><h1>Approved change log</h1>'
            f'<p class="page-sub">Client: {esc(client_id)}. Lifecycle from proposal '
            "to verified result.</p></div>"
            f'<section class="panel"><h2>Pipeline</h2>{_pipeline_figure(changes)}</section>'
            f"{table}"
            '<form method="post" action="/clients/{}/changes/new" class="inline-form panel">'.format(client_id)
            + '<label class="field"><span class="field-label">Change</span>'
            + '<input name="title" placeholder="Change title" required></label>'
            + '<label class="field"><span class="field-label">Proposed by</span>'
            + '<input name="proposed_by" placeholder="proposed by"></label>'
            + '<button type="submit">Propose change</button></form>'
        )
        return self._send(200, self._page("Changes", client_id, body))

    def _view_scorecards(self, client_id: str, store):
        cards = store.list_scorecards()
        rows = "".join(
            f"<tr><td>{esc(c.period_start)} → {esc(c.period_end)}</td>"
            f"<td>{esc(c.generated_at)}</td><td>{esc(c.export_path or '')}</td></tr>"
            for c in cards
        )
        table = (
            '<div class="panel"><table><thead><tr><th scope="col">Period</th>'
            '<th scope="col">Generated</th><th scope="col">Export</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>"
            if rows
            else '<div class="empty-state"><p class="empty-title">No scorecards yet</p>'
            "<p>Generate a scorecard for a period below. Exports are written to "
            "the client data folder.</p></div>"
        )
        body = (
            f'<div class="page-head"><h1>Scorecards</h1>'
            f'<p class="page-sub">Client: {esc(client_id)}. Generated period '
            "reports.</p></div>"
            f"{table}"
            '<form method="post" action="/clients/{}/scorecard/generate" class="inline-form panel">'.format(client_id)
            + '<label class="field"><span class="field-label">Period start</span>'
            + '<input name="period_start" value="2026-07-01"></label>'
            + '<label class="field"><span class="field-label">Period end</span>'
            + '<input name="period_end" value="2026-07-31"></label>'
            + '<button type="submit">Generate scorecard</button></form>'
        )
        return self._send(200, self._page("Scorecards", client_id, body))

    def _view_backlog(self, client_id: str, store):
        items = store.list_backlog()
        rows = "".join(
            f"<tr><td>{esc(i.title)}</td><td>{esc(i.category)}</td>"
            f"<td>{_fmt(i.impact)}</td><td>{_fmt(i.effort)}</td><td>{_fmt(i.score)}</td></tr>"
            for i in items
        )
        table = (
            '<div class="panel"><table><thead><tr><th scope="col">Opportunity</th>'
            '<th scope="col">Category</th><th scope="col">Impact</th>'
            '<th scope="col">Effort</th><th scope="col">Score</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>"
            if rows
            else '<div class="empty-state"><p class="empty-title">Backlog is empty</p>'
            "<p>Add an opportunity below. Items plot on the impact versus effort "
            "chart once added.</p></div>"
        )
        chart = (
            f'<section class="panel"><h2>Impact vs effort</h2>{_quadrant_figure(items)}</section>'
            if items
            else ""
        )
        body = (
            f'<div class="page-head"><h1>Backlog</h1>'
            f'<p class="page-sub">Client: {esc(client_id)}. Opportunities ranked '
            "by score.</p></div>"
            f"{chart}{table}"
            '<form method="post" action="/clients/{}/backlog/add" class="inline-form panel">'.format(client_id)
            + '<label class="field"><span class="field-label">Opportunity</span>'
            + '<input name="title" placeholder="Opportunity" required></label>'
            + '<label class="field"><span class="field-label">Impact 1-5</span>'
            + '<input name="impact" value="3"></label>'
            + '<label class="field"><span class="field-label">Effort 1-5</span>'
            + '<input name="effort" value="3"></label>'
            + '<button type="submit">Add</button></form>'
        )
        return self._send(200, self._page("Backlog", client_id, body))

    # ---------- actions ----------

    def _action(self, client_id: str, store, action: str, form: dict) -> Optional[str]:
        client_dir = self.data_root / "clients" / client_id
        if action == "ingest":
            source = form.get("source", "")
            file_path = form.get("path", "")
            if not file_path:
                raise ValueError("path is required for ingestion")
            batch = import_file(store, source, Path(file_path))
            return (
                f"<p>Imported batch {esc(batch.id)}: {batch.row_count} rows "
                f"({esc(batch.rule)})</p>"
            )
        if action == "evidence/add":
            item = capture_evidence(
                store,
                client_dir,
                form.get("kind", "note"),
                file_path=Path(form["file_path"]) if form.get("file_path") else None,
                inline_text=form.get("inline_text") or None,
                captured_by=form.get("captured_by") or "operator",
                source_description=form.get("source_description") or None,
            )
            return f"<p>Captured evidence {esc(item.id)} sha256={esc(item.sha256)}</p>"
        if action == "changes/new":
            change = changeflow.new_change(
                store, form.get("title", ""), form.get("proposed_by") or "operator"
            )
            return f"<p>Proposed change {esc(change.id)}</p>"
        if action == "changes/approve":
            change = changeflow.approve(store, form.get("change_id", ""), form.get("approved_by") or "operator")
            return f"<p>Approved {esc(change.id)}</p>"
        if action == "changes/deploy":
            change = changeflow.deploy(store, form.get("change_id", ""))
            return f"<p>Deployed {esc(change.id)}</p>"
        if action == "changes/verify":
            window = MeasurementWindow(
                pre_start=form.get("pre_start", ""),
                pre_end=form.get("pre_end", ""),
                post_start=form.get("post_start", ""),
                post_end=form.get("post_end", ""),
            )
            change = changeflow.verify(
                store,
                form.get("change_id", ""),
                [form.get("pre_evidence_id", "")] if form.get("pre_evidence_id") else [],
                [form.get("post_evidence_id", "")] if form.get("post_evidence_id") else [],
                window,
                form.get("family", "seo"),
                form.get("metric", "clicks"),
            )
            return f"<p>Verified {esc(change.id)}</p>"
        if action == "scorecard/generate":
            card = scorecard_mod.generate_scorecard(
                store, client_dir, form.get("period_start", ""), form.get("period_end", "")
            )
            return f"<p>Generated scorecard {esc(card.id)} → {esc(card.export_path)}</p>"
        if action == "backlog/add":
            item = backlog_add(
                store,
                form.get("title", ""),
                float(form.get("impact", 3)),
                float(form.get("effort", 3)),
            )
            return f"<p>Added backlog item {esc(item.id)} score={_fmt(item.score)}</p>"
        if action == "audits/add":
            finding = AuditFinding(
                id=new_id(),
                created_at=utc_now(),
                category=form.get("category", "technical"),
                severity=form.get("severity", "medium"),
                title=form.get("title", ""),
                description=form.get("description") or None,
                recommendation=form.get("recommendation") or None,
            )
            store.add_finding(finding)
            return f"<p>Added finding {esc(finding.id)}</p>"
        return None


def make_server(data_root: Path, port: int = 8765) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    server.data_root = data_root  # type: ignore[attr-defined]
    return server


def serve(data_root: Path, port: int = 8765) -> None:
    server = make_server(data_root, port)
    print(f"seo-ops dashboard on http://127.0.0.1:{port} (loopback only)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

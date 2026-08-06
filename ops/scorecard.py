"""Scorecard artifact generation (HTML + Markdown) per client."""

from __future__ import annotations

import html
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from .ids import new_id, utc_now
from .metrics import all_families_summary, period_values
from .models import Scorecard
from .store import ClientStore


def _iso_add(start: str, end: str) -> tuple[str, str]:
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    span = end_d - start_d
    prev_end = start_d - timedelta(days=1)
    prev_start = prev_end - span
    return prev_start.isoformat(), prev_end.isoformat()


def generate_scorecard(
    store: ClientStore,
    client_dir: Path,
    period_start: str,
    period_end: str,
    highlights: Optional[list[str]] = None,
) -> Scorecard:
    pre_start, pre_end = _iso_add(period_start, period_end)
    summary = all_families_summary(store, pre_start, pre_end, period_start, period_end)
    values = {
        family: period_values(store, family, period_start, period_end)
        for family in ("seo", "aeo", "geo", "analytics")
    }
    changes_in_period = [
        c.id
        for c in store.list_changes()
        if c.status in ("deployed", "verified")
        and c.deployed_at
        and period_start <= c.deployed_at[:10] <= period_end
    ]
    definitions = store.list_metric_definitions()
    card = Scorecard(
        id=new_id(),
        period_start=period_start,
        period_end=period_end,
        generated_at=utc_now(),
        metrics_snapshot={
            "period_values": values,
            "deltas_vs_previous_period": summary,
        },
        highlights=highlights or [],
        changes_in_period=changes_in_period,
    )
    exports = client_dir / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    stem = f"scorecard-{period_start}_{period_end}"
    md_path = exports / f"{stem}.md"
    html_path = exports / f"{stem}.html"
    md_path.write_text(render_markdown(card, definitions), encoding="utf-8")
    html_path.write_text(render_html(card, definitions), encoding="utf-8")
    card.export_path = str(html_path)
    return store.add_scorecard(card)


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _delta_line(metric: str, entry: dict) -> str:
    pre, post = entry.get("pre"), entry.get("post")
    rel = entry.get("rel_delta")
    rel_s = f"{rel * 100:+.1f}%" if rel is not None else ""
    return f"{metric}: {_fmt(pre)} -> {_fmt(post)} ({rel_s})"


def render_markdown(card: Scorecard, definitions) -> str:
    lines = [
        f"# Scorecard {card.period_start} to {card.period_end}",
        "",
        f"Generated: {card.generated_at}",
        "",
        "## Highlights",
    ]
    lines += [f"- {h}" for h in card.highlights] or ["- (none)"]
    lines += ["", "## Period values"]
    for family, metrics in card.metrics_snapshot["period_values"].items():
        lines.append(f"### {family.upper()}")
        for metric, value in metrics.items():
            lines.append(f"- {metric}: {_fmt(value)}")
    lines += ["", "## Deltas vs previous period"]
    for family, metrics in card.metrics_snapshot["deltas_vs_previous_period"].items():
        lines.append(f"### {family.upper()}")
        for metric, entry in metrics.items():
            lines.append(f"- {_delta_line(metric, entry)}")
    lines += ["", "## Changes in period"]
    lines += [f"- {cid}" for cid in card.changes_in_period] or ["- (none)"]
    lines += ["", "## Metric definitions referenced"]
    for d in definitions:
        lines.append(f"- `{d.id}` ({d.family}): {d.name} — {d.formula}")
    return "\n".join(lines) + "\n"


def render_html(card: Scorecard, definitions) -> str:
    def esc(value) -> str:
        return html.escape(str(value))

    family_blocks = []
    for family, metrics in card.metrics_snapshot["period_values"].items():
        rows = "".join(
            f"<tr><td>{esc(metric)}</td><td>{_fmt(value)}</td></tr>"
            for metric, value in metrics.items()
        )
        family_blocks.append(
            f"<h3>{esc(family.upper())}</h3><table><tbody>{rows}</tbody></table>"
        )
    delta_blocks = []
    for family, metrics in card.metrics_snapshot["deltas_vs_previous_period"].items():
        rows = "".join(
            f"<tr><td>{esc(metric)}</td><td>{_fmt(entry.get('pre'))}</td>"
            f"<td>{_fmt(entry.get('post'))}</td><td>{esc(_delta_line(metric, entry))}</td></tr>"
            for metric, entry in metrics.items()
        )
        delta_blocks.append(
            f"<h3>{esc(family.upper())}</h3><table><tbody>{rows}</tbody></table>"
        )
    defs = "".join(
        f"<li><code>{esc(d.id)}</code> ({esc(d.family)}): {esc(d.name)} — {esc(d.formula)}</li>"
        for d in definitions
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Scorecard {esc(card.period_start)} — {esc(card.period_end)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;color:#1c2430}}
table{{border-collapse:collapse;width:100%;margin:0.5rem 0 1.25rem}}td,th{{border:1px solid #d8dee8;padding:6px 8px;text-align:left}}
h2,h3{{margin-top:1.5rem}}</style></head><body>
<h1>Scorecard {esc(card.period_start)} to {esc(card.period_end)}</h1>
<p>Generated: {esc(card.generated_at)}</p>
<h2>Highlights</h2><ul>{''.join(f'<li>{esc(h)}</li>' for h in card.highlights) or '<li>(none)</li>'}</ul>
<h2>Period values</h2>{''.join(family_blocks)}
<h2>Deltas vs previous period</h2>{''.join(delta_blocks)}
<h2>Changes in period</h2><ul>{''.join(f'<li>{esc(c)}</li>' for c in card.changes_in_period) or '<li>(none)</li>'}</ul>
<h2>Metric definitions referenced</h2><ul>{defs}</ul>
</body></html>
"""

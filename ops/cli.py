"""Operator CLI entry points (argparse).

Everything stays local under the data root (default: `<repo>/data`, override
with `SEO_OPS_DATA_ROOT` or `--data-root`). No external calls.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import changeflow
from . import openseo as openseo_mod
from .backlog import add_item as backlog_add
from .clients import (
    default_data_root,
    create_client,
    list_clients,
    open_client_store,
)
from .evidence import capture_evidence, verify_evidence
from .ingest import import_file
from .models import AuditFinding, MeasurementWindow
from .scorecard import generate_scorecard
from .serve import serve
from .ids import new_id, utc_now


def _parent() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--data-root", type=Path, default=None)
    return parser


def _root(args) -> Path:
    return args.data_root or default_data_root()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ops", description="seo-ops local operations CLI")
    parent = _parent()
    sub = parser.add_subparsers(dest="command", required=True)

    p_client_add = sub.add_parser("client-add", parents=[parent])
    p_client_add.add_argument("--name", required=True)
    p_client_add.add_argument("--id", default=None)
    p_client_add.add_argument("--domain", action="append", default=[])
    p_client_add.add_argument("--prompt", action="append", default=[])

    sub.add_parser("client-list", parents=[parent])

    p_ingest = sub.add_parser("ingest", parents=[parent])
    p_ingest.add_argument("--client", required=True)
    p_ingest.add_argument("--source", required=True,
                          choices=["search_console", "crawl", "analytics", "geo", "aeo"])
    p_ingest.add_argument("--file", type=Path, required=True)

    p_openseo = sub.add_parser("openseo-import", parents=[parent])
    p_openseo.add_argument("--client", required=True)
    p_openseo.add_argument("--file", type=Path, required=True)
    p_openseo.add_argument(
        "--source",
        default="openseo",
        choices=["openseo", "dataforseo"],
        help="Label only; format is detected from the file content.",
    )
    p_openseo.add_argument(
        "--no-evidence",
        action="store_true",
        help="Skip capturing the sanitized export as evidence.",
    )
    p_openseo.add_argument(
        "--backlog",
        action="store_true",
        help="Derive backlog opportunities from SERP rows outside the top 10.",
    )
    p_openseo.add_argument("--backlog-max", type=int, default=25)
    p_openseo.add_argument("--by", default="operator")

    p_ev = sub.add_parser("evidence-add", parents=[parent])
    p_ev.add_argument("--client", required=True)
    p_ev.add_argument("--kind", required=True)
    p_ev.add_argument("--file", type=Path, default=None)
    p_ev.add_argument("--inline-text", default=None)
    p_ev.add_argument("--by", default="operator")
    p_ev.add_argument("--source-description", default=None)

    p_check = sub.add_parser("evidence-verify", parents=[parent])
    p_check.add_argument("--client", required=True)
    p_check.add_argument("--rust", action="store_true", default=True)

    p_audit = sub.add_parser("audit-add", parents=[parent])
    p_audit.add_argument("--client", required=True)
    p_audit.add_argument("--category", required=True)
    p_audit.add_argument("--severity", required=True)
    p_audit.add_argument("--title", required=True)
    p_audit.add_argument("--description", default=None)
    p_audit.add_argument("--recommendation", default=None)

    p_change = sub.add_parser("change-new", parents=[parent])
    p_change.add_argument("--client", required=True)
    p_change.add_argument("--title", required=True)
    p_change.add_argument("--proposed-by", default="operator")

    p_appr = sub.add_parser("change-approve", parents=[parent])
    p_appr.add_argument("--client", required=True)
    p_appr.add_argument("--change-id", required=True)
    p_appr.add_argument("--by", default="operator")

    p_dep = sub.add_parser("change-deploy", parents=[parent])
    p_dep.add_argument("--client", required=True)
    p_dep.add_argument("--change-id", required=True)

    p_ver = sub.add_parser("change-verify", parents=[parent])
    p_ver.add_argument("--client", required=True)
    p_ver.add_argument("--change-id", required=True)
    p_ver.add_argument("--pre-evidence", action="append", required=True)
    p_ver.add_argument("--post-evidence", action="append", required=True)
    p_ver.add_argument("--pre-start", required=True)
    p_ver.add_argument("--pre-end", required=True)
    p_ver.add_argument("--post-start", required=True)
    p_ver.add_argument("--post-end", required=True)
    p_ver.add_argument("--family", default="seo")
    p_ver.add_argument("--metric", default="clicks")

    p_back = sub.add_parser("backlog-add", parents=[parent])
    p_back.add_argument("--client", required=True)
    p_back.add_argument("--title", required=True)
    p_back.add_argument("--impact", type=float, required=True)
    p_back.add_argument("--effort", type=float, required=True)
    p_back.add_argument("--category", default="content")

    p_score = sub.add_parser("scorecard", parents=[parent])
    p_score.add_argument("--client", required=True)
    p_score.add_argument("--start", required=True)
    p_score.add_argument("--end", required=True)
    p_score.add_argument("--highlight", action="append", default=[])

    p_serve = sub.add_parser("serve", parents=[parent])
    p_serve.add_argument("--port", type=int, default=8765)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    root = _root(args)
    cmd = args.command

    if cmd == "client-add":
        info = create_client(
            root, args.name, args.domain, args.prompt, explicit_id=args.id
        )
        print(f"created client {info.id} ({info.name})")
    elif cmd == "client-list":
        for c in list_clients(root):
            print(f"{c.id}\t{c.name}\t{','.join(c.domains)}")
    elif cmd == "ingest":
        store = open_client_store(root, args.client)
        batch = import_file(store, args.source, args.file)
        print(
            f"imported {batch.row_count} rows as batch {batch.id} "
            f"[{batch.rule}]"
        )
    elif cmd == "openseo-import":
        store = open_client_store(root, args.client)
        result = openseo_mod.import_openseo_export(
            store,
            root / "clients" / args.client,
            args.file,
            capture_evidence=not args.no_evidence,
            build_backlog=args.backlog,
            backlog_max=args.backlog_max,
            captured_by=args.by,
        )
        batch = result["batch"]
        print(
            f"openseo import batch {batch.id}: {result['new_rows']} new rows "
            f"(idempotent={result['idempotent']}) evidence="
            f"{','.join(result['evidence']) or 'none'} "
            f"backlog_items={len(result['backlog'])}"
        )
    elif cmd == "evidence-add":
        store = open_client_store(root, args.client)
        item = capture_evidence(
            store,
            root / "clients" / args.client,
            args.kind,
            file_path=args.file,
            inline_text=args.inline_text,
            captured_by=args.by,
            source_description=args.source_description,
        )
        print(f"evidence {item.id} sha256={item.sha256}")
    elif cmd == "evidence-verify":
        store = open_client_store(root, args.client)
        report = verify_evidence(store, root / "clients" / args.client, prefer_rust=args.rust)
        print(
            f"integrity tool={report.tool} clean={report.clean} "
            f"checked={report.checked} mismatches={len(report.mismatches)} "
            f"missing={len(report.missing)}"
        )
        for m in report.mismatches:
            print(f"  MISMATCH {m['path']}")
        for m in report.missing:
            print(f"  MISSING {m['path']}")
    elif cmd == "audit-add":
        store = open_client_store(root, args.client)
        finding = AuditFinding(
            id=new_id(),
            created_at=utc_now(),
            category=args.category,
            severity=args.severity,
            title=args.title,
            description=args.description,
            recommendation=args.recommendation,
        )
        store.add_finding(finding)
        print(f"added finding {finding.id}")
    elif cmd == "change-new":
        store = open_client_store(root, args.client)
        change = changeflow.new_change(store, args.title, args.proposed_by)
        print(f"proposed change {change.id}")
    elif cmd == "change-approve":
        store = open_client_store(root, args.client)
        change = changeflow.approve(store, args.change_id, args.by)
        print(f"approved {change.id}")
    elif cmd == "change-deploy":
        store = open_client_store(root, args.client)
        change = changeflow.deploy(store, args.change_id)
        print(f"deployed {change.id}")
    elif cmd == "change-verify":
        store = open_client_store(root, args.client)
        change = changeflow.verify(
            store,
            args.change_id,
            args.pre_evidence,
            args.post_evidence,
            MeasurementWindow(
                pre_start=args.pre_start,
                pre_end=args.pre_end,
                post_start=args.post_start,
                post_end=args.post_end,
            ),
            args.family,
            args.metric,
        )
        summary = change.result_summary
        print(
            f"verified {change.id}: {summary.metric} {summary.pre_value} -> "
            f"{summary.post_value} (abs {summary.abs_delta}, "
            f"rel {summary.rel_delta})"
        )
    elif cmd == "backlog-add":
        store = open_client_store(root, args.client)
        item = backlog_add(
            store, args.title, args.impact, args.effort, category=args.category
        )
        print(f"backlog item {item.id} score={item.score}")
    elif cmd == "scorecard":
        store = open_client_store(root, args.client)
        card = generate_scorecard(
            store,
            root / "clients" / args.client,
            args.start,
            args.end,
            highlights=args.highlight,
        )
        print(f"scorecard {card.id} -> {card.export_path}")
    elif cmd == "serve":
        serve(root, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

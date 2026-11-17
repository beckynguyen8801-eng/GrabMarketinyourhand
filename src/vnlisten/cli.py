"""CLI: vnlisten <command>."""
from __future__ import annotations

import argparse
import dataclasses
import logging
import subprocess
import sys
from pathlib import Path

from .container import PROJECT_ROOT, Settings, build_app
from .domain.models import SourceType


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="vnlisten", description="Multi-industry social listening & marketing research")
    parser.add_argument("--db", help="SQLite path (overrides VNLISTEN_DB)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("hourly", help="Run the hourly job once (hot queries + alerts)")
    sub.add_parser("daily", help="Run the daily job once (all queries, marketplace, keywords, insights)")
    sub.add_parser("schedule", help="Run the scheduler (hourly + daily)")
    sub.add_parser("alerts", help="Evaluate alert rules on stored data")
    ins = sub.add_parser("insight", help="Generate insights & recommendations from the last 7 days")
    ins.add_argument("--industry", help="Empty = all industries")
    sub.add_parser("industries", help="List configured industries")

    imp = sub.add_parser("import-csv", help="Import posts from CSV (Facebook/TikTok/Threads...)")
    imp.add_argument("path")
    imp.add_argument("--source", default="facebook", choices=[s.value for s in SourceType])
    imp.add_argument("--category", default="")
    imp.add_argument("--industry", default="", help="Empty = auto-detect from mentioned brands/products")

    demo = sub.add_parser("seed-demo", help="Generate demo data into data/demo.db")
    demo.add_argument("--days", type=int, default=30)

    sub.add_parser("dashboard", help="Open the Streamlit dashboard")
    srv = sub.add_parser("serve", help="Local ingest server for the VN Listen Capture browser extension")
    srv.add_argument("--port", type=int, default=8765)

    watch = sub.add_parser("watch", help="Manage extra keywords tracked by the daily job")
    watch.add_argument("action", choices=["add", "remove", "list"])
    watch.add_argument("keyword", nargs="?", default="")
    watch.add_argument("--industry", default="")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings = Settings.from_env()
    if args.cmd == "seed-demo" and not args.db:
        args.db = "data/demo.db"
    if args.db:
        db = Path(args.db)
        settings = dataclasses.replace(settings, db_path=db if db.is_absolute() else PROJECT_ROOT / db)

    if args.cmd == "dashboard":
        app_file = PROJECT_ROOT / "dashboard" / "app.py"
        cmd = [sys.executable, "-m", "streamlit", "run", str(app_file), "--", "--db", str(settings.db_path)]
        raise SystemExit(subprocess.call(cmd, cwd=PROJECT_ROOT))  # cwd để đọc .streamlit/config.toml

    from . import demo, jobs  # noqa: PLC0415
    from .connectors.csv_import import read_csv  # noqa: PLC0415

    app = build_app(settings)
    match args.cmd:
        case "hourly":
            jobs.run_hourly(app)
        case "daily":
            jobs.run_daily(app)
        case "schedule":
            jobs.start_scheduler(app)
        case "alerts":
            print(f"{len(app.alerts.run())} new alerts")
        case "insight":
            for industry in [args.industry] if args.industry else app.registry.ids():
                print(app.insights.run(industry), end="\n\n")
        case "industries":
            for t in app.registry.all():
                print(f"{t.industry:<16} {t.name:<16} {len(t.categories)} categories, "
                      f"{len(t.brands)} brands/entities, {len(t.products)} products")
        case "import-csv":
            stats = app.collection.ingest(read_csv(args.path, SourceType(args.source), args.category, args.industry))
            print(f"Read {stats.fetched}, kept {stats.kept} relevant, {stats.new} new")
        case "serve":
            from .ingest_server import serve  # noqa: PLC0415

            serve(app.collection, args.port)
        case "watch":
            if args.action == "list":
                for ind, kw in app.repo.watchlist(args.industry or None):
                    print(f"{ind:<16} {kw}")
            elif not (args.keyword and args.industry in app.registry):
                raise SystemExit(f"Need a keyword and --industry ({', '.join(app.registry.ids())})")
            elif args.action == "add":
                app.repo.add_watch(args.industry, args.keyword)
                print(f"Tracking '{args.keyword}' daily in {args.industry}")
            else:
                app.repo.remove_watch(args.industry, args.keyword)
                print(f"Stopped tracking '{args.keyword}'")
        case "seed-demo":
            print(f"Generated {demo.seed_demo(app, days=args.days)} demo mentions into {settings.db_path}")


if __name__ == "__main__":
    main()

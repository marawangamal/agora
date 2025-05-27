import argparse
from typing import Callable, Optional
import appdirs
from pathlib import Path
from jrun.job_submitter import JobSubmitter
from jrun.job_viewer import JobViewer
from jrun.jrun_server_v2 import serve
from jrun.jweb_server import serve_react_app  # Updated import


def get_default_db_path():
    """Get the default database path using appdirs user data directory."""
    app_data_dir = appdirs.user_data_dir("jrun")
    Path(app_data_dir).mkdir(parents=True, exist_ok=True)
    return str(Path(app_data_dir) / "jrun.db")


def ask_user_yes_no_question(
    question: str = "Are you sure you want to delete the database? (y/n): ",
    on_yes: Optional[Callable] = None,
    on_no: Optional[Callable] = None,
):
    """Delete the database file if it exists."""
    confirm = input(question).strip().lower()
    if confirm == "y":
        if on_yes:
            on_yes()
        else:
            if on_no:
                on_no()
    else:
        print("Operation cancelled.")


def parse_args():
    default_db = get_default_db_path()
    parser = argparse.ArgumentParser(prog="jrun", description="Tiny Slurm helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ###### jrun submit --file workflow.yaml (run all jobs in the workflow)
    p_submit = sub.add_parser("submit", help="Submit jobs from a YAML workflow")
    p_submit.add_argument("--file", required=True, help="Path to workflow.yaml")
    p_submit.add_argument("--db", default=default_db, help="SQLite DB path")
    p_submit.add_argument(
        "--dry", action="store_true", help="Pass --dry to all job commands"
    )
    p_submit.add_argument(
        "--debug", action="store_true", help="Don't call sbatch, just print & record"
    )
    p_submit.add_argument(
        "--deptype", choices=["afterok", "afterany"], default="afterok"
    )

    ###### jrun status (get job status)
    p_status = sub.add_parser("status", help="Show job status table")
    p_status.add_argument("--db", default=default_db, help="SQLite DB path")
    p_status.add_argument(
        "--filters",
        nargs="*",
        help="Filter jobs (e.g, job_id=123  or command~train)",
        default=None,
    )

    ###### jrun sbatch (pass args straight to sbatch)
    p_sbatch = sub.add_parser("sbatch", help="Pass args straight to sbatch")
    p_sbatch.add_argument("--db", default=default_db, help="SQLite DB path")

    ###### jrun viz (visualize job dependencies)
    p_viz = sub.add_parser("viz", help="Visualize job dependencies")
    p_viz.add_argument("--db", default=default_db, help="SQLite DB path")
    p_viz.add_argument(
        "--filters",
        nargs="*",
        help="Filter jobs (e.g, job_id=123  or command~train)",
        default=None,
    )
    p_viz.add_argument(
        "--mode",
        choices=["main", "mermaid", "group", "json"],
        default="main",
        help="Visualization mode",
    )

    ###### jrun cancel (stop jobs)
    p_cancel = sub.add_parser("cancel", help="Cancel jobs")
    p_cancel.add_argument(
        "job_ids",
        nargs="*",  # Zero or more (optional)
        help="Job IDs to cancel (space-separated)",
    )
    p_cancel.add_argument(
        "--db", default=default_db, help=f"SQLite DB path (default: {default_db})"
    )

    ###### jrun delete
    p_clean = sub.add_parser("delete", help="Clear up the database")
    p_clean.add_argument("--db", default=default_db, help="SQLite DB path")
    p_clean.add_argument(
        "job_ids",
        nargs="*",  # Zero or more (optional)
        help="Job IDs to delete (space-separated)",
    )

    ###### jrun retry (resubmit jobs)
    p_retry = sub.add_parser("retry", help="Retry jobs")
    p_retry.add_argument("--db", default=default_db, help="SQLite DB path")
    p_retry.add_argument(
        "--dry", action="store_true", help="Pass --dry to all job commands"
    )
    p_retry.add_argument(
        "--force",
        action="store_true",
        help="Force resubmit even if job is not in failed state",
        default=False,
    )
    p_retry.add_argument(
        "job_ids",
        nargs="*",  # Zero or more (optional)
        help="Job IDs to retry (space-separated)",
    )
    p_retry.add_argument(
        "--deptype", choices=["afterok", "afterany"], default="afterok"
    )

    ###### jrun serve (start web interface)
    p_serve = sub.add_parser("serve", help="Start Next.js web interface server")
    p_serve.add_argument(
        "--port", type=int, default=3000, help="Port to serve on (default: 3000)"
    )
    p_serve.add_argument(
        "--host", default="localhost", help="Host to bind to (default: localhost)"
    )
    p_serve.add_argument("--db", default=default_db, help="SQLite DB path")
    p_serve.add_argument(
        "--no-browser", action="store_true", help="Don't open browser automatically"
    )

    ###### jrun info
    p_info = sub.add_parser("info", help="Show jrun info")
    p_info.add_argument(
        "--db", default=default_db, help="SQLite DB path (default: jrun.db)"
    )

    ###### jrun data
    p_data = sub.add_parser("data", help="Show jrun data")
    p_data.add_argument(
        "--db", default=default_db, help="SQLite DB path (default: jrun.db)"
    )

    # ---------- Passthrough for sbatch ----------
    args, unknown = parser.parse_known_args()
    if args.cmd == "sbatch":
        args.sbatch_args = unknown  # forward everything
    elif unknown:
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")
    return args


def get_build_directory():
    """Auto-detect the Next.js build directory"""
    # Look for jweb directory relative to main.py
    current_file = Path(__file__)
    project_root = current_file.parent.parent  # Go up from jrun/jrun/ to jrun/

    # Try different possible locations
    possible_paths = [
        project_root / "jweb" / "out",  # jrun/jweb/out
        project_root / "jweb" / "build",  # jrun/jweb/build
        Path("jweb/out"),  # Current directory
        Path("jweb/build"),  # Current directory
        Path("out"),  # Current directory
        Path("build"),  # Current directory
    ]

    for path in possible_paths:
        if path.exists() and path.is_dir():
            return str(path.absolute())

    # Default fallback
    return str(project_root / "jweb" / "out")


def main():
    args = parse_args()

    # Submit yaml workflow
    if args.cmd == "submit":
        jr = JobSubmitter(args.db, deptype=args.deptype)
        jr.submit(args.file, debug=args.debug, dry=args.dry)

    elif args.cmd == "retry":
        jr = JobSubmitter(args.db, deptype=args.deptype)
        job_ids = [int(job_id) for job_id in args.job_ids]
        for job_id in job_ids:
            jr.retry(job_id, force=args.force)

    # Show job statuses
    elif args.cmd == "status":
        jr = JobViewer(args.db)
        jr.status(args.filters)

    # Visualize job dependencies
    elif args.cmd == "viz":
        jr = JobViewer(args.db)
        viz_fn = {
            "main": jr.visualize,
            "mermaid": jr.visualize_mermaid,
            "group": jr.visualize_grouped,
            "json": jr.visualize_json,
        }[args.mode]
        viz_fn(args.filters)

    # Pass args straight to sbatch
    elif args.cmd == "sbatch":
        jr = JobSubmitter(args.db)
        jr.sbatch(args.sbatch_args)

    # Delete the database
    elif args.cmd == "delete":
        jr = JobSubmitter(args.db)
        if not args.job_ids:
            # If no job IDs are provided, ask for confirmation to delete the database
            ask_user_yes_no_question(
                question="Are you sure you want to delete the database? (y/n): ",
                on_yes=lambda: jr.delete(),
                on_no=lambda: print("Database deletion cancelled."),
            )
        jr.delete(args.job_ids, cascade=True)

    # Cancel jobs
    elif args.cmd == "cancel":
        jr = JobSubmitter(args.db)
        job_ids = [int(job_id) for job_id in args.job_ids]
        if len(job_ids) == 0:
            return jr.cancel_all()
        for job_id in job_ids:
            jr.cancel(job_id)

    # Start web server
    elif args.cmd == "serve":
        try:
            # # Auto-detect build directory if not specified
            # build_dir = args.build_dir or get_build_directory()

            # print(f"🔍 Looking for Next.js build at: {build_dir}")

            # # Check if build directory exists
            # if not Path(build_dir).exists():
            #     print(f"❌ Build directory not found: {build_dir}")
            #     print(f"💡 Please build your Next.js app first:")
            #     print(f"   cd jweb && npm run build")
            #     exit(1)

            # serve_react_app(
            #     port=args.port,
            #     host=args.host,
            #     build_dir=build_dir,
            #     open_browser=False,
            #     blocking=True,
            # )
            serve(
                db=args.db,
                host=args.host,
                port=args.port,
                web_folder="web",  # relative to project root
                # web_folder="jweb/out",  # relative to project root
            )
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            exit(1)

    # Show jrun data
    elif args.cmd == "data":
        jr = JobViewer(args.db)

    # Show jrun info
    elif args.cmd == "info":
        print(f"Using jrun database at {args.db}")

    else:
        print("Unknown command")
        exit(1)


if __name__ == "__main__":
    main()

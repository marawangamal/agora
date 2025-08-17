import os
import sys
import appdirs
import argparse
import subprocess

from typing import Callable, Optional
from pathlib import Path
from agora.job_submitter import JobSubmitter
from agora.job_viewer import JobViewer
from agora.server import serve


def get_default_db_path():
    """Get the default database path using appdirs user cache directory."""
    cache_dir = appdirs.user_cache_dir("agora")
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    return str(Path(cache_dir) / "agora.db")


def get_cache_directory():
    """Get the cache directory path for agora."""
    return appdirs.user_cache_dir("agora")


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
    parser = argparse.ArgumentParser(prog="agora", description="Tiny Slurm helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ###### agora submit --file workflow.yaml (run all jobs in the workflow)
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

    ###### agora status (get job status)
    p_status = sub.add_parser("status", help="Show job status table")
    p_status.add_argument("--db", default=default_db, help="SQLite DB path")
    p_status.add_argument(
        "filters",
        nargs="*",
        help="Filter jobs (e.g, job_id=123  or command~train)",
        default=None,
    )
    p_status.add_argument(
        "--cols",
        nargs="*",
        default=["id", "node_name", "node_id", "command", "status"],
        help="Columns to display in the status table (default: id, node_name, node_id, command, status)",
    )

    ###### agora sbatch (pass args straight to sbatch)
    p_sbatch = sub.add_parser("sbatch", help="Pass args straight to sbatch")
    p_sbatch.add_argument("--db", default=default_db, help="SQLite DB path")

    ###### agora viz (visualize job dependencies)
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

    ###### agora cancel (stop jobs)
    p_cancel = sub.add_parser("cancel", help="Cancel jobs")
    p_cancel.add_argument(
        "job_ids",
        nargs="*",  # Zero or more (optional)
        help="Job IDs to cancel (space-separated)",
    )
    p_cancel.add_argument(
        "--db", default=default_db, help=f"SQLite DB path (default: {default_db})"
    )

    ###### agora delete
    p_clean = sub.add_parser("delete", help="Clear up the database")
    p_clean.add_argument("--db", default=default_db, help="SQLite DB path")
    p_clean.add_argument(
        "-j",
        "--job_ids",
        nargs="*",  # Zero or more (optional)
        help="Job IDs to delete (space-separated)",
    )
    p_clean.add_argument(
        "-n",
        "--node_ids",
        nargs="*",
        help="Node IDs to delete (space-separated). If provided, deletes jobs for these nodes only.",
    )

    ###### agora retry (resubmit jobs)
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
    p_retry.add_argument(
        "--debug", action="store_true", help="Don't call sbatch, just print & record"
    )
    p_retry.add_argument(
        "-n",
        "--node_ids",
        nargs="*",
        help="Node IDs to delete (space-separated). If provided, deletes jobs for these nodes only.",
    )

    ###### agora serve (start web interface)
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

    ###### agora pit (tmux cockpit)
    p_pit = sub.add_parser("pit", help="Launch tmux cockpit with command monitoring")
    p_pit.add_argument("command", nargs="+", help="Command to run in the left pane")

    ###### agora info
    p_info = sub.add_parser("info", help="Show agora info")
    p_info.add_argument(
        "--db", default=default_db, help="SQLite DB path (default: agora.db)"
    )

    ###### agora data
    p_data = sub.add_parser("data", help="Show agora data")
    p_data.add_argument(
        "--db", default=default_db, help="SQLite DB path (default: agora.db)"
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
    # Look for agora directory relative to main.py
    current_file = Path(__file__)
    project_root = current_file.parent.parent  # Go up from agora/agora/ to agora/

    # Try different possible locations
    possible_paths = [
        project_root / "agora" / "out",  # agora/agora/out
        project_root / "agora" / "build",  # agora/agora/build
        Path("agora/out"),  # Current directory
        Path("agora/build"),  # Current directory
        Path("out"),  # Current directory
        Path("build"),  # Current directory
    ]

    for path in possible_paths:
        if path.exists() and path.is_dir():
            return str(path.absolute())

    # Default fallback
    return str(project_root / "agora" / "out")


def main():
    args = parse_args()

    # Submit yaml workflow
    if args.cmd == "submit":
        jr = JobSubmitter(args.db, deptype=args.deptype)
        jr.submit(args.file, debug=args.debug, dry=args.dry)

    elif args.cmd == "retry":
        jr = JobSubmitter(args.db, deptype=args.deptype)
        if args.node_ids:
            jr.retry_by_node(args.node_ids)
        else:
            for job_id in args.job_ids:
                jr.retry(job_id, force=args.force, debug=args.debug)

    # Show job statuses
    elif args.cmd == "status":
        jr = JobViewer(args.db)
        jr.status(args.filters, args.cols)

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
        if args.node_ids:
            # If node_ids are provided, delete jobs for those nodes
            jr.delete_by_node(args.node_ids)
            return
        elif args.job_ids:
            jr.delete(args.job_ids, cascade=True)
        else:
            # If no IDs are provided, ask for confirmation to delete the database
            ask_user_yes_no_question(
                question="Are you sure you want to delete the database? (y/n): ",
                on_yes=lambda: jr.delete(),
                on_no=lambda: print("Database deletion cancelled."),
            )

    # Cancel jobs
    elif args.cmd == "cancel":
        jr = JobSubmitter(args.db)
        if len(args.job_ids) == 0:
            return jr.cancel_all()
        for job_id in args.job_ids:
            jr.cancel(job_id)

    # Start web server
    elif args.cmd == "serve":
        try:
            serve(
                db=args.db,
                host=args.host,
                port=args.port,
                web_folder=os.path.join(os.path.dirname(__file__), "web"),
            )
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            exit(1)

    # Show agora data
    elif args.cmd == "data":
        jr = JobViewer(args.db)

    # Show agora info
    elif args.cmd == "info":
        cache_dir = get_cache_directory()
        print(f"📁 Cache directory: {cache_dir}")
        print(f"🗄️  Database file: {args.db}")
        print(f"📊 Database exists: {'Yes' if Path(args.db).exists() else 'No'}")

    # Launch tmux cockpit debug session
    elif args.cmd == "pit":
        script_path = Path(__file__).parent.parent / "scripts" / "tmux_cockpit.sh"
        subprocess.run(["bash", str(script_path)] + args.command)

    else:
        print("Unknown command")
        exit(1)


if __name__ == "__main__":
    main()

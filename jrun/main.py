import argparse

import appdirs
from pathlib import Path

from jrun.job_submitter import JobSubmitter
from jrun.job_viewer import JobViewer


def get_default_db_path():
    """Get the default database path using appdirs user data directory."""
    app_data_dir = appdirs.user_data_dir("jrun")
    Path(app_data_dir).mkdir(parents=True, exist_ok=True)
    return str(Path(app_data_dir) / "jrun.db")


def handle_delete_db(db_path):
    """Delete the database file if it exists."""
    confirm = (
        input("Are you sure you want to delete the database? (y/n): ").strip().lower()
    )
    if confirm == "y":
        db_path = Path(db_path)
        # Cancel all jobs before deleting the database
        jr = JobSubmitter(db_path)
        jr.cancel_all()
        if db_path.exists():
            db_path.unlink()
            print(f"Deleted database at {db_path}")
        else:
            print(f"No database found at {db_path}, nothing to delete.")
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
        choices=["main", "mermaid", "group"],
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

    # ---------- Passthough for sbatch ----------
    args, unknown = parser.parse_known_args()

    if args.cmd == "sbatch":
        args.sbatch_args = unknown  # forward everything
    elif unknown:
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")

    return args


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
        }[args.mode]
        viz_fn(args.filters)

    # Pass args straight to sbatch
    elif args.cmd == "sbatch":
        jr = JobSubmitter(args.db)
        jr.sbatch(args.sbatch_args)

    # Delete the database
    elif args.cmd == "delete":
        handle_delete_db(args.db)

    # Cancel jobs
    elif args.cmd == "cancel":
        jr = JobSubmitter(args.db)
        job_ids = [int(job_id) for job_id in args.job_ids]
        if len(job_ids) == 0:
            return jr.cancel_all()
        for job_id in job_ids:
            jr.cancel(job_id)

    else:
        print("Unknown command")
        exit(1)


if __name__ == "__main__":
    main()

import argparse

from jrun.job_submitter import JobSubmitter
from jrun.job_viewer import JobViewer


def parse_args():
    parser = argparse.ArgumentParser(prog="jrun", description="Tiny Slurm helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # jrun submit --file workflow.yaml
    p_submit = sub.add_parser("submit", help="Submit jobs from a YAML workflow")
    p_submit.add_argument("--file", required=True, help="Path to workflow.yaml")
    p_submit.add_argument("--db", default="jrun.db", help="SQLite DB path")
    p_submit.add_argument(
        "--dry", action="store_true", help="Don't call sbatch, just print & record"
    )

    # jrun status
    p_status = sub.add_parser("status", help="Show job status table")
    p_status.add_argument("--db", default="jrun.db", help="SQLite DB path")

    # jrun sbatch ... (thin passthrough)
    p_sbatch = sub.add_parser("sbatch", help="Pass args straight to sbatch")
    p_sbatch.add_argument("--db", default="jrun.db", help="SQLite DB path")

    # jrun viz
    p_viz = sub.add_parser("viz", help="Visualize job dependencies")
    p_viz.add_argument("--db", default="jrun.db", help="SQLite DB path")
    p_viz.add_argument(
        "--mode", choices=["main", "compact", "mermaid"], default="main", help="Visualization mode"
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
    if args.cmd == "submit":
        jr = JobSubmitter(args.db)
        jr.submit(args.file, dry=args.dry)
    elif args.cmd == "status":
        jr = JobViewer(args.db)
        jr.status()
    elif args.cmd == "viz":
        jr = JobViewer(args.db)
        viz_fn = {
            "main": jr.visualize,
            "compact": jr.visualize_compact,
            "mermaid": jr.visualize_mermaid,
        }[args.mode]
        viz_fn()
    elif args.cmd == "sbatch":
        jr = JobSubmitter(args.db)
        jr.sbatch(args.sbatch_args)
    else:
        print("Unknown command")
        exit(1)


if __name__ == "__main__":
    main()

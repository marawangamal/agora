import argparse


def main(args):
    print("This is a simple script to demonstrate job submission.")
    print(f"Dry run: {args.dry}")
    print(f"Job ID: {args.job_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A simple script to demonstrate job submission"
    )
    parser.add_argument(
        "--dry", action="store_true", help="Dry run, do not submit jobs"
    )
    parser.add_argument("--job-id", type=int, help="SLURM Job ID to")
    parser.add_argument(
        "--param", default=None, type=str, help="Parameter to pass to the job"
    )

    args = parser.parse_args()
    main(args)

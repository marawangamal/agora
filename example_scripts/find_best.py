import argparse


def main():
    # sleep 10s
    import time

    time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train a model with specified parameters."
    )
    # add lr,  and model
    parser.add_argument(
        "--lr", type=float, default=0.001, help="Learning rate for the model."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="resnet50",
        help="Model architecture to use for training.",
    )
    # add group_id
    parser.add_argument(
        "--group_id",
        type=str,
        default="default_group",
        help="Group ID for the training run.",
    )

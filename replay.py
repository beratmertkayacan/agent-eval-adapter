"""Replay a stored run: python replay.py run-0005"""

import argparse

from adapter.main import get_service
from adapter.recorder import RunNotFoundError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send a stored run again as a new run.")
    parser.add_argument("run_id", help="ID of the run to replay, for example run-0005")
    args = parser.parse_args(argv)

    try:
        run = get_service().replay(args.run_id)
    except RunNotFoundError as error:
        print(error)
        return 1

    status = run.normalized_response.response.status
    error = run.error.type if run.error else "none"
    print(f"{run.run_id} replays {args.run_id} (status: {status}, error: {error})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

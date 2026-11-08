"""Command-line entry point for a repeatable two-hour demo run."""

import json

from orbitlink.analytics.simulator import run_simulation


def main() -> None:
    print(json.dumps(run_simulation().summary(), indent=2))


if __name__ == "__main__":
    main()

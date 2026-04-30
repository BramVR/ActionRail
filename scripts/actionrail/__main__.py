"""Command-line project map for ActionRail."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .project import about


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show ActionRail project navigation data.")
    parser.add_argument("--json", action="store_true", help="Print the full project map as JSON.")
    args = parser.parse_args(argv)

    project = about()
    if args.json:
        print(json.dumps(project, indent=2, sort_keys=True))
        return 0

    print(f"{project['product']} {project['version']}")
    print(f"Status: {project['status']['phase']}")
    print(f"Next: {project['status']['next_slice']}")
    print("Start docs:")
    for entry in project["docs"][:3]:
        print(f"  - {entry['path']}: {entry['summary']}")
    print("Use --json for the full agent/navigation map.")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests.
    raise SystemExit(main())

import argparse
import sys
from pathlib import Path

from discourse_retrieval.archiver import Archiver
from discourse_retrieval.config import Config

_VERSION = "0.1.0"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="discourse-retrieval",
        description="Archive Discourse forum threads to local Markdown files.",
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        metavar="PATH",
        help="Path to config.toml (default: ./config.toml)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_VERSION}")
    args = parser.parse_args()

    try:
        config = Config.from_file(Path(args.config))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        Archiver(config).run()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(3)

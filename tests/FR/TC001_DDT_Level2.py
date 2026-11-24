import argparse
import json
from pathlib import Path

from utils.ddt_runner import PROJECT_ROOT, run_suite


def main():
    parser = argparse.ArgumentParser(description="Run TC001 Level 2 Selenium DDT")
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "test_data" / "tc001_ddt_config.json"),
        help="JSON file containing site URLs and element selectors",
    )
    parser.add_argument(
        "--data",
        default=str(PROJECT_ROOT / "test_data" / "add_user_test_data.csv"),
        help="Path to the test data CSV",
    )
    parser.add_argument("--base-url", help="Overrides base_url from JSON or MOODLE_BASE_URL")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the Chrome browser instead of running headless",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate and list CSV cases without opening a browser",
    )
    args = parser.parse_args()

    with Path(args.config).open(encoding="utf-8") as file:
        config = json.load(file)
    return run_suite(
        config,
        Path(args.data),
        base_url=args.base_url,
        headless=not args.headed,
        validate_only=args.validate_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())

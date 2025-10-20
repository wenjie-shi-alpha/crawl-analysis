#!/usr/bin/env python3
"""Command-line entry point for the NOAA complete crawler."""

from crawling.noaa_complete_crawler import main as _run_cli


def main() -> None:
    """Execute the interactive NOAA complete crawler workflow."""
    _run_cli()


if __name__ == "__main__":
    main()

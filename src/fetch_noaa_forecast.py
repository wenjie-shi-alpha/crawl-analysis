#!/usr/bin/env python3
"""Command-line entry point for downloading NOAA forecast text products."""

from crawling.noaa_forecast_extractor import main as _run_cli


def main() -> None:
    """Execute the interactive NOAA forecast extractor workflow."""
    _run_cli()


if __name__ == "__main__":
    main()

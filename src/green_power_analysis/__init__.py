"""Green Power Analysis package."""

from importlib.metadata import version, PackageNotFoundError

__all__ = ["__version__"]

try:
    __version__ = version("green_power_analysis")
except PackageNotFoundError:
    __version__ = "0.1.0"

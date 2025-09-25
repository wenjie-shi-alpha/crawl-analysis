"""Green Power Analysis package."""

from importlib.metadata import PackageNotFoundError, version

from dotenv import load_dotenv

__all__ = ["__version__"]

# Load environment variables from a local .env file if present so the pipeline
# picks up API keys without extra setup.
load_dotenv()

try:
    __version__ = version("green_power_analysis")
except PackageNotFoundError:
    __version__ = "0.1.0"

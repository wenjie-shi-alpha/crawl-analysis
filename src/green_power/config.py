"""Configuration models for the analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import os


DEFAULT_KEYWORDS: List[str] = [
    "绿色电力消费",
    "居民绿色电力",
    "清洁能源消费",
    "可再生能源消费",
    "绿电消费",
    "绿色电力证书",
    "居民用电行为",
    "绿色用电意愿",
]


@dataclass(slots=True)
class PipelinePaths:
    """Container for all directories used by the pipeline."""

    base_dir: Path
    results_dir: Path = field(init=False)
    raw_dir: Path = field(init=False)
    processed_dir: Path = field(init=False)
    analysis_dir: Path = field(init=False)
    output_dir: Path = field(init=False)
    charts_dir: Path = field(init=False)
    reports_dir: Path = field(init=False)
    meta_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.results_dir = self.base_dir / "output"
        self.raw_dir = self.results_dir / "raw"
        self.processed_dir = self.results_dir / "processed"
        self.analysis_dir = self.results_dir / "analysis"
        self.output_dir = self.results_dir / "final"
        self.charts_dir = self.output_dir / "charts"
        self.reports_dir = self.output_dir / "reports"
        self.meta_dir = self.results_dir / "meta"

    def ensure_directories(self) -> None:
        for path in (
            self.base_dir,
            self.results_dir,
            self.raw_dir,
            self.processed_dir,
            self.analysis_dir,
            self.output_dir,
            self.charts_dir,
            self.reports_dir,
            self.meta_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class PipelineConfig:
    """High-level configuration for the whole pipeline."""

    base_dir: Path = Path("data")
    keywords: List[str] = field(default_factory=lambda: list(DEFAULT_KEYWORDS))
    tavily_search_depth: str = "advanced"
    tavily_results_per_keyword: int = 10
    tavily_api_base_url: str = "https://api.tavily.com/search"
    tavily_request_timeout: int = 30
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    openai_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    )
    openai_base_url: str = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    openai_organization: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_ORG") or None
    )
    openai_project: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_PROJECT") or None
    )

    def paths(self) -> PipelinePaths:
        paths = PipelinePaths(self.base_dir)
        paths.ensure_directories()
        return paths

    def timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

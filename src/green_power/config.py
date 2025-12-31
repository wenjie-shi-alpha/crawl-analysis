"""Configuration models for the analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import os


DEFAULT_KEYWORDS: List[str] = [
    # 基础概念
    "绿色电力消费",
    "居民绿色电力",
    "清洁能源消费",
    "可再生能源消费",
    "绿电消费",
    "绿色电力证书",
    "居民用电行为",
    "绿色用电意愿",

    # 驱动因素
    "绿色电力消费 驱动因素",
    "绿电消费 动机",
    "可再生能源购买意愿",
    "绿色电力 政策激励",
    "绿色电力 环保意识",
    "绿电消费 经济效益",
    "绿色电力 社会责任",
    "清洁能源 消费态度",

    # 阻碍因素
    "绿色电力消费 阻碍因素",
    "绿电消费 障碍",
    "可再生能源消费 壁垒",
    "绿色电力 价格阻力",
    "绿电消费 信任问题",
    "绿色电力 便捷性",
    "可再生能源 认知障碍",
    "绿色电力 消费顾虑",

    # 政策和市场
    "中国 绿色电力政策",
    "绿电交易机制",
    "可再生能源配额",
    "绿色电力证书交易",
    "电力市场化改革 绿色",
    "双碳目标 绿色电力",

    # 实践案例
    "绿色电力消费 案例",
    "企业绿电采购",
    "家庭绿电消费",
    "绿色电力试点",
    "绿电消费模式 创新",
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
    crawler_mode: str = "tavily"
    tavily_search_depth: str = "advanced"
    tavily_results_per_keyword: int = 25  # 增加结果数量以支持学术研究
    tavily_api_base_url: str = "https://api.tavily.com/search"
    tavily_request_timeout: int = 30
    manual_sites_max_results: int = 8
    manual_sites_request_timeout: int = 20
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

    # Enhanced configuration options
    max_workers: int = 4
    batch_size: int = 10
    rate_limit: float = 1.0  # requests per second
    retry_attempts: int = 3
    retry_backoff: float = 1.0
    secure_config: bool = True
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    performance_monitoring: bool = True
    incremental_saves: bool = True
    content_max_length: int = 100000
    request_timeout: int = 30

    def paths(self) -> PipelinePaths:
        paths = PipelinePaths(self.base_dir)
        paths.ensure_directories()
        return paths

    def timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

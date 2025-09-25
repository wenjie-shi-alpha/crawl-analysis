"""Crawler implementation powered by the Tavily search API."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from ..utils.io import write_json

try:  # Imported lazily to provide a friendlier error message.
    from tavily import TavilyClient
except ImportError as exc:  # pragma: no cover - import-time guard
    raise ImportError("请先安装 tavily: pip install tavily") from exc


@dataclass(slots=True)
class TavilyCrawler:
    """Searches the web for green power content using Tavily."""

    keywords: Iterable[str]
    output_dir: str
    api_key: Optional[str] = None
    search_depth: str = "advanced"
    max_results_per_keyword: int = 10
    client: TavilyClient = field(init=False)

    def __post_init__(self) -> None:
        api_key = self.api_key or os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("未检测到 Tavily API 密钥，请设置环境变量 TAVILY_API_KEY")
        self.client = TavilyClient(api_key=api_key)

    def crawl(self) -> List[Dict]:
        """Fetches search results for all configured keywords."""
        aggregated: List[Dict] = []
        for keyword in self.keywords:
            aggregated.extend(self._search_keyword(keyword))
        return aggregated

    def _search_keyword(self, keyword: str) -> List[Dict]:
        response = self.client.search(
            query=keyword,
            search_depth=self.search_depth,
            max_results=self.max_results_per_keyword,
            include_images=False,
            include_answer=False,
        )
        now = datetime.utcnow().isoformat()
        results: List[Dict] = []
        for item in response.get("results", []):
            results.append(
                {
                    "title": item.get("title") or "",
                    "url": item.get("url") or "",
                    "content": item.get("content") or item.get("snippet") or "",
                    "source": item.get("source") or "tavily",
                    "keyword": keyword,
                    "crawl_time": now,
                }
            )
        return results

    def save(self, results: List[Dict], filename: Optional[str] = None) -> str:
        """Persist crawled results into the raw data folder."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = filename or f"tavily_results_{timestamp}.json"
        output_path = Path(self.output_dir) / name
        write_json(output_path, results)
        return str(output_path)

"""Crawler implementation powered by the Tavily search API."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import requests
from requests import Response, Session

from ..utils.io import write_json


@dataclass(slots=True)
class TavilyCrawler:
    """Searches the web for green power content using Tavily."""

    keywords: Iterable[str]
    output_dir: str
    api_key: Optional[str] = None
    search_depth: str = "advanced"
    max_results_per_keyword: int = 10
    api_base_url: str = "https://api.tavily.com/search"
    request_timeout: int = 30
    session: Session = field(init=False)
    _api_key: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        api_key = self.api_key or os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("未检测到 Tavily API 密钥，请设置环境变量 TAVILY_API_KEY")
        self._api_key = api_key
        self.session = requests.Session()
        # 将请求头更新为正确的格式
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                # 修正：使用 Authorization 请求头，并添加 "Bearer " 前缀
                "Authorization": f"Bearer {self._api_key}",
            }
        )

    def crawl(self) -> List[Dict]:
        """Fetches search results for all configured keywords."""
        aggregated: List[Dict] = []
        for keyword in self.keywords:
            aggregated.extend(self._search_keyword(keyword))
        return aggregated

    def _search_keyword(self, keyword: str) -> List[Dict]:
        payload = {
            "query": keyword,
            "search_depth": self.search_depth,
            "max_results": self.max_results_per_keyword,
            "include_images": False,
            "include_answer": False,
        }
        try:
            response: Response = self.session.post(
                self.api_base_url,
                json=payload,
                timeout=self.request_timeout,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:  # pragma: no cover - network guard
            raise RuntimeError(
                f"Tavily API 请求失败 (状态码 {exc.response.status_code}): {exc.response.text}"
            ) from exc
        except requests.exceptions.RequestException as exc:  # pragma: no cover - network guard
            raise RuntimeError(f"调用 Tavily API 时发生网络错误: {exc}") from exc

        data = response.json() if response.content else {}
        now = datetime.utcnow().isoformat()
        results: List[Dict] = []
        for item in data.get("results", []):
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

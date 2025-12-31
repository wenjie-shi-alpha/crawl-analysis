"""Manual site scraper powered by requests and BeautifulSoup."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from utils.io import write_json

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0 Safari/537.36"
)


@dataclass(slots=True)
class SiteConfig:
    """Definition of a site list page and its extractor."""

    name: str
    list_url: str
    base_url: str
    parser: Callable[[BeautifulSoup, "SiteConfig"], List[Dict]]


@dataclass(slots=True)
class LocalSiteCrawler:
    """Scrape fixed government/industry sites without using Tavily."""

    keywords: Iterable[str]
    output_dir: str
    max_articles_per_site: int = 8
    request_timeout: int = 20
    session: requests.Session = field(init=False)
    _keyword_set: List[str] = field(init=False)
    _sites: List[SiteConfig] = field(init=False)

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self._keyword_set = self._build_keyword_set(self.keywords)
        self._sites = [
            SiteConfig(
                name="中国政府网-最新政策",
                list_url="https://www.gov.cn/zhengce/zuixin/home.htm",
                base_url="https://www.gov.cn/zhengce/zuixin/",
                parser=self._parse_gov_latest,
            ),
            SiteConfig(
                name="国家发展改革委-通知",
                list_url="https://www.ndrc.gov.cn/xxgk/zcfb/tz/",
                base_url="https://www.ndrc.gov.cn/xxgk/zcfb/tz/",
                parser=self._parse_ndrc_notifications,
            ),
            SiteConfig(
                name="生态环境部-时政要闻",
                list_url="https://www.mee.gov.cn/ywdt/szyw/",
                base_url="https://www.mee.gov.cn/ywdt/szyw/",
                parser=self._parse_mee_politics,
            ),
        ]

    def crawl(self) -> List[Dict]:
        """Fetch and filter articles from configured sites."""
        aggregated: List[Dict] = []
        for site in self._sites:
            try:
                articles = self._scrape_site(site)
            except Exception as exc:  # pragma: no cover - network guard
                logger.warning("抓取 %s 失败: %s", site.name, exc)
                continue
            aggregated.extend(articles)
        return aggregated

    def save(self, results: List[Dict], filename: Optional[str] = None) -> str:
        """Persist scraped articles in the raw folder."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = filename or f"site_scrape_results_{timestamp}.json"
        output_path = Path(self.output_dir) / name
        write_json(output_path, results)
        return str(output_path)

    # ------------------------------------------------------------------ helpers
    def _scrape_site(self, site: SiteConfig) -> List[Dict]:
        response = self._get(site.list_url)
        soup = BeautifulSoup(response, "html.parser")
        candidates = site.parser(soup, site)
        selected: List[Dict] = []
        fallback: List[Dict] = []
        for article in candidates:
            matches = self._match_keywords(
                f"{article.get('title','')}{article.get('summary','')}"
            )
            content = ""
            if not matches:
                content = self._fetch_article_content(article["url"])
                matches = self._match_keywords(content)
            if matches:
                if not content:
                    content = self._fetch_article_content(article["url"])
                article["content"] = content
                article["keyword_hits"] = matches
                article["source"] = site.name
                selected.append(article)
            else:
                article["content"] = content
                article["keyword_hits"] = []
                article["source"] = site.name
                fallback.append(article)
            if len(selected) >= self.max_articles_per_site:
                break
        if selected:
            return selected[: self.max_articles_per_site]
        return fallback[: self.max_articles_per_site]

    def _get(self, url: str) -> str:
        response = self.session.get(url, timeout=self.request_timeout)
        response.raise_for_status()
        if response.encoding in (None, "ISO-8859-1"):
            response.encoding = response.apparent_encoding
        return response.text

    def _fetch_article_content(self, url: str) -> str:
        try:
            html = self._get(url)
        except Exception as exc:  # pragma: no cover - network guard
            logger.debug("获取正文失败 %s: %s", url, exc)
            return ""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in soup.select("p")
            if p.get_text(strip=True)
        ]
        if not paragraphs:
            text = soup.get_text(" ", strip=True)
            return text[:2000]
        text = "\n".join(paragraphs)
        return text[:4000]

    def _match_keywords(self, text: str) -> List[str]:
        if not text:
            return []
        hits = [kw for kw in self._keyword_set if kw in text]
        return hits

    @staticmethod
    def _build_keyword_set(keywords: Iterable[str]) -> List[str]:
        base = {kw.strip() for kw in keywords if kw and kw.strip()}
        fallback = {
            "绿电",
            "绿色电力",
            "可再生能源",
            "新能源",
            "绿色消费",
            "消费意愿",
            "绿色用电",
        }
        merged = {kw for kw in base.union(fallback) if kw}
        return sorted(merged, key=len, reverse=True)

    # ----------------------------- site-specific parsers
    def _parse_gov_latest(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        records: List[Dict] = []
        for li in soup.select("div.news_box div.list ul > li"):
            anchor = li.find("a")
            if not anchor:
                continue
            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""
            url = urljoin(site.base_url, href)
            date_span = li.find("span", class_="date")
            records.append(
                {
                    "title": title,
                    "url": url,
                    "publish_date": date_span.get_text(strip=True) if date_span else None,
                    "summary": "",
                }
            )
        return records

    def _parse_ndrc_notifications(
        self, soup: BeautifulSoup, site: SiteConfig
    ) -> List[Dict]:
        records: List[Dict] = []
        for li in soup.select("div.list ul.u-list > li"):
            anchor = li.find("a")
            if not anchor:
                continue
            href = anchor.get("href") or ""
            url = urljoin(site.base_url, href)
            date_span = li.find("span")
            records.append(
                {
                    "title": anchor.get_text(strip=True),
                    "url": url,
                    "publish_date": date_span.get_text(strip=True) if date_span else None,
                    "summary": "",
                }
            )
        return records

    def _parse_mee_politics(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        records: List[Dict] = []
        for li in soup.select("ul.cjcx_danduimg_list > li"):
            anchor = li.select_one("dl dt a.cjcx_biaobnan") or li.select_one(
                "dl dd a.cjcx_biaob"
            )
            if not anchor:
                continue
            href = anchor.get("href") or ""
            url = urljoin(site.base_url, href)
            date_span = li.select_one("span.cjcx_shijian")
            summary_para = li.select_one("dl dd p")
            records.append(
                {
                    "title": anchor.get_text(strip=True),
                    "url": url,
                    "publish_date": date_span.get_text(strip=True) if date_span else None,
                    "summary": summary_para.get_text(strip=True) if summary_para else "",
                }
            )
        return records

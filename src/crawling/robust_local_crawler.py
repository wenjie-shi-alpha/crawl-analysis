"""Robust local crawler focused on accessible and reliable websites."""

from __future__ import annotations

import logging
import time
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional
from urllib.parse import urljoin
import re

import requests
from bs4 import BeautifulSoup

from utils.io import write_json

logger = logging.getLogger(__name__)

# Reliable user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
]

@dataclass(slots=True)
class ReliableSiteConfig:
    """Definition of a reliable website with proven accessibility."""
    name: str
    list_url: str
    base_url: str
    parser: Callable[[BeautifulSoup, "ReliableSiteConfig"], List[Dict]]
    enabled: bool = True

@dataclass(slots=True)
class RobustLocalCrawler:
    """Robust crawler focusing on reliable, accessible websites."""

    keywords: Iterable[str]
    output_dir: str
    max_articles_per_site: int = 20
    request_timeout: int = 25
    delay_between_requests: float = 2.0
    session: requests.Session = field(init=False)
    _keyword_set: List[str] = field(init=False)
    _sites: List[ReliableSiteConfig] = field(init=False)

    def __post_init__(self) -> None:
        # Setup session with conservative settings
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self._keyword_set = self._build_keyword_set(self.keywords)
        self._sites = self._build_reliable_site_list()

    def _build_reliable_site_list(self) -> List[ReliableSiteConfig]:
        """Build list of reliable, tested websites."""
        sites = [
            # Government sites - generally reliable
            ReliableSiteConfig(
                name="国家发展改革委",
                list_url="https://www.ndrc.gov.cn/xxgk/zcfb/",
                base_url="https://www.ndrc.gov.cn",
                parser=self._parse_ndrc_news,
                enabled=True
            ),
            ReliableSiteConfig(
                name="生态环境部",
                list_url="https://www.mee.gov.cn/xxgk2018/xxgk/xxgk06/",
                base_url="https://www.mee.gov.cn",
                parser=self._parse_mee_news,
                enabled=True
            ),
            ReliableSiteConfig(
                name="国家能源局",
                list_url="https://www.nea.gov.cn/",
                base_url="https://www.nea.gov.cn",
                parser=self._parse_nea_news,
                enabled=True
            ),

            # News sites focused on energy
            ReliableSiteConfig(
                name="中国能源报",
                list_url="https://www.cpnn.com.cn/",
                base_url="https://www.cpnn.com.cn",
                parser=self._parse_cpnn_main,
                enabled=True
            ),
            ReliableSiteConfig(
                name="北极星电力网",
                list_url="https://www.bjx.com.cn/",
                base_url="https://www.bjx.com.cn",
                parser=self._parse_bjx_main,
                enabled=True
            ),
            ReliableSiteConfig(
                name="国际能源小数据",
                list_url="https://www.in-en.com/",
                base_url="https://www.in-en.com",
                parser=self._parse_inen_main,
                enabled=True
            ),

            # Research and industry sites
            ReliableSiteConfig(
                name="中国电力企业联合会",
                list_url="http://www.cec.org.cn/",
                base_url="http://www.cec.org.cn",
                parser=self._parse_cec_main,
                enabled=True
            ),
            ReliableSiteConfig(
                name="新华网能源频道",
                list_url="http://www.news.cn/energy/",
                base_url="http://www.news.cn",
                parser=self._parse_xinhua_energy,
                enabled=True
            ),
            ReliableSiteConfig(
                name="人民网能源频道",
                list_url="http://energy.people.com.cn/",
                base_url="http://energy.people.com.cn",
                parser=self._parse_people_energy,
                enabled=True
            ),
        ]

        return [site for site in sites if site.enabled]

    def crawl(self) -> List[Dict]:
        """Crawl reliable websites sequentially for stability."""
        logger.info(f"开始从 {len(self._sites)} 个可靠网站抓取内容")

        all_results = []

        for i, site in enumerate(self._sites, 1):
            logger.info(f"正在抓取 ({i}/{len(self._sites)}): {site.name}")

            try:
                # Add delay between requests
                if i > 1:
                    time.sleep(self.delay_between_requests)

                articles = self._scrape_site(site)
                if articles:
                    all_results.extend(articles)
                    logger.info(f"✅ {site.name}: 获取 {len(articles)} 篇文章")
                else:
                    logger.warning(f"⚠️ {site.name}: 未获取到文章")

            except Exception as e:
                logger.error(f"❌ {site.name}: 抓取失败 - {e}")
                continue

        logger.info(f"网站抓取完成，共获取 {len(all_results)} 篇文章")
        return all_results

    def _scrape_site(self, site: ReliableSiteConfig) -> List[Dict]:
        """Scrape a single site with enhanced error handling."""
        try:
            response = self.session.get(site.list_url, timeout=self.request_timeout)
            response.raise_for_status()

            if response.encoding in (None, "ISO-8859-1"):
                response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.text, "html.parser")
            candidates = site.parser(soup, site)

            selected = []
            for article in candidates[:self.max_articles_per_site]:
                try:
                    # Apply keyword matching
                    full_text = f"{article.get('title', '')} {article.get('summary', '')}"
                    matches = self._match_keywords(full_text)

                    if matches:
                        # Fetch full content if needed
                        if not article.get("content"):
                            content = self._fetch_article_content(article["url"])
                            article["content"] = content

                        article["keyword_hits"] = matches
                        article["source"] = site.name
                        article["crawl_time"] = datetime.now().isoformat()
                        selected.append(article)

                except Exception as e:
                    logger.debug(f"处理文章时出错: {e}")
                    continue

            return selected

        except requests.exceptions.Timeout:
            logger.warning(f"请求超时: {site.name}")
            return []
        except requests.exceptions.ConnectionError:
            logger.warning(f"连接失败: {site.name}")
            return []
        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTP错误 {e.response.status_code}: {site.name}")
            return []
        except Exception as e:
            logger.error(f"抓取 {site.name} 时发生错误: {e}")
            return []

    def _fetch_article_content(self, url: str) -> str:
        """Fetch article content with simple approach."""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            if response.encoding in (None, "ISO-8859-1"):
                response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove unwanted elements
            for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
                tag.decompose()

            # Try to find main content
            content_areas = [
                "div.article-content",
                "div.content",
                "div.main-content",
                "div.article-body",
                "article",
                "div#content"
            ]

            main_content = None
            for selector in content_areas:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            if not main_content:
                main_content = soup.find("body")

            if not main_content:
                return ""

            # Extract text
            paragraphs = main_content.find_all("p")
            if paragraphs:
                text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
            else:
                text = main_content.get_text(" ", strip=True)

            # Clean up
            text = re.sub(r'\s+', ' ', text)
            return text[:3000]  # Limit length

        except Exception as e:
            logger.debug(f"获取文章内容失败 {url}: {e}")
            return ""

    def _match_keywords(self, text: str) -> List[str]:
        """Check if text matches keywords."""
        if not text:
            return []

        text_lower = text.lower()
        hits = [kw for kw in self._keyword_set if kw.lower() in text_lower]
        return hits

    @staticmethod
    def _build_keyword_set(keywords: Iterable[str]) -> List[str]:
        """Build comprehensive keyword set."""
        base = {kw.strip() for kw in keywords if kw and kw.strip()}

        # Add related terms
        related = {
            "绿电", "绿色电力", "可再生能源", "新能源", "清洁能源",
            "风电", "光伏", "太阳能", "水电", "生物质能",
            "碳达峰", "碳中和", "节能减排", "能源转型",
            "电力市场", "绿证", "绿色证书", "碳交易",
            "能源消费", "用电", "发电", "电网", "储能"
        }

        merged = {kw for kw in base.union(related) if kw}
        return sorted(merged, key=len, reverse=True)

    # Site-specific parsers - simplified but effective
    def _parse_ndrc_news(self, soup: BeautifulSoup, site: ReliableSiteConfig) -> List[Dict]:
        """Parse NDRC news."""
        records = []

        # Try different selectors
        selectors = [
            "div.list ul li",
            "ul.u-list li",
            "div.news-list li"
        ]

        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items:
                break

        for li in items[:self.max_articles_per_site]:
            anchor = li.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title or len(title) < 10:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_mee_news(self, soup: BeautifulSoup, site: ReliableSiteConfig) -> List[Dict]:
        """Parse MEE news."""
        records = []

        items = soup.select("div.list li, ul.news-list li")

        for li in items[:self.max_articles_per_site]:
            anchor = li.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_nea_news(self, soup: BeautifulSoup, site: ReliableSiteConfig) -> List[Dict]:
        """Parse NEA news."""
        records = []

        items = soup.select("div.news-item, li, article")

        for item in items[:self.max_articles_per_site]:
            anchor = item.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_cpnn_main(self, soup: BeautifulSoup, site: ReliableSiteConfig) -> List[Dict]:
        """Parse CPNN main page."""
        records = []

        # Look for energy-related news
        items = soup.select("div.news, div.item, article, li")

        for item in items[:self.max_articles_per_site]:
            anchor = item.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title or len(title) < 15:  # Filter for meaningful titles
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_bjx_main(self, soup: BeautifulSoup, site: ReliableSiteConfig) -> List[Dict]:
        """Parse BJX main page."""
        records = []

        items = soup.select("div.news-list li, div.item, article")

        for item in items[:self.max_articles_per_site]:
            anchor = item.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_inen_main(self, soup: BeautifulSoup, site: ReliableSiteConfig) -> List[Dict]:
        """Parse IN-EN main page."""
        records = []

        items = soup.select("div.news, div.item, article, li")

        for item in items[:self.max_articles_per_site]:
            anchor = item.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_cec_main(self, soup: BeautifulSoup, site: ReliableSiteConfig) -> List[Dict]:
        """Parse CEC main page."""
        records = []

        items = soup.select("div.news, li, article")

        for item in items[:self.max_articles_per_site]:
            anchor = item.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_xinhua_energy(self, soup: BeautifulSoup, site: ReliableSiteConfig) -> List[Dict]:
        """Parse Xinhua Energy."""
        records = []

        items = soup.select("div.news, li, article")

        for item in items[:self.max_articles_per_site]:
            anchor = item.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_people_energy(self, soup: BeautifulSoup, site: ReliableSiteConfig) -> List[Dict]:
        """Parse People Energy."""
        records = []

        items = soup.select("div.news, li, article")

        for item in items[:self.max_articles_per_site]:
            anchor = item.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def save(self, results: List[Dict], filename: Optional[str] = None) -> str:
        """Save scraped results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = filename or f"robust_local_crawl_{timestamp}.json"
        output_path = Path(self.output_dir) / name
        write_json(output_path, results)
        return str(output_path)
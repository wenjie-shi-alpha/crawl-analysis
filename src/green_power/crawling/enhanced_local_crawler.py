"""Enhanced local crawler with expanded data sources and concurrent processing."""

from __future__ import annotations

import logging
import time
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse
import re

import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.io import write_json
from utils.network import create_session, RetryConfig
from utils.logging_config import ProgressTracker

logger = logging.getLogger(__name__)

# Rotate user agents to avoid blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
]

@dataclass(slots=True)
class SiteConfig:
    """Definition of a site list page and its extractor."""
    name: str
    list_url: str
    base_url: str
    parser: Callable[[BeautifulSoup, "SiteConfig"], List[Dict]]
    enabled: bool = True
    priority: int = 1  # 1=high, 2=medium, 3=low

@dataclass(slots=True)
class EnhancedLocalCrawler:
    """Enhanced crawler with more data sources and concurrent processing."""

    keywords: Iterable[str]
    output_dir: str
    max_articles_per_site: int = 15
    request_timeout: int = 30
    max_workers: int = 3
    delay_between_requests: float = 1.0
    retry_attempts: int = 3
    session: requests.Session = field(init=False)
    _keyword_set: List[str] = field(init=False)
    _sites: List[SiteConfig] = field(init=False)

    def __post_init__(self) -> None:
        # Setup enhanced session with retry
        retry_config = RetryConfig(
            max_retries=self.retry_attempts,
            backoff_factor=1.0
        )
        self.session = create_session(
            retry_config=retry_config,
            rate_limit=1.0 / self.delay_between_requests
        )

        # Rotate user agent
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self._keyword_set = self._build_keyword_set(self.keywords)
        self._sites = self._build_site_list()

    def _build_site_list(self) -> List[SiteConfig]:
        """Build comprehensive list of sites to crawl."""
        sites = [
            # High priority - Government sites
            SiteConfig(
                name="中国政府网-最新政策",
                list_url="https://www.gov.cn/zhengce/zuixin/home.htm",
                base_url="https://www.gov.cn",
                parser=self._parse_gov_latest,
                priority=1
            ),
            SiteConfig(
                name="国家发展改革委-通知公告",
                list_url="https://www.ndrc.gov.cn/xxgk/zcfb/tz/",
                base_url="https://www.ndrc.gov.cn",
                parser=self._parse_ndrc_notifications,
                priority=1
            ),
            SiteConfig(
                name="生态环境部-时政要闻",
                list_url="https://www.mee.gov.cn/ywdt/szyw/",
                base_url="https://www.mee.gov.cn",
                parser=self._parse_mee_politics,
                priority=1
            ),
            SiteConfig(
                name="国家能源局-政策文件",
                list_url="https://www.nea.gov.cn/",
                base_url="https://www.nea.gov.cn",
                parser=self._parse_nea_policies,
                priority=1
            ),
            SiteConfig(
                name="住房和城乡建设部-政策发布",
                list_url="http://www.mohurd.gov.cn/zcfb/index.html",
                base_url="http://www.mohurd.gov.cn",
                parser=self._parse_mohurd_policies,
                priority=1
            ),

            # Medium priority - Industry associations
            SiteConfig(
                name="中国电力企业联合会",
                list_url="http://www.cec.org.cn/",
                base_url="http://www.cec.org.cn",
                parser=self._parse_cec_news,
                priority=2
            ),
            SiteConfig(
                name="中国可再生能源学会",
                list_url="http://www.cresa.org.cn/",
                base_url="http://www.cresa.org.cn",
                parser=self._parse_cresa_news,
                priority=2
            ),
            SiteConfig(
                name="中国新能源网",
                list_url="https://www.china-nengyuan.com/",
                base_url="https://www.china-nengyuan.com",
                parser=self._parse_china_nengyuan,
                priority=2
            ),

            # Medium priority - News sites
            SiteConfig(
                name="中国能源报",
                list_url="http://www.cpnn.com.cn/",
                base_url="http://www.cpnn.com.cn",
                parser=self._parse_cpnn_news,
                priority=2
            ),
            SiteConfig(
                name="北极星电力网",
                list_url="https://www.bjx.com.cn/",
                base_url="https://www.bjx.com.cn",
                parser=self._parse_bjx_news,
                priority=2
            ),
            SiteConfig(
                name="国际能源网",
                list_url="https://www.in-en.com/",
                base_url="https://www.in-en.com",
                parser=self._parse_inen_news,
                priority=2
            ),

            # Low priority - Research institutes
            SiteConfig(
                name="清华大学能源互联网创新研究院",
                list_url="https://www.eiri.tsinghua.edu.cn/",
                base_url="https://www.eiri.tsinghua.edu.cn",
                parser=self._parse_tsinghua_eiri,
                priority=3
            ),
            SiteConfig(
                name="国家发改委能源研究所",
                list_url="http://www.eri.org.cn/",
                base_url="http://www.eri.org.cn",
                parser=self._parse_eri_news,
                priority=3
            ),
        ]

        # Only return enabled sites
        return [site for site in sites if site.enabled]

    def crawl(self) -> List[Dict]:
        """Fetch and filter articles from configured sites with concurrent processing."""
        logger.info(f"开始从 {len(self._sites)} 个网站抓取内容")

        # Sort sites by priority
        sites_sorted = sorted(self._sites, key=lambda x: x.priority)

        all_results = []
        progress = ProgressTracker(
            total=len(sites_sorted),
            task_name="网站抓取",
            logger=logger
        )

        # Process sites with limited concurrency
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_site = {}

            for site in sites_sorted:
                future = executor.submit(self._scrape_site_safe, site)
                future_to_site[future] = site

            for future in as_completed(future_to_site):
                site = future_to_site[future]
                try:
                    articles = future.result(timeout=60)  # 60 second timeout per site
                    if articles:
                        all_results.extend(articles)
                        logger.info(f"✅ {site.name}: 获取 {len(articles)} 篇文章")
                    else:
                        logger.warning(f"⚠️ {site.name}: 未获取到文章")
                    progress.update(1, f"完成 {site.name}")
                except Exception as e:
                    logger.error(f"❌ {site.name}: 抓取失败 - {e}")
                    progress.update(1, f"{site.name} 失败")

        logger.info(f"网站抓取完成，共获取 {len(all_results)} 篇文章")
        return all_results

    def _scrape_site_safe(self, site: SiteConfig) -> List[Dict]:
        """Safe wrapper for site scraping with error handling."""
        try:
            return self._scrape_site(site)
        except Exception as e:
            logger.error(f"抓取网站 {site.name} 时发生错误: {e}")
            return []

    def _scrape_site(self, site: SiteConfig) -> List[Dict]:
        """Scrape a single site for articles."""
        logger.debug(f"正在抓取: {site.name}")

        try:
            response = self._get(site.list_url)
            soup = BeautifulSoup(response, "html.parser")
            candidates = site.parser(soup, site)

            selected = []
            for article in candidates[:self.max_articles_per_site]:
                try:
                    # Apply keyword matching
                    full_text = f"{article.get('title', '')} {article.get('summary', '')}"
                    matches = self._match_keywords(full_text)

                    if matches:
                        # Fetch full content if not already present
                        if not article.get("content"):
                            article["content"] = self._fetch_article_content(article["url"])

                        article["keyword_hits"] = matches
                        article["source"] = site.name
                        article["crawl_time"] = datetime.now().isoformat()
                        selected.append(article)

                except Exception as e:
                    logger.warning(f"处理文章时出错: {e}")
                    continue

            logger.debug(f"{site.name}: 找到 {len(selected)} 篇匹配文章")
            return selected

        except Exception as e:
            logger.error(f"抓取 {site.name} 列表页失败: {e}")
            return []

    def _get(self, url: str) -> str:
        """Enhanced GET with better error handling."""
        try:
            # Rotate user agent
            self.session.headers["User-Agent"] = random.choice(USER_AGENTS)

            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()

            if response.encoding in (None, "ISO-8859-1"):
                response.encoding = response.apparent_encoding

            return response.text
        except requests.exceptions.Timeout:
            raise Exception(f"请求超时: {url}")
        except requests.exceptions.ConnectionError:
            raise Exception(f"连接失败: {url}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP错误 {e.response.status_code}: {url}")
        except Exception as e:
            raise Exception(f"未知错误: {url} - {e}")

    def _fetch_article_content(self, url: str) -> str:
        """Fetch full article content with retry logic."""
        try:
            html = self._get(url)
            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
                tag.decompose()

            # Try to find main content areas
            content_selectors = [
                "div.article-content",
                "div.content",
                "div.main-content",
                "div.article-body",
                "div.post-content",
                "article",
                "div#content",
                "div.article",
                "main"
            ]

            main_content = None
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            # Fallback to body if no specific content area found
            if not main_content:
                main_content = soup.find("body")

            if not main_content:
                return ""

            # Extract text from paragraphs
            paragraphs = main_content.find_all("p")
            if paragraphs:
                text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
            else:
                text = main_content.get_text(" ", strip=True)

            # Clean up text
            text = re.sub(r'\s+', ' ', text)
            return text[:5000]  # Limit to 5000 characters

        except Exception as e:
            logger.debug(f"获取文章内容失败 {url}: {e}")
            return ""

    def _match_keywords(self, text: str) -> List[str]:
        """Check if text matches any of our keywords."""
        if not text:
            return []

        text_lower = text.lower()
        hits = [kw for kw in self._keyword_set if kw.lower() in text_lower]
        return hits

    @staticmethod
    def _build_keyword_set(keywords: Iterable[str]) -> List[str]:
        """Build comprehensive keyword set including related terms."""
        base = {kw.strip() for kw in keywords if kw and kw.strip()}

        # Add related terms
        related = {
            "绿电", "绿色电力", "可再生能源", "新能源", "绿色能源", "清洁能源",
            "风电", "光伏", "太阳能", "水电", "生物质能", "地热能",
            "碳达峰", "碳中和", "碳排放", "节能减排", "能源转型",
            "电力市场", "绿证", "绿色证书", "碳交易", "节能减排",
            "能源消费", "用电", "发电", "电网", "储能", "充电桩"
        }

        merged = {kw for kw in base.union(related) if kw}
        return sorted(merged, key=len, reverse=True)

    # Site-specific parsers (enhanced versions)
    def _parse_gov_latest(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        """Parse government website latest policies."""
        records = []

        # Try multiple selectors for robustness
        selectors = [
            "div.news_box div.list ul > li",
            "ul.xw_list1 > li",
            "div.list ul li",
            "div.content ul li",
            "ul.news-list li"
        ]

        for selector in selectors:
            items = soup.select(selector)
            if items:
                logger.debug(f"政府网使用选择器: {selector}, 找到 {len(items)} 项")
                break

        for li in items[:self.max_articles_per_site]:
            anchor = li.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title or len(title) < 5:
                continue

            url = urljoin(site.base_url, href)

            # Try to get date
            date_elem = li.find("span", class_="date") or li.find("time")
            date = date_elem.get_text(strip=True) if date_elem else ""

            records.append({
                "title": title,
                "url": url,
                "publish_date": date,
                "summary": ""
            })

        return records

    def _parse_ndrc_notifications(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        """Parse NDRC notifications."""
        records = []

        selectors = [
            "div.list ul.u-list > li",
            "ul.u-list > li",
            "div.content-list li",
            "div.article-list li"
        ]

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

            if not title or len(title) < 5:
                continue

            url = urljoin(site.base_url, href)

            # Try to get date
            date_elem = li.find("span") or li.find("time")
            date = date_elem.get_text(strip=True) if date_elem else ""

            records.append({
                "title": title,
                "url": url,
                "publish_date": date,
                "summary": ""
            })

        return records

    def _parse_mee_politics(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        """Parse MEE politics news."""
        records = []

        selectors = [
            "ul.cjcx_danduimg_list > li",
            "ul.news-list > li",
            "div.list ul li"
        ]

        for selector in selectors:
            items = soup.select(selector)
            if items:
                break

        for li in items[:self.max_articles_per_site]:
            # Try multiple anchor selectors
            anchor = (li.select_one("dl dt a.cjcx_biaobnan") or
                     li.select_one("dl dd a.cjcx_biaob") or
                     li.find("a"))

            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title or len(title) < 5:
                continue

            url = urljoin(site.base_url, href)

            # Try to get date and summary
            date_elem = li.select_one("span.cjcx_shijian") or li.find("time")
            date = date_elem.get_text(strip=True) if date_elem else ""

            summary_elem = li.select_one("dl dd p")
            summary = summary_elem.get_text(strip=True) if summary_elem else ""

            records.append({
                "title": title,
                "url": url,
                "publish_date": date,
                "summary": summary[:200] if summary else ""
            })

        return records

    # Additional parsers for other sites
    def _parse_nea_policies(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        """Parse NEA policies."""
        records = []

        # General approach for NEA
        items = soup.select("div.list li, ul.news-list li, article")

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

    def _parse_mohurd_policies(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        """Parse MOHURD policies."""
        records = []

        items = soup.select("li, div.item, article")

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

    def _parse_cec_news(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        """Parse CEC news."""
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

    # Simplified parsers for other sites (can be expanded)
    def _parse_cresa_news(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        return self._parse_generic_news(soup, site)

    def _parse_china_nengyuan(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        return self._parse_generic_news(soup, site)

    def _parse_cpnn_news(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        return self._parse_generic_news(soup, site)

    def _parse_bjx_news(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        return self._parse_generic_news(soup, site)

    def _parse_inen_news(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        return self._parse_generic_news(soup, site)

    def _parse_tsinghua_eiri(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        return self._parse_generic_news(soup, site)

    def _parse_eri_news(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        return self._parse_generic_news(soup, site)

    def _parse_generic_news(self, soup: BeautifulSoup, site: SiteConfig) -> List[Dict]:
        """Generic parser for sites without specific implementation."""
        records = []

        # Try common selectors
        selectors = [
            "li a",
            "div.item a",
            "article a",
            "h2 a", "h3 a", "h4 a",
            ".title a",
            ".news-title a"
        ]

        anchors = []
        for selector in selectors:
            anchors = soup.select(selector)
            if anchors:
                break

        for anchor in anchors[:self.max_articles_per_site]:
            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title or len(title) < 10:  # Filter out very short titles
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
        """Save scraped articles."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = filename or f"enhanced_local_crawl_{timestamp}.json"
        output_path = Path(self.output_dir) / name
        write_json(output_path, results)
        return str(output_path)
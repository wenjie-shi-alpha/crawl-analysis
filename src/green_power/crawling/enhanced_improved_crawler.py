"""Enhanced improved local crawler with better content extraction and quality control."""

from __future__ import annotations

import logging
import time
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse
import hashlib

import requests
from bs4 import BeautifulSoup

from utils.io import write_json

logger = logging.getLogger(__name__)

# 增强的User-Agent列表，更像真实浏览器
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
]

@dataclass(slots=True)
class ImprovedSiteConfig:
    """改进的网站配置，包含更详细的抓取策略."""
    name: str
    list_url: str
    base_url: str
    parser: Callable[[BeautifulSoup, "ImprovedSiteConfig"], List[Dict]]
    enabled: bool = True
    priority: int = 1
    article_url_patterns: List[str] = field(default_factory=list)  # 文章URL模式
    exclude_url_patterns: List[str] = field(default_factory=list)  # 排除URL模式

@dataclass(slots=True)
class EnhancedImprovedCrawler:
    """增强改进的本地爬虫，专注于高质量内容抓取。"""

    keywords: Iterable[str]
    output_dir: str
    max_articles_per_site: int = 15
    request_timeout: int = 30
    delay_between_requests: float = 2.0
    min_content_length: int = 500  # 最小内容长度
    session: requests.Session = field(init=False)
    _keyword_set: List[str] = field(init=False)
    _sites: List[ImprovedSiteConfig] = field(init=False)
    _visited_urls: set = field(default_factory=set)  # 避免重复URL

    def __post_init__(self) -> None:
        # Setup session with better configuration
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        })

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self._keyword_set = self._build_enhanced_keyword_set(self.keywords)
        self._sites = self._build_enhanced_site_list()

    def _build_enhanced_keyword_set(self, keywords: Iterable[str]) -> List[str]:
        """构建增强的关键词集合，包含更多相关术语。"""
        base = {kw.strip() for kw in keywords if kw and kw.strip()}

        # 扩展相关术语
        related = {
            # 基础术语
            "绿电", "绿色电力", "可再生能源", "新能源", "清洁能源", "绿色能源",
            "风电", "光伏", "太阳能", "水电", "生物质能", "地热能", "海洋能",
            "核能", "氢能", "储能", "微电网", "智能电网", "分布式能源",

            # 消费相关
            "绿色电力消费", "居民绿色电力", "清洁能源消费", "可再生能源消费",
            "绿电消费", "绿色电力证书", "绿证", "绿证交易", "绿色用电",
            "居民用电行为", "绿色用电意愿", "消费模式", "用电结构", "电力消费",

            # 政策市场
            "碳达峰", "碳中和", "碳交易", "碳排放", "节能减排", "能源转型",
            "双碳目标", "低碳发展", "绿色发展", "可持续发展", "能源革命",
            "电力市场", "绿电交易", "市场化交易", "电力改革", "能源互联网",

            # 技术应用
            "充电桩", "电动汽车", "新能源车", "充电基础设施", "电池技术",
            "光伏发电", "风力发电", "新能源并网", "电网接入", "电力调度",

            # 具体行业
            "绿色建筑", "绿色制造", "工业园区", "数据中心", "智慧城市",
            "绿色交通", "新能源产业", "储能电站", "抽水蓄能", "调峰调频"
        }

        merged = {kw for kw in base.union(related) if kw}
        return sorted(merged, key=len, reverse=True)

    def _build_enhanced_site_list(self) -> List[ImprovedSiteConfig]:
        """构建增强的网站列表，专注于高质量内容。"""
        sites = [
            # 政府政策网站 - 高质量官方内容
            ImprovedSiteConfig(
                name="国家发改委-政策文件",
                list_url="https://www.ndrc.gov.cn/xxgk/zcfb/",
                base_url="https://www.ndrc.gov.cn",
                parser=self._parse_ndrc_policies,
                article_url_patterns=[
                    r"/zcfb/.*\.html",
                    r"/xxgk/.*\.html"
                ],
                exclude_url_patterns=[
                    r"/index\.html$",
                    r"/#",
                    r"/\?",
                    r"^javascript:"
                ]
            ),
            ImprovedSiteConfig(
                name="国家能源局-政策发布",
                list_url="https://www.nea.gov.cn/",
                base_url="https://www.nea.gov.cn",
                parser=self._parse_nea_policies,
                article_url_patterns=[
                    r"/.*\.html",
                    r"/.*\.htm"
                ]
            ),
            ImprovedSiteConfig(
                name="生态环境部-政策文件",
                list_url="https://www.mee.gov.cn/xxgk2018/xxgk/",
                base_url="https://www.mee.gov.cn",
                parser=self._parse_mee_policies,
                article_url_patterns=[
                    r"/.*\.html",
                    r"/.*\.htm"
                ]
            ),

            # 行业专业媒体 - 深度行业分析
            ImprovedSiteConfig(
                name="中国能源报-深度报道",
                list_url="https://www.cpnn.com.cn/",
                base_url="https://www.cpnn.com.cn",
                parser=self._parse_cpnn_articles,
                article_url_patterns=[
                    r"/news/.*",
                    r"/article/.*",
                    r"/hy/.*"  # 行业观察
                ]
            ),
            ImprovedSiteConfig(
                name="北极星电力网-行业新闻",
                list_url="https://www.bjx.com.cn/",
                base_url="https://www.bjx.com.cn",
                parser=self._parse_bjx_articles,
                article_url_patterns=[
                    r"/news/.*",
                    r"/html/.*-\\d{4}.*\\.html",
                    r"/.*-\\d{6}\\.html"
                ]
            ),
            ImprovedSiteConfig(
                name="国际能源小数据-深度分析",
                list_url="https://www.in-en.com/",
                base_url="https://www.in-en.com",
                parser=self._parse_inen_articles,
                article_url_patterns=[
                    r"/news/.*",
                    r"/analysis/.*",
                    r"/html/.*-\\d{4}.*\\.html"
                ]
            ),

            # 研究机构 - 权威研究报告
            ImprovedSiteConfig(
                name="中国电力企业联合会-研究报告",
                list_url="http://www.cec.org.cn/",
                base_url="http://www.cec.org.cn",
                parser=self._parse_cec_reports,
                article_url_patterns=[
                    r"/research/.*",
                    r"/report/.*",
                    r"/.*report.*\\.html",
                    r"/.*study.*\\.html"
                ]
            ),
            ImprovedSiteConfig(
                name="能源基金会-研究报告",
                list_url="https://www.efchina.org/",
                base_url="https://www.efchina.org",
                parser=self._parse_ef_reports,
                article_url_patterns=[
                    r"/Attachments/.*",
                    r"/research/.*",
                    r"/program/.*",
                    r"/.*\\.pdf$"
                ]
            ),

            # 权威媒体能源频道
            ImprovedSiteConfig(
                name="新华网-能源频道",
                list_url="http://www.news.cn/energy/",
                base_url="http://www.news.cn",
                parser=self._parse_xinhua_energy,
                article_url_patterns=[
                    r"/energy/.*\\.c.*\\.html",
                    r"/politics/.*\\.c.*\\.html",
                    r"/.*-\\d{8}.*\\.html"
                ]
            ),
            ImprovedSiteConfig(
                name="人民网-能源频道",
                list_url="http://energy.people.com.cn/",
                base_url="http://energy.people.com.cn",
                parser=self._parse_people_energy,
                article_url_patterns=[
                    r"/n1/.*\\.c.*\\.html",
                    r"/.*-\\d{8}.*\\.html",
                    r"/.*htm"
                ]
            ),
        ]

        return [site for site in sites if site.enabled]

    def crawl(self) -> List[Dict]:
        """执行增强的抓取流程。"""
        logger.info(f"开始增强抓取，目标网站: {len(self._sites)}个")

        all_results = []
        successful_sites = 0
        failed_sites = 0

        for i, site in enumerate(self._sites, 1):
            logger.info(f"正在抓取 ({i}/{len(self._sites)}): {site.name}")

            try:
                if i > 1:
                    time.sleep(self.delay_between_requests)

                # 随机更换User-Agent
                self.session.headers["User-Agent"] = random.choice(USER_AGENTS)

                articles = self._scrape_site_enhanced(site)
                if articles:
                    # 过滤低质量内容
                    quality_articles = [a for a in articles if a.get('quality_score', 0) >= 60]

                    if quality_articles:
                        all_results.extend(quality_articles)
                        successful_sites += 1
                        avg_quality = sum(a.get('quality_score', 0) for a in quality_articles) / len(quality_articles)
                        logger.info(f"✅ {site.name}: 获取 {len(quality_articles)} 篇高质量文章 (平均质量: {avg_quality:.1f})")
                    else:
                        logger.warning(f"⚠️ {site.name}: 获取 {len(articles)}篇文章但质量不达标")
                else:
                    logger.warning(f"⚠️ {site.name}: 未获取到文章")
                    failed_sites += 1

            except Exception as e:
                logger.error(f"❌ {site.name}: 抓取失败 - {e}")
                failed_sites += 1
                continue

        # 去重和最终质量检查
        final_results = self._deduplicate_and_filter(all_results)

        logger.info(f"增强抓取完成:")
        logger.info(f"   - 成功网站: {successful_sites}/{len(self._sites)}")
        logger.info(f"   - 失败网站: {failed_sites}")
        logger.info(f"   - 原始文章: {len(all_results)}")
        logger.info(f"   - 高质量文章: {len(final_results)}")
        logger.info(f"   - 去重后文章: {len(final_results)}")

        return final_results

    def _scrape_site_enhanced(self, site: ImprovedSiteConfig) -> List[Dict]:
        """增强的网站抓取方法。"""
        try:
            response = self.session.get(site.list_url, timeout=self.request_timeout)
            response.raise_for_status()

            if response.encoding in (None, "ISO-8859-1"):
                response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.text, "html.parser")
            candidates = site.parser(soup, site)

            selected = []
            for article in candidates[:self.max_articles_per_site * 2]:  # 多抓一些用于筛选
                try:
                    # 获取详细内容
                    if not article.get("content"):
                        content = self._fetch_detailed_content(article["url"])
                        article["content"] = content

                    # 内容质量评估
                    quality_score = self._assess_content_quality(article)
                    article["quality_score"] = quality_score

                    # 关键词匹配
                    full_text = f"{article.get('title', '')} {article.get('content', '')}"
                    matches = self._match_keywords(full_text)
                    article["keyword_hits"] = matches

                    # 元数据
                    article["source"] = site.name
                    article["crawl_time"] = datetime.now().isoformat()

                    selected.append(article)

                except Exception as e:
                    logger.debug(f"处理文章时出错: {e}")
                    continue

            return selected

        except requests.exceptions.Timeout:
            raise Exception(f"请求超时")
        except requests.exceptions.ConnectionError:
            raise Exception(f"连接失败")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP错误 {e.response.status_code}")
        except Exception as e:
            raise Exception(f"未知错误: {e}")

    def _fetch_detailed_content(self, url: str) -> str:
        """获取详细的文章内容。"""
        # 避免重复抓取
        url_hash = hashlib.md5(url.encode()).hexdigest()
        if url_hash in self._visited_urls:
            return ""
        self._visited_urls.add(url_hash)

        try:
            # 增加随机延迟，避免被封
            time.sleep(random.uniform(0.5, 1.5))

            response = self.session.get(url, timeout=25)
            response.raise_for_status()

            if response.encoding in (None, "ISO-8859-1"):
                response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.text, "html.parser")

            # 移除不需要的元素
            for tag in soup.select("script, style, noscript, header, footer, nav, .ad, .advertisement, .sidebar, .menu, .navigation"):
                tag.decompose()

            # 尝试多种内容选择器
            content_selectors = [
                # 文章内容区域
                "div.article-content",
                "div.post-content",
                "div.entry-content",
                "div[itemprop='articleBody']",
                "article",
                "main",
                "#main-content",
                ".content-area",
                ".post-content",
                ".article-body",

                # 新闻文章特定选择器
                ".article-body",
                ".news-content",
                ".post-body",
                ".content-body",
                "#article-content",
                ".story-body",

                # 通用内容区域
                "div.content",
                ".content",
                "div.main-content",
                "#content"
            ]

            main_content = None
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            if not main_content:
                # 最后尝试body
                main_content = soup.find("body")

            if not main_content:
                return ""

            # 提取段落
            paragraphs = []
            for p in main_content.find_all("p"):
                text = p.get_text(" ", strip=True)
                if len(text) > 30:  # 过滤掉太短的段落
                    # 过滤掉明显的导航或广告文字
                    if not self._is_navigation_or_ad_text(text):
                        paragraphs.append(text)

            # 如果段落太少，尝试其他元素
            if len(paragraphs) < 2:
                for tag in main_content.find_all(["div", "section"]):
                    text = tag.get_text(" ", strip=True)
                    if len(text) > 200 and not self._is_navigation_or_ad_text(text):
                        paragraphs.append(text)

            content = " ".join(paragraphs)

            # 基本清理
            content = re.sub(r'\s+', ' ', content)
            content = content.strip()

            # 内容质量检查
            if len(content) < self.min_content_length:
                return ""

            # 移除常见的无用模式
            patterns_to_remove = [
                r'点击.*查看更多',
                r'更多.*信息',
                r'继续阅读',
                r'点击.*查看',
                r'详情.*请.*',
                r'联系电话.*',
                r'邮箱地址.*',
                r'地址.*邮编.*'
            ]

            for pattern in patterns_to_remove:
                content = re.sub(pattern, '', content, flags=re.IGNORECASE)

            return content[:8000]  # 限制长度

        except Exception as e:
            logger.debug(f"获取详细内容失败 {url}: {e}")
            return ""

    def _is_navigation_or_ad_text(self, text: str) -> bool:
        """判断是否为导航或广告文本。"""
        # 导航文本常见模式
        nav_patterns = [
            r'首页',
            r'登录',
            r'注册',
            r'联系我们',
            r'关于我们',
            r'产品中心',
            r'新闻中心',
            r'服务项目',
            r'网站地图',
            r'友情链接',
            r'版权所有',
            r'^\s*$',
            r'^\s*[-=_]+\s*$',
            r'^\s*\d+\.\s*$'  # 纯数字
        ]

        # 广告文本常见模式
        ad_patterns = [
            r'广告',
            r'推广',
            r'热线',
            r'客服',
            r'咨询',
            r'立即.*购买',
            r'免费.*试用',
            r'点击.*了解',
            r'电话.*',
            r'微信.*二维码'
        ]

        combined_patterns = nav_patterns + ad_patterns

        for pattern in combined_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # 检查是否包含足够的中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_chars < 5:
            return True

        return False

    def _assess_content_quality(self, article: Dict) -> float:
        """评估内容质量。"""
        score = 0

        # 标题质量 (30分)
        title = article.get('title', '')
        if len(title) >= 10 and len(title) <= 100:
            score += 15
        elif len(title) >= 5:
            score += 10

        # 内容长度 (40分)
        content = article.get('content', '')
        if len(content) >= 1000:
            score += 40
        elif len(content) >= 500:
            score += 30
        elif len(content) >= 200:
            score += 20
        elif len(content) >= self.min_content_length:
            score += 10

        # 关键词匹配 (20分)
        keyword_hits = article.get('keyword_hits', [])
        if len(keyword_hits) >= 3:
            score += 20
        elif len(keyword_hits) >= 2:
            score += 15
        elif len(keyword_hits) >= 1:
            score += 10

        # URL质量 (10分)
        url = article.get('url', '')
        if url and not any(pattern in url for pattern in ['/', 'index', 'list']):
            score += 5
        if url and not any(pattern in url for pattern in ['javascript:', 'mailto:', '#']):
            score += 5

        return min(score, 100)

    def _match_keywords(self, text: str) -> List[str]:
        """关键词匹配。"""
        if not text:
            return []

        text_lower = text.lower()
        hits = [kw for kw in self._keyword_set if kw.lower() in text_lower]
        return hits

    def _deduplicate_and_filter(self, results: List[Dict]) -> List[Dict]:
        """去重和最终过滤。"""
        if not results:
            return []

        # 按标题和URL去重
        seen = set()
        unique_results = []

        for result in results:
            title = result.get('title', '').strip()
            url = result.get('url', '').strip()
            content = result.get('content', '')

            # 创建唯一标识
            identifier = f"{title}|{url}|{hashlib.md5(content.encode()).hexdigest()[:16]}"

            if identifier not in seen and title and len(title) >= 10:
                seen.add(identifier)
                # 只保留高质量的文章
                if result.get('quality_score', 0) >= 60:
                    unique_results.append(result)

        return unique_results

    # 增强的解析器实现
    def _parse_ndrc_policies(self, soup: BeautifulSoup, site: ImprovedSiteConfig) -> List[Dict]:
        """解析国家发改委政策文件。"""
        records = []

        # 寻找政策文件列表
        selectors = [
            "div.list ul li",
            "div.zcfgb-list ul li",
            "div.xxgk-list ul li",
            "div.main-list li",
            "ul.u-list li"
        ]

        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items and len(items) > 3:  # 确保是真正的列表
                break

        for li in items[:self.max_articles_per_site]:
            anchor = li.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title or len(title) < 20:
                continue

            url = urljoin(site.base_url, href)

            # 尝试获取发布日期
            date_elem = li.find("span", class_="date") or li.find("time")
            publish_date = date_elem.get_text(strip=True) if date_elem else ""

            records.append({
                "title": title,
                "url": url,
                "publish_date": publish_date,
                "summary": ""
            })

        return records

    def _parse_nea_policies(self, soup: BeautifulSoup, site: ImprovedSiteConfig) -> List[Dict]:
        """解析国家能源局政策文件。"""
        records = []

        # 寻找多种可能的内容区域
        selectors = [
            "div.news-list li",
            "div.main-content li",
            "div.article-list li",
            "div.info-list li",
            "div.list li",
            "ul li"
        ]

        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items and len(items) > 2:
                break

        for li in items[:self.max_articles_per_site]:
            anchor = li.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title or len(title) < 15:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_mee_policies(self, soup: BeautifulSoup, site: ImprovedSiteConfig) -> List[Dict]:
        """解析生态环境部政策文件。"""
        records = []

        # 查找政策相关的链接
        selectors = [
            "div.xxgk-list li",
            "div.main-list li",
            "div.news-list li",
            "div.list li"
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

    def _parse_cpnn_articles(self, soup: BeautifulSoup, site: ImprovedSiteConfig) -> List[Dict]:
        """解析中国能源报文章。"""
        records = []

        # 寻找文章链接，优先深度报道
        selectors = [
            "div.news-list li",
            "div.article-list li",
            "div.hy-list li",  # 行业观察
            "div.content-list li",
            "main li",
            "article",
            "div.post"
        ]

        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items and len(items) > 3:
                break

        for item in items[:self.max_articles_per_site]:
            anchor = item.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title or len(title) < 25:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_bjx_articles(self, soup: BeautifulSoup, site: ImprovedSiteConfig) -> List[Dict]:
        """解析北极星电力网文章。"""
        records = []

        # 北极星电力网通常有详细的文章结构
        selectors = [
            "div.news-list li",
            "div.article-list li",
            "div.main-list li",
            "div.content-list li",
            "li"
        ]

        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items and len(items) > 5:
                break

        for li in items[:self.max_articles_per_site]:
            anchor = li.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title or len(title) < 20:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_inen_articles(self, soup: BeautifulSoup, site: ImprovedSiteConfig) -> List[Dict]:
        """解析国际能源小数据文章。"""
        records = []

        selectors = [
            "div.news-list li",
            "div.article-list li",
            "div.main-list li",
            "li"
        ]

        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items and len(items) > 3:
                break

        for li in items[:self.max_articles_per_site]:
            anchor = li.find("a")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href") or ""

            if not title or len(title) < 25:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_cec_reports(self, soup: BeautifulSoup, site: ImprovedSiteConfig) -> List[Dict]:
        """解析中国电力企业联合会研究报告。"""
        records = []

        selectors = [
            "div.news-list li",
            "div.report-list li",
            "div.article-list li",
            "li"
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

    def _parse_ef_reports(self, soup: BeautifulSoup, site: ImprovedSiteConfig) -> List[Dict]:
        """解析能源基金会研究报告。"""
        records = []

        selectors = [
            "div.news-list li",
            "div.report-list li",
            "div.project-list li",
            "li"
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

    def _parse_xinhua_energy(self, soup: BeautifulSoup, site: ImprovedSiteConfig) -> List[Dict]:
        """解析新华网能源频道。"""
        records = []

        selectors = [
            "div.news-list li",
            "div.main-list li",
            "div.content-list li",
            "li"
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

            if not title or len(title) < 30:
                continue

            url = urljoin(site.base_url, href)

            records.append({
                "title": title,
                "url": url,
                "publish_date": "",
                "summary": ""
            })

        return records

    def _parse_people_energy(self, soup: BeautifulSoup, site: ImprovedSiteConfig) -> List[Dict]:
        """解析人民网能源频道。"""
        records = []

        selectors = [
            "div.news-list li",
            "div.main-list li",
            "div.content-list li",
            "li"
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

            if not title or len(title) < 25:
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
        """保存结果。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = filename or f"enhanced_improved_crawl_{timestamp}.json"
        output_path = Path(self.output_dir) / name
        write_json(output_path, results)
        return str(output_path)
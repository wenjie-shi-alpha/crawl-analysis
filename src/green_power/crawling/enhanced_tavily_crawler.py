"""增强版Tavily爬虫实现，使用官方SDK并优化配置用于学术研究。"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from tavily import TavilyClient

from utils.io import write_json


class EnhancedTavilyCrawler:
    """使用官方SDK的增强版Tavily爬虫，专为学术研究优化。"""

    def __init__(
        self,
        keywords: Iterable[str],
        output_dir: str,
        api_key: Optional[str] = None,
        search_depth: str = "advanced",
        max_results_per_keyword: int = 25,
        request_timeout: int = 30,
        max_concurrent_requests: int = 3,
        rate_limit_delay: float = 1.0,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ):
        """
        初始化增强版Tavily爬虫。

        Args:
            keywords: 搜索关键词列表
            output_dir: 输出目录
            api_key: Tavily API密钥
            search_depth: 搜索深度，可选 "basic" 或 "advanced"
            max_results_per_keyword: 每个关键词的最大结果数
            request_timeout: 请求超时时间
            max_concurrent_requests: 最大并发请求数
            rate_limit_delay: 请求间隔时间（秒）
            include_domains: 包含的域名列表
            exclude_domains: 排除的域名列表
        """
        self.keywords = list(keywords)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # API配置
        api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("未检测到 Tavily API 密钥，请设置环境变量 TAVILY_API_KEY")

        # 初始化Tavily客户端
        self.client = TavilyClient(api_key=api_key)

        # 搜索配置
        self.search_depth = search_depth
        self.max_results_per_keyword = max_results_per_keyword
        self.request_timeout = request_timeout
        self.max_concurrent_requests = max_concurrent_requests
        self.rate_limit_delay = rate_limit_delay
        self.include_domains = include_domains
        self.exclude_domains = exclude_domains

    def crawl(self) -> List[Dict]:
        """
        执行所有关键词的数据爬取。

        Returns:
            爬取到的结果列表
        """
        print(f"开始爬取 {len(self.keywords)} 个关键词...")

        results = []
        for i, keyword in enumerate(self.keywords, 1):
            print(f"正在处理关键词 {i}/{len(self.keywords)}: {keyword}")

            try:
                keyword_results = self._search_keyword(keyword)
                results.extend(keyword_results)
                print(f"✓ 关键词 '{keyword}' 获得了 {len(keyword_results)} 条结果")

                # 请求间隔以避免速率限制
                if i < len(self.keywords):
                    time.sleep(self.rate_limit_delay)

            except Exception as e:
                print(f"✗ 关键词 '{keyword}' 搜索失败: {e}")
                continue

        print(f"\n爬取完成！共获得 {len(results)} 条结果")
        return results

    def _search_keyword(self, keyword: str) -> List[Dict]:
        """
        搜索单个关键词。

        Args:
            keyword: 搜索关键词

        Returns:
            搜索结果列表
        """
        search_params = {
            "query": keyword,
            "search_depth": self.search_depth,
            "max_results": self.max_results_per_keyword,
            "include_raw_content": True,  # 获取完整内容
            "include_images": False,
        }

        # 添加域名筛选（如果指定）
        if self.include_domains:
            search_params["include_domains"] = self.include_domains
        if self.exclude_domains:
            search_params["exclude_domains"] = self.exclude_domains

        try:
            # 使用Tavily客户端执行搜索
            response = self.client.search(**search_params)

            now = datetime.utcnow().isoformat()
            results = []

            for item in response.get("results", []):
                result = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "raw_content": item.get("raw_content", ""),  # 完整内容
                    "score": item.get("score", 0.0),
                    "source": item.get("source", "tavily"),
                    "keyword": keyword,
                    "crawl_time": now,
                    "published_date": item.get("published_date", ""),
                }
                results.append(result)

            return results

        except Exception as e:
            raise RuntimeError(f"搜索关键词 '{keyword}' 时发生错误: {e}")

    def save(self, results: List[Dict], filename: Optional[str] = None) -> str:
        """
        保存爬取结果到文件。

        Args:
            results: 要保存的结果列表
            filename: 可选的文件名

        Returns:
            保存文件的路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = filename or f"enhanced_tavily_results_{timestamp}.json"
        output_path = self.output_dir / name

        # 添加元数据
        metadata = {
            "crawl_time": datetime.now().isoformat(),
            "total_results": len(results),
            "keywords_count": len(self.keywords),
            "keywords": self.keywords,
            "search_depth": self.search_depth,
            "max_results_per_keyword": self.max_results_per_keyword,
        }

        output_data = {
            "metadata": metadata,
            "results": results,
        }

        write_json(output_path, output_data)
        print(f"结果已保存到: {output_path}")
        return str(output_path)

    async def crawl_async(self) -> List[Dict]:
        """
        异步执行爬取（提高性能），支持递归搜索。

        Returns:
            爬取到的结果列表
        """
        print(f"开始异步爬取 {len(self.keywords)} 个关键词...")

        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        all_results = []
        visited_urls = set()

        async def search_with_semaphore(keyword: str, depth: int = 0) -> List[Dict]:
            if depth > 1: # Limit recursion depth to 1 for now to avoid explosion
                return []
            
            async with semaphore:
                results = await asyncio.get_event_loop().run_in_executor(
                    None, self._search_keyword, keyword
                )
            
            new_results = []
            for res in results:
                if res['url'] not in visited_urls:
                    visited_urls.add(res['url'])
                    new_results.append(res)
            
            # Recursive step
            if depth < 1 and new_results:
                sub_queries = []
                # Generate sub-queries from top 3 results
                for res in new_results[:3]:
                    # Simple heuristic: use title as basis for more specific search
                    # In a real scenario, we might use an LLM here to generate better queries
                    # For now, we append "analysis" or "details" to the title or use the title itself if it's not too long
                    title = res['title']
                    if len(title) < 50:
                        sub_queries.append(f"{title} analysis")
                
                if sub_queries:
                    print(f"  -> Generating {len(sub_queries)} sub-queries for '{keyword}'")
                    sub_tasks = [search_with_semaphore(q, depth + 1) for q in sub_queries]
                    sub_results_list = await asyncio.gather(*sub_tasks, return_exceptions=True)
                    for sub_res in sub_results_list:
                        if not isinstance(sub_res, Exception):
                            new_results.extend(sub_res)

            return new_results

        tasks = []
        for keyword in self.keywords:
            task = asyncio.create_task(search_with_semaphore(keyword))
            tasks.append(task)

        # Execute initial tasks
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                print(f"搜索失败: {result}")
                continue
            all_results.extend(result)

        print(f"异步爬取完成！共获得 {len(all_results)} 条结果")
        return all_results
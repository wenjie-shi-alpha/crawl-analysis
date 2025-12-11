#!/usr/bin/env python3
"""
中国绿电消费驱动和阻碍因素学术研究专用爬虫

使用Tavily API爬取足够支撑中文论文发表的研究资料。
包含全面的关键词配置、结果去重、内容质量评估等功能。
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from config import DEFAULT_KEYWORDS, PipelineConfig
from crawling.tavily_crawler import TavilyCrawler


class AcademicGreenPowerCrawler:
    """学术研究专用的绿电消费数据爬虫。"""

    def __init__(self, output_base_dir: str = "academic_data"):
        """
        初始化学术研究爬虫。

        Args:
            output_base_dir: 输出基础目录
        """
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

        # 学术研究优化的关键词配置
        self.academic_keywords = [
            # 核心概念
            "绿色电力消费", "绿电消费", "可再生能源消费", "清洁电力消费",

            # 驱动因素（正面因素）
            "绿色电力消费 动机", "绿电消费 驱动机制", "可再生能源购买意愿",
            "绿色电力 环保意识", "绿电消费 社会责任", "绿色电力 消费态度",
            "可再生能源 消费行为", "绿色电力 消费偏好", "清洁能源 采纳意愿",
            "绿电消费 影响因素", "可再生能源消费 激励因素",

            # 阻碍因素（负面因素）
            "绿色电力消费 阻碍", "绿电消费 障碍", "可再生能源消费 壁垒",
            "绿色电力 价格阻力", "绿电消费 成本问题", "绿色电力 信任问题",
            "可再生能源 认知障碍", "绿电消费 便捷性", "绿色电力 接受度",
            "清洁能源 消费障碍", "绿电消费 消费顾虑", "可再生能源 推广阻力",

            # 政策制度因素
            "中国 绿色电力政策", "绿电交易机制", "可再生能源配额制",
            "绿色电力证书", "绿证交易", "电力市场化改革", "双碳目标",
            "碳中和 绿色电力", "碳达峰 电力消费", "绿色电力 补贴政策",

            # 技术市场因素
            "绿色电力 供应能力", "可再生能源 电网接入", "绿电交易 市场",
            "清洁能源 成本分析", "绿色电力 竞争力", "可再生能源 价格机制",

            # 消费者行为
            "居民 绿色电力选择", "企业 绿电采购", "家庭 绿电消费",
            "消费者 绿色电力认知", "公众 绿色电力态度", "用户 绿色电力偏好",

            # 区域案例
            "中国 绿色电力试点", "省级 绿色电力政策", "城市 绿电消费",
            "工业园区 绿色电力", "商业建筑 绿色电力",

            # 国际经验
            "国外 绿色电力消费", "欧盟 绿色电力", "美国 可再生能源消费",
            "国际 绿电交易经验", "发达国 绿色电力政策",
        ]

        # 高质量域名白名单（优先获取权威内容）
        self.quality_domains = [
            # 政府机构
            "gov.cn", "ndrc.gov.cn", "nea.gov.cn", "mee.gov.cn",

            # 学术机构
            "cnki.net", "wanfangdata.com.cn", "cqvip.com",
            "tsinghua.edu.cn", "pku.edu.cn", "ruc.edu.cn",

            # 研究院所
            "cass.cn", "cenews.com.cn", "cec.org.cn",

            # 权威媒体
            "people.com.cn", "xinhuanet.com", "ce.cn", "cpnn.com.cn",

            # 行业组织
            "china-cpa.org", "creia.org", "creei.cn",
        ]

        # 垃圾域名黑名单
        self.spam_domains = [
            "ads.", "ad.", "marketing.", "promotion.",
            "gambling.", "casino.", "adult.", "xxx.",
        ]

    def deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """
        对爬取结果进行去重。

        Args:
            results: 原始结果列表

        Returns:
            去重后的结果列表
        """
        seen_urls: Set[str] = set()
        seen_content: Set[str] = set()
        deduplicated = []

        for item in results:
            url = item.get("url", "")
            content = item.get("content", "")

            # URL去重
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # 内容去重（基于内容哈希）
            content_hash = hashlib.md5(content.encode()).hexdigest()
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            deduplicated.append(item)

        print(f"去重前: {len(results)} 条，去重后: {len(deduplicated)} 条")
        return deduplicated

    def filter_by_quality(self, results: List[Dict]) -> List[Dict]:
        """
        按内容质量过滤结果。

        Args:
            results: 原始结果列表

        Returns:
            高质量结果列表
        """
        quality_filtered = []

        for item in results:
            title = item.get("title", "")
            content = item.get("content", "")
            url = item.get("url", "")

            # 过滤条件
            conditions = [
                len(title.strip()) > 10,  # 标题长度
                len(content.strip()) > 50,  # 内容长度
                not any(spam in url.lower() for spam in self.spam_domains),  # 非垃圾域名
                "绿电" in content or "绿色电力" in content or "可再生能源" in content,  # 相关性
            ]

            if all(conditions):
                quality_filtered.append(item)

        print(f"质量过滤前: {len(results)} 条，过滤后: {len(quality_filtered)} 条")
        return quality_filtered

    def crawl_academic_data(self) -> str:
        """
        执行学术研究数据爬取。

        Returns:
            结果文件路径
        """
        print("=" * 60)
        print("中国绿电消费驱动和阻碍因素学术研究数据爬取")
        print("=" * 60)

        # 配置爬虫
        crawler = TavilyCrawler(
            keywords=self.academic_keywords,
            output_dir=str(self.output_base_dir / "raw"),
            search_depth="advanced",
            max_results_per_keyword=30,  # 每个关键词获取更多结果
        )

        # 执行爬取
        raw_results = crawler.crawl()

        if not raw_results:
            raise RuntimeError("爬取未获得任何结果，请检查API配置")

        print(f"\n原始爬取完成，共 {len(raw_results)} 条结果")

        # 数据处理
        print("\n开始数据后处理...")

        # 去重
        deduplicated = self.deduplicate_results(raw_results)

        # 质量过滤
        quality_results = self.filter_by_quality(deduplicated)

        # 保存处理后的结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_base_dir / f"academic_green_power_results_{timestamp}.json"

        # 添加学术研究元数据
        academic_metadata = {
            "research_topic": "中国绿电消费驱动和阻碍因素研究",
            "crawl_time": datetime.now().isoformat(),
            "total_keywords": len(self.academic_keywords),
            "original_results": len(raw_results),
            "deduplicated_results": len(deduplicated),
            "quality_filtered_results": len(quality_results),
            "quality_rate": f"{len(quality_results)/len(raw_results)*100:.1f}%",
            "keywords_used": self.academic_keywords,
            "research_categories": {
                "core_concepts": 4,
                "driving_factors": 11,
                "hindering_factors": 12,
                "policy_factors": 9,
                "technical_market_factors": 6,
                "consumer_behavior": 6,
                "regional_cases": 5,
                "international_experience": 5,
            }
        }

        final_data = {
            "metadata": academic_metadata,
            "results": quality_results,
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

        print(f"\n学术研究数据爬取完成！")
        print(f"最终结果文件: {output_file}")
        print(f"高质量结果数量: {len(quality_results)}")
        print(f"预计可支撑1-2篇中文论文的实证研究")

        return str(output_file)

    def generate_summary_report(self, results_file: str) -> str:
        """
        生成爬取结果摘要报告。

        Args:
            results_file: 结果文件路径

        Returns:
            摘要报告文件路径
        """
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        metadata = data["metadata"]
        results = data["results"]

        # 统计分析
        domain_stats = {}
        keyword_stats = {}

        for result in results:
            url = result.get("url", "")
            keyword = result.get("keyword", "")

            # 域名统计
            domain = url.split('/')[2] if '/' in url else "unknown"
            domain_stats[domain] = domain_stats.get(domain, 0) + 1

            # 关键词统计
            keyword_stats[keyword] = keyword_stats.get(keyword, 0) + 1

        # 生成报告
        report = {
            "summary": {
                "total_results": len(results),
                "unique_domains": len(domain_stats),
                "effective_keywords": len([k for k, v in keyword_stats.items() if v > 0]),
                "average_results_per_keyword": len(results) / len(keyword_stats) if keyword_stats else 0,
            },
            "top_domains": dict(sorted(domain_stats.items(), key=lambda x: x[1], reverse=True)[:20]),
            "keyword_coverage": keyword_stats,
            "metadata": metadata,
        }

        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_base_dir / f"crawl_summary_report_{timestamp}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"摘要报告已保存: {report_file}")
        return str(report_file)


def main():
    """主函数。"""
    # 检查环境变量
    if not os.getenv("TAVILY_API_KEY"):
        print("错误: 请设置 TAVILY_API_KEY 环境变量")
        print("在命令行中运行: export TAVILY_API_KEY='your_api_key_here'")
        return 1

    try:
        # 创建学术研究爬虫
        crawler = AcademicGreenPowerCrawler()

        # 执行数据爬取
        results_file = crawler.crawl_academic_data()

        # 生成摘要报告
        report_file = crawler.generate_summary_report(results_file)

        print(f"\n✓ 学术研究数据爬取任务完成")
        print(f"✓ 结果数据: {results_file}")
        print(f"✓ 摘要报告: {report_file}")

        return 0

    except Exception as e:
        print(f"❌ 爬取过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
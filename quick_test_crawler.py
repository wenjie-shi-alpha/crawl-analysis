#!/usr/bin/env python3
"""
快速测试版爬虫，用于验证Tavily API配置
"""

import os
import sys
from pathlib import Path

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from crawling.tavily_crawler import TavilyCrawler

def main():
    """快速测试Tavily爬虫"""
    print("=" * 50)
    print("快速测试 Tavily API 配置")
    print("=" * 50)

    # 检查API密钥
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("❌ 未检测到TAVILY_API_KEY环境变量")
        return 1

    print("✓ TAVILY_API_KEY 已配置")

    # 使用少量关键词进行测试
    test_keywords = [
        "绿色电力消费",
        "绿电消费 驱动因素",
        "可再生能源消费 阻碍因素"
    ]

    print(f"\n测试关键词: {test_keywords}")

    try:
        # 创建爬虫实例
        crawler = TavilyCrawler(
            keywords=test_keywords,
            output_dir="test_output",
            max_results_per_keyword=5,
            search_depth="basic"
        )

        print("\n开始爬取测试...")
        results = crawler.crawl()

        if results:
            print(f"✓ 成功获取 {len(results)} 条结果")

            # 显示前几条结果
            print("\n前3条结果:")
            for i, result in enumerate(results[:3], 1):
                print(f"{i}. {result.get('title', 'N/A')}")
                print(f"   URL: {result.get('url', 'N/A')}")
                print(f"   内容: {result.get('content', 'N/A')[:100]}...")
                print()

            # 保存结果
            output_file = crawler.save(results, "test_results.json")
            print(f"✓ 结果已保存到: {output_file}")

            return 0
        else:
            print("❌ 未获取到任何结果")
            return 1

    except Exception as e:
        print(f"❌ 爬取过程中发生错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
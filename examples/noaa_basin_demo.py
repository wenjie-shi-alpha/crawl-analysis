#!/usr/bin/env python3
"""
测试海区分类功能的爬虫
"""

import sys

sys.path.insert(0, "src")

from green_power.crawling import NOAACompleteCrawler

def main():
    print("="*70)
    print("测试NOAA海区分类功能")
    print("="*70)
    
    # 创建爬虫
    crawler = NOAACompleteCrawler(
        output_dir="data/output/raw/noaa_complete"
    )
    
    # 测试单个年份
    test_year = 2011
    print(f"\n测试年份: {test_year}")
    print("这个年份包含Atlantic和E. Pacific两个海区")
    print("\n开始爬取...\n")
    
    # 只获取气旋信息，不下载数据
    cyclones = crawler.get_year_cyclones(test_year)
    
    if cyclones:
        print(f"\n{'='*70}")
        print(f"气旋列表详情:")
        print(f"{'='*70}")
        
        for cyclone in cyclones:
            print(f"\n气旋: {cyclone['name']}")
            print(f"  完整名称: {cyclone['full_name']}")
            print(f"  ID: {cyclone['id']}")
            print(f"  海区: {cyclone.get('basin', 'Unknown')}")
            print(f"  海区代码: {cyclone.get('basin_code', 'N/A')}")
            print(f"  格式: {cyclone['format']}")
    
    print(f"\n{'='*70}")
    response = input("\n是否继续下载这些气旋的数据? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\n开始下载数据...")
        crawler.crawl_year(test_year)
        
        print("\n下载完成! 查看目录结构:")
        crawler.list_downloaded_data(test_year)
    else:
        print("已取消下载")

if __name__ == "__main__":
    main()

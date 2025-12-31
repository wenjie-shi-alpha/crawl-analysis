#!/usr/bin/env python3
"""
简单的IEM爬虫测试脚本（独立运行）
"""

import sys
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from green_power.crawling import IEMTextProductCrawler


def test_list_products():
    """测试: 列出可用产品"""
    print("\n" + "="*70)
    print("测试: 列出可用产品类型")
    print("="*70)
    
    crawler = IEMTextProductCrawler()
    crawler.list_available_products()


def test_crawl_mcd_recent():
    """测试: 爬取最近的MCD产品"""
    print("\n" + "="*70)
    print("测试: 爬取最近2天的MCD产品")
    print("="*70)
    
    crawler = IEMTextProductCrawler(
        output_dir="data/output/raw/iem_products"
    )
    
    # 最近2天
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)
    
    crawler.crawl_products_by_date_range(
        pil='MCD',
        start_date=start_date,
        end_date=end_date,
    )


def test_crawl_afd_with_center():
    """测试: 爬取特定中心的AFD"""
    print("\n" + "="*70)
    print("测试: 爬取DMX中心最近1天的AFD产品")
    print("="*70)
    
    crawler = IEMTextProductCrawler(
        output_dir="data/output/raw/iem_products"
    )
    
    # 最近1天
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    crawler.crawl_products_by_date_range(
        pil='AFD',
        start_date=start_date,
        end_date=end_date,
        center='DMX',
    )


def test_view_downloaded():
    """测试: 查看已下载的数据"""
    print("\n" + "="*70)
    print("测试: 查看已下载的数据")
    print("="*70)
    
    crawler = IEMTextProductCrawler(
        output_dir="data/output/raw/iem_products"
    )
    
    crawler.list_downloaded_data()


def main():
    print("="*70)
    print("IEM爬虫简单测试")
    print("="*70)
    print("\n选择测试:")
    print("1. 列出可用产品类型")
    print("2. 爬取最近2天的MCD产品 (小测试)")
    print("3. 爬取DMX中心最近1天的AFD产品")
    print("4. 查看已下载的数据")
    print("0. 退出")
    
    choice = input("\n请选择 (0-4): ").strip()
    
    if choice == '1':
        test_list_products()
    elif choice == '2':
        test_crawl_mcd_recent()
    elif choice == '3':
        test_crawl_afd_with_center()
    elif choice == '4':
        test_view_downloaded()
    elif choice == '0':
        print("退出")
    else:
        print("无效选择")


if __name__ == "__main__":
    main()

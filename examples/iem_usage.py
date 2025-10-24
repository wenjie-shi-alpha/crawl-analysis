#!/usr/bin/env python3
"""测试IEM爬虫的示例脚本"""

import sys
from datetime import datetime, timedelta

sys.path.insert(0, "src")

from green_power.crawling import IEMTextProductCrawler


def example_1_crawl_mcd():
    """示例1: 爬取Model Diagnostic Discussion (MCD)产品"""
    print("示例1: 爬取最近7天的MCD产品\n")
    
    crawler = IEMTextProductCrawler(
        output_dir="data/output/raw/iem_products"
    )
    
    # 设置日期范围（最近7天）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # 爬取MCD产品
    crawler.crawl_products_by_date_range(
        pil='MCD',
        start_date=start_date,
        end_date=end_date,
    )


def example_2_crawl_multiple_products():
    """示例2: 爬取多种产品类型"""
    print("示例2: 爬取多种产品类型（AFD和HWO）\n")
    
    crawler = IEMTextProductCrawler(
        output_dir="data/output/raw/iem_products"
    )
    
    # 设置日期范围（最近3天）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)
    
    # 爬取多种产品
    crawler.crawl_multiple_products(
        pils=['AFD', 'HWO'],
        start_date=start_date,
        end_date=end_date,
        center='DMX',  # Des Moines中心
    )


def example_3_crawl_specific_date():
    """示例3: 爬取特定日期的产品"""
    print("示例3: 爬取特定日期的产品\n")
    
    crawler = IEMTextProductCrawler(
        output_dir="data/output/raw/iem_products"
    )
    
    # 设置特定日期
    target_date = datetime(2024, 10, 1)
    
    # 爬取该日期的多种产品
    products = ['AFD', 'MCD', 'SWO', 'HWO']
    
    for pil in products:
        crawler.crawl_products_by_date_range(
            pil=pil,
            start_date=target_date,
            end_date=target_date,
        )


def example_4_list_products():
    """示例4: 列出可用的产品类型"""
    print("示例4: 列出可用的产品类型\n")
    
    crawler = IEMTextProductCrawler()
    
    # 显示所有可用的产品类型
    products = crawler.list_available_products()
    
    print(f"\n总计 {len(products)} 种产品类型")


def example_5_view_downloaded():
    """示例5: 查看已下载的数据"""
    print("示例5: 查看已下载的数据\n")
    
    crawler = IEMTextProductCrawler(
        output_dir="data/output/raw/iem_products"
    )
    
    # 列出已下载的数据
    crawler.list_downloaded_data()


def main():
    """运行示例"""
    print("="*70)
    print("IEM爬虫使用示例")
    print("="*70)
    
    print("\n选择要运行的示例:")
    print("1. 爬取MCD产品（最近7天）")
    print("2. 爬取多种产品（AFD和HWO，最近3天）")
    print("3. 爬取特定日期的产品")
    print("4. 列出可用的产品类型")
    print("5. 查看已下载的数据")
    print("0. 退出")
    
    choice = input("\n请选择 (0-5): ").strip()
    
    if choice == '1':
        example_1_crawl_mcd()
    elif choice == '2':
        example_2_crawl_multiple_products()
    elif choice == '3':
        example_3_crawl_specific_date()
    elif choice == '4':
        example_4_list_products()
    elif choice == '5':
        example_5_view_downloaded()
    elif choice == '0':
        print("退出")
    else:
        print("无效选择")


if __name__ == "__main__":
    main()

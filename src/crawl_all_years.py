#!/usr/bin/env python3
"""一键爬取所有年份的NOAA飓风数据."""

from crawling.noaa_crawler import NOAACompleteCrawler

def main():
    print("=" * 70)
    print("NOAA飓风数据 - 批量爬取所有年份")
    print("=" * 70)
    
    # 定义要爬取的年份范围
    start_year = 1998  # NOAA档案开始年份
    end_year = 2025    # 当前年份
    
    years = list(range(start_year, end_year + 1))
    
    print(f"\n准备爬取年份: {start_year} - {end_year}")
    print(f"总共: {len(years)} 个年份")
    print(f"年份列表: {years[:5]}...{years[-5:]}")
    
    # 确认
    response = input("\n确认开始爬取? (y/n): ").strip().lower()
    
    if response != 'y':
        print("已取消")
        return
    
    # 创建爬虫并开始爬取
    crawler = NOAACompleteCrawler(
        output_dir="data/output/raw/noaa_complete"
    )
    
    print("\n开始批量爬取...")
    print("提示: 这可能需要较长时间（数小时），请耐心等待")
    print("提示: 可以随时中断(Ctrl+C)，下次运行会自动跳过已下载的文件\n")
    
    try:
        crawler.crawl_years(years)
    except KeyboardInterrupt:
        print("\n\n用户中断，已保存当前进度")
        print(f"当前统计: {crawler.stats}")
    except Exception as e:
        print(f"\n发生错误: {e}")
        print(f"当前统计: {crawler.stats}")
    
    print("\n完成！")

if __name__ == "__main__":
    main()

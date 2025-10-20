"""NOAA Hurricane Archive Crawler - 获取NOAA飓风档案网页HTML内容."""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup


class NOAAArchiveCrawler:
    """从NOAA飓风档案网站获取HTML内容的爬虫."""
    
    def __init__(
        self,
        base_url: str = "https://www.nhc.noaa.gov/archive/",
        output_dir: str = "data/output/raw/noaa_archive",
        timeout: int = 30
    ):
        """
        初始化NOAA档案爬虫.
        
        Args:
            base_url: NOAA档案基础URL
            output_dir: 输出目录路径
            timeout: 请求超时时间(秒)
        """
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.timeout = timeout
        self.session = requests.Session()
        
        # 设置User-Agent，避免被网站拦截
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch_page(self, url: Optional[str] = None) -> str:
        """
        获取指定URL的HTML内容.
        
        Args:
            url: 要获取的URL，如果为None则使用base_url
            
        Returns:
            页面的HTML内容
            
        Raises:
            requests.RequestException: 请求失败时抛出
        """
        target_url = url or self.base_url
        
        print(f"正在获取: {target_url}")
        
        try:
            response = self.session.get(target_url, timeout=self.timeout)
            response.raise_for_status()  # 检查HTTP错误
            
            print(f"✓ 成功获取页面 (状态码: {response.status_code})")
            return response.text
            
        except requests.RequestException as e:
            print(f"✗ 获取页面失败: {e}")
            raise
    
    def save_html(
        self,
        html_content: str,
        filename: Optional[str] = None,
        subdirectory: Optional[str] = None
    ) -> Path:
        """
        将HTML内容保存到本地文件.
        
        Args:
            html_content: HTML内容
            filename: 文件名，如果为None则自动生成
            subdirectory: 子目录名称
            
        Returns:
            保存文件的路径
        """
        # 确定保存目录
        save_dir = self.output_dir
        if subdirectory:
            save_dir = save_dir / subdirectory
            save_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"noaa_archive_{timestamp}.html"
        
        # 确保文件名以.html结尾
        if not filename.endswith('.html'):
            filename += '.html'
        
        filepath = save_dir / filename
        
        # 保存文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ HTML内容已保存到: {filepath}")
        print(f"  文件大小: {len(html_content):,} 字符")
        
        return filepath
    
    def fetch_and_save(
        self,
        url: Optional[str] = None,
        filename: Optional[str] = None,
        subdirectory: Optional[str] = None
    ) -> Path:
        """
        获取页面HTML并保存到本地.
        
        Args:
            url: 要获取的URL
            filename: 保存的文件名
            subdirectory: 子目录名称
            
        Returns:
            保存文件的路径
        """
        html_content = self.fetch_page(url)
        filepath = self.save_html(html_content, filename, subdirectory)
        return filepath
    
    def parse_archive_index(self, html_content: str) -> list[dict]:
        """
        解析档案索引页面，提取所有年份链接.
        
        Args:
            html_content: HTML内容
            
        Returns:
            包含年份和链接信息的字典列表
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        # 查找所有链接
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            # 构建完整URL
            if href.startswith('http'):
                full_url = href
            else:
                full_url = self.base_url.rstrip('/') + '/' + href.lstrip('/')
            
            links.append({
                'text': text,
                'href': href,
                'full_url': full_url
            })
        
        print(f"✓ 解析到 {len(links)} 个链接")
        return links
    
    def crawl_multiple_years(self, years: list[int]) -> list[Path]:
        """
        抓取多个年份的档案页面.
        
        Args:
            years: 年份列表
            
        Returns:
            保存的文件路径列表
        """
        saved_files = []
        
        for year in years:
            try:
                # 构建年份URL (通常格式为 /archive/2023/)
                year_url = f"{self.base_url.rstrip('/')}/{year}/"
                filename = f"archive_{year}.html"
                
                filepath = self.fetch_and_save(
                    url=year_url,
                    filename=filename,
                    subdirectory=str(year)
                )
                saved_files.append(filepath)
                
            except Exception as e:
                print(f"✗ 获取 {year} 年数据失败: {e}")
                continue
        
        return saved_files


def main():
    """主函数 - 示例用法."""
    
    # 创建爬虫实例
    crawler = NOAAArchiveCrawler(
        base_url="https://www.nhc.noaa.gov/archive/",
        output_dir="data/output/raw/noaa_archive"
    )
    
    print("=" * 60)
    print("NOAA飓风档案爬虫")
    print("=" * 60)
    
    # 1. 获取主页面
    print("\n[1] 获取档案主页...")
    try:
        main_page_path = crawler.fetch_and_save(
            filename="archive_index.html"
        )
        
        # 读取并解析主页
        with open(main_page_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        links = crawler.parse_archive_index(html_content)
        
        print(f"\n找到的链接示例 (前10个):")
        for i, link in enumerate(links[:10], 1):
            print(f"  {i}. {link['text']}: {link['full_url']}")
        
    except Exception as e:
        print(f"获取主页失败: {e}")
        return
    
    # 2. 可选：获取特定年份的数据
    print("\n[2] 获取特定年份数据...")
    years_to_crawl = [2023, 2022, 2021]  # 可以修改为需要的年份
    
    response = input(f"\n是否要获取 {years_to_crawl} 这些年份的数据? (y/n): ")
    
    if response.lower() == 'y':
        saved_files = crawler.crawl_multiple_years(years_to_crawl)
        print(f"\n✓ 成功保存 {len(saved_files)} 个文件")
    else:
        print("跳过年份数据获取")
    
    print("\n" + "=" * 60)
    print("爬取完成!")
    print(f"所有文件保存在: {crawler.output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()

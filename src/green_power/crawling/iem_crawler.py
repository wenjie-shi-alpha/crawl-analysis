#!/usr/bin/env python3
"""Iowa Environmental Mesonet (IEM) NWS Text Product Archive爬虫."""

import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlencode

import requests
from bs4 import BeautifulSoup


class IEMTextProductCrawler:
    """从Iowa Environmental Mesonet (IEM) 获取NWS文本产品的爬虫"""
    
    # 常用的产品ID（PIL - Product Identifier）
    COMMON_PRODUCTS = {
        'AFD': 'Area Forecast Discussion',
        'MCD': 'Mesoscale Convective Discussion',  # SPC产品
        'SWO': 'Severe Storm Outlook Narrative',
        'WOU': 'Tornado/Severe Thunderstorm Watch',
        'TOR': 'Tornado Warning',
        'SVR': 'Severe Thunderstorm Warning',
        'FFW': 'Flash Flood Warning',
        'HWO': 'Hazardous Weather Outlook',
        'LSR': 'Local Storm Report',
        'PNS': 'Public Information Statement',
        'NOW': 'Short Term Forecast',
        'TAF': 'Terminal Aerodrome Forecast',
    }
    
    # 常用的WFO中心（3字母标识）
    COMMON_CENTERS = {
        'DMX': 'Des Moines',
        'OUN': 'Norman, OK',
        'OAX': 'Omaha/Valley',
        'TOP': 'Topeka',
        'ICT': 'Wichita',
        'DDC': 'Dodge City',
        'GLD': 'Goodland',
        'LBF': 'North Platte',
        'GID': 'Hastings',
    }
    
    def __init__(
        self,
        base_url: str = "https://mesonet.agron.iastate.edu",
        output_dir: str = "data/output/raw/iem_products",
    ):
        """
        初始化IEM爬虫
        
        Args:
            base_url: IEM基础URL
            output_dir: 输出目录路径
        """
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 统计信息
        self.stats = {
            'products_downloaded': 0,
            'products_failed': 0,
            'dates_processed': 0,
        }
    
    def fetch_page(self, url: str) -> Optional[str]:
        """获取网页HTML"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"✗ 获取失败 {url}: {e}")
            return None
    
    def search_products_by_pil(
        self,
        pil: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        center: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        按产品ID搜索文本产品
        
        Args:
            pil: 产品标识符（3字母代码，如AFD, MCD等）
            start_date: 开始日期（UTC时间）
            end_date: 结束日期（UTC时间），如果为None则使用start_date
            center: WFO中心代码（可选，如DMX）
            
        Returns:
            产品列表，每个产品包含pid（产品ID）、时间、文本等信息
        """
        if end_date is None:
            end_date = start_date
        
        # 构建查询URL - 使用IEM API
        params = {
            'pil': pil.upper(),
            'sdate': start_date.strftime('%Y-%m-%d'),
            'edate': end_date.strftime('%Y-%m-%d'),
        }
        
        if center:
            params['center'] = center.upper()
        
        # 使用API接口
        api_url = f"{self.base_url}/api/1/nws/afos/list.json"
        
        print(f"  搜索产品: {pil} ({self.COMMON_PRODUCTS.get(pil.upper(), 'Unknown')})")
        print(f"  日期范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        if center:
            print(f"  中心: {center} ({self.COMMON_CENTERS.get(center.upper(), 'Unknown')})")
        
        try:
            response = self.session.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            products = data.get('data', [])
            print(f"  找到 {len(products)} 个产品")
            
            return products
            
        except Exception as e:
            print(f"✗ API请求失败: {e}")
            # 如果API失败，尝试网页爬取
            return self._scrape_products_from_web(pil, start_date, end_date, center)
    
    def _scrape_products_from_web(
        self,
        pil: str,
        start_date: datetime,
        end_date: datetime,
        center: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """从网页界面抓取产品列表（备用方法）"""
        print("  使用网页抓取方式...")
        
        # 构建查询参数
        params = {
            'pil': pil.upper(),
            'sdate': start_date.strftime('%Y-%m-%d'),
            'edate': end_date.strftime('%Y-%m-%d'),
        }
        
        if center:
            params['center'] = center.upper()
        
        # 访问列表页面
        list_url = f"{self.base_url}/wx/afos/list.phtml?" + urlencode(params)
        html = self.fetch_page(list_url)
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # 查找所有产品链接
        # IEM使用的格式: /p.php?pid=YYYYMMDDHHMI-KXXX-CCCCCC-PILXXX
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # 匹配产品链接格式
            if '/p.php?pid=' in href:
                # 提取产品ID
                match = re.search(r'pid=([^&"\']+)', href)
                if match:
                    pid = match.group(1)
                    text = link.get_text(strip=True)
                    
                    products.append({
                        'pid': pid,
                        'text': text,
                        'url': urljoin(self.base_url, href)
                    })
        
        print(f"  从网页抓取到 {len(products)} 个产品")
        return products
    
    def fetch_product_content(self, pid: str) -> Optional[str]:
        """
        获取单个产品的文本内容
        
        Args:
            pid: 产品ID（格式: YYYYMMDDHHMI-KXXX-CCCCCC-PILXXX）
            
        Returns:
            产品的文本内容
        """
        # 构建产品URL
        product_url = f"{self.base_url}/p.php?pid={pid}"
        
        html = self.fetch_page(product_url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 产品文本通常在<pre>标签中
        pre_tags = soup.find_all('pre')
        if pre_tags:
            # 选择最长的<pre>标签（通常包含主要内容）
            content_pre = max(pre_tags, key=lambda x: len(x.get_text()))
            return content_pre.get_text().strip()
        
        # 备用：查找特定class的div
        content_div = soup.find('div', class_='product')
        if content_div:
            return content_div.get_text().strip()
        
        return None
    
    def download_product(self, product: Dict[str, str], save_dir: Path) -> bool:
        """
        下载单个产品并保存
        
        Args:
            product: 产品信息字典（必须包含pid）
            save_dir: 保存目录
            
        Returns:
            是否成功下载
        """
        pid = product.get('pid')
        if not pid:
            return False
        
        # 解析产品ID获取信息
        # 格式: YYYYMMDDHHMI-KXXX-CCCCCC-PILXXX
        parts = pid.split('-')
        if len(parts) >= 4:
            timestamp = parts[0]
            center = parts[1]
            pil = parts[3]
        else:
            # 备用格式
            timestamp = datetime.now().strftime('%Y%m%d%H%M')
            center = 'UNKNOWN'
            pil = 'UNKNOWN'
        
        # 获取产品内容
        content = self.fetch_product_content(pid)
        
        if not content:
            return False
        
        # 保存文件
        save_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{timestamp}_{center}_{pil}.txt"
        filepath = save_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # 写入元数据和内容
            f.write(f"Product ID: {pid}\n")
            f.write(f"Retrieved: {datetime.now().isoformat()}\n")
            f.write(f"URL: {self.base_url}/p.php?pid={pid}\n")
            f.write("="*70 + "\n\n")
            f.write(content)
        
        return True
    
    def crawl_products_by_date_range(
        self,
        pil: str,
        start_date: datetime,
        end_date: datetime,
        center: Optional[str] = None,
        max_days_per_request: int = 7,
    ):
        """
        按日期范围批量爬取产品
        
        Args:
            pil: 产品标识符
            start_date: 开始日期
            end_date: 结束日期
            center: WFO中心（可选）
            max_days_per_request: 每次请求的最大天数（IEM限制）
        """
        print(f"\n{'='*70}")
        print(f"开始爬取产品: {pil} ({self.COMMON_PRODUCTS.get(pil.upper(), 'Unknown')})")
        print(f"日期范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        if center:
            print(f"中心: {center}")
        print(f"{'='*70}")
        
        # 创建保存目录
        save_dir = self.output_dir / pil.upper()
        if center:
            save_dir = save_dir / center.upper()
        
        # 按max_days_per_request分段请求
        current_date = start_date
        total_downloaded = 0
        
        while current_date <= end_date:
            # 计算本次请求的结束日期
            segment_end = min(
                current_date + timedelta(days=max_days_per_request - 1),
                end_date
            )
            
            # 搜索产品
            products = self.search_products_by_pil(
                pil=pil,
                start_date=current_date,
                end_date=segment_end,
                center=center,
            )
            
            # 下载每个产品
            segment_downloaded = 0
            for product in products:
                if self.download_product(product, save_dir):
                    segment_downloaded += 1
                    total_downloaded += 1
                    self.stats['products_downloaded'] += 1
                else:
                    self.stats['products_failed'] += 1
                
                # 避免请求过快
                time.sleep(0.5)
            
            print(f"  {current_date.strftime('%Y-%m-%d')} 至 {segment_end.strftime('%Y-%m-%d')}: "
                  f"下载 {segment_downloaded}/{len(products)} 个产品")
            
            # 移动到下一个时间段
            current_date = segment_end + timedelta(days=1)
            self.stats['dates_processed'] += 1
            
            # 段间延迟
            time.sleep(1)
        
        print(f"\n{'='*70}")
        print(f"完成！共下载 {total_downloaded} 个产品")
        print(f"保存目录: {save_dir.absolute()}")
        print(f"{'='*70}")
    
    def crawl_multiple_products(
        self,
        pils: List[str],
        start_date: datetime,
        end_date: datetime,
        center: Optional[str] = None,
    ):
        """
        批量爬取多种产品类型
        
        Args:
            pils: 产品标识符列表
            start_date: 开始日期
            end_date: 结束日期
            center: WFO中心（可选）
        """
        print(f"\n{'='*70}")
        print(f"批量爬取多种产品")
        print(f"产品类型: {', '.join(pils)}")
        print(f"日期范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        for pil in pils:
            self.crawl_products_by_date_range(
                pil=pil,
                start_date=start_date,
                end_date=end_date,
                center=center,
            )
        
        elapsed = time.time() - start_time
        
        # 打印统计信息
        print(f"\n{'='*70}")
        print("爬取完成！统计信息:")
        print(f"{'='*70}")
        print(f"处理日期段数: {self.stats['dates_processed']}")
        print(f"成功下载: {self.stats['products_downloaded']} 个产品")
        print(f"失败: {self.stats['products_failed']} 个产品")
        print(f"总耗时: {elapsed:.1f} 秒")
        print(f"输出目录: {self.output_dir.absolute()}")
        print(f"{'='*70}")
    
    def list_available_products(self) -> Dict[str, str]:
        """列出可用的产品类型"""
        print("\n可用的产品类型:")
        print("="*70)
        for pil, desc in sorted(self.COMMON_PRODUCTS.items()):
            print(f"  {pil:5s} - {desc}")
        print("="*70)
        return self.COMMON_PRODUCTS
    
    def list_downloaded_data(self):
        """列出已下载的数据"""
        print(f"\n{'='*70}")
        print(f"已下载数据列表: {self.output_dir}")
        print(f"{'='*70}")
        
        if not self.output_dir.exists():
            print("目录不存在")
            return
        
        for pil_dir in sorted(self.output_dir.iterdir()):
            if not pil_dir.is_dir():
                continue
            
            print(f"\n{pil_dir.name}/")
            
            # 统计每个中心的文件数
            center_counts = {}
            total_files = 0
            
            for center_dir in pil_dir.iterdir():
                if center_dir.is_dir():
                    file_count = len(list(center_dir.glob('*.txt')))
                    center_counts[center_dir.name] = file_count
                    total_files += file_count
            
            # 如果没有子目录，统计当前目录的文件
            if not center_counts:
                file_count = len(list(pil_dir.glob('*.txt')))
                total_files = file_count
                print(f"  总计: {total_files} 个文件")
            else:
                for center, count in sorted(center_counts.items()):
                    print(f"  {center}: {count} 个文件")
                print(f"  总计: {total_files} 个文件")


def main():
    """主函数"""
    print("="*70)
    print("IEM NWS Text Product Archive 爬虫")
    print("="*70)
    
    # 创建爬虫
    crawler = IEMTextProductCrawler()
    
    # 显示选项
    print("\n选项:")
    print("1. 列出可用产品类型")
    print("2. 爬取单个产品类型")
    print("3. 爬取多个产品类型")
    print("4. 爬取MCD（Mesoscale Convective Discussion）")
    print("5. 爬取AFD（Area Forecast Discussion）")
    print("6. 查看已下载数据")
    
    choice = input("\n请选择 (1-6): ").strip()
    
    if choice == '1':
        crawler.list_available_products()
    
    elif choice == '2':
        pil = input("请输入产品代码 (如 MCD, AFD): ").strip().upper()
        
        start_date_str = input("请输入开始日期 (YYYY-MM-DD): ").strip()
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        
        end_date_str = input("请输入结束日期 (YYYY-MM-DD, 回车使用开始日期): ").strip()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else start_date
        
        center = input("请输入中心代码 (可选，如 DMX，回车跳过): ").strip().upper()
        center = center if center else None
        
        crawler.crawl_products_by_date_range(
            pil=pil,
            start_date=start_date,
            end_date=end_date,
            center=center,
        )
    
    elif choice == '3':
        pils_str = input("请输入产品代码，用逗号分隔 (如 MCD,AFD,HWO): ").strip().upper()
        pils = [p.strip() for p in pils_str.split(',')]
        
        start_date_str = input("请输入开始日期 (YYYY-MM-DD): ").strip()
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        
        end_date_str = input("请输入结束日期 (YYYY-MM-DD): ").strip()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        center = input("请输入中心代码 (可选，回车跳过): ").strip().upper()
        center = center if center else None
        
        crawler.crawl_multiple_products(
            pils=pils,
            start_date=start_date,
            end_date=end_date,
            center=center,
        )
    
    elif choice == '4':
        # 快速测试：爬取最近7天的MCD
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"\n爬取最近7天的MCD产品")
        crawler.crawl_products_by_date_range(
            pil='MCD',
            start_date=start_date,
            end_date=end_date,
        )
    
    elif choice == '5':
        # 爬取特定中心的AFD
        center = input("请输入中心代码 (如 DMX): ").strip().upper()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"\n爬取最近7天 {center} 的AFD产品")
        crawler.crawl_products_by_date_range(
            pil='AFD',
            start_date=start_date,
            end_date=end_date,
            center=center,
        )
    
    elif choice == '6':
        crawler.list_downloaded_data()
    
    else:
        print("无效选择")


if __name__ == "__main__":
    main()

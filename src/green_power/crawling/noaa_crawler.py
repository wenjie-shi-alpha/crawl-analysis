#!/usr/bin/env python3
"""NOAA飓风数据抓取与提取相关工具集合."""

import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class NOAACompleteCrawler:
    """NOAA飓风完整数据爬虫"""
    
    # 数据类型映射
    DATA_TYPES = {
        'fstadv': 'forecast_advisory',      # Forecast Advisory
        'public': 'public_advisory',        # Public Advisory
        'discus': 'forecast_discussion',    # Forecast Discussion
        'wndprb': 'wind_speed_probabilities' # Wind Speed Probabilities
    }
    
    # 海区映射
    BASIN_NAMES = {
        'al': 'Atlantic',
        'ep': 'E_Pacific',
        'cp': 'C_Pacific',
    }
    
    def __init__(self, base_url="https://www.nhc.noaa.gov/archive/",
                 output_dir="data/output/raw/noaa_complete"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 统计信息
        self.stats = {
            'years_processed': 0,
            'cyclones_processed': 0,
            'files_downloaded': 0,
            'files_failed': 0
        }
    
    def fetch_page(self, url: str, follow_redirects: bool = True) -> Optional[str]:
        """获取网页HTML"""
        try:
            response = self.session.get(url, timeout=30, allow_redirects=follow_redirects)
            response.raise_for_status()
            
            # 检查是否有meta refresh重定向（早期年份使用这种方式）
            if 'meta http-equiv="refresh"' in response.text.lower():
                # 提取重定向URL
                match = re.search(r'content="0;URL=([^"]+)"', response.text, re.IGNORECASE)
                if match:
                    redirect_url = match.group(1)
                    if not redirect_url.startswith('http'):
                        # 相对路径，需要拼接
                        from urllib.parse import urljoin
                        redirect_url = urljoin(url, redirect_url)
                    # 重新获取重定向后的页面
                    return self.fetch_page(redirect_url, follow_redirects=False)
            
            return response.text
        except Exception as e:
            print(f"✗ 获取失败 {url}: {e}")
            return None
    
    def extract_text_from_html(self, html: str) -> Optional[str]:
        """从HTML中提取预报文本（在<pre>标签中）"""
        soup = BeautifulSoup(html, 'html.parser')
        pre_tags = soup.find_all('pre')
        
        if pre_tags:
            forecast_pre = max(pre_tags, key=lambda x: len(x.get_text()))
            return forecast_pre.get_text().strip()
        
        return None
    
    def get_year_cyclones(self, year: int) -> List[Dict[str, str]]:
        """获取指定年份的所有气旋信息，按海区组织"""
        year_url = f"{self.base_url}{year}/"
        html = self.fetch_page(year_url)
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        cyclones = []
        
        # 首先找到所有海区表头 (th元素，id为al/ep/cp等)
        basin_headers = {}
        for th in soup.find_all('th', id=True):
            basin_id = th.get('id', '').lower()
            if basin_id in self.BASIN_NAMES:
                basin_headers[basin_id] = th
        
        # 方法1: 新格式 (2008年之后) - 使用 atcf_index 注释
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and 'atcf_index=' in text):
            match = re.search(r'atcf_index=([a-z]{2}\d{2})', comment)
            if match:
                cyclone_id = match.group(1)
                basin_code = cyclone_id[:2]  # 提取海区代码 (al, ep, cp等)
                
                next_element = comment.next_sibling
                if next_element and next_element.name == 'a':
                    href = next_element.get('href', '')
                    name = next_element.get_text(strip=True)
                    name_only = re.sub(r'^(Hurricane|Tropical Storm|Tropical Depression)\s+', '', name)
                    
                    # 确定气旋所属的海区
                    basin_name = self.BASIN_NAMES.get(basin_code, 'Unknown')
                    
                    cyclones.append({
                        'id': cyclone_id,
                        'name': name_only,
                        'full_name': name,
                        'url': urljoin(year_url, href),
                        'format': 'new',
                        'basin': basin_name,
                        'basin_code': basin_code
                    })
        
        # 方法2: 旧格式 (2007年及之前) - 查找特定模式的链接
        if not cyclones:
            # 旧格式有多种链接模式:
            # 1998-1998: {year}{NAME}adv.html (例: 1998ALEXadv.html)
            # 1999-2002: {NAME}.html (例: ARLENE.html)
            # 2003-2007: {year}{NAME}.shtml (例: 2003ANA.shtml)
            
            # 尝试多种模式
            patterns = [
                rf'{year}([A-Z]+)adv\.html',       # 1998格式
                rf'([A-Z]+)\.html',                # 1999-2002格式
                rf'{year}([A-Z]+)\.shtml',         # 2003-2007格式
                rf'([A-Z]+)\.shtml',               # 另一种旧格式
            ]
            
            # 首先尝试查找有 headers 属性的 td 元素（部分旧格式使用）
            td_with_headers = soup.find_all('td', headers=True)
            
            if td_with_headers:
                # 有 headers 属性的情况
                current_basin = 'Atlantic'
                current_basin_code = 'al'
                
                for td in td_with_headers:
                    headers_attr = td.get('headers', '')
                    # headers_attr 可能是字符串或列表，统一处理
                    if isinstance(headers_attr, list):
                        headers_attr = headers_attr[0] if headers_attr else ''
                    
                    if headers_attr in self.BASIN_NAMES:
                        current_basin = self.BASIN_NAMES[headers_attr]
                        current_basin_code = headers_attr
                    
                    # 尝试所有模式
                    for pattern in patterns:
                        for link in td.find_all('a', href=re.compile(pattern)):
                            href = link.get('href', '')
                            text = link.get_text(strip=True)
                            
                            match = re.search(pattern, href)
                            if match:
                                cyclone_name = match.group(1)
                                
                                # 避免重复添加
                                cyclone_id = f'legacy_{year}_{cyclone_name.lower()}'
                                if not any(c['id'] == cyclone_id for c in cyclones):
                                    cyclones.append({
                                        'id': cyclone_id,
                                        'name': cyclone_name,
                                        'full_name': text,
                                        'url': urljoin(year_url, href),
                                        'format': 'legacy',
                                        'basin': current_basin,
                                        'basin_code': current_basin_code
                                    })
            else:
                # 没有 headers 属性，需要通过表格结构推断海区
                # 旧格式通常是：一行标题（多个th），下一行数据（多个td，按列对应）
                
                # 查找表格
                for table in soup.find_all('table'):
                    rows = table.find_all('tr')
                    
                    # 查找标题行（包含th的行）
                    header_row = None
                    data_rows = []
                    
                    for row in rows:
                        # 先找有id的th
                        ths = row.find_all('th', id=True)
                        if not ths:
                            # 如果没有id，找所有th（用于1999-2002这种格式）
                            ths = row.find_all('th')
                        
                        if ths:
                            # 这是标题行，记录每列对应的海区
                            header_row = ths
                        elif row.find_all('td'):
                            # 这是数据行
                            data_rows.append(row)
                    
                    # 如果找到了标题行和数据行
                    if header_row and data_rows:
                        # 建立列索引到海区的映射
                        basin_by_column = {}
                        for idx, th in enumerate(header_row):
                            basin_id = th.get('id', '').lower()
                            
                            # 如果有id属性，直接使用
                            if basin_id in self.BASIN_NAMES:
                                basin_by_column[idx] = {
                                    'name': self.BASIN_NAMES[basin_id],
                                    'code': basin_id
                                }
                            else:
                                # 如果没有id，尝试从文本内容判断
                                th_text = th.get_text(strip=True).lower()
                                if 'atlantic' in th_text:
                                    basin_by_column[idx] = {
                                        'name': 'Atlantic',
                                        'code': 'al'
                                    }
                                elif 'pacific' in th_text and 'east' not in th_text.lower():
                                    # 简单的Pacific（通常指东太平洋）
                                    basin_by_column[idx] = {
                                        'name': 'E_Pacific',
                                        'code': 'ep'
                                    }
                                elif 'central' in th_text and 'pacific' in th_text:
                                    basin_by_column[idx] = {
                                        'name': 'C_Pacific',
                                        'code': 'cp'
                                    }
                        
                        # 处理数据行
                        for row in data_rows:
                            tds = row.find_all('td')
                            
                            # 遍历每个单元格，根据列索引确定海区
                            for col_idx, td in enumerate(tds):
                                # 获取当前列对应的海区信息
                                basin_info = basin_by_column.get(col_idx, {
                                    'name': 'Atlantic',
                                    'code': 'al'
                                })
                                
                                # 在当前单元格中查找气旋链接，尝试所有模式
                                for pattern in patterns:
                                    for link in td.find_all('a', href=re.compile(pattern)):
                                        href = link.get('href', '')
                                        text = link.get_text(strip=True)
                                        
                                        match = re.search(pattern, href)
                                        if match:
                                            cyclone_name = match.group(1)
                                            
                                            # 避免重复添加
                                            cyclone_id = f'legacy_{year}_{cyclone_name.lower()}'
                                            if not any(c['id'] == cyclone_id for c in cyclones):
                                                cyclones.append({
                                                    'id': cyclone_id,
                                                    'name': cyclone_name,
                                                    'full_name': text,
                                                    'url': urljoin(year_url, href),
                                                    'format': 'legacy',
                                                    'basin': basin_info['name'],
                                                    'basin_code': basin_info['code']
                                                })
        
        # 按海区统计
        basin_counts = {}
        for cyclone in cyclones:
            basin = cyclone.get('basin', 'Unknown')
            basin_counts[basin] = basin_counts.get(basin, 0) + 1
        
        print(f"  找到 {len(cyclones)} 个气旋", end='')
        if basin_counts:
            basin_summary = ', '.join([f"{basin}: {count}" for basin, count in sorted(basin_counts.items())])
            print(f" ({basin_summary})")
        else:
            print()
        
        return cyclones
    
    def get_cyclone_advisories(self, cyclone_url: str, cyclone_id: str, year: int, format_type: str = 'new') -> Dict[str, List[str]]:
        """获取指定气旋的所有预报文件链接"""
        html = self.fetch_page(cyclone_url)
        
        if not html:
            return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        advisories = {data_type: [] for data_type in self.DATA_TYPES.keys()}
        
        if format_type == 'legacy':
            # 旧格式: 页面包含指向各个预报文件的链接
            # 有多种子格式:
            # 1. 1998格式: archive/mar/MAL0198.001 (纯文本文件)
            # 2. 1999-2002格式: /archive/1999/mar/MAL0199.001.html (HTML文件)
            # 3. 2003-2007格式: /archive/2003/mar/al012003.fstadv.001.shtml (类似新格式)
            
            # 对于2003-2007年，尝试从页面内容中提取真实的气旋ID（如 al01）
            real_cyclone_id = cyclone_id
            if year >= 2003:
                id_match = re.search(r'(al|ep|cp)(\d{2})\d{4}', html)
                if id_match:
                    real_cyclone_id = id_match.group(1) + id_match.group(2)
            
            # 先尝试新格式风格的链接（2003-2007）
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # 匹配2003-2007格式: /archive/2003/mar/al012003.fstadv.001.shtml
                year_2digit = str(year)[-2:]
                
                for short_name in self.DATA_TYPES.keys():
                    # 2003-2007年的文件名包含完整的短名称
                    # wndprb在2003-2007年可能叫prblty
                    type_patterns = [short_name]
                    if short_name == 'wndprb':
                        type_patterns.append('prblty')
                    
                    for type_name in type_patterns:
                        # 2003-2006: /archive/2003/mar/al012003.fstadv.001.shtml
                        # 2007: /archive/2007/al01/al012007.fstadv.001.shtml
                        pattern1 = rf'/archive/{year}/[a-z]+/{real_cyclone_id}{year}\.{type_name}\.\d{{3}}\.shtml'
                        pattern2 = rf'/archive/{year}/{real_cyclone_id}/{real_cyclone_id}{year}\.{type_name}\.\d{{3}}\.shtml'
                        
                        if re.search(pattern1, href) or re.search(pattern2, href):
                            full_url = urljoin(cyclone_url, href)
                            advisories[short_name].append(full_url)
                            break  # 找到一个就跳出type_patterns循环
            
            # 如果没有找到文件，尝试旧格式链接（1998-2002）
            if not any(advisories.values()):
                # 定义旧格式的目录映射
                legacy_dir_mapping = {
                    'mar': 'fstadv',     # Marine/Forecast Advisory -> fstadv
                    'pub': 'public',     # Public Advisory -> public
                    'dis': 'discus',     # Discussion -> discus
                    'prb': 'wndprb',     # Probabilities -> wndprb
                }
                
                # 查找所有链接
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    
                    # 匹配旧格式链接模式，支持多种格式:
                    # - archive/mar/MAL0198.001 (1998年格式，无扩展名)
                    # - /archive/1999/mar/MAL0199.001.html (1999+格式，有扩展名)
                    for legacy_dir, data_type in legacy_dir_mapping.items():
                        # 匹配模式：archive/{目录}/{字母}{数字}.{数字}[.html]
                        pattern = rf'archive(/\d{{4}})?/{legacy_dir}/[A-Z]+\d+\.\d+(\.html)?'
                        if re.search(pattern, href):
                            full_url = urljoin(cyclone_url, href)
                            advisories[data_type].append(full_url)
            
        else:
            # 新格式: 查找所有预报文件链接
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # 匹配预报文件格式: ep012023.discus.001.shtml
                year_2digit = str(year)[-2:]
                
                for short_name in self.DATA_TYPES.keys():
                    # 尝试4位年份
                    pattern1 = rf'{cyclone_id}{year}\.{short_name}\.\d{{3}}\.shtml'
                    # 尝试2位年份
                    pattern2 = rf'{cyclone_id}{year_2digit}\.{short_name}\.\d{{3}}\.shtml'
                    
                    if re.search(pattern1, href) or re.search(pattern2, href):
                        full_url = urljoin(cyclone_url, href)
                        advisories[short_name].append(full_url)
        
        # 对每种类型的链接排序
        for key in advisories:
            advisories[key] = sorted(advisories[key])
        
        return advisories
    
    def download_advisory(self, url: str, save_path: Path) -> bool:
        """下载单个预报文件"""
        content = self.fetch_page(url)
        
        if not content:
            return False
        
        # 检查是否是纯文本格式（旧格式文件）
        # 如果内容不包含HTML标签，说明是纯文本
        is_plain_text = not ('<html' in content.lower() or '<body' in content.lower() or '<!doctype' in content.lower())
        
        if is_plain_text:
            # 纯文本，直接保存
            text_content = content
        else:
            # HTML格式，尝试提取<pre>标签中的内容
            text_content = self.extract_text_from_html(content)
            
            if not text_content:
                # 如果没有找到<pre>标签，保存整个HTML
                text_content = content
                save_path = save_path.with_suffix('.html')
        
        # 保存文件
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        return True
    
    def crawl_cyclone(self, year: int, cyclone: Dict[str, str]) -> int:
        """爬取单个气旋的所有数据"""
        cyclone_id = cyclone['id']
        cyclone_name = cyclone['name']
        format_type = cyclone.get('format', 'new')
        basin = cyclone.get('basin', 'Unknown')
        
        print(f"\n  处理气旋: {cyclone['full_name']} ({cyclone_id}) - {basin}")
        
        # 获取所有预报文件链接
        advisories = self.get_cyclone_advisories(cyclone['url'], cyclone_id, year, format_type)
        
        files_downloaded = 0
        
        # 下载每种类型的数据
        for short_name, full_name in self.DATA_TYPES.items():
            urls = advisories.get(short_name, [])
            
            if not urls:
                # print(f"    ⚠ {full_name}: 无数据")
                continue
            
            print(f"    {full_name}: {len(urls)} 个文件", end='')
            
            # 创建目录: 年份/海区/气旋名/数据类型/
            save_dir = self.output_dir / str(year) / basin / cyclone_name / full_name
            
            downloaded_count = 0
            # 下载每个文件
            for idx, url in enumerate(urls, 1):
                # 从URL提取文件名
                filename = url.split('/')[-1].replace('.shtml', '.txt').replace('.html', '.txt')
                
                # 旧格式可能需要特殊文件名
                if format_type == 'legacy' and not filename.endswith('.txt'):
                    filename = f"{cyclone_name.lower()}_advisory_{idx:03d}.txt"
                
                save_path = save_dir / filename
                
                # 如果文件已存在，跳过
                if save_path.exists():
                    continue
                
                # 下载
                if self.download_advisory(url, save_path):
                    files_downloaded += 1
                    downloaded_count += 1
                    self.stats['files_downloaded'] += 1
                else:
                    self.stats['files_failed'] += 1
                
                # 避免请求过快
                time.sleep(0.3)
            
            if downloaded_count > 0:
                print(f" - 新下载 {downloaded_count} 个")
            else:
                print(f" - 已存在")
        
        return files_downloaded
    
    def crawl_year(self, year: int) -> int:
        """爬取指定年份的所有数据"""
        print(f"\n{'='*70}")
        print(f"处理年份: {year}")
        print(f"{'='*70}")
        
        # 获取该年所有气旋
        cyclones = self.get_year_cyclones(year)
        
        if not cyclones:
            print(f"  ⚠ {year}年无数据或无法访问")
            return 0
        
        total_files = 0
        
        # 处理每个气旋
        for cyclone in cyclones:
            files = self.crawl_cyclone(year, cyclone)
            total_files += files
            self.stats['cyclones_processed'] += 1
        
        self.stats['years_processed'] += 1
        print(f"\n  年份 {year} 完成，共下载 {total_files} 个文件")
        
        return total_files
    
    def crawl_years(self, years: List[int]):
        """批量爬取多个年份"""
        print(f"\n{'='*70}")
        print(f"开始批量爬取 {len(years)} 个年份的数据")
        print(f"年份范围: {min(years)} - {max(years)}")
        print(f"输出目录: {self.output_dir}")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        for year in years:
            self.crawl_year(year)
        
        elapsed = time.time() - start_time
        
        # 打印统计信息
        print(f"\n{'='*70}")
        print("爬取完成！统计信息:")
        print(f"{'='*70}")
        print(f"处理年份数: {self.stats['years_processed']}")
        print(f"处理气旋数: {self.stats['cyclones_processed']}")
        print(f"成功下载: {self.stats['files_downloaded']} 个文件")
        print(f"失败: {self.stats['files_failed']} 个文件")
        print(f"总耗时: {elapsed:.1f} 秒")
        print(f"输出目录: {self.output_dir.absolute()}")
        print(f"{'='*70}")
    
    def list_downloaded_data(self, year: Optional[int] = None):
        """列出已下载的数据"""
        if year:
            search_dir = self.output_dir / str(year)
        else:
            search_dir = self.output_dir
        
        if not search_dir.exists():
            print(f"目录不存在: {search_dir}")
            return
        
        print(f"\n{'='*70}")
        print(f"已下载数据列表: {search_dir}")
        print(f"{'='*70}")
        
        for year_dir in sorted(search_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            
            print(f"\n{year_dir.name}/")
            
            # 遍历海区目录
            for basin_dir in sorted(year_dir.iterdir()):
                if not basin_dir.is_dir():
                    continue
                
                print(f"  {basin_dir.name}/")
                
                # 遍历气旋目录
                for cyclone_dir in sorted(basin_dir.iterdir()):
                    if not cyclone_dir.is_dir():
                        continue
                    
                    print(f"    {cyclone_dir.name}/")
                    
                    # 遍历数据类型目录
                    for data_type_dir in sorted(cyclone_dir.iterdir()):
                        if not data_type_dir.is_dir():
                            continue
                        
                        file_count = len(list(data_type_dir.glob('*.txt')))
                        print(f"      {data_type_dir.name}/  ({file_count} 文件)")


class NOAAArchiveCrawler:
    """从NOAA飓风档案网站获取HTML内容的爬虫."""

    def __init__(
        self,
        base_url: str = "https://www.nhc.noaa.gov/archive/",
        output_dir: str = "data/output/raw/noaa_archive",
        timeout: int = 30,
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

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            }
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def fetch_page(self, url: Optional[str] = None) -> str:
        """
        获取指定URL的HTML内容.

        Args:
            url: 要获取的URL，如果为None则使用base_url

        Returns:
            页面的HTML内容
        """
        target_url = url or self.base_url

        print(f"正在获取: {target_url}")

        response = self.session.get(target_url, timeout=self.timeout)
        response.raise_for_status()

        print(f"✓ 成功获取页面 (状态码: {response.status_code})")
        return response.text

    def save_html(
        self,
        html_content: str,
        filename: Optional[str] = None,
        subdirectory: Optional[str] = None,
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
        save_dir = self.output_dir
        if subdirectory:
            save_dir = save_dir / subdirectory
            save_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"noaa_archive_{timestamp}.html"

        if not filename.endswith(".html"):
            filename += ".html"

        filepath = save_dir / filename

        with open(filepath, "w", encoding="utf-8") as file:
            file.write(html_content)

        print(f"✓ HTML内容已保存到: {filepath}")
        print(f"  文件大小: {len(html_content):,} 字符")

        return filepath

    def fetch_and_save(
        self,
        url: Optional[str] = None,
        filename: Optional[str] = None,
        subdirectory: Optional[str] = None,
    ) -> Path:
        """获取页面HTML并保存到本地."""
        html_content = self.fetch_page(url)
        return self.save_html(html_content, filename, subdirectory)

    def parse_archive_index(self, html_content: str) -> List[Dict[str, str]]:
        """解析档案索引页面，提取所有年份链接."""
        soup = BeautifulSoup(html_content, "html.parser")
        links: List[Dict[str, str]] = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)

            if href.startswith("http"):
                full_url = href
            else:
                full_url = self.base_url.rstrip("/") + "/" + href.lstrip("/")

            links.append(
                {
                    "text": text,
                    "href": href,
                    "full_url": full_url,
                }
            )

        print(f"✓ 解析到 {len(links)} 个链接")
        return links

    def crawl_multiple_years(self, years: List[int]) -> List[Path]:
        """抓取多个年份的档案页面."""
        saved_files: List[Path] = []

        for year in years:
            try:
                year_url = f"{self.base_url.rstrip('/')}/{year}/"
                filename = f"archive_{year}.html"

                filepath = self.fetch_and_save(
                    url=year_url,
                    filename=filename,
                    subdirectory=str(year),
                )
                saved_files.append(filepath)
            except Exception as exc:
                print(f"✗ 获取 {year} 年数据失败: {exc}")
                continue

        return saved_files


class NOAAForecastExtractor:
    """NOAA飓风预报文本提取器."""

    def __init__(self, output_dir: str = "data/output/raw/noaa_forecasts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36"
                )
            }
        )

    def fetch_page(self, url: str) -> Optional[str]:
        """获取网页HTML内容."""
        try:
            print(f"正在获取: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            print(f"✓ 成功获取 (状态码: {response.status_code})")
            return response.text
        except Exception as exc:
            print(f"✗ 获取失败: {exc}")
            return None

    def extract_forecast_text(self, html_content: str) -> Optional[str]:
        """从HTML中提取预报文本内容."""
        soup = BeautifulSoup(html_content, "html.parser")

        pre_tags = soup.find_all("pre")
        if pre_tags:
            forecast_pre = max(pre_tags, key=lambda tag: len(tag.get_text()))
            forecast_text = forecast_pre.get_text().strip()
            if len(forecast_text) > 100:
                return forecast_text

        content_divs = soup.find_all(
            "div", class_=["textproduct", "text-product", "forecast-text"]
        )
        for div in content_divs:
            text = div.get_text().strip()
            if len(text) > 100:
                return text

        text = soup.get_text()
        if "ZCZC" in text:
            lines = text.split("\n")
            in_forecast = False
            forecast_lines: List[str] = []

            for line in lines:
                if "ZCZC" in line or in_forecast:
                    in_forecast = True
                    forecast_lines.append(line)
                    if "NNNN" in line:
                        break

            if forecast_lines:
                return "\n".join(forecast_lines).strip()

        print("⚠ 未能提取到预报文本")
        return None

    def save_forecast(
        self,
        forecast_text: str,
        filename: str,
        save_html: bool = False,
        html_content: Optional[str] = None,
    ) -> Path:
        """保存预报文本到文件."""
        txt_file = self.output_dir / f"{filename}.txt"
        with open(txt_file, "w", encoding="utf-8") as file:
            file.write(forecast_text)

        print(f"✓ 预报文本已保存: {txt_file}")
        print(f"  文本长度: {len(forecast_text):,} 字符")
        print(f"  行数: {len(forecast_text.splitlines())}")

        if save_html and html_content:
            html_file = self.output_dir / f"{filename}.html"
            with open(html_file, "w", encoding="utf-8") as file:
                file.write(html_content)
            print(f"✓ HTML已保存: {html_file}")

        return txt_file

    def fetch_and_extract(
        self,
        url: str,
        filename: Optional[str] = None,
        save_html: bool = False,
    ) -> Optional[Path]:
        """获取页面并提取预报文本."""
        if filename is None:
            url_parts = url.rstrip("/").split("/")
            filename = (
                url_parts[-1].replace(".shtml", "").replace(".html", "")
                if url_parts
                else f"forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        html_content = self.fetch_page(url)
        if not html_content:
            return None

        forecast_text = self.extract_forecast_text(html_content)
        if not forecast_text:
            print("⚠ 未能提取预报文本，保存原始HTML供检查")
            save_html = True

        if forecast_text:
            return self.save_forecast(forecast_text, filename, save_html, html_content)

        if save_html:
            html_file = self.output_dir / f"{filename}_raw.html"
            with open(html_file, "w", encoding="utf-8") as file:
                file.write(html_content)
            print(f"✓ 原始HTML已保存: {html_file}")
            return html_file

        return None

    def display_preview(self, forecast_text: str, lines: int = 30) -> None:
        """显示预报文本预览."""
        print("\n" + "=" * 70)
        print(f"预报文本预览 (前{lines}行):")
        print("=" * 70)

        text_lines = forecast_text.split("\n")
        for idx, line in enumerate(text_lines[:lines], 1):
            print(line)

        if len(text_lines) > lines:
            print(f"\n... (还有 {len(text_lines) - lines} 行未显示)")

        print("=" * 70)


def main():
    """主函数"""
    print("="*70)
    print("NOAA飓风数据完整爬虫")
    print("="*70)
    
    # 创建爬虫
    crawler = NOAACompleteCrawler()
    
    # 示例：爬取最近几年的数据
    print("\n选项:")
    print("1. 爬取单个年份")
    print("2. 爬取多个年份")
    print("3. 爬取2021-2023年")
    print("4. 爬取2023年（测试）")
    print("5. 查看已下载数据")
    
    choice = input("\n请选择 (1-5): ").strip()
    
    if choice == '1':
        year = int(input("请输入年份 (如 2023): "))
        crawler.crawl_year(year)
    
    elif choice == '2':
        years_input = input("请输入年份，用逗号分隔 (如 2021,2022,2023): ")
        years = [int(y.strip()) for y in years_input.split(',')]
        crawler.crawl_years(years)
    
    elif choice == '3':
        years = [2021, 2022, 2023]
        crawler.crawl_years(years)
    
    elif choice == '4':
        # 快速测试模式 - 只下载2023年前3个气旋
        print("\n快速测试模式 - 2023年前3个气旋")
        crawler.crawl_year(2023)
    
    elif choice == '5':
        crawler.list_downloaded_data()
    
    else:
        print("无效选择")


if __name__ == "__main__":
    main()

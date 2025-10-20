#!/usr/bin/env python3
"""
NOAA飓风预报文本提取工具
从NOAA预报页面提取灰色框中的纯文本预报内容
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup


class NOAAForecastExtractor:
    """NOAA飓风预报文本提取器"""
    
    def __init__(self, output_dir="data/output/raw/noaa_forecasts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_page(self, url: str) -> Optional[str]:
        """获取网页HTML内容"""
        try:
            print(f"正在获取: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            print(f"✓ 成功获取 (状态码: {response.status_code})")
            return response.text
        except Exception as e:
            print(f"✗ 获取失败: {e}")
            return None
    
    def extract_forecast_text(self, html_content: str) -> Optional[str]:
        """
        从HTML中提取预报文本内容
        NOAA的预报文本通常在<pre>标签中
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 方法1: 查找<pre>标签（最常见的预报文本格式）
        pre_tags = soup.find_all('pre')
        
        if pre_tags:
            # 通常第一个或最大的<pre>标签包含预报文本
            # 找到内容最多的<pre>标签
            forecast_pre = max(pre_tags, key=lambda x: len(x.get_text()))
            forecast_text = forecast_pre.get_text()
            
            # 清理文本
            forecast_text = forecast_text.strip()
            
            if len(forecast_text) > 100:  # 确保有实质内容
                return forecast_text
        
        # 方法2: 查找特定class的div（备用方法）
        content_divs = soup.find_all('div', class_=['textproduct', 'text-product', 'forecast-text'])
        for div in content_divs:
            text = div.get_text().strip()
            if len(text) > 100:
                return text
        
        # 方法3: 查找包含"ZCZC"的文本块（NOAA产品标识符）
        text = soup.get_text()
        if 'ZCZC' in text:
            # 提取从ZCZC开始的文本块
            lines = text.split('\n')
            in_forecast = False
            forecast_lines = []
            
            for line in lines:
                if 'ZCZC' in line or in_forecast:
                    in_forecast = True
                    forecast_lines.append(line)
                    if 'NNNN' in line:  # NOAA产品结束标识
                        break
            
            if forecast_lines:
                return '\n'.join(forecast_lines).strip()
        
        print("⚠ 未能提取到预报文本")
        return None
    
    def save_forecast(self, forecast_text: str, filename: str, 
                     save_html: bool = False, html_content: str = None) -> Path:
        """保存预报文本到文件"""
        
        # 保存文本文件
        txt_file = self.output_dir / f"{filename}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(forecast_text)
        
        print(f"✓ 预报文本已保存: {txt_file}")
        print(f"  文本长度: {len(forecast_text):,} 字符")
        print(f"  行数: {len(forecast_text.splitlines())}")
        
        # 可选：同时保存HTML
        if save_html and html_content:
            html_file = self.output_dir / f"{filename}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✓ HTML已保存: {html_file}")
        
        return txt_file
    
    def fetch_and_extract(self, url: str, filename: Optional[str] = None,
                         save_html: bool = False) -> Optional[Path]:
        """获取页面并提取预报文本"""
        
        # 从URL生成文件名
        if filename is None:
            # 提取URL中的文件名部分
            url_parts = url.rstrip('/').split('/')
            filename = url_parts[-1].replace('.shtml', '').replace('.html', '')
            if not filename:
                filename = f"forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 获取HTML
        html_content = self.fetch_page(url)
        if not html_content:
            return None
        
        # 提取预报文本
        forecast_text = self.extract_forecast_text(html_content)
        if not forecast_text:
            print("⚠ 未能提取预报文本，保存原始HTML供检查")
            save_html = True
        
        # 保存
        if forecast_text:
            return self.save_forecast(forecast_text, filename, save_html, html_content)
        elif save_html:
            html_file = self.output_dir / f"{filename}_raw.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✓ 原始HTML已保存: {html_file}")
            return html_file
        
        return None
    
    def display_preview(self, forecast_text: str, lines: int = 30):
        """显示预报文本预览"""
        print("\n" + "=" * 70)
        print("预报文本预览 (前{}行):".format(lines))
        print("=" * 70)
        
        text_lines = forecast_text.split('\n')
        for i, line in enumerate(text_lines[:lines], 1):
            print(line)
        
        if len(text_lines) > lines:
            print(f"\n... (还有 {len(text_lines) - lines} 行未显示)")
        
        print("=" * 70)


def main():
    """主函数"""
    
    print("=" * 70)
    print("NOAA飓风预报文本提取工具")
    print("=" * 70)
    
    # 创建提取器
    extractor = NOAAForecastExtractor()
    
    # 示例URL（根据您的截图）
    example_url = "https://www.nhc.noaa.gov/archive/2023/ep01/ep012023.discus.001.shtml"
    
    print(f"\n示例URL: {example_url}\n")
    
    # 提取预报文本
    result = extractor.fetch_and_extract(example_url, save_html=True)
    
    if result:
        # 读取并显示预览
        if result.suffix == '.txt':
            with open(result, 'r', encoding='utf-8') as f:
                forecast_text = f.read()
            extractor.display_preview(forecast_text, lines=50)
    
    print("\n" + "=" * 70)
    print("批量下载示例")
    print("=" * 70)
    
    # 可以批量下载多个预报文件
    response = input("\n是否要下载更多预报文件? (y/n): ")
    
    if response.lower() == 'y':
        # 示例：下载同一风暴的多个预报
        storm_id = "ep012023"
        base_url = f"https://www.nhc.noaa.gov/archive/2023/ep01/"
        
        # 下载前5个讨论文件
        for i in range(1, 6):
            file_num = str(i).zfill(3)
            url = f"{base_url}{storm_id}.discus.{file_num}.shtml"
            filename = f"{storm_id}_discus_{file_num}"
            
            print(f"\n下载 #{i}...")
            extractor.fetch_and_extract(url, filename, save_html=False)
    
    print("\n" + "=" * 70)
    print("完成!")
    print(f"所有文件保存在: {extractor.output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()

"""
气旋事件匹配和预报数据提取工具
用于将IBTrACS气旋事件与NOAA预报文件匹配，并提取预报和讨论信息
"""

import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import re


class CycloneMatcher:
    """气旋事件匹配器"""
    
    def __init__(self, ibtracs_path: str, noaa_base_path: str):
        """
        初始化匹配器
        
        Args:
            ibtracs_path: IBTrACS CSV文件路径
            noaa_base_path: NOAA数据根目录路径
        """
        self.ibtracs_path = Path(ibtracs_path)
        self.noaa_base_path = Path(noaa_base_path)
        self.ibtracs_data = None
        self.noaa_storms = []
        
    def load_ibtracs_data(self) -> pd.DataFrame:
        """加载IBTrACS数据"""
        print(f"Loading IBTrACS data from {self.ibtracs_path}...")
        self.ibtracs_data = pd.read_csv(self.ibtracs_path)
        
        # 提取年份信息
        self.ibtracs_data['year'] = pd.to_datetime(
            self.ibtracs_data['iso_time'], errors='coerce'
        ).dt.year
        
        # 清理风暴名称（转大写，去除空格）
        self.ibtracs_data['name_clean'] = (
            self.ibtracs_data['name']
            .str.upper()
            .str.strip()
        )
        
        print(f"Loaded {len(self.ibtracs_data)} records from IBTrACS")
        return self.ibtracs_data
    
    def scan_noaa_directory(self) -> List[Dict]:
        """扫描NOAA目录结构"""
        print(f"\nScanning NOAA directory: {self.noaa_base_path}...")
        self.noaa_storms = []
        
        if not self.noaa_base_path.exists():
            print(f"Error: NOAA directory not found: {self.noaa_base_path}")
            return self.noaa_storms
        
        for year_dir in sorted(self.noaa_base_path.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
                
            year = int(year_dir.name)
            
            for basin_dir in year_dir.iterdir():
                if not basin_dir.is_dir():
                    continue
                    
                basin = basin_dir.name
                
                for storm_dir in basin_dir.iterdir():
                    if not storm_dir.is_dir():
                        continue
                    
                    storm_name = storm_dir.name.upper().strip()
                    
                    # 检查是否有预报文件
                    forecast_adv_dir = storm_dir / 'forecast_advisory'
                    forecast_disc_dir = storm_dir / 'forecast_discussion'
                    
                    has_advisory = forecast_adv_dir.exists() and any(forecast_adv_dir.iterdir())
                    has_discussion = forecast_disc_dir.exists() and any(forecast_disc_dir.iterdir())
                    
                    if has_advisory or has_discussion:
                        self.noaa_storms.append({
                            'year': year,
                            'basin': basin,
                            'storm_name': storm_name,
                            'storm_path': str(storm_dir),
                            'has_advisory': has_advisory,
                            'has_discussion': has_discussion
                        })
        
        print(f"Found {len(self.noaa_storms)} storms in NOAA data")
        return self.noaa_storms
    
    def match_storms(self) -> pd.DataFrame:
        """
        匹配IBTrACS和NOAA中的气旋事件
        
        Returns:
            匹配结果的DataFrame
        """
        print("\nMatching storms between IBTrACS and NOAA...")
        
        if self.ibtracs_data is None:
            self.load_ibtracs_data()
        
        if not self.noaa_storms:
            self.scan_noaa_directory()
        
        # 获取IBTrACS中的唯一风暴
        ibtracs_storms = self.ibtracs_data.groupby(['sid', 'name_clean', 'year']).agg({
            'season': 'first',
            'iso_time': ['min', 'max']
        }).reset_index()
        
        ibtracs_storms.columns = ['sid', 'name', 'year', 'season', 'start_time', 'end_time']
        
        # 匹配NOAA风暴
        matched_storms = []
        
        for noaa_storm in self.noaa_storms:
            # 基于年份和名称匹配
            year = noaa_storm['year']
            name = noaa_storm['storm_name']
            
            # 清理NOAA风暴名称（移除"Potential Tropical Cyclone"等前缀）
            name_clean = self._clean_storm_name(name)
            
            # 在IBTrACS中查找匹配
            matches = ibtracs_storms[
                (ibtracs_storms['year'] == year) & 
                (ibtracs_storms['name'].str.contains(name_clean, case=False, na=False))
            ]
            
            if len(matches) > 0:
                # 如果有多个匹配，取第一个
                match = matches.iloc[0]
                matched_storms.append({
                    'ibtracs_sid': match['sid'],
                    'ibtracs_name': match['name'],
                    'year': year,
                    'season': match['season'],
                    'start_time': match['start_time'],
                    'end_time': match['end_time'],
                    'noaa_basin': noaa_storm['basin'],
                    'noaa_name': noaa_storm['storm_name'],
                    'noaa_path': noaa_storm['storm_path'],
                    'has_advisory': noaa_storm['has_advisory'],
                    'has_discussion': noaa_storm['has_discussion']
                })
        
        matched_df = pd.DataFrame(matched_storms)
        print(f"\nMatched {len(matched_df)} storms between IBTrACS and NOAA")
        
        return matched_df
    
    def _clean_storm_name(self, name: str) -> str:
        """清理风暴名称"""
        # 移除常见前缀
        name = re.sub(r'^Potential Tropical Cyclone\s+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'^Tropical (Depression|Storm|Cyclone)\s+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'^Hurricane\s+', '', name, flags=re.IGNORECASE)
        
        # 如果名称是数字（如"EIGHT"），保留
        # 否则取第一个单词
        words = name.strip().split()
        if words:
            return words[0].upper()
        return name.upper()
    
    def extract_forecast_data(self, matched_storms_df: pd.DataFrame, output_dir: str) -> Dict:
        """
        提取预报和讨论数据
        
        Args:
            matched_storms_df: 匹配的风暴DataFrame
            output_dir: 输出目录
            
        Returns:
            包含所有风暴预报数据的字典
        """
        print("\nExtracting forecast and discussion data...")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        all_storms_data = {}
        
        for idx, row in matched_storms_df.iterrows():
            storm_key = f"{row['year']}_{row['noaa_basin']}_{row['noaa_name']}"
            print(f"\nProcessing {storm_key}...")
            
            storm_data = {
                'ibtracs_sid': row['ibtracs_sid'],
                'ibtracs_name': row['ibtracs_name'],
                'noaa_name': row['noaa_name'],
                'year': int(row['year']),
                'season': float(row['season']),
                'basin': row['noaa_basin'],
                'start_time': row['start_time'],
                'end_time': row['end_time'],
                'forecasts': [],
                'discussions': []
            }
            
            storm_path = Path(row['noaa_path'])
            
            # 提取预报advisory
            if row['has_advisory']:
                advisory_dir = storm_path / 'forecast_advisory'
                storm_data['forecasts'] = self._extract_text_files(advisory_dir)
            
            # 提取预报discussion
            if row['has_discussion']:
                discussion_dir = storm_path / 'forecast_discussion'
                storm_data['discussions'] = self._extract_text_files(discussion_dir)
            
            all_storms_data[storm_key] = storm_data
            
            print(f"  - Extracted {len(storm_data['forecasts'])} forecasts")
            print(f"  - Extracted {len(storm_data['discussions'])} discussions")
        
        # 保存为JSON文件
        json_output_path = output_path / 'cyclone_forecasts.json'
        with open(json_output_path, 'w', encoding='utf-8') as f:
            json.dump(all_storms_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved forecast data to {json_output_path}")
        
        return all_storms_data
    
    def _extract_text_files(self, directory: Path) -> List[Dict]:
        """
        提取目录中的文本文件
        
        Args:
            directory: 文件目录
            
        Returns:
            包含文件内容的列表
        """
        files_data = []
        
        if not directory.exists():
            return files_data
        
        for file_path in sorted(directory.iterdir()):
            if file_path.suffix == '.txt':
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 提取时间戳（如果有）
                    timestamp = self._extract_timestamp(content)
                    
                    files_data.append({
                        'filename': file_path.name,
                        'timestamp': timestamp,
                        'content': content
                    })
                except Exception as e:
                    print(f"    Warning: Failed to read {file_path}: {e}")
        
        return files_data
    
    def _extract_timestamp(self, content: str) -> str:
        """从文件内容中提取时间戳"""
        # 尝试匹配常见的时间格式
        patterns = [
            r'(\d{1,2}:\d{2}\s+(?:AM|PM)\s+[A-Z]{3}\s+\w+\s+\w+\s+\d{1,2}\s+\d{4})',
            r'(\d{4}\s+UTC\s+\w+\s+\w+\s+\d{1,2}\s+\d{4})',
            r'(\d{2}/\d{4}Z)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        return ""
    
    def save_matched_storms_csv(self, matched_df: pd.DataFrame, output_path: str):
        """
        保存匹配的风暴列表为CSV
        
        Args:
            matched_df: 匹配的风暴DataFrame
            output_path: 输出CSV文件路径
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        matched_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\nSaved matched storms CSV to {output_file}")


def main():
    """主函数"""
    # 配置路径
    ibtracs_path = 'cycloneTrack/ibtracs_master_index_1980-2025.csv'
    noaa_base_path = 'data/output/raw/noaa_complete'
    output_base = 'data/output/processed'
    
    # 创建匹配器
    matcher = CycloneMatcher(ibtracs_path, noaa_base_path)
    
    # 加载和匹配数据
    matcher.load_ibtracs_data()
    matcher.scan_noaa_directory()
    matched_df = matcher.match_storms()
    
    # 保存匹配结果CSV
    csv_output = f'{output_base}/matched_cyclones.csv'
    matcher.save_matched_storms_csv(matched_df, csv_output)
    
    # 提取预报数据并保存为JSON
    forecast_data = matcher.extract_forecast_data(matched_df, output_base)
    
    print("\n" + "="*50)
    print("处理完成!")
    print(f"匹配的气旋事件: {len(matched_df)}")
    print(f"CSV输出: {csv_output}")
    print(f"JSON输出: {output_base}/cyclone_forecasts.json")
    print("="*50)


if __name__ == '__main__':
    main()

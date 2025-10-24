"""
气旋预报数据查询工具
用于查询和分析cyclone_forecasts.json中的数据
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional


class CycloneDataQuery:
    """气旋预报数据查询类"""
    
    def __init__(self, json_path: str):
        """
        初始化查询工具
        
        Args:
            json_path: JSON文件路径
        """
        self.json_path = Path(json_path)
        self.data = None
        self.load_data()
    
    def load_data(self):
        """加载JSON数据"""
        if not self.json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {self.json_path}")
        
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        print(f"Loaded data for {len(self.data)} storms")
    
    def list_all_storms(self) -> List[str]:
        """列出所有气旋"""
        return list(self.data.keys())
    
    def get_storm_by_name(self, name: str, year: Optional[int] = None) -> Dict:
        """
        根据名称查询气旋
        
        Args:
            name: 气旋名称
            year: 年份（可选）
            
        Returns:
            匹配的气旋数据
        """
        name_upper = name.upper()
        matches = []
        
        for key, storm in self.data.items():
            if storm['noaa_name'].upper() == name_upper:
                if year is None or storm['year'] == year:
                    matches.append((key, storm))
        
        return matches
    
    def get_storm_by_year(self, year: int) -> List[Dict]:
        """
        根据年份查询气旋
        
        Args:
            year: 年份
            
        Returns:
            该年份的所有气旋
        """
        return [(k, v) for k, v in self.data.items() if v['year'] == year]
    
    def get_storm_by_basin(self, basin: str) -> List[Dict]:
        """
        根据流域查询气旋
        
        Args:
            basin: 流域名称（Atlantic, E_Pacific, C_Pacific）
            
        Returns:
            该流域的所有气旋
        """
        return [(k, v) for k, v in self.data.items() if v['basin'] == basin]
    
    def get_storm_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {
            'total_storms': len(self.data),
            'years': {},
            'basins': {},
            'total_forecasts': 0,
            'total_discussions': 0
        }
        
        for storm in self.data.values():
            year = storm['year']
            basin = storm['basin']
            
            stats['years'][year] = stats['years'].get(year, 0) + 1
            stats['basins'][basin] = stats['basins'].get(basin, 0) + 1
            stats['total_forecasts'] += len(storm['forecasts'])
            stats['total_discussions'] += len(storm['discussions'])
        
        return stats
    
    def search_in_content(self, keyword: str, 
                         search_in: str = 'both',
                         limit: int = 10) -> List[Dict]:
        """
        在预报和讨论内容中搜索关键词
        
        Args:
            keyword: 搜索关键词
            search_in: 搜索范围 ('forecasts', 'discussions', 'both')
            limit: 最大返回结果数
            
        Returns:
            包含关键词的气旋列表
        """
        results = []
        keyword_lower = keyword.lower()
        
        for key, storm in self.data.items():
            matches = []
            
            if search_in in ['forecasts', 'both']:
                for forecast in storm['forecasts']:
                    if keyword_lower in forecast['content'].lower():
                        matches.append({
                            'type': 'forecast',
                            'filename': forecast['filename'],
                            'timestamp': forecast['timestamp']
                        })
            
            if search_in in ['discussions', 'both']:
                for discussion in storm['discussions']:
                    if keyword_lower in discussion['content'].lower():
                        matches.append({
                            'type': 'discussion',
                            'filename': discussion['filename'],
                            'timestamp': discussion['timestamp']
                        })
            
            if matches:
                results.append({
                    'storm_key': key,
                    'storm_name': storm['noaa_name'],
                    'year': storm['year'],
                    'basin': storm['basin'],
                    'matches': matches
                })
                
                if len(results) >= limit:
                    break
        
        return results
    
    def print_storm_info(self, storm_key: str):
        """打印气旋详细信息"""
        if storm_key not in self.data:
            print(f"Storm not found: {storm_key}")
            return
        
        storm = self.data[storm_key]
        
        print(f"\n{'='*60}")
        print(f"Storm: {storm_key}")
        print(f"{'='*60}")
        print(f"IBTrACS SID: {storm['ibtracs_sid']}")
        print(f"IBTrACS Name: {storm['ibtracs_name']}")
        print(f"NOAA Name: {storm['noaa_name']}")
        print(f"Year: {storm['year']}")
        print(f"Season: {storm['season']}")
        print(f"Basin: {storm['basin']}")
        print(f"Start Time: {storm['start_time']}")
        print(f"End Time: {storm['end_time']}")
        print(f"\nForecasts: {len(storm['forecasts'])} files")
        print(f"Discussions: {len(storm['discussions'])} files")
        
        if storm['forecasts']:
            print(f"\nFirst forecast: {storm['forecasts'][0]['filename']}")
            print(f"  Timestamp: {storm['forecasts'][0]['timestamp']}")
        
        if storm['discussions']:
            print(f"\nFirst discussion: {storm['discussions'][0]['filename']}")
            print(f"  Timestamp: {storm['discussions'][0]['timestamp']}")
        
        print(f"{'='*60}\n")


def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description='查询气旋预报数据')
    parser.add_argument('--json', default='data/output/processed/cyclone_forecasts.json',
                       help='JSON文件路径')
    parser.add_argument('--stats', action='store_true',
                       help='显示统计信息')
    parser.add_argument('--list', action='store_true',
                       help='列出所有气旋')
    parser.add_argument('--name', type=str,
                       help='根据名称查询气旋')
    parser.add_argument('--year', type=int,
                       help='根据年份查询气旋')
    parser.add_argument('--basin', type=str,
                       help='根据流域查询气旋 (Atlantic, E_Pacific, C_Pacific)')
    parser.add_argument('--info', type=str,
                       help='显示指定气旋的详细信息（使用storm_key，如：2024_Atlantic_BERYL）')
    parser.add_argument('--search', type=str,
                       help='在内容中搜索关键词')
    parser.add_argument('--search-in', choices=['forecasts', 'discussions', 'both'],
                       default='both', help='搜索范围')
    parser.add_argument('--limit', type=int, default=10,
                       help='搜索结果限制数量')
    
    args = parser.parse_args()
    
    # 初始化查询工具
    query = CycloneDataQuery(args.json)
    
    # 显示统计信息
    if args.stats:
        stats = query.get_storm_statistics()
        print("\n=== 气旋预报数据统计 ===")
        print(f"总气旋数: {stats['total_storms']}")
        print(f"总预报文件数: {stats['total_forecasts']}")
        print(f"总讨论文件数: {stats['total_discussions']}")
        print("\n按年份分布:")
        for year in sorted(stats['years'].keys()):
            print(f"  {year}: {stats['years'][year]} storms")
        print("\n按流域分布:")
        for basin, count in sorted(stats['basins'].items()):
            print(f"  {basin}: {count} storms")
    
    # 列出所有气旋
    if args.list:
        storms = query.list_all_storms()
        print(f"\n=== 所有气旋列表 ({len(storms)}个) ===")
        for i, storm in enumerate(storms, 1):
            print(f"{i}. {storm}")
    
    # 根据名称查询
    if args.name:
        matches = query.get_storm_by_name(args.name, args.year)
        print(f"\n=== 名称匹配: {args.name} ===")
        if matches:
            for key, storm in matches:
                print(f"\n{key}")
                print(f"  Year: {storm['year']}, Basin: {storm['basin']}")
                print(f"  Forecasts: {len(storm['forecasts'])}, Discussions: {len(storm['discussions'])}")
        else:
            print("未找到匹配的气旋")
    
    # 根据年份查询
    if args.year and not args.name:
        matches = query.get_storm_by_year(args.year)
        print(f"\n=== 年份: {args.year} ({len(matches)}个气旋) ===")
        for key, storm in matches:
            print(f"{key} - {storm['basin']}")
    
    # 根据流域查询
    if args.basin:
        matches = query.get_storm_by_basin(args.basin)
        print(f"\n=== 流域: {args.basin} ({len(matches)}个气旋) ===")
        for key, storm in matches:
            print(f"{key} - {storm['year']}")
    
    # 显示详细信息
    if args.info:
        query.print_storm_info(args.info)
    
    # 搜索关键词
    if args.search:
        results = query.search_in_content(args.search, args.search_in, args.limit)
        print(f"\n=== 搜索结果: '{args.search}' ===")
        print(f"找到 {len(results)} 个匹配的气旋")
        for result in results:
            print(f"\n{result['storm_key']}")
            print(f"  匹配数: {len(result['matches'])}")
            for match in result['matches'][:3]:  # 只显示前3个匹配
                print(f"    - {match['type']}: {match['filename']} ({match['timestamp']})")


if __name__ == '__main__':
    main()

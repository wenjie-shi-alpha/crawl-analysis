"""
气旋预报数据使用示例
演示如何在Python程序中使用cyclone_forecasts.json数据
"""

import json
from pathlib import Path
from typing import Dict, List
import re


def load_cyclone_data(json_path: str = 'data/output/processed/cyclone_forecasts.json') -> Dict:
    """加载气旋预报数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_storm_by_key(data: Dict, storm_key: str) -> Dict:
    """通过storm_key获取气旋数据"""
    return data.get(storm_key)


def get_storm_forecasts_summary(storm_data: Dict) -> Dict:
    """获取气旋预报摘要统计"""
    forecasts = storm_data.get('forecasts', [])
    discussions = storm_data.get('discussions', [])
    
    summary = {
        'storm_name': storm_data.get('noaa_name'),
        'year': storm_data.get('year'),
        'basin': storm_data.get('basin'),
        'total_forecasts': len(forecasts),
        'total_discussions': len(discussions),
        'forecast_filenames': [f['filename'] for f in forecasts],
        'discussion_filenames': [d['filename'] for d in discussions],
    }
    
    if forecasts:
        summary['first_forecast_time'] = forecasts[0].get('timestamp')
        summary['last_forecast_time'] = forecasts[-1].get('timestamp')
    
    return summary


def extract_wind_speeds_from_forecast(forecast_content: str) -> List[int]:
    """从预报内容中提取风速信息"""
    # 查找 "MAX WIND XX KT" 模式
    pattern = r'MAX WIND\s+(\d+)\s+KT'
    matches = re.findall(pattern, forecast_content, re.IGNORECASE)
    return [int(m) for m in matches]


def analyze_storm_intensity_evolution(storm_data: Dict) -> Dict:
    """分析气旋强度演变"""
    forecasts = storm_data.get('forecasts', [])
    
    intensity_data = {
        'storm_name': storm_data.get('noaa_name'),
        'year': storm_data.get('year'),
        'max_winds': [],
        'timestamps': []
    }
    
    for forecast in forecasts:
        content = forecast.get('content', '')
        winds = extract_wind_speeds_from_forecast(content)
        timestamp = forecast.get('timestamp', '')
        
        if winds:
            intensity_data['max_winds'].append(max(winds))
            intensity_data['timestamps'].append(timestamp)
    
    if intensity_data['max_winds']:
        intensity_data['peak_intensity'] = max(intensity_data['max_winds'])
        intensity_data['initial_intensity'] = intensity_data['max_winds'][0]
        intensity_data['final_intensity'] = intensity_data['max_winds'][-1]
    
    return intensity_data


def search_keyword_in_discussions(storm_data: Dict, keyword: str) -> List[Dict]:
    """在讨论内容中搜索关键词"""
    discussions = storm_data.get('discussions', [])
    matches = []
    
    keyword_lower = keyword.lower()
    
    for discussion in discussions:
        content = discussion.get('content', '')
        if keyword_lower in content.lower():
            # 提取包含关键词的句子
            sentences = re.split(r'[.!?]\s+', content)
            relevant_sentences = [
                s for s in sentences if keyword_lower in s.lower()
            ]
            
            matches.append({
                'filename': discussion.get('filename'),
                'timestamp': discussion.get('timestamp'),
                'relevant_sentences': relevant_sentences[:3]  # 只取前3个句子
            })
    
    return matches


def get_storms_by_year_and_basin(data: Dict, year: int, basin: str) -> List[Dict]:
    """获取特定年份和流域的所有气旋"""
    storms = []
    
    for storm_key, storm_data in data.items():
        if storm_data.get('year') == year and storm_data.get('basin') == basin:
            storms.append({
                'key': storm_key,
                'name': storm_data.get('noaa_name'),
                'start_time': storm_data.get('start_time'),
                'end_time': storm_data.get('end_time'),
                'num_forecasts': len(storm_data.get('forecasts', [])),
                'num_discussions': len(storm_data.get('discussions', []))
            })
    
    return sorted(storms, key=lambda x: x['start_time'])


def example_1_basic_usage():
    """示例1：基本使用"""
    print("="*60)
    print("示例1：基本使用 - 加载和查询气旋数据")
    print("="*60)
    
    # 加载数据
    data = load_cyclone_data()
    print(f"已加载 {len(data)} 个气旋的数据\n")
    
    # 查询特定气旋
    storm_key = "2024_Atlantic_BERYL"
    storm_data = get_storm_by_key(data, storm_key)
    
    if storm_data:
        print(f"气旋: {storm_key}")
        print(f"名称: {storm_data['noaa_name']}")
        print(f"年份: {storm_data['year']}")
        print(f"流域: {storm_data['basin']}")
        print(f"预报文件数: {len(storm_data['forecasts'])}")
        print(f"讨论文件数: {len(storm_data['discussions'])}")


def example_2_forecast_summary():
    """示例2：预报摘要"""
    print("\n" + "="*60)
    print("示例2：获取预报摘要")
    print("="*60)
    
    data = load_cyclone_data()
    storm_data = get_storm_by_key(data, "2024_Atlantic_BERYL")
    
    if storm_data:
        summary = get_storm_forecasts_summary(storm_data)
        print(f"\n气旋: {summary['storm_name']}")
        print(f"总预报数: {summary['total_forecasts']}")
        print(f"总讨论数: {summary['total_discussions']}")
        print(f"首次预报时间: {summary.get('first_forecast_time')}")
        print(f"最后预报时间: {summary.get('last_forecast_time')}")


def example_3_intensity_analysis():
    """示例3：强度分析"""
    print("\n" + "="*60)
    print("示例3：分析气旋强度演变")
    print("="*60)
    
    data = load_cyclone_data()
    storm_data = get_storm_by_key(data, "2024_Atlantic_BERYL")
    
    if storm_data:
        intensity = analyze_storm_intensity_evolution(storm_data)
        print(f"\n气旋: {intensity['storm_name']}")
        print(f"初始强度: {intensity.get('initial_intensity')} kt")
        print(f"峰值强度: {intensity.get('peak_intensity')} kt")
        print(f"最终强度: {intensity.get('final_intensity')} kt")
        print(f"\n强度演变:")
        for i, (wind, time) in enumerate(zip(intensity['max_winds'][:5], intensity['timestamps'][:5])):
            print(f"  {i+1}. {wind} kt ({time})")
        if len(intensity['max_winds']) > 5:
            print(f"  ... (共 {len(intensity['max_winds'])} 个数据点)")


def example_4_keyword_search():
    """示例4：关键词搜索"""
    print("\n" + "="*60)
    print("示例4：在讨论中搜索关键词")
    print("="*60)
    
    data = load_cyclone_data()
    storm_data = get_storm_by_key(data, "2024_Atlantic_BERYL")
    
    if storm_data:
        keyword = "rapid intensification"
        matches = search_keyword_in_discussions(storm_data, keyword)
        
        print(f"\n在 {storm_data['noaa_name']} 的讨论中搜索 '{keyword}'")
        print(f"找到 {len(matches)} 个匹配\n")
        
        for i, match in enumerate(matches[:3]):  # 只显示前3个
            print(f"匹配 {i+1}:")
            print(f"  文件: {match['filename']}")
            print(f"  时间: {match['timestamp']}")
            print(f"  相关句子: {match['relevant_sentences'][0][:100]}...")
            print()


def example_5_batch_query():
    """示例5：批量查询"""
    print("\n" + "="*60)
    print("示例5：批量查询2024年大西洋气旋")
    print("="*60)
    
    data = load_cyclone_data()
    storms = get_storms_by_year_and_basin(data, 2024, "Atlantic")
    
    print(f"\n2024年大西洋共有 {len(storms)} 个气旋:\n")
    
    for i, storm in enumerate(storms[:10]):  # 只显示前10个
        print(f"{i+1}. {storm['name']}")
        print(f"   开始: {storm['start_time'][:10]}")
        print(f"   预报数: {storm['num_forecasts']}, 讨论数: {storm['num_discussions']}")


def main():
    """运行所有示例"""
    example_1_basic_usage()
    example_2_forecast_summary()
    example_3_intensity_analysis()
    example_4_keyword_search()
    example_5_batch_query()
    
    print("\n" + "="*60)
    print("所有示例运行完成!")
    print("="*60)


if __name__ == '__main__':
    main()

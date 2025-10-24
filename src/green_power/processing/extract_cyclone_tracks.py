"""
提取匹配气旋的完整路径和强度数据
从IBTrACS数据中提取matched_cyclones.csv中所有气旋的时间序列数据
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict
from datetime import datetime


class CycloneTrackExtractor:
    """气旋路径数据提取器"""
    
    def __init__(self, ibtracs_path: str, matched_csv_path: str):
        """
        初始化提取器
        
        Args:
            ibtracs_path: IBTrACS CSV文件路径
            matched_csv_path: 匹配的气旋CSV文件路径
        """
        self.ibtracs_path = Path(ibtracs_path)
        self.matched_csv_path = Path(matched_csv_path)
        self.ibtracs_data = None
        self.matched_storms = None
        
    def load_data(self):
        """加载数据"""
        print(f"Loading IBTrACS data from {self.ibtracs_path}...")
        self.ibtracs_data = pd.read_csv(self.ibtracs_path)
        print(f"Loaded {len(self.ibtracs_data)} IBTrACS records")
        
        print(f"\nLoading matched storms from {self.matched_csv_path}...")
        self.matched_storms = pd.read_csv(self.matched_csv_path)
        print(f"Loaded {len(self.matched_storms)} matched storms")
        
    def extract_tracks(self, output_path: str):
        """
        提取匹配气旋的完整路径数据
        
        Args:
            output_path: 输出CSV文件路径
        """
        if self.ibtracs_data is None or self.matched_storms is None:
            self.load_data()
        
        print("\nExtracting track data for matched storms...")
        
        # 获取所有匹配气旋的SID列表
        matched_sids = set(self.matched_storms['ibtracs_sid'].unique())
        print(f"Found {len(matched_sids)} unique storm IDs")
        
        # 从IBTrACS中筛选这些气旋的所有记录
        track_data = self.ibtracs_data[
            self.ibtracs_data['sid'].isin(matched_sids)
        ].copy()
        
        print(f"Extracted {len(track_data)} track records")
        
        # 添加额外信息（从matched_storms合并）
        storm_info = self.matched_storms[[
            'ibtracs_sid', 'year', 'noaa_basin', 'noaa_name'
        ]].rename(columns={'ibtracs_sid': 'sid'})
        
        # 合并数据
        track_data = track_data.merge(
            storm_info,
            on='sid',
            how='left'
        )
        
        # 解析时间信息
        print("Parsing datetime information...")
        track_data['datetime'] = pd.to_datetime(track_data['iso_time'], errors='coerce')
        track_data['year'] = track_data['datetime'].dt.year
        track_data['month'] = track_data['datetime'].dt.month
        track_data['day'] = track_data['datetime'].dt.day
        track_data['hour'] = track_data['datetime'].dt.hour
        
        # 计算气旋移动速度和方向
        print("Calculating storm movement speed and direction...")
        track_data = self._calculate_storm_movement(track_data)
        
        # 重命名和选择列
        track_data_final = pd.DataFrame()
        track_data_final['storm_id'] = track_data['sid']
        track_data_final['storm_name'] = track_data['name']
        track_data_final['season'] = track_data['season']
        track_data_final['datetime'] = track_data['iso_time']
        track_data_final['year'] = track_data['year']
        track_data_final['month'] = track_data['month']
        track_data_final['day'] = track_data['day']
        track_data_final['hour'] = track_data['hour']
        track_data_final['latitude'] = track_data['lat']
        track_data_final['longitude'] = track_data['lon']
        track_data_final['max_wind_wmo'] = track_data['wmo_wind']
        track_data_final['min_pressure_wmo'] = track_data['wmo_pres']
        
        # USA数据在当前IBTrACS导出中不可用，设为NaN
        track_data_final['max_wind_usa'] = np.nan
        track_data_final['min_pressure_usa'] = np.nan
        
        # 添加计算的移动速度和方向
        track_data_final['storm_speed'] = track_data['storm_speed']
        track_data_final['storm_direction'] = track_data['storm_direction']
        
        # distance_to_land需要地理数据，暂时设为NaN
        track_data_final['distance_to_land'] = np.nan
        
        # 添加额外的辅助字段
        track_data_final['noaa_name'] = track_data['noaa_name']
        track_data_final['noaa_basin'] = track_data['noaa_basin']
        
        # 按storm_id和datetime排序
        track_data_final = track_data_final.sort_values(['storm_id', 'datetime'])
        
        # 保存到CSV
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        track_data_final.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\nSaved track data to {output_file}")
        
        # 打印统计信息
        self._print_statistics(track_data_final)
        
        return track_data_final
    
    def _calculate_storm_movement(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算气旋移动速度和方向
        
        Args:
            df: 包含位置和时间信息的DataFrame
            
        Returns:
            添加了storm_speed和storm_direction列的DataFrame
        """
        df = df.copy()
        df['storm_speed'] = np.nan
        df['storm_direction'] = np.nan
        
        # 按气旋分组计算
        for storm_id in df['sid'].unique():
            mask = df['sid'] == storm_id
            storm_data = df[mask].sort_values('datetime')
            
            if len(storm_data) < 2:
                continue
            
            speeds = []
            directions = []
            
            for i in range(len(storm_data)):
                if i == 0:
                    speeds.append(np.nan)
                    directions.append(np.nan)
                    continue
                
                # 获取前后两个点
                prev_idx = storm_data.index[i-1]
                curr_idx = storm_data.index[i]
                
                lat1 = storm_data.loc[prev_idx, 'lat']
                lon1 = storm_data.loc[prev_idx, 'lon']
                lat2 = storm_data.loc[curr_idx, 'lat']
                lon2 = storm_data.loc[curr_idx, 'lon']
                time1 = storm_data.loc[prev_idx, 'datetime']
                time2 = storm_data.loc[curr_idx, 'datetime']
                
                # 检查数据有效性
                if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
                    speeds.append(np.nan)
                    directions.append(np.nan)
                    continue
                
                if pd.isna(time1) or pd.isna(time2):
                    speeds.append(np.nan)
                    directions.append(np.nan)
                    continue
                
                # 计算距离（使用Haversine公式）
                distance_km = self._haversine_distance(lat1, lon1, lat2, lon2)
                
                # 计算时间差（小时）
                time_diff = (time2 - time1).total_seconds() / 3600.0
                
                if time_diff > 0:
                    # 速度（km/h）
                    speed = distance_km / time_diff
                    speeds.append(speed)
                    
                    # 方向（度，北为0度，顺时针）
                    direction = self._calculate_bearing(lat1, lon1, lat2, lon2)
                    directions.append(direction)
                else:
                    speeds.append(np.nan)
                    directions.append(np.nan)
            
            # 更新DataFrame
            df.loc[mask, 'storm_speed'] = speeds
            df.loc[mask, 'storm_direction'] = directions
        
        return df
    
    def _haversine_distance(self, lat1: float, lon1: float, 
                           lat2: float, lon2: float) -> float:
        """
        使用Haversine公式计算两点间的距离
        
        Args:
            lat1, lon1: 第一个点的纬度和经度（度）
            lat2, lon2: 第二个点的纬度和经度（度）
            
        Returns:
            距离（公里）
        """
        # 地球半径（公里）
        R = 6371.0
        
        # 转换为弧度
        lat1_rad = np.radians(lat1)
        lon1_rad = np.radians(lon1)
        lat2_rad = np.radians(lat2)
        lon2_rad = np.radians(lon2)
        
        # 差值
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine公式
        a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        distance = R * c
        return distance
    
    def _calculate_bearing(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """
        计算从点1到点2的方位角
        
        Args:
            lat1, lon1: 第一个点的纬度和经度（度）
            lat2, lon2: 第二个点的纬度和经度（度）
            
        Returns:
            方位角（度，北为0度，顺时针0-360）
        """
        # 转换为弧度
        lat1_rad = np.radians(lat1)
        lon1_rad = np.radians(lon1)
        lat2_rad = np.radians(lat2)
        lon2_rad = np.radians(lon2)
        
        # 计算方位角
        dlon = lon2_rad - lon1_rad
        
        x = np.sin(dlon) * np.cos(lat2_rad)
        y = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon)
        
        bearing_rad = np.arctan2(x, y)
        bearing_deg = np.degrees(bearing_rad)
        
        # 转换为0-360度
        bearing_deg = (bearing_deg + 360) % 360
        
        return bearing_deg
    
    def _print_statistics(self, track_data: pd.DataFrame):
        """打印统计信息"""
        print("\n" + "="*60)
        print("轨迹数据统计")
        print("="*60)
        
        print(f"\n总记录数: {len(track_data)}")
        print(f"唯一气旋数: {track_data['storm_id'].nunique()}")
        
        # 按年份统计
        print("\n按年份分布:")
        year_counts = track_data.groupby('year')['storm_id'].nunique().sort_index()
        for year, count in year_counts.items():
            if pd.notna(year):
                print(f"  {int(year)}: {count} 个气旋")
        
        # 按流域统计
        print("\n按流域分布:")
        basin_counts = track_data.groupby('noaa_basin')['storm_id'].nunique()
        for basin, count in basin_counts.items():
            if pd.notna(basin):
                print(f"  {basin}: {count} 个气旋")
        
        # 数据完整性统计
        print("\n数据完整性:")
        total_records = len(track_data)
        wind_wmo = track_data['max_wind_wmo'].notna().sum()
        pres_wmo = track_data['min_pressure_wmo'].notna().sum()
        speed_available = track_data['storm_speed'].notna().sum()
        direction_available = track_data['storm_direction'].notna().sum()
        
        print(f"  有WMO风速数据: {wind_wmo}/{total_records} ({wind_wmo/total_records*100:.1f}%)")
        print(f"  有WMO气压数据: {pres_wmo}/{total_records} ({pres_wmo/total_records*100:.1f}%)")
        print(f"  有移动速度数据: {speed_available}/{total_records} ({speed_available/total_records*100:.1f}%)")
        print(f"  有移动方向数据: {direction_available}/{total_records} ({direction_available/total_records*100:.1f}%)")
        
        # 风速和气压范围
        if wind_wmo > 0:
            print(f"\nWMO风速范围: {track_data['max_wind_wmo'].min():.1f} - {track_data['max_wind_wmo'].max():.1f} knots")
        
        if pres_wmo > 0:
            print(f"WMO气压范围: {track_data['min_pressure_wmo'].min():.1f} - {track_data['min_pressure_wmo'].max():.1f} mb")
        
        # 移动速度范围
        if speed_available > 0:
            speed_stats = track_data['storm_speed'].describe()
            print(f"\n气旋移动速度统计 (km/h):")
            print(f"  平均: {speed_stats['mean']:.1f}")
            print(f"  中位数: {speed_stats['50%']:.1f}")
            print(f"  最大: {speed_stats['max']:.1f}")
        
        # 示例数据
        print("\n示例数据（前5条记录）:")
        display_cols = ['storm_id', 'storm_name', 'datetime', 'latitude', 'longitude', 
                       'max_wind_wmo', 'min_pressure_wmo', 'storm_speed', 'storm_direction']
        print(track_data[display_cols].head().to_string(index=False))
        
        print("\n" + "="*60)


def main():
    """主函数"""
    # 配置路径
    ibtracs_path = 'cycloneTrack/ibtracs_master_index_1980-2025.csv'
    matched_csv_path = 'data/output/processed/matched_cyclones.csv'
    output_path = 'data/output/processed/matched_cyclone_tracks.csv'
    
    # 创建提取器
    extractor = CycloneTrackExtractor(ibtracs_path, matched_csv_path)
    
    # 提取轨迹数据
    track_data = extractor.extract_tracks(output_path)
    
    print("\n" + "="*60)
    print("处理完成!")
    print(f"输出文件: {output_path}")
    print(f"总记录数: {len(track_data)}")
    print("="*60)


if __name__ == '__main__':
    main()

# 气旋轨迹数据文件更新说明

## 更新日期
2025年10月21日

## 更新内容

根据用户需求，已更新 `matched_cyclone_tracks.csv` 文件结构，包含以下字段：

### 必需字段（已实现）

| 字段名 | 数据来源 | 状态 |
|--------|----------|------|
| storm_id | IBTrACS | ✅ 完整 |
| storm_name | IBTrACS | ✅ 完整 |
| season | IBTrACS | ✅ 完整 |
| datetime | IBTrACS | ✅ 完整 |
| year | 从datetime解析 | ✅ 完整 |
| month | 从datetime解析 | ✅ 完整 |
| day | 从datetime解析 | ✅ 完整 |
| hour | 从datetime解析 | ✅ 完整 |
| latitude | IBTrACS | ✅ 完整 |
| longitude | IBTrACS | ✅ 完整 |
| max_wind_wmo | IBTrACS | ⚠️ 49.9% 可用 |
| min_pressure_wmo | IBTrACS | ⚠️ 50.0% 可用 |
| max_wind_usa | 不可用 | ❌ 全部为NaN |
| min_pressure_usa | 不可用 | ❌ 全部为NaN |
| storm_speed | 计算得出 | ✅ 98.1% 可用 |
| storm_direction | 计算得出 | ✅ 98.1% 可用 |
| distance_to_land | 不可用 | ❌ 全部为NaN |

### 辅助字段（新增）

| 字段名 | 说明 |
|--------|------|
| noaa_name | NOAA气旋名称 |
| noaa_basin | NOAA流域分类 |

## 计算方法

### storm_speed（气旋移动速度）
- **方法**: Haversine公式
- **计算**: distance / time_interval
- **单位**: km/h
- **公式**:
  ```
  a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
  c = 2 × atan2(√a, √(1−a))
  distance = R × c  (R = 6371 km)
  speed = distance / Δt
  ```

### storm_direction（气旋移动方向）
- **方法**: 方位角计算
- **单位**: 度（0-360°）
- **参考**: 北为0°，顺时针
- **公式**:
  ```
  x = sin(Δlon) × cos(lat2)
  y = cos(lat1) × sin(lat2) - sin(lat1) × cos(lat2) × cos(Δlon)
  bearing = atan2(x, y)
  ```

## 数据统计

### 文件信息
- **文件大小**: 8.3 MB
- **总记录数**: 53,186 条
- **气旋数量**: 870 个
- **年份范围**: 1998-2025

### 数据完整性
- **时间位置**: 100% 完整
- **WMO风速/气压**: 约50% 可用（这是IBTrACS原始数据的特征）
- **移动速度/方向**: 98.1% 可用（第一个时间点无法计算）
- **USA数据**: 0%（当前IBTrACS导出不包含）
- **到陆地距离**: 0%（需要额外地理数据库）

### 速度统计
- **平均移动速度**: 19.3 km/h
- **中位数速度**: 17.7 km/h
- **最大速度**: 148.2 km/h
- **风速范围**: 10.0 - 185.0 knots

## 使用示例

### 快速加载
```python
import pandas as pd
df = pd.read_csv('data/output/processed/matched_cyclone_tracks.csv')
print(df.columns.tolist())
```

### 查询特定气旋
```python
beryl_2024 = df[(df['storm_name'] == 'BERYL') & (df['year'] == 2024)]
print(f"记录数: {len(beryl_2024)}")
print(beryl_2024[['datetime', 'latitude', 'longitude', 'max_wind_wmo', 
                  'storm_speed', 'storm_direction']].head())
```

### 分析移动特征
```python
# 筛选有速度数据的记录
with_speed = df[df['storm_speed'].notna()]

# 按方向分类（简化）
def classify_direction(deg):
    if pd.isna(deg):
        return 'Unknown'
    if 315 <= deg or deg < 45:
        return 'N'
    elif 45 <= deg < 135:
        return 'E'
    elif 135 <= deg < 225:
        return 'S'
    else:
        return 'W'

with_speed['direction_class'] = with_speed['storm_direction'].apply(classify_direction)
print(with_speed['direction_class'].value_counts())
```

## 限制说明

### 1. USA数据不可用
- **原因**: 当前IBTrACS导出文件只包含基本的WMO数据
- **解决方案**: 需要使用完整版IBTrACS数据库（包含多机构数据）
- **影响**: max_wind_usa 和 min_pressure_usa 字段全部为 NaN

### 2. 到陆地距离未计算
- **原因**: 需要额外的地理边界数据库（如Natural Earth, GSHHG）
- **解决方案**: 可以使用 geopandas 和海岸线数据计算
- **影响**: distance_to_land 字段全部为 NaN

### 3. WMO数据部分缺失
- **原因**: 
  - 早期历史数据可能不完整
  - 某些观测时间点没有测量
  - 数据质量控制移除了不可靠数据
- **影响**: 约50%的记录有风速和气压数据
- **建议**: 在分析前先筛选非空值

## 文件路径

- **输出文件**: `data/output/processed/matched_cyclone_tracks.csv`
- **生成脚本**: `src/green_power/processing/extract_cyclone_tracks.py`
- **详细文档**: `README_CYCLONE_TRACKS.md`

## 重新生成

如需重新生成此文件：

```bash
cd /root/projectResearch
python -m green_power.processing.extract_cyclone_tracks
```

## 相关文件

1. **matched_cyclones.csv** - 气旋概要列表
2. **matched_cyclone_tracks.csv** - 完整轨迹时间序列（本文件）
3. **cyclone_forecasts.json** - NOAA预报和讨论文本

---

**更新时间**: 2025年10月21日  
**脚本版本**: 2.0（添加计算字段和时间解析）  
**数据版本**: IBTrACS 1980-2025

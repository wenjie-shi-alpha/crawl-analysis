# NOAA飓风数据爬虫使用指南

## 概述

这个项目提供一个交互式脚本，用于从NOAA（美国国家飓风中心）批量获取完整的飓风预报数据。同时，`crawling.noaa_crawler` 模块还暴露了按需下载档案索引与单页预报文本的工具类。

## 脚本说明

### `src/crawl_all_years.py` - 完整数据爬虫 ⭐ **推荐使用**
系统化下载每年所有气旋的完整预报数据。

**功能：**
- 自动识别每年的所有气旋
- 下载4种类型的预报数据：
  - Forecast Advisory（预报公告）
  - Public Advisory（公众公告）
  - Forecast Discussion（预报讨论）
  - Wind Speed Probabilities（风速概率）
- 按照规范的目录结构存储
- 自动跳过已下载的文件
- 显示下载进度和统计

**运行：**
```bash
python3 -m green_power.crawl_all_years
```

**交互式选项：**
1. 爬取单个年份 - 输入年份（如2023）
2. 爬取多个年份 - 输入逗号分隔的年份（如2021,2022,2023）
3. 爬取2021-2023年 - 自动爬取最近三年
4. 爬取2023年（测试） - 快速测试
5. 查看已下载数据 - 显示目录结构

## 目录结构

下载的数据按以下结构组织：

```
data/output/raw/noaa_complete/
├── 2021/
│   ├── ADRIAN/
│   │   ├── forecast_advisory/
│   │   │   ├── ep012021.fstadv.001.txt
│   │   │   ├── ep012021.fstadv.002.txt
│   │   │   └── ...
│   │   ├── public_advisory/
│   │   │   ├── ep012021.public.001.txt
│   │   │   └── ...
│   │   ├── forecast_discussion/
│   │   │   ├── ep012021.discus.001.txt
│   │   │   └── ...
│   │   └── wind_speed_probabilities/
│   │       ├── ep012021.wndprb.001.txt
│   │       └── ...
│   ├── BEATRIZ/
│   └── ...
├── 2022/
└── 2023/
    ├── ARLENE/
    ├── BRET/
    └── ...
```

## 数据类型说明

| 类型 | 短代码 | 目录名 | 说明 |
|------|--------|--------|------|
| Forecast Advisory | fstadv | forecast_advisory | 预报公告，包含技术细节 |
| Public Advisory | public | public_advisory | 公众预报，易于理解的格式 |
| Forecast Discussion | discus | forecast_discussion | 预报分析讨论 |
| Wind Speed Probabilities | wndprb | wind_speed_probabilities | 风速概率预测 |

## 示例用法

### 快速开始 - 下载2023年所有数据
```bash
python3 -m green_power.crawl_all_years
# 选择 1，然后输入 2023
```

### 批量下载多年数据
```bash
python3 -m green_power.crawl_all_years
# 选择 2，然后输入 2020,2021,2022,2023
```

### 查看已下载内容
```bash
python3 -m green_power.crawl_all_years
# 选择 5
```

### 编程方式使用
```python
from green_power.crawling import (
    NOAAArchiveCrawler,
    NOAACompleteCrawler,
    NOAAForecastExtractor,
)

# 创建爬虫实例
crawler = NOAACompleteCrawler(output_dir="my_data")

# 爬取单个年份
crawler.crawl_year(2023)

# 爬取多个年份
crawler.crawl_years([2021, 2022, 2023])

# 查看统计
print(crawler.stats)

# 其他工具
archive_crawler = NOAAArchiveCrawler()
forecast_extractor = NOAAForecastExtractor()
```

## 依赖要求

```bash
pip install requests beautifulsoup4
```

或使用项目的requirements.txt：
```bash
pip install -r requirements.txt
```

## 注意事项

1. **请求频率**：脚本已设置0.3秒的请求间隔，避免对服务器造成过大压力
2. **断点续传**：脚本会自动跳过已下载的文件，可以随时中断后继续
3. **网络稳定性**：建议在稳定的网络环境下运行
4. **存储空间**：每年的数据大约需要几十MB空间
5. **数据完整性**：某些气旋可能缺少某种类型的预报数据

## 数据来源

- 网站：https://www.nhc.noaa.gov/archive/
- 数据提供方：NOAA National Hurricane Center
- 数据格式：纯文本（从HTML的`<pre>`标签中提取）

## 故障排除

### 问题：无法找到气旋
- 确保年份输入正确
- 检查网络连接
- 某些年份可能没有气旋数据

### 问题：提取的文本为空
- 某些预报类型可能不可用
- 检查原始HTML文件（如果保存了）

### 问题：下载速度慢
- 这是正常的，脚本有延时保护
- 可以调整`time.sleep()`的值（不建议太小）

## 许可与使用

NOAA的数据是公开的，可以自由使用。请遵守NOAA的使用条款和合理使用原则。

## 更新日志

- 2023-10: 初始版本
  - 支持4种预报类型
  - 自动目录组织
  - 断点续传功能

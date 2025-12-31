# IEM NWS Text Product Archive 爬虫

## 简介

这是一个用于从Iowa Environmental Mesonet (IEM) 的NWS Text Product Archive获取国家气象局(NWS)文本产品的爬虫。

**数据源**: https://mesonet.agron.iastate.edu/wx/afos/list.phtml

## 功能特性

- ✅ 支持按产品ID（PIL）搜索和下载
- ✅ 支持按日期范围批量下载
- ✅ 支持指定WFO中心过滤
- ✅ 支持多种产品类型同时下载
- ✅ 自动解析产品元数据
- ✅ 智能错误处理和重试
- ✅ 完整的下载统计信息

## 支持的产品类型

爬虫支持所有NWS文本产品，常用的包括：

| 产品代码 | 产品名称 | 说明 |
|---------|---------|------|
| **MCD** | Mesoscale Convective Discussion | **中尺度对流讨论** - SPC发布的关于对流天气系统发展的分析和预测 |
| AFD | Area Forecast Discussion | 区域预报讨论 - WFO发布的详细天气预报分析 |
| SWO | Severe Storm Outlook Narrative | 强对流天气展望 |
| HWO | Hazardous Weather Outlook | 危险天气展望 |
| WOU | Tornado/Severe Thunderstorm Watch | 龙卷风/强雷暴监视 |
| TOR | Tornado Warning | 龙卷风警告 |
| SVR | Severe Thunderstorm Warning | 强雷暴警告 |
| FFW | Flash Flood Warning | 山洪暴发警告 |
| LSR | Local Storm Report | 本地风暴报告 |
| NOW | Short Term Forecast | 短期预报 |
| TAF | Terminal Aerodrome Forecast | 机场终端预报 |

更多产品类型请参考：https://forecast.weather.gov/product_types.php?site=NWS

## 安装依赖

```bash
pip install requests beautifulsoup4
```

或使用项目的requirements.txt：

```bash
pip install -r requirements.txt
```

## 使用方法

### 方法1: 直接运行爬虫脚本

```bash
python -m green_power.crawling.iem_crawler
```

然后按照交互式提示选择操作。

### 方法2: 使用测试脚本

```bash
python examples/iem_usage.py
```

### 方法3: 在代码中使用

#### 示例1: 爬取MCD产品

```python
from datetime import datetime, timedelta
from green_power.crawling.iem_crawler import IEMTextProductCrawler

# 创建爬虫实例
crawler = IEMTextProductCrawler(
    output_dir="data/output/raw/iem_products"
)

# 设置日期范围（最近7天）
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

# 爬取MCD产品
crawler.crawl_products_by_date_range(
    pil='MCD',
    start_date=start_date,
    end_date=end_date,
)
```

#### 示例2: 爬取特定中心的AFD产品

```python
from datetime import datetime, timedelta
from green_power.crawling.iem_crawler import IEMTextProductCrawler

crawler = IEMTextProductCrawler()

# 爬取Des Moines中心的AFD产品
crawler.crawl_products_by_date_range(
    pil='AFD',
    start_date=datetime(2024, 10, 1),
    end_date=datetime(2024, 10, 7),
    center='DMX',  # Des Moines
)
```

#### 示例3: 批量爬取多种产品

```python
from datetime import datetime, timedelta
from green_power.crawling.iem_crawler import IEMTextProductCrawler

crawler = IEMTextProductCrawler()

# 爬取多种产品类型
crawler.crawl_multiple_products(
    pils=['MCD', 'AFD', 'HWO', 'SWO'],
    start_date=datetime(2024, 10, 1),
    end_date=datetime(2024, 10, 7),
)
```

#### 示例4: 查看可用产品类型

```python
from green_power.crawling.iem_crawler import IEMTextProductCrawler

crawler = IEMTextProductCrawler()
products = crawler.list_available_products()
```

#### 示例5: 查看已下载数据

```python
from green_power.crawling.iem_crawler import IEMTextProductCrawler

crawler = IEMTextProductCrawler()
crawler.list_downloaded_data()
```

## 数据输出格式

### 目录结构

```
data/output/raw/iem_products/
├── MCD/                          # 产品类型
│   ├── 202410200353_KDMX_MCD0001.txt
│   ├── 202410200756_KDMX_MCD0002.txt
│   └── ...
├── AFD/
│   ├── DMX/                      # WFO中心（如果指定）
│   │   ├── 202410200353_KDMX_AFDDMX.txt
│   │   └── ...
│   └── OUN/
│       └── ...
└── ...
```

### 文件格式

每个产品文件包含：

```
Product ID: YYYYMMDDHHMI-KXXX-CCCCCC-PILXXX
Retrieved: YYYY-MM-DDTHH:MM:SS
URL: https://mesonet.agron.iastate.edu/p.php?pid=...
======================================================================

[产品文本内容]
```

## API接口说明

### IEMTextProductCrawler

主要的爬虫类。

#### 初始化参数

```python
crawler = IEMTextProductCrawler(
    base_url="https://mesonet.agron.iastate.edu",  # IEM基础URL
    output_dir="data/output/raw/iem_products",     # 输出目录
)
```

#### 主要方法

##### 1. `crawl_products_by_date_range()`

按日期范围爬取产品。

```python
crawler.crawl_products_by_date_range(
    pil='MCD',                    # 产品标识符（必需）
    start_date=datetime(...),     # 开始日期（必需）
    end_date=datetime(...),       # 结束日期（必需）
    center='DMX',                 # WFO中心代码（可选）
    max_days_per_request=7,       # 每次请求的最大天数
)
```

##### 2. `crawl_multiple_products()`

批量爬取多种产品类型。

```python
crawler.crawl_multiple_products(
    pils=['MCD', 'AFD', 'HWO'],  # 产品标识符列表（必需）
    start_date=datetime(...),     # 开始日期（必需）
    end_date=datetime(...),       # 结束日期（必需）
    center='DMX',                 # WFO中心代码（可选）
)
```

##### 3. `search_products_by_pil()`

搜索产品但不下载。

```python
products = crawler.search_products_by_pil(
    pil='MCD',                    # 产品标识符（必需）
    start_date=datetime(...),     # 开始日期（必需）
    end_date=datetime(...),       # 结束日期（可选）
    center='DMX',                 # WFO中心代码（可选）
)
```

返回值：包含产品信息的字典列表。

##### 4. `fetch_product_content()`

获取单个产品的内容。

```python
content = crawler.fetch_product_content(
    pid='202410200353-KDMX-FXUS63-AFDDMX'  # 产品ID
)
```

##### 5. `list_available_products()`

列出可用的产品类型。

```python
products = crawler.list_available_products()
```

##### 6. `list_downloaded_data()`

列出已下载的数据统计。

```python
crawler.list_downloaded_data()
```

## 常用WFO中心代码

| 代码 | 中心名称 |
|-----|---------|
| DMX | Des Moines, IA |
| OUN | Norman, OK |
| OAX | Omaha/Valley, NE |
| TOP | Topeka, KS |
| ICT | Wichita, KS |
| DDC | Dodge City, KS |
| GLD | Goodland, KS |
| LBF | North Platte, NE |
| GID | Hastings, NE |

完整列表请访问：https://www.weather.gov/srh/nwsoffices

## 注意事项

1. **日期范围限制**: IEM建议每次请求不超过10天，爬虫默认设置为7天
2. **请求频率**: 爬虫内置了延迟（0.5秒/产品），避免过载服务器
3. **数据完整性**: 
   - 1983-2001年: 数据可能不完整
   - 2002-2007年: 较好的覆盖
   - 2008年至今: 非常好的数据覆盖
4. **存储空间**: 根据产品类型和日期范围，可能需要大量存储空间

## IEM API文档

IEM提供了RESTful API接口：

- API文档: https://mesonet.agron.iastate.edu/api/1/docs
- 产品列表API: `/api/1/nws/afos/list.json`
- 单个产品API: `/p.php?pid=<product_id>`

爬虫优先使用API接口，如果API失败则回退到网页爬取模式。

## 关于Model Diagnostic Discussion (MCD)

MCD是Storm Prediction Center (SPC)发布的关于中尺度对流系统发展的专业分析和预测产品，包含：

- 对流发展的物理机制分析
- 当前天气系统的诊断
- 未来几小时的演变预测
- 可能的强对流天气威胁

这些产品对于理解和预测强对流天气（如龙卷风、冰雹、大风等）非常重要。

## 故障排除

### 问题1: API请求失败

如果API请求失败，爬虫会自动切换到网页爬取模式。检查网络连接和IEM服务器状态。

### 问题2: 找不到产品

- 确认产品代码正确（3字母代码，大小写不敏感）
- 确认日期范围内该产品确实存在
- 某些产品可能只在特定时期或特定中心发布

### 问题3: 下载速度慢

这是正常的，爬虫设置了延迟以避免过载服务器。可以调整但不建议过快。

## 相关资源

- IEM主页: https://mesonet.agron.iastate.edu/
- IEM产品归档: https://mesonet.agron.iastate.edu/wx/afos/list.phtml
- NWS产品类型: https://forecast.weather.gov/product_types.php?site=NWS
- SPC主页: https://www.spc.noaa.gov/

## 许可证

本爬虫遵循项目的许可证。数据版权归National Weather Service所有。

## 贡献

欢迎提交问题和改进建议！

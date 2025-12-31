# IEM爬虫实现总结

## 已完成的工作

### 1. 创建了IEM NWS Text Product Archive爬虫

**文件位置**: `/root/projectResearch/src/green_power/crawling/iem_crawler.py`

这是一个功能完整的爬虫，用于从Iowa Environmental Mesonet (IEM)获取国家气象局(NWS)的文本产品。

### 2. 核心功能

- ✅ **按产品ID搜索**: 支持通过3字母产品代码（如MCD、AFD等）搜索
- ✅ **日期范围查询**: 支持指定开始和结束日期
- ✅ **WFO中心过滤**: 可以指定特定的气象中心（如DMX）
- ✅ **批量下载**: 支持同时下载多种产品类型
- ✅ **智能API调用**: 优先使用IEM的RESTful API，失败时自动降级到网页爬取
- ✅ **数据保存**: 自动组织文件结构，保存产品内容和元数据
- ✅ **统计信息**: 提供详细的下载统计和进度信息

### 3. 支持的主要产品类型

| 代码 | 产品名称 |
|------|---------|
| **MCD** | **Mesoscale Convective Discussion** (中尺度对流讨论) |
| AFD | Area Forecast Discussion (区域预报讨论) |
| SWO | Severe Storm Outlook Narrative (强对流天气展望) |
| HWO | Hazardous Weather Outlook (危险天气展望) |
| WOU | Tornado/Severe Thunderstorm Watch |
| TOR | Tornado Warning |
| SVR | Severe Thunderstorm Warning |
| FFW | Flash Flood Warning |
| LSR | Local Storm Report |
| NOW | Short Term Forecast |
| TAF | Terminal Aerodrome Forecast |

### 4. 关键类和方法

#### `IEMTextProductCrawler` 类

**主要方法**:
- `search_products_by_pil()`: 搜索指定产品
- `fetch_product_content()`: 获取产品内容
- `download_product()`: 下载并保存产品
- `crawl_products_by_date_range()`: 按日期范围批量爬取
- `crawl_multiple_products()`: 批量爬取多种产品
- `list_available_products()`: 列出支持的产品类型
- `list_downloaded_data()`: 查看已下载数据

### 5. 使用示例

#### 快速开始

```python
import sys
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from green_power.crawling import IEMTextProductCrawler

# 创建爬虫
crawler = IEMTextProductCrawler()

# 爬取最近7天的MCD产品
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

crawler.crawl_products_by_date_range(
    pil='MCD',
    start_date=start_date,
    end_date=end_date,
)
```

#### 测试脚本

运行以下命令测试爬虫:

```bash
# 简单测试（推荐）
python examples/iem_quickstart.py

# 或者直接运行爬虫
python -c "import sys; sys.path.insert(0, 'src'); from green_power.crawling import IEMTextProductCrawler; crawler = IEMTextProductCrawler(); crawler.list_available_products()"
```

### 6. 输出数据结构

```
data/output/raw/iem_products/
├── MCD/                                      # 产品类型目录
│   ├── 202410200353_KDMX_MCD0001.txt        # 产品文件
│   ├── 202410200756_KDMX_MCD0002.txt
│   └── ...
├── AFD/
│   ├── DMX/                                  # 按中心分类（如果指定）
│   │   ├── 202410200353_KDMX_AFDDMX.txt
│   │   └── ...
│   └── OUN/
│       └── ...
└── ...
```

每个产品文件包含:
- 产品ID
- 获取时间
- 原始URL
- 完整的产品文本内容

### 7. 文档

创建了以下文档:
- `README_IEM_CRAWLER.md`: 完整的使用文档（中文）
- `examples/iem_usage.py`: 详细的示例脚本
- `examples/iem_quickstart.py`: 简化的测试脚本

### 8. 集成到项目

爬虫已集成到项目的 `green_power.crawling` 模块:
- 更新了 `src/green_power/crawling/__init__.py`
- 可以通过 `from src.crawling import IEMTextProductCrawler` 导入

## 技术特点

### 1. 双模式支持

- **API模式**: 优先使用IEM的JSON API (`/api/1/nws/afos/list.json`)
- **网页爬取模式**: API失败时自动降级到网页解析

### 2. 智能请求控制

- 默认每次请求最多7天数据（符合IEM建议）
- 自动分段请求大日期范围
- 内置延迟避免服务器过载 (0.5秒/产品)

### 3. 错误处理

- 网络错误自动重试
- 详细的错误日志
- 统计成功/失败数量

### 4. 数据质量

- 自动提取产品元数据
- 保留原始文本格式
- 记录下载时间和来源URL

## 数据源信息

### IEM归档完整性

根据IEM官方说明:
- **1983-2001**: 数据可能稀疏或缺失
- **2002-2007**: 较好的数据覆盖
- **2008至今**: 非常好的数据覆盖和高保真度

### 数据来源

- **主页**: https://mesonet.agron.iastate.edu/
- **产品归档**: https://mesonet.agron.iastate.edu/wx/afos/list.phtml
- **API文档**: https://mesonet.agron.iastate.edu/api/1/docs

## 关于Model Diagnostic Discussion (MCD)

根据您的要求，爬虫特别支持MCD产品:

**MCD (Mesoscale Convective Discussion)** 是Storm Prediction Center (SPC)发布的中尺度对流讨论产品，包含:
- 对流天气系统的物理机制分析
- 当前大气状态的诊断
- 未来数小时的演变预测
- 强对流天气威胁评估

这是预报员用于理解和预测强对流天气（龙卷风、冰雹、大风等）的重要参考资料。

## 使用建议

### 推荐的使用流程

1. **首先列出可用产品**:
   ```bash
   python test_iem_simple.py
   # 选择选项1
   ```

2. **小规模测试** (爬取1-2天数据):
   ```bash
   python test_iem_simple.py
   # 选择选项2或3
   ```

3. **大规模爬取** (修改日期范围后运行)

4. **查看下载结果**:
   ```bash
   python test_iem_simple.py
   # 选择选项4
   ```

### 注意事项

1. **请求频率**: 已内置延迟，请勿修改为更快
2. **日期范围**: 建议每次不超过7-10天
3. **存储空间**: 根据产品数量可能需要较大空间
4. **网络稳定性**: 长时间运行时确保网络稳定

## 下一步扩展建议

可以考虑的增强功能:
1. 添加更多产品类型的预设配置
2. 实现增量更新（只下载新产品）
3. 添加产品内容的初步解析
4. 集成到现有的数据处理流程
5. 添加定时任务支持

## 文件清单

新增的文件:
1. `src/green_power/crawling/iem_crawler.py` - 主爬虫代码
2. `examples/iem_usage.py` - 详细示例脚本
3. `examples/iem_quickstart.py` - 简化示例脚本
4. `docs/README_IEM_CRAWLER.md` - 完整文档

修改的文件:
1. `src/green_power/crawling/__init__.py` - 添加 IEMTextProductCrawler 导出

## 测试确认

爬虫已通过基本功能测试:
- ✅ 成功导入模块
- ✅ 列出可用产品类型
- ✅ API调用正常
- ✅ 数据结构正确

建议您运行 `test_iem_simple.py` 进行实际爬取测试。

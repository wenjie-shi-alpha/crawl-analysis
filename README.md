# 综合网络信息爬取与分析工具集

该项目构建了一条通用的"网络检索 → 文本处理 → LLM 分析 → 报告输出"数据处理流水线，适用于多领域信息追踪与分析。核心能力包括多源自动化爬取、批量数据清洗、调用 OpenAI 兼容模型完成深度分析，并输出图表/报告以辅助决策。项目已集成气象数据（NOAA、IEM）、网络搜索（Tavily）、特定行业数据源等多种爬虫，并可轻松扩展至新的数据源和应用场景。

## 功能特性
- **多源网络爬取**：集成 Tavily 通用搜索、NOAA 气象数据、IEM 天气产品、TheWindPower 风电场信息等多种爬虫，支持关键词批量检索与结构化存档，可扩展至任意网络数据源。
- **多语言文本预处理**：支持中文和英文的去重、分词、关键词提取等加工流程，提供标准化的数据输入接口。
- **LLM 驱动智能分析**：调用 OpenAI 兼容模型（如 `gpt-4o-mini`）进行深度文本挖掘、模式识别、因素提取，并生成结构化分析结果。
- **数据匹配与关联**：内置气旋轨迹匹配、时空数据关联等算法，支持跨数据源的智能关联分析。
- **结果可视化与报告**：自动生成对比图表、桑基图、词云等可视化，输出 Markdown/JSON 格式报告。
- **模块化流水线架构**：通过命令行灵活控制 `crawl`、`preprocess`、`analyze`、`report` 等独立步骤，支持自定义扩展。
- **丰富示例与文档**：`examples/` 提供即用脚本，`docs/` 收录详细的爬虫使用说明与技术文档。

## 项目结构
```
projectResearch/
├── data/                         # 默认数据工作区（运行后生成）
│   ├── output/                   # 处理结果输出
│   │   ├── raw/                  # 原始爬取数据
│   │   ├── processed/            # 清洗后的结构化数据
│   │   ├── analysis/             # LLM 分析结果
│   │   ├── final/                # 最终报告与图表
│   │   └── meta/                 # 元数据与配置快照
├── cycloneTrack/                 # 气旋轨迹数据（IBTrACS）
├── docs/                         # 技术文档与使用说明
│   ├── README_IEM_CRAWLER.md
│   ├── README_NOAA_CRAWLER.md
│   └── CYCLONE_MATCHER_SUMMARY.md
├── examples/                     # 功能演示脚本
│   ├── cyclone_data_usage.py     # 气旋数据处理示例
│   ├── iem_quickstart.py         # IEM 爬虫快速入门
│   ├── iem_usage.py              # IEM 高级用法
│   ├── noaa_basin_demo.py        # NOAA 数据查询演示
│   └── quickchart_sankey.py      # 可视化图表生成
├── src/
│   └── green_power/              # 核心代码包
│       ├── analysis/             # LLM 文本分析模块
│       ├── crawling/             # 多源爬虫实现
│       │   ├── tavily_crawler.py       # 通用搜索
│       │   ├── noaa_crawler.py         # 气象数据
│       │   ├── iem_crawler.py          # 天气产品
│       │   └── thewindpower_browser.py # 风电场信息
│       ├── processing/           # 数据处理与匹配
│       │   ├── text_preprocessor.py
│       │   ├── cyclone_matcher.py
│       │   └── cyclone_query.py
│       ├── reporting/            # 报告生成与可视化
│       ├── utils/                # 通用工具函数
│       ├── cli.py                # 命令行接口
│       ├── config.py             # 配置管理
│       ├── pipeline.py           # 流水线编排逻辑
│       └── crawl_all_years.py    # 批量数据抓取
├── main.py                       # 主入口文件
├── pyproject.toml                # Python 项目配置
├── requirements.txt              # 依赖包列表
└── README.md                     # 项目说明文档
```

## 环境准备
1. **创建虚拟环境并安装依赖**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   或使用可编辑安装：
   ```bash
   pip install -e .[dev]
   ```

2. **配置 API 密钥**  
   根据使用的数据源配置相应的 API 密钥：
   
   - **Tavily 搜索 API**（用于通用网络检索）：
     ```bash
     export TAVILY_API_KEY="your_api_key"    # Windows 使用 set / $Env:
     ```
   
   - **OpenAI 兼容模型**（用于 LLM 分析）：
     ```bash
     export OPENAI_API_KEY="sk-your-key"
     export OPENAI_MODEL="gpt-4o-mini"
     export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选，支持兼容服务
     ```
   
   也可在项目根目录创建 `.env` 文件统一管理配置：
   ```bash
   TAVILY_API_KEY=your_tavily_key
   OPENAI_API_KEY=sk-your-key
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_BASE_URL=https://api.openai.com/v1
   OPENAI_ORG=your-org-id                        # 可选
   OPENAI_PROJECT=your-project-id                # 可选
   ```

## 命令行使用
安装为可执行脚本后，可直接调用 `green-power-analysis`；或在仓库根目录运行 `python main.py`。

- **运行完整流程**
  ```bash
  python main.py --full
  # 或
  green-power-analysis --full
  ```

- **执行单独阶段**
  ```bash
  python main.py --step crawl
  python main.py --step preprocess
  python main.py --step analyze
  python main.py --step report
  ```

- **查看数据目录状态**
  ```bash
  python main.py --status
  ```

- **常用参数**
  - `--dir`：自定义数据工作目录（默认 `data`）
  - `--keywords`：覆盖默认关键词列表
  - `--openai-model` / `--openai-base-url` / `--openai-api-key`：临时指定 LLM 相关配置
  - `--tavily-depth`：搜索深度（`basic` 或 `advanced`）
  - `--tavily-max`：每个关键词最大返回条数

## 运行结果
完整流程结束后，数据目录会生成如下结构：
```
data/
└── output/
    ├── raw/             # 原始检索结果
    ├── processed/       # 预处理后的结构化文本
    ├── analysis/        # LLM 分析输出（JSON/Markdown）
    ├── final/
    │   ├── charts/      # 可视化图表
    │   └── reports/     # 汇总报告
    └── meta/            # 配置快照等元信息
```

## 示例脚本
`examples/` 目录提供多种数据源的使用示例：

### 气象数据爬取
- `iem_quickstart.py`：快速入门 IEM（Iowa Environmental Mesonet）文本产品抓取
- `iem_usage.py`：展示 IEM 爬虫的多种抓取方式与参数配置
- `noaa_basin_demo.py`：查询 NOAA 气旋数据并演示分盆地分类处理

### 数据处理与分析
- `cyclone_data_usage.py`：气旋轨迹数据的读取、过滤与处理示例
- `quickchart_sankey.py`：使用 QuickChart API 生成桑基图（Sankey Diagram）

**运行提示**：所有示例需要在安装项目包后运行（`pip install -e .`），或在脚本开头添加 `sys.path.insert(0, "src")` 以导入 `green_power` 模块。

## 技术文档
`docs/` 目录包含详细的技术文档与研究记录：
- `README_IEM_CRAWLER.md`：IEM 文本产品爬虫完整使用指南
- `README_NOAA_CRAWLER.md`：NOAA 气象数据抓取接口说明
- `CYCLONE_MATCHER_SUMMARY.md`：气旋轨迹匹配算法与实现细节
- `CYCLONE_TRACKS_UPDATE.md`：气旋轨迹数据更新与维护指南
- `IEM_CRAWLER_SUMMARY.md`：IEM 爬虫设计总结

这些文档为不同数据源的集成提供了详细的技术参考，有助于扩展新的爬虫模块。

## 应用场景
该工具集适用于多种信息分析场景：
- **气象研究**：气旋轨迹分析、天气产品数据挖掘
- **行业研究**：可再生能源、电力市场等垂直领域信息追踪
- **舆情监测**：多源网络信息的自动化采集与分析
- **数据科学**：构建定制化的数据处理与分析流水线
- **知识挖掘**：基于 LLM 的文本深度分析与知识提取

## 开发指南
- **项目结构**：遵循 `src` 布局，建议使用 `pip install -e .` 进行开发安装
- **流水线扩展**：核心逻辑封装于 `green_power.pipeline.GreenPowerPipeline`，可继承或扩展
- **添加新爬虫**：在 `src/green_power/crawling/` 下实现新的爬虫类，参考现有爬虫接口
- **文本处理**：支持中英文处理，中文依赖 `jieba` 与 `pypinyin`，可通过 `TextPreprocessor` 自定义
- **数据匹配算法**：参考 `cyclone_matcher.py` 实现自定义的数据关联逻辑
- **代码规范**：使用 `black` 进行代码格式化（配置见 `pyproject.toml`）

## 许可证
MIT License

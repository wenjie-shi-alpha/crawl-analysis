# 中国绿色电力信息爬取与分析工具集

该项目围绕“网络检索 → 文本处理 → LLM 分析 → 报告输出”构建一条可复用的数据处理流水线，用于追踪绿色电力与可再生能源相关的政策、舆情与研究动态。核心能力包括自动化爬取、批量清洗、调用 OpenAI 兼容模型完成深度分析，并输出图表/报告以辅助决策。

## 功能特性
- **多源网络爬取**：内置 Tavily 搜索、NOAA 气旋数据、IEM 文本产品等爬虫，支持关键词批量检索与结构化存档。
- **中文文本预处理**：去重、分词、关键词提取等加工流程，为上游分析提供稳定输入。
- **OpenAI 驱动分析**：调用 `gpt-4o-mini` 等模型识别驱动与障碍因素、行为模式，并生成综合报告。
- **结果可视化**：自动绘制因素对比、词云等图表，并输出 Markdown/JSON 报告。
- **模块化流水线**：可通过命令行选择执行 `crawl`、`preprocess`、`analyze`、`report` 等独立步骤。
- **示例与文档完善**：`examples/` 提供脚本演示，`docs/` 收录各爬虫说明与研究笔记。

## 项目结构
```
projectResearch/
├── data/                         # 默认数据工作区（运行后生成）
├── docs/                         # 研究文档与爬虫说明
├── examples/                     # 交互式示例脚本
│   ├── cyclone_data_usage.py
│   ├── iem_quickstart.py
│   ├── iem_usage.py
│   ├── noaa_basin_demo.py
│   └── quickchart_sankey.py
├── src/
│   └── green_power/
│       ├── analysis/             # LLM 分析实现
│       ├── crawling/             # 各类爬虫
│       ├── processing/           # 数据清洗与匹配
│       ├── reporting/            # 图表与报告生成
│       ├── utils/                # IO 等公共工具
│       ├── cli.py                # 命令行入口
│       ├── config.py             # 配置管理
│       ├── pipeline.py           # 流水线编排
│       └── crawl_all_years.py    # NOAA 批量抓取脚本
├── main.py                       # 便捷入口（自动添加 src 到路径）
├── pyproject.toml                # 打包与依赖声明
├── requirements.txt              # 运行时依赖列表
├── package.json / package-lock.json
└── README.md
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

2. **配置 Tavily API**  
   Tavily 检索依赖官方 REST 接口，在运行前设置密钥：
   ```bash
   export TAVILY_API_KEY="your_api_key"    # Windows 使用 set / $Env:
   ```

3. **配置 OpenAI 兼容模型**  
   生成分析报告需要 OpenAI API Key，可在根目录创建 `.env` 或直接设置环境变量：
   ```bash
   OPENAI_API_KEY=sk-your-key
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_BASE_URL=https://api.openai.com/v1      # 可选，兼容服务地址
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
`examples/` 目录提供与在线服务交互的脚本示例：
- `iem_quickstart.py`：快速体验 IEM 文本产品抓取。
- `iem_usage.py`：展示多种 IEM 抓取方式与参数。
- `noaa_basin_demo.py`：查询 NOAA 气旋信息并演示分盆地分类。
- `cyclone_data_usage.py`：处理气旋轨迹数据的示例。
- `quickchart_sankey.py`：生成 QuickChart Sankey 图 URL 的工具。

所有示例在运行前都需执行 `sys.path.insert(0, "src")` 或安装为包后直接导入 `green_power`。

## 其他文档
仓库内的更多调研笔记、特定爬虫说明详见 `docs/`：
- `README_IEM_CRAWLER.md`：IEM 文本产品爬虫使用说明。
- `README_NOAA_CRAWLER.md`：NOAA 气象数据抓取指南。
- `CYCLONE_MATCHER_SUMMARY.md` 等：气旋匹配、轨迹处理研究记录。

## 开发提示
- 项目遵循 `src` 布局，建议以 `pip install -e .` 进行开发安装。
- 核心流水线封装于 `green_power.pipeline.GreenPowerPipeline`，可按需继承或扩展。
- 文本预处理依赖 `jieba` 与 `pypinyin`，如需自定义词典可修改 `TextPreprocessor`。
- 代码格式化可使用 `black`（配置见 `pyproject.toml`）。

## 许可证
MIT License

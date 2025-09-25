# 中国绿色电力消费驱动机制与障碍分析系统

该项目重构为标准 Python 包结构，围绕“数据检索 → 文本预处理 → 本地 LLM 挖掘 → 结果可视化”四个核心环节构建全流程分析能力。搜索阶段依托 Tavily API，文本洞察由本地 Ollama 模型完成，确保数据合规与私有化部署需求。

## 功能亮点
- **Tavily 智能检索**：基于多关键词批量获取绿色电力相关资讯，自动生成原始语料库。
- **中文文本预处理**：去重、清洗、关键词抽取与轻量情感判定，为后续分析提供结构化输入。
- **本地 Ollama 挖掘**：调用本地 LLM（默认 `qwen2.5:7b`）提取驱动因素与障碍因素，自动生成执行摘要与政策建议。
- **可视化与报告输出**：生成因素对比图、词云及 Markdown/HTML 报告，支持快速浏览研究结论。
- **模块化流水线**：可按需运行 `crawl`、`preprocess`、`analyze`、`report` 任一阶段，便于调试与扩展。

## 目录结构
```
projectResearch/
├── data/                     # 工作目录（默认忽略内容，仅保留结构）
│   ├── raw/
│   ├── processed/
│   ├── analysis/
│   └── output/
├── src/
│   └── green_power_analysis/
│       ├── analysis/         # Ollama 文本挖掘
│       ├── crawling/         # Tavily 检索
│       ├── processing/       # 文本预处理
│       ├── reporting/        # 报告与可视化
│       ├── utils/
│       ├── cli.py            # 命令行入口
│       └── pipeline.py       # 流水线编排
├── main.py                   # 兼容入口（等同于 `python -m green_power_analysis.cli`）
├── pyproject.toml            # 项目配置 & 安装信息
├── requirements.txt          # 运行依赖
├── .vscode/settings.json     # VSCode 推荐配置
├── .gitignore
└── README.md
```

## 环境准备
1. **创建虚拟环境并安装依赖**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **配置 Tavily API**
   ```bash
   export TAVILY_API_KEY="your_api_key"  # Windows 使用 set 或 $Env:
   ```

3. **准备 Ollama 模型**
   - 安装 [Ollama](https://ollama.com/) 并启动服务：`ollama serve`
   - 拉取默认模型（可选其他模型）：
     ```bash
     ollama pull qwen2.5:7b
     ```
   - 若使用自定义模型或非默认地址，可在命令行参数中覆盖 `--ollama-model` 与 `--ollama-url`。

## 快速上手
### 运行完整分析流程
```bash
python -m green_power_analysis.cli --full
# 或使用脚本入口
python main.py --full
# 安装后也可直接调用
# green-power-analysis --full
```

### 分步骤执行
```bash
python -m green_power_analysis.cli --step crawl
python -m green_power_analysis.cli --step preprocess
python -m green_power_analysis.cli --step analyze
python -m green_power_analysis.cli --step report
```

### 查看目录状态
```bash
python -m green_power_analysis.cli --status
```

### 常用参数
- `--dir`: 指定数据工作目录（默认 `data`）
- `--keywords`: 传入自定义检索关键词列表
- `--ollama-model`: 指定 Ollama 模型名称
- `--ollama-url`: 指定 Ollama 服务地址
- `--tavily-depth`: Tavily 搜索深度（`basic` / `advanced`）
- `--tavily-max`: 每个关键词返回结果数量

## 输出内容
完整流程结束后，工作目录将生成以下内容：
```
data/
├── raw/                 # Tavily 搜索原始结果
├── processed/           # 预处理后的结构化文本与统计
├── analysis/            # LLM 分析产物（详细&综合报告）
└── output/
    ├── charts/          # 因素对比图、词云等
    └── reports/         # HTML / Markdown 综合报告
```

## 开发提示
- 项目遵循 `src` 布局，可通过 `pip install -e .` 安装到环境中。
- `green_power_analysis/pipeline.py` 集中描述流水线逻辑，便于定制各阶段实现。
- 预处理阶段依赖 `jieba` 分词，如需自定义词典可在 `TextPreprocessor` 中扩展。
- 若 Ollama 输出非 JSON，系统会自动回退到基于关键词的统计逻辑。

## 许可证
MIT License

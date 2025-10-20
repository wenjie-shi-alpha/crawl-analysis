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
│   └── output/
│       ├── raw/              # Tavily 原始检索结果
│       ├── processed/        # 结构化文本与统计
│       ├── analysis/         # LLM 深度分析输出
│       ├── final/            # 报告与图表
│       │   ├── charts/
│       │   └── reports/
│       └── meta/             # 运行元数据（配置快照等）
├── src/
│   ├── analysis/             # OpenAI 文本挖掘
│   ├── crawling/             # Tavily 检索
│   ├── processing/           # 文本预处理
│   ├── reporting/            # 报告与可视化
│   ├── utils/
│   ├── cli.py                # 命令行入口
│   ├── config.py
│   └── pipeline.py           # 流水线编排
├── main.py                   # 兼容入口（自动将 src 加入 PYTHONPATH）
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
   Tavily 调用通过官方 REST 接口完成，无需安装额外 Python 包，仅需提供 API Key。
   ```bash
   export TAVILY_API_KEY="your_api_key"  # Windows 使用 set 或 $Env:
   ```

3. **配置 OpenAI 接口**
   项目依赖 OpenAI 兼容接口完成 LLM 分析，可在根目录创建 `.env`（或直接设置环境变量）：
   ```bash
   OPENAI_API_KEY=sk-your-key
   OPENAI_MODEL=gpt-4.1-mini          # 可选，默认为 gpt-4o-mini
   OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，兼容服务地址
   OPENAI_ORG=your-org-id            # 可选，用于企业账号
   OPENAI_PROJECT=your-project-id    # 可选，用于分项目计费
   ```
   运行时会自动读取上述配置，确保 API Key 拥有调用对应模型的权限。

## 快速上手
### 运行完整分析流程
```bash
python main.py --full
# 安装为包后，也可直接使用命令行脚本
# green-power-analysis --full
```

### 分步骤执行
```bash
python main.py --step crawl
python main.py --step preprocess
python main.py --step analyze
python main.py --step report
```

### 查看目录状态
```bash
python main.py --status
```

### 常用参数
- `--dir`: 指定数据工作目录（默认 `data`）
- `--keywords`: 传入自定义检索关键词列表
- `--openai-model`: 指定 OpenAI 模型名称
- `--openai-base-url`: 覆盖 OpenAI 兼容服务地址
- `--openai-api-key`: 临时覆盖 API Key（如需在命令行传递）
- `--openai-org`: 设置 OpenAI 组织 ID
- `--openai-project`: 设置 OpenAI 项目 ID
- `--tavily-depth`: Tavily 搜索深度（`basic` / `advanced`）
- `--tavily-max`: 每个关键词返回结果数量

## 自动化风电厂省份查询
为满足在 [thewindpower.net](https://www.thewindpower.net/) 上批量查询风电厂所属省份的需求，新增了基于 Selenium 的浏览器自动化脚本 `src/crawling/thewindpower_browser.py`。

### 准备工作
- 安装 Chrome/Chromium 浏览器。
- 安装与浏览器版本匹配的 `chromedriver` 并放入 PATH，或在运行脚本时通过 `--driver-path` 指定驱动路径。使用 Selenium 4 自带的 Selenium Manager 也可自动下载驱动（首次运行需外网访问）。
- 准备包含风电厂名称的 CSV 文件，默认列名为 `name`。

### 运行示例
```bash
# 建议在虚拟环境中运行；如未安装为包，可先将 src 加入 PYTHONPATH
PYTHONPATH=src python -m crawling.thewindpower_browser \
  data/windfarms.csv \
  data/output/windfarms_province.csv \
  --name-column name \
  --delay 2.0
```

常用选项：
- `--headed`：以可视化方式启动浏览器，便于调试；默认后台无界面运行。
- `--wait`：控制元素查找超时时间（秒），默认 15。
- `--delay`：每次查询之间的休眠秒数，默认 1.5，建议视服务器限制适当增大。
- `--driver-path`：当驱动不在 PATH 中时，显式指定 `chromedriver` 位置。
- `--remote-url`：连接远程 WebDriver 服务（例如 `http://192.168.1.10:62256`）。

### 远程 chromedriver（Windows 主机 + Ubuntu 虚拟机）
若脚本运行在 Windows 上的 Ubuntu 虚拟机，而 `chromedriver` 在宿主 Windows 中运行，可按以下流程连接：
1. 在 Windows 上启动 `chromedriver.exe`，指定监听端口：
   ```powershell
   .\chromedriver.exe --port=62256 --allowed-origins=* --allowed-ips=* 
   ```
   如需绑定到特定地址，可使用 `--ip=0.0.0.0`。
2. 确认 Windows 防火墙或安全软件放行该端口；若两台机器跨网络，还需在路由器或 VPN 中开放 62256。
3. 在 Ubuntu 虚拟机上运行脚本，通过 `--remote-url` 指定宿主 Windows 的局域网/桥接地址（在宿主中执行 `ipconfig` 获取）：
   ```bash
   PYTHONPATH=src python -m crawling.thewindpower_browser \
     data/windfarms.csv \
     data/output/windfarms_province.csv \
     --remote-url http://WINDOWS_IP:62256 \
     --delay 2.5
   ```
   如需观察浏览器，请在启动 chromedriver 时加入 `--verbose` 并在脚本侧添加 `--headed`。

## 代码风格
- 项目使用 Black 统一 Python 代码格式，可通过 `pip install -e .[dev]` 安装开发依赖，或在虚拟环境中单独执行 `pip install black`。
- 激活虚拟环境后运行 `black .` 会按照 `pyproject.toml` 中的配置格式化代码，建议在提交代码前执行。

## 输出内容
完整流程结束后，工作目录将生成以下内容：
```
data/
└── output/
    ├── raw/             # Tavily 搜索原始结果
    ├── processed/       # 预处理后的结构化文本与统计
    ├── analysis/        # LLM 分析产物（详细&综合报告）
    ├── final/
    │   ├── charts/      # 因素对比图、词云等
    │   └── reports/     # HTML / Markdown 综合报告
    └── meta/            # 运行配置与其他元信息
```

## 开发提示
- 项目遵循 `src` 布局，可通过 `pip install -e .` 安装到环境中。
- `src/pipeline.py` 集中描述流水线逻辑，便于定制各阶段实现。
- 预处理阶段依赖 `jieba` 分词，如需自定义词典可在 `TextPreprocessor` 中扩展。
- 若 OpenAI 输出非 JSON，系统会自动回退到基于关键词的统计逻辑。

## 许可证
MIT License

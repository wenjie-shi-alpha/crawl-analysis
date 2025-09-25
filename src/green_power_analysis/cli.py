"""Command line interface for the project."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import replace
from pathlib import Path
from typing import Dict

from .config import PipelineConfig
from .pipeline import GreenPowerPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="green-power-analysis",
        description="中国居民绿色电力消费驱动机制与障碍分析系统",
    )
    parser.add_argument("--full", action="store_true", help="运行完整流程")
    parser.add_argument(
        "--step",
        choices=["crawl", "preprocess", "analyze", "report"],
        help="运行单独步骤",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="显示当前数据目录状态",
    )
    parser.add_argument(
        "--dir",
        default="data",
        help="指定数据工作目录",
    )
    parser.add_argument(
        "--keywords",
        nargs="*",
        help="覆盖默认检索关键词",
    )
    parser.add_argument(
        "--ollama-model",
        default=None,
        help="指定 Ollama 模型名称",
    )
    parser.add_argument(
        "--ollama-url",
        default=None,
        help="本地 Ollama 服务地址 (默认 http://localhost:11434)",
    )
    parser.add_argument(
        "--tavily-depth",
        default=None,
        help="Tavily 搜索深度 (basic/advanced)",
    )
    parser.add_argument(
        "--tavily-max",
        type=int,
        default=None,
        help="每个关键词最多返回结果数",
    )
    return parser


def apply_overrides(config: PipelineConfig, args: argparse.Namespace) -> PipelineConfig:
    kwargs = {}
    if args.dir:
        kwargs["base_dir"] = Path(args.dir)
    if args.keywords:
        kwargs["keywords"] = args.keywords
    if args.ollama_model:
        kwargs["ollama_model"] = args.ollama_model
    if args.ollama_url:
        kwargs["ollama_base_url"] = args.ollama_url
    if args.tavily_depth:
        kwargs["tavily_search_depth"] = args.tavily_depth
    if args.tavily_max is not None:
        kwargs["tavily_results_per_keyword"] = args.tavily_max
    return replace(config, **kwargs)


def show_status(config: PipelineConfig) -> None:
    paths = config.paths()
    info: Dict[str, Dict[str, str]] = {}
    for name, directory in {
        "raw": paths.raw_dir,
        "processed": paths.processed_dir,
        "analysis": paths.analysis_dir,
        "output": paths.output_dir,
    }.items():
        files = list(directory.glob("*")) if directory.exists() else []
        info[name] = {
            "path": str(directory.resolve()),
            "exists": str(directory.exists()),
            "files": str(len(files)),
        }
    print(json.dumps(info, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = apply_overrides(PipelineConfig(), args)
    pipeline = GreenPowerPipeline(config)

    if args.status:
        show_status(config)
        return

    try:
        if args.full:
            pipeline.run_all()
        elif args.step:
            step = args.step
            if step == "crawl":
                pipeline.crawl()
            elif step == "preprocess":
                pipeline.preprocess()
            elif step == "analyze":
                pipeline.analyze()
            elif step == "report":
                pipeline.report()
        else:
            parser.print_help()
    except Exception as exc:  # pragma: no cover - command line feedback
        logger.error("执行失败: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":  # pragma: no cover
    main()

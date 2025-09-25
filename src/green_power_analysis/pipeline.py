"""High level orchestration for the project pipeline."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from .analysis import OllamaTextMiner
from .config import PipelineConfig
from .crawling import TavilyCrawler
from .processing import TextPreprocessor
from .reporting import ResultAnalyzer
from .utils.io import write_json

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineResult:
    raw_file: Optional[str] = None
    processed_files: Optional[List[str]] = None
    analysis_report: Optional[str] = None
    reporting_outputs: Optional[Dict] = None


class GreenPowerPipeline:
    """Coordinates every stage of the analysis."""

    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        self.config = config or PipelineConfig()
        self.paths = self.config.paths()
        logger.debug("Pipeline initialised with config %s", self.config)

    def run_all(self) -> PipelineResult:
        logger.info("启动完整分析流程")
        self._write_config()
        raw_file = self.crawl()
        processed = self.preprocess()
        analysis_report = self.analyze()
        reporting_outputs = self.report()
        logger.info("分析流程完成")
        return PipelineResult(raw_file, processed, analysis_report, reporting_outputs)

    def crawl(self) -> str:
        logger.info("阶段一: 调用 Tavily 执行数据检索")
        crawler = TavilyCrawler(
            keywords=self.config.keywords,
            output_dir=str(self.paths.raw_dir),
            search_depth=self.config.tavily_search_depth,
            max_results_per_keyword=self.config.tavily_results_per_keyword,
        )
        results = crawler.crawl()
        if not results:
            raise RuntimeError("Tavily 未返回任何结果，请检查关键词或配额")
        output_path = crawler.save(results)
        logger.info("已保存 %s 条搜索结果 -> %s", len(results), output_path)
        return output_path

    def preprocess(self) -> List[str]:
        logger.info("阶段二: 文本预处理")
        preprocessor = TextPreprocessor(self.paths.raw_dir, self.paths.processed_dir)
        outputs = preprocessor.process_all()
        if not outputs:
            raise RuntimeError("预处理阶段未生成文件，请确认原始数据是否存在")
        logger.info("完成预处理，共输出 %d 个文件", len(outputs))
        return outputs

    def analyze(self) -> str:
        logger.info("阶段三: 使用本地 Ollama 进行文本挖掘")
        miner = OllamaTextMiner(
            input_dir=self.paths.processed_dir,
            output_dir=self.paths.analysis_dir,
            model_name=self.config.ollama_model,
            base_url=self.config.ollama_base_url,
        )
        report_path = miner.run_analysis()
        logger.info("文本挖掘完成 -> %s", report_path)
        return report_path

    def report(self) -> Dict:
        logger.info("阶段四: 结果分析与可视化")
        analyzer = ResultAnalyzer(
            input_dir=str(self.paths.analysis_dir),
            output_dir=str(self.paths.output_dir),
        )
        outputs = analyzer.run_analysis()
        logger.info("已生成报告和图表")
        return outputs

    def _write_config(self) -> None:
        config_path = self.paths.base_dir / "config.json"
        data = asdict(self.config)
        data["paths"] = {"base": str(self.paths.base_dir)}
        write_json(config_path, data)
        logger.debug("保存配置文件 -> %s", config_path)

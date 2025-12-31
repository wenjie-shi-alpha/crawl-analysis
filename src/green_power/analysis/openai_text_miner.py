"""Text mining powered by the OpenAI API."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from openai import OpenAI

from ..utils.io import read_json, write_json, write_text

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import matplotlib

# Set non-interactive backend
matplotlib.use('Agg')
# Set Chinese font support if available, otherwise fallback
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

logger = logging.getLogger(__name__)

DRIVING_FRAMEWORK: Dict[str, List[str]] = {
    "经济因素": ["成本效益", "价格优势", "补贴政策", "税收优惠", "投资回报"],
    "环境因素": ["环保意识", "气候变化", "碳中和", "清洁能源", "减排目标"],
    "社会因素": ["社会责任", "品牌形象", "社区压力", "邻里效应", "示范效应"],
    "技术因素": ["技术成熟", "便利性", "可靠性", "智能化", "创新性"],
    "政策因素": ["政策支持", "法规要求", "标准制定", "市场机制", "激励措施"],
}

BARRIER_FRAMEWORK: Dict[str, List[str]] = {
    "经济障碍": ["高成本", "价格昂贵", "经济负担", "收益不明", "投资风险"],
    "认知障碍": ["认知不足", "信息缺乏", "知识缺乏", "理解困难", "误解"],
    "基础设施障碍": ["基础设施", "供给不足", "网络覆盖", "配套服务", "技术限制"],
    "制度障碍": ["政策不完善", "标准缺失", "监管空白", "市场失灵", "制度障碍"],
    "行为障碍": ["习惯依赖", "惰性", "风险规避", "保守心理", "从众心理"],
}


@dataclass(slots=True)
class OpenAIClient:
    """Lightweight wrapper around the OpenAI SDK."""

    api_key: str
    model: str
    base_url: Optional[str] = None
    organization: Optional[str] = None
    project: Optional[str] = None
    timeout: int = 120
    _client: OpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise RuntimeError("未配置 OPENAI_API_KEY，无法调用 OpenAI 接口")
        client_kwargs = {
            "api_key": self.api_key,
            "timeout": self.timeout,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        if self.organization:
            client_kwargs["organization"] = self.organization
        if self.project:
            client_kwargs["project"] = self.project
        self._client = OpenAI(**client_kwargs)

    def generate(self, prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an energy policy analyst. Respond in strict JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # pragma: no cover - network errors
            raise RuntimeError(
                "调用 OpenAI 模型失败，请检查网络、API Key 或模型配置"
            ) from exc
        if not response.choices:
            return ""
        message = response.choices[0].message
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [segment.get("text", "") for segment in content if isinstance(segment, dict)]
            return "".join(parts).strip()
        return ""


@dataclass(slots=True)
class OpenAITextMiner:
    """Run high-level analysis with an OpenAI-hosted model."""

    input_dir: Path
    output_dir: Path
    api_key: str
    model_name: str
    base_url: Optional[str] = None
    organization: Optional[str] = None
    project: Optional[str] = None
    client: OpenAIClient = field(init=False)

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = OpenAIClient(
            api_key=self.api_key,
            model=self.model_name,
            base_url=self.base_url,
            organization=self.organization,
            project=self.project,
        )

    def run_analysis(self) -> str:
        processed_files = sorted(self.input_dir.glob("processed_*.json"))
        if not processed_files:
            raise RuntimeError(f"在 {self.input_dir} 中未找到预处理文件")

        detailed_results: List[Dict] = []
        for file_path in processed_files:
            try:
                result = self._analyze_file(file_path)
            except Exception as exc:
                result = {
                    "file": file_path.name,
                    "error": str(exc),
                    "generated_at": datetime.now().isoformat(),
                }
            detailed_results.append(result)

        comprehensive = self._generate_comprehensive_report(detailed_results)
        
        # Generate charts
        chart_paths = self._generate_charts(comprehensive)
        comprehensive["charts"] = chart_paths

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        detailed_path = self.output_dir / f"detailed_analysis_{timestamp}.json"
        report_path = self.output_dir / f"comprehensive_report_{timestamp}.json"
        markdown_path = self.output_dir / f"comprehensive_report_{timestamp}.md"

        # Update markdown with charts
        comprehensive["markdown_report"] = self._build_markdown(
            comprehensive["driving_factors_analysis"],
            comprehensive["barriers_analysis"],
            comprehensive["recommendations"],
            comprehensive["executive_summary"],
            chart_paths
        )

        write_json(detailed_path, detailed_results)
        write_json(report_path, comprehensive)
        write_text(markdown_path, comprehensive.get("markdown_report", ""))

        return str(report_path)

    def _analyze_file(self, file_path: Path) -> Dict:
        documents = read_json(file_path)
        texts = [doc.get("cleaned_content") or doc.get("content") or "" for doc in documents]
        texts = [text for text in texts if text]
        sample_text = "\n\n".join(texts[:15])  # limit prompt length for efficiency

        driving = self._extract_with_llm(sample_text, DRIVING_FRAMEWORK, "驱动因素")
        barriers = self._extract_with_llm(sample_text, BARRIER_FRAMEWORK, "障碍因素")
        behavior = self._aggregate_behavior(documents)

        return {
            "file": file_path.name,
            "documents": len(documents),
            "driving_factors": driving,
            "barriers": barriers,
            "behavior_patterns": behavior,
            "generated_at": datetime.now().isoformat(),
        }

    def _extract_with_llm(
        self,
        text: str,
        framework: Dict[str, List[str]],
        label: str,
    ) -> Dict[str, List[Dict]]:
        if not text:
            return self._fallback_extraction(text, framework)

        prompt = self._build_prompt(text, framework, label)
        try:
            response = self.client.generate(prompt)
        except RuntimeError as exc:
            logger.warning(
                "OpenAI 调用失败 (%s)，切换到关键词统计回退。", exc, exc_info=False
            )
            return self._fallback_extraction(text, framework)
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return self._fallback_extraction(text, framework)

    def _build_prompt(self, text: str, framework: Dict[str, List[str]], label: str) -> str:
        categories = "\n".join(
            f"- {category}: {', '.join(factors)}" for category, factors in framework.items()
        )
        return (
            "你是一名资深能源政策分析师，正在撰写关于中国居民绿色电力消费的学术报告。"
            "请阅读下列文本片段，基于PESTEL（政治、经济、社会、技术、环境、法律）框架，"
            "深入挖掘并归纳{label}。请保持学术严谨性，避免泛泛而谈。"
            "\n\n分类参考:\n"
            + categories
            + "\n\n文本内容:\n"
            + text
            + "\n\n请输出 JSON 对象，键为上述分类，值为对象数组，每个对象包含 factor (具体因素描述), "
            + "evidence (原文依据), confidence (high/medium/low), impact_score (1-5, 影响程度) 四个字段。"
        )

    def _fallback_extraction(
        self, text: str, framework: Dict[str, List[str]]
    ) -> Dict[str, List[Dict]]:
        aggregate: Dict[str, List[Dict]] = {}
        for category, keywords in framework.items():
            found = []
            for keyword in keywords:
                count = text.count(keyword) if text else 0
                if count:
                    found.append({"factor": keyword, "frequency": count, "confidence": "medium"})
            aggregate[category] = sorted(found, key=lambda item: item["frequency"], reverse=True)
        return aggregate

    def _aggregate_behavior(self, documents: Sequence[Dict]) -> Dict[str, int]:
        counter: Counter = Counter()
        for doc in documents:
            for factor in doc.get("behavior_factors", []):
                counter[factor] += 1
        return dict(counter)

    def _generate_comprehensive_report(self, results: List[Dict]) -> Dict:
        driving_combined: Dict[str, List[Dict]] = defaultdict(list)
        barrier_combined: Dict[str, List[Dict]] = defaultdict(list)
        behavior_combined: Counter = Counter()
        errors = []

        for result in results:
            if "error" in result:
                errors.append(result)
                continue
            for category, factors in result.get("driving_factors", {}).items():
                driving_combined[category].extend(factors)
            for category, factors in result.get("barriers", {}).items():
                barrier_combined[category].extend(factors)
            behavior_combined.update(result.get("behavior_patterns", {}))

        driving_summary = {k: driving_combined[k] for k in sorted(driving_combined)}
        barrier_summary = {k: barrier_combined[k] for k in sorted(barrier_combined)}
        behavior_summary = dict(behavior_combined.most_common())
        recommendations = self._build_recommendations(driving_summary, barrier_summary)
        executive_summary = self._build_executive_summary(driving_summary, barrier_summary)
        markdown_report = self._build_markdown(driving_summary, barrier_summary, recommendations, executive_summary)

        return {
            "generated_at": datetime.now().isoformat(),
            "driving_factors_analysis": driving_summary,
            "barriers_analysis": barrier_summary,
            "behavior_patterns": behavior_summary,
            "recommendations": recommendations,
            "executive_summary": executive_summary,
            "errors": errors,
            "markdown_report": markdown_report,
        }

    def _build_recommendations(
        self,
        driving: Dict[str, List[Dict]],
        barriers: Dict[str, List[Dict]],
    ) -> List[str]:
        recommendations = [
            "加强绿色电力政策宣传与科普，提高居民认知度",
            "完善财税激励与价格机制，降低绿色电力消费门槛",
            "加快配套基础设施建设，确保绿色电力供给稳定",
            "建立权威认证与信息透明机制，增强消费者信心",
            "引导社区与企业示范，营造绿色用电的社会氛围",
        ]
        if not barriers:
            return recommendations
        barrier_counts = Counter()
        for factors in barriers.values():
            for factor in factors:
                name = factor.get("factor") if isinstance(factor, dict) else str(factor)
                barrier_counts[name] += factor.get("frequency", 1) if isinstance(factor, dict) else 1
        if barrier_counts:
            top_barrier, _ = barrier_counts.most_common(1)[0]
            recommendations.insert(0, f"优先解决 '{top_barrier}' 等制约绿色电力推广的核心障碍")
        return recommendations

    def _build_executive_summary(
        self,
        driving: Dict[str, List[Dict]],
        barriers: Dict[str, List[Dict]],
    ) -> Dict[str, str]:
        return {
            "主要发现": "居民绿色电力消费受政策、经济与环境多重因素影响，认知与成本仍是主要瓶颈",
            "驱动因素": "政策激励与环保意识持续增强，技术便利性逐步提高",
            "障碍因素": "高成本、供给不确定与信息不对称仍然显著",
            "建议方向": "从政策宣传、价格机制、基础设施与示范引导四个维度协同推进",
        }

    def _generate_charts(self, data: Dict) -> Dict[str, str]:
        """Generate visualizations for the report."""
        charts = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Driving Factors Bar Chart
        driving_data = []
        for category, factors in data.get("driving_factors_analysis", {}).items():
            count = len(factors)
            driving_data.append({"Category": category, "Count": count})
        
        if driving_data:
            df_driving = pd.DataFrame(driving_data)
            plt.figure(figsize=(10, 6))
            sns.barplot(data=df_driving, x="Category", y="Count", palette="viridis")
            plt.title("Distribution of Driving Factors by Category")
            plt.xticks(rotation=45)
            plt.tight_layout()
            path = self.output_dir / f"driving_factors_{timestamp}.png"
            plt.savefig(path)
            plt.close()
            charts["driving_factors"] = str(path)

        # 2. Barriers Bar Chart
        barrier_data = []
        for category, factors in data.get("barriers_analysis", {}).items():
            count = len(factors)
            barrier_data.append({"Category": category, "Count": count})
            
        if barrier_data:
            df_barrier = pd.DataFrame(barrier_data)
            plt.figure(figsize=(10, 6))
            sns.barplot(data=df_barrier, x="Category", y="Count", palette="magma")
            plt.title("Distribution of Barriers by Category")
            plt.xticks(rotation=45)
            plt.tight_layout()
            path = self.output_dir / f"barriers_{timestamp}.png"
            plt.savefig(path)
            plt.close()
            charts["barriers"] = str(path)

        return charts

    def _build_markdown(
        self,
        driving: Dict[str, List[Dict]],
        barriers: Dict[str, List[Dict]],
        recommendations: List[str],
        executive_summary: Dict[str, str],
        charts: Dict[str, str] = None,
    ) -> str:
        lines = ["# 中国居民绿色电力消费驱动机制与障碍分析报告", ""]
        lines.append(f"*报告生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}*")
        lines.append("")
        lines.append("## 执行摘要")
        for key, value in executive_summary.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")

        if driving:
            lines.append("## 驱动因素分析")
            if charts and "driving_factors" in charts:
                lines.append(f"![Driving Factors]({charts['driving_factors']})")
                lines.append("")
            
            for category, factors in driving.items():
                lines.append(f"### {category}")
                for factor in factors[:5]:
                    if isinstance(factor, dict):
                        name = factor.get("factor", "")
                        freq = factor.get("frequency")
                        confidence = factor.get("confidence", "")
                        lines.append(f"- {name} (频率: {freq}, 信心: {confidence})")
                    else:
                        lines.append(f"- {factor}")
                lines.append("")

        if barriers:
            lines.append("## 障碍因素分析")
            if charts and "barriers" in charts:
                lines.append(f"![Barriers]({charts['barriers']})")
                lines.append("")

            for category, factors in barriers.items():
                lines.append(f"### {category}")
                for factor in factors[:5]:
                    if isinstance(factor, dict):
                        name = factor.get("factor", "")
                        freq = factor.get("frequency")
                        confidence = factor.get("confidence", "")
                        lines.append(f"- {name} (频率: {freq}, 信心: {confidence})")
                    else:
                        lines.append(f"- {factor}")
                lines.append("")

        if recommendations:
            lines.append("## 政策建议")
            for idx, rec in enumerate(recommendations, 1):
                lines.append(f"{idx}. {rec}")
            lines.append("")

        return "\n".join(lines)

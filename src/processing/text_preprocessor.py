"""Text preprocessing for green power analysis."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Set

import jieba
import jieba.analyse

from utils.io import write_json


@dataclass(slots=True)
class TextPreprocessor:
    """Cleans raw search documents and extracts lightweight features."""

    input_dir: Path
    output_dir: Path

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.stopwords = self._load_stopwords()
        self.green_power_keywords = self._build_keyword_map()

    def _load_stopwords(self) -> Set[str]:
        return {
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
            "一个",
            "上",
            "也",
            "很",
            "到",
            "说",
            "要",
            "去",
            "你",
            "会",
            "着",
            "没有",
            "看",
            "好",
            "自己",
            "这",
            "对",
            "于",
            "时",
            "可以",
            "这个",
            "与",
            "中",
            "还",
            "能",
            "为",
            "以",
            "及",
            "但",
            "或",
            "而",
            "等",
            "如",
            "所",
            "此",
            "其",
            "但是",
            "因为",
            "所以",
            "虽然",
            "然而",
            "不过",
            "另外",
            "此外",
        }

    def _build_keyword_map(self) -> Dict[str, List[str]]:
        return {
            "驱动因素": [
                "政策支持",
                "政府补贴",
                "环保意识",
                "经济效益",
                "技术进步",
                "社会责任",
                "品牌形象",
                "成本节约",
                "能源安全",
                "气候变化",
                "碳中和",
                "碳达峰",
                "清洁生产",
                "可持续发展",
            ],
            "障碍因素": [
                "成本较高",
                "价格昂贵",
                "技术不成熟",
                "基础设施不足",
                "认知不足",
                "政策不完善",
                "市场机制缺失",
                "信息不对称",
                "供给不稳定",
                "质量担忧",
                "便利性差",
                "选择有限",
                "标准不统一",
                "监管不到位",
            ],
            "消费行为": [
                "购买意愿",
                "使用频率",
                "支付意愿",
                "推荐行为",
                "重复购买",
                "口碑传播",
                "品牌忠诚",
                "价格敏感",
                "质量要求",
                "服务期望",
            ],
        }

    def process_all(self) -> List[str]:
        """Process every JSON document inside the input directory."""
        json_files = sorted(self.input_dir.glob("*.json"))
        if not json_files:
            return []

        outputs: List[str] = []
        for json_file in json_files:
            output = self._process_file(json_file)
            if output:
                outputs.append(output)
        return outputs

    def _process_file(self, path: Path) -> str | None:
        with path.open("r", encoding="utf-8") as handle:
            raw_data = json.load(handle)

        unique_data = self._remove_duplicates(raw_data)
        processed = []
        for item in unique_data:
            try:
                processed_item = self._categorize_content(item)
            except ValueError:
                continue
            if processed_item["quality_score"] > 10:
                processed.append(processed_item)

        stats = self._generate_statistics(processed)
        stem = path.stem
        processed_path = self.output_dir / f"processed_{stem}.json"
        stats_path = self.output_dir / f"stats_{stem}.json"
        write_json(processed_path, processed)
        write_json(stats_path, stats)
        return str(processed_path)

    def _remove_duplicates(self, data: Iterable[Dict]) -> List[Dict]:
        seen_titles: Set[str] = set()
        seen_contents: Set[str] = set()
        unique: List[Dict] = []
        for item in data:
            title = (item.get("title") or "").strip()
            content = (item.get("content") or "").strip()
            title_key = re.sub(r"\s+", "", title.lower())
            content_key_raw = content[:200] if len(content) > 200 else content
            content_key = re.sub(r"\s+", "", content_key_raw.lower())
            if title_key in seen_titles or content_key in seen_contents:
                continue
            seen_titles.add(title_key)
            seen_contents.add(content_key)
            unique.append(item)
        return unique

    def _categorize_content(self, item: Dict) -> Dict:
        title = item.get("title", "")
        content = item.get("content", "")
        full_text = f"{title} {content}".strip()
        cleaned_text = self._clean_text(full_text)
        if not cleaned_text:
            raise ValueError("缺少有效文本")

        keywords = self._extract_keywords(cleaned_text)
        driving_factors: List[str] = []
        barrier_factors: List[str] = []
        behavior_factors: List[str] = []
        for category, factor_list in self.green_power_keywords.items():
            for factor in factor_list:
                if factor in full_text:
                    if category == "驱动因素":
                        driving_factors.append(factor)
                    elif category == "障碍因素":
                        barrier_factors.append(factor)
                    else:
                        behavior_factors.append(factor)

        positive_words = ["支持", "推广", "优势", "便利", "实惠", "可靠", "清洁", "环保"]
        negative_words = ["困难", "障碍", "问题", "缺乏", "不足", "昂贵", "复杂"]
        positive_count = sum(1 for word in positive_words if word in full_text)
        negative_count = sum(1 for word in negative_words if word in full_text)
        sentiment = "neutral"
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"

        text_length = len(cleaned_text)
        quality_score = min(100, text_length / 10)

        return {
            **item,
            "cleaned_content": cleaned_text,
            "keywords": keywords,
            "driving_factors": driving_factors,
            "barrier_factors": barrier_factors,
            "behavior_factors": behavior_factors,
            "sentiment": sentiment,
            "text_length": text_length,
            "quality_score": quality_score,
            "processed_time": datetime.now().isoformat(),
        }

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9\s\.,!?;:()（）。，！？；：]", "", text)
        text = re.sub(r"\s+", " ", text)
        sentences = text.split("。")
        filtered = [s.strip() for s in sentences if 10 <= len(s.strip()) <= 500]
        return "。".join(filtered)

    def _extract_keywords(self, text: str, top_k: int = 20) -> List[str]:
        keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=False)
        return [kw for kw in keywords if kw not in self.stopwords and len(kw) > 1]

    def _generate_statistics(self, processed_data: List[Dict]) -> Dict:
        stats = {
            "total_items": len(processed_data),
            "source_distribution": Counter(item.get("source", "unknown") for item in processed_data),
            "sentiment_distribution": Counter(item.get("sentiment", "neutral") for item in processed_data),
            "avg_text_length": (
                sum(item.get("text_length", 0) for item in processed_data) / len(processed_data)
                if processed_data
                else 0
            ),
            "top_keywords": [],
            "driving_factors_frequency": Counter(),
            "barrier_factors_frequency": Counter(),
            "behavior_factors_frequency": Counter(),
        }
        all_keywords: List[str] = []
        for item in processed_data:
            all_keywords.extend(item.get("keywords", []))
            for factor in item.get("driving_factors", []):
                stats["driving_factors_frequency"][factor] += 1
            for factor in item.get("barrier_factors", []):
                stats["barrier_factors_frequency"][factor] += 1
            for factor in item.get("behavior_factors", []):
                stats["behavior_factors_frequency"][factor] += 1

        stats["top_keywords"] = Counter(all_keywords).most_common(30)
        stats["source_distribution"] = dict(stats["source_distribution"])
        stats["sentiment_distribution"] = dict(stats["sentiment_distribution"])
        stats["driving_factors_frequency"] = dict(stats["driving_factors_frequency"])
        stats["barrier_factors_frequency"] = dict(stats["barrier_factors_frequency"])
        stats["behavior_factors_frequency"] = dict(stats["behavior_factors_frequency"])
        stats["generated_at"] = datetime.now().isoformat()
        return stats

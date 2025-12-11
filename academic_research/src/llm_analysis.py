import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


class LLMInterpreter:
    """Leverages OpenAI models to summarize topics and generate policy insights."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.enabled = bool(self.api_key) and os.getenv("ENABLE_LLM_ANALYSIS", "true").lower() not in ("0", "false", "off")
        self.client: Optional[OpenAI] = None

        if self.enabled:
            try:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception:
                self.enabled = False
                self.client = None

    def available(self) -> bool:
        return self.enabled and self.client is not None

    def _extract_text(self, response) -> str:
        if not response:
            return ""
        try:
            # openai Responses API format
            return response.output[0].content[0].text
        except Exception:
            pass
        try:
            return response.choices[0].message['content']  # legacy fallback
        except Exception:
            return ""

    def summarize_topics(self, lda_topics: Dict, nmf_topics: Dict) -> List[str]:
        if not self.available() or (not lda_topics and not nmf_topics):
            return []

        prompt_lines = [
            "你是一名能源经济学研究员，请基于以下主题词提炼更高级别的洞察。",
            "请给出3-4条结构化bullet，每条包含：主题名称、核心含义、潜在政策含义。",
            "\n【LDA主题】",
        ]
        for topic, words in lda_topics.items():
            term_str = ', '.join([w['word'] for w in words[:8]])
            prompt_lines.append(f"- {topic}: {term_str}")

        prompt_lines.append("\n【NMF主题】")
        for topic, words in nmf_topics.items():
            term_str = ', '.join([w['word'] for w in words[:8]])
            prompt_lines.append(f"- {topic}: {term_str}")

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": "You are an expert energy-policy analyst providing concise insights in Chinese."
                },
                {
                    "role": "user",
                    "content": '\n'.join(prompt_lines)
                }
            ]
        )

        text = self._extract_text(response)
        return [line.strip() for line in text.split('\n') if line.strip()]

    def generate_factor_insights(self, factor_details: List[Dict], sentiment_profile: Dict) -> List[str]:
        if not self.available() or not factor_details:
            return []

        factor_lines = [f"{item['factor']}: 覆盖{item['coverage_docs']}篇, 净强度{item['net_score']}, 高频词{','.join(item['top_terms'])}" for item in factor_details]
        sentiment_line = f"平均情感: {sentiment_profile.get('mean')}, 中位数: {sentiment_profile.get('median')}, 情感分布: {sentiment_profile.get('label_counts')}"

        prompt = "请根据以下驱动-阻碍要素指标和情感结果，给出政策建议：\n" + '\n'.join(factor_lines) + "\n" + sentiment_line

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": "You are an energy policy advisor. Respond with numbered recommendations in Chinese."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        text = self._extract_text(response)
        return [line.strip() for line in text.split('\n') if line.strip()]

    def label_clusters(self, cluster_details: List[Dict]) -> List[str]:
        if not self.available() or not cluster_details:
            return []

        prompt_lines = ["请为以下语义聚类命名，并描述代表性叙事："]
        for detail in cluster_details:
            prompt_lines.append(
                f"Cluster {detail['cluster_id']} (size={detail['size']}): {', '.join(detail['top_terms'][:10])}"
            )

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": "Name clusters with short Chinese titles plus one-sentence explanation."
                },
                {
                    "role": "user",
                    "content": '\n'.join(prompt_lines)
                }
            ]
        )

        text = self._extract_text(response)
        return [line.strip() for line in text.split('\n') if line.strip()]

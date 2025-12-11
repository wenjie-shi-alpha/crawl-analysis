import json
import re
from urllib.parse import urlparse

import jieba
from pathlib import Path
from typing import List, Dict

class TextPreprocessor:
    def __init__(self, stopwords_path: str = "academic_research/data/stopwords.txt"):
        self.stopwords = self._load_stopwords(stopwords_path)
        self._add_custom_words()

    def _load_stopwords(self, path: str) -> set:
        stopwords = set()
        if Path(path).exists():
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    stopwords.add(line.strip())
        # Add some common English stopwords just in case
        stopwords.update(['the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but'])
        return stopwords

    def _add_custom_words(self):
        """Add domain-specific terms to jieba dictionary"""
        custom_words = [
            "绿电", "绿色电力", "可再生能源", "清洁能源", "双碳", "碳中和", "碳达峰",
            "绿证", "绿色电力证书", "配额制", "消纳责任", "电力市场", "电力交易",
            "碳足迹", "ESG", "供应链", "分布式光伏", "风电", "光伏", "上网电价",
            "平价上网", "溢价", "电碳联动", "碳关税", "CBAM", "RE100"
        ]
        for word in custom_words:
            jieba.add_word(word)

    def clean_text(self, text: str) -> str:
        """Remove URLs, HTML tags, and special characters"""
        if not text:
            return ""
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove special characters but keep Chinese, English, numbers
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text and remove stopwords"""
        text = self.clean_text(text)
        words = jieba.cut(text)
        return [w for w in words if w.strip() and w not in self.stopwords and len(w) > 1]

    def _extract_domain(self, url: str) -> str:
        if not url:
            return ""
        try:
            netloc = urlparse(url).netloc.lower()
            return netloc[4:] if netloc.startswith("www.") else netloc
        except ValueError:
            return ""

    def process_file(self, input_path: str) -> List[Dict]:
        """Load JSON file and process all records"""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        processed_docs = []
        results = data.get('results', [])

        for idx, item in enumerate(results):
            # Combine title and content for fuller context
            full_text = f"{item.get('title', '')} {item.get('content', '')}"
            tokens = self.tokenize(full_text)

            if tokens:
                processed_docs.append({
                    'doc_id': idx,
                    'original_title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'domain': self._extract_domain(item.get('url', '')),
                    'source': item.get('source', ''),
                    'keyword': item.get('keyword', ''),
                    'crawl_time': item.get('crawl_time', ''),
                    'full_text': full_text,
                    'tokens': tokens,
                    'processed_text': ' '.join(tokens),
                    'token_count': len(tokens),
                    'character_len': len(full_text)
                })

        return processed_docs

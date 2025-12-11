import numpy as np
import pandas as pd
from collections import Counter, defaultdict
from itertools import combinations
from typing import Dict, List, Optional, Tuple, Any, Union
from urllib.parse import urlparse

from gensim import corpora, models
from sklearn.cluster import KMeans
from sklearn.decomposition import NMF, TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import TSNE
from sklearn.metrics.pairwise import cosine_similarity
from snownlp import SnowNLP


class TextAnalyzer:
    SOURCE_CATEGORY_RULES = {
        "政府监管": ("gov.cn", "nea.gov", "ndrc", "mee.gov", "miit.gov", "mof.gov", "sasac"),
        "央媒/党媒": ("xinhuanet", "news.cn", "people.com.cn", "cctv", "qstheory", "crntt", "cnr.cn"),
        "财经与行业媒体": ("caixin", "yicai", "21jingji", "bjx", "chinaenergy", "chinapower", "ce.cn", "sxcoal", "energychina"),
        "研究机构/智库": ("wri", "casisd", "cas", "pku.edu", "tsinghua", "sjtu", "research", "thinktank"),
        "国际组织/外媒": ("reuters", "bloomberg", "ft.com", "un.org", "iea", "worldbank", "oecd", "ieee", "weforum"),
        "企业/园区实践": ("stategrid", "sgcc", "jd.com", "alibaba", "baidu", "trip.com", "corp", "company", "group"),
    }

    DRIVER_TERMS = frozenset({
        "促进", "推动", "激励", "鼓励", "支持", "优势", "收益", "机会", "保障", "便利",
        "提振", "示范", "创新", "低碳", "减排", "履约", "倡议", "承诺", "品牌", "竞争力",
        "ESG", "双碳", "增效", "降本", "普惠", "补贴", "奖励", "保障", "绿色"
    })

    BARRIER_TERMS = frozenset({
        "阻碍", "困难", "问题", "挑战", "成本", "价格", "高昂", "不足", "缺乏", "缺少",
        "壁垒", "风险", "复杂", "滞后", "波动", "限制", "瓶颈", "障碍", "不确定", "压力",
        "负担", "溢价", "缺口", "矛盾"
    })

    FACTOR_KEYWORDS = {
        "政策制度": frozenset({"政策", "制度", "配额", "责任", "考核", "监管", "标准", "规划", "绿证", "消纳", "条例", "指标", "核算"}),
        "市场机制": frozenset({"交易", "市场", "竞价", "合约", "合同", "现货", "平台", "价格", "溢价", "市场化", "电价", "撮合"}),
        "经济激励": frozenset({"成本", "收益", "补贴", "税收", "融资", "投资", "价格", "降本", "预算", "资本", "溢价"}),
        "技术与基础设施": frozenset({"技术", "电网", "储能", "并网", "系统", "数字", "智能", "设备", "平台", "数据中心", "算力", "改造"}),
        "企业战略与ESG": frozenset({"企业", "ESG", "供应链", "责任", "承诺", "品牌", "合规", "碳中和", "双碳", "采购", "管理"}),
        "社会认知与需求": frozenset({"公众", "消费者", "认知", "教育", "意识", "舆论", "信任", "需求", "意愿", "接受", "透明", "信息", "服务"}),
        "国际压力与贸易": frozenset({"国际", "出口", "欧盟", "CBAM", "碳关税", "全球", "跨境", "RE100", "外资", "海外", "贸易"}),
    }

    def __init__(self, docs: List[Dict]):
        self.docs = docs or []
        self.texts = [doc.get('processed_text', '') for doc in self.docs]
        self.tokens = [doc.get('tokens', []) for doc in self.docs]
        self.df = pd.DataFrame(self.docs)
        self._tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None

        if not self.df.empty:
            self.df['source_category'] = self.df.apply(
                lambda row: self._infer_source_category(row.get('domain', ''), row.get('url', '')),
                axis=1
            )
            if 'crawl_time' in self.df.columns:
                self.df['crawl_date'] = pd.to_datetime(self.df['crawl_time'], errors='coerce')
                self.df['crawl_day'] = self.df['crawl_date'].dt.date

    def _infer_source_category(self, domain: str, url: str) -> str:
        domain = (domain or '').lower()
        if not domain and url:
            domain = urlparse(url).netloc.lower()

        if not domain:
            return "未标注"

        for category, keywords in self.SOURCE_CATEGORY_RULES.items():
            if any(key in domain for key in keywords):
                return category

        if domain.endswith('.edu.cn') or '.edu.' in domain:
            return "高校与科研"
        if domain.endswith('.org') or '.org.' in domain:
            return "研究机构/组织"
        if domain.endswith('.gov'):
            return "政府监管"

        return "其他渠道"

    def _ensure_tfidf(self, max_df: float = 0.95, min_df: int = 2):
        if not self.texts:
            return None, None
        if self._tfidf_matrix is None:
            vectorizer = TfidfVectorizer(max_df=max_df, min_df=min_df)
            self._tfidf_matrix = vectorizer.fit_transform(self.texts)
            self._tfidf_vectorizer = vectorizer
        return self._tfidf_matrix, self._tfidf_vectorizer

    def corpus_overview(self) -> Dict[str, Any]:
        if not self.docs:
            return {}

        token_lengths = [len(doc.get('tokens', [])) for doc in self.docs]
        char_lengths = [doc.get('character_len', 0) for doc in self.docs]
        vocab = {token for doc in self.tokens for token in doc}

        time_span = None
        if not self.df.empty and 'crawl_date' in self.df.columns:
            valid_dates = self.df['crawl_date'].dropna()
            if not valid_dates.empty:
                time_span = f"{valid_dates.min().date()} 至 {valid_dates.max().date()}"

        return {
            'documents': len(self.docs),
            'vocabulary_size': len(vocab),
            'avg_tokens_per_doc': float(np.mean(token_lengths)) if token_lengths else 0,
            'median_tokens_per_doc': float(np.median(token_lengths)) if token_lengths else 0,
            'avg_character_len': float(np.mean(char_lengths)) if char_lengths else 0,
            'time_span': time_span,
            'unique_domains': int(self.df['domain'].nunique()) if 'domain' in self.df else 0,
            'keywords_covered': int(self.df['keyword'].nunique()) if 'keyword' in self.df else 0,
        }

    def get_source_distribution(self) -> Dict[str, int]:
        if self.df.empty or 'source_category' not in self.df.columns:
            return {}
        return self.df['source_category'].value_counts().to_dict()

    def get_top_keywords(self, top_k: int = 50) -> List[Tuple[str, float]]:
        tfidf_matrix, vectorizer = self._ensure_tfidf()
        if tfidf_matrix is None or vectorizer is None:
            return []

        feature_names = vectorizer.get_feature_names_out()
        mean_tfidf = np.array(tfidf_matrix.mean(axis=0)).flatten()
        sorted_indices = mean_tfidf.argsort()[::-1]

        top_keywords = []
        for idx in sorted_indices[:top_k]:
            top_keywords.append((feature_names[idx], float(mean_tfidf[idx])))

        return top_keywords

    def perform_lda_analysis(self, num_topics: int = 5, num_words: int = 10) -> Dict:
        if not self.tokens:
            return {'topics': {}, 'doc_topics': [], 'topic_strength': {}}

        dictionary = corpora.Dictionary(self.tokens)
        dictionary.filter_extremes(no_below=5, no_above=0.5)
        corpus = [dictionary.doc2bow(text) for text in self.tokens]

        if not corpus or len(dictionary) == 0:
            return {'topics': {}, 'doc_topics': [], 'topic_strength': {}}

        lda_model = models.LdaModel(
            corpus=corpus,
            id2word=dictionary,
            num_topics=num_topics,
            random_state=42,
            passes=20,
            alpha='auto'
        )

        topics = {}
        for idx in range(num_topics):
            terms = lda_model.get_topic_terms(idx, topn=num_words)
            words = []
            for term_id, weight in terms:
                words.append({
                    'word': dictionary.id2token[term_id],
                    'weight': float(weight)
                })
            topics[f"Topic_{idx+1}"] = words

        doc_topics = []
        topic_strength = defaultdict(float)
        for doc_id, bow in enumerate(corpus):
            distribution = lda_model.get_document_topics(bow, minimum_probability=0.0)
            distribution = sorted(distribution, key=lambda x: x[1], reverse=True)
            if distribution:
                dominant_topic = distribution[0]
                doc_topics.append({
                    'doc_id': doc_id,
                    'topic': f"Topic_{dominant_topic[0] + 1}",
                    'probability': float(dominant_topic[1])
                })
            for topic_idx, prob in distribution:
                topic_strength[f"Topic_{topic_idx + 1}"] += prob

        for topic_name in topic_strength:
            topic_strength[topic_name] = float(topic_strength[topic_name] / len(corpus))

        return {
            'model': lda_model,
            'corpus': corpus,
            'dictionary': dictionary,
            'topics': topics,
            'doc_topics': doc_topics,
            'topic_strength': dict(topic_strength)
        }

    def compute_nmf_topics(self, num_topics: int = 8, num_words: int = 12) -> Dict:
        tfidf_matrix, vectorizer = self._ensure_tfidf()
        if tfidf_matrix is None or vectorizer is None:
            return {'topics': {}, 'components': []}

        num_topics = min(num_topics, max(2, tfidf_matrix.shape[0] // 5)) or 2
        nmf_model = NMF(n_components=num_topics, random_state=42, init='nndsvda', max_iter=400)
        W = nmf_model.fit_transform(tfidf_matrix)
        H = nmf_model.components_
        feature_names = vectorizer.get_feature_names_out()

        topics = {}
        for idx, component in enumerate(H):
            top_indices = component.argsort()[::-1][:num_words]
            topics[f"NMF_{idx+1}"] = [
                {'word': feature_names[i], 'weight': float(component[i])}
                for i in top_indices
            ]

        doc_strength = [float(val) for val in W.max(axis=1)]

        return {
            'model': nmf_model,
            'topics': topics,
            'document_weights': doc_strength,
            'components': H
        }

    def _infer_factor_category(self, word: str) -> str:
        scores = {}
        for factor, keywords in self.FACTOR_KEYWORDS.items():
            matches = sum(1 for key in keywords if key in word)
            if matches:
                scores[factor] = matches
        if not scores:
            return "其他要素"
        return max(scores, key=scores.get)

    def classify_factors(self, keywords: List[Tuple[str, float]]) -> Dict[str, List[Dict[str, Any]]]:
        classified = {
            'drivers': [],
            'barriers': [],
            'neutral': []
        }

        for word, score in keywords:
            category = self._infer_factor_category(word)
            is_driver = any(seed in word for seed in self.DRIVER_TERMS)
            is_barrier = any(seed in word for seed in self.BARRIER_TERMS)

            record = {
                'word': word,
                'score': float(score),
                'category': category
            }

            if is_driver and not is_barrier:
                classified['drivers'].append(record)
            elif is_barrier and not is_driver:
                classified['barriers'].append(record)
            elif is_driver and is_barrier:
                classified['drivers'].append(record)
                classified['barriers'].append(record)
            else:
                classified['neutral'].append(record)

        return classified

    def analyze_factor_landscape(self) -> Dict[str, Any]:
        if not self.docs:
            return {'matrix': pd.DataFrame(), 'details': []}

        factor_stats = {
            factor: {
                'driver_docs': 0,
                'barrier_docs': 0,
                'documents': set(),
                'keywords': Counter()
            }
            for factor in self.FACTOR_KEYWORDS
        }

        for doc in self.docs:
            tokens = set(doc.get('tokens', []))
            doc_id = doc.get('doc_id')
            driver_hits = tokens & self.DRIVER_TERMS
            barrier_hits = tokens & self.BARRIER_TERMS

            for factor, keywords in self.FACTOR_KEYWORDS.items():
                matched = tokens & keywords
                if matched:
                    factor_stats[factor]['documents'].add(doc_id)
                    factor_stats[factor]['keywords'].update(matched)
                    if driver_hits:
                        factor_stats[factor]['driver_docs'] += 1
                    if barrier_hits:
                        factor_stats[factor]['barrier_docs'] += 1

        rows = []
        details = []
        for factor, stats in factor_stats.items():
            coverage = len(stats['documents'])
            driver_docs = stats['driver_docs']
            barrier_docs = stats['barrier_docs']
            top_terms = ', '.join([term for term, _ in stats['keywords'].most_common(5)])

            rows.append({
                'Factor': factor,
                'Coverage': coverage,
                'DriverDocs': driver_docs,
                'BarrierDocs': barrier_docs,
                'NetScore': driver_docs - barrier_docs,
                'TopTerms': top_terms
            })

            details.append({
                'factor': factor,
                'coverage_docs': coverage,
                'driver_docs': driver_docs,
                'barrier_docs': barrier_docs,
                'net_score': driver_docs - barrier_docs,
                'top_terms': top_terms.split(', ') if top_terms else []
            })

        matrix = pd.DataFrame(rows).sort_values(by='Coverage', ascending=False)
        return {'matrix': matrix, 'details': details}

    def compute_sentiment_profile(self) -> Dict:
        if not self.docs:
            return {'scores': []}

        sentiments = []
        for doc in self.docs:
            text = doc.get('full_text') or doc.get('processed_text', '')
            if not text.strip():
                sentiments.append(np.nan)
                continue
            try:
                score = SnowNLP(text).sentiments
            except Exception:
                score = np.nan
            sentiments.append(score)

        self.df['sentiment'] = sentiments
        valid = self.df['sentiment'].dropna()

        label_series = self.df['sentiment'].apply(
            lambda x: '正向' if pd.notna(x) and x >= 0.6 else (
                '负向' if pd.notna(x) and x <= 0.4 else (
                    '中性' if pd.notna(x) else '未知'))
        )
        self.df['sentiment_label'] = label_series

        by_source = []
        if 'source_category' in self.df.columns:
            by_source = (
                self.df.dropna(subset=['sentiment'])
                .groupby('source_category')['sentiment']
                .agg(['mean', 'count'])
                .sort_values('count', ascending=False)
                .reset_index()
                .to_dict(orient='records')
            )

        return {
            'scores': valid.astype(float).tolist(),
            'mean': float(valid.mean()) if not valid.empty else None,
            'median': float(valid.median()) if not valid.empty else None,
            'std': float(valid.std()) if not valid.empty else None,
            'label_counts': label_series.value_counts().to_dict(),
            'by_source': by_source
        }

    def build_cooccurrence_network(self, focus_words: List[str], min_edge_weight: int = 4) -> pd.DataFrame:
        if not focus_words:
            return pd.DataFrame(columns=['source', 'target', 'weight'])

        focus_set = set(focus_words)
        edge_counter = Counter()

        for tokens in self.tokens:
            filtered = [token for token in set(tokens) if token in focus_set]
            if len(filtered) < 2:
                continue
            for a, b in combinations(sorted(filtered), 2):
                edge_counter[(a, b)] += 1

        records = [
            {'source': source, 'target': target, 'weight': weight}
            for (source, target), weight in edge_counter.items()
            if weight >= min_edge_weight
        ]

        return pd.DataFrame(records)

    def cluster_documents(self, num_clusters: int = 8, top_terms: int = 10) -> Dict:
        tfidf_matrix, vectorizer = self._ensure_tfidf()
        if tfidf_matrix is None or vectorizer is None:
            return {}

        n_docs = tfidf_matrix.shape[0]
        if n_docs < 2:
            return {}
        num_clusters = max(2, min(num_clusters, n_docs))

        svd_dim = min(100, tfidf_matrix.shape[1] - 1, n_docs - 1)
        if svd_dim >= 2:
            svd = TruncatedSVD(n_components=svd_dim, random_state=42)
            features = svd.fit_transform(tfidf_matrix)
        else:
            features = tfidf_matrix.toarray()

        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(features)

        feature_names = vectorizer.get_feature_names_out()
        cluster_details = []
        for cluster_id in range(num_clusters):
            mask = labels == cluster_id
            if not mask.any():
                continue
            cluster_matrix = tfidf_matrix[mask]
            mean_scores = np.array(cluster_matrix.mean(axis=0)).ravel()
            top_idx = mean_scores.argsort()[::-1][:top_terms]
            top_terms_list = [feature_names[idx] for idx in top_idx]
            cluster_details.append({
                'cluster_id': cluster_id,
                'size': int(mask.sum()),
                'top_terms': top_terms_list,
                'centroid_distance': float(np.linalg.norm(kmeans.cluster_centers_[cluster_id]))
            })

        return {
            'labels': labels.tolist(),
            'clusters': cluster_details,
            'features': features.tolist()
        }

    def project_embeddings_tsne(self, labels: Optional[List[int]] = None, perplexity: int = 30) -> pd.DataFrame:
        tfidf_matrix, _ = self._ensure_tfidf()
        if tfidf_matrix is None or tfidf_matrix.shape[0] < 3:
            return pd.DataFrame()

        n_docs = tfidf_matrix.shape[0]
        perplexity = min(perplexity, max(5, n_docs // 3))
        svd_dim = min(50, tfidf_matrix.shape[1] - 1, n_docs - 1)
        if svd_dim >= 2:
            svd = TruncatedSVD(n_components=svd_dim, random_state=42)
            reduced = svd.fit_transform(tfidf_matrix)
        else:
            reduced = tfidf_matrix.toarray()

        tsne = TSNE(n_components=2, init='pca', random_state=42, perplexity=perplexity, learning_rate='auto')
        coords = tsne.fit_transform(reduced)

        df = pd.DataFrame(coords, columns=['x', 'y'])
        if labels:
            df['cluster'] = labels
        else:
            df['cluster'] = 0
        return df

    def build_similarity_graph(self, top_k: int = 30) -> pd.DataFrame:
        tfidf_matrix, _ = self._ensure_tfidf()
        if tfidf_matrix is None or tfidf_matrix.shape[0] < 2:
            return pd.DataFrame(columns=['source', 'target', 'weight'])

        n_docs = tfidf_matrix.shape[0]
        svd_dim = min(50, tfidf_matrix.shape[1] - 1, n_docs - 1)
        if svd_dim >= 2:
            svd = TruncatedSVD(n_components=svd_dim, random_state=42)
            features = svd.fit_transform(tfidf_matrix)
        else:
            features = tfidf_matrix.toarray()

        sim_matrix = cosine_similarity(features)
        upper_indices = np.triu_indices(sim_matrix.shape[0], k=1)
        sims = sim_matrix[upper_indices]
        if sims.size == 0:
            return pd.DataFrame(columns=['source', 'target', 'weight'])

        top = sims.argsort()[::-1][:top_k]
        rows = []
        for idx in top:
            i = int(upper_indices[0][idx])
            j = int(upper_indices[1][idx])
            rows.append({'source': i, 'target': j, 'weight': float(sims[idx])})

        return pd.DataFrame(rows)

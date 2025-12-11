"""
时间序列分析模块
用于分析绿电消费驱动-阻碍因素的时间演变规律
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')


class TemporalAnalyzer:
    """时间序列分析器"""

    def __init__(self):
        self.time_series_data = {}
        self.event_timeline = []

    def extract_time_from_documents(self, documents):
        """
        从文档中提取时间信息

        Args:
            documents: 文档列表，每个文档包含 'content' 和 'crawl_time' 字段

        Returns:
            带时间戳的文档数据
        """
        timed_docs = []

        for doc in documents:
            # 使用爬取时间作为基准时间
            crawl_time = doc.get('crawl_time', '')
            if crawl_time:
                try:
                    # 尝试解析时间戳
                    doc_time = pd.to_datetime(crawl_time)
                except:
                    # 如果解析失败，使用当前时间
                    doc_time = datetime.now()

                timed_doc = {
                    'content': doc.get('content', ''),
                    'title': doc.get('title', ''),
                    'url': doc.get('url', ''),
                    'timestamp': doc_time,
                    'year': doc_time.year,
                    'quarter': f"{doc_time.year}Q{(doc_time.month-1)//3 + 1}",
                    'month': f"{doc_time.year}-{doc_time.month:02d}"
                }
                timed_docs.append(timed_doc)

        return timed_docs

    def create_temporal_corpus(self, timed_documents, time_unit='month'):
        """
        创建按时序组织的语料库

        Args:
            timed_documents: 带时间戳的文档列表
            time_unit: 时间单位 ('day', 'month', 'quarter', 'year')

        Returns:
            按时间组织的语料库字典
        """
        temporal_corpus = defaultdict(list)

        for doc in timed_documents:
            if time_unit == 'day':
                time_key = doc['timestamp'].strftime('%Y-%m-%d')
            elif time_unit == 'month':
                time_key = doc['month']
            elif time_unit == 'quarter':
                time_key = doc['quarter']
            elif time_unit == 'year':
                time_key = str(doc['year'])
            else:
                time_key = doc['month']

            temporal_corpus[time_key].append(doc)

        return dict(temporal_corpus)

    def analyze_factor_evolution(self, temporal_corpus, factor_keywords):
        """
        分析因素强度的时间演变

        Args:
            temporal_corpus: 按时间组织的语料库
            factor_keywords: 因素关键词字典 {factor_name: [keywords]}

        Returns:
            因素演变时间序列数据
        """
        evolution_data = {}

        # 获取时间排序
        time_periods = sorted(temporal_corpus.keys())

        for factor_name, keywords in factor_keywords.items():
            factor_series = []

            for time_period in time_periods:
                docs = temporal_corpus[time_period]
                total_docs = len(docs)
                if total_docs == 0:
                    factor_series.append(0)
                    continue

                # 计算该时间段内提及该因素的文档数量
                mention_count = 0
                total_mentions = 0

                for doc in docs:
                    content = (doc.get('title', '') + ' ' + doc.get('content', '')).lower()
                    keyword_count = sum(1 for keyword in keywords if keyword.lower() in content)

                    if keyword_count > 0:
                        mention_count += 1
                        total_mentions += keyword_count

                # 计算覆盖率（提及该因素的文档比例）和强度（平均提及次数）
                coverage = mention_count / total_docs
                intensity = total_mentions / total_docs if total_docs > 0 else 0

                factor_series.append({
                    'time': time_period,
                    'coverage': coverage,
                    'intensity': intensity,
                    'mention_count': mention_count,
                    'total_docs': total_docs
                })

            evolution_data[factor_name] = factor_series

        return evolution_data, time_periods

    def detect_sentiment_trends(self, temporal_corpus, sentiment_analyzer):
        """
        检测情感倾向的时间趋势

        Args:
            temporal_corpus: 按时间组织的语料库
            sentiment_analyzer: 情感分析器

        Returns:
            情感演变数据
        """
        sentiment_evolution = {}
        time_periods = sorted(temporal_corpus.keys())

        for time_period in time_periods:
            docs = temporal_corpus[time_period]
            sentiment_scores = []

            for doc in docs:
                content = doc.get('title', '') + ' ' + doc.get('content', '')
                if sentiment_analyzer:
                    score = sentiment_analyzer.analyze(content)
                    sentiment_scores.append(score)

            if sentiment_scores:
                sentiment_evolution[time_period] = {
                    'mean_sentiment': np.mean(sentiment_scores),
                    'median_sentiment': np.median(sentiment_scores),
                    'std_sentiment': np.std(sentiment_scores),
                    'pos_ratio': sum(1 for s in sentiment_scores if s > 0.6) / len(sentiment_scores),
                    'neg_ratio': sum(1 for s in sentiment_scores if s < 0.4) / len(sentiment_scores),
                    'neu_ratio': sum(1 for s in sentiment_scores if 0.4 <= s <= 0.6) / len(sentiment_scores),
                    'doc_count': len(sentiment_scores)
                }
            else:
                sentiment_evolution[time_period] = {
                    'mean_sentiment': 0,
                    'median_sentiment': 0,
                    'std_sentiment': 0,
                    'pos_ratio': 0,
                    'neg_ratio': 0,
                    'neu_ratio': 0,
                    'doc_count': 0
                }

        return sentiment_evolution

    def extract_policy_events(self, documents, policy_keywords):
        """
        提取政策事件时间线

        Args:
            documents: 文档列表
            policy_keywords: 政策相关关键词

        Returns:
            政策事件时间线
        """
        policy_events = []

        for doc in documents:
            content = (doc.get('title', '') + ' ' + doc.get('content', '')).lower()

            # 检查是否包含政策关键词
            policy_mentions = [kw for kw in policy_keywords if kw.lower() in content]

            if policy_mentions:
                # 尝试从内容中提取具体政策信息
                policy_event = self._extract_policy_details(doc, policy_mentions)
                if policy_event:
                    policy_events.append(policy_event)

        # 按时间排序
        policy_events.sort(key=lambda x: x['timestamp'])

        return policy_events

    def _extract_policy_details(self, doc, policy_mentions):
        """提取政策事件详情"""
        content = doc.get('title', '') + ' ' + doc.get('content', '')

        # 简单的政策类型识别
        policy_type = 'unknown'
        if any(kw in content for kw in ['补贴', 'subsidy']):
            policy_type = 'subsidy'
        elif any(kw in content for kw in ['配额', 'quota']):
            policy_type = 'quota'
        elif any(kw in content for kw in ['税收', 'tax']):
            policy_type = 'tax'
        elif any(kw in content for kw in ['交易', 'trading']):
            policy_type = 'trading'
        elif any(kw in content for kw in ['规划', 'plan']):
            policy_type = 'plan'

        return {
            'timestamp': doc.get('timestamp', datetime.now()),
            'title': doc.get('title', ''),
            'url': doc.get('url', ''),
            'policy_type': policy_type,
            'mentions': policy_mentions,
            'content_length': len(content)
        }

    def compute_event_impact(self, sentiment_data, factor_data, event_date, window_days=30):
        """
        计算事件对情感和因素的影响

        Args:
            sentiment_data: 情感时间序列数据
            factor_data: 因素时间序列数据
            event_date: 事件日期
            window_days: 分析窗口天数

        Returns:
            事件影响分析结果
        """
        # 转换事件日期为datetime
        if isinstance(event_date, str):
            event_date = pd.to_datetime(event_date)

        # 定义事件前后的时间窗口
        pre_window = timedelta(days=window_days)
        post_window = timedelta(days=window_days)

        # 计算事件前后的平均情感和因素强度
        pre_sentiment = []
        post_sentiment = []
        pre_factor_intensity = defaultdict(list)
        post_factor_intensity = defaultdict(list)

        for time_period, sentiment_info in sentiment_data.items():
            try:
                period_date = pd.to_datetime(time_period)
                period_sentiment = sentiment_info.get('mean_sentiment', 0)

                if period_date < event_date and (event_date - period_date) <= pre_window:
                    pre_sentiment.append(period_sentiment)
                elif period_date > event_date and (period_date - event_date) <= post_window:
                    post_sentiment.append(period_sentiment)
            except:
                continue

        # 分析因素变化
        for factor_name, factor_series in factor_data.items():
            for data_point in factor_series:
                try:
                    point_date = pd.to_datetime(data_point['time'])
                    intensity = data_point.get('intensity', 0)

                    if point_date < event_date and (event_date - point_date) <= pre_window:
                        pre_factor_intensity[factor_name].append(intensity)
                    elif point_date > event_date and (point_date - event_date) <= post_window:
                        post_factor_intensity[factor_name].append(intensity)
                except:
                    continue

        # 计算变化统计
        impact_analysis = {
            'event_date': event_date,
            'sentiment_change': self._compute_change(pre_sentiment, post_sentiment),
            'factor_changes': {}
        }

        for factor_name in pre_factor_intensity.keys():
            pre_values = pre_factor_intensity.get(factor_name, [])
            post_values = post_factor_intensity.get(factor_name, [])
            impact_analysis['factor_changes'][factor_name] = self._compute_change(pre_values, post_values)

        return impact_analysis

    def _compute_change(self, pre_values, post_values):
        """计算前后变化"""
        if not pre_values or not post_values:
            return {
                'pre_mean': 0,
                'post_mean': 0,
                'absolute_change': 0,
                'relative_change': 0,
                'significance': 'insufficient_data'
            }

        pre_mean = np.mean(pre_values)
        post_mean = np.mean(post_values)
        absolute_change = post_mean - pre_mean
        relative_change = (absolute_change / pre_mean * 100) if pre_mean != 0 else float('inf')

        # 简单的显著性检验
        if len(pre_values) >= 3 and len(post_values) >= 3:
            _, p_value = stats.ttest_ind(pre_values, post_values)
            significance = 'significant' if p_value < 0.05 else 'not_significant'
        else:
            significance = 'insufficient_sample'

        return {
            'pre_mean': pre_mean,
            'post_mean': post_mean,
            'absolute_change': absolute_change,
            'relative_change': relative_change,
            'significance': significance
        }

    def create_temporal_heatmap(self, evolution_data, time_periods):
        """
        创建时间演变热力图数据

        Args:
            evolution_data: 因素演变数据
            time_periods: 时间周期列表

        Returns:
            热力图数据矩阵
        """
        # 创建数据矩阵
        factors = list(evolution_data.keys())
        matrix_data = []

        for factor_name in factors:
            factor_series = evolution_data[factor_name]
            row_data = []

            for time_period in time_periods:
                # 找到对应时间点的数据
                intensity_value = 0
                for data_point in factor_series:
                    if data_point['time'] == time_period:
                        intensity_value = data_point['intensity']
                        break
                row_data.append(intensity_value)

            matrix_data.append(row_data)

        return pd.DataFrame(matrix_data, index=factors, columns=time_periods)

    def detect_trend_patterns(self, time_series_data):
        """
        检测时间序列的趋势模式

        Args:
            time_series_data: 时间序列数据

        Returns:
            趋势模式分析结果
        """
        trend_patterns = {}

        for factor_name, series_data in time_series_data.items():
            if len(series_data) < 3:
                continue

            # 提取强度值
            values = [point.get('intensity', 0) for point in series_data]
            time_points = list(range(len(values)))

            # 线性趋势分析
            slope, intercept, r_value, p_value, std_err = stats.linregress(time_points, values)

            # 趋势分类
            if p_value < 0.05:  # 显著趋势
                if slope > 0.01:
                    trend_type = 'strong_increasing'
                elif slope > 0:
                    trend_type = 'weak_increasing'
                elif slope < -0.01:
                    trend_type = 'strong_decreasing'
                else:
                    trend_type = 'weak_decreasing'
            else:
                trend_type = 'no_clear_trend'

            # 检测周期性模式（简单方法）
            if len(values) >= 6:
                # 计算自相关
                autocorr = [np.corrcoef(values[:-i], values[i:])[0,1] for i in range(1, len(values)//2)]
                max_autocorr = max(autocorr) if autocorr else 0
                cyclic_pattern = max_autocorr > 0.3
            else:
                cyclic_pattern = False

            trend_patterns[factor_name] = {
                'trend_type': trend_type,
                'slope': slope,
                'r_squared': r_value ** 2,
                'p_value': p_value,
                'cyclic_pattern': cyclic_pattern,
                'trend_strength': abs(r_value)
            }

        return trend_patterns

    def generate_temporal_summary(self, evolution_data, sentiment_data, policy_events):
        """
        生成时间分析摘要报告

        Args:
            evolution_data: 因素演变数据
            sentiment_data: 情感演变数据
            policy_events: 政策事件时间线

        Returns:
            时间分析摘要
        """
        summary = {
            'time_span': {},
            'key_trends': {},
            'policy_impacts': {},
            'sentiment_evolution': {}
        }

        # 时间跨度分析
        if evolution_data:
            all_time_periods = set()
            for factor_data in evolution_data.values():
                all_time_periods.update([point['time'] for point in factor_data])

            if all_time_periods:
                sorted_periods = sorted(list(all_time_periods))
                summary['time_span'] = {
                    'start_period': sorted_periods[0],
                    'end_period': sorted_periods[-1],
                    'total_periods': len(sorted_periods)
                }

        # 关键趋势分析
        if evolution_data:
            trend_patterns = self.detect_trend_patterns(evolution_data)
            summary['key_trends'] = {
                'increasing_factors': [k for k, v in trend_patterns.items() if 'increasing' in v['trend_type']],
                'decreasing_factors': [k for k, v in trend_patterns.items() if 'decreasing' in v['trend_type']],
                'stable_factors': [k for k, v in trend_patterns.items() if v['trend_type'] == 'no_clear_trend']
            }

        # 情感演变摘要
        if sentiment_data:
            sentiment_values = [data.get('mean_sentiment', 0) for data in sentiment_data.values()]
            if sentiment_values:
                summary['sentiment_evolution'] = {
                    'overall_trend': 'improving' if sentiment_values[-1] > sentiment_values[0] else 'declining',
                    'average_sentiment': np.mean(sentiment_values),
                    'sentiment_volatility': np.std(sentiment_values),
                    'most_positive_period': max(sentiment_data.items(), key=lambda x: x[1].get('mean_sentiment', 0))[0],
                    'most_negative_period': min(sentiment_data.items(), key=lambda x: x[1].get('mean_sentiment', 1))[0]
                }

        # 政策影响摘要
        if policy_events and evolution_data:
            policy_impacts = []
            for event in policy_events[-5:]:  # 最近5个政策事件
                event_date = event['timestamp']
                impact = self.compute_event_impact(sentiment_data, evolution_data, event_date, window_days=15)
                policy_impacts.append({
                    'event': event['title'],
                    'date': event_date,
                    'impact_summary': impact
                })
            summary['policy_impacts'] = policy_impacts

        return summary
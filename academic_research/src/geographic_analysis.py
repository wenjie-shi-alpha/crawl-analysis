"""
地理空间分析模块
用于分析中国绿电消费的地理分布特征和区域差异
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict, Counter
import re
import jieba
import jieba.posseg as pseg
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


# 中国省份列表及其所属区域
CHINA_PROVINCES = {
    '华北': ['北京', '天津', '河北', '山西', '内蒙古'],
    '东北': ['辽宁', '吉林', '黑龙江'],
    '华东': ['上海', '江苏', '浙江', '安徽', '福建', '江西', '山东'],
    '华中': ['河南', '湖北', '湖南'],
    '华南': ['广东', '广西', '海南'],
    '西南': ['重庆', '四川', '贵州', '云南', '西藏'],
    '西北': ['陕西', '甘肃', '青海', '宁夏', '新疆']
}

# 省份经济水平分类
PROVINCE_ECONOMIC_LEVEL = {
    '发达地区': ['北京', '上海', '广东', '江苏', '浙江', '天津', '福建'],
    '发展中地区': ['山东', '河北', '河南', '湖北', '湖南', '安徽', '江西', '四川', '重庆'],
    '欠发达地区': ['山西', '内蒙古', '辽宁', '吉林', '黑龙江', '广西', '海南', '贵州', '云南',
                    '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆']
}


class GeographicAnalyzer:
    """地理空间分析器"""

    def __init__(self):
        self.province_pattern = self._build_province_pattern()
        self.region_mapping = self._build_region_mapping()

    def _build_province_pattern(self):
        """构建省份识别正则表达式"""
        provinces = []
        for region_provinces in CHINA_PROVINCES.values():
            provinces.extend(region_provinces)

        # 构建正则模式，考虑省份的多种表达方式
        province_patterns = []
        for province in provinces:
            # 添加省份名称和简称
            patterns = [province]
            if province == '内蒙古':
                patterns.extend(['内蒙'])
            elif province == '黑龙江':
                patterns.extend(['黑龙江'])
            elif province == '西藏':
                patterns.extend(['藏'])
            else:
                # 其他省份的简称
                short_name = province[0]
                patterns.extend([short_name + '省', short_name])

            province_patterns.extend(patterns)

        return '|'.join(province_patterns)

    def _build_region_mapping(self):
        """构建区域映射"""
        mapping = {}
        for region, provinces in CHINA_PROVINCES.items():
            for province in provinces:
                mapping[province] = region
        return mapping

    def extract_geographic_entities(self, documents):
        """
        从文档中提取地理实体

        Args:
            documents: 文档列表

        Returns:
            包含地理信息的文档数据
        """
        geo_documents = []

        for doc in documents:
            content = (doc.get('title', '') + ' ' + doc.get('content', ''))

            # 提取省份信息
            provinces_mentioned = self._extract_provinces(content)
            regions_mentioned = self._extract_regions(provinces_mentioned)

            # 提取城市信息（如果有）
            cities_mentioned = self._extract_cities(content)

            # 地理丰富度评分
            geo_richness_score = self._calculate_geo_richness(content, provinces_mentioned, cities_mentioned)

            geo_doc = {
                'original_doc': doc,
                'provinces': provinces_mentioned,
                'regions': regions_mentioned,
                'cities': cities_mentioned,
                'geo_richness_score': geo_richness_score,
                'has_geo_info': len(provinces_mentioned) > 0 or len(cities_mentioned) > 0
            }

            geo_documents.append(geo_doc)

        return geo_documents

    def _extract_provinces(self, text):
        """提取文本中提到的省份"""
        provinces_found = []
        text_lower = text.lower()

        for province in self.province_pattern.split('|'):
            if province and len(province) > 1 and province in text:
                provinces_found.append(province)

        return list(set(provinces_found))

    def _extract_regions(self, provinces):
        """根据省份提取所属区域"""
        regions_found = []
        for province in provinces:
            region = self.region_mapping.get(province)
            if region and region not in regions_found:
                regions_found.append(region)
        return regions_found

    def _extract_cities(self, text):
        """提取文本中提到的城市（简化版本）"""
        # 这里可以扩展更详细的城市列表
        major_cities = [
            '北京', '上海', '广州', '深圳', '天津', '重庆', '成都', '武汉', '西安', '南京',
            '杭州', '苏州', '青岛', '大连', '宁波', '厦门', '长沙', '郑州', '济南', '福州'
        ]

        cities_found = [city for city in major_cities if city in text]
        return list(set(cities_found))

    def _calculate_geo_richness(self, text, provinces, cities):
        """计算地理信息丰富度评分"""
        geo_count = len(provinces) + len(cities)
        text_length = len(text)

        # 标准化评分：地理实体数量 / 文本长度（千字符）
        if text_length > 0:
            return (geo_count / text_length * 1000)
        return 0

    def analyze_geographic_distribution(self, geo_documents):
        """
        分析地理分布特征

        Args:
            geo_documents: 包含地理信息的文档列表

        Returns:
            地理分布分析结果
        """
        distribution_analysis = {
            'province_distribution': defaultdict(int),
            'region_distribution': defaultdict(int),
            'economic_level_distribution': defaultdict(int),
            'multi_province_docs': 0,
            'cross_region_docs': 0
        }

        total_geo_docs = 0

        for geo_doc in geo_documents:
            if not geo_doc['has_geo_info']:
                continue

            total_geo_docs += 1
            provinces = geo_doc['provinces']
            regions = geo_doc['regions']

            # 统计省份分布
            for province in provinces:
                distribution_analysis['province_distribution'][province] += 1

            # 统计区域分布
            for region in regions:
                distribution_analysis['region_distribution'][region] += 1

            # 统计跨省份文档
            if len(provinces) > 1:
                distribution_analysis['multi_province_docs'] += 1

            # 统计跨区域文档
            if len(regions) > 1:
                distribution_analysis['cross_region_docs'] += 1

        # 计算经济水平分布
        for province, count in distribution_analysis['province_distribution'].items():
            for level, provinces in PROVINCE_ECONOMIC_LEVEL.items():
                if province in provinces:
                    distribution_analysis['economic_level_distribution'][level] += count
                    break

        # 计算比例
        if total_geo_docs > 0:
            distribution_analysis['geo_doc_ratio'] = total_geo_docs / len(geo_documents)
            distribution_analysis['multi_province_ratio'] = distribution_analysis['multi_province_docs'] / total_geo_docs
            distribution_analysis['cross_region_ratio'] = distribution_analysis['cross_region_docs'] / total_geo_docs

        return distribution_analysis

    def compute_regional_factor_profiles(self, geo_documents, factor_keywords):
        """
        计算各地区的因素特征画像

        Args:
            geo_documents: 包含地理信息的文档列表
            factor_keywords: 因素关键词字典

        Returns:
            地区因素画像
        """
        regional_profiles = {}

        # 按地区分组文档
        regional_docs = defaultdict(list)
        for geo_doc in geo_documents:
            for region in geo_doc['regions']:
                regional_docs[region].append(geo_doc['original_doc'])

        # 为每个地区计算因素特征
        for region, docs in regional_docs.items():
            if not docs:
                continue

            profile = {
                'doc_count': len(docs),
                'factor_intensity': {},
                'total_mentions': 0
            }

            # 计算每个因素的强度
            for factor_name, keywords in factor_keywords.items():
                factor_mentions = 0
                total_content_length = 0

                for doc in docs:
                    content = (doc.get('title', '') + ' ' + doc.get('content', '')).lower()
                    total_content_length += len(content)

                    # 计算关键词提及次数
                    for keyword in keywords:
                        factor_mentions += content.count(keyword.lower())

                # 标准化强度（每千字符的提及次数）
                if total_content_length > 0:
                    intensity = (factor_mentions / total_content_length) * 1000
                else:
                    intensity = 0

                profile['factor_intensity'][factor_name] = intensity
                profile['total_mentions'] += factor_mentions

            # 标准化强度值
            if profile['total_mentions'] > 0:
                max_intensity = max(profile['factor_intensity'].values()) if profile['factor_intensity'] else 1
                for factor in profile['factor_intensity']:
                    profile['factor_intensity'][factor] /= max_intensity

            regional_profiles[region] = profile

        return regional_profiles

    def identify_regional_specializations(self, regional_profiles, factor_keywords):
        """
        识别各地区专业化特征

        Args:
            regional_profiles: 地区因素画像
            factor_keywords: 因素关键词

        Returns:
            地区专业化特征
        """
        specializations = {}

        for region, profile in regional_profiles.items():
            factor_intensities = profile['factor_intensity']

            if not factor_intensities:
                continue

            # 找出该地区最突出的因素
            sorted_factors = sorted(factor_intensities.items(), key=lambda x: x[1], reverse=True)
            top_factors = sorted_factors[:3]  # 取前3个

            # 计算专业化指数（相对于其他地区的差异）
            specialization_scores = {}
            for factor_name, intensity in factor_intensities.items():
                # 计算该因素在所有地区的平均强度
                all_region_intensities = [
                    regional_profiles[r]['factor_intensity'].get(factor_name, 0)
                    for r in regional_profiles
                ]
                avg_intensity = np.mean(all_region_intensities) if all_region_intensities else 0

                # 专业化指数 = (地区强度 - 平均强度) / 平均强度
                if avg_intensity > 0:
                    specialization_score = (intensity - avg_intensity) / avg_intensity
                else:
                    specialization_score = intensity

                specialization_scores[factor_name] = specialization_score

            # 识别最专业化的因素
            sorted_specializations = sorted(specialization_scores.items(), key=lambda x: x[1], reverse=True)

            specializations[region] = {
                'dominant_factors': top_factors,
                'specialization_ranking': sorted_specializations,
                'most_specialized': sorted_specializations[0] if sorted_specializations else None,
                'profile_diversity': len([f for f, i in factor_intensities.items() if i > 0.1])
            }

        return specializations

    def analyze_interregional_connections(self, geo_documents):
        """
        分析区域间联系

        Args:
            geo_documents: 包含地理信息的文档列表

        Returns:
            区域间联系分析
        """
        connection_matrix = defaultdict(lambda: defaultdict(int))
        co_occurrence_data = []

        for geo_doc in geo_documents:
            if not geo_doc['has_geo_info']:
                continue

            regions = geo_doc['regions']
            provinces = geo_doc['provinces']

            # 记录区域共现
            if len(regions) > 1:
                for i, region1 in enumerate(regions):
                    for j, region2 in enumerate(regions):
                        if i != j:
                            connection_matrix[region1][region2] += 1

                co_occurrence_data.append({
                    'regions': regions,
                    'provinces': provinces,
                    'doc_title': geo_doc['original_doc'].get('title', ''),
                    'connection_strength': len(regions) * len(provinces)
                })

        # 计算连接强度指标
        connection_strength = {}
        for region1 in connection_matrix:
            for region2 in connection_matrix[region1]:
                if region1 != region2:
                    pair = tuple(sorted([region1, region2]))
                    if pair not in connection_strength:
                        connection_strength[pair] = 0
                    connection_strength[pair] += connection_matrix[region1][region2]

        # 排序连接强度
        sorted_connections = sorted(connection_strength.items(), key=lambda x: x[1], reverse=True)

        return {
            'connection_matrix': dict(connection_matrix),
            'connection_strength': dict(sorted_connections),
            'co_occurrence_examples': co_occurrence_data[:10],  # 前10个例子
            'top_connections': sorted_connections[:5],  # 前5个最强连接
            'total_interregional_docs': len(co_occurrence_data)
        }

    def create_geographic_summary(self, distribution_analysis, regional_profiles,
                                regional_specializations, interregional_connections):
        """
        创建地理分析摘要

        Args:
            distribution_analysis: 地理分布分析
            regional_profiles: 地区因素画像
            regional_specializations: 地区专业化特征
            interregional_connections: 区域间联系

        Returns:
            地理分析摘要报告
        """
        summary = {
            'geographic_coverage': {},
            'regional_highlights': {},
            'specialization_patterns': {},
            'connectivity_insights': {}
        }

        # 地理覆盖度摘要
        if distribution_analysis:
            summary['geographic_coverage'] = {
                'total_provinces_mentioned': len(distribution_analysis.get('province_distribution', {})),
                'total_regions_mentioned': len(distribution_analysis.get('region_distribution', {})),
                'most_mentioned_province': max(distribution_analysis.get('province_distribution', {}).items(), key=lambda x: x[1])[0] if distribution_analysis.get('province_distribution') else None,
                'most_mentioned_region': max(distribution_analysis.get('region_distribution', {}).items(), key=lambda x: x[1])[0] if distribution_analysis.get('region_distribution') else None,
                'geo_document_ratio': distribution_analysis.get('geo_doc_ratio', 0),
                'cross_regional_focus': distribution_analysis.get('cross_region_ratio', 0)
            }

        # 地区亮点摘要
        if regional_profiles:
            summary['regional_highlights'] = {}
            for region, profile in regional_profiles.items():
                summary['regional_highlights'][region] = {
                    'doc_count': profile['doc_count'],
                    'key_factors': sorted(profile['factor_intensity'].items(), key=lambda x: x[1], reverse=True)[:3],
                    'total_factor_engagement': sum(profile['factor_intensity'].values())
                }

        # 专业化模式摘要
        if regional_specializations:
            summary['specialization_patterns'] = {}
            for region, specialization in regional_specializations.items():
                most_specialized = specialization.get('most_specialized')
                if most_specialized:
                    summary['specialization_patterns'][region] = {
                        'signature_factor': most_specialized[0],
                        'specialization_strength': most_specialized[1],
                        'factor_diversity': specialization.get('profile_diversity', 0)
                    }

        # 连通性洞察摘要
        if interregional_connections:
            top_connection = interregional_connections.get('top_connections', [])
            if top_connection:
                summary['connectivity_insights'] = {
                    'strongest_connection': top_connection[0][0] if top_connection else None,
                    'connection_strength': top_connection[0][1] if top_connection else 0,
                    'total_interregional_discussions': interregional_connections.get('total_interregional_docs', 0),
                    'regional_collaboration_level': 'high' if interregional_connections.get('total_interregional_docs', 0) > 50 else 'medium' if interregional_connections.get('total_interregional_docs', 0) > 20 else 'low'
                }

        return summary

    def generate_geographic_insights(self, geo_summary):
        """
        生成地理分析洞察

        Args:
            geo_summary: 地理分析摘要

        Returns:
            地理分析洞察列表
        """
        insights = []

        # 地理覆盖度洞察
        coverage = geo_summary.get('geographic_coverage', {})
        if coverage.get('geo_document_ratio', 0) > 0.7:
            insights.append({
                'type': 'coverage',
                'insight': f"研究具有很高的地理覆盖度，{coverage.get('total_provinces_mentioned', 0)}个省份和{coverage.get('total_regions_mentioned', 0)}个区域都被提及",
                'significance': 'high'
            })

        # 区域专业化洞察
        specializations = geo_summary.get('specialization_patterns', {})
        for region, pattern in specializations.items():
            if pattern.get('specialization_strength', 0) > 0.5:
                insights.append({
                    'type': 'specialization',
                    'insight': f"{region}地区在{pattern.get('signature_factor', '未知因素')}方面表现出明显专业化特征",
                    'significance': 'medium',
                    'region': region
                })

        # 连通性洞察
        connectivity = geo_summary.get('connectivity_insights', {})
        if connectivity.get('regional_collaboration_level') == 'high':
            insights.append({
                'type': 'connectivity',
                'insight': f"研究显示区域间存在强协作关系，特别是{connectivity.get('strongest_connection', '未知区域对')}之间的联系最为紧密",
                'significance': 'high'
            })

        return insights
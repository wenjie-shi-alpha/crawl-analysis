"""
高级统计分析模块
为绿电消费研究提供深度统计分析和建模能力
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import pdist, squareform
from sklearn.decomposition import FactorAnalysis, PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
import networkx as nx
from collections import defaultdict, Counter
import warnings
warnings.filterwarnings('ignore')


class AdvancedStatistics:
    """高级统计分析类"""

    def __init__(self, corpus_data=None):
        """
        初始化统计分析器

        Args:
            corpus_data: 包含文档数据的列表，每个元素是字典格式
        """
        self.corpus_data = corpus_data or []
        self.scaler = StandardScaler()

    def compute_correlation_matrix(self, factor_data):
        """
        计算驱动-阻碍因素间的相关系数矩阵

        Args:
            factor_data: 因素数据字典 {factor_name: [values]}

        Returns:
            相关系数矩阵和p值矩阵
        """
        if not factor_data:
            return None, None

        df = pd.DataFrame(factor_data)

        # 计算皮尔逊相关系数
        corr_matrix = df.corr(method='pearson')

        # 计算p值
        p_values = pd.DataFrame(index=corr_matrix.index, columns=corr_matrix.columns)

        for i in range(len(corr_matrix.columns)):
            for j in range(len(corr_matrix.columns)):
                if i <= j:
                    _, p_val = stats.pearsonr(
                        df.iloc[:, i].dropna(),
                        df.iloc[:, j].dropna()
                    )
                    p_values.iloc[i, j] = p_val
                    p_values.iloc[j, i] = p_val

        return corr_matrix, p_values

    def perform_factor_analysis(self, factor_data, n_factors=5):
        """
        执行因子分析以识别潜在的潜在因子

        Args:
            factor_data: 因素数据字典
            n_factors: 要提取的因子数量

        Returns:
            因子载荷矩阵、解释方差比例等
        """
        if not factor_data:
            return None

        df = pd.DataFrame(factor_data).dropna()

        # 标准化数据
        scaled_data = self.scaler.fit_transform(df)

        # 执行因子分析
        fa = FactorAnalysis(n_components=n_factors, random_state=42)
        factor_loadings = fa.fit_transform(scaled_data)

        # 计算因子载荷矩阵
        loadings_matrix = pd.DataFrame(
            fa.components_.T,
            index=df.columns,
            columns=[f'Factor_{i+1}' for i in range(n_factors)]
        )

        # 计算每个因子的解释方差
        explained_variance = fa.noise_variance_
        total_variance = np.var(scaled_data, axis=0).sum()
        explained_variance_ratio = 1 - (explained_variance / total_variance)

        return {
            'loadings_matrix': loadings_matrix,
            'factor_scores': factor_loadings,
            'explained_variance_ratio': explained_variance_ratio,
            'communalities': 1 - fa.noise_variance_
        }

    def regression_analysis(self, X_data, y_data, model_type='linear'):
        """
        执行回归分析

        Args:
            X_data: 自变量数据
            y_data: 因变量数据
            model_type: 回归类型 ('linear', 'logistic', 'random_forest')

        Returns:
            回归结果和模型评估指标
        """
        if not X_data or not y_data:
            return None

        # 准备数据
        X = np.array(X_data).reshape(-1, 1) if len(np.array(X_data).shape) == 1 else np.array(X_data)
        y = np.array(y_data)

        # 划分训练测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # 选择模型
        if model_type == 'linear':
            model = LinearRegression()
        elif model_type == 'logistic':
            model = LogisticRegression(random_state=42)
        elif model_type == 'random_forest':
            model = RandomForestRegressor(n_estimators=100, random_state=42)
        else:
            return None

        # 训练模型
        model.fit(X_train, y_train)

        # 预测和评估
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)

        # 交叉验证
        cv_scores = cross_val_score(model, X, y, cv=5)

        results = {
            'model': model,
            'train_score': train_score,
            'test_score': test_score,
            'cv_scores': cv_scores,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std()
        }

        # 对于线性模型，添加系数信息
        if model_type in ['linear', 'logistic'] and hasattr(model, 'coef_'):
            results['coefficients'] = model.coef_
            results['intercept'] = model.intercept_

        # 对于随机森林，添加特征重要性
        if model_type == 'random_forest' and hasattr(model, 'feature_importances_'):
            results['feature_importance'] = model.feature_importances_

        return results

    def hierarchical_clustering(self, factor_data, n_clusters=5):
        """
        执行层次聚类分析

        Args:
            factor_data: 因素数据字典
            n_clusters: 聚类数量

        Returns:
            聚类结果和树状图数据
        """
        if not factor_data:
            return None

        df = pd.DataFrame(factor_data).dropna()

        # 标准化数据
        scaled_data = self.scaler.fit_transform(df)

        # 计算距离矩阵
        distance_matrix = pdist(scaled_data, metric='euclidean')

        # 层次聚类
        linkage_matrix = linkage(distance_matrix, method='ward')

        # 获取聚类标签
        cluster_labels = fcluster(linkage_matrix, n_clusters, criterion='maxclust')

        # 计算轮廓系数
        silhouette_avg = silhouette_score(scaled_data, cluster_labels)

        return {
            'linkage_matrix': linkage_matrix,
            'cluster_labels': cluster_labels,
            'silhouette_score': silhouette_avg,
            'data_labels': dict(zip(df.index, cluster_labels))
        }

    def significance_testing(self, group1_data, group2_data, test_type='ttest'):
        """
        执行显著性检验

        Args:
            group1_data: 第一组数据
            group2_data: 第二组数据
            test_type: 检验类型 ('ttest', 'mannwhitney', 'chi2')

        Returns:
            检验统计量和p值
        """
        if not group1_data or not group2_data:
            return None

        group1 = np.array(group1_data)
        group2 = np.array(group2_data)

        if test_type == 'ttest':
            # 独立样本t检验
            statistic, p_value = stats.ttest_ind(group1, group2)
        elif test_type == 'mannwhitney':
            # Mann-Whitney U检验
            statistic, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
        elif test_type == 'chi2':
            # 卡方检验
            # 需要将数据转换为频数表
            contingency_table = pd.crosstab(group1, group2)
            statistic, p_value, _, _ = stats.chi2_contingency(contingency_table)
        else:
            return None

        return {
            'test_type': test_type,
            'statistic': statistic,
            'p_value': p_value,
            'significant': p_value < 0.05
        }

    def time_series_trend_analysis(self, time_series_data):
        """
        时间序列趋势分析

        Args:
            time_series_data: 时间序列数据 {time_point: value}

        Returns:
            趋势分析结果
        """
        if not time_series_data:
            return None

        # 转换为DataFrame
        df = pd.DataFrame(list(time_series_data.items()), columns=['time', 'value'])
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time')

        # 计算趋势
        x = np.arange(len(df))
        y = df['value'].values

        # 线性回归分析趋势
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # 计算移动平均
        window_size = min(3, len(df) // 2)  # 确保窗口大小合理
        df['moving_avg'] = df['value'].rolling(window=window_size).mean()

        # 趋势分类
        trend_direction = 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
        trend_strength = 'strong' if abs(r_value) > 0.7 else 'moderate' if abs(r_value) > 0.3 else 'weak'

        return {
            'slope': slope,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'trend_direction': trend_direction,
            'trend_strength': trend_strength,
            'data_with_trend': df,
            'moving_avg': df['moving_avg'].tolist()
        }

    def effect_size_analysis(self, group1_data, group2_data):
        """
        效应大小分析

        Args:
            group1_data: 第一组数据
            group2_data: 第二组数据

        Returns:
            效应大小指标
        """
        if not group1_data or not group2_data:
            return None

        group1 = np.array(group1_data)
        group2 = np.array(group2_data)

        # Cohen's d
        pooled_std = np.sqrt(((len(group1) - 1) * np.var(group1, ddof=1) +
                              (len(group2) - 1) * np.var(group2, ddof=1)) /
                             (len(group1) + len(group2) - 2))
        cohens_d = (np.mean(group1) - np.mean(group2)) / pooled_std

        # 效应大小解释
        if abs(cohens_d) < 0.2:
            effect_interpretation = 'negligible'
        elif abs(cohens_d) < 0.5:
            effect_interpretation = 'small'
        elif abs(cohens_d) < 0.8:
            effect_interpretation = 'medium'
        else:
            effect_interpretation = 'large'

        return {
            'cohens_d': cohens_d,
            'effect_interpretation': effect_interpretation,
            'group1_mean': np.mean(group1),
            'group2_mean': np.mean(group2),
            'group1_std': np.std(group1, ddof=1),
            'group2_std': np.std(group2, ddof=1)
        }

    def reliability_analysis(self, scale_data):
        """
        信度分析（Cronbach's Alpha）

        Args:
            scale_data: 量表数据，每个变量为一列

        Returns:
            Cronbach's Alpha和各项目分析
        """
        if not scale_data:
            return None

        df = pd.DataFrame(scale_data).dropna()

        # 计算Cronbach's Alpha
        n_items = df.shape[1]
        item_variances = df.var(axis=0, ddof=1)
        total_variance = df.sum(axis=1).var(ddof=1)

        cronbach_alpha = (n_items / (n_items - 1)) * (1 - item_variances.sum() / total_variance)

        # 删除每个项目后的Alpha值
        alpha_if_deleted = {}
        for item in df.columns:
            items_without = df.drop(item, axis=1)
            n_items_without = items_without.shape[1]

            if n_items_without > 1:
                item_variances_without = items_without.var(axis=0, ddof=1)
                total_variance_without = items_without.sum(axis=1).var(ddof=1)
                alpha_without = (n_items_without / (n_items_without - 1)) * (1 - item_variances_without.sum() / total_variance_without)
                alpha_if_deleted[item] = alpha_without
            else:
                alpha_if_deleted[item] = cronbach_alpha

        return {
            'cronbach_alpha': cronbach_alpha,
            'alpha_if_deleted': alpha_if_deleted,
            'n_items': n_items,
            'interpretation': self._interpret_reliability(cronbach_alpha)
        }

    def _interpret_reliability(self, alpha):
        """解释信度水平"""
        if alpha >= 0.9:
            return 'Excellent'
        elif alpha >= 0.8:
            return 'Good'
        elif alpha >= 0.7:
            return 'Acceptable'
        elif alpha >= 0.6:
            return 'Questionable'
        elif alpha >= 0.5:
            return 'Poor'
        else:
            return 'Unacceptable'

    def create_statistical_summary(self, data_dict):
        """
        创建统计摘要

        Args:
            data_dict: 数据字典 {variable_name: [values]}

        Returns:
            统计摘要DataFrame
        """
        if not data_dict:
            return None

        summary_stats = []

        for var_name, values in data_dict.items():
            if values:
                values_array = np.array(values)
                stats_dict = {
                    'Variable': var_name,
                    'N': len(values),
                    'Mean': np.mean(values_array),
                    'Median': np.median(values_array),
                    'Std': np.std(values_array, ddof=1),
                    'Min': np.min(values_array),
                    'Max': np.max(values_array),
                    'Skewness': stats.skew(values_array),
                    'Kurtosis': stats.kurtosis(values_array),
                    'Missing': sum(np.isnan(values_array))
                }
                summary_stats.append(stats_dict)

        return pd.DataFrame(summary_stats)


class CausalInference:
    """因果推断分析类"""

    def __init__(self):
        self.causal_graph = nx.DiGraph()

    def build_causal_network(self, factor_relationships):
        """
        构建因果关系网络

        Args:
            factor_relationships: 因素关系数据 [(factor1, factor2, strength)]
        """
        for source, target, strength in factor_relationships:
            self.causal_graph.add_edge(source, target, weight=strength)

    def compute_causal_effects(self, treatment_factors, outcome_factors):
        """
        计算因果效应

        Args:
            treatment_factors: 处理因素列表
            outcome_factors: 结果因素列表

        Returns:
            因果效应估计
        """
        causal_effects = {}

        for treatment in treatment_factors:
            for outcome in outcome_factors:
                # 寻找从treatment到outcome的所有路径
                try:
                    paths = list(nx.all_simple_paths(self.causal_graph, treatment, outcome, cutoff=3))

                    # 计算路径强度（路径上边的权重乘积）
                    path_strengths = []
                    for path in paths:
                        path_strength = 1.0
                        for i in range(len(path) - 1):
                            edge_weight = self.causal_graph[path[i]][path[i+1]].get('weight', 1.0)
                            path_strength *= edge_weight
                        path_strengths.append(path_strength)

                    # 最大路径强度作为因果效应估计
                    max_effect = max(path_strengths) if path_strengths else 0.0
                    causal_effects[(treatment, outcome)] = {
                        'effect_size': max_effect,
                        'n_paths': len(paths),
                        'path_details': list(zip(paths, path_strengths))
                    }

                except nx.NetworkXNoPath:
                    causal_effects[(treatment, outcome)] = {
                        'effect_size': 0.0,
                        'n_paths': 0,
                        'path_details': []
                    }

        return causal_effects
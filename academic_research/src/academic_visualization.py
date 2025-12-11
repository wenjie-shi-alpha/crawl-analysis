"""
学术级可视化模块
创建符合期刊发表标准的高质量可视化图表
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager as fm
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import networkx as nx
from scipy.cluster.hierarchy import dendrogram, linkage
import warnings
warnings.filterwarnings('ignore')

# 设置学术风格的配色方案
ACADEMIC_COLORS = {
    'primary': '#2c3e50',      # 深蓝灰色
    'secondary': '#3498db',    # 蓝色
    'accent1': '#e74c3c',      # 红色
    'accent2': '#f39c12',      # 橙色
    'accent3': '#27ae60',      # 绿色
    'accent4': '#9b59b6',      # 紫色
    'neutral': '#95a5a6',      # 灰色
    'drivers': '#27ae60',      # 驱动因素-绿色
    'barriers': '#e74c3c',     # 阻碍因素-红色
    'neutral_factors': '#95a5a6'  # 中性因素-灰色
}

# 设置学术字体样式
ACADEMIC_FONT_SETTINGS = {
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif', 'serif'],
    'font.size': 12,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 16,
    'text.usetex': False  # 设为True需要LaTeX环境
}


class AcademicVisualizer:
    """学术级可视化器"""

    def __init__(self, font_path=None, output_dir="academic_research/output/academic_figures", dpi=300):
        self.output_dir = output_dir
        self.dpi = dpi
        os.makedirs(output_dir, exist_ok=True)

        # 设置中文字体支持
        if font_path and os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            font_prop = fm.FontProperties(fname=font_path)
            plt.rcParams['font.sans-serif'] = [font_prop.get_name()]
        else:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']

        # 应用学术风格设置
        plt.rcParams.update(ACADEMIC_FONT_SETTINGS)
        plt.rcParams['axes.unicode_minus'] = False

        # 设置学术风格
        self.style = 'seaborn-v0_8-whitegrid'
        self.color_palette = 'Set2'

        # 定义学术级colormap
        self.academic_cmap = LinearSegmentedColormap.from_list(
            'academic', ['#f7f7f7', '#d1e5f0', '#92c5de', '#4393c3', '#2166ac']
        )

    def create_three_dimensional_force_field(self, temporal_evolution, factor_categories):
        """
        创建三维力场分析图（时间×因素×强度）

        Args:
            temporal_evolution: 时间演变数据
            factor_categories: 因素分类数据
        """
        fig = plt.figure(figsize=(16, 12))
        ax = fig.add_subplot(111, projection='3d')

        # 准备数据
        time_periods = list(temporal_evolution.keys()) if temporal_evolution else []
        factors = list(factor_categories.keys()) if factor_categories else []

        # 为每个因素创建3D曲线
        colors = plt.cm.Set3(np.linspace(0, 1, len(factors)))

        for i, factor in enumerate(factors):
            if factor not in temporal_evolution:
                continue

            factor_data = temporal_evolution[factor]
            x_values = list(range(len(factor_data)))
            y_values = [i] * len(factor_data)
            z_values = [point.get('intensity', 0) for point in factor_data]

            # 创建3D线条
            ax.plot(x_values, y_values, z_values,
                   color=colors[i], linewidth=2.5, marker='o', markersize=4,
                   label=factor, alpha=0.8)

            # 添加强度标签
            for j, (x, y, z) in enumerate(zip(x_values, y_values, z_values)):
                if z > 0.1:  # 只显示有意义的值
                    ax.text(x, y, z, f'{z:.2f}', fontsize=8, alpha=0.7)

        # 设置坐标轴标签
        ax.set_xlabel('Time Period', fontsize=12)
        ax.set_ylabel('Factors', fontsize=12)
        ax.set_zlabel('Intensity', fontsize=12)
        ax.set_title('3D Force Field Analysis: Green Power Consumption\nTemporal Evolution of Driver and Barrier Factors',
                    fontsize=14, pad=20)

        # 设置Y轴为因素标签
        ax.set_yticks(range(len(factors)))
        ax.set_yticklabels(factors)

        # 设置X轴为时间标签
        if time_periods:
            ax.set_xticks(range(len(time_periods)))
            ax.set_xticklabels(time_periods, rotation=45, ha='right')

        # 添加图例
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)

        # 调整视角
        ax.view_init(elev=20, azim=45)

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, "3d_force_field_analysis.png")
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"3D力场分析图已保存至: {output_path}")

    def create_sankey_diagram(self, flow_data):
        """
        创建桑基图显示政策→市场→企业→消费的流转路径

        Args:
            flow_data: 流转数据，格式为 {'source': [], 'target': [], 'value': []}
        """
        # 创建更清晰的颜色映射
        node_colors = {
            'Policy': ACADEMIC_COLORS['primary'],
            'Market': ACADEMIC_COLORS['secondary'],
            'Enterprise': ACADEMIC_COLORS['accent3'],
            'Consumption': ACADEMIC_COLORS['accent1']
        }

        # 准备数据
        sources = flow_data.get('source', [])
        targets = flow_data.get('target', [])
        values = flow_data.get('value', [])

        # 创建唯一的节点列表
        all_nodes = list(set(sources + targets))
        node_indices = {node: i for i, node in enumerate(all_nodes)}

        # 转换为索引
        source_indices = [node_indices[src] for src in sources]
        target_indices = [node_indices[tgt] for tgt in targets]

        # 创建图表
        fig = go.Figure(data=[go.Sankey(
            arrangement='snap',
            node=dict(
                pad=20,
                thickness=30,
                line=dict(color='black', width=1),
                label=all_nodes,
                color=[node_colors.get(node.split()[0], '#cccccc') for node in all_nodes]
            ),
            link=dict(
                source=source_indices,
                target=target_indices,
                value=values,
                hovertemplate='%{source.label} → %{target.label}<br>Strength: %{value}<extra></extra>'
            )
        )])

        # 更新布局
        fig.update_layout(
            title=dict(
                text='Green Power Consumption Flow Analysis<br>Policy → Market → Enterprise → Consumption',
                x=0.5,
                font=dict(size=16)
            ),
            font=dict(size=12),
            width=1000,
            height=600,
            margin=dict(l=50, r=50, t=100, b=50)
        )

        # 保存为HTML和PNG
        html_path = os.path.join(self.output_dir, "green_power_flow_sankey.html")
        png_path = os.path.join(self.output_dir, "green_power_flow_sankey.png")

        fig.write_html(html_path)
        fig.write_image(png_path, width=1000, height=600, scale=2)

        print(f"桑基图已保存至: {html_path} (HTML) 和 {png_path} (PNG)")

    def create_temporal_heatmap(self, evolution_data, time_periods):
        """
        创建时间演变热力图

        Args:
            evolution_data: 演变数据
            time_periods: 时间周期列表
        """
        if not evolution_data or not time_periods:
            print("没有足够的数据创建热力图")
            return

        # 准备数据矩阵
        factors = list(evolution_data.keys())
        matrix_data = []

        for factor in factors:
            factor_series = evolution_data[factor]
            row_data = []

            for period in time_periods:
                intensity = 0
                for data_point in factor_series:
                    if data_point['time'] == period:
                        intensity = data_point.get('intensity', 0)
                        break
                row_data.append(intensity)

            matrix_data.append(row_data)

        # 创建DataFrame
        df = pd.DataFrame(matrix_data, index=factors, columns=time_periods)

        # 创建热力图
        fig, ax = plt.subplots(figsize=(14, 10))

        # 使用学术级colormap
        sns.heatmap(df,
                   cmap=self.academic_cmap,
                   annot=True,
                   fmt='.2f',
                   linewidths=0.5,
                   cbar_kws={'label': 'Factor Intensity'},
                   ax=ax)

        # 设置标题和标签
        ax.set_title('Temporal Evolution of Green Power Consumption Factors',
                    fontsize=14, pad=20, fontweight='bold')
        ax.set_xlabel('Time Period', fontsize=12)
        ax.set_ylabel('Factors', fontsize=12)

        # 旋转x轴标签
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, "temporal_evolution_heatmap.png")
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"时间演变热力图已保存至: {output_path}")

        return df

    def create_network_evolution(self, network_snapshots):
        """
        创建网络演化图

        Args:
            network_snapshots: 不同时间点的网络快照
        """
        if not network_snapshots:
            print("没有网络快照数据")
            return

        n_snapshots = len(network_snapshots)
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        axes = axes.flatten()

        for i, (time_point, network_data) in enumerate(network_snapshots.items()):
            if i >= 4:  # 最多显示4个时间点
                break

            ax = axes[i]

            # 创建网络图
            G = nx.Graph()

            # 添加边
            if 'edges' in network_data:
                for edge in network_data['edges']:
                    G.add_edge(edge['source'], edge['target'], weight=edge.get('weight', 1))

            # 设置布局
            pos = nx.spring_layout(G, k=1, iterations=50, seed=42)

            # 绘制节点
            node_sizes = [max(nx.degree(G, node) * 100, 200) for node in G.nodes()]
            nx.draw_networkx_nodes(G, pos, node_size=node_sizes,
                                  node_color=ACADEMIC_COLORS['secondary'],
                                  alpha=0.8, ax=ax)

            # 绘制边
            edge_widths = [G[u][v].get('weight', 1) for u, v in G.edges()]
            nx.draw_networkx_edges(G, pos, width=edge_widths,
                                  alpha=0.6, edge_color=ACADEMIC_COLORS['neutral'], ax=ax)

            # 绘制标签
            nx.draw_networkx_labels(G, pos, font_size=8, ax=ax)

            # 设置标题
            ax.set_title(f'Network Evolution: {time_point}', fontsize=12, fontweight='bold')
            ax.axis('off')

        plt.suptitle('Evolution of Keyword Co-occurrence Networks',
                    fontsize=16, y=0.95, fontweight='bold')
        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "network_evolution.png")
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"网络演化图已保存至: {output_path}")

    def create_geographic_heatmap(self, provincial_data):
        """
        创建省级绿电政策强度热力图

        Args:
            provincial_data: 省级数据字典
        """
        if not provincial_data:
            print("没有省级数据")
            return

        # 准备数据
        provinces = list(provincial_data.keys())
        values = list(provincial_data.values())

        # 创建DataFrame
        df = pd.DataFrame({
            'Province': provinces,
            'Intensity': values
        })

        # 按强度排序
        df = df.sort_values('Intensity', ascending=False)

        # 创建热力图样式
        fig, ax = plt.subplots(figsize=(12, 16))

        # 创建颜色映射
        colors = [self.academic_cmap(i/len(df)) for i in range(len(df))]

        # 创建水平条形图
        bars = ax.barh(range(len(df)), df['Intensity'], color=colors)

        # 设置标签
        ax.set_yticks(range(len(df)))
        ax.set_yticklabels(df['Province'])
        ax.set_xlabel('Green Power Policy Intensity Index', fontsize=12)
        ax.set_title('Provincial Distribution of Green Power Policy Focus in China',
                    fontsize=14, pad=20, fontweight='bold')

        # 添加数值标签
        for i, (bar, value) in enumerate(zip(bars, df['Intensity'])):
            ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                   f'{value:.3f}', va='center', fontsize=9)

        # 添加网格
        ax.grid(axis='x', alpha=0.3)

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, "provincial_policy_heatmap.png")
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"省级政策热力图已保存至: {output_path}")

    def create_radar_comparison(self, comparison_data, time_points=None):
        """
        创建雷达图对比不同时期或地区的驱动-阻碍因素

        Args:
            comparison_data: 对比数据字典
            time_points: 时间点列表
        """
        if not comparison_data:
            print("没有对比数据")
            return

        fig, axes = plt.subplots(2, 2, figsize=(16, 12), subplot_kw=dict(projection='polar'))
        axes = axes.flatten()

        categories = list(list(comparison_data.values())[0].keys())
        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # 闭合图形

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

        for i, (label, data) in enumerate(comparison_data.items()):
            if i >= 4:
                break

            ax = axes[i]

            # 准备数据
            values = list(data.values())
            values += values[:1]  # 闭合图形

            # 绘制雷达图
            ax.plot(angles, values, 'o-', linewidth=2,
                   color=colors[i % len(colors)], label=label)
            ax.fill(angles, values, alpha=0.25, color=colors[i % len(colors)])

            # 设置标签
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories)
            ax.set_ylim(0, 1)
            ax.set_title(f'{label}', fontsize=12, fontweight='bold', pad=20)
            ax.grid(True)

        plt.suptitle('Comparative Analysis of Green Power Factors Across Different Dimensions',
                    fontsize=16, y=0.95, fontweight='bold')
        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "factor_radar_comparison.png")
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"雷达对比图已保存至: {output_path}")

    def create_boxplot_analysis(self, sentiment_data_by_source):
        """
        创建箱线图分析不同来源类型的情感分布差异

        Args:
            sentiment_data_by_source: 按来源分组的情感数据
        """
        if not sentiment_data_by_source:
            print("没有按来源分组的情感数据")
            return

        # 准备数据
        data_for_boxplot = []
        sources = []
        sentiments = []

        for source, scores in sentiment_data_by_source.items():
            for score in scores:
                sources.append(source)
                sentiments.append(score)

        df = pd.DataFrame({
            'Source': sources,
            'Sentiment': sentiments
        })

        # 创建箱线图
        fig, ax = plt.subplots(figsize=(14, 8))

        # 使用学术配色
        palette = sns.color_palette("Set2", len(df['Source'].unique()))

        sns.boxplot(data=df, x='Source', y='Sentiment',
                   palette=palette, ax=ax, width=0.6)

        # 添加散点图显示数据点
        sns.stripplot(data=df, x='Source', y='Sentiment',
                     color='black', alpha=0.3, size=4, ax=ax)

        # 设置标题和标签
        ax.set_title('Sentiment Score Distribution by Information Source',
                    fontsize=14, pad=20, fontweight='bold')
        ax.set_xlabel('Information Source Type', fontsize=12)
        ax.set_ylabel('Sentiment Score', fontsize=12)

        # 添加水平参考线
        ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.7, label='Neutral Line')
        ax.axhline(y=0.6, color='green', linestyle='--', alpha=0.7, label='Positive Threshold')
        ax.axhline(y=0.4, color='orange', linestyle='--', alpha=0.7, label='Negative Threshold')

        # 旋转x轴标签
        plt.xticks(rotation=45, ha='right')

        # 添加图例
        ax.legend(loc='upper right')

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, "sentiment_distribution_by_source.png")
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"来源情感分布箱线图已保存至: {output_path}")

    def create_regression_forest_plot(self, regression_results):
        """
        创建回归森林图显示各因素的影响系数

        Args:
            regression_results: 回归分析结果
        """
        if not regression_results or 'coefficients' not in regression_results:
            print("没有回归系数数据")
            return

        # 准备数据
        coefficients = regression_results['coefficients']
        feature_names = [f'Factor_{i+1}' for i in range(len(coefficients))]

        # 创建置信区间（模拟）
        std_errors = np.abs(coefficients) * 0.2  # 假设标准误差为系数的20%
        confidence_intervals = [(coef - 1.96*se, coef + 1.96*se)
                               for coef, se in zip(coefficients, std_errors)]

        # 创建森林图
        fig, ax = plt.subplots(figsize=(12, 10))

        # 计算y轴位置
        y_pos = np.arange(len(feature_names))

        # 绘制置信区间
        for i, (ci_low, ci_high) in enumerate(confidence_intervals):
            ax.plot([ci_low, ci_high], [i, i], 'k-', linewidth=2)
            ax.plot([ci_low], [i], 'ko', markersize=6)
            ax.plot([ci_high], [i], 'ko', markersize=6)

        # 绘制系数点
        colors = ['red' if coef < 0 else 'green' for coef in coefficients]
        ax.scatter(coefficients, y_pos, c=colors, s=100, alpha=0.7, zorder=5)

        # 添加零参考线
        ax.axvline(x=0, color='black', linestyle='-', linewidth=1, alpha=0.5)

        # 设置标签和标题
        ax.set_yticks(y_pos)
        ax.set_yticklabels(feature_names)
        ax.set_xlabel('Regression Coefficient', fontsize=12)
        ax.set_title('Forest Plot: Impact Factors on Green Power Consumption',
                    fontsize=14, pad=20, fontweight='bold')

        # 添加网格
        ax.grid(axis='x', alpha=0.3)

        # 添加显著性标记
        p_values = regression_results.get('p_values', [0.05] * len(coefficients))
        significance = ['*' if p < 0.05 else '' for p in p_values]

        for i, (coeff, sig) in enumerate(zip(coefficients, significance)):
            if sig:
                ax.text(coeff, i, sig, fontsize=12, ha='left' if coeff > 0 else 'right',
                       va='center', fontweight='bold')

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, "regression_forest_plot.png")
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"回归森林图已保存至: {output_path}")

    def create_academic_wordcloud(self, keyword_data, title="Academic Word Cloud"):
        """
        创建符合学术标准的高级词云图

        Args:
            keyword_data: 关键词数据 {word: frequency}
            title: 图表标题
        """
        from wordcloud import WordCloud, STOPWORDS
        from matplotlib.colors import LinearSegmentedColormap

        # 定义学术配色
        colors = ["#2c3e50", "#34495e", "#7f8c8d", "#95a5a6", "#bdc3c7"]
        cmap = LinearSegmentedColormap.from_list("academic", colors)

        # 创建词云
        wc = WordCloud(
            width=1600,
            height=800,
            background_color='white',
            max_words=100,
            colormap=cmap,
            contour_width=2,
            contour_color='#2c3e50',
            relative_scaling=0.8,
            random_state=42
        )

        # 生成词云
        wc.generate_from_frequencies(keyword_data)

        # 创建图表
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')

        # 添加标题
        ax.set_title(title, fontsize=18, pad=20, fontweight='bold', color=ACADEMIC_COLORS['primary'])

        # 添加边框
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(ACADEMIC_COLORS['neutral'])
            spine.set_linewidth(1)

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, f"{title.lower().replace(' ', '_')}.png")
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"学术词云图已保存至: {output_path}")

    def create_comprehensive_dashboard(self, all_analysis_data):
        """
        创建综合分析仪表盘

        Args:
            all_analysis_data: 包含所有分析数据的字典
        """
        fig = plt.figure(figsize=(20, 16))
        gs = fig.add_gridspec(4, 4, hspace=0.3, wspace=0.3)

        # 1. 力场分析 (左上角, 2x2)
        ax1 = fig.add_subplot(gs[0:2, 0:2])
        self._plot_force_field_subset(ax1, all_analysis_data.get('factor_data', {}))

        # 2. 时间趋势 (右上角, 2x2)
        ax2 = fig.add_subplot(gs[0:2, 2:4])
        self._plot_temporal_trends(ax2, all_analysis_data.get('temporal_data', {}))

        # 3. 地理分布 (左下角, 2x2)
        ax3 = fig.add_subplot(gs[2:4, 0:2])
        self._plot_geographic_distribution(ax3, all_analysis_data.get('geo_data', {}))

        # 4. 情感分析 (右下角, 1x2)
        ax4 = fig.add_subplot(gs[2, 2:4])
        self._plot_sentiment_analysis(ax4, all_analysis_data.get('sentiment_data', {}))

        # 5. 因素重要性 (右下角, 1x2)
        ax5 = fig.add_subplot(gs[3, 2:4])
        self._plot_factor_importance(ax5, all_analysis_data.get('importance_data', {}))

        # 添加总标题
        fig.suptitle('Comprehensive Analysis Dashboard: Green Power Consumption in China',
                    fontsize=20, fontweight='bold', y=0.95)

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, "comprehensive_analysis_dashboard.png")
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"综合分析仪表盘已保存至: {output_path}")

    def _plot_force_field_subset(self, ax, factor_data):
        """绘制力场分析子图"""
        # 实现简化的力场分析
        drivers = factor_data.get('drivers', [])[:5]
        barriers = factor_data.get('barriers', [])[:5]

        # 驱动因素（左侧）
        y_pos = np.arange(len(drivers))
        ax.barh(y_pos, [d[1] for d in drivers], color=ACADEMIC_COLORS['drivers'], alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([d[0] for d in drivers])
        ax.set_xlabel('Driver Strength')
        ax.set_title('Top Drivers & Barriers', fontweight='bold')

        # 障碍因素（右侧，使用反向坐标）
        ax2 = ax.twiny()
        ax2.barh(y_pos + len(drivers) + 1, [b[1] for b in barriers],
                color=ACADEMIC_COLORS['barriers'], alpha=0.7)
        ax2.set_xlabel('Barrier Strength')

    def _plot_temporal_trends(self, ax, temporal_data):
        """绘制时间趋势子图"""
        # 简化的时间趋势图
        if temporal_data:
            for factor, data in list(temporal_data.items())[:3]:  # 只显示前3个因素
                values = [point.get('intensity', 0) for point in data]
                ax.plot(values, label=factor, linewidth=2, marker='o', markersize=4)

        ax.set_xlabel('Time Period')
        ax.set_ylabel('Intensity')
        ax.set_title('Temporal Trends', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_geographic_distribution(self, ax, geo_data):
        """绘制地理分布子图"""
        # 简化的地理分布图
        if geo_data:
            regions = list(geo_data.keys())[:10]  # 显示前10个地区
            values = [geo_data[r] for r in regions]

            ax.barh(regions, values, color=ACADEMIC_COLORS['secondary'], alpha=0.7)
            ax.set_xlabel('Frequency')
            ax.set_title('Geographic Distribution', fontweight='bold')

    def _plot_sentiment_analysis(self, ax, sentiment_data):
        """绘制情感分析子图"""
        # 简化的情感分析图
        if sentiment_data:
            scores = sentiment_data.get('scores', [])
            if scores:
                ax.hist(scores, bins=20, alpha=0.7, color=ACADEMIC_COLORS['accent4'], edgecolor='black')
                ax.axvline(x=np.mean(scores), color='red', linestyle='--', label='Mean')
                ax.set_xlabel('Sentiment Score')
                ax.set_ylabel('Frequency')
                ax.set_title('Sentiment Distribution', fontweight='bold')
                ax.legend()

    def _plot_factor_importance(self, ax, importance_data):
        """绘制因素重要性子图"""
        # 简化的因素重要性图
        if importance_data:
            factors = list(importance_data.keys())[:8]  # 显示前8个因素
            importances = [importance_data[f] for f in factors]

            # 水平条形图
            y_pos = np.arange(len(factors))
            ax.barh(y_pos, importances, color=ACADEMIC_COLORS['accent2'], alpha=0.7)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(factors)
            ax.set_xlabel('Importance Score')
            ax.set_title('Factor Importance', fontweight='bold')
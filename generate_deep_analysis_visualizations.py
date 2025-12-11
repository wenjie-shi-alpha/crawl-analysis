#!/usr/bin/env python3
"""
基于增强分析结果的深度分析与可视化脚本
Deep Analysis and Visualization Script based on Enhanced Analysis Results

实现researchGreenSpec.md中描述的高级可视化方案：
- 桑基图 (Sankey Diagram) - 驱动/阻碍因素流向
- 语义共现网络图 (Co-occurrence Network)
- 主题河流图 (ThemeRiver) - 时间演化
- 因果链网络图 (Causal Network)
- 地理热力图
- 雷达图 (Radar Chart) - 供需错配分析
- 情感分布热力图
"""

import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib import rcParams
from matplotlib import colors as mcolors
import textwrap
import seaborn as sns

# 尝试导入高级可视化库
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("Warning: plotly not available, some visualizations will be skipped")

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("Warning: networkx not available, network visualizations will be skipped")

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeepAnalysisVisualizer:
    """深度分析可视化器"""
    
    def __init__(self, output_dir: str = "data/output/final/refined_analysis"):
        # 输出目录采用全新的refined_analysis，避免覆盖旧版本并集中所有产出
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 高级配色方案（柔和中性色 + 点缀色），统一全局视觉语言
        base_palette = sns.color_palette("muted")
        accent_palette = sns.color_palette("crest", 6)

        self.colors = {
            'driver': accent_palette[3],   # 驱动因素
            'barrier': accent_palette[0],  # 障碍因素
            'policy': base_palette[2],     # 政策端
            'market': base_palette[4],     # 市场端
            'public': base_palette[1],     # 舆论端
            'positive': accent_palette[4],
            'negative': accent_palette[1],
            'neutral': base_palette[0],
            'background': '#f6f6f4'
        }

        # PESTEL颜色统一到同一风格，避免饱和度杂乱
        self.pestel_colors = {
            '政治因素': accent_palette[0],
            '经济因素': accent_palette[2],
            '社会因素': accent_palette[1],
            '技术因素': accent_palette[3],
            '环境因素': accent_palette[4],
            '法律因素': accent_palette[5]
        }

        # 载入中文字体以避免方框显示
        font_path = Path("academic_research/data/fonts/SimHei.ttf")
        if font_path.exists():
            fm.fontManager.addfont(str(font_path))
            rcParams['font.family'] = 'SimHei'
        else:
            rcParams['font.family'] = 'DejaVu Sans'

        # 全局样式
        sns.set_theme(style="whitegrid", context="talk", font=rcParams['font.family'])
        rcParams['axes.facecolor'] = self.colors['background']
        rcParams['figure.facecolor'] = self.colors['background']
        rcParams['savefig.facecolor'] = self.colors['background']
        rcParams['axes.edgecolor'] = '#d7d7d0'
        self._to_hex = lambda c: mcolors.to_hex(c)

        # 文本包装工具，避免长标签溢出
        def wrap_label(text: str, width: int = 12, max_lines: int = 3) -> str:
            if not text:
                return ''
            lines = textwrap.wrap(str(text), width=width)
            return "\n".join(lines[:max_lines]) + ("…" if len(lines) > max_lines else "")

        self.wrap_label = wrap_label
        self.wrap_plotly = lambda text, width=10, max_lines=2: wrap_label(text, width, max_lines).replace("\n", "<br>")
    
    def load_analysis_data(self, enhanced_file: str, comprehensive_file: str = None) -> Tuple[Dict, Dict]:
        """加载分析数据"""
        logger.info(f"Loading analysis data from {enhanced_file}")
        
        with open(enhanced_file, 'r', encoding='utf-8') as f:
            enhanced_data = json.load(f)
        
        comprehensive_data = {}
        if comprehensive_file and Path(comprehensive_file).exists():
            try:
                # 文件可能很大,只加载关键部分
                with open(comprehensive_file, 'r', encoding='utf-8') as f:
                    comprehensive_data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load comprehensive file: {e}")
        
        return enhanced_data, comprehensive_data
    
    def create_temporal_evolution_chart(self, temporal_data: Dict) -> str:
        """
        创建时间演化图表 - 主题河流图风格
        """
        logger.info("Creating temporal evolution visualization...")
        
        time_dist = temporal_data.get('time_distribution', {})
        
        # 过滤有效年份数据
        valid_years = {k: v for k, v in time_dist.items() 
                       if k != 'unknown' and k.isdigit() and int(k) >= 2010 and int(k) <= 2030}
        
        if not valid_years:
            logger.warning("No valid temporal data found")
            return ""
        
        # 按年份排序
        years_int = sorted([int(y) for y in valid_years.keys()])
        years = [str(y) for y in years_int]
        counts = [valid_years[str(y)] for y in years_int]
        
        # 创建图表
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 文档时间分布柱状图
        ax1 = axes[0, 0]
        bars = ax1.bar(years, counts, color=self.colors['policy'], alpha=0.7, edgecolor='white')
        ax1.set_xlabel('年份', fontsize=12)
        ax1.set_ylabel('文档数量', fontsize=12)
        ax1.set_title('绿电相关文档时间分布', fontsize=14, fontweight='bold')
        ax1.tick_params(axis='x', rotation=45)
        
        # 添加数值标签
        for bar, count in zip(bars, counts):
            ax1.annotate(f'{count}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        ha='center', va='bottom', fontsize=9)
        
        # 2. 演化趋势面积图
        ax2 = axes[0, 1]
        ax2.fill_between(years, counts, alpha=0.4, color=self.colors['driver'])
        ax2.plot(years, counts, 'o-', color=self.colors['driver'], linewidth=2, markersize=6)
        ax2.set_xlabel('年份', fontsize=12)
        ax2.set_ylabel('文档数量', fontsize=12)
        ax2.set_title('绿电消费关注度演化趋势', fontsize=14, fontweight='bold')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        # 3. 演化模式分析
        ax3 = axes[1, 0]
        evolution_patterns = temporal_data.get('evolution_patterns', [])
        if evolution_patterns:
            pattern_names = [self.wrap_label(p.get('pattern', ''), width=14, max_lines=3)
                             for p in evolution_patterns[:6]]
            significance = [1 if p.get('significance') == 'high' else 0.6 
                           for p in evolution_patterns[:6]]
            
            y_pos = np.arange(len(pattern_names))
            bars = ax3.barh(y_pos, significance, color=[self.colors['driver'] if s == 1 
                           else self.colors['neutral'] for s in significance])
            ax3.set_yticks(y_pos)
            ax3.set_yticklabels(pattern_names, fontsize=9)
            ax3.set_xlabel('重要性', fontsize=12)
            ax3.set_title('关键演化模式', fontsize=14, fontweight='bold')
        else:
            ax3.text(0.5, 0.5, '无演化模式数据', ha='center', va='center', fontsize=12)
            ax3.set_axis_off()
        
        # 4. 新兴/消退因素对比
        ax4 = axes[1, 1]
        emerging = temporal_data.get('emerging_factors', [])[:5]
        declining = temporal_data.get('declining_factors', [])[:5]
        
        if emerging or declining:
            # 创建对比数据
            all_factors = []
            factor_types = []
            
            for f in emerging:
                all_factors.append(self.wrap_label(f, width=16, max_lines=3))
                factor_types.append('新兴')
            for f in declining:
                all_factors.append(self.wrap_label(f, width=16, max_lines=3))
                factor_types.append('消退')
            
            if all_factors:
                y_pos = np.arange(len(all_factors))
                colors_list = [self.colors['driver'] if t == '新兴' else self.colors['barrier'] 
                              for t in factor_types]
                ax4.barh(y_pos, [1]*len(all_factors), color=colors_list, alpha=0.7)
                ax4.set_yticks(y_pos)
                ax4.set_yticklabels(all_factors, fontsize=9)
                ax4.set_title('新兴与消退因素', fontsize=14, fontweight='bold')
                
                # 添加图例
                from matplotlib.patches import Patch
                legend_elements = [Patch(facecolor=self.colors['driver'], label='新兴因素'),
                                  Patch(facecolor=self.colors['barrier'], label='消退因素')]
                ax4.legend(handles=legend_elements, loc='lower right')
        else:
            ax4.text(0.5, 0.5, '无新兴/消退因素数据', ha='center', va='center', fontsize=12)
            ax4.set_axis_off()
        
        plt.tight_layout()
        
        output_path = self.output_dir / f"temporal_evolution_{self.timestamp}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=self.colors['background'])
        plt.close()
        
        logger.info(f"Saved temporal evolution chart to {output_path}")
        return str(output_path)
    
    def create_causal_network(self, causal_data: Dict) -> str:
        """
        创建因果链网络图（分层+社区+关键节点，避免“毛球图”）
        """
        if not NETWORKX_AVAILABLE:
            logger.warning("NetworkX not available, skipping causal network")
            return ""

        logger.info("Creating causal chain network visualization...")

        raw_chains = causal_data.get('raw_chains', [])
        core_chains = causal_data.get('核心因果链', [])

        # 创建有向图，并控制规模，优先核心链，再补充高置信度链
        G = nx.DiGraph()

        def _short(text: str, limit: int = 50) -> str:
            # 包装为多行，优先可读性
            if not text:
                return ''
            return self.wrap_label(text, width=12, max_lines=3)

        for chain in core_chains:
            cause = chain.get('cause', '')
            effect = chain.get('effect', '')
            impact = float(chain.get('影响指数', 0.5) or 0.5)
            if cause and effect:
                G.add_edge(_short(cause), _short(effect), weight=impact, origin='core')

        # 按置信度排序原始链，筛选Top 60，避免噪声
        sorted_raw = sorted(
            [c for c in raw_chains if c.get('cause') and c.get('effect')],
            key=lambda x: x.get('confidence', 0.0),
            reverse=True
        )[:60]

        for chain in sorted_raw:
            cause = chain.get('cause', '')
            effect = chain.get('effect', '')
            confidence = float(chain.get('confidence', 0.5) or 0.5)
            G.add_edge(_short(cause), _short(effect), weight=confidence, origin='raw')

        if len(G.nodes()) < 2:
            logger.warning("Not enough nodes for causal network")
            return ""

        # 提取最强边，减少杂乱
        top_edges = sorted(G.edges(data=True), key=lambda x: x[2].get('weight', 0), reverse=True)[:40]
        H = nx.DiGraph()
        H.add_edges_from(top_edges)

        # 社区划分以突出结构
        try:
            communities = list(nx.community.greedy_modularity_communities(H.to_undirected()))
        except Exception:
            communities = []
        community_map = {}
        for idx, comm in enumerate(communities):
            for node in comm:
                community_map[node] = idx

        # 中介中心性用于节点大小
        centrality = nx.betweenness_centrality(H, weight='weight', normalized=True)
        node_sizes = [600 + centrality.get(n, 0) * 4000 for n in H.nodes()]

        # 颜色映射：社区优先，否则按因果方向
        palette = sns.color_palette("Set2", max(3, len(communities)))
        node_colors = []
        for n in H.nodes():
            if community_map:
                node_colors.append(palette[community_map.get(n, 0) % len(palette)])
            else:
                # 如果没有社区划分，就根据出入度方向着色
                if H.out_degree(n) >= H.in_degree(n):
                    node_colors.append(self.colors['driver'])
                else:
                    node_colors.append(self.colors['barrier'])

        # 布局：spring_layout + weight，减小交叉
        pos = nx.spring_layout(H, k=0.9, iterations=200, weight='weight', seed=42)

        # 绘制多分区面板：网络 + 关键节点条形 + 统计摘要
        fig = plt.figure(figsize=(18, 12), facecolor=self.colors['background'])
        gs = fig.add_gridspec(2, 2, height_ratios=[3, 1])

        ax_net = fig.add_subplot(gs[0, :])
        edge_weights = [H[u][v].get('weight', 0.5) * 2.5 for u, v in H.edges()]
        edge_colors = ['#b6b6b6' if H[u][v].get('origin') == 'raw' else '#565656' for u, v in H.edges()]

        nx.draw_networkx_nodes(H, pos, node_color=node_colors, node_size=node_sizes,
                               alpha=0.9, ax=ax_net, linewidths=0.8, edgecolors='#444444')
        nx.draw_networkx_edges(H, pos, edge_color=edge_colors, width=edge_weights,
                               alpha=0.5, arrows=True, arrowsize=12, ax=ax_net,
                               connectionstyle="arc3,rad=0.08")
        nx.draw_networkx_labels(H, pos, font_size=8, font_family='DejaVu Sans', ax=ax_net)

        ax_net.set_title('因果链结构与关键路径（前40条高置信度链）', fontsize=16, fontweight='bold')
        ax_net.axis('off')

        # 关键节点Top10
        ax_bar = fig.add_subplot(gs[1, 0])
        top_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
        if top_nodes:
            names = [n for n, _ in top_nodes][::-1]
            vals = [v for _, v in top_nodes][::-1]
            colors = [node_colors[list(H.nodes()).index(n)] for n in names]
            ax_bar.barh(names, vals, color=colors, alpha=0.9)
            ax_bar.set_title('关键节点（中介中心性 Top10）', fontsize=12, fontweight='bold')
            ax_bar.set_xlabel('Betweenness Centrality')
        else:
            ax_bar.text(0.5, 0.5, '无有效因果链', ha='center', va='center')
            ax_bar.axis('off')

        # 统计摘要
        ax_kpi = fig.add_subplot(gs[1, 1])
        ax_kpi.axis('off')
        stats_text = [
            f"节点数: {H.number_of_nodes()}",
            f"边数: {H.number_of_edges()}",
            f"平均出度: {np.mean([d for _, d in H.out_degree()]):.2f}",
            f"平均入度: {np.mean([d for _, d in H.in_degree()]):.2f}",
            f"密度: {nx.density(H):.4f}",
            f"直径(无向): {nx.diameter(H.to_undirected()) if nx.is_connected(H.to_undirected()) else 'N/A'}"
        ]
        ax_kpi.text(0.02, 0.9, "关键结构指标", fontsize=12, fontweight='bold')
        ax_kpi.text(0.02, 0.75, "\n".join(stats_text), fontsize=10, va='top')

        # 图例
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#565656', label='核心链边'),
            Patch(facecolor='#b6b6b6', label='原始链边')
        ]
        if community_map:
            for idx in range(min(len(communities), 4)):
                legend_elements.append(Patch(facecolor=palette[idx % len(palette)], label=f'社区 {idx+1}'))
        else:
            legend_elements.extend([
                Patch(facecolor=self.colors['driver'], label='多输出节点'),
                Patch(facecolor=self.colors['barrier'], label='多输入节点')
            ])
        ax_net.legend(handles=legend_elements, loc='lower left', bbox_to_anchor=(0.0, -0.05), ncol=3)

        fig.tight_layout()

        output_path = self.output_dir / f"causal_network_{self.timestamp}.png"
        plt.savefig(output_path, dpi=200, bbox_inches='tight')
        plt.close()

        logger.info(f"Saved causal network to {output_path}")
        return str(output_path)
    
    def create_semantic_clustering_chart(self, clustering_data: Dict) -> str:
        """
        创建语义聚类可视化
        """
        logger.info("Creating semantic clustering visualization...")
        
        core_indicators = clustering_data.get('core_indicators', [])
        
        if not core_indicators:
            logger.warning("No clustering data found")
            return ""
        
        # 准备数据
        indicators = []
        counts = []
        categories = []
        
        for ind in core_indicators[:15]:
            name = ind.get('indicator_name', '')
            count = ind.get('count', 1)
            category = ind.get('category', '其他')
            
            if name:
                indicators.append(self.wrap_label(name, width=14, max_lines=3))
                counts.append(count)
                categories.append(category)
        
        if not indicators:
            return ""
        
        # 创建图表
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        
        # 1. 核心指标柱状图
        ax1 = axes[0]
        y_pos = np.arange(len(indicators))
        colors_list = [self.pestel_colors.get(cat, self.colors['neutral']) for cat in categories]
        
        bars = ax1.barh(y_pos, counts, color=colors_list, alpha=0.8)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(indicators, fontsize=9)
        ax1.set_xlabel('出现频次', fontsize=12)
        ax1.set_title('核心指标聚类结果', fontsize=14, fontweight='bold')
        ax1.invert_yaxis()
        
        # 2. 类别分布饼图
        ax2 = axes[1]
        category_counts = Counter(categories)
        
        if category_counts:
            labels = list(category_counts.keys())
            sizes = list(category_counts.values())
            colors_pie = [self.pestel_colors.get(cat, self.colors['neutral']) for cat in labels]
            
            wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors_pie, 
                                               autopct='%1.1f%%', startangle=90)
            ax2.set_title('核心指标类别分布', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        output_path = self.output_dir / f"semantic_clustering_{self.timestamp}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=self.colors['background'])
        plt.close()
        
        logger.info(f"Saved semantic clustering chart to {output_path}")
        return str(output_path)
    
    def create_conflict_analysis_chart(self, conflict_data: Dict) -> str:
        """
        创建政策-市场矛盾分析图表
        """
        logger.info("Creating conflict analysis visualization...")
        
        conflicts = conflict_data.get('identified_conflicts', [])
        attention_shift = conflict_data.get('attention_shift_analysis', {})
        systemic_gaps = conflict_data.get('systemic_gaps', {})
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 矛盾严重程度分析
        ax1 = axes[0, 0]
        if conflicts:
            severity_counts = Counter([c.get('gap_severity', 'medium') for c in conflicts])
            labels = list(severity_counts.keys())
            sizes = list(severity_counts.values())
            colors_sev = {'high': self.colors['barrier'], 'medium': self.colors['neutral'], 
                         'low': self.colors['driver']}
            colors_list = [colors_sev.get(l, self.colors['neutral']) for l in labels]
            
            ax1.pie(sizes, labels=labels, colors=colors_list, autopct='%1.1f%%', startangle=90)
            ax1.set_title('矛盾严重程度分布', fontsize=14, fontweight='bold')
        else:
            ax1.text(0.5, 0.5, '无矛盾数据', ha='center', va='center', fontsize=12)
            ax1.set_axis_off()
        
        # 2. 关注点差异雷达图
        ax2 = axes[0, 1]
        policy_focus = attention_shift.get('policy_focus', [])
        enterprise_focus = attention_shift.get('enterprise_focus', [])
        
        if policy_focus or enterprise_focus:
            # 简化为文字展示
            ax2.axis('off')
            text_content = "政策关注点:\n"
            for i, p in enumerate(policy_focus[:5], 1):
                text_content += f"  {i}. {p[:30]}...\n" if len(p) > 30 else f"  {i}. {p}\n"
            text_content += "\n企业关注点:\n"
            for i, e in enumerate(enterprise_focus[:5], 1):
                text_content += f"  {i}. {e[:30]}...\n" if len(e) > 30 else f"  {i}. {e}\n"
            
            ax2.text(0.1, 0.9, text_content, transform=ax2.transAxes, fontsize=10,
                    verticalalignment='top', fontfamily='sans-serif',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            ax2.set_title('政策与企业关注点差异', fontsize=14, fontweight='bold')
        else:
            ax2.text(0.5, 0.5, '无关注点差异数据', ha='center', va='center', fontsize=12)
            ax2.set_axis_off()
        
        # 3. 系统性差距分析
        ax3 = axes[1, 0]
        if systemic_gaps:
            gap_types = list(systemic_gaps.keys())
            gap_values = [1] * len(gap_types)  # 用于显示
            
            y_pos = np.arange(len(gap_types))
            ax3.barh(y_pos, gap_values, color=self.colors['barrier'], alpha=0.7)
            ax3.set_yticks(y_pos)
            ax3.set_yticklabels([g.replace('_', ' ').title() for g in gap_types], fontsize=10)
            ax3.set_title('系统性差距类型', fontsize=14, fontweight='bold')
            
            # 添加描述
            for i, gap_type in enumerate(gap_types):
                desc = self.wrap_label(str(systemic_gaps[gap_type]), width=22, max_lines=2)
                ax3.annotate(desc, xy=(0.1, i), fontsize=8, va='center')
        else:
            ax3.text(0.5, 0.5, '无系统性差距数据', ha='center', va='center', fontsize=12)
            ax3.set_axis_off()
        
        # 4. 矛盾类型统计
        ax4 = axes[1, 1]
        if conflicts:
            conflict_types = Counter([c.get('conflict_type', '未知') for c in conflicts])
            if conflict_types:
                labels = list(conflict_types.keys())
                sizes = list(conflict_types.values())
                
                ax4.bar(range(len(labels)), sizes, color=self.colors['market'], alpha=0.7)
                ax4.set_xticks(range(len(labels)))
                ax4.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
                ax4.set_ylabel('数量', fontsize=12)
                ax4.set_title('矛盾类型分布', fontsize=14, fontweight='bold')
        else:
            ax4.text(0.5, 0.5, '无矛盾类型数据', ha='center', va='center', fontsize=12)
            ax4.set_axis_off()
        
        plt.tight_layout()
        
        output_path = self.output_dir / f"conflict_analysis_{self.timestamp}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=self.colors['background'])
        plt.close()
        
        logger.info(f"Saved conflict analysis chart to {output_path}")
        return str(output_path)
    
    def create_aspect_sentiment_heatmap(self, aspect_data: Dict) -> str:
        """
        创建细粒度情感分析热力图
        """
        logger.info("Creating aspect sentiment heatmap...")
        
        aspect_sentiments = aspect_data.get('aspect_sentiments', {})
        pain_index = aspect_data.get('pain_index_ranking', [])
        stakeholder_sentiments = aspect_data.get('stakeholder_sentiments', {})
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 方面情感分布热力图
        ax1 = axes[0, 0]
        if aspect_sentiments:
            aspects = list(aspect_sentiments.keys())[:10]
            pos_ratios = [aspect_sentiments[a].get('positive_ratio', 0) for a in aspects]
            neg_ratios = [aspect_sentiments[a].get('negative_ratio', 0) for a in aspects]
            neu_ratios = [aspect_sentiments[a].get('neutral_ratio', 0) for a in aspects]
            
            data = np.array([pos_ratios, neg_ratios, neu_ratios])
            
            im = ax1.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
            ax1.set_xticks(range(len(aspects)))
            ax1.set_xticklabels([self.wrap_label(a, width=10, max_lines=2) for a in aspects],
                               rotation=0, ha='center', fontsize=9)
            ax1.set_yticks([0, 1, 2])
            ax1.set_yticklabels(['积极', '消极', '中立'], fontsize=10)
            ax1.set_title('方面情感分布热力图', fontsize=14, fontweight='bold')
            
            # 添加颜色条
            plt.colorbar(im, ax=ax1, label='比例')
        else:
            ax1.text(0.5, 0.5, '无方面情感数据', ha='center', va='center', fontsize=12)
            ax1.set_axis_off()
        
        # 2. 痛点指数排行
        ax2 = axes[0, 1]
        if pain_index:
            pain_points = [self.wrap_label(p.get('pain_point', ''), width=14, max_lines=3) for p in pain_index[:10]]
            scores = [p.get('pain_score', 0) for p in pain_index[:10]]
            
            y_pos = np.arange(len(pain_points))
            bars = ax2.barh(y_pos, scores, color=self.colors['barrier'], alpha=0.8)
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels(pain_points, fontsize=9)
            ax2.set_xlabel('痛苦指数', fontsize=12)
            ax2.set_title('消费者痛点排行榜', fontsize=14, fontweight='bold')
            ax2.invert_yaxis()
        else:
            ax2.text(0.5, 0.5, '无痛点数据', ha='center', va='center', fontsize=12)
            ax2.set_axis_off()
        
        # 3. 利益相关者情感分布
        ax3 = axes[1, 0]
        if stakeholder_sentiments:
            stakeholders = list(stakeholder_sentiments.keys())[:6]
            pos_counts = [stakeholder_sentiments[s].get('positive', 0) for s in stakeholders]
            neg_counts = [stakeholder_sentiments[s].get('negative', 0) for s in stakeholders]
            neu_counts = [stakeholder_sentiments[s].get('neutral', 0) for s in stakeholders]
            
            x = np.arange(len(stakeholders))
            width = 0.25
            
            ax3.bar(x - width, pos_counts, width, label='积极', color=self.colors['positive'])
            ax3.bar(x, neg_counts, width, label='消极', color=self.colors['negative'])
            ax3.bar(x + width, neu_counts, width, label='中立', color=self.colors['neutral'])
            
            ax3.set_xticks(x)
            ax3.set_xticklabels(stakeholders, fontsize=10)
            ax3.set_ylabel('计数', fontsize=12)
            ax3.set_title('利益相关者情感态度', fontsize=14, fontweight='bold')
            ax3.legend()
        else:
            ax3.text(0.5, 0.5, '无利益相关者数据', ha='center', va='center', fontsize=12)
            ax3.set_axis_off()
        
        # 4. 整体情感分布饼图
        ax4 = axes[1, 1]
        if aspect_sentiments:
            total_pos = sum(aspect_sentiments[a].get('positive_ratio', 0) for a in aspect_sentiments)
            total_neg = sum(aspect_sentiments[a].get('negative_ratio', 0) for a in aspect_sentiments)
            total_neu = sum(aspect_sentiments[a].get('neutral_ratio', 0) for a in aspect_sentiments)
            
            total = total_pos + total_neg + total_neu
            if total > 0:
                sizes = [total_pos/total, total_neg/total, total_neu/total]
                labels = ['积极', '消极', '中立']
                colors_list = [self.colors['positive'], self.colors['negative'], self.colors['neutral']]
                
                ax4.pie(sizes, labels=labels, colors=colors_list, autopct='%1.1f%%', startangle=90)
                ax4.set_title('整体情感分布', fontsize=14, fontweight='bold')
        else:
            ax4.text(0.5, 0.5, '无情感分布数据', ha='center', va='center', fontsize=12)
            ax4.set_axis_off()
        
        plt.tight_layout()
        
        output_path = self.output_dir / f"aspect_sentiment_{self.timestamp}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=self.colors['background'])
        plt.close()
        
        logger.info(f"Saved aspect sentiment heatmap to {output_path}")
        return str(output_path)
    
    def create_sankey_diagram(self, enhanced_data: Dict) -> str:
        """
        创建桑基图 - 驱动/阻碍因素流向
        """
        if not PLOTLY_AVAILABLE:
            logger.warning("Plotly not available, skipping Sankey diagram")
            return ""
        
        logger.info("Creating Sankey diagram...")
        
        # 提取数据并按真实计数构建流向
        raw_factors = enhanced_data.get('raw_extracted_factors', {})
        drivers = raw_factors.get('drivers', [])
        barriers = raw_factors.get('barriers', [])
        data_sources = list(enhanced_data.get('data_source_stratification', {}).get('source_distribution', {}).keys())
        if not data_sources:
            data_sources = ['政策端', '市场端', '舆论端']
        source_counts = enhanced_data.get('data_source_stratification', {}).get('source_distribution',
                                                                              enhanced_data.get('data_source_distribution', {}))

        # PESTEL映射
        def to_pestel(cat: str) -> str:
            mapping = {
                'Policy': '政治因素', 'Environmental': '环境因素', 'Environment': '环境因素',
                'Social': '社会因素', 'Technology': '技术因素', 'Technical': '技术因素',
                'Economic': '经济因素', 'Finance': '经济因素', 'Legal': '法律因素',
            }
            return mapping.get(cat, '社会因素')

        driver_cats = Counter([to_pestel(d.get('category', '')) for d in drivers])
        barrier_cats = Counter([to_pestel(b.get('category', '')) for b in barriers])

        stakeholder_counts = Counter()
        for item in drivers + barriers:
            stakeholder = item.get('stakeholder', '其他') or '其他'
            stakeholder_counts[stakeholder] += 1

        # 节点列表
        display_ds = [self.wrap_plotly(s, width=6, max_lines=2) for s in data_sources]
        factor_types = ['驱动因素', '阻碍因素']
        pestel_cats = list(self.pestel_colors.keys())
        display_pestel = [self.wrap_plotly(c, width=6, max_lines=2) for c in pestel_cats]
        stakeholders = list(stakeholder_counts.keys()) if stakeholder_counts else ['政府', '企业', '公众']
        display_stakeholders = [self.wrap_plotly(s, width=8, max_lines=2) for s in stakeholders]

        labels = display_ds + factor_types + display_pestel + display_stakeholders

        idx = {name: i for i, name in enumerate(labels)}

        sources, targets, values, colors = [], [], [], []

        total_source = sum(source_counts.values()) or 1
        driver_ratio = len(drivers) / max(1, len(drivers) + len(barriers))
        # 数据源 -> 驱动/阻碍
        for src, src_disp in zip(data_sources, display_ds):
            src_val = source_counts.get(src, total_source / len(data_sources))
            sources.append(idx[src_disp]); targets.append(idx['驱动因素']); values.append(src_val * driver_ratio)
            sources.append(idx[src_disp]); targets.append(idx['阻碍因素']); values.append(src_val * (1 - driver_ratio))
            colors.extend([self.colors['driver'], self.colors['barrier']])

        # 驱动 -> PESTEL
        for cat, cnt in driver_cats.items():
            target_label = display_pestel[pestel_cats.index(cat)] if cat in pestel_cats else display_pestel[0]
            sources.append(idx['驱动因素']); targets.append(idx.get(target_label, idx[display_pestel[0]])); values.append(cnt)
            colors.append(self.pestel_colors.get(cat, self.colors['driver']))
        # 阻碍 -> PESTEL
        for cat, cnt in barrier_cats.items():
            target_label = display_pestel[pestel_cats.index(cat)] if cat in pestel_cats else display_pestel[0]
            sources.append(idx['阻碍因素']); targets.append(idx.get(target_label, idx[display_pestel[0]])); values.append(cnt)
            colors.append(self.pestel_colors.get(cat, self.colors['barrier']))

        # PESTEL -> 利益相关者
        for cat, cat_disp in zip(pestel_cats, display_pestel):
            for stakeholder, stakeholder_disp in zip(stakeholders, display_stakeholders):
                val = stakeholder_counts.get(stakeholder, 0) / max(1, len(pestel_cats))
                if val:
                    sources.append(idx[cat_disp]); targets.append(idx[stakeholder_disp]); values.append(val)
                    colors.append(self.colors['market'])

        fig = go.Figure(data=[go.Sankey(
            arrangement='snap',
            node=dict(
                pad=16,
                thickness=18,
                line=dict(color='#d0d0d0', width=0.6),
                label=labels,
                color=[self._to_hex(self.colors['policy'])] * len(data_sources) +
                    [self._to_hex(self.colors['driver']), self._to_hex(self.colors['barrier'])] +
                    [self._to_hex(self.pestel_colors.get(cat, self.colors['neutral'])) for cat in pestel_cats] +
                    [self._to_hex(self.colors['market'])] * len(stakeholders)
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=['rgba(120,120,120,0.35)' for _ in values]
            )
        )])

        fig.update_layout(
            title_text="绿电消费因素流向桑基图（数据源→驱动/阻碍→PESTEL→利益相关者）",
            font_size=12,
            height=650,
            paper_bgcolor=self.colors['background'],
            plot_bgcolor=self.colors['background']
        )

        output_path = self.output_dir / f"sankey_diagram_{self.timestamp}.html"
        fig.write_html(str(output_path))

        png_path = self.output_dir / f"sankey_diagram_{self.timestamp}.png"
        try:
            fig.write_image(str(png_path), width=1400, height=900)
        except Exception as e:
            logger.warning(f"Could not save Sankey as PNG: {e}")

        logger.info(f"Saved Sankey diagram to {output_path}")
        return str(output_path)
    
    def create_statistical_summary(self, enhanced_data: Dict) -> str:
        """
        创建计量统计摘要图表
        """
        logger.info("Creating statistical summary...")
        
        temporal = enhanced_data.get('temporal_evolution', {})
        causal = enhanced_data.get('causal_chain_analysis', {})
        clustering = enhanced_data.get('semantic_clustering', {})
        conflicts = enhanced_data.get('policy_market_conflicts', {})
        aspect = enhanced_data.get('aspect_sentiment_analysis', {})
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        
        # 1. 时间分布统计
        ax1 = axes[0, 0]
        time_dist = temporal.get('time_distribution', {})
        valid_years = {k: v for k, v in time_dist.items() if k != 'unknown' and k.isdigit()}
        if valid_years:
            total_docs = sum(valid_years.values())
            unknown = time_dist.get('unknown', 0)
            
            ax1.bar(['有时间标签', '未知时间'], [total_docs, unknown], 
                   color=[self.colors['driver'], self.colors['neutral']])
            ax1.set_ylabel('文档数', fontsize=12)
            ax1.set_title(f'时间标签分布\n(总计: {total_docs + unknown})', fontsize=12, fontweight='bold')
        
        # 2. 因果链统计
        ax2 = axes[0, 1]
        chain_count = causal.get('total_chains_extracted', 0)
        core_chain_count = len(causal.get('核心因果链', []))
        feedback_count = len(causal.get('反馈循环识别', []))
        
        ax2.bar(['提取因果链', '核心因果链', '反馈循环'], 
               [chain_count, core_chain_count, feedback_count],
               color=[self.colors['policy'], self.colors['driver'], self.colors['market']])
        ax2.set_ylabel('数量', fontsize=12)
        ax2.set_title('因果链分析统计', fontsize=12, fontweight='bold')
        
        # 3. 语义聚类统计
        ax3 = axes[0, 2]
        summary = clustering.get('clustering_summary', {})
        total_factors = summary.get('total_factors', 0)
        core_count = summary.get('core_indicators_count', len(clustering.get('core_indicators', [])))
        compression = summary.get('compression_ratio', 0)
        
        ax3.bar(['原始因子', '核心指标'], [total_factors, core_count],
               color=[self.colors['neutral'], self.colors['driver']])
        ax3.set_ylabel('数量', fontsize=12)
        ax3.set_title(f'语义聚类效果\n(压缩率: {compression:.2%})', fontsize=12, fontweight='bold')
        
        # 4. 矛盾分析统计
        ax4 = axes[1, 0]
        conflict_list = conflicts.get('identified_conflicts', [])
        conflict_count = len(conflict_list)
        high_severity = sum(1 for c in conflict_list if c.get('gap_severity') == 'high')
        
        ax4.bar(['识别矛盾总数', '高严重度'], [conflict_count, high_severity],
               color=[self.colors['market'], self.colors['barrier']])
        ax4.set_ylabel('数量', fontsize=12)
        ax4.set_title('政策-市场矛盾统计', fontsize=12, fontweight='bold')
        
        # 5. 情感分析统计
        ax5 = axes[1, 1]
        aspect_count = len(aspect.get('aspect_sentiments', {}))
        pain_count = aspect.get('total_pain_points', 0)
        stakeholder_count = len(aspect.get('stakeholder_sentiments', {}))
        
        ax5.bar(['分析方面', '痛点数', '利益相关者'], 
               [aspect_count, pain_count, stakeholder_count],
               color=[self.colors['policy'], self.colors['barrier'], self.colors['public']])
        ax5.set_ylabel('数量', fontsize=12)
        ax5.set_title('细粒度情感分析统计', fontsize=12, fontweight='bold')
        
        # 6. 综合数据质量评分
        ax6 = axes[1, 2]
        # 计算综合评分
        scores = {
            '时间数据完整性': min(1.0, sum(valid_years.values()) / max(1, sum(valid_years.values()) + time_dist.get('unknown', 0))),
            '因果链提取质量': min(1.0, chain_count / 50) if chain_count else 0,
            '语义聚类效果': 1 - compression if compression else 0.5,
            '矛盾识别覆盖': min(1.0, conflict_count / 10) if conflict_count else 0,
            '情感分析深度': min(1.0, aspect_count / 10) if aspect_count else 0
        }
        
        categories = list(scores.keys())
        values = list(scores.values())
        
        # 雷达图
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        values_plot = values + [values[0]]
        angles += angles[:1]
        
        ax6 = plt.subplot(2, 3, 6, polar=True)
        ax6.plot(angles, values_plot, 'o-', linewidth=2, color=self.colors['driver'])
        ax6.fill(angles, values_plot, alpha=0.25, color=self.colors['driver'])
        ax6.set_xticks(angles[:-1])
        ax6.set_xticklabels(categories, fontsize=8)
        ax6.set_title('分析质量评分', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        output_path = self.output_dir / f"statistical_summary_{self.timestamp}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=self.colors['background'])
        plt.close()
        
        logger.info(f"Saved statistical summary to {output_path}")
        return str(output_path)
    
    def generate_all_visualizations(self, enhanced_data: Dict) -> Dict[str, str]:
        """
        生成所有可视化图表
        """
        logger.info("="*60)
        logger.info("开始生成深度分析可视化")
        logger.info("="*60)
        
        results = {}
        
        # 1. 时间演化图
        temporal_data = enhanced_data.get('temporal_evolution', {})
        if temporal_data:
            results['temporal_evolution'] = self.create_temporal_evolution_chart(temporal_data)
        
        # 2. 因果链网络图
        causal_data = enhanced_data.get('causal_chain_analysis', {})
        if causal_data:
            results['causal_network'] = self.create_causal_network(causal_data)
        
        # 3. 语义聚类图
        clustering_data = enhanced_data.get('semantic_clustering', {})
        if clustering_data:
            results['semantic_clustering'] = self.create_semantic_clustering_chart(clustering_data)
        
        # 4. 矛盾分析图
        conflict_data = enhanced_data.get('policy_market_conflicts', {})
        if conflict_data:
            results['conflict_analysis'] = self.create_conflict_analysis_chart(conflict_data)
        
        # 5. 细粒度情感分析图
        aspect_data = enhanced_data.get('aspect_sentiment_analysis', {})
        if aspect_data:
            results['aspect_sentiment'] = self.create_aspect_sentiment_heatmap(aspect_data)
        
        # 6. 桑基图
        results['sankey_diagram'] = self.create_sankey_diagram(enhanced_data)
        
        # 7. 统计摘要
        results['statistical_summary'] = self.create_statistical_summary(enhanced_data)
        
        # 过滤空结果
        results = {k: v for k, v in results.items() if v}
        
        logger.info("="*60)
        logger.info(f"生成了 {len(results)} 个可视化图表")
        for name, path in results.items():
            logger.info(f"  ✓ {name}: {path}")
        logger.info("="*60)
        
        return results


def main():
    """主函数"""
    logger.info("="*80)
    logger.info("🚀 开始深度分析与可视化")
    logger.info("="*80)
    
    # 查找最新的增强分析文件
    final_dir = Path("data/output/final")
    enhanced_files = sorted(final_dir.glob("enhanced_analysis_*.json"), reverse=True)
    
    if not enhanced_files:
        logger.error("未找到增强分析结果文件!")
        return
    
    latest_enhanced = enhanced_files[0]
    logger.info(f"使用增强分析文件: {latest_enhanced}")
    
    # 创建可视化器
    visualizer = DeepAnalysisVisualizer()
    
    # 加载数据
    enhanced_data, _ = visualizer.load_analysis_data(str(latest_enhanced))
    
    # 生成所有可视化
    results = visualizer.generate_all_visualizations(enhanced_data)
    
    # 保存结果索引
    index_file = visualizer.output_dir / f"visualization_index_{visualizer.timestamp}.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': visualizer.timestamp,
            'source_file': str(latest_enhanced),
            'visualizations': results
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ 可视化完成! 结果保存到: {visualizer.output_dir}")
    logger.info(f"📄 索引文件: {index_file}")


if __name__ == "__main__":
    main()

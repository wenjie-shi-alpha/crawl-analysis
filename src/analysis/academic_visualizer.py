"""
Academic-level visualization module for green power consumption research.
Generates publication-quality charts and figures for academic papers.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib import font_manager

# Logger setup first (needed for setup_chinese_fonts)
logger = logging.getLogger(__name__)

# Try to set up Chinese fonts
def setup_chinese_fonts():
    """Setup Chinese font support for matplotlib."""
    # Clear font cache to force reload (compatible with all matplotlib versions)
    try:
        cache_dir = Path(matplotlib.get_cachedir())
        for cache_file in cache_dir.glob('*.json'):
            cache_file.unlink(missing_ok=True)
    except Exception as e:
        logger.debug(f"Cache clear issue: {e}")
    
    # Priority list of Chinese fonts (commonly available on Linux)
    chinese_fonts = [
        'WenQuanYi Micro Hei',      # 文泉驿微米黑
        'WenQuanYi Zen Hei',        # 文泉驿正黑
        'Noto Sans CJK SC',         # Google Noto 简体中文
        'Noto Sans CJK TC',         # Google Noto 繁体中文
        'AR PL UMing CN',           # 文鼎明体
        'AR PL UKai CN',            # 文鼎楷体
        'SimHei',                   # 黑体 (Windows)
        'Microsoft YaHei',          # 微软雅黑 (Windows)
        'Source Han Sans CN',       # 思源黑体
        'DejaVu Sans',              # Fallback
    ]
    
    available_fonts = set(f.name for f in font_manager.fontManager.ttflist)
    logger.debug(f"Available fonts: {sorted(available_fonts)[:20]}...")  # Print first 20
    
    # Find the first available Chinese font
    selected_font = None
    for font in chinese_fonts:
        if font in available_fonts:
            selected_font = font
            logger.info(f"Found Chinese font: {font}")
            break
    
    if selected_font:
        # Set as the primary font for all text
        plt.rcParams['font.sans-serif'] = [selected_font, 'DejaVu Sans', 'Arial']
        plt.rcParams['font.family'] = 'sans-serif'
        logger.info(f"Using Chinese font: {selected_font}")
    else:
        # Try to find any CJK font
        cjk_fonts = [f.name for f in font_manager.fontManager.ttflist 
                     if 'CJK' in f.name or 'Hei' in f.name or 'Ming' in f.name or 'Kai' in f.name or 'WenQuanYi' in f.name]
        logger.debug(f"CJK fonts found: {cjk_fonts}")
        if cjk_fonts:
            plt.rcParams['font.sans-serif'] = [cjk_fonts[0], 'DejaVu Sans', 'Arial']
            plt.rcParams['font.family'] = 'sans-serif'
            logger.info(f"Using CJK font: {cjk_fonts[0]}")
        else:
            logger.warning("No Chinese font found, using default")
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
            plt.rcParams['font.family'] = 'sans-serif'
    
    plt.rcParams['axes.unicode_minus'] = False

setup_chinese_fonts()

# Set academic paper style AFTER font setup
sns.set_theme(context="talk", style="whitegrid", font_scale=1.05)
sns.set_palette("colorblind")
plt.rcParams['axes.facecolor'] = '#fbfbfb'
plt.rcParams['figure.facecolor'] = 'white'

# Re-apply font settings after style (style may reset them)
def ensure_chinese_fonts():
    """Ensure Chinese fonts are still set after style changes."""
    chinese_fonts = [
        'WenQuanYi Micro Hei',
        'WenQuanYi Zen Hei',
        'Noto Sans CJK SC',
    ]
    available_fonts = set(f.name for f in font_manager.fontManager.ttflist)
    for font in chinese_fonts:
        if font in available_fonts:
            plt.rcParams['font.sans-serif'] = [font, 'DejaVu Sans', 'Arial']
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['axes.unicode_minus'] = False
            break

ensure_chinese_fonts()


class AcademicVisualizer:
    """Generate academic publication-quality visualizations."""
    
    def __init__(self, output_dir: str = "output/figures", dpi: int = 300):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Academic color palettes
        self.driving_colors = sns.color_palette("crest", 6)
        self.barrier_colors = sns.color_palette("rocket", 6)
        self.comparison_colors = ["#2ecc71", "#e74c3c"]  # Green for drivers, Red for barriers
        self.sentiment_palette = ['#2ecc71', '#f1c40f', '#e74c3c']
        self.neutral_color = "#34495e"
        
        self.figure_counter = 0
        self.generated_figures = []
    
    def _get_figure_path(self, name: str) -> Path:
        """Generate figure path with counter."""
        self.figure_counter += 1
        path = self.output_dir / f"fig_{self.figure_counter:02d}_{name}_{self.timestamp}.png"
        self.generated_figures.append(str(path))
        return path
    
    def _prepare_driver_summary(self, driving_factors: Dict) -> List[Dict[str, Any]]:
        summary = driving_factors.get("category_summary")
        if summary:
            return summary
        
        fallback = []
        for category, factors in driving_factors.get("driving_factors", {}).items():
            if not isinstance(factors, list) or not factors:
                continue
            values = [f.get("impact_score", 0) for f in factors if isinstance(f, dict)]
            avg_score = float(np.mean(values)) if values else 0.0
            top_factor = max(factors, key=lambda f: f.get("impact_score", 0) if isinstance(f, dict) else 0)
            fallback.append({
                "category": category,
                "count": len(factors),
                "avg_score": round(avg_score, 2),
                "top_factor": top_factor.get("factor", "") if isinstance(top_factor, dict) else str(top_factor),
                "sample_evidence": top_factor.get("evidence", "") if isinstance(top_factor, dict) else "",
                "top_keywords": []
            })
        return fallback
    
    def _prepare_barrier_summary(self, barrier_analysis: Dict) -> List[Dict[str, Any]]:
        summary = barrier_analysis.get("category_summary")
        if summary:
            return summary
        
        fallback = []
        for category, barriers in barrier_analysis.get("barriers", {}).items():
            if not isinstance(barriers, list) or not barriers:
                continue
            severity_values = [b.get("severity_score", 0) for b in barriers if isinstance(b, dict)]
            difficulty_values = [b.get("difficulty_score", 0) for b in barriers if isinstance(b, dict)]
            avg_severity = float(np.mean(severity_values)) if severity_values else 0.0
            avg_difficulty = float(np.mean(difficulty_values)) if difficulty_values else 0.0
            top_barrier = max(barriers, key=lambda b: b.get("severity_score", 0) if isinstance(b, dict) else 0)
            fallback.append({
                "category": category,
                "count": len(barriers),
                "avg_severity": round(avg_severity, 2),
                "avg_difficulty": round(avg_difficulty, 2),
                "top_barrier": top_barrier.get("barrier", "") if isinstance(top_barrier, dict) else str(top_barrier),
                "sample_evidence": top_barrier.get("evidence", "") if isinstance(top_barrier, dict) else "",
                "top_keywords": []
            })
        return fallback
    
    def _prepare_barrier_dataframe(self, barrier_analysis: Dict) -> pd.DataFrame:
        barriers = barrier_analysis.get("barriers", {})
        data = []
        for category, barrier_list in barriers.items():
            for barrier in barrier_list[:5]:
                if isinstance(barrier, dict):
                    data.append({
                        "类别": category.replace("障碍", ""),
                        "障碍": barrier.get("barrier", ""),
                        "严重程度": barrier.get("severity_score", 3),
                        "克服难度": barrier.get("difficulty_score", 3)
                    })
        return pd.DataFrame(data)
    
    @staticmethod
    def _attitude_string_to_score(attitude: str) -> float:
        if not attitude:
            return 0.5
        positives = ["积极", "支持", "推动", "乐观", "强化"]
        negatives = ["消极", "阻碍", "谨慎", "担忧", "风险"]
        attitude = str(attitude)
        score = 0.5
        if any(word in attitude for word in positives):
            score += 0.3
        if any(word in attitude for word in negatives):
            score -= 0.3
        return min(1.0, max(0.0, score))
    
    def create_pestel_radar_chart(self, driving_factors: Dict) -> str:
        """Create PESTEL framework radar chart for driving factors."""
        categories = ["政治", "经济", "社会", "技术", "环境", "法律"]
        
        # Calculate scores for each PESTEL category
        scores = []
        for cat in categories:
            cat_key = f"{cat}因素"
            factors = driving_factors.get("driving_factors", {}).get(cat_key, [])
            if factors:
                avg_score = np.mean([f.get("impact_score", 3) for f in factors if isinstance(f, dict)])
            else:
                avg_score = 0
            scores.append(avg_score)
        
        # Normalize scores
        max_score = max(scores) if max(scores) > 0 else 1
        scores = [s / max_score * 5 for s in scores]
        
        # Create radar chart
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        scores_plot = scores + [scores[0]]  # Close the polygon
        angles += angles[:1]
        
        ax.plot(angles, scores_plot, 'o-', linewidth=2, color='#3498db', markersize=8)
        ax.fill(angles, scores_plot, alpha=0.25, color='#3498db')
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=12, fontweight='bold')
        ax.set_ylim(0, 5)
        ax.set_title('PESTEL框架驱动因素分析\nPESTEL Framework Analysis of Driving Factors', 
                     fontsize=14, fontweight='bold', pad=20)
        
        # Add score labels
        for angle, score, cat in zip(angles[:-1], scores, categories):
            ax.annotate(f'{score:.1f}', xy=(angle, score), xytext=(5, 5),
                       textcoords='offset points', fontsize=10)
        
        plt.tight_layout()
        path = self._get_figure_path("pestel_radar")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"PESTEL雷达图已保存: {path}")
        return str(path)
    
    def create_barrier_severity_heatmap(self, barrier_analysis: Dict) -> str:
        """Create heatmap showing barrier severity and difficulty to overcome."""
        df = self._prepare_barrier_dataframe(barrier_analysis)
        if df.empty:
            logger.warning("没有障碍数据用于生成热力图")
            return ""
        
        severity_pivot = df.pivot_table(values="严重程度", index="障碍", columns="类别", aggfunc='mean')
        if severity_pivot.empty:
            logger.warning("严重程度数据不足，跳过热力图生成")
            return ""
        
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(
            severity_pivot,
            ax=ax,
            cmap="YlOrRd",
            annot=True,
            fmt=".1f",
            linewidths=0.5,
            vmin=1,
            vmax=5,
            cbar_kws={'label': '严重程度'}
        )
        ax.set_title('障碍因素严重程度矩阵\nBarrier Severity Matrix', fontsize=13, fontweight='bold')
        ax.set_xlabel('')
        ax.set_ylabel('')
        plt.tight_layout()
        path = self._get_figure_path("barrier_severity_heatmap")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"障碍热力图已保存: {path}")
        return str(path)
    
    def create_barrier_difficulty_heatmap(self, barrier_analysis: Dict) -> str:
        """Create difficulty heatmap as a standalone figure."""
        df = self._prepare_barrier_dataframe(barrier_analysis)
        if df.empty:
            logger.warning("没有障碍数据用于生成难度热力图")
            return ""
        
        difficulty_pivot = df.pivot_table(values="克服难度", index="障碍", columns="类别", aggfunc='mean')
        if difficulty_pivot.empty:
            logger.warning("克服难度数据不足")
            return ""
        
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(
            difficulty_pivot,
            ax=ax,
            cmap="YlGnBu",
            annot=True,
            fmt=".1f",
            linewidths=0.5,
            vmin=1,
            vmax=5,
            cbar_kws={'label': '克服难度'}
        )
        ax.set_title('障碍因素克服难度矩阵\nDifficulty to Overcome Matrix', fontsize=13, fontweight='bold')
        ax.set_xlabel('')
        ax.set_ylabel('')
        plt.tight_layout()
        path = self._get_figure_path("barrier_difficulty_heatmap")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"障碍难度热力图已保存: {path}")
        return str(path)
    
    def create_driver_strength_chart(self, driving_factors: Dict) -> str:
        """Highlight average impact of each driver category."""
        summary = self._prepare_driver_summary(driving_factors)
        if not summary:
            logger.warning("缺少驱动因素摘要，无法生成强度图")
            return ""
        
        df = pd.DataFrame(summary)
        df = df.sort_values("avg_score", ascending=True)
        y_pos = np.arange(len(df))
        colors = sns.light_palette("#2563eb", n_colors=len(df))
        
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.barh(y_pos, df["avg_score"], color=colors, alpha=0.9)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df["category"])
        ax.set_xlim(0, 5.1)
        ax.set_xlabel('平均影响分 (1-5)', fontsize=12)
        ax.set_title('PESTEL驱动因素强度\nDriver Strength by Dimension', fontsize=14, fontweight='bold')
        ax.grid(axis='x', linestyle='--', alpha=0.4)
        ax.invert_yaxis()
        
        for i, (idx, row) in enumerate(df.iterrows()):
            ax.text(
                row["avg_score"] + 0.05,
                i,
                f"{row['avg_score']:.1f}分 · n={row['count']}",
                va='center',
                fontsize=10,
                color=self.neutral_color
            )
        
        plt.tight_layout()
        path = self._get_figure_path("driver_strength")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        logger.info(f"驱动因素强度图已保存: {path}")
        return str(path)
    
    def create_barrier_risk_scatter(self, barrier_analysis: Dict) -> str:
        """Create scatter plot of barrier severity vs difficulty."""
        summary = self._prepare_barrier_summary(barrier_analysis)
        if not summary:
            logger.warning("缺少障碍因素摘要，无法生成风险散点图")
            return ""
        
        df = pd.DataFrame(summary)
        fig, ax = plt.subplots(figsize=(9, 6))
        sizes = 120.0 + np.array(df["count"]) * 8
        scatter = ax.scatter(
            df["avg_difficulty"],
            df["avg_severity"],
            s=sizes,
            c=df["avg_severity"],
            cmap="Reds",
            alpha=0.85,
            edgecolors='white',
            linewidth=1.2
        )
        
        for _, row in df.iterrows():
            ax.text(
                row["avg_difficulty"] + 0.05,
                row["avg_severity"] + 0.05,
                row["category"].replace("障碍", ""),
                fontsize=10,
                color=self.neutral_color
            )
        
        ax.set_xlim(1, 5.1)
        ax.set_ylim(1, 5.1)
        ax.set_xlabel('克服难度 (1-5)', fontsize=12)
        ax.set_ylabel('严重程度 (1-5)', fontsize=12)
        ax.set_title('障碍因素风险位置\nBarrier Risk Landscape', fontsize=14, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.3)
        plt.colorbar(scatter, ax=ax, label='严重程度')
        
        plt.tight_layout()
        path = self._get_figure_path("barrier_risk_scatter")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        logger.info(f"障碍风险散点图已保存: {path}")
        return str(path)
    
    def create_keyword_focus_chart(self, highlights: Dict[str, Any]) -> str:
        """Create a minimalist lollipop chart for top keywords."""
        keywords = highlights.get("keyword_frequency", []) if highlights else []
        if not keywords:
            logger.warning("缺少关键词数据，无法生成关键词图")
            return ""
        
        df = pd.DataFrame(keywords[:10])
        df = df.iloc[::-1]  # show most frequent at top
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hlines(df["keyword"], xmin=0, xmax=df["count"], color="#d0d5dd", linewidth=2)
        ax.plot(df["count"], df["keyword"], "o", color="#1f78b4", markersize=10)
        
        ax.set_xlabel('出现次数', fontsize=12)
        ax.set_title('高频研究关键词\nTop Research Keywords', fontsize=14, fontweight='bold')
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        plt.tight_layout()
        
        path = self._get_figure_path("keyword_focus")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        logger.info(f"关键词图已保存: {path}")
        return str(path)
    
    def create_stakeholder_attitudes_chart(self, sentiment_analysis: Dict) -> str:
        """Visualize stakeholder attitudes with calibrated scores."""
        stakeholder_attitudes = sentiment_analysis.get("stakeholder_attitudes", {})
        if not stakeholder_attitudes:
            logger.warning("缺少利益相关方数据，无法生成态度图")
            return ""
        
        rows = []
        for stakeholder, description in stakeholder_attitudes.items():
            rows.append({
                "stakeholder": stakeholder,
                "score": self._attitude_string_to_score(description),
                "description": description
            })
        df = pd.DataFrame(rows)
        df = df.sort_values("score")
        y_pos = np.arange(len(df))
        colors = sns.light_palette("#6c5ce7", n_colors=len(df))
        
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(y_pos, df["score"], color=colors, alpha=0.95)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df["stakeholder"])
        ax.set_xlim(0, 1)
        ax.set_xlabel('态度得分 (0=消极, 1=积极)', fontsize=12)
        ax.set_title('利益相关方态度\nStakeholder Sentiment', fontsize=14, fontweight='bold')
        ax.axvline(x=0.5, color='gray', linestyle='--', linewidth=1)
        
        for i, (idx, row) in enumerate(df.iterrows()):
            ax.text(
                row["score"] + 0.02,
                i,
                row["description"][:18],
                va='center',
                fontsize=9,
                color=self.neutral_color
            )
        
        plt.tight_layout()
        path = self._get_figure_path("stakeholder_attitudes")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        logger.info(f"利益相关方态度图已保存: {path}")
        return str(path)
    
    def create_driver_barrier_comparison(self, driving_factors: Dict, barrier_analysis: Dict) -> str:
        """Create side-by-side comparison of drivers and barriers."""
        fig, axes = plt.subplots(1, 2, figsize=(16, 10))
        
        # Process driving factors
        driver_data = []
        for category, factors in driving_factors.get("driving_factors", {}).items():
            count = len(factors) if isinstance(factors, list) else 0
            avg_impact = np.mean([f.get("impact_score", 3) for f in factors if isinstance(f, dict)]) if factors else 0
            driver_data.append({
                "类别": category.replace("因素", ""),
                "数量": count,
                "平均影响": avg_impact
            })
        
        if driver_data:
            df_drivers = pd.DataFrame(driver_data)
            x = range(len(df_drivers))
            bars1 = axes[0].bar(x, df_drivers["数量"], color=self.driving_colors[2], alpha=0.8)
            axes[0].set_xticks(x)
            axes[0].set_xticklabels(df_drivers["类别"], rotation=45, ha='right')
            axes[0].set_ylabel('因素数量', fontsize=11)
            axes[0].set_title('驱动因素分布\nDistribution of Driving Factors', fontsize=12, fontweight='bold')
            
            # Add impact score as secondary y-axis
            ax1_twin = axes[0].twinx()
            ax1_twin.plot(x, df_drivers["平均影响"], 'ro-', linewidth=2, markersize=8, label='平均影响分')
            ax1_twin.set_ylabel('平均影响分 (1-5)', color='red', fontsize=11)
            ax1_twin.tick_params(axis='y', labelcolor='red')
            ax1_twin.legend(loc='upper right')
        
        # Process barriers
        barrier_data = []
        for category, barriers in barrier_analysis.get("barriers", {}).items():
            count = len(barriers) if isinstance(barriers, list) else 0
            avg_severity = np.mean([b.get("severity_score", 3) for b in barriers if isinstance(b, dict)]) if barriers else 0
            barrier_data.append({
                "类别": category.replace("障碍", ""),
                "数量": count,
                "平均严重程度": avg_severity
            })
        
        if barrier_data:
            df_barriers = pd.DataFrame(barrier_data)
            x = range(len(df_barriers))
            bars2 = axes[1].bar(x, df_barriers["数量"], color=self.barrier_colors[2], alpha=0.8)
            axes[1].set_xticks(x)
            axes[1].set_xticklabels(df_barriers["类别"], rotation=45, ha='right')
            axes[1].set_ylabel('因素数量', fontsize=11)
            axes[1].set_title('障碍因素分布\nDistribution of Barriers', fontsize=12, fontweight='bold')
            
            # Add severity score as secondary y-axis
            ax2_twin = axes[1].twinx()
            ax2_twin.plot(x, df_barriers["平均严重程度"], 'ro-', linewidth=2, markersize=8, label='平均严重程度')
            ax2_twin.set_ylabel('平均严重程度 (1-5)', color='red', fontsize=11)
            ax2_twin.tick_params(axis='y', labelcolor='red')
            ax2_twin.legend(loc='upper right')
        
        plt.tight_layout()
        path = self._get_figure_path("driver_barrier_comparison")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"驱动障碍对比图已保存: {path}")
        return str(path)
    
    def create_policy_priority_matrix(self, policy_recommendations: Dict) -> str:
        """Create policy priority matrix (urgency vs impact)."""
        priority_matrix = policy_recommendations.get("priority_matrix", {})
        
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Define quadrants
        quadrants = {
            "high_urgency_high_impact": (0.75, 0.75, "#2ecc71", "优先实施\nPriority"),
            "high_urgency_low_impact": (0.75, 0.25, "#f39c12", "快速行动\nQuick Wins"),
            "low_urgency_high_impact": (0.25, 0.75, "#3498db", "战略规划\nStrategic"),
            "low_urgency_low_impact": (0.25, 0.25, "#95a5a6", "低优先级\nLow Priority")
        }
        
        # Draw quadrants
        for quadrant, (x, y, color, label) in quadrants.items():
            rect = mpatches.FancyBboxPatch((x-0.2, y-0.2), 0.4, 0.4, 
                                           boxstyle="round,pad=0.02",
                                           facecolor=color, alpha=0.3,
                                           edgecolor=color, linewidth=2)
            ax.add_patch(rect)
            ax.text(x, y+0.15, label, ha='center', va='center', fontsize=12, fontweight='bold')
            
            # Add policies in this quadrant
            policies = priority_matrix.get(quadrant, [])
            if policies:
                policy_text = "\n".join([f"• {p[:20]}..." if len(str(p)) > 20 else f"• {p}" 
                                        for p in policies[:3]])
                ax.text(x, y-0.05, policy_text, ha='center', va='top', fontsize=9, 
                       wrap=True)
        
        # Draw axes
        ax.axhline(y=0.5, color='gray', linestyle='--', linewidth=1)
        ax.axvline(x=0.5, color='gray', linestyle='--', linewidth=1)
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel('紧迫性 (Urgency) →', fontsize=12, fontweight='bold')
        ax.set_ylabel('影响力 (Impact) →', fontsize=12, fontweight='bold')
        ax.set_title('政策优先级矩阵\nPolicy Priority Matrix', fontsize=14, fontweight='bold')
        
        # Remove ticks
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Add annotations
        ax.text(0.02, 0.02, '低 Low', fontsize=10, color='gray')
        ax.text(0.92, 0.02, '高 High', fontsize=10, color='gray')
        ax.text(0.02, 0.96, '高 High', fontsize=10, color='gray', rotation=90)
        
        plt.tight_layout()
        path = self._get_figure_path("policy_priority_matrix")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"政策优先级矩阵已保存: {path}")
        return str(path)
    
    def create_sentiment_distribution(self, sentiment_analysis: Dict) -> str:
        """Create minimalist stacked sentiment profile."""
        sentiment_dist = sentiment_analysis.get("sentiment_distribution", {})
        if not sentiment_dist:
            logger.warning("缺少情感分布数据，无法生成情感图")
            return ""
        
        values = [
            sentiment_dist.get("positive", 0),
            sentiment_dist.get("neutral", 0),
            sentiment_dist.get("negative", 0)
        ]
        labels = ['积极 Positive', '中立 Neutral', '消极 Negative']
        
        fig, ax = plt.subplots(figsize=(8, 3.6))
        left = 0
        for value, label, color in zip(values, labels, self.sentiment_palette):
            ax.barh(
                ["舆情倾向 Overall"],
                value,
                left=left,
                color=color,
                alpha=0.9,
                height=0.5
            )
            ax.text(
                left + value / 2,
                0,
                f"{label}\n{value*100:.1f}%",
                ha='center',
                va='center',
                color='white',
                fontweight='bold',
                fontsize=10
            )
            left += value
        
        ax.set_xlim(0, 1)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax.set_yticks([])
        ax.set_title('舆情情感剖面\nSentiment Profile', fontsize=14, fontweight='bold')
        dominant = sentiment_analysis.get("dominant_sentiment")
        if dominant:
            ax.text(
                0.02,
                -0.4,
                f"主导倾向：{dominant}",
                fontsize=10,
                color=self.neutral_color
            )
        plt.tight_layout()
        path = self._get_figure_path("sentiment_profile")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"情感分布图已保存: {path}")
        return str(path)
    
    def create_theoretical_framework_diagram(self) -> str:
        """Create a conceptual framework diagram for the research."""
        fig, ax = plt.subplots(figsize=(16, 12))
        
        # Title
        ax.text(0.5, 0.95, '中国居民绿色电力消费研究理论框架\nTheoretical Framework for Green Power Consumption Research',
               ha='center', va='top', fontsize=16, fontweight='bold', transform=ax.transAxes)
        
        # Draw boxes for different theories
        theories = [
            {"name": "计划行为理论\n(TPB)", "x": 0.15, "y": 0.7, "color": "#3498db"},
            {"name": "价值-信念-规范\n(VBN)", "x": 0.5, "y": 0.7, "color": "#2ecc71"},
            {"name": "技术接受模型\n(TAM)", "x": 0.85, "y": 0.7, "color": "#e74c3c"},
        ]
        
        for theory in theories:
            rect = mpatches.FancyBboxPatch((theory["x"]-0.12, theory["y"]-0.08), 0.24, 0.16,
                                           boxstyle="round,pad=0.02",
                                           facecolor=theory["color"], alpha=0.3,
                                           edgecolor=theory["color"], linewidth=2,
                                           transform=ax.transAxes)
            ax.add_patch(rect)
            ax.text(theory["x"], theory["y"], theory["name"], ha='center', va='center',
                   fontsize=11, fontweight='bold', transform=ax.transAxes)
        
        # Central construct
        center_rect = mpatches.FancyBboxPatch((0.35, 0.4), 0.3, 0.12,
                                               boxstyle="round,pad=0.02",
                                               facecolor="#9b59b6", alpha=0.3,
                                               edgecolor="#9b59b6", linewidth=3,
                                               transform=ax.transAxes)
        ax.add_patch(center_rect)
        ax.text(0.5, 0.46, '绿色电力消费意愿与行为\nGreen Power Consumption\nIntention & Behavior',
               ha='center', va='center', fontsize=12, fontweight='bold', transform=ax.transAxes)
        
        # Driver and barrier boxes
        driver_rect = mpatches.FancyBboxPatch((0.05, 0.15), 0.35, 0.18,
                                               boxstyle="round,pad=0.02",
                                               facecolor="#27ae60", alpha=0.2,
                                               edgecolor="#27ae60", linewidth=2,
                                               transform=ax.transAxes)
        ax.add_patch(driver_rect)
        ax.text(0.225, 0.28, '驱动因素 Drivers', ha='center', va='top',
               fontsize=11, fontweight='bold', color='#27ae60', transform=ax.transAxes)
        ax.text(0.225, 0.22, '• 政策激励 • 环保意识\n• 经济效益 • 社会规范',
               ha='center', va='center', fontsize=9, transform=ax.transAxes)
        
        barrier_rect = mpatches.FancyBboxPatch((0.6, 0.15), 0.35, 0.18,
                                                boxstyle="round,pad=0.02",
                                                facecolor="#c0392b", alpha=0.2,
                                                edgecolor="#c0392b", linewidth=2,
                                                transform=ax.transAxes)
        ax.add_patch(barrier_rect)
        ax.text(0.775, 0.28, '障碍因素 Barriers', ha='center', va='top',
               fontsize=11, fontweight='bold', color='#c0392b', transform=ax.transAxes)
        ax.text(0.775, 0.22, '• 高成本 • 信息不对称\n• 制度缺陷 • 心理障碍',
               ha='center', va='center', fontsize=9, transform=ax.transAxes)
        
        # Arrows
        arrow_style = dict(arrowstyle='->', color='gray', lw=2)
        for theory in theories:
            ax.annotate('', xy=(0.5, 0.52), xytext=(theory["x"], theory["y"]-0.08),
                       arrowprops=arrow_style, transform=ax.transAxes)
        
        ax.annotate('', xy=(0.35, 0.46), xytext=(0.4, 0.33),
                   arrowprops=dict(arrowstyle='->', color='#27ae60', lw=2), transform=ax.transAxes)
        ax.annotate('', xy=(0.65, 0.46), xytext=(0.6, 0.33),
                   arrowprops=dict(arrowstyle='-|>', color='#c0392b', lw=2), transform=ax.transAxes)
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        path = self._get_figure_path("theoretical_framework")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"理论框架图已保存: {path}")
        return str(path)
    
    def create_comprehensive_summary_infographic(self, analysis_results: Dict) -> str:
        """Create a comprehensive summary infographic."""
        fig = plt.figure(figsize=(20, 16))
        gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        # Title
        fig.suptitle('中国居民绿色电力消费研究综合分析\nComprehensive Analysis of Green Power Consumption in China',
                    fontsize=18, fontweight='bold', y=0.98)
        
        # 1. Key findings summary (top left)
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_title('核心发现 Key Findings', fontsize=12, fontweight='bold')
        
        key_findings = analysis_results.get("academic_synthesis", {}).get("key_findings", [])
        if key_findings:
            text = "\n\n".join([f"• {f[:50]}..." if len(f) > 50 else f"• {f}" for f in key_findings[:5]])
        else:
            text = "• 驱动因素：政策激励、环保意识\n• 障碍因素：高成本、信息不对称\n• 建议方向：多元政策协同"
        ax1.text(0.1, 0.9, text, va='top', fontsize=10, wrap=True, transform=ax1.transAxes)
        ax1.axis('off')
        
        # 2. Core drivers (top middle)
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_title('核心驱动因素 Core Drivers', fontsize=12, fontweight='bold')
        
        core_drivers = analysis_results.get("driving_factors_analysis", {}).get("core_drivers", 
                                           ["政策支持", "环保意识", "经济激励", "技术进步"])
        if core_drivers:
            y_pos = np.arange(len(core_drivers[:5]))
            bars = ax2.barh(y_pos, [5-i for i in range(len(core_drivers[:5]))], color=self.driving_colors[2])
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels([d[:15] for d in core_drivers[:5]], fontsize=9)
            ax2.set_xlabel('重要性排序')
        
        # 3. Core barriers (top right)
        ax3 = fig.add_subplot(gs[0, 2])
        ax3.set_title('核心障碍因素 Core Barriers', fontsize=12, fontweight='bold')
        
        core_barriers = analysis_results.get("barriers_analysis", {}).get("core_barriers",
                                            ["高成本", "信息不足", "制度缺陷", "心理障碍"])
        if core_barriers:
            y_pos = np.arange(len(core_barriers[:5]))
            bars = ax3.barh(y_pos, [5-i for i in range(len(core_barriers[:5]))], color=self.barrier_colors[2])
            ax3.set_yticks(y_pos)
            ax3.set_yticklabels([b[:15] for b in core_barriers[:5]], fontsize=9)
            ax3.set_xlabel('严重性排序')
        
        # 4. Sentiment overview (middle left)
        ax4 = fig.add_subplot(gs[1, 0])
        ax4.set_title('舆情分析 Sentiment Analysis', fontsize=12, fontweight='bold')
        
        sentiment = analysis_results.get("sentiment_trend_analysis", {}).get("sentiment_distribution", 
                                         {"positive": 0.4, "neutral": 0.35, "negative": 0.25})
        labels = ['积极', '中立', '消极']
        sizes = [sentiment.get("positive", 0.33), sentiment.get("neutral", 0.34), sentiment.get("negative", 0.33)]
        colors = ['#2ecc71', '#f39c12', '#e74c3c']
        ax4.pie(sizes, labels=labels, colors=colors, autopct='%1.0f%%', startangle=90)
        
        # 5. Policy timeline (middle center and right)
        ax5 = fig.add_subplot(gs[1, 1:])
        ax5.set_title('政策实施时间线 Policy Implementation Timeline', fontsize=12, fontweight='bold')
        
        policy_framework = analysis_results.get("policy_recommendations", {}).get("policy_framework", {})
        
        # Simple timeline visualization
        timeline_data = [
            ("短期 (1年内)", policy_framework.get("short_term", ["政策宣传", "试点项目"])[:2]),
            ("中期 (1-3年)", policy_framework.get("medium_term", ["市场机制", "基础设施"])[:2]),
            ("长期 (3-5年)", policy_framework.get("long_term", ["产业升级", "全面覆盖"])[:2])
        ]
        
        x_positions = [0.2, 0.5, 0.8]
        for i, (period, policies) in enumerate(timeline_data):
            ax5.axvline(x=x_positions[i], color='#3498db', linestyle='-', linewidth=3, ymin=0.3, ymax=0.7)
            ax5.plot(x_positions[i], 0.5, 'o', markersize=15, color='#3498db')
            ax5.text(x_positions[i], 0.75, period, ha='center', fontsize=11, fontweight='bold')
            policy_text = "\n".join([f"• {p[:12]}..." if len(str(p)) > 12 else f"• {p}" for p in policies])
            ax5.text(x_positions[i], 0.3, policy_text, ha='center', va='top', fontsize=9)
        
        ax5.plot([0.2, 0.8], [0.5, 0.5], '-', color='#bdc3c7', linewidth=2, zorder=0)
        ax5.set_xlim(0, 1)
        ax5.set_ylim(0, 1)
        ax5.axis('off')
        
        # 6. Recommendations summary (bottom)
        ax6 = fig.add_subplot(gs[2, :])
        ax6.set_title('核心政策建议 Key Policy Recommendations', fontsize=12, fontweight='bold')
        
        recommendations = analysis_results.get("policy_recommendations", {}).get("detailed_recommendations", [])
        if recommendations:
            rec_text = ""
            for i, rec in enumerate(recommendations[:6]):
                if isinstance(rec, dict):
                    name = rec.get("name", f"建议{i+1}")
                    measures = rec.get("measures", [])[:2]
                    rec_text += f"{i+1}. {name}: {', '.join(str(m)[:20] for m in measures)}\n"
                else:
                    rec_text += f"{i+1}. {str(rec)[:60]}\n"
        else:
            rec_text = "1. 加强政策宣传和科普教育\n2. 完善财税激励机制\n3. 建设绿电基础设施\n4. 推动试点示范项目\n5. 建立信息透明机制\n6. 培育绿色消费文化"
        
        ax6.text(0.05, 0.9, rec_text, va='top', fontsize=11, transform=ax6.transAxes, 
                family='monospace', linespacing=1.8)
        ax6.axis('off')
        
        path = self._get_figure_path("comprehensive_infographic")
        plt.savefig(path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"综合信息图已保存: {path}")
        return str(path)
    
    def generate_all_visualizations(self, analysis_results: Dict) -> Dict[str, str]:
        """Generate all visualizations for the analysis results."""
        figures = {}
        
        logger.info("开始生成学术级可视化...")
        
        # 1. Theoretical framework
        framework_path = self.create_theoretical_framework_diagram()
        if framework_path:
            figures["theoretical_framework"] = framework_path
        
        driving_analysis = analysis_results.get("driving_factors_analysis")
        barrier_analysis = analysis_results.get("barriers_analysis")
        sentiment_analysis = analysis_results.get("sentiment_trend_analysis")
        policy_analysis = analysis_results.get("policy_recommendations")
        highlights = analysis_results.get("quantitative_highlights", {})
        
        # 2. Driving factor visuals
        if driving_analysis:
            radar_path = self.create_pestel_radar_chart(driving_analysis)
            driver_strength = self.create_driver_strength_chart(driving_analysis)
            if radar_path:
                figures["pestel_radar"] = radar_path
            if driver_strength:
                figures["driver_strength"] = driver_strength
        
        # 3. Barrier visuals
        if barrier_analysis:
            severity_heatmap = self.create_barrier_severity_heatmap(barrier_analysis)
            difficulty_heatmap = self.create_barrier_difficulty_heatmap(barrier_analysis)
            risk_scatter = self.create_barrier_risk_scatter(barrier_analysis)
            if severity_heatmap:
                figures["barrier_severity_heatmap"] = severity_heatmap
            if difficulty_heatmap:
                figures["barrier_difficulty_heatmap"] = difficulty_heatmap
            if risk_scatter:
                figures["barrier_risk_scatter"] = risk_scatter
        
        # 4. Keyword focus
        keyword_path = self.create_keyword_focus_chart(highlights)
        if keyword_path:
            figures["keyword_focus"] = keyword_path
        
        # 5. Sentiment visuals
        if sentiment_analysis:
            sentiment_profile = self.create_sentiment_distribution(sentiment_analysis)
            stakeholder_chart = self.create_stakeholder_attitudes_chart(sentiment_analysis)
            if sentiment_profile:
                figures["sentiment_profile"] = sentiment_profile
            if stakeholder_chart:
                figures["stakeholder_attitudes"] = stakeholder_chart
        
        # 6. Policy priority matrix
        if policy_analysis:
            policy_matrix = self.create_policy_priority_matrix(policy_analysis)
            if policy_matrix:
                figures["policy_priority_matrix"] = policy_matrix
        
        logger.info(f"共生成 {len(figures)} 个可视化图表")
        
        return figures

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果分析和输出脚本
生成可视化图表和分析报告
"""

import json
import os
from typing import List, Dict
from datetime import datetime
import logging
import matplotlib.pyplot as plt
import pandas as pd
from wordcloud import WordCloud
import seaborn as sns
from collections import Counter
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResultAnalyzer:
    def __init__(self, input_dir="analysis_results", output_dir="final_output"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'charts'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'reports'), exist_ok=True)

    def load_analysis_results(self) -> Dict:
        """加载分析结果"""
        results = {}
        
        # 查找最新的综合报告文件
        report_files = [f for f in os.listdir(self.input_dir) 
                       if f.startswith('comprehensive_report_') and f.endswith('.json')]
        
        if not report_files:
            logger.error("未找到综合报告文件")
            return {}
        
        # 选择最新的报告文件
        latest_report = max(report_files, key=lambda x: x.split('_')[-1])
        report_path = os.path.join(self.input_dir, latest_report)
        
        with open(report_path, 'r', encoding='utf-8') as f:
            results['comprehensive_report'] = json.load(f)
        
        # 查找详细分析结果
        detail_files = [f for f in os.listdir(self.input_dir) 
                       if f.startswith('detailed_analysis_') and f.endswith('.json')]
        
        if detail_files:
            latest_detail = max(detail_files, key=lambda x: x.split('_')[-1])
            detail_path = os.path.join(self.input_dir, latest_detail)
            
            with open(detail_path, 'r', encoding='utf-8') as f:
                results['detailed_analysis'] = json.load(f)
        
        logger.info(f"加载分析结果完成: {latest_report}")
        return results

    def create_driving_factors_chart(self, driving_factors: Dict) -> str:
        """创建驱动因素图表"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('中国居民绿色电力消费驱动因素分析', fontsize=16, fontweight='bold')
        
        categories = list(driving_factors.keys())[:6]  # 最多显示6个类别
        
        for idx, category in enumerate(categories):
            row = idx // 3
            col = idx % 3
            ax = axes[row, col]
            
            factors = driving_factors[category]
            if not factors:
                ax.text(0.5, 0.5, f'{category}\n(暂无数据)', ha='center', va='center')
                ax.set_title(category)
                continue
            
            # 提取因素名称和频率
            if isinstance(factors[0], dict):
                factor_names = [f['factor'] if 'factor' in f else str(f) for f in factors[:5]]
                frequencies = [f.get('frequency', 1) for f in factors[:5]]
            else:
                factor_names = [str(f) for f in factors[:5]]
                frequencies = [1] * len(factor_names)
            
            # 创建条形图
            bars = ax.barh(range(len(factor_names)), frequencies, color=plt.cm.Set3(idx))
            ax.set_yticks(range(len(factor_names)))
            ax.set_yticklabels(factor_names)
            ax.set_title(f'{category}驱动因素')
            ax.set_xlabel('频率')
            
            # 添加数值标签
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                       f'{width}', ha='left', va='center')
        
        # 隐藏空的子图
        for idx in range(len(categories), 6):
            row = idx // 3
            col = idx % 3
            axes[row, col].set_visible(False)
        
        plt.tight_layout()
        chart_path = os.path.join(self.output_dir, 'charts', 'driving_factors.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"驱动因素图表已保存: {chart_path}")
        return chart_path

    def create_barriers_chart(self, barriers: Dict) -> str:
        """创建障碍因素图表"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('中国居民绿色电力消费障碍因素分析', fontsize=16, fontweight='bold')
        
        categories = list(barriers.keys())[:6]
        
        for idx, category in enumerate(categories):
            row = idx // 3
            col = idx % 3
            ax = axes[row, col]
            
            barrier_list = barriers[category]
            if not barrier_list:
                ax.text(0.5, 0.5, f'{category}\n(暂无数据)', ha='center', va='center')
                ax.set_title(category)
                continue
            
            # 提取障碍名称和频率
            if isinstance(barrier_list[0], dict):
                barrier_names = [b['factor'] if 'factor' in b else str(b) for b in barrier_list[:5]]
                frequencies = [b.get('frequency', 1) for b in barrier_list[:5]]
            else:
                barrier_names = [str(b) for b in barrier_list[:5]]
                frequencies = [1] * len(barrier_names)
            
            # 创建条形图
            bars = ax.barh(range(len(barrier_names)), frequencies, color=plt.cm.Set1(idx))
            ax.set_yticks(range(len(barrier_names)))
            ax.set_yticklabels(barrier_names)
            ax.set_title(f'{category}障碍因素')
            ax.set_xlabel('频率')
            
            # 添加数值标签
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                       f'{width}', ha='left', va='center')
        
        # 隐藏空的子图
        for idx in range(len(categories), 6):
            row = idx // 3
            col = idx % 3
            axes[row, col].set_visible(False)
        
        plt.tight_layout()
        chart_path = os.path.join(self.output_dir, 'charts', 'barriers.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"障碍因素图表已保存: {chart_path}")
        return chart_path

    def create_factor_comparison_chart(self, driving_factors: Dict, barriers: Dict) -> str:
        """创建驱动因素与障碍因素对比图表"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        fig.suptitle('驱动因素 vs 障碍因素 对比分析', fontsize=16, fontweight='bold')
        
        # 统计各类别的因素数量
        driving_counts = {}
        for category, factors in driving_factors.items():
            driving_counts[category] = len(factors) if factors else 0
        
        barrier_counts = {}
        for category, barriers_list in barriers.items():
            barrier_counts[category] = len(barriers_list) if barriers_list else 0
        
        # 驱动因素饼图
        if driving_counts and any(driving_counts.values()):
            labels = list(driving_counts.keys())
            sizes = list(driving_counts.values())
            colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
            
            wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%')
            ax1.set_title('驱动因素分布')
        else:
            ax1.text(0.5, 0.5, '暂无驱动因素数据', ha='center', va='center')
            ax1.set_title('驱动因素分布')
        
        # 障碍因素饼图
        if barrier_counts and any(barrier_counts.values()):
            labels = list(barrier_counts.keys())
            sizes = list(barrier_counts.values())
            colors = plt.cm.Set1(np.linspace(0, 1, len(labels)))
            
            wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%')
            ax2.set_title('障碍因素分布')
        else:
            ax2.text(0.5, 0.5, '暂无障碍因素数据', ha='center', va='center')
            ax2.set_title('障碍因素分布')
        
        plt.tight_layout()
        chart_path = os.path.join(self.output_dir, 'charts', 'factor_comparison.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"对比图表已保存: {chart_path}")
        return chart_path

    def create_wordcloud(self, text_data: List[str], title: str) -> str:
        """创建词云图"""
        if not text_data:
            logger.warning(f"无法创建词云图 '{title}': 没有文本数据")
            return ""
        
        # 合并所有文本
        combined_text = ' '.join(text_data)
        
        try:
            # 创建词云
            wordcloud = WordCloud(
                font_path=None,  # 如果有中文字体文件可以指定路径
                width=800,
                height=400,
                background_color='white',
                max_words=100,
                collocations=False
            ).generate(combined_text)
            
            # 绘制词云图
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.title(title, fontsize=16, fontweight='bold')
            
            chart_path = os.path.join(self.output_dir, 'charts', f'wordcloud_{title.replace(" ", "_")}.png')
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"词云图已保存: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"创建词云图失败 '{title}': {e}")
            return ""

    def generate_html_report(self, results: Dict, chart_paths: List[str]) -> str:
        """生成HTML报告"""
        report = results.get('comprehensive_report', {})
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>中国居民绿色电力消费驱动机制与障碍分析报告</title>
            <style>
                body {{
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #2c3e50;
                    text-align: center;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #27ae60;
                    border-left: 4px solid #27ae60;
                    padding-left: 15px;
                    margin-top: 30px;
                }}
                h3 {{
                    color: #e74c3c;
                    margin-top: 25px;
                }}
                .summary {{
                    background-color: #ecf0f1;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .chart-container {{
                    text-align: center;
                    margin: 20px 0;
                }}
                .chart-container img {{
                    max-width: 100%;
                    height: auto;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .factor-list {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
                .recommendation {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
                ul {{
                    padding-left: 20px;
                }}
                li {{
                    margin: 5px 0;
                }}
                .timestamp {{
                    text-align: center;
                    color: #7f8c8d;
                    font-style: italic;
                    margin-top: 30px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>中国居民绿色电力消费驱动机制与障碍分析报告</h1>
                
                <div class="summary">
                    <h2>执行摘要</h2>
        """
        
        # 添加执行摘要
        executive_summary = report.get('executive_summary', {})
        for key, value in executive_summary.items():
            html_content += f"<p><strong>{key}:</strong> {value}</p>\n"
        
        html_content += "</div>\n"
        
        # 添加图表
        if chart_paths:
            html_content += '<h2>数据可视化</h2>\n'
            for chart_path in chart_paths:
                if chart_path and os.path.exists(chart_path):
                    chart_name = os.path.basename(chart_path)
                    relative_path = f"charts/{chart_name}"
                    html_content += f'''
                    <div class="chart-container">
                        <img src="{relative_path}" alt="{chart_name}">
                    </div>
                    '''
        
        # 添加驱动因素分析
        driving_factors = report.get('driving_factors_analysis', {})
        if driving_factors:
            html_content += '<h2>驱动因素分析</h2>\n'
            for category, factors in driving_factors.items():
                html_content += f'<h3>{category}</h3>\n<div class="factor-list">\n<ul>\n'
                for factor in factors[:5]:  # 显示前5个因素
                    if isinstance(factor, dict):
                        factor_name = factor.get('factor', str(factor))
                        frequency = factor.get('frequency', 'N/A')
                        html_content += f'<li>{factor_name} (频率: {frequency})</li>\n'
                    else:
                        html_content += f'<li>{factor}</li>\n'
                html_content += '</ul>\n</div>\n'
        
        # 添加障碍因素分析
        barriers = report.get('barriers_analysis', {})
        if barriers:
            html_content += '<h2>障碍因素分析</h2>\n'
            for category, barrier_list in barriers.items():
                html_content += f'<h3>{category}</h3>\n<div class="factor-list">\n<ul>\n'
                for barrier in barrier_list[:5]:
                    if isinstance(barrier, dict):
                        barrier_name = barrier.get('factor', str(barrier))
                        frequency = barrier.get('frequency', 'N/A')
                        html_content += f'<li>{barrier_name} (频率: {frequency})</li>\n'
                    else:
                        html_content += f'<li>{barrier}</li>\n'
                html_content += '</ul>\n</div>\n'
        
        # 添加建议
        recommendations = report.get('recommendations', [])
        if recommendations:
            html_content += '<h2>政策建议</h2>\n'
            for idx, rec in enumerate(recommendations, 1):
                html_content += f'<div class="recommendation">建议{idx}: {rec}</div>\n'
        
        # 添加时间戳
        html_content += f'''
                <div class="timestamp">
                    报告生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        '''
        
        # 保存HTML报告
        html_path = os.path.join(self.output_dir, 'reports', 'comprehensive_report.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML报告已保存: {html_path}")
        return html_path

    def generate_markdown_report(self, results: Dict) -> str:
        """生成Markdown格式报告"""
        report = results.get('comprehensive_report', {})
        
        markdown_content = f"""# 中国居民绿色电力消费驱动机制与障碍分析报告

*报告生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}*

## 执行摘要

"""
        
        # 添加执行摘要
        executive_summary = report.get('executive_summary', {})
        for key, value in executive_summary.items():
            markdown_content += f"**{key}**: {value}\n\n"
        
        # 添加驱动因素分析
        driving_factors = report.get('driving_factors_analysis', {})
        if driving_factors:
            markdown_content += "## 驱动因素分析\n\n"
            for category, factors in driving_factors.items():
                markdown_content += f"### {category}\n\n"
                for factor in factors[:5]:
                    if isinstance(factor, dict):
                        factor_name = factor.get('factor', str(factor))
                        frequency = factor.get('frequency', 'N/A')
                        markdown_content += f"- {factor_name} (频率: {frequency})\n"
                    else:
                        markdown_content += f"- {factor}\n"
                markdown_content += "\n"
        
        # 添加障碍因素分析
        barriers = report.get('barriers_analysis', {})
        if barriers:
            markdown_content += "## 障碍因素分析\n\n"
            for category, barrier_list in barriers.items():
                markdown_content += f"### {category}\n\n"
                for barrier in barrier_list[:5]:
                    if isinstance(barrier, dict):
                        barrier_name = barrier.get('factor', str(barrier))
                        frequency = barrier.get('frequency', 'N/A')
                        markdown_content += f"- {barrier_name} (频率: {frequency})\n"
                    else:
                        markdown_content += f"- {barrier}\n"
                markdown_content += "\n"
        
        # 添加建议
        recommendations = report.get('recommendations', [])
        if recommendations:
            markdown_content += "## 政策建议\n\n"
            for idx, rec in enumerate(recommendations, 1):
                markdown_content += f"{idx}. {rec}\n"
            markdown_content += "\n"
        
        # 保存Markdown报告
        md_path = os.path.join(self.output_dir, 'reports', 'comprehensive_report.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"Markdown报告已保存: {md_path}")
        return md_path

    def run_analysis(self) -> Dict:
        """运行结果分析"""
        logger.info("开始结果分析和输出生成...")
        
        # 加载分析结果
        results = self.load_analysis_results()
        if not results:
            logger.error("无法加载分析结果")
            return {}
        
        report = results.get('comprehensive_report', {})
        chart_paths = []
        
        try:
            # 创建驱动因素图表
            driving_factors = report.get('driving_factors_analysis', {})
            if driving_factors:
                chart_path = self.create_driving_factors_chart(driving_factors)
                if chart_path:
                    chart_paths.append(chart_path)
            
            # 创建障碍因素图表
            barriers = report.get('barriers_analysis', {})
            if barriers:
                chart_path = self.create_barriers_chart(barriers)
                if chart_path:
                    chart_paths.append(chart_path)
            
            # 创建对比图表
            if driving_factors and barriers:
                chart_path = self.create_factor_comparison_chart(driving_factors, barriers)
                if chart_path:
                    chart_paths.append(chart_path)
            
        except Exception as e:
            logger.warning(f"图表生成过程中出现错误: {e}")
        
        # 生成报告
        output_files = {}
        
        try:
            html_path = self.generate_html_report(results, chart_paths)
            output_files['html_report'] = html_path
        except Exception as e:
            logger.warning(f"HTML报告生成失败: {e}")
        
        try:
            md_path = self.generate_markdown_report(results)
            output_files['markdown_report'] = md_path
        except Exception as e:
            logger.warning(f"Markdown报告生成失败: {e}")
        
        output_files['charts'] = chart_paths
        
        logger.info("结果分析完成")
        logger.info(f"输出文件: {list(output_files.values())}")
        
        return output_files

if __name__ == "__main__":
    analyzer = ResultAnalyzer()
    output_files = analyzer.run_analysis()
    
    if output_files:
        print("分析完成，输出文件:")
        for file_type, path in output_files.items():
            if isinstance(path, list):
                print(f"{file_type}: {', '.join(path)}")
            else:
                print(f"{file_type}: {path}")
    else:
        print("分析失败，请检查输入文件")
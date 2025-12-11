import os
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns
from wordcloud import WordCloud

class Visualizer:
    def __init__(self, font_path: str = "academic_research/data/fonts/SimHei.ttf", output_dir: str = "academic_research/output/figures"):
        self.font_path = font_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Configure matplotlib for Chinese support
        font_name = None
        if os.path.exists(self.font_path):
            fm.fontManager.addfont(self.font_path)
            font_name = fm.FontProperties(fname=self.font_path).get_name()

        plt.rcParams['font.sans-serif'] = [font_name or 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False    # Fix minus sign display

    def generate_wordcloud(self, text_freq: Dict[str, float], title: str = "Word Cloud"):
        """Generate and save a word cloud image"""
        wc = WordCloud(
            font_path=self.font_path,
            width=1600,
            height=800,
            background_color='white',
            max_words=200
        )
        
        wc.generate_from_frequencies(text_freq)
        
        plt.figure(figsize=(20, 10))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        plt.title(title, fontsize=20)
        
        output_path = os.path.join(self.output_dir, f"{title.lower().replace(' ', '_')}.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved wordcloud to {output_path}")

    def plot_top_keywords(self, keywords: List[Tuple[str, float]], top_n: int = 20):
        """Plot bar chart of top keywords"""
        words, scores = zip(*keywords[:top_n])
        
        plt.figure(figsize=(12, 8))
        sns.barplot(x=list(scores), y=list(words), hue=list(words), dodge=False, legend=False, palette='viridis')
        plt.title(f"Top {top_n} Keywords by TF-IDF Score", fontsize=16)
        plt.xlabel("TF-IDF Score")
        
        output_path = os.path.join(self.output_dir, "top_keywords_bar.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved keyword bar chart to {output_path}")

    def plot_drivers_barriers(self, drivers: List[Tuple[str, float]], barriers: List[Tuple[str, float]]):
        """Plot a comparison of drivers and barriers (Force Field Analysis style)"""
        def normalize(items):
            normalized = []
            for item in items:
                if isinstance(item, tuple):
                    normalized.append(item)
                elif isinstance(item, dict):
                    normalized.append((item.get('word'), item.get('score', 0)))
            return normalized

        drivers = normalize(drivers)
        barriers = normalize(barriers)

        if not drivers and not barriers:
            print("No driver/barrier data available for plotting.")
            return

        top_drivers = sorted(drivers, key=lambda x: x[1], reverse=True)[:10]
        top_barriers = sorted(barriers, key=lambda x: x[1], reverse=True)[:10]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        if top_drivers:
            d_words, d_scores = zip(*top_drivers)
            sns.barplot(x=list(d_scores), y=list(d_words), hue=list(d_words), dodge=False, legend=False, ax=ax1, palette='Greens_r')
            ax1.set_title("Drivers (驱动因素)", fontsize=14)
            ax1.invert_xaxis()
            ax1.yaxis.tick_right()
        else:
            ax1.axis('off')

        if top_barriers:
            b_words, b_scores = zip(*top_barriers)
            sns.barplot(x=list(b_scores), y=list(b_words), hue=list(b_words), dodge=False, legend=False, ax=ax2, palette='Reds_r')
            ax2.set_title("Barriers (阻碍因素)", fontsize=14)
            ax2.yaxis.tick_left()
        else:
            ax2.axis('off')

        plt.suptitle("Force Field Analysis: Green Power Consumption", fontsize=18)
        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "force_field_analysis.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved force field analysis to {output_path}")

    def plot_topic_heatmap(self, topics: Dict):
        """Generate a heatmap of topic-word distributions"""
        data = []
        for topic_name, words in topics.items():
            for item in words:
                data.append({
                    'Topic': topic_name,
                    'Word': item['word'],
                    'Weight': item['weight']
                })
        
        df = pd.DataFrame(data)
        
        # Pivot for heatmap
        pivot_df = df.pivot(index='Word', columns='Topic', values='Weight').fillna(0)
        
        plt.figure(figsize=(12, 10))
        sns.heatmap(pivot_df, cmap='YlOrRd', annot=True, fmt='.3f')
        plt.title("Topic-Word Weight Heatmap", fontsize=16)
        
        output_path = os.path.join(self.output_dir, "topic_heatmap.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved topic heatmap to {output_path}")

    def plot_topic_strength_radar(self, topic_strength: Dict[str, float], title: str = "Topic Strength Radar"):
        if not topic_strength:
            print("No topic strength data to plot.")
            return

        labels = list(topic_strength.keys())
        values = list(topic_strength.values())
        labels.append(labels[0])
        values.append(values[0])
        angles = np.linspace(0, 2 * np.pi, len(labels))

        plt.figure(figsize=(8, 8))
        ax = plt.subplot(111, polar=True)
        ax.plot(angles, values, 'o-', linewidth=2)
        ax.fill(angles, values, alpha=0.25)
        ax.set_thetagrids(angles * 180 / np.pi, labels)
        ax.set_title(title)

        output_path = os.path.join(self.output_dir, f"{title.lower().replace(' ', '_')}.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved topic radar chart to {output_path}")

    def plot_cluster_scatter(self, tsne_df: pd.DataFrame):
        if tsne_df is None or tsne_df.empty:
            print("No cluster projection data to plot.")
            return

        plt.figure(figsize=(10, 8))
        sns.scatterplot(
            data=tsne_df,
            x='x',
            y='y',
            hue='cluster',
            palette='tab10',
            alpha=0.75,
            s=70
        )
        plt.title("文档语义分布 (t-SNE)")
        plt.xlabel("Dimension 1")
        plt.ylabel("Dimension 2")
        plt.legend(title='Cluster', bbox_to_anchor=(1.05, 1), loc='upper left')

        output_path = os.path.join(self.output_dir, "cluster_scatter.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved cluster scatter to {output_path}")

    def plot_source_distribution(self, source_dist: Dict[str, int]):
        if not source_dist:
            print("No source distribution data to plot.")
            return

        labels = list(source_dist.keys())
        values = list(source_dist.values())

        plt.figure(figsize=(12, 6))
        sns.barplot(x=values, y=labels, hue=labels, dodge=False, legend=False, palette='Blues_d')
        plt.xlabel("Document Count")
        plt.ylabel("Source Category")
        plt.title("Source/Channel Distribution")

        output_path = os.path.join(self.output_dir, "source_distribution.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved source distribution chart to {output_path}")

    def plot_sentiment_distribution(self, sentiment_scores: List[float], label_counts: Dict[str, int]):
        if not sentiment_scores:
            print("No sentiment scores to visualize.")
            return

        plt.figure(figsize=(12, 6))
        sns.histplot(sentiment_scores, bins=20, kde=True, color='#2a9d8f')
        plt.axvline(0.4, color='red', linestyle='--', linewidth=1)
        plt.axvline(0.6, color='green', linestyle='--', linewidth=1)
        plt.title("Sentiment Distribution (SnowNLP Scores)")
        plt.xlabel("Sentiment Score (0=负向, 1=正向)")
        plt.ylabel("Document Count")

        output_path = os.path.join(self.output_dir, "sentiment_distribution.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved sentiment distribution chart to {output_path}")

        if label_counts:
            plt.figure(figsize=(8, 6))
            labels = list(label_counts.keys())
            values = list(label_counts.values())
            sns.barplot(x=labels, y=values, hue=labels, dodge=False, legend=False, palette='Pastel1')
            plt.title("Sentiment Labels")
            plt.ylabel("Document Count")
            output_path = os.path.join(self.output_dir, "sentiment_labels.png")
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"Saved sentiment label chart to {output_path}")

    def plot_factor_matrix(self, factor_matrix):
        if factor_matrix is None or factor_matrix.empty:
            print("No factor matrix data to plot.")
            return

        df = factor_matrix.copy().sort_values('Coverage', ascending=True)
        plt.figure(figsize=(14, 8))
        plt.barh(df['Factor'], df['BarrierDocs'], color='#ef476f', label='阻碍文献')
        plt.barh(df['Factor'], df['DriverDocs'], left=df['BarrierDocs'], color='#06d6a0', label='驱动文献')
        plt.xlabel("Document Mentions")
        plt.title("驱动-阻碍强度对比 (按要素类别)")
        plt.legend()

        output_path = os.path.join(self.output_dir, "factor_force_matrix.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved factor force matrix to {output_path}")

    def plot_cooccurrence_network(self, edge_df):
        if edge_df is None or edge_df.empty:
            print("No co-occurrence edges to plot.")
            return

        G = nx.Graph()
        for _, row in edge_df.iterrows():
            G.add_edge(row['source'], row['target'], weight=row['weight'])

        pos = nx.spring_layout(G, k=0.6, seed=42, weight='weight')
        node_sizes = [
            max(nx.degree(G, node, weight='weight'), 1) * 300
            for node in G.nodes()
        ]
        edge_widths = [max(data['weight'], 1) for _, _, data in G.edges(data=True)]

        plt.figure(figsize=(12, 12))
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='#90caf9', alpha=0.9)
        nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.4, edge_color='#333333')
        nx.draw_networkx_labels(G, pos, font_size=10)
        plt.title("关键词共现网络")
        plt.axis('off')

        output_path = os.path.join(self.output_dir, "keyword_cooccurrence_network.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved co-occurrence network to {output_path}")

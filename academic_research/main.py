import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path to allow absolute imports
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from academic_research.src.preprocessing import TextPreprocessor
from academic_research.src.analysis import TextAnalyzer
from academic_research.src.visualization import Visualizer
from academic_research.src.llm_analysis import LLMInterpreter


load_dotenv()


def main():
    # Configuration
    INPUT_FILE = "academic_data/academic_green_power_results_20251119_185225.json"
    STOPWORDS_FILE = "academic_research/data/stopwords.txt"
    FONT_FILE = "academic_research/data/fonts/SimHei.ttf"
    OUTPUT_REPORT_DIR = "academic_research/output/reports"

    print("Step 1: Data Preprocessing...")
    preprocessor = TextPreprocessor(stopwords_path=STOPWORDS_FILE)
    docs = preprocessor.process_file(INPUT_FILE)
    print(f"Processed {len(docs)} documents.")

    if not docs:
        print("No documents available after preprocessing. Exiting.")
        return

    print("\nStep 2: Text Analysis...")
    analyzer = TextAnalyzer(docs)

    corpus_stats = analyzer.corpus_overview()
    source_dist = analyzer.get_source_distribution()

    # Keyword and topic insights
    top_keywords = analyzer.get_top_keywords(top_k=120)
    print("Top 10 Keywords:", top_keywords[:10])

    lda_results = analyzer.perform_lda_analysis(num_topics=8, num_words=12)
    if lda_results['topics']:
        print("\nIdentified Topics:")
        for topic, words in lda_results['topics'].items():
            print(f"{topic}: {[w['word'] for w in words[:8]]}")
    else:
        print("\nLDA did not return valid topics (insufficient vocabulary).")

    nmf_results = analyzer.compute_nmf_topics(num_topics=8, num_words=12)
    cluster_results = analyzer.cluster_documents(num_clusters=8, top_terms=12)
    tsne_projection = analyzer.project_embeddings_tsne(cluster_results.get('labels') if cluster_results else None)
    similarity_graph = analyzer.build_similarity_graph(top_k=40)

    classified_factors = analyzer.classify_factors(top_keywords)
    factor_landscape = analyzer.analyze_factor_landscape()
    sentiment_profile = analyzer.compute_sentiment_profile()

    keyword_nodes = [word for word, _ in top_keywords[:40]]
    cooccurrence_edges = analyzer.build_cooccurrence_network(keyword_nodes, min_edge_weight=3)

    llm = LLMInterpreter()
    llm_topic_notes = []
    llm_factor_notes = []
    llm_cluster_notes = []
    if llm.available():
        try:
            llm_topic_notes = llm.summarize_topics(lda_results.get('topics', {}), nmf_results.get('topics', {}))
            llm_factor_notes = llm.generate_factor_insights(factor_landscape['details'], sentiment_profile)
            llm_cluster_notes = llm.label_clusters(cluster_results.get('clusters', [])) if cluster_results else []
        except Exception as exc:
            print(f"LLM analysis failed: {exc}")

    print("\nStep 3: Visualization...")
    visualizer = Visualizer(font_path=FONT_FILE)

    if top_keywords:
        keyword_dict = {k: v for k, v in top_keywords}
        visualizer.generate_wordcloud(keyword_dict, "Green Power Research Word Cloud")
        visualizer.plot_top_keywords(top_keywords, top_n=25)

    visualizer.plot_source_distribution(source_dist)
    visualizer.plot_sentiment_distribution(
        sentiment_profile.get('scores', []),
        sentiment_profile.get('label_counts', {})
    )

    driver_pairs = [(item['word'], item['score']) for item in classified_factors['drivers'][:15]]
    barrier_pairs = [(item['word'], item['score']) for item in classified_factors['barriers'][:15]]
    visualizer.plot_drivers_barriers(driver_pairs, barrier_pairs)

    if lda_results['topics']:
        visualizer.plot_topic_heatmap(lda_results['topics'])
        visualizer.plot_topic_strength_radar(lda_results.get('topic_strength', {}), title="LDA Topic Strength Radar")

    nmf_strength = {topic: float(sum(item['weight'] for item in words[:5])) for topic, words in nmf_results.get('topics', {}).items()}
    if nmf_strength:
        visualizer.plot_topic_strength_radar(nmf_strength, title="NMF Topic Strength Radar")

    visualizer.plot_cluster_scatter(tsne_projection)

    visualizer.plot_factor_matrix(factor_landscape['matrix'])
    visualizer.plot_cooccurrence_network(cooccurrence_edges)

    print("\nStep 4: Generating Report...")
    report_path = os.path.join(OUTPUT_REPORT_DIR, "analysis_summary.md")
    os.makedirs(OUTPUT_REPORT_DIR, exist_ok=True)

    dominant_topics = Counter([item['topic'] for item in lda_results.get('doc_topics', [])])
    topic_strength = lda_results.get('topic_strength', {})

    def format_stat_line(label: str, value):
        return f"- **{label}**: {value}"

    report_lines = []
    report_lines.append("# Green Power Consumption Analysis Report\n")
    report_lines.append("## 1. 数据与覆盖面")
    if corpus_stats:
        report_lines.append(format_stat_line("语料规模", corpus_stats['documents']))
        report_lines.append(format_stat_line("独立词汇数", corpus_stats['vocabulary_size']))
        report_lines.append(format_stat_line("平均分词长度", f"{corpus_stats['avg_tokens_per_doc']:.1f}"))
        report_lines.append(format_stat_line("中位分词长度", f"{corpus_stats['median_tokens_per_doc']:.1f}"))
        report_lines.append(format_stat_line("平均字符长度", f"{corpus_stats['avg_character_len']:.1f}"))
        report_lines.append(format_stat_line("覆盖域名数", corpus_stats['unique_domains']))
        report_lines.append(format_stat_line("关键词覆盖数", corpus_stats['keywords_covered']))
        if corpus_stats['time_span']:
            report_lines.append(format_stat_line("采集时间跨度", corpus_stats['time_span']))

    report_lines.append("\n## 2. 信息来源结构")
    if source_dist:
        for source, count in sorted(source_dist.items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"- {source}: {count} 篇")
    else:
        report_lines.append("- 未能识别来源类型")

    report_lines.append("\n## 3. 关键词特征")
    for word, score in top_keywords[:25]:
        report_lines.append(f"- **{word}**: {score:.4f}")

    report_lines.append("\n## 4. 主题模型洞察 (LDA)")
    if lda_results['topics']:
        sorted_topics = sorted(
            lda_results['topics'].items(),
            key=lambda item: topic_strength.get(item[0], 0),
            reverse=True
        )
        for topic, words in sorted_topics:
            strength = topic_strength.get(topic, 0)
            keywords = ', '.join([w['word'] for w in words[:10]])
            coverage = dominant_topics.get(topic, 0)
            report_lines.append(
                f"- **{topic}** (权重 {strength:.3f}, 覆盖 {coverage} 篇): {keywords}"
            )
    else:
        report_lines.append("- 主题数量不足，未能形成稳定聚类")

    report_lines.append("\n## 5. NMF 主题矩阵")
    if nmf_results.get('topics'):
        for topic, words in nmf_results['topics'].items():
            keywords = ', '.join([w['word'] for w in words[:10]])
            report_lines.append(f"- **{topic}**: {keywords}")
    else:
        report_lines.append("- NMF 模型尚未收敛")

    report_lines.append("\n## 6. 语义聚类与嵌入")
    clusters = cluster_results.get('clusters') if cluster_results else []
    if clusters:
        for detail in sorted(clusters, key=lambda x: x['size'], reverse=True):
            report_lines.append(
                f"- Cluster {detail['cluster_id']} ({detail['size']} 篇): {', '.join(detail['top_terms'][:12])}"
            )
    else:
        report_lines.append("- 文档数量不足或聚类未成功")

    report_lines.append("\n## 7. 驱动-阻碍要素力场")
    factor_details = sorted(
        [d for d in factor_landscape['details'] if d['coverage_docs'] > 0],
        key=lambda x: x['coverage_docs'],
        reverse=True
    ) or factor_landscape['details']

    for detail in factor_details:
        report_lines.append(
            f"- **{detail['factor']}** | 覆盖 {detail['coverage_docs']} 篇 | 驱动 {detail['driver_docs']} / 阻碍 {detail['barrier_docs']} | 净强度 {detail['net_score']} | 高频词：{', '.join(detail['top_terms']) if detail['top_terms'] else '—'}"
        )

    report_lines.append("\n## 8. 情感倾向")
    if sentiment_profile.get('scores'):
        mean_score = sentiment_profile.get('mean')
        median_score = sentiment_profile.get('median')
        std_score = sentiment_profile.get('std')

        if mean_score is not None:
            report_lines.append(format_stat_line("平均情感得分", f"{mean_score:.3f}"))
        if median_score is not None:
            report_lines.append(format_stat_line("中位数", f"{median_score:.3f}"))
        if std_score is not None:
            report_lines.append(format_stat_line("标准差", f"{std_score:.3f}"))
        label_counts = sentiment_profile.get('label_counts', {})
        total_sent = sum(label_counts.values()) or 1
        for label, count in label_counts.items():
            report_lines.append(f"- {label}: {count} 篇 ({count / total_sent:.1%})")
    else:
        report_lines.append("- 数据不足，未能评估情感")

    report_lines.append("\n## 9. 关键词驱动/阻碍清单")
    report_lines.append("### 驱动关键词")
    for item in sorted(classified_factors['drivers'], key=lambda x: x['score'], reverse=True)[:20]:
        report_lines.append(f"- {item['word']} ({item['category']}, {item['score']:.4f})")

    report_lines.append("\n### 阻碍关键词")
    for item in sorted(classified_factors['barriers'], key=lambda x: x['score'], reverse=True)[:20]:
        report_lines.append(f"- {item['word']} ({item['category']}, {item['score']:.4f})")

    report_lines.append("\n### 中性高频词")
    for item in sorted(classified_factors['neutral'], key=lambda x: x['score'], reverse=True)[:15]:
        report_lines.append(f"- {item['word']} ({item['category']}, {item['score']:.4f})")

    report_lines.append("\n## 10. LLM 深度洞察")
    if llm_topic_notes or llm_factor_notes or llm_cluster_notes:
        if llm_topic_notes:
            report_lines.append("### 主题解读")
            report_lines.extend([f"- {note}" for note in llm_topic_notes])
        if llm_cluster_notes:
            report_lines.append("\n### 聚类命名")
            report_lines.extend([f"- {note}" for note in llm_cluster_notes])
        if llm_factor_notes:
            report_lines.append("\n### 政策建议")
            report_lines.extend([f"- {note}" for note in llm_factor_notes])
    else:
        report_lines.append("- 未开启 LLM 分析或调用失败")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"Report generated at {report_path}")
    print("\nAnalysis Complete!")


if __name__ == "__main__":
    main()

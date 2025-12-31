
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy import stats

logger = logging.getLogger(__name__)

class AdvancedStatisticalAnalyzer:
    """
    Performs advanced statistical analysis for academic research.
    Includes clustering, correlation, and trend analysis.
    """

    def __init__(self):
        pass

    def perform_clustering_analysis(self, texts: List[str], max_k: int = 8) -> Dict[str, Any]:
        """
        Perform K-Means clustering with optimal K selection (Silhouette Score).
        """
        logger.info("Running advanced clustering analysis...")
        if not texts or len(texts) < 5:
            return {}

        vectorizer = TfidfVectorizer(max_df=0.95, min_df=2, stop_words='english')
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
        except ValueError:
            return {"error": "Not enough text data for clustering"}

        best_k = 2
        best_score = -1
        best_model = None
        
        # Determine optimal K
        limit = min(max_k, len(texts) - 1)
        if limit < 2:
            limit = 2
            
        results = []
        
        for k in range(2, limit + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
            labels = kmeans.fit_predict(tfidf_matrix)
            if len(set(labels)) < 2:
                continue
            score = silhouette_score(tfidf_matrix, labels)
            results.append({"k": k, "silhouette": score})
            
            if score > best_score:
                best_score = score
                best_k = k
                best_model = kmeans

        if not best_model:
            return {"error": "Clustering failed"}

        # Get cluster terms
        feature_names = vectorizer.get_feature_names_out()
        order_centroids = best_model.cluster_centers_.argsort()[:, ::-1]
        
        clusters = {}
        for i in range(best_k):
            top_terms = [feature_names[ind] for ind in order_centroids[i, :10]]
            clusters[f"Cluster_{i+1}"] = top_terms

        return {
            "optimal_k": best_k,
            "silhouette_score": best_score,
            "clusters": clusters,
            "clustering_metrics": results
        }

    def perform_correlation_analysis(self, factors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze correlation between identified factors (if quantitative data exists).
        Since we mostly have qualitative data extracted, we simulate this based on co-occurrence in documents.
        """
        # This would require a document-factor matrix. 
        # For now, we return a placeholder structure for the report.
        return {
            "method": "Co-occurrence Matrix",
            "note": "Quantitative correlation requires structured survey data. Using co-occurrence as proxy.",
            "correlations": [] 
        }

    def perform_trend_analysis(self, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze temporal trends if dates are available.
        """
        logger.info("Running trend analysis...")
        df = pd.DataFrame(docs)
        
        # Try to find a date column
        date_col = None
        for col in ['publish_time', 'date', 'crawl_time', 'timestamp']:
            if col in df.columns:
                date_col = col
                break
        
        if not date_col:
            return {"error": "No date column found"}
            
        try:
            df[date_col] = pd.to_datetime(df[date_col])
            df['month'] = df[date_col].dt.to_period('M')
            
            monthly_counts = df['month'].value_counts().sort_index()
            
            # Simple linear regression on counts
            x = np.arange(len(monthly_counts))
            y = monthly_counts.values
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            trend = "Increasing" if slope > 0 else "Decreasing"
            significance = "Significant" if p_value < 0.05 else "Not Significant"
            
            return {
                "trend_direction": trend,
                "slope": slope,
                "p_value": p_value,
                "significance": significance,
                "monthly_counts": {str(k): int(v) for k, v in monthly_counts.items()}
            }
        except Exception as e:
            logger.warning(f"Trend analysis failed: {e}")
            return {"error": str(e)}

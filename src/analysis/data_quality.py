
import hashlib
import logging
from typing import List, Dict, Any, Set
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class DataQualityChecker:
    """
    Ensures data quality for academic research.
    Includes deduplication, completeness checks, and basic statistics.
    """

    def __init__(self):
        pass

    def _compute_hash(self, text: str) -> str:
        """Compute MD5 hash of text for exact deduplication."""
        return hashlib.md5(text.strip().lower().encode('utf-8')).hexdigest()

    def _compute_simhash(self, text: str) -> int:
        """Compute a simple SimHash for near-duplicate detection."""
        # Simplified implementation for demonstration
        features = set(text.lower().split())
        hash_val = 0
        for feature in features:
            hash_val ^= hash(feature)
        return hash_val

    def detect_duplicates(self, docs: List[Dict[str, Any]], threshold: float = 0.9) -> List[Dict[str, Any]]:
        """
        Detect and remove duplicates.
        """
        logger.info("Running duplicate detection...")
        unique_docs = []
        seen_hashes = set()
        
        duplicates_count = 0
        
        for doc in docs:
            # Extract text content
            text = doc.get('content') or doc.get('text') or doc.get('body') or doc.get('snippet') or ""
            if not isinstance(text, str) or not text.strip():
                continue
                
            doc_hash = self._compute_hash(text)
            
            if doc_hash in seen_hashes:
                duplicates_count += 1
                continue
            
            seen_hashes.add(doc_hash)
            unique_docs.append(doc)
            
        logger.info(f"Removed {duplicates_count} duplicate documents. Remaining: {len(unique_docs)}")
        return unique_docs

    def assess_completeness(self, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assess the completeness of the dataset fields.
        """
        logger.info("Assessing data completeness...")
        if not docs:
            return {}
            
        df = pd.DataFrame(docs)
        stats = {
            "total_docs": len(docs),
            "missing_values": df.isnull().sum().to_dict(),
            "empty_strings": (df == "").sum().to_dict()
        }
        
        # Calculate completeness score
        total_cells = df.size
        missing_cells = df.isnull().sum().sum() + (df == "").sum().sum()
        completeness_score = 1.0 - (missing_cells / total_cells) if total_cells > 0 else 0.0
        
        stats["completeness_score"] = round(completeness_score, 4)
        logger.info(f"Data Completeness Score: {stats['completeness_score']}")
        return stats

    def generate_quality_report(self, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a full data quality report.
        """
        unique_docs = self.detect_duplicates(docs)
        completeness = self.assess_completeness(unique_docs)
        
        # Text length statistics
        lengths = [len(str(d.get('content', '') or d.get('text', ''))) for d in unique_docs]
        length_stats = {
            "min_length": int(np.min(lengths)) if lengths else 0,
            "max_length": int(np.max(lengths)) if lengths else 0,
            "mean_length": float(np.mean(lengths)) if lengths else 0,
            "median_length": float(np.median(lengths)) if lengths else 0
        }
        
        return {
            "quality_score": completeness.get("completeness_score", 0),
            "original_count": len(docs),
            "clean_count": len(unique_docs),
            "completeness_stats": completeness,
            "text_stats": length_stats,
            "cleaned_docs": unique_docs
        }

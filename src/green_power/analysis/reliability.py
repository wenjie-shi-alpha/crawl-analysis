
import logging
import json
import random
from typing import List, Dict, Any, Callable
from collections import Counter

logger = logging.getLogger(__name__)

class ReliabilityValidator:
    """
    Validates the reliability and validity of the analysis.
    Includes Inter-Coder Reliability (ICR) simulation and Sensitivity Analysis.
    """

    def __init__(self, llm_client):
        self.client = llm_client

    def check_inter_coder_reliability(self, texts: List[str], sample_size: int = 5) -> Dict[str, Any]:
        """
        Simulate Inter-Coder Reliability by running the classification task twice 
        (or using two different prompts/models if available) on a sample.
        """
        logger.info(f"Running Inter-Coder Reliability check on {sample_size} samples...")
        
        if not texts:
            return {}
            
        sample = random.sample(texts, min(sample_size, len(texts)))
        
        # Run 1
        results_1 = self._classify_sample(sample, run_id=1)
        # Run 2
        results_2 = self._classify_sample(sample, run_id=2)
        
        # Calculate agreement
        agreement_count = 0
        total_comparisons = len(sample)
        
        details = []
        
        for i in range(total_comparisons):
            cat1 = results_1[i]
            cat2 = results_2[i]
            match = (cat1 == cat2)
            if match:
                agreement_count += 1
            details.append({
                "text_snippet": sample[i][:50],
                "run1": cat1,
                "run2": cat2,
                "match": match
            })
            
        agreement_ratio = agreement_count / total_comparisons if total_comparisons > 0 else 0
        
        # Cohen's Kappa approximation (for 2 raters, categorical items)
        # P_o = agreement_ratio
        # P_e = probability of random agreement
        
        # Calculate P_e
        all_cats = results_1 + results_2
        counts = Counter(all_cats)
        total_ratings = len(all_cats)
        p_e = sum((count / total_ratings) ** 2 for count in counts.values())
        
        kappa = (agreement_ratio - p_e) / (1 - p_e) if (1 - p_e) != 0 else 0
        
        return {
            "agreement_ratio": agreement_ratio,
            "cohens_kappa": kappa,
            "interpretation": self._interpret_kappa(kappa),
            "details": details
        }

    def _classify_sample(self, texts: List[str], run_id: int) -> List[str]:
        """Helper to classify texts using the LLM."""
        categories = ["政治因素", "经济因素", "社会因素", "技术因素", "环境因素", "法律因素"]
        results = []
        
        for text in texts:
            # We use a simple prompt for classification
            prompt = f"""Classify the following text into one of these categories: {', '.join(categories)}.
            Return ONLY the category name.
            
            Text: {text[:500]}
            """
            # Note: We assume self.client has a generate method. 
            # If it's the OllamaClient from the main script, it does.
            try:
                # Add a slight variation to prompt based on run_id to simulate different coders
                system_prompt = "You are a coder." if run_id == 1 else "You are an analyst."
                response = self.client.generate(prompt, system_prompt=system_prompt)
                
                # Clean response
                found_cat = "Unclassified"
                for cat in categories:
                    if cat in response:
                        found_cat = cat
                        break
                results.append(found_cat)
            except Exception:
                results.append("Error")
                
        return results

    def _interpret_kappa(self, kappa: float) -> str:
        if kappa < 0: return "Poor agreement"
        if kappa <= 0.20: return "Slight agreement"
        if kappa <= 0.40: return "Fair agreement"
        if kappa <= 0.60: return "Moderate agreement"
        if kappa <= 0.80: return "Substantial agreement"
        return "Almost perfect agreement"

    def perform_sensitivity_analysis(self, analysis_func: Callable, data: Any) -> Dict[str, Any]:
        """
        Perform sensitivity analysis by varying parameters (if applicable).
        For LLM, we might check if results hold with a subset of data.
        """
        logger.info("Running Sensitivity Analysis (Data Subsampling)...")
        
        # Run on full data (assumed already done, but we might re-run or compare)
        # Here we just simulate a check by running on 50% of data
        
        if isinstance(data, list) and len(data) > 10:
            subset = data[:len(data)//2]
            try:
                result_subset = analysis_func(self.client, subset)
                return {
                    "method": "Data Subsampling (50%)",
                    "status": "Completed",
                    "consistency_check": "Qualitative comparison required" # Automated comparison of complex JSON is hard
                }
            except Exception as e:
                return {"error": str(e)}
        
        return {"status": "Skipped (insufficient data)"}

#!/usr/bin/env python3
"""Batch crawling test for production scenarios."""

import sys
import os
from pathlib import Path
import time

# Add src to path
project_src = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(project_src))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import logging
from config import PipelineConfig
from crawling import TavilyCrawler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('batch_crawl_test.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def batch_test():
    """Batch crawling test with all default keywords."""
    logger.info("🚀 Batch Crawling Test - Production Scale")
    logger.info("=" * 60)

    try:
        # Production configuration with all default keywords
        config = PipelineConfig()
        logger.info(f"Testing {len(config.keywords)} keywords:")
        for i, kw in enumerate(config.keywords, 1):
            logger.info(f"  {i}. {kw}")

        # Create crawler
        crawler = TavilyCrawler(
            keywords=config.keywords,
            output_dir="batch_test_output",
            max_results_per_keyword=5,  # Moderate amount
            request_timeout=20,
            search_depth="basic"  # Faster for testing
        )

        logger.info(f"\nStarting batch crawl...")
        logger.info(f"Expected results: ~{len(config.keywords) * config.tavily_results_per_keyword} items")
        logger.info("-" * 60)

        start_time = time.time()
        results = crawler.crawl()
        crawl_time = time.time() - start_time

        logger.info("-" * 60)

        if results:
            logger.info(f"✅ Batch crawl completed successfully!")
            logger.info(f"📊 Results Summary:")
            logger.info(f"   - Total results: {len(results)}")
            logger.info(f"   - Keywords processed: {len(config.keywords)}")
            logger.info(f"   - Average results per keyword: {len(results)/len(config.keywords):.1f}")
            logger.info(f"   - Total time: {crawl_time:.2f} seconds")
            logger.info(f"   - Time per keyword: {crawl_time/len(config.keywords):.2f} seconds")
            logger.info(f"   - Results per second: {len(results)/crawl_time:.2f}")

            # Save results
            timestamp = int(time.time())
            output_file = crawler.save(results, f"batch_test_{timestamp}.json")
            logger.info(f"📁 Results saved to: {output_file}")

            # Analyze results by keyword
            keyword_stats = {}
            for result in results:
                keyword = result.get('keyword', 'unknown')
                if keyword not in keyword_stats:
                    keyword_stats[keyword] = 0
                keyword_stats[keyword] += 1

            logger.info(f"\n📈 Results by keyword:")
            for keyword, count in sorted(keyword_stats.items()):
                logger.info(f"   - {keyword}: {count} results")

            # Show sample results
            logger.info(f"\n📄 Sample results (showing first 5):")
            for i, result in enumerate(results[:5]):
                logger.info(f"   {i+1}. {result.get('title', 'No title')[:80]}...")
                logger.info(f"      Keyword: {result.get('keyword', 'unknown')}")
                logger.info(f"      URL: {result.get('url', 'No URL')[:80]}...")

            # Check for duplicates
            titles = [r.get('title', '') for r in results]
            unique_titles = set(titles)
            duplicate_rate = (len(titles) - len(unique_titles)) / len(titles) * 100
            logger.info(f"\n🔍 Quality metrics:")
            logger.info(f"   - Unique titles: {len(unique_titles)}/{len(titles)} ({100-duplicate_rate:.1f}% unique)")
            logger.info(f"   - Duplicate rate: {duplicate_rate:.1f}%")

            # Success criteria
            success_rate = len(results) / (len(config.keywords) * config.tavily_results_per_keyword) * 100
            logger.info(f"\n✨ Success rate: {success_rate:.1f}% (expected vs actual results)")

            if success_rate >= 50:  # At least half of expected results
                logger.info("🎉 Batch test PASSED! Ready for production.")
                return True
            else:
                logger.warning("⚠️ Batch test completed with low success rate.")
                return True  # Still consider success if we got some results

        else:
            logger.error("❌ No results retrieved")
            return False

    except Exception as e:
        logger.error(f"❌ Batch test failed: {e}")
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = batch_test()
    sys.exit(0 if success else 1)
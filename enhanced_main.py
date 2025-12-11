#!/usr/bin/env python3
"""Enhanced main entry point with improved error handling and monitoring."""

import sys
import signal
import logging
from pathlib import Path
from typing import Optional

# Add src to path
project_src = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(project_src))

from utils.logging_config import setup_logging, ProgressTracker
from utils.security import SecureConfig
from config import PipelineConfig
from pipeline import GreenPowerPipeline

# Global variables for graceful shutdown
shutdown_requested = False
current_progress: Optional[ProgressTracker] = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logging.getLogger(__name__).info(f"Received signal {signum}. Initiating graceful shutdown...")
    shutdown_requested = True
    if current_progress:
        logging.getLogger(__name__).info(f"Current progress: {current_progress.current}/{current_progress.total}")


def setup_secure_environment(config: PipelineConfig) -> PipelineConfig:
    """Setup secure configuration handling."""
    if not config.secure_config:
        return config

    secure_config = SecureConfig()
    stored_config = secure_config.decrypt_config()

    # Override environment variables with stored secure config if available
    if stored_config.get('openai_api_key'):
        config.openai_api_key = stored_config['openai_api_key']
    if stored_config.get('tavily_api_key'):
        # Add TAVILY_API_KEY to environment
        import os
        os.environ['TAVILY_API_KEY'] = stored_config['tavily_api_key']

    return config


def run_with_monitoring(config: PipelineConfig) -> int:
    """Run pipeline with enhanced monitoring."""
    # Setup logging
    log_file = config.log_file or config.paths().meta_dir / f"pipeline_{config.timestamp()}.log"
    logger, performance_monitor = setup_logging(
        log_level=config.log_level,
        log_file=log_file,
        structured=True
    )

    logger.info("🚀 Starting enhanced Green Power Analysis Pipeline")
    logger.info(f"Configuration: {config}")

    try:
        # Setup secure environment
        config = setup_secure_environment(config)

        # Initialize pipeline
        pipeline = GreenPowerPipeline(config)

        # Run full pipeline with progress tracking
        global current_progress
        current_progress = ProgressTracker(total=4, task_name="Pipeline Stages", logger=logger)

        # Stage 1: Crawling
        if not shutdown_requested:
            current_progress.update(1, "Starting crawling stage")
            logger.info("📡 Stage 1: Data Crawling")
            raw_file = pipeline.crawl()
            logger.info(f"✅ Crawling completed: {raw_file}")

        # Stage 2: Preprocessing
        if not shutdown_requested:
            current_progress.update(1, "Starting preprocessing stage")
            logger.info("🔧 Stage 2: Text Preprocessing")
            processed_files = pipeline.preprocess()
            logger.info(f"✅ Preprocessing completed: {len(processed_files)} files")

        # Stage 3: Analysis
        if not shutdown_requested:
            current_progress.update(1, "Starting analysis stage")
            logger.info("🧠 Stage 3: OpenAI Analysis")
            analysis_report = pipeline.analyze()
            logger.info(f"✅ Analysis completed: {analysis_report}")

        # Stage 4: Reporting
        if not shutdown_requested:
            current_progress.update(1, "Starting reporting stage")
            logger.info("📊 Stage 4: Results Reporting")
            reporting_outputs = pipeline.report()
            logger.info(f"✅ Reporting completed: {reporting_outputs}")

        current_progress = None

        # Log performance summary
        if config.performance_monitoring:
            performance_monitor.log_summary(logger)

        logger.info("🎉 Pipeline completed successfully!")
        return 0

    except KeyboardInterrupt:
        logger.info("⏹️ Pipeline interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"💥 Pipeline failed: {e}", exc_info=True)
        return 1
    finally:
        if shutdown_requested:
            logger.warning("⚠️ Pipeline was shutdown during execution")


def main() -> int:
    """Enhanced main function with better error handling."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Create default configuration
        config = PipelineConfig()

        # You could add command line argument parsing here if needed
        # For now, using defaults

        return run_with_monitoring(config)

    except Exception as e:
        logging.getLogger(__name__).error(f"Fatal error in main: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
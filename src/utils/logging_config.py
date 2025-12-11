"""Enhanced logging configuration for the project."""

import logging
import logging.handlers
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import sys


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    module: str
    message: str
    details: Optional[Dict[str, Any]] = None


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created).isoformat(),
            level=record.levelname,
            module=record.name,
            message=record.getMessage(),
            details={
                'function': record.funcName,
                'line': record.lineno,
                'thread': threading.current_thread().name,
            }
        )

        # Add exception info if present
        if record.exc_info:
            log_entry.details['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry.details[key] = value

        return json.dumps(asdict(log_entry), ensure_ascii=False, default=str)


class ProgressTracker:
    """Track and log progress for long-running tasks."""

    def __init__(self, total: int, task_name: str, logger: logging.Logger):
        self.total = total
        self.current = 0
        self.task_name = task_name
        self.logger = logger
        self.start_time = time.time()
        self.last_log_time = 0
        self.log_interval = 10  # Log every 10 seconds

    def update(self, increment: int = 1, message: str = None) -> None:
        """Update progress counter."""
        self.current += increment
        current_time = time.time()

        # Log progress periodically
        if current_time - self.last_log_time >= self.log_interval or self.current >= self.total:
            elapsed = current_time - self.start_time
            progress_percent = (self.current / self.total) * 100

            if self.total > 0:
                estimated_total = elapsed * self.total / self.current
                remaining = estimated_total - elapsed
                eta_str = f", ETA: {remaining:.0f}s"
            else:
                eta_str = ""

            log_message = f"{self.task_name}: {self.current}/{self.total} ({progress_percent:.1f}%)"
            if message:
                log_message += f" - {message}"

            log_message += f" (elapsed: {elapsed:.0f}s{eta_str})"

            if self.current >= self.total:
                self.logger.info(f"✅ {self.task_name} completed in {elapsed:.1f}s")
            else:
                self.logger.info(log_message)

            self.last_log_time = current_time

    def set_current(self, current: int, message: str = None) -> None:
        """Set current progress directly."""
        increment = current - self.current
        if increment > 0:
            self.update(increment, message)


class PerformanceMonitor:
    """Monitor performance metrics."""

    def __init__(self):
        self.metrics: Dict[str, list] = {}
        self.lock = threading.Lock()

    def record_timing(self, operation: str, duration: float) -> None:
        """Record timing for an operation."""
        with self.lock:
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(duration)

    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation."""
        with self.lock:
            timings = self.metrics.get(operation, [])
            if not timings:
                return {}

            return {
                'count': len(timings),
                'avg': sum(timings) / len(timings),
                'min': min(timings),
                'max': max(timings),
                'total': sum(timings)
            }

    def log_summary(self, logger: logging.Logger) -> None:
        """Log performance summary."""
        with self.lock:
            if not self.metrics:
                return

            logger.info("📊 Performance Summary:")
            for operation, timings in self.metrics.items():
                stats = self.get_stats(operation)
                logger.info(f"  {operation}: {stats['count']} calls, "
                          f"avg {stats['avg']:.2f}s, "
                          f"min {stats['min']:.2f}s, "
                          f"max {stats['max']:.2f}s, "
                          f"total {stats['total']:.2f}s")


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    structured: bool = True
) -> tuple[logging.Logger, PerformanceMonitor]:
    """Setup enhanced logging configuration."""

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if structured:
        console_formatter = StructuredFormatter()
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (rotating)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_formatter = StructuredFormatter() if structured else console_formatter
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Set specific logger levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)

    # Create performance monitor
    performance_monitor = PerformanceMonitor()

    return root_logger, performance_monitor


def log_function_performance(logger: logging.Logger, monitor: PerformanceMonitor):
    """Decorator to log function performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            operation_name = f"{func.__module__}.{func.__name__}"

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                monitor.record_timing(operation_name, duration)
                logger.debug(f"⏱️ {operation_name} completed in {duration:.2f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                monitor.record_timing(f"{operation_name} (failed)", duration)
                logger.error(f"❌ {operation_name} failed after {duration:.2f}s: {e}")
                raise

        return wrapper
    return decorator
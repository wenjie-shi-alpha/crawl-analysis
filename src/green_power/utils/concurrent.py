"""Concurrent processing utilities for improved performance."""

import asyncio
import threading
import queue
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional, Iterator
from dataclasses import dataclass
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of a processed task."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0


class WorkerThreadPool:
    """Thread pool with task queuing and result aggregation."""

    def __init__(self, max_workers: int = 4, timeout: float = 300.0):
        self.max_workers = max_workers
        self.timeout = timeout
        self.executor: Optional[ThreadPoolExecutor] = None
        self.results: List[TaskResult] = []
        self.lock = threading.Lock()

    def __enter__(self):
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.executor:
            self.executor.shutdown(wait=True)

    def submit_task(self, func: Callable, task_id: str, *args, **kwargs) -> None:
        """Submit a task to the thread pool."""
        if not self.executor:
            raise RuntimeError("ThreadPool not initialized. Use as context manager.")

        future = self.executor.submit(self._wrap_task, func, task_id, *args, **kwargs)
        return future

    def _wrap_task(self, func: Callable, task_id: str, *args, **kwargs) -> TaskResult:
        """Wrap function execution with timing and error handling."""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            task_result = TaskResult(
                task_id=task_id,
                success=True,
                result=result,
                duration=duration
            )
        except Exception as e:
            duration = time.time() - start_time
            task_result = TaskResult(
                task_id=task_id,
                success=False,
                error=e,
                duration=duration
            )
            logger.error(f"Task {task_id} failed: {e}")

        # Thread-safe result storage
        with self.lock:
            self.results.append(task_result)

        return task_result

    def wait_for_completion(self) -> List[TaskResult]:
        """Wait for all tasks to complete and return results."""
        if not self.executor:
            return self.results

        # Wait for all futures to complete
        self.executor.shutdown(wait=True)
        return self.results

    def get_progress(self) -> Dict[str, int]:
        """Get current progress statistics."""
        with self.lock:
            total = len(self.results)
            successful = sum(1 for r in self.results if r.success)
            failed = total - successful
            return {
                'total': total,
                'successful': successful,
                'failed': failed,
                'success_rate': successful / total if total > 0 else 0.0
            }


class BatchProcessor:
    """Process items in batches with concurrent execution."""

    def __init__(self, batch_size: int = 10, max_workers: int = 4):
        self.batch_size = batch_size
        self.max_workers = max_workers

    def process_batches(
        self,
        items: List[Any],
        process_func: Callable,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """Process items in batches concurrently."""
        results = []
        total_items = len(items)
        processed_items = 0

        # Create batches
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, total_items, self.batch_size)
        ]

        logger.info(f"Processing {total_items} items in {len(batches)} batches "
                   f"(batch_size={self.batch_size}, workers={self.max_workers})")

        with WorkerThreadPool(max_workers=self.max_workers) as pool:
            # Submit all batch tasks
            futures = []
            for i, batch in enumerate(batches):
                future = pool.submit_task(
                    self._process_batch,
                    f"batch_{i}",
                    process_func,
                    batch
                )
                futures.append(future)

            # Wait for completion and collect results
            for future in as_completed(futures):
                try:
                    task_result = future.result(timeout=600)  # 10 minute timeout
                    if task_result.success:
                        results.extend(task_result.result)
                        processed_items += len(task_result.result)
                    else:
                        logger.error(f"Batch failed: {task_result.error}")

                    if progress_callback:
                        progress_callback(processed_items, total_items)

                except Exception as e:
                    logger.error(f"Error processing batch: {e}")

        logger.info(f"Batch processing completed. Processed {len(results)} items.")
        return results

    def _process_batch(self, process_func: Callable, batch: List[Any]) -> List[Any]:
        """Process a single batch."""
        batch_results = []
        for item in batch:
            try:
                result = process_func(item)
                if result is not None:
                    batch_results.append(result)
            except Exception as e:
                logger.error(f"Error processing item {item}: {e}")
        return batch_results


class AsyncTaskQueue:
    """Asynchronous task queue for I/O-bound operations."""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.queue = asyncio.Queue()
        self.results = []
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def add_task(self, coro, task_id: str = None) -> None:
        """Add a coroutine task to the queue."""
        await self.queue.put((coro, task_id))

    async def process_all(self) -> List[TaskResult]:
        """Process all tasks in the queue."""
        tasks = []
        while not self.queue.empty():
            coro, task_id = await self.queue.get()
            task = asyncio.create_task(self._wrap_async_task(coro, task_id))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, TaskResult)]

    async def _wrap_async_task(self, coro, task_id: str = None) -> TaskResult:
        """Wrap coroutine with error handling and timing."""
        start_time = time.time()
        try:
            async with self.semaphore:
                result = await coro
                duration = time.time() - start_time
                return TaskResult(
                    task_id=task_id or "unknown",
                    success=True,
                    result=result,
                    duration=duration
                )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Async task {task_id} failed: {e}")
            return TaskResult(
                task_id=task_id or "unknown",
                success=False,
                error=e,
                duration=duration
            )


def process_files_concurrently(
    file_paths: List[Path],
    process_func: Callable[[Path], Any],
    max_workers: int = 4,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[Any]:
    """Process multiple files concurrently."""
    processor = BatchProcessor(batch_size=1, max_workers=max_workers)
    return processor.process_batches(file_paths, process_func, progress_callback)


def save_results_incrementally(
    results: List[Any],
    output_file: Path,
    batch_size: int = 100
) -> None:
    """Save results incrementally to prevent data loss."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    for i in range(0, len(results), batch_size):
        batch = results[i:i + batch_size]
        mode = 'w' if i == 0 else 'a'

        with open(output_file, mode, encoding='utf-8') as f:
            for result in batch:
                f.write(json.dumps(result, ensure_ascii=False, default=str) + '\n')
                f.flush()  # Ensure data is written immediately
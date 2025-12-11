"""Enhanced network utilities with retry and rate limiting."""

import time
import random
import logging
import requests
from typing import Optional, Dict, Any, Callable
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    backoff_factor: float = 1.0
    retry_on_status: list = None
    retry_on_exceptions: tuple = None

    def __post_init__(self):
        if self.retry_on_status is None:
            self.retry_on_status = [429, 500, 502, 503, 504]
        if self.retry_on_exceptions is None:
            self.retry_on_exceptions = (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError
            )


class RateLimiter:
    """Simple rate limiter to prevent overwhelming servers."""

    def __init__(self, calls_per_second: float = 1.0):
        self.calls_per_second = calls_per_second
        self.last_call = 0
        self.lock = threading.Lock()

    def wait(self) -> None:
        """Wait if necessary to respect rate limit."""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_call
            min_interval = 1.0 / self.calls_per_second

            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_call = time.time()


def retry_with_backoff(retry_config: Optional[RetryConfig] = None):
    """Decorator for retrying functions with exponential backoff."""
    if retry_config is None:
        retry_config = RetryConfig()

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(retry_config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_config.retry_on_exceptions as e:
                    last_exception = e

                    if attempt == retry_config.max_retries:
                        logger.error(f"Function {func.__name__} failed after {attempt + 1} attempts: {e}")
                        raise

                    # Calculate backoff time with jitter
                    base_delay = retry_config.backoff_factor * (2 ** attempt)
                    jitter = random.uniform(0.1, 0.3) * base_delay
                    delay = base_delay + jitter

                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s")
                    time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


class EnhancedSession(requests.Session):
    """Enhanced requests session with retry logic and rate limiting."""

    def __init__(self, retry_config: Optional[RetryConfig] = None, rate_limit: float = 1.0):
        super().__init__()
        self.retry_config = retry_config or RetryConfig()
        self.rate_limiter = RateLimiter(rate_limit)

        # Configure retry adapter
        retry_strategy = Retry(
            total=self.retry_config.max_retries,
            backoff_factor=self.retry_config.backoff_factor,
            status_forcelist=self.retry_config.retry_on_status,
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.mount("http://", adapter)
        self.mount("https://", adapter)

        # Set default headers
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ProjectResearch/1.0; +https://example.com/bot)',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

    @retry_with_backoff()
    def get(self, url: str, **kwargs) -> requests.Response:
        """Enhanced GET method with rate limiting."""
        self.rate_limiter.wait()
        return super().get(url, **kwargs)

    @retry_with_backoff()
    def post(self, url: str, **kwargs) -> requests.Response:
        """Enhanced POST method with rate limiting."""
        self.rate_limiter.wait()
        return super().post(url, **kwargs)

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Enhanced request method with timeout and error handling."""
        # Set default timeout
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30

        # Validate URL
        from .security import validate_url
        if not validate_url(url):
            raise ValueError(f"Invalid URL: {url}")

        try:
            response = super().request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {method} {url}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for {method} {url}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for {method} {url}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {e}")
            raise


def create_session(retry_config: Optional[RetryConfig] = None, rate_limit: float = 1.0) -> EnhancedSession:
    """Create an enhanced session with retry and rate limiting."""
    return EnhancedSession(retry_config, rate_limit)
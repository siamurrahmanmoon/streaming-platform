import asyncio
import functools
import inspect
from tqdm import tqdm
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import config


def retry_with_backoff(max_retries=None, base_delay=None):
    max_retries = max_retries or config.MAX_RETRIES
    base_delay = base_delay or config.RETRY_DELAY_BASE

    def decorator(func):
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as error:
                        delay = base_delay * (2**attempt)
                        tqdm.write(
                            f"{func.__name__} failed (Attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {delay}s... Error: {error}"
                        )
                        await asyncio.sleep(delay)
                tqdm.write(f"{func.__name__} failed after {max_retries} attempts.")
                return None

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as error:
                    delay = base_delay * (2**attempt)
                    tqdm.write(
                        f"{func.__name__} failed (Attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay}s... Error: {error}"
                    )
                    import time

                    time.sleep(delay)
            tqdm.write(f"{func.__name__} failed after {max_retries} attempts.")
            return None

        return sync_wrapper

    return decorator

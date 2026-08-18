import asyncio
import functools
from tqdm import tqdm
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import config

def retry_with_backoff(max_retries=None, base_delay=None):
    max_retries = max_retries or config.MAX_RETRIES
    base_delay = base_delay or config.RETRY_DELAY_BASE

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    delay = base_delay * (2 ** (attempt - 1))  # Exponential backoff
                    tqdm.write(f"⚠️ {func.__name__} failed (Attempt {attempt}/{max_retries}). Retrying in {delay}s... Error: {e}")
                    await asyncio.sleep(delay)
            tqdm.write(f"❌ {func.__name__} failed after {max_retries} attempts.")
            return None
        return wrapper
    return decorator
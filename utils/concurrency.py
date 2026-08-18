import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import config

class UploadLimiter:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_UPLOADS)
        self.bandwidth_limit_bytes_per_sec = config.BANDWIDTH_LIMIT_MBPS * 1024 * 1024 if config.BANDWIDTH_LIMIT_MBPS > 0 else 0

    async def __aenter__(self):
        await self.semaphore.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.semaphore.release()

    async def throttled_read(self, file_obj, chunk_size: int) -> bytes:
        """Read chunk and apply bandwidth throttling if configured."""
        chunk = file_obj.read(chunk_size)
        if self.bandwidth_limit_bytes_per_sec > 0 and chunk:
            sleep_time = len(chunk) / self.bandwidth_limit_bytes_per_sec
            await asyncio.sleep(sleep_time)
        return chunk

# Global instance to be shared across all uploads
limiter = UploadLimiter()
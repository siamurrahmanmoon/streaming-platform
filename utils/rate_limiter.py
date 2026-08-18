import asyncio
import time
from typing import Dict, Optional
from loguru import logger

class RateLimiter:
    """Handles API rate limiting with exponential backoff"""
    
    def __init__(self):
        self.retry_counts: Dict[str, int] = {}
        self.cooldown_until: Dict[str, float] = {}
        
    async def check_rate_limit(self, api_name: str, response_status: int, response_text: str = "") -> bool:
        """
        Check if we're being rate limited.
        Returns True if we should retry, False if we should stop.
        """
        # Check if we're in cooldown
        if api_name in self.cooldown_until:
            if time.time() < self.cooldown_until[api_name]:
                wait_time = self.cooldown_until[api_name] - time.time()
                logger.warning(f"⏳ {api_name} in cooldown, waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                return True
        
        # Handle 429 Too Many Requests
        if response_status == 429:
            retry_count = self.retry_counts.get(api_name, 0) + 1
            self.retry_counts[api_name] = retry_count
            
            # Exponential backoff: 60s, 120s, 240s, 480s...
            wait_time = 60 * (2 ** (retry_count - 1))
            wait_time = min(wait_time, 3600)  # Max 1 hour
            
            self.cooldown_until[api_name] = time.time() + wait_time
            
            logger.warning(f"️ {api_name} rate limited! Waiting {wait_time}s (attempt {retry_count})")
            
            # Reset after 1 hour
            if retry_count >= 6:
                self.retry_counts[api_name] = 0
                
            return True
        
        # Handle 503 Service Unavailable
        if response_status == 503:
            retry_count = self.retry_counts.get(api_name, 0) + 1
            self.retry_counts[api_name] = retry_count
            
            wait_time = 30 * retry_count
            self.cooldown_until[api_name] = time.time() + wait_time
            
            logger.warning(f"⚠️ {api_name} unavailable! Waiting {wait_time}s")
            return True
        
        # Success - reset counters
        if response_status in [200, 201]:
            if api_name in self.retry_counts:
                logger.info(f"✅ {api_name} rate limit reset")
            self.retry_counts[api_name] = 0
            if api_name in self.cooldown_until:
                del self.cooldown_until[api_name]
        
        return False
    
    def get_status(self, api_name: str) -> Dict:
        """Get current rate limit status for an API"""
        return {
            'retry_count': self.retry_counts.get(api_name, 0),
            'in_cooldown': api_name in self.cooldown_until and time.time() < self.cooldown_until[api_name],
            'cooldown_remaining': max(0, self.cooldown_until.get(api_name, 0) - time.time())
        }

# Global instance
rate_limiter = RateLimiter()
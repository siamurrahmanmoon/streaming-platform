import os
import aiohttp
from pathlib import Path
from typing import Optional
from loguru import logger

class AlertManager:
    """Sends alerts to Telegram/Discord when critical events occur"""
    
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        
    async def send_telegram(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send alert to Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        logger.info(f"✅ Telegram alert sent")
                        return True
                    else:
                        logger.error(f" Telegram alert failed: {resp.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Telegram alert error: {e}")
            return False
    
    async def send_discord(self, message: str, color: int = 16711680) -> bool:
        """Send alert to Discord webhook"""
        if not self.discord_webhook:
            return False
            
        try:
            payload = {
                'embeds': [{
                    'title': '🚨 Anime Uploader Alert',
                    'description': message,
                    'color': color
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status in [200, 204]:
                        logger.info(f"✅ Discord alert sent")
                        return True
                    else:
                        logger.error(f"❌ Discord alert failed: {resp.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Discord alert error: {e}")
            return False
    
    async def notify_critical(self, title: str, message: str):
        """Send critical alert to all configured platforms"""
        full_message = f"<b>🚨 {title}</b>\n\n{message}"
        
        await self.send_telegram(full_message)
        await self.send_discord(message)
        
    async def notify_success(self, title: str, message: str):
        """Send success notification"""
        full_message = f"<b>✅ {title}</b>\n\n{message}"
        
        await self.send_telegram(full_message)
        await self.send_discord(message, color=3066993)

# Global instance
alert_manager = AlertManager()
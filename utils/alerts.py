import os
from io import BytesIO
import aiohttp
from loguru import logger

DISCORD_WEBHOOK_PREFIXES = (
    'https://discord.com/api/webhooks/',
    'https://discordapp.com/api/webhooks/',
)

class AlertManager:
    """Sends alerts to Telegram/Discord with Poster"""
    
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        
    async def send_telegram(self, message: str, parse_mode: str = "HTML") -> bool:
        if not self.telegram_token or not self.telegram_chat_id:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {'chat_id': self.telegram_chat_id, 'text': message, 'parse_mode': parse_mode}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"❌ Telegram text alert error: {e}")
            return False
    
    async def send_telegram_photo(self, photo_url: str, caption: str, parse_mode: str = "HTML") -> bool:
        if not self.telegram_token or not self.telegram_chat_id:
            return False
        try:
            async with aiohttp.ClientSession() as session:
                download_timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=50)
                async with session.get(photo_url, timeout=download_timeout) as photo_response:
                    if photo_response.status != 200:
                        logger.error(f"❌ Poster download failed: HTTP {photo_response.status}")
                        return False
                    photo_bytes = await photo_response.read()

                form = aiohttp.FormData()
                form.add_field('chat_id', self.telegram_chat_id)
                form.add_field('caption', caption)
                form.add_field('parse_mode', parse_mode)
                form.add_field(
                    'photo',
                    BytesIO(photo_bytes),
                    filename='poster.jpg',
                    content_type='image/jpeg'
                )

                telegram_url = f"https://api.telegram.org/bot{self.telegram_token}/sendPhoto"
                async with session.post(telegram_url, data=form, timeout=download_timeout) as resp:
                    if resp.status == 200:
                        logger.info("✅ Telegram photo sent successfully!")
                        return True
                    response_text = await resp.text()
                    logger.error(
                        f"❌ Telegram photo failed (Status: {resp.status}, "
                        f"Response: {response_text[:200]})"
                    )
                    return False
        except Exception as e:
            logger.error(f"❌ Telegram photo alert error: {type(e).__name__}: {e}")
            return False

    async def send_discord(self, message: str, color: int = 16711680) -> bool:
        if not self.discord_webhook or not self.discord_webhook.startswith(DISCORD_WEBHOOK_PREFIXES):
            return False
        try:
            payload = {'embeds': [{'title': '🚨 Anime Uploader Alert', 'description': message, 'color': color}]}
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return resp.status in [200, 204]
        except Exception as e:
            logger.error(f"❌ Discord alert error: {e}")
            return False
    
    async def notify_video_upload_success(self, metadata) -> bool:
        # Keep long titles within Telegram's caption limit.
        title = metadata.title
        if len(title) > 50:
            title = title[:47] + "..."

        message = f"<b>✅ New video uploaded successfully!</b>\n\n"
        message += f"<b>📺 Title:</b> {title}\n"
        
        if metadata.media_type == "Movie":
            message += f"<b>🎞️ Type:</b> Movie\n"
        else:
            message += f"<b>📅 Season:</b> {metadata.season} | <b>Episode:</b> {metadata.episode}\n"
        
        if metadata.release_year:
            message += f"<b>Year:</b> {metadata.release_year}\n"
        
        message += f"<b>Quality:</b> {metadata.quality}\n"
        message += f"<b>🌍 Languages:</b> {', '.join(metadata.languages)}\n"
        message += f"<b>💾 Size:</b> {metadata.file_size / (1024*1024):.2f} MB\n"
        
        if metadata.vote_average and metadata.vote_average > 0:
            message += f"<b>⭐ Rating:</b> {metadata.vote_average}/10\n"
        
        if metadata.genres:
            genre_names = [g['name'] if isinstance(g, dict) else str(g) for g in metadata.genres[:3]]
            message += f"<b>Genres:</b> {', '.join(genre_names)}\n"
        
        message += f"\n<b>🔗 Upload links:</b>\n"
        if metadata.doodstream_url:
            message += f"• <a href='{metadata.doodstream_url}'>DoodStream</a>\n"
        if metadata.mixdrop_url:
            message += f"• <a href='{metadata.mixdrop_url}'>MixDrop</a>\n"
        if metadata.streamtape_url:
            message += f"• <a href='{metadata.streamtape_url}'>StreamTape</a>\n"
        
        # Send the poster when metadata includes a poster URL.
        poster_url = metadata.poster_url if metadata.poster_url else None
        
        if poster_url:
            photo_sent = await self.send_telegram_photo(poster_url, message)
            if not photo_sent:
                logger.error("❌ Required Telegram poster notification was not sent.")
        else:
            logger.error("❌ Required Telegram poster notification skipped: no poster URL.")
            
        await self.send_discord(message, color=3066993)
        return True
    
    async def notify_unmatched_video(self, filename: str, title: str, year: int = None):
        message = f"<b>❌ Video metadata match failed!</b>\n\n"
        message += f"<b>📁 File:</b> <code>{filename}</code>\n"
        message += f"<b>📺 Title:</b> {title}\n"
        if year:
            message += f"<b>🗓️ Year:</b> {year}\n"
        message += f"\n⚠️ The file was moved to the <code>unmatched_videos</code> folder.\n"
        message += f"💡 Rename the file according to the TMDB naming convention and try again."
        
        await self.send_telegram(message)
        await self.send_discord(message, color=16711680)

    async def notify_critical(self, title: str, message: str):
        full_message = f"<b>🚨 {title}</b>\n\n{message}"
        await self.send_telegram(full_message)
        await self.send_discord(message, color=16711680)

alert_manager = AlertManager()
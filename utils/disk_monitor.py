import os
import shutil
from pathlib import Path
from typing import Tuple
from loguru import logger
from utils.alerts import alert_manager

class DiskMonitor:
    """Monitors disk space and alerts when running low"""
    
    def __init__(self, warning_threshold: float = 90.0, critical_threshold: float = 95.0):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.last_alert_time = 0
        
    def get_disk_usage(self, path: str = "/") -> Tuple[float, float, float]:
        """Returns (total, used, free) in GB"""
        usage = shutil.disk_usage(path)
        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        return total_gb, used_gb, free_gb
    
    def get_usage_percentage(self, path: str = "/") -> float:
        """Returns disk usage percentage"""
        usage = shutil.disk_usage(path)
        return (usage.used / usage.total) * 100
    
    async def check_and_alert(self, path: str = "/") -> bool:
        """Check disk space and send alert if needed"""
        try:
            usage_percent = self.get_usage_percentage(path)
            total_gb, used_gb, free_gb = self.get_disk_usage(path)
            
            if usage_percent >= self.critical_threshold:
                message = f"🚨 <b>CRITICAL: Disk Space Low!</b>\n\n"
                message += f"Usage: {usage_percent:.1f}%\n"
                message += f"Total: {total_gb:.2f} GB\n"
                message += f"Used: {used_gb:.2f} GB\n"
                message += f"Free: {free_gb:.2f} GB\n\n"
                message += "⚠️ Uploads may fail! Please free up space immediately."
                
                await alert_manager.notify_critical("Disk Space Critical", message)
                logger.critical(f"🚨 CRITICAL: Disk usage at {usage_percent:.1f}% - Only {free_gb:.2f} GB free!")
                return False
                
            elif usage_percent >= self.warning_threshold:
                message = f"⚠️ <b>WARNING: Disk Space Running Low</b>\n\n"
                message += f"Usage: {usage_percent:.1f}%\n"
                message += f"Free: {free_gb:.2f} GB\n\n"
                message += "Consider freeing up space soon."
                
                await alert_manager.notify_critical("Disk Space Warning", message)
                logger.warning(f"⚠️ WARNING: Disk usage at {usage_percent:.1f}% - {free_gb:.2f} GB free")
                return True
            else:
                logger.debug(f" Disk usage: {usage_percent:.1f}% ({free_gb:.2f} GB free)")
                return True
                
        except Exception as e:
            logger.error(f"❌ Disk monitoring error: {e}")
            return True

# Global instance
disk_monitor = DiskMonitor()
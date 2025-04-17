import os
import time
import shutil
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Union
from utils.singleton import Singleton

from loguru import logger
import aiofiles
import aiofiles.os


class PermanentMediaStorage(metaclass=Singleton):
    """永久媒体存储管理器，用于永久保存从MediaManager复制的媒体文件"""
    
    def __init__(self, base_dir: str = "resource/permanent_media"):
        """初始化永久存储管理器
        
        Args:
            base_dir: 永久存储的基础目录
        """
        self.base_dir = base_dir
        self.media_manager = MediaManager()
        
        # 确保目录存在
        os.makedirs(base_dir, exist_ok=True)
    
    async def save_voice(self, msg_id: str, date: Optional[str] = None) -> Optional[str]:
        """从MediaManager复制语音文件到永久存储
        
        Args:
            msg_id: 消息ID
            date: 日期字符串（格式：YYYYMMDD），如果为None则搜索所有日期
            
        Returns:
            Optional[str]: 语音文件保存路径，不存在则为None
        """
        voice_path = self.media_manager.get_voice(msg_id, date)
        if not voice_path:
            return None
            
        voice_dir = os.path.join(self.base_dir, "voice")
        os.makedirs(voice_dir, exist_ok=True)
        save_path = os.path.join(voice_dir, f"{msg_id}.wav")
        
        async with aiofiles.open(voice_path, "rb") as src, aiofiles.open(save_path, "wb") as dst:
            await dst.write(await src.read())
        return save_path
    
    async def save_image(self, msg_id: str, date: Optional[str] = None) -> Optional[str]:
        """从MediaManager复制图片文件到永久存储
        
        Args:
            msg_id: 消息ID
            date: 日期字符串（格式：YYYYMMDD），如果为None则搜索所有日期
            
        Returns:
            Optional[str]: 图片文件保存路径，不存在则为None
        """
        image_path = self.media_manager.get_image(msg_id, date)
        if not image_path:
            return None
            
        image_dir = os.path.join(self.base_dir, "image")
        os.makedirs(image_dir, exist_ok=True)
        save_path = os.path.join(image_dir, f"{msg_id}.jpg")
        
        async with aiofiles.open(image_path, "rb") as src, aiofiles.open(save_path, "wb") as dst:
            await dst.write(await src.read())
        return save_path
    
    async def delete_voice(self, msg_id: str) -> None:
        """删除指定消息ID的语音文件
        
        Args:
            msg_id: 消息ID
        """
        voice_path = os.path.join(self.base_dir, "voice", f"{msg_id}.wav")
        logger.info(f"删除语音文件: {voice_path}")
        if await aiofiles.os.path.exists(voice_path):
            await aiofiles.os.remove(voice_path)
    
    async def delete_image(self, msg_id: str) -> None:
        """删除指定消息ID的图片文件
        
        Args:
            msg_id: 消息ID
        """
        image_path = os.path.join(self.base_dir, "image", f"{msg_id}.jpg")
        logger.info(f"删除图片文件: {image_path}")

        if await aiofiles.os.path.exists(image_path):
            await aiofiles.os.remove(image_path)
    
    async def get_voice(self, msg_id: str) -> Optional[str]:
        """获取指定消息ID的语音文件路径
        
        Args:
            msg_id: 消息ID
            
        Returns:
            Optional[str]: 语音文件路径，不存在则为None
        """
        voice_path = os.path.join(self.base_dir, "voice", f"{msg_id}.wav")
        return voice_path if await aiofiles.os.path.exists(voice_path) else None
    
    async def get_image(self, msg_id: str) -> Optional[str]:
        """获取指定消息ID的图片文件路径
        
        Args:
            msg_id: 消息ID
            
        Returns:
            Optional[str]: 图片文件路径，不存在则为None
        """
        image_path = os.path.join(self.base_dir, "image", f"{msg_id}.jpg")
        
        return image_path if await aiofiles.os.path.exists(image_path) else None

class MediaManager(metaclass=Singleton):
    """媒体文件管理器，用于管理下载的语音和图片数据"""
    
    def __init__(self, base_dir: str = "resource/media",
                 max_age_days: int = 1,
                 max_storage_mb: int = 500):
        """初始化媒体管理器
        
        Args:
            base_dir: 媒体文件存储的基础目录
            max_age_days: 文件最大保存天数
            max_storage_mb: 最大存储空间（MB）
        """
        self.base_dir = base_dir
        self.max_age_days = max_age_days
        self.max_storage_mb = max_storage_mb
        
        # 确保目录存在
        self.voice_dir = os.path.join(base_dir, "voice")
        self.image_dir = os.path.join(base_dir, "image")
        os.makedirs(self.voice_dir, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
    
    async def save_voice(self, msg_id: str, voice_data: Union[str, bytes]) -> str:
        """保存语音数据
        
        Args:
            msg_id: 消息ID
            voice_data: 语音数据（base64字符串或字节）
            
        Returns:
            str: 保存的文件路径
        """
        date_dir = datetime.now().strftime("%Y%m%d")
        save_dir = os.path.join(self.voice_dir, date_dir)
        os.makedirs(save_dir, exist_ok=True)
        
        file_path = os.path.join(save_dir, f"{msg_id}.wav")
        
        # 如果是base64字符串，先解码
        if isinstance(voice_data, str):
            import base64
            voice_data = base64.b64decode(voice_data)
        
        
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(voice_data)
        
        await self._check_and_clean()
        return file_path
    
    async def save_image(self, msg_id: str, image_data: Union[str, bytes]) -> str:
        """保存图片数据
        
        Args:
            msg_id: 消息ID
            image_data: 图片数据（base64字符串或字节）
            
        Returns:
            str: 保存的文件路径
        """
        date_dir = datetime.now().strftime("%Y%m%d")
        save_dir = os.path.join(self.image_dir, date_dir)
        os.makedirs(save_dir, exist_ok=True)
        
        file_path = os.path.join(save_dir, f"{msg_id}.jpg")
        
        # 如果是base64字符串，先解码
        if isinstance(image_data, str):
            import base64
            image_data = base64.b64decode(image_data)
        
        
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(image_data)
        
        await self._check_and_clean()
        return file_path
    
    def get_voice(self, msg_id: str, date: Optional[str] = None) -> Optional[str]:
        """获取语音文件路径
        
        Args:
            msg_id: 消息ID
            date: 日期字符串（格式：YYYYMMDD），如果为None则搜索所有日期
            
        Returns:
            Optional[str]: 文件路径，如果不存在返回None
        """
        if date:
            path = os.path.join(self.voice_dir, date, f"{msg_id}.wav")
            return path if os.path.exists(path) else None
        
        # 搜索所有日期目录
        for date_dir in os.listdir(self.voice_dir):
            path = os.path.join(self.voice_dir, date_dir, f"{msg_id}.wav")
            if os.path.exists(path):
                return path
        return None
    
    def get_image(self, msg_id: str, date: Optional[str] = None) -> Optional[str]:
        """获取图片文件路径
        
        Args:
            msg_id: 消息ID
            date: 日期字符串（格式：YYYYMMDD），如果为None则搜索所有日期
            
        Returns:
            Optional[str]: 文件路径，如果不存在返回None
        """
        if date:
            path = os.path.join(self.image_dir, date, f"{msg_id}.jpg")
            return path if os.path.exists(path) else None
        
        # 搜索所有日期目录
        for date_dir in os.listdir(self.image_dir):
            path = os.path.join(self.image_dir, date_dir, f"{msg_id}.jpg")
            if os.path.exists(path):
                return path
        return None
    
    async def _check_and_clean(self):
        """检查并清理过期和超量的文件，保留最近3天的文件"""
        # 清理过期文件
        expire_time = time.time() - (self.max_age_days * 24 * 3600)
        
        async def clean_expired(directory):
            # 收集所有文件及其修改时间
            all_files = []
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    mtime = os.path.getmtime(file_path)
                    all_files.append((file_path, mtime))
            
            # 按修改时间排序
            all_files.sort(key=lambda x: x[1], reverse=True)
            
            # 保留最近3天的文件
            recent_time = time.time() - (3 * 24 * 3600)
            recent_files = set(path for path, mtime in all_files if mtime >= recent_time)
            
            # 删除超过max_age_days的文件，但保留最近3天的文件
            for file_path, mtime in all_files:
                if mtime < expire_time and file_path not in recent_files:
                    await aiofiles.os.remove(file_path)
        
        await clean_expired(self.voice_dir)
        await clean_expired(self.image_dir)
        
        # 检查总存储大小
        total_size = 0
        for directory in [self.voice_dir, self.image_dir]:
            for root, _, files in os.walk(directory):
                total_size += sum(os.path.getsize(os.path.join(root, f)) for f in files)
        
        # 如果超过存储限制，删除最旧的文件直到满足限制
        if total_size > self.max_storage_mb * 1024 * 1024:
            all_files = []
            for directory in [self.voice_dir, self.image_dir]:
                for root, _, files in os.walk(directory):
                    all_files.extend(
                        (os.path.join(root, f), os.path.getmtime(os.path.join(root, f)))
                        for f in files
                    )
            
            # 按修改时间排序
            all_files.sort(key=lambda x: x[1])
            
            # 删除旧文件直到满足存储限制
            while total_size > self.max_storage_mb * 1024 * 1024 and all_files:
                file_path, _ = all_files.pop(0)
                total_size -= os.path.getsize(file_path)
                await aiofiles.os.remove(file_path)
    
    def clean_empty_dirs(self):
        """清理空目录"""
        for directory in [self.voice_dir, self.image_dir]:
            for root, dirs, files in os.walk(directory, topdown=False):
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)


from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase

from loguru import logger
from random import randint

import tomllib
import asyncio

from datetime import datetime

class Ping(PluginBase):
    description = "Ping"
    author = "xxx"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/Ping/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)


        config = plugin_config["Ping"]
        self.enable = config["enable"] 

        main_config = main_config["XYBot"]
        # 获取管理员人员
        self.admins = main_config["admins"]

    @schedule('cron', hour='6-23', minute='*/10')
    async def daily_task(self, bot: WechatAPIClient):
        if not self.enable:
            return

        weekend = ["一", "二", "三", "四", "五", "六", "日"]
        message = f"现在是 {datetime.now().strftime('%Y年%m月%d号%H时%M分%S秒')}，星期{weekend[datetime.now().weekday()]}"

        logger.info(f"ping --> {message}")

        for admin in self.admins:
            await bot.send_text_message(admin, message)
            await asyncio.sleep(randint(1, 5))


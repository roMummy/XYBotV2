import asyncio
import tomllib
from datetime import datetime
from random import randint

import aiohttp

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase

from loguru import logger


class GoodMorning(PluginBase):
    description = "早上好插件"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/GoodMorning/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["GoodMorning"]

        self.enable = config["enable"]

    @schedule('cron', hour=7, minute=30)
    async def daily_task(self, bot: WechatAPIClient):
        if not self.enable:
            return

        id_list = []
        wx_seq, chatroom_seq = 0, 0
        while True:
            contact_list = await bot.get_contract_list(wx_seq, chatroom_seq)
            id_list.extend(contact_list["ContactUsernameList"])
            wx_seq = contact_list["CurrentWxcontactSeq"]
            chatroom_seq = contact_list["CurrentChatRoomContactSeq"]
            if contact_list["CountinueFlag"] != 1:
                break

        chatrooms = []
        for id in id_list:
            if id.endswith("@chatroom"):
                chatrooms.append(id)

        async with aiohttp.request("GET", "https://zj.v.api.aa1.cn/api/bk/?num=1&type=json", ssl=False) as req:
            resp = await req.json()
            history_today = "N/A"
            if resp.get("content"):
                history_events = resp.get("content", [])
                history_today = "\n".join([str(event) for event in history_events])

        
        async with aiohttp.request("GET", "https://v.api.aa1.cn/api/api-weather/qq-weather.php?msg=重庆", ssl=False) as req:
            resp = await req.text()
            weather_today = "N/A"
            if resp:
                # 清理脚本内容
                clean_text = resp.split('城市：')
                if len(clean_text) > 1:
                    weather_today = '城市：' + clean_text[1].strip()
                else:
                    weather_today = "获取天气信息失败"

        weekend = ["一", "二", "三", "四", "五", "六", "日"]
        message = ("----- 腾里云 -----\n"
                   f"[Sun]早上好！今天是 {datetime.now().strftime('%Y年%m月%d号')}，星期{weekend[datetime.now().weekday()]}。\n"
                   "\n"
                   "📖历史上的今天：\n"
                   f"{history_today}\n"
                   "\n"
                   "🌈今日天气：\n"
                   f"{weather_today}")

        logger.info(f"message --> {message}")
        for chatroom in chatrooms:
            await bot.send_text_message(chatroom, message)
            await asyncio.sleep(randint(1, 5))

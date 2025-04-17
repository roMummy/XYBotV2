from WechatAPI import WechatAPIClient
from utils.plugin_base import PluginBase
from utils.decorators import *

from loguru import logger

import tomllib
import asyncio

class Revoke(PluginBase):
    description = "撤回消息"
    author = "xxx"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/Revoke/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["Revoke"]
        self.enable = config["enable"] 
        self.command = config["command"]
        # 获取管理员人员
        self.admins = config["admins"]

    
    @on_quote_message
    async def handle_quote(self, bot: WechatAPIClient, message: dict):
        """
        处理引用消息
        """
        if not self.enable:
            return

        cmd = str(message["Content"]).strip()
        
        # 不是有效命令
        if cmd not in self.command:
            return
        
        sender_wxid = message.get("SenderWxid", "")
        # 不是管理员
        if sender_wxid not in self.admins:
            return
        
        # 撤回消息
        wxid = messageget("FromWxid", None)
        client_msg_id = message.get("MsgId", None)
        create_time = message.get("Quote", None).get("Createtime", None)
        new_msg_id = message.get("Quote", None).get("NewMsgId", None)
        await bot.revoke_message(wxid=wxid, client_msg_id=client_msg_id, create_time=create_time, new_msg_id=new_msg_id)


        

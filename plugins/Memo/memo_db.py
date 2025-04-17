from database.XYBotDB import *
from sqlalchemy import Text, delete
from typing import List

import json

from plugins.Memo.memo_message_db import MemoMessageDB
from database.messsagDB import Message
from plugins.Memo.media_manager import PermanentMediaStorage

class Memo(Base):
    """ 
    备忘录表
    message_id       	引用消息id(str)
    wxid 				记录者id(str)
    chatroom_id			群id(str)
    quote_user_id		引用消息用户id(str)
    quote_user_name		引用消息用户名字(str)
    quote_msg_type      引用消息类型(int)
    tag                 标签(str)
    create_time 		创建时间(date)
    """
    __tablename__ = 'memo'

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(40), nullable=False, unique=True, index=True,
                        comment='message_id')
    wxid = Column(String(40), nullable=False, default="", comment='wxid')
    chatroom_id = Column(String(40), nullable=False, default="", comment='chatroom_id')
    quote_user_id = Column(String(40), nullable=False, default="", comment='quote_user_id')
    quote_user_name = Column(String(255), nullable=False, default="", comment='quote_user_name') 
    quote_msg_type = Column(Integer, nullable=False, default=0, comment='quote_msg_type') 
    tag = Column(String(255), nullable=False, default="", comment='tag')  
    create_time = Column(DateTime, nullable=False, default=datetime.datetime.fromtimestamp(0), comment='create_time')       

class BackupMessage(Base):
    """
    消息备份表
    """
    __tablename__ = 'messages_backup'

    id = Column(Integer, primary_key=True, autoincrement=True)
    msg_id = Column(Integer, index=True, comment='消息唯一ID（整型）')
    sender_wxid = Column(String(40), index=True, comment='消息发送人wxid')
    from_wxid = Column(String(40), index=True, comment='消息来源wxid')
    msg_type = Column(Integer, comment='消息类型（整型编码）')
    content = Column(Text, comment='消息内容')
    timestamp = Column(DateTime, default=datetime.datetime.fromtimestamp(0), index=True, comment='消息时间戳')
    is_group = Column(Boolean, default=False, comment='是否群消息')


class MemoDB(XYBotDB):
    def __init__(self):
        super().__init__()
        self.msg_db = MemoMessageDB()
        self.permanent_storage = PermanentMediaStorage()

    # MARK: - 写入
    async def add_memo(self, message_id: str, wxid: str, chatroom_id: str, quote_user_id: str, quote_user_name: str, create_time: datetime.datetime, tag: str, quote_msg_type: int) -> bool:
        """
        添加一条备忘录
        """
        logger.info("add_memo")
        if quote_msg_type == 3:
            image_path = await self.permanent_storage.save_image(message_id)
            if image_path is None:
                logger.error(f"添加备忘录失败，message_id: {message_id}, 保存图片失败")
                return False

        # 先获取原始消息
        msgs = await MemoMessageDB().fetch_messages(message_ids=[int(message_id)])
        
        msg = msgs[0] if len(msgs) > 0 else None
        if msg is None:
            logger.error(f"添加备忘录失败，message_id: {message_id}, 原始消息不存在")
            return False

        # 备份消息
        is_ok = self._backup_message(msg)
        if not is_ok:
            logger.error(f"添加备忘录失败，message_id: {message_id}, 备份消息失败")
            return False

        return self._execute_in_queue(self._add_memo, message_id, wxid, chatroom_id, quote_user_id, quote_user_name, create_time, tag, quote_msg_type)


    def _add_memo(self, message_id: str, wxid: str, chatroom_id: str, quote_user_id: str, quote_user_name: str, create_time: datetime.datetime, tag: str, quote_msg_type: int) -> bool:
        """
        添加一条备忘录
        """
        session = self.DBSession()

        try:
            # 存在就更新
            result = session.execute(
                update(Memo)
                .where(Memo.message_id == message_id)
                .values(
                    wxid = wxid,
                    chatroom_id = chatroom_id,
                    quote_user_id = quote_user_id,
                    quote_user_name = quote_user_name,
                    create_time = create_time,
                    tag = tag,
                    quote_msg_type = quote_msg_type
                )
            )
            # 不存在则添加
            if result.rowcount == 0:
                session.add(
                    Memo(
                        message_id = message_id,
                        wxid = wxid,
                        chatroom_id = chatroom_id,
                        quote_user_id = quote_user_id,
                        quote_user_name = quote_user_name,
                        create_time = create_time,
                        tag = tag,
                        quote_msg_type = quote_msg_type
                    )
                )

            logger.info(f"添加备忘录成功，message_id: {message_id}")
            session.commit()
            return True
        except Exception as e:
            logger.error(f"添加备忘录失败，message_id: {message_id}, error: {e}")
            session.rollback()
            return False
        finally:
            session.close()



     # MARK: - 查询
    def get_memo(self, wxid: str, chatroom_id: str=None, time: datetime.datetime=None, keyword: str=None) -> list:
        """
        获取查询人的所有备忘录
        wxid: 查询人的wxid
        time: 查询时间
        condition: 可以查询包含的内容
        """
        session = self.DBSession()

        try:
            query = session.query(Memo) \
            .filter_by(wxid=wxid) \
            .filter_by(chatroom_id=chatroom_id) 

            if time is not None:
                start_time = time
                end_time = datetime.datetime.combine(time + datetime.timedelta(days=1), datetime.time.min)
                query = query.filter(Memo.create_time >= start_time, Memo.create_time < end_time)

            if keyword is not None:
                query = query.filter(Memo.content.like(f"%{keyword}%"))
                
            memos = query.all()

            logger.info(f"获取备忘录成功，wxid: {wxid}")

            result = [self._memo_format(memo) for memo in memos]
            return result
        except Exception as e:
            logger.error(f"获取备忘录失败，wxid: {wxid}, error: {e}")
            return []
        finally:
            session.close()
    
    # MARK: - 查询所有tag 
    def query_all(self, wxid: str, chatroom_id: str, tag: str=None) -> list:
        """
        获取查询人的所有tag
        wxid: 查询人的wxid
        chatroom_id: 群id或者个人id
        """
        session = self.DBSession()

        try:
            query = session.query(Memo) \
            .filter_by(chatroom_id=chatroom_id) 
                
            if tag is not None:
                query = query.filter_by(tag=tag) 

            memos = query.all()
           
            logger.info(f"获取备忘录成功，wxid: {wxid} chatroom_id:{chatroom_id} tag: {tag} count:{len(memos)}")
            result = [self._memo_format(memo) for memo in memos]
            return result
        except Exception as e:
            logger.error(f"获取备忘录失败，wxid: {wxid}, error: {e}")
            return []
        finally:
            session.close()
    
    def _memo_format(self, memo: Memo) -> dict:
        return {
            'message_id': memo.message_id,
            'wxid': memo.wxid,
            'chatroom_id': memo.chatroom_id,
            'quote_user_id': memo.quote_user_id,
            'quote_user_name': memo.quote_user_name,
            'quote_msg_type': memo.quote_msg_type,
            'tag': memo.tag,
            'create_time': memo.create_time.strftime('%Y-%m-%d %H:%M:%S') if memo.create_time else None
        }

    def query_tag(self, wxid: str, chatroom_id: str, tag: str) -> list:
        """查询所有tag数据 通过引用消息id从消息库里面获取对应的内容"""
        memos = self.query_all(wxid, chatroom_id, tag)

        for memo in memos:
            # 通过message_id从备份消息库里面获取对应的内容
            msg = self._query_back_message([int(memo['message_id'])])
            if len(msg) > 0:
                memo['content'] = msg[0].content
                memo["msg_type"] = msg[0].msg_type
            else:
                memo['content'] = ""
                memo["msg_type"] = ""
        return memos

    # MARK: - 通过消息id查询
    def query_message_ids(self, message_ids: List[str]) -> List[Message]:
        """通过消息id查询"""
        session = self.DBSession()

        try:
            query = session.query(Memo) \
            .filter(Memo.message_id.in_(message_ids))
            memos = query.all()
            logger.info(f"获取备忘录成功，message_ids: {message_ids}")
            result = [self._memo_format(memo) for memo in memos]
                
            return result
        except Exception as e:
            logger.error(f"获取备忘录失败，message_ids: {message_ids}, error: {e}")
            return []
        finally:
            session.close()

    # MARK: - 删除
    async def delete(self, wxid: str, message_ids: List[str]) -> bool:
        """通过消息id删除"""
        # 先查询是否是图片 图片需要删除本地的图片数据
        memos = self.query_message_ids(message_ids)
        for memo in memos:
            if memo.get("quote_msg_type") == 3:
                await self.permanent_storage.delete_image(memo.get("message_id"))

        memo_ok = self._delete_memo(wxid, message_ids)
        logger.info(f"删除备忘录: {memo_ok}")
        msg_ok = self._delete_back_message([int(message_id) for message_id in message_ids])
        logger.info(f"删除备份: {msg_ok}")

        return memo_ok
    
    def _delete_memo(self, wxid: str, message_ids: List[str]) -> bool:
        """通过消息id删除备忘录"""
        session = self.DBSession()

        try:
            result = session.execute(
                delete(Memo)
                .where(Memo.wxid == wxid)
                .where(Memo.message_id.in_(message_ids))
            )
            deleted_count = result.rowcount
            logger.info(f"删除备忘录成功，wxid: {wxid}, 删除数量: {deleted_count}")
            
            session.commit()
            return True
        except Exception as e:
            logger.error(f"获取备忘录失败，wxid: {wxid}, error: {e}")
            return False
        finally:
            session.close()

    # MARK: - 备份表

    def _backup_message(self, message: Message) -> bool:
        """
        备份一条消息
        """
        session = self.DBSession()
        try:
            # 存在就更新
            result = session.execute(
                update(BackupMessage)
                .where(BackupMessage.msg_id == message.msg_id)
                .values(
                    msg_id=message.msg_id,
                    sender_wxid=message.sender_wxid,
                    from_wxid=message.from_wxid,
                    msg_type=message.msg_type,
                    content=message.content,
                    is_group=message.is_group,
                    timestamp=message.timestamp
                )
            )
            # 不存在则添加
            if result.rowcount == 0:
                session.add(
                    BackupMessage(
                        msg_id=message.msg_id,
                        sender_wxid=message.sender_wxid,
                        from_wxid=message.from_wxid,
                        msg_type=message.msg_type,
                        content=message.content,
                        is_group=message.is_group,
                        timestamp=message.timestamp
                    )
                )

            logger.info(f"备份消息成功，message_id: {message.msg_id}")
            session.commit()
            return True
        except Exception as e:
            logger.error(f"添加备忘录失败，message_id: {message.msg_id}, error: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def _query_back_message(self, message_ids: List[int]) -> list:
        """备份里面查询"""
        session = self.DBSession()

        try:
            query = session.query(BackupMessage) \
            .filter(BackupMessage.msg_id.in_(message_ids)) 

            messages = query.all()
           
            logger.info(f"获取备份消息成功， message_ids: {message_ids} count:{len(messages)}")

            return messages
        except Exception as e:
            logger.error(f"获取备份消息失败， message_ids: {message_ids}, error: {e}")
            return []
        finally:
            session.close()

    def _delete_back_message(self, message_ids: List[int]) -> bool:
        """通过消息id删除备份消息数据"""
        session = self.DBSession()
        try:
            result = session.execute(
                delete(BackupMessage)
               .where(BackupMessage.msg_id.in_(message_ids))
            )
            deleted_count = result.rowcount
            logger.info(f"删除备份消息成功， message_ids: {message_ids} count:{deleted_count}")
            session.commit()
            return True
        except Exception as e:
            logger.error(f"删除备份消息失败， message_ids: {message_ids}, error: {e}")
            return False
        finally:
            session.close()
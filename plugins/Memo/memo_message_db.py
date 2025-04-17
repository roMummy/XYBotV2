from database.messsagDB import *


class MemoMessageDB(MessageDB):
    _instance = None 
    
    def __init__(self):
        super().__init__()
        

    async def fetch_messages(self, message_ids: List[int] = None, limit: int = 100) -> List[Message]:
        """异步查询消息记录"""
        async with self._async_session_factory() as session:
            try:

                query = select(Message).order_by(Message.timestamp.desc())

                # 通过消息ID列表查询
                if message_ids:
                    query = query.where(Message.msg_id.in_(message_ids))
                
                # 添加限制条数
                query = query.limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
            except Exception as e:
                logging.error(f"查询消息失败: {str(e)}")
                return []



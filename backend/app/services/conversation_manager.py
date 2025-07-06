#!/usr/bin/env python3
"""
对话管理服务 - 从RAG服务中提取的对话相关功能
"""
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from app.models.rag import (
    ConversationHistory, ChatMessage, ChatRole, RAGMetrics
)


class ConversationManager:
    """对话管理器"""
    
    def __init__(self, max_conversations: int = 1000, expire_hours: int = 24):
        self.conversations: Dict[str, ConversationHistory] = {}
        self.max_conversations = max_conversations
        self.expire_hours = expire_hours
        self.metrics = RAGMetrics()
        
        logger.info(f"对话管理器初始化完成，最大对话数: {max_conversations}")
    
    def create_conversation(self, conversation_id: Optional[str] = None) -> str:
        """创建新对话"""
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = ConversationHistory(
                conversation_id=conversation_id,
                messages=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            logger.info(f"创建新对话: {conversation_id}")
        
        return conversation_id
    
    def add_message(
        self, 
        conversation_id: str, 
        role: ChatRole, 
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """添加消息到对话"""
        if conversation_id not in self.conversations:
            self.create_conversation(conversation_id)
        
        conversation = self.conversations[conversation_id]
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        conversation.messages.append(message)
        conversation.updated_at = datetime.now()
        
        # 限制消息数量
        max_messages = 100  # 每个对话最多保留100条消息
        if len(conversation.messages) > max_messages:
            conversation.messages = conversation.messages[-max_messages:]
        
        logger.debug(f"添加消息到对话 {conversation_id}: {role.value}")
        return True
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationHistory]:
        """获取对话历史"""
        return self.conversations.get(conversation_id)
    
    def get_recent_messages(
        self, 
        conversation_id: str, 
        limit: int = 10
    ) -> List[ChatMessage]:
        """获取最近的消息"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        
        return conversation.messages[-limit:] if conversation.messages else []
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """清除对话历史"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.info(f"清除对话: {conversation_id}")
            return True
        return False
    
    def get_conversation_summary(self, conversation_id: str) -> Dict:
        """获取对话摘要"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return {}
        
        user_messages = [msg for msg in conversation.messages if msg.role == ChatRole.USER]
        assistant_messages = [msg for msg in conversation.messages if msg.role == ChatRole.ASSISTANT]
        
        return {
            'conversation_id': conversation_id,
            'total_messages': len(conversation.messages),
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
            'duration_minutes': (conversation.updated_at - conversation.created_at).total_seconds() / 60
        }
    
    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """列出对话"""
        conversations = []
        for conv_id, conv in list(self.conversations.items())[-limit:]:
            conversations.append(self.get_conversation_summary(conv_id))
        
        return sorted(conversations, key=lambda x: x['updated_at'], reverse=True)
    
    def cleanup_expired_conversations(self) -> int:
        """清理过期的对话"""
        if self.expire_hours <= 0:
            return 0
        
        cutoff_time = datetime.now() - timedelta(hours=self.expire_hours)
        expired_ids = []
        
        for conv_id, conversation in self.conversations.items():
            if conversation.updated_at < cutoff_time:
                expired_ids.append(conv_id)
        
        for conv_id in expired_ids:
            del self.conversations[conv_id]
        
        if expired_ids:
            logger.info(f"清理了 {len(expired_ids)} 个过期对话")
        
        return len(expired_ids)
    
    def cleanup_excess_conversations(self) -> int:
        """清理超出限制的对话"""
        if len(self.conversations) <= self.max_conversations:
            return 0
        
        # 按更新时间排序，删除最旧的对话
        sorted_conversations = sorted(
            self.conversations.items(),
            key=lambda x: x[1].updated_at
        )
        
        excess_count = len(self.conversations) - self.max_conversations
        removed_count = 0
        
        for conv_id, _ in sorted_conversations[:excess_count]:
            del self.conversations[conv_id]
            removed_count += 1
        
        if removed_count > 0:
            logger.info(f"清理了 {removed_count} 个超出限制的对话")
        
        return removed_count
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        if not self.conversations:
            return {
                'total_conversations': 0,
                'total_messages': 0,
                'average_messages_per_conversation': 0,
                'active_conversations_24h': 0
            }
        
        total_messages = sum(len(conv.messages) for conv in self.conversations.values())
        
        # 24小时内活跃的对话
        cutoff_24h = datetime.now() - timedelta(hours=24)
        active_24h = sum(
            1 for conv in self.conversations.values() 
            if conv.updated_at > cutoff_24h
        )
        
        return {
            'total_conversations': len(self.conversations),
            'total_messages': total_messages,
            'average_messages_per_conversation': total_messages / len(self.conversations),
            'active_conversations_24h': active_24h
        }
    
    def update_metrics(self, response_time: float, success: bool):
        """更新性能指标"""
        self.metrics.total_requests += 1
        self.metrics.total_response_time += response_time
        
        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        
        # 更新平均响应时间
        if self.metrics.total_requests > 0:
            self.metrics.average_response_time = (
                self.metrics.total_response_time / self.metrics.total_requests
            )
    
    def get_metrics(self) -> RAGMetrics:
        """获取性能指标"""
        return self.metrics
    
    def reset_metrics(self):
        """重置性能指标"""
        self.metrics = RAGMetrics()
        logger.info("性能指标已重置")

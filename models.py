"""
数据模型定义
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class Role(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """聊天消息"""
    role: Role = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(default=None, description="名称(可选)")


class MemoryItem(BaseModel):
    """记忆条目"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="记忆ID")
    content: str = Field(..., description="记忆内容")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="创建时间"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="更新时间"
    )
    source: Optional[str] = Field(default=None, description="记忆来源")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    def to_list_item(self) -> str:
        """转换为列表项格式"""
        time_str = self.created_at[:10] if self.created_at else "未知"
        return f"- [{time_str}]{self.content}"


class MemoryAction(str, Enum):
    """记忆操作类型"""
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"


class MemoryActionItem(BaseModel):
    """记忆操作项"""
    action: MemoryAction = Field(..., description="操作类型")
    id: Optional[str] = Field(default=None, description="记忆ID(更新/删除时需要)")
    content: Optional[str] = Field(default=None, description="记忆内容(添加/更新时需要)")
    new_content: Optional[str] = Field(default=None, description="新内容(更新时使用)")


class MemoryActionRequest(BaseModel):
    """记忆操作请求"""
    actions: List[MemoryActionItem] = Field(default_factory=list, description="操作列表")


class OpenAIChatRequest(BaseModel):
    """OpenAI聊天请求"""
    model: str = Field(..., description="模型名称")
    messages: List[ChatMessage] = Field(..., description="消息列表")
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    stream: bool = Field(default=False)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    stop: Optional[Union[str, List[str]]] = Field(default=None)


class AnthropicContent(BaseModel):
    """Anthropic消息内容"""
    type: str = Field(default="text")
    text: str = Field(...)


class AnthropicMessage(BaseModel):
    """Anthropic消息"""
    role: Role = Field(...)
    content: Union[str, List[AnthropicContent]] = Field(...)


class AnthropicChatRequest(BaseModel):
    """Anthropic聊天请求"""
    model: str = Field(...)
    messages: List[AnthropicMessage] = Field(...)
    max_tokens: int = Field(default=4096, ge=1)
    temperature: Optional[float] = Field(default=0.7, ge=0, le=1)
    system: Optional[str] = Field(default=None)
    stream: bool = Field(default=False)
    stop_sequences: Optional[List[str]] = Field(default=None)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    top_k: Optional[int] = Field(default=None)


class StreamChoice(BaseModel):
    """流式响应选择"""
    index: int = Field(default=0)
    delta: Dict[str, Any] = Field(default_factory=dict)
    finish_reason: Optional[str] = Field(default=None)


class ChatCompletionChunk(BaseModel):
    """聊天完成流式块"""
    id: str = Field(...)
    object: str = Field(default="chat.completion.chunk")
    created: int = Field(...)
    model: str = Field(...)
    choices: List[StreamChoice] = Field(default_factory=list)


class NonStreamChoice(BaseModel):
    """非流式响应选择"""
    index: int = Field(default=0)
    message: Dict[str, Any] = Field(default_factory=dict)
    finish_reason: Optional[str] = Field(default="stop")


class ChatCompletion(BaseModel):
    """聊天完成响应"""
    id: str = Field(...)
    object: str = Field(default="chat.completion")
    created: int = Field(...)
    model: str = Field(...)
    choices: List[NonStreamChoice] = Field(default_factory=list)
    usage: Dict[str, int] = Field(default_factory=dict)


class AnthropicDelta(BaseModel):
    """Anthropic流式增量"""
    type: str = Field(...)
    text: Optional[str] = Field(default=None)


class AnthropicStreamChunk(BaseModel):
    """Anthropic流式块"""
    type: str = Field(...)
    index: Optional[int] = Field(default=None)
    delta: Optional[AnthropicDelta] = Field(default=None)
    message: Optional[Dict[str, Any]] = Field(default=None)
    content_block: Optional[Dict[str, Any]] = Field(default=None)
    usage: Optional[Dict[str, int]] = Field(default=None)
    stop_reason: Optional[str] = Field(default=None)


class ModelInfo(BaseModel):
    """模型信息"""
    id: str = Field(...)
    object: str = Field(default="model")
    created: int = Field(default=0)
    owned_by: str = Field(default="memory-proxy")


class ModelList(BaseModel):
    """模型列表"""
    object: str = Field(default="list")
    data: List[ModelInfo] = Field(default_factory=list)
"""
OpenAI和Anthropic API格式转换器
"""

import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from models import (
    ChatMessage,
    OpenAIChatRequest,
    AnthropicChatRequest,
    AnthropicMessage,
    ChatCompletion,
    ChatCompletionChunk,
    NonStreamChoice,
    StreamChoice,
    AnthropicStreamChunk,
)


class APIConverter:
    """API格式转换器"""
    
    @staticmethod
    def openai_to_anthropic(request: OpenAIChatRequest) -> AnthropicChatRequest:
        """将OpenAI请求转换为Anthropic请求"""
        # 分离system消息
        system_content = None
        anthropic_messages = []
        
        for msg in request.messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                anthropic_messages.append(AnthropicMessage(
                    role=msg.role,
                    content=msg.content
                ))
        
        # 构建Anthropic请求
        anthropic_request = AnthropicChatRequest(
            model=request.model,
            messages=anthropic_messages,
            max_tokens=request.max_tokens or 4096,
            temperature=request.temperature,
            system=system_content,
            stream=request.stream
        )
        
        if request.stop:
            if isinstance(request.stop, str):
                anthropic_request.stop_sequences = [request.stop]
            else:
                anthropic_request.stop_sequences = request.stop
        
        return anthropic_request
    
    @staticmethod
    def anthropic_to_openai(request: AnthropicChatRequest) -> OpenAIChatRequest:
        """将Anthropic请求转换为OpenAI请求"""
        openai_messages = []
        
        # 先添加system消息
        if request.system:
            openai_messages.append(ChatMessage(
                role="system",
                content=request.system
            ))
        
        # 添加其他消息
        for msg in request.messages:
            content = msg.content
            if isinstance(content, list):
                # 取第一个文本内容
                content = content[0].text if content else ""
            
            openai_messages.append(ChatMessage(
                role=msg.role,
                content=content
            ))
        
        openai_request = OpenAIChatRequest(
            model=request.model,
            messages=openai_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream
        )
        
        if request.stop_sequences:
            openai_request.stop = request.stop_sequences
        
        return openai_request
    
    @staticmethod
    def anthropic_response_to_openai(
        anthropic_response: Dict[str, Any],
        model: str
    ) -> ChatCompletion:
        """将Anthropic响应转换为OpenAI格式"""
        # 提取内容
        content = ""
        if "content" in anthropic_response and anthropic_response["content"]:
            for block in anthropic_response["content"]:
                if block.get("type") == "text":
                    content += block.get("text", "")
        
        # 获取用量信息
        usage = anthropic_response.get("usage", {})
        
        return ChatCompletion(
            id=f"chatcmpl-{uuid.uuid4().hex[:10]}",
            created=int(time.time()),
            model=model,
            choices=[
                NonStreamChoice(
                    message={
                        "role": "assistant",
                        "content": content
                    },
                    finish_reason=anthropic_response.get("stop_reason", "stop")
                )
            ],
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            }
        )
    
    @staticmethod
    async def anthropic_stream_to_openai(
        stream_generator: AsyncGenerator[Dict[str, Any], None],
        model: str
    ) -> AsyncGenerator[str, None]:
        """将Anthropic流式响应转换为OpenAI SSE格式"""
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:10]}"
        created = int(time.time())
        
        async for chunk in stream_generator:
            chunk_type = chunk.get("type")
            
            if chunk_type == "content_block_delta":
                delta = chunk.get("delta", {})
                text = delta.get("text", "")
                
                if text:
                    openai_chunk = ChatCompletionChunk(
                        id=completion_id,
                        created=created,
                        model=model,
                        choices=[
                            StreamChoice(
                                delta={"content": text}
                            )
                        ]
                    )
                    yield f"data: {openai_chunk.model_dump_json()}\n\n"
            
            elif chunk_type == "message_stop":
                # 发送结束标记
                openai_chunk = ChatCompletionChunk(
                    id=completion_id,
                    created=created,
                    model=model,
                    choices=[
                        StreamChoice(
                            delta={},
                            finish_reason="stop"
                        )
                    ]
                )
                yield f"data: {openai_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
    
    @staticmethod
    async def openai_stream_to_anthropic(
        stream_generator: AsyncGenerator[str, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """将OpenAI流式响应转换为Anthropic格式"""
        # 发送开始事件
        yield {
            "type": "message_start",
            "message": {
                "id": f"msg_{uuid.uuid4().hex[:12]}",
                "type": "message",
                "role": "assistant",
                "content": []
            }
        }
        
        # 发送内容块开始
        yield {
            "type": "content_block_start",
            "index": 0,
            "content_block": {
                "type": "text",
                "text": ""
            }
        }
        
        async for line in stream_generator:
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                
                try:
                    import json
                    openai_chunk = json.loads(data)
                    
                    choices = openai_chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        
                        if content:
                            yield {
                                "type": "content_block_delta",
                                "index": 0,
                                "delta": {
                                    "type": "text_delta",
                                    "text": content
                                }
                            }
                    
                    # 检查是否完成
                    finish_reason = choices[0].get("finish_reason")
                    if finish_reason:
                        yield {
                            "type": "content_block_stop",
                            "index": 0
                        }
                        yield {
                            "type": "message_delta",
                            "delta": {
                                "stop_reason": finish_reason,
                                "stop_sequence": None
                            }
                        }
                        yield {"type": "message_stop"}
                
                except Exception:
                    pass
    
    @staticmethod
    def extract_system_message(messages: List[ChatMessage]) -> tuple:
        """
        提取系统消息和对话消息
        
        Returns:
            (system_content, conversation_messages)
        """
        system_content = None
        conversation = []
        
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                conversation.append(msg)
        
        return system_content, conversation

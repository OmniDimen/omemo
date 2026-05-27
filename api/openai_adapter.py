"""
OpenAI API适配器
"""

import json
import time
from typing import Any, AsyncGenerator, Dict, Optional

import httpx

from models import OpenAIChatRequest, ChatCompletion, ChatCompletionChunk, NonStreamChoice


class OpenAIAdapter:
    """OpenAI API适配器"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def chat_completions(
        self,
        request: OpenAIChatRequest
    ) -> ChatCompletion:
        """非流式聊天完成"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = self._build_payload(request)
        
        response = await self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # 尝试打印缓存命中情况
        try:
            if "usage" in result:
                usage_data = result["usage"]
                prompt_tokens = usage_data.get("prompt_tokens", 0)
                if "prompt_tokens_details" in usage_data:
                    cached_tokens = usage_data["prompt_tokens_details"].get("cached_tokens", 0)
                    if cached_tokens > 0:
                        hit_rate = (cached_tokens / prompt_tokens * 100) if prompt_tokens > 0 else 0
                        print(f"\n🎯 [缓存命中] 命中 Token: {cached_tokens} / {prompt_tokens} (命中率: {hit_rate:.1f}%)\n")
        except Exception:
            pass
            
        return ChatCompletion(**result)
    
    async def chat_completions_stream(
        self,
        request: OpenAIChatRequest
    ) -> AsyncGenerator[str, None]:
        """流式聊天完成，返回SSE格式数据"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = self._build_payload(request)
        payload["stream"] = True
        
        async with self.client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.strip():
                    # 尝试解析并打印缓存命中情况
                    if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                        try:
                            data = json.loads(line[6:])
                            if "usage" in data and data["usage"]:
                                usage_data = data["usage"]
                                prompt_tokens = usage_data.get("prompt_tokens", 0)
                                if "prompt_tokens_details" in usage_data:
                                    cached_tokens = usage_data["prompt_tokens_details"].get("cached_tokens", 0)
                                    if cached_tokens > 0:
                                        # 计算命中率
                                        hit_rate = (cached_tokens / prompt_tokens * 100) if prompt_tokens > 0 else 0
                                        print(f"\n🎯 [缓存命中] 命中 Token: {cached_tokens} / {prompt_tokens} (命中率: {hit_rate:.1f}%)\n")
                        except Exception:
                            pass
                    yield line + "\n\n"
    
    async def list_models(self) -> Dict[str, Any]:
        """获取模型列表"""
        url = f"{self.base_url}/models"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def _build_payload(self, request: OpenAIChatRequest) -> Dict[str, Any]:
        """构建请求体"""
        messages = []
        for msg in request.messages:
            # 如果是内容为空（比如被丢弃的图片），填充一个占位符防止上游API报错挂起
            safe_content = msg.content if msg.content is not None else "[收到不支持解析的图片或空消息]"
            msg_dict = {"role": msg.role, "content": safe_content}
            if hasattr(msg, 'tool_call_id') and msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            if hasattr(msg, 'name') and msg.name:
                msg_dict["name"] = msg.name
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                msg_dict["reasoning_content"] = msg.reasoning_content
            messages.append(msg_dict)
        
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": request.stream
        }
        
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty
        
        if request.stop is not None:
            payload["stop"] = request.stop
        
        # MCP/Tools 支持
        if request.tools is not None:
            payload["tools"] = request.tools
        
        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice
        
        return payload
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

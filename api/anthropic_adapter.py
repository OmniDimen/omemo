"""
Anthropic API适配器
"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from models import AnthropicChatRequest, AnthropicMessage


class AnthropicAdapter:
    """Anthropic API适配器"""
    
    def __init__(self, base_url: str, api_key: str):
        # Anthropic API默认地址
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def chat_completions(
        self,
        request: AnthropicChatRequest
    ) -> Dict[str, Any]:
        """非流式聊天完成"""
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = self._build_payload(request)
        
        response = await self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        return response.json()
    
    async def chat_completions_stream(
        self,
        request: AnthropicChatRequest
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式聊天完成"""
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = self._build_payload(request)
        payload["stream"] = True
        
        async with self.client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.strip():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            yield event
                        except json.JSONDecodeError:
                            pass
    
    def _build_payload(self, request: AnthropicChatRequest) -> Dict[str, Any]:
        """构建请求体"""
        # 转换消息格式
        messages = []
        for msg in request.messages:
            content = msg.content
            if isinstance(content, list):
                content = [{"type": "text", "text": c.text} for c in content]
            else:
                content = [{"type": "text", "text": content}]
            
            messages.append({
                "role": msg.role,
                "content": content
            })
        
        payload = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens
        }
        
        if request.system:
            payload["system"] = request.system
        
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        
        if request.top_k is not None:
            payload["top_k"] = request.top_k
        
        if request.stop_sequences:
            payload["stop_sequences"] = request.stop_sequences
        
        return payload
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
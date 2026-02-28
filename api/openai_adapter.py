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
        payload = {
            "model": request.model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ],
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
        
        return payload
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

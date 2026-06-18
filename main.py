"""
Omni Memory - 带记忆功能的API中转站
主应用文件
"""

import json
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import config, EndpointConfig, MemorySettings, debug_print, setup_logging
from config import generate_session_key, verify_session_key, set_session_key, clear_session_key
from models import (
    ChatMessage,
    OpenAIChatRequest,
    AnthropicChatRequest,
    MemoryItem,
    ChatCompletion,
    ModelList,
    ModelInfo,
)
from memory import MemoryStorage, MemoryManager, MemorySummarizer
from memory.manager import MemoryAction
from api import OpenAIAdapter, AnthropicAdapter, APIConverter


# 配置日志（应用启动前尽早调用）
setup_logging(debug=True)
logger = logging.getLogger("omemo.main")

# 全局状态
storage: MemoryStorage
manager: MemoryManager
summarizer: Optional[MemorySummarizer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global storage, manager, summarizer
    
    # 启动时初始化
    storage = MemoryStorage(config.settings.data_dir)
    manager = MemoryManager(storage, config.memory_settings)
    
    # 如果配置了外接模型，初始化总结器并注入到 manager
    ms = config.memory_settings
    if ms.external_model_endpoint and ms.external_model_api_key and ms.external_model_name:
        summarizer = MemorySummarizer(
            api_endpoint=ms.external_model_endpoint,
            api_key=ms.external_model_api_key,
            model=ms.external_model_name
        )
        manager.summarizer = summarizer
    
    logger.info("🚀 Omni Memory 启动成功")
    logger.info("📁 数据目录: %s", config.settings.data_dir)
    logger.info("🧠 记忆模式: %s", ms.memory_mode)
    logger.info("💉 注入模式: %s", ms.injection_mode)
    
    yield
    
    # 关闭时清理
    logger.info("🛑 Omni Memory 关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title="Omni Memory",
    description="带记忆功能的OpenAI/Anthropic API中转站",
    version="1.1.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Setup守卫：未配置端点时重定向到初始配置页
@app.middleware("http")
async def setup_guard(request: Request, call_next):
    path = request.url.path
    if path.startswith(("/static", "/setup", "/api/setup", "/api/models/fetch", "/favicon", "/health")):
        return await call_next(request)
    if not config.endpoints:
        from starlette.responses import RedirectResponse
        return RedirectResponse("/setup")
    return await call_next(request)


# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ==================== 辅助函数 ====================

async def require_auth(request: Request):
    if not config.memory_settings.login_enabled:
        return
    auth_header = request.headers.get("Authorization", "")
    session_key = None
    if auth_header.startswith("Bearer "):
        session_key = auth_header[7:]
    if not session_key or not verify_session_key(session_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未授权访问，请提供有效的Session Key"
        )


def get_adapter_for_model(model: str):
    """根据模型名称获取适配器（支持别名，检测冲突）"""
    conflicts = config.get_model_conflicts()
    if model in conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"模型 '{model}' 存在冲突，请在「模型列表」中设置别名。冲突端点: {', '.join(conflicts[model])}"
        )

    endpoint = config.get_endpoint_by_model(model)

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到模型 '{model}' 的配置"
        )

    actual_model = config.get_actual_model_name(model)

    if endpoint.provider == "openai":
        return OpenAIAdapter(endpoint.url, endpoint.api_key), endpoint, "openai", actual_model
    elif endpoint.provider == "anthropic":
        return AnthropicAdapter(endpoint.url, endpoint.api_key), endpoint, "anthropic", actual_model
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的提供商: {endpoint.provider}"
        )


# ==================== WebUI路由 ====================

@app.get("/", response_class=HTMLResponse)
async def webui(request: Request):
    """WebUI首页"""
    return templates.TemplateResponse(request, "index.html")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse(request, "login.html")



# ==================== 首次配置 ====================

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """首次配置页面"""
    if config.endpoints:
        from starlette.responses import RedirectResponse
        return RedirectResponse("/")
    return templates.TemplateResponse(request, "setup.html")


@app.post("/api/setup")
async def do_setup(data: dict):
    """首次配置 - 创建第一个端点"""
    if config.endpoints:
        raise HTTPException(status_code=400, detail="已完成初始配置，请在管理页面中添加更多端点")

    name = data.get("name", "").strip()
    provider = data.get("provider", "openai")
    url = data.get("url", "").strip()
    api_key = data.get("api_key", "").strip()
    models_raw = data.get("models", [])

    if not name or not url or not api_key:
        raise HTTPException(status_code=400, detail="名称、URL和API密钥为必填项")

    if isinstance(models_raw, str):
        models = [m.strip() for m in models_raw.split(",") if m.strip()]
    else:
        models = models_raw

    if not models:
        raise HTTPException(status_code=400, detail="至少需要一个模型")

    endpoint = EndpointConfig(
        name=name,
        provider=provider,
        url=url,
        api_key=api_key,
        models=models,
        enabled=True
    )

    if not config.add_endpoint(endpoint):
        raise HTTPException(status_code=400, detail="添加端点失败")

    config.save_memory_settings()
    return {"success": True}


# ==================== 管理API ====================

@app.get("/api/config/endpoints")
async def get_endpoints(_: None = Depends(require_auth)):
    """获取所有端点配置"""
    endpoints = []
    for ep in config.endpoints:
        data = ep.model_dump()
        key = data.get("api_key", "")
        data["api_key"] = f"***{key[-4:]}" if len(key) > 4 else "***"
        endpoints.append(data)
    return endpoints


@app.post("/api/config/endpoints")
async def add_endpoint(endpoint: EndpointConfig, _: None = Depends(require_auth)):
    """添加端点配置"""
    if not config.add_endpoint(endpoint):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="端点名称已存在"
        )
    return {"success": True}


@app.put("/api/config/endpoints/{name}")
async def update_endpoint(name: str, endpoint: EndpointConfig, _: None = Depends(require_auth)):
    """更新端点配置"""
    if not config.update_endpoint(name, endpoint):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="端点不存在"
        )
    return {"success": True}


@app.delete("/api/config/endpoints/{name}")
async def delete_endpoint(name: str, _: None = Depends(require_auth)):
    """删除端点配置"""
    if not config.delete_endpoint(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="端点不存在"
        )
    return {"success": True}


# ==================== 模型管理API ====================

@app.get("/api/models")
async def get_models(_: None = Depends(require_auth)):
    """获取所有模型列表（包含冲突信息）"""
    return config.get_all_models()


@app.get("/api/models/conflicts")
async def get_model_conflicts(_: None = Depends(require_auth)):
    """获取模型冲突列表"""
    return config.get_model_conflicts()


@app.post("/api/models/alias")
async def set_model_alias(data: Dict[str, str], _: None = Depends(require_auth)):
    """设置模型别名"""
    endpoint_name = data.get("endpoint_name")
    model = data.get("model")
    alias = data.get("alias", "")
    
    if not endpoint_name or not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少必要参数"
        )
    
    if not config.set_model_alias(endpoint_name, model, alias):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="端点或模型不存在"
        )
    
    return {"success": True}


@app.get("/api/config/memory")
async def get_memory_settings(_: None = Depends(require_auth)):
    """获取记忆设置"""
    data = config.memory_settings.model_dump()
    data.pop("session_key_hash", None)
    return data


@app.post("/api/config/memory")
async def update_memory_settings(settings: MemorySettings, _: None = Depends(require_auth)):
    """更新记忆设置"""
    global summarizer

    settings.session_key_hash = config.memory_settings.session_key_hash
    settings.login_enabled = config.memory_settings.login_enabled

    if config.update_memory_settings(settings):
        # 更新内存中的设置
        manager.settings = settings
        
        # 重新初始化总结器
        if settings.external_model_endpoint and settings.external_model_api_key and settings.external_model_name:
            summarizer = MemorySummarizer(
                api_endpoint=settings.external_model_endpoint,
                api_key=settings.external_model_api_key,
                model=settings.external_model_name
            )
        else:
            summarizer = None
        
        return {"success": True}
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="保存设置失败"
    )


# ==================== 记忆管理API ====================

@app.get("/api/memories")
async def get_memories(keyword: Optional[str] = None, _: None = Depends(require_auth)):
    """获取所有记忆或搜索记忆"""
    if keyword:
        memories = manager.search_memories(keyword)
    else:
        memories = manager.get_all_memories()
    
    return [m.model_dump() for m in memories]


@app.post("/api/memories")
async def add_memory(data: Dict[str, str], _: None = Depends(require_auth)):
    """添加记忆"""
    content = data.get("content", "").strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="记忆内容不能为空"
        )
    
    memory = manager.add_memory(content, source="manual")
    return memory.model_dump()


@app.put("/api/memories/{memory_id}")
async def update_memory(memory_id: str, data: Dict[str, str], _: None = Depends(require_auth)):
    """更新记忆"""
    content = data.get("content", "").strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="记忆内容不能为空"
        )
    
    memory = manager.update_memory(memory_id, content)
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="记忆不存在"
        )
    
    return memory.model_dump()


@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str, _: None = Depends(require_auth)):
    """删除记忆"""
    if not manager.delete_memory(memory_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="记忆不存在"
        )
    return {"success": True}


@app.post("/api/models/fetch")
async def fetch_models_from_endpoint(data: Dict[str, str], _: None = Depends(require_auth)):
    """从指定端点获取可用模型列表"""
    url = data.get("url", "").strip().rstrip("/")
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "openai")
    
    if not url or not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL和API密钥不能为空"
        )
    
    try:
        if provider == "openai":
            adapter = OpenAIAdapter(url, api_key)
            result = await adapter.list_models()
            models = [m.get("id") for m in result.get("data", []) if m.get("id")]
            await adapter.close()
            return {"models": models, "provider": "openai"}
        elif provider == "anthropic":
            # Anthropic没有models端点，返回预定义列表
            predefined_models = [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-2.1",
                "claude-2.0",
                "claude-instant-1.2"
            ]
            return {"models": predefined_models, "provider": "anthropic"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的提供商: {provider}"
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取模型列表失败: HTTP {e.response.status_code}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取模型列表失败: {str(e)}"
        )


@app.get("/api/memories/stats")
async def get_memory_stats(_: None = Depends(require_auth)):
    """获取记忆统计"""
    memories = manager.get_all_memories()
    return {
        "total": len(memories),
        "recent": len([m for m in memories if m.created_at and m.created_at.startswith(time.strftime("%Y-%m"))])
    }


# ==================== 登录认证API ====================

@app.get("/api/auth/status")
async def get_auth_status():
    """获取登录认证状态"""
    return {
        "login_enabled": config.memory_settings.login_enabled,
        "has_session_key": config.memory_settings.session_key_hash is not None
    }


@app.post("/api/auth/login")
async def login(data: Dict[str, str]):
    """登录验证"""
    session_key = data.get("session_key", "").strip()
    
    if not config.memory_settings.login_enabled:
        return {"success": True, "message": "登录功能未启用"}
    
    if not session_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session key不能为空"
        )
    
    if verify_session_key(session_key):
        return {"success": True, "message": "登录成功"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session key无效"
        )


@app.post("/api/auth/enable")
async def enable_login(request: Request):
    """启用登录功能（生成新的session key）"""
    if config.memory_settings.login_enabled:
        auth_header = request.headers.get("Authorization", "")
        session_key = None
        if auth_header.startswith("Bearer "):
            session_key = auth_header[7:]
        if not session_key or not verify_session_key(session_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未授权访问，请提供有效的Session Key"
            )
    new_key = generate_session_key()
    set_session_key(new_key)
    config.memory_settings.login_enabled = True
    config.save_memory_settings()
    return {
        "success": True,
        "session_key": new_key,
        "message": "请妥善保存此Key，关闭后将无法再次查看"
    }


@app.post("/api/auth/disable")
async def disable_login(_: None = Depends(require_auth)):
    """禁用登录功能（销毁session key）"""
    config.memory_settings.login_enabled = False
    clear_session_key()
    config.save_memory_settings()
    return {"success": True, "message": "登录功能已禁用，Session Key已销毁"}


@app.post("/api/auth/reset-key")
async def reset_session_key(_: None = Depends(require_auth)):
    """重置session key"""
    # 生成新的key
    new_key = generate_session_key()
    set_session_key(new_key)
    
    return {
        "success": True,
        "session_key": new_key,
        "message": "请妥善保存此Key，关闭后将无法再次查看"
    }


@app.post("/api/debug/preview-system-prompt")
async def preview_system_prompt(data: dict, _: None = Depends(require_auth)):
    """预览系统提示词（调试用）"""
    original_system = data.get("system", "")
    mode = data.get("mode", config.memory_settings.memory_mode)
    
    memories = manager.get_all_memories()
    
    if mode == "builtin":
        prompt = manager.build_builtin_system_prompt(original_system, memories)
    else:
        prompt = manager.build_system_prompt_with_memories(original_system, memories, "full")
    
    return {
        "system_prompt": prompt,
        "memory_count": len(memories),
        "mode": mode
    }


# ==================== OpenAI兼容API ====================

@app.get("/v1/models")
async def list_models():
    """获取模型列表"""
    models = []
    seen_names = set()
    
    for ep in config.get_enabled_endpoints():
        for model in ep.models:
            # 查找该模型是否有别名
            alias = None
            for alias_name, actual_name in ep.model_aliases.items():
                if actual_name == model:
                    alias = alias_name
                    break
            
            # 可用名称：优先别名，没有别名就用原名
            available_name = alias if alias else model
            
            if available_name not in seen_names:
                seen_names.add(available_name)
                models.append(ModelInfo(
                    id=available_name,
                    owned_by=ep.provider
                ))
    
    return ModelList(data=models)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, _: None = Depends(require_auth)):
    """聊天完成接口 - 支持OpenAI格式"""
    try:
        body = await request.json()
        openai_request = OpenAIChatRequest(**body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请求解析失败: {str(e)}"
        )
    
    # 获取适配器
    adapter, endpoint, provider, actual_model = get_adapter_for_model(openai_request.model)
    
    # 准备消息（注入记忆）
    messages = openai_request.messages
    original_system = None
    
    # 根据注入模式处理记忆
    if config.memory_settings.injection_mode == "rag" and config.memory_settings.memory_mode != "builtin":
        # RAG模式：筛选相关记忆
        selected_memories = await manager.select_memories_for_rag(messages)
        messages = manager.prepare_messages_with_memories(messages, "rag", selected_memories)
    else:
        # 全量模式或内置模式
        all_memories = manager.get_all_memories()
        if config.memory_settings.memory_mode == "builtin":
            messages = manager.prepare_messages_with_memories(messages, "builtin", all_memories)
        else:
            messages = manager.prepare_messages_with_memories(messages, "full", all_memories)
    
    # 调试：打印系统提示词
    for msg in messages:
        if msg.role == "system":
            sys_content = msg.get_text_content()
            debug_print(f"\n{'='*50}")
            debug_print(f"[System Prompt 预览] 长度: {len(sys_content)}")
            debug_print(f"{'='*50}")
            debug_print(sys_content[:8000] + "..." if len(sys_content) > 8000 else sys_content)
            debug_print(f"{'='*50}\n")
            break
    
    # 使用实际模型名称
    openai_request.model = actual_model
    openai_request.messages = messages
    
    try:
        if provider == "anthropic":
            # 转换为Anthropic格式
            anthropic_request = APIConverter.openai_to_anthropic(openai_request)
            
            if openai_request.stream:
                # 流式响应
                async def anthropic_stream_generator():
                    full_response = ""
                    memory_processed = False
                    memory_tag_started = False  # 标记是否开始<memory>标签
                    chunk_count = 0
                    
                    async for chunk in adapter.chat_completions_stream(anthropic_request):
                        chunk_count += 1
                        if chunk_count <= 3:
                            debug_print(f"[流式响应] Anthropic chunk {chunk_count}: {repr(str(chunk)[:100])}")
                        
                        # 转换为OpenAI SSE格式
                        if chunk.get("type") == "content_block_delta":
                            delta = chunk.get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                # 检查是否开始<memory>标签
                                if '<memory>' in text and not memory_tag_started:
                                    memory_tag_started = True
                                    debug_print(f"[流式响应] 检测到<memory>开始，后续内容不再输出")
                                
                                full_response += text
                                
                                if chunk_count <= 5 and not memory_tag_started:
                                    debug_print(f"[流式响应] Anthropic: {repr(text[:80])}")
                                
                                # 检查是否包含</memory>结束标签
                                if not memory_processed and '</memory>' in text:
                                    debug_print(f"[流式响应] 检测到</memory>结束，开始提取记忆")
                                    await manager.process_builtin_memory_extraction(full_response)
                                    memory_processed = True
                                
                                # 只在未开始memory标签时输出
                                if not memory_tag_started:
                                    openai_chunk = {
                                        "id": f"chatcmpl-{uuid.uuid4().hex[:10]}",
                                        "object": "chat.completion.chunk",
                                        "created": int(time.time()),
                                        "model": openai_request.model,
                                        "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]
                                    }
                                    yield f"data: {json.dumps(openai_chunk, ensure_ascii=False)}\n\n"
                        
                        elif chunk.get("type") == "message_stop":
                            debug_print(f"[流式响应] Anthropic 收到 message_stop, 总长度: {len(full_response)}")
                            # 处理内置模式的记忆提取（如果还没处理）
                            if config.memory_settings.memory_mode == "builtin" and not memory_processed:
                                await manager.process_builtin_memory_extraction(full_response)
                            
                            yield f"data: {json.dumps({'choices': [{'finish_reason': 'stop'}]}, ensure_ascii=False)}\n\n"
                            yield "data: [DONE]\n\n"
                    
                    debug_print(f"[流式响应] Anthropic 总共 {chunk_count} 个chunks")
                    
                    # 外接模型模式：检查是否需要总结
                    if config.memory_settings.memory_mode == "external":
                        manager.conversation_counter += 1
                        if manager.conversation_counter >= config.memory_settings.summary_interval:
                            await manager.external_summarize_memory(openai_request.messages)
                            manager.conversation_counter = 0
                
                return StreamingResponse(
                    anthropic_stream_generator(),
                    media_type="text/event-stream"
                )
            else:
                # 非流式响应
                response = await adapter.chat_completions(anthropic_request)
                openai_response = APIConverter.anthropic_response_to_openai(
                    response,
                    openai_request.model
                )
                
                # 处理内置模式的记忆提取
                if config.memory_settings.memory_mode == "builtin":
                    response_text = ""
                    for block in response.get("content", []):
                        if block.get("type") == "text":
                            response_text += block.get("text", "")
                    
                    cleaned_text = await manager.process_builtin_memory_extraction(response_text)
                    # 更新响应内容
                    if openai_response.choices:
                        openai_response.choices[0].message["content"] = cleaned_text
                
                # 外接模型模式：检查是否需要总结
                if config.memory_settings.memory_mode == "external":
                    manager.conversation_counter += 1
                    if manager.conversation_counter >= config.memory_settings.summary_interval:
                        await manager.external_summarize_memory(openai_request.messages)
                        manager.conversation_counter = 0
                
                return JSONResponse(content=openai_response.model_dump())
        
        else:
            # OpenAI提供商
            if openai_request.stream:
                async def openai_stream_generator():
                    # 分别追踪思维链和用户输出
                    full_reasoning = ""  # 完整的思维链内容
                    full_content = ""    # 完整的用户输出内容
                    memory_processed = False
                    
                    # === 标签检测状态机 ===
                    # 用于检测跨 token 的标签
                    tag_buffer = ""      # 标签缓冲区
                    in_memory = False    # 是否在 <memory> 标签内
                    
                    # 需要识别的标签
                    MEMORY_OPEN = "<memory>"
                    MEMORY_CLOSE = "</memory>"
                    # 允许正常输出的标签（部分列表）
                    SAFE_TAG_STARTS = ["<think", "</think", "<details", "</details", "<｜", "<|", "<code", "</code", "<pre", "</pre"]
                    
                    chunk_count = 0
                    
                    def process_content_char(char: str) -> str:
                        """处理单个字符，返回应该输出的内容"""
                        nonlocal tag_buffer, in_memory, full_content
                        
                        if in_memory:
                            # 在 memory 标签内，收集但不输出
                            full_content += char
                            tag_buffer += char
                            # 检测 </memory> 结束标签
                            if tag_buffer.endswith(MEMORY_CLOSE):
                                debug_print(f"[流式响应] 检测到</memory>结束")
                                in_memory = False
                                # 获取 </memory> 之后的内容
                                close_pos = tag_buffer.rfind(MEMORY_CLOSE)
                                after_close = tag_buffer[close_pos + len(MEMORY_CLOSE):]
                                tag_buffer = ""
                                # 如果 </memory> 后面还有内容，需要继续处理
                                if after_close:
                                    # 递归处理后续内容
                                    result = ""
                                    for c in after_close:
                                        result += process_content_char(c)
                                    return result
                            # 限制缓冲区长度（但保留足够长度以检测 </memory>）
                            if len(tag_buffer) > 100:
                                tag_buffer = tag_buffer[-50:]
                            return ""
                        else:
                            # 不在 memory 标签内
                            if char == '<':
                                # 可能是标签开始，开始缓存
                                tag_buffer = '<'
                                full_content += char
                                return ""  # 暂不输出，等待判断
                            elif tag_buffer:
                                # 正在缓存可能的标签
                                tag_buffer += char
                                full_content += char
                                
                                # 检查是否形成 <memory> 标签
                                if tag_buffer == MEMORY_OPEN:
                                    debug_print(f"[流式响应] 检测到<memory>开始")
                                    in_memory = True
                                    tag_buffer = ""
                                    return ""
                                
                                # 检查是否是其他已知安全标签
                                is_safe_tag = any(
                                    tag_buffer.startswith(safe) or safe.startswith(tag_buffer)
                                    for safe in SAFE_TAG_STARTS
                                )
                                
                                # 检查是否可以确定不是 memory 标签
                                if len(tag_buffer) > len(MEMORY_OPEN):
                                    # 已经超过 memory 标签长度，肯定不是
                                    output = tag_buffer
                                    tag_buffer = ""
                                    return output
                                
                                # 如果以 'm' 开头，可能是 memory
                                if tag_buffer == "<m":
                                    # 继续等待
                                    return ""
                                if tag_buffer == "<me" or tag_buffer == "<mem" or tag_buffer == "<memo" or tag_buffer == "<memor":
                                    # 继续等待
                                    return ""
                                
                                # 如果确定不是 memory 标签（如 <t, <d 等），输出缓冲区
                                if not tag_buffer.startswith("<m"):
                                    # 检查是否可能是其他安全标签
                                    possible_safe = any(
                                        safe.startswith(tag_buffer)
                                        for safe in SAFE_TAG_STARTS
                                    )
                                    if not possible_safe and len(tag_buffer) >= 2:
                                        # 不是任何已知标签，输出缓冲区
                                        output = tag_buffer
                                        tag_buffer = ""
                                        return output
                                    elif not possible_safe:
                                        # 不确定，继续等待
                                        return ""
                                
                                return ""  # 继续等待
                            else:
                                # 正常字符，直接输出
                                full_content += char
                                return char
                    
                    def process_content(text: str) -> str:
                        """处理文本内容，返回应该输出的部分"""
                        output = ""
                        for char in text:
                            output += process_content_char(char)
                        return output
                    
                    async for line in adapter.chat_completions_stream(openai_request):
                        chunk_count += 1
                        original_line = line
                        line = line.strip()
                        if not line:
                            continue
                            
                        if chunk_count <= 5:
                            debug_print(f"[流式响应] 收到数据块 {chunk_count}: {repr(line[:150])}")
                        
                        if line.startswith("data:"):
                            if "[DONE]" in line:
                                # 输出剩余缓冲区
                                if tag_buffer and not in_memory:
                                    yield f"data: {json.dumps({'choices': [{'delta': {'content': tag_buffer}}]}, ensure_ascii=False)}\n\n"
                                yield original_line + "\n\n"
                                continue
                                
                            try:
                                json_str = line[5:].strip()
                                data = json.loads(json_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    reasoning_content = delta.get("reasoning_content", "")
                                    
                                    # 思维链直接输出，不处理
                                    if reasoning_content:
                                        full_reasoning += reasoning_content
                                    
                                    # 处理 content
                                    if content:
                                        output_content = process_content(content)
                                        
                                        if output_content != content:
                                            data["choices"][0]["delta"]["content"] = output_content
                                            line = f"data:{json.dumps(data)}"
                                            
                            except Exception as e:
                                if chunk_count <= 3:
                                    debug_print(f"[流式响应] 解析错误: {e}, line: {repr(line[:80])}")
                        
                        yield line + "\n\n"
                    
                    debug_print(f"[流式响应] 总共收到 {chunk_count} 个数据块")
                    debug_print(f"[流式响应] 思维链长度: {len(full_reasoning)}, 内容输出长度: {len(full_content)}")
                    if full_content:
                        debug_print(f"[流式响应] 内容输出: {repr(full_content[-200:])}")
                    
                    # 处理记忆提取
                    if config.memory_settings.memory_mode == "builtin" and not memory_processed:
                        await manager.process_builtin_memory_extraction(full_content)
                    
                    # 发送结束标记
                    if in_memory or tag_buffer:
                        yield f"data: {json.dumps({'choices': [{'finish_reason': 'stop'}]}, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    
                    # 外接模型模式
                    if config.memory_settings.memory_mode == "external":
                        manager.conversation_counter += 1
                        if manager.conversation_counter >= config.memory_settings.summary_interval:
                            await manager.external_summarize_memory(openai_request.messages)
                            manager.conversation_counter = 0
                
                return StreamingResponse(
                    openai_stream_generator(),
                    media_type="text/event-stream"
                )
            else:
                response = await adapter.chat_completions(openai_request)
                
                # 处理内置模式的记忆提取
                if config.memory_settings.memory_mode == "builtin":
                    response_text = response.choices[0].message.get("content", "") if response.choices else ""
                    cleaned_text = await manager.process_builtin_memory_extraction(response_text)
                    if response.choices:
                        response.choices[0].message["content"] = cleaned_text
                
                # 外接模型模式：检查是否需要总结
                if config.memory_settings.memory_mode == "external":
                    manager.conversation_counter += 1
                    if manager.conversation_counter >= config.memory_settings.summary_interval:
                        await manager.external_summarize_memory(openai_request.messages)
                        manager.conversation_counter = 0
                
                return JSONResponse(content=response.model_dump())
    
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"上游API错误: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {str(e)}"
        )


# ==================== Anthropic兼容API ====================

@app.post("/v1/messages")
async def anthropic_messages(request: Request, _: None = Depends(require_auth)):
    """Anthropic格式的聊天完成接口"""
    try:
        body = await request.json()
        anthropic_request = AnthropicChatRequest(**body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请求解析失败: {str(e)}"
        )
    
    # 转换为OpenAI格式以便处理
    openai_request = APIConverter.anthropic_to_openai(anthropic_request)
    
    # 获取适配器
    adapter, endpoint, provider, actual_model = get_adapter_for_model(openai_request.model)
    
    # 准备消息（注入记忆）
    messages = openai_request.messages
    
    if config.memory_settings.injection_mode == "rag" and config.memory_settings.memory_mode != "builtin":
        selected_memories = await manager.select_memories_for_rag(messages)
        messages = manager.prepare_messages_with_memories(messages, "rag", selected_memories)
    else:
        all_memories = manager.get_all_memories()
        if config.memory_settings.memory_mode == "builtin":
            messages = manager.prepare_messages_with_memories(messages, "builtin", all_memories)
        else:
            messages = manager.prepare_messages_with_memories(messages, "full", all_memories)
    
    # 使用实际模型名称
    openai_request.model = actual_model
    openai_request.messages = messages
    
    try:
        if provider == "openai":
            # 需要将OpenAI响应转换为Anthropic格式
            if openai_request.stream:
                # 流式转换较复杂，这里简化处理
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Anthropic格式的流式请求暂不支持OpenAI提供商"
                )
            
            response = await adapter.chat_completions(openai_request)
            
            # 转换为Anthropic格式
            content_text = response.choices[0].message.get("content", "") if response.choices else ""
            
            anthropic_response = {
                "id": f"msg_{uuid.uuid4().hex[:12]}",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": content_text}],
                "model": anthropic_request.model,
                "stop_reason": "end_turn",
                "usage": {
                    "input_tokens": response.usage.get("prompt_tokens", 0),
                    "output_tokens": response.usage.get("completion_tokens", 0)
                }
            }
            
            return JSONResponse(content=anthropic_response)
        else:
            # Anthropic提供商，直接转发
            if anthropic_request.stream:
                async def anthropic_raw_stream():
                    full_response = ""
                    
                    async for chunk in adapter.chat_completions_stream(anthropic_request):
                        yield f"data: {json.dumps(chunk)}\n\n"
                        
                        # 收集响应
                        if chunk.get("type") == "content_block_delta":
                            delta = chunk.get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                full_response += text
                    
                    # 处理记忆提取
                    if config.memory_settings.memory_mode == "builtin":
                        await manager.process_builtin_memory_extraction(full_response)
                    
                    # 外接模型模式
                    if config.memory_settings.memory_mode == "external":
                        manager.conversation_counter += 1
                        if manager.conversation_counter >= config.memory_settings.summary_interval:
                            await manager.external_summarize_memory(openai_request.messages)
                            manager.conversation_counter = 0
                
                return StreamingResponse(
                    anthropic_raw_stream(),
                    media_type="text/event-stream"
                )
            else:
                response = await adapter.chat_completions(anthropic_request)
                
                # 处理内置模式的记忆提取
                if config.memory_settings.memory_mode == "builtin":
                    response_text = ""
                    for block in response.get("content", []):
                        if block.get("type") == "text":
                            response_text += block.get("text", "")
                    
                    cleaned_text = await manager.process_builtin_memory_extraction(response_text)
                    # 更新响应内容
                    for block in response.get("content", []):
                        if block.get("type") == "text":
                            block["text"] = cleaned_text
                            break
                
                # 外接模型模式
                if config.memory_settings.memory_mode == "external":
                    manager.conversation_counter += 1
                    if manager.conversation_counter >= config.memory_settings.summary_interval:
                        await manager.external_summarize_memory(openai_request.messages)
                        manager.conversation_counter = 0
                
                return JSONResponse(content=response)
    
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"上游API错误: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config.settings.host,
        port=config.settings.port,
        reload=config.settings.debug
    )
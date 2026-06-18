"""
配置管理模块
支持从环境变量和配置文件加载配置
"""

import json
import logging
import os
import secrets
import hashlib
import hmac
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# ==================== 日志配置 ====================

def setup_logging(debug: bool = False) -> None:
    """配置全局日志系统"""
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    # 降低 httpx 的日志级别，避免刷屏
    logging.getLogger("httpx").setLevel(logging.WARNING)


# 项目根日志器，所有子模块从此继承
omemo_logger = logging.getLogger("omemo")


class EndpointConfig(BaseModel):
    """API端点配置"""
    name: str = Field(..., description="端点名称")
    url: str = Field(..., description="API基础URL")
    api_key: str = Field(..., description="API密钥")
    provider: str = Field(..., description="提供商: openai 或 anthropic")
    models: List[str] = Field(default_factory=list, description="支持的模型列表")
    enabled: bool = Field(default=True, description="是否启用")
    model_aliases: Dict[str, str] = Field(default_factory=dict, description="模型别名映射: 别名 -> 实际模型名")


class MemorySettings(BaseModel):
    """记忆功能设置"""
    # 调试模式
    debug_mode: bool = Field(default=False, description="调试模式，开启后打印详细日志")
    
    # 登录认证
    login_enabled: bool = Field(default=False, description="是否启用登录认证")
    session_key_hash: Optional[str] = Field(default=None, description="Session key的SHA256哈希值")
    
    # 记忆方式: builtin(内置) 或 external(外接模型)
    memory_mode: str = Field(default="builtin", description="记忆方式")
    
    # 注入方式: full(全量) 或 rag(类RAG)
    injection_mode: str = Field(default="full", description="注入方式")
    
    # 外接模型配置（用于external模式和rag模式）
    external_model_endpoint: Optional[str] = Field(default=None, description="外接模型端点")
    external_model_api_key: Optional[str] = Field(default=None, description="外接模型API密钥")
    external_model_name: Optional[str] = Field(default=None, description="外接模型名称")
    
    # 每n轮总结记忆
    summary_interval: int = Field(default=5, description="每n轮对话总结一次记忆")
    
    # RAG注入配置
    rag_max_memories: int = Field(default=10, description="RAG模式最多返回的记忆数量")
    rag_model_endpoint: Optional[str] = Field(default=None, description="RAG模型端点URL")
    rag_model: Optional[str] = Field(default=None, description="RAG专用模型名称")
    
    # 记忆格式配置
    memory_format: str = Field(
        default="<memory>\n{memories}\n</memory>",
        description="记忆注入格式模板"
    )


class Settings(BaseSettings):
    """全局设置"""
    # 应用配置
    app_name: str = Field(default="Omni Memory", description="应用名称")
    debug: bool = Field(default=False, description="调试模式")
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8080, description="监听端口")
    
    # 数据存储路径
    data_dir: str = Field(default="./data", description="数据存储目录")
    
    # 默认系统提示词
    default_system_prompt: Optional[str] = Field(
        default=None,
        description="默认系统提示词"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.settings = Settings()
        self.endpoints: List[EndpointConfig] = []
        self.memory_settings = MemorySettings()
        self._ensure_directories()
        self._load_configs()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        Path(self.settings.data_dir).mkdir(parents=True, exist_ok=True)
        Path("./config").mkdir(parents=True, exist_ok=True)
    
    def _get_endpoints_file(self) -> Path:
        return Path("./config/endpoints.json")
    
    def _get_settings_file(self) -> Path:
        return Path("./config/settings.json")
    
    def _get_old_settings_file(self) -> Path:
        return Path("./config/memory_settings.json")
    
    def _load_configs(self):
        """加载所有配置"""
        self._load_endpoints()
        self._load_memory_settings()
    
    def _load_endpoints(self):
        """加载端点配置"""
        file_path = self._get_endpoints_file()
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.endpoints = [EndpointConfig(**ep) for ep in data]
            except Exception as e:
                print(f"加载端点配置失败: {e}")
                self.endpoints = []
        else:
            self.endpoints = []
    
    def _load_memory_settings(self):
        """加载设置，如果旧文件存在则迁移到新文件"""
        old_file_path = self._get_old_settings_file()
        new_file_path = self._get_settings_file()
        
        # 如果旧文件存在但新文件不存在，则迁移
        if old_file_path.exists() and not new_file_path.exists():
            try:
                import shutil
                shutil.move(str(old_file_path), str(new_file_path))
                print(f"已迁移配置文件: {old_file_path} -> {new_file_path}")
            except Exception as e:
                print(f"迁移配置文件失败: {e}")
        
        # 从新文件加载
        if new_file_path.exists():
            try:
                with open(new_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.memory_settings = MemorySettings(**data)
            except Exception as e:
                print(f"加载设置失败: {e}")
                self.memory_settings = MemorySettings()
    
    def save_endpoints(self):
        """保存端点配置"""
        file_path = self._get_endpoints_file()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    [ep.model_dump() for ep in self.endpoints],
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            return True
        except Exception as e:
            print(f"保存端点配置失败: {e}")
            return False
    
    def save_memory_settings(self):
        """保存设置"""
        file_path = self._get_settings_file()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    self.memory_settings.model_dump(),
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            return True
        except Exception as e:
            print(f"保存设置失败: {e}")
            return False
    
    def add_endpoint(self, endpoint: EndpointConfig) -> bool:
        """添加端点"""
        # 检查名称是否重复
        if any(ep.name == endpoint.name for ep in self.endpoints):
            return False
        self.endpoints.append(endpoint)
        return self.save_endpoints()
    
    def update_endpoint(self, name: str, endpoint: EndpointConfig) -> bool:
        """更新端点"""
        for i, ep in enumerate(self.endpoints):
            if ep.name == name:
                self.endpoints[i] = endpoint
                return self.save_endpoints()
        return False
    
    def delete_endpoint(self, name: str) -> bool:
        """删除端点"""
        for i, ep in enumerate(self.endpoints):
            if ep.name == name:
                del self.endpoints[i]
                return self.save_endpoints()
        return False
    
    def get_enabled_endpoints(self) -> List[EndpointConfig]:
        """获取启用的端点"""
        return [ep for ep in self.endpoints if ep.enabled]
    
    def get_endpoint_by_model(self, model: str) -> Optional[EndpointConfig]:
        """根据模型名称获取端点（支持别名）"""
        for ep in self.endpoints:
            if not ep.enabled:
                continue
            # 先检查别名
            if model in ep.model_aliases:
                return ep
            # 再检查原始模型名
            if model in ep.models:
                return ep
        return None
    
    def get_actual_model_name(self, model: str) -> str:
        """获取实际模型名称（解析别名）"""
        for ep in self.endpoints:
            if not ep.enabled:
                continue
            if model in ep.model_aliases:
                return ep.model_aliases[model]
            if model in ep.models:
                return model
        return model
    
    def get_model_conflicts(self) -> Dict[str, List[str]]:
        """获取模型名称冲突"""
        model_endpoints: Dict[str, List[str]] = {}
        for ep in self.endpoints:
            if not ep.enabled:
                continue
            for model in ep.models:
                if model not in model_endpoints:
                    model_endpoints[model] = []
                model_endpoints[model].append(ep.name)
        
        # 只返回有冲突的模型
        return {model: endpoints for model, endpoints in model_endpoints.items() if len(endpoints) > 1}
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """获取所有模型列表（包含冲突和别名信息）"""
        from typing import Any
        conflicts = self.get_model_conflicts()
        models = []
        
        for ep in self.endpoints:
            if not ep.enabled:
                continue
            for model in ep.models:
                # 检查是否有别名
                alias = None
                for alias_name, actual_name in ep.model_aliases.items():
                    if actual_name == model:
                        alias = alias_name
                        break
                
                # 可用名称：优先别名，没有别名就用原名
                available_name = alias if alias else model
                
                models.append({
                    "model": model,
                    "alias": alias,
                    "available_name": available_name,
                    "endpoint": ep.name,
                    "provider": ep.provider,
                    "has_conflict": model in conflicts,
                    "conflict_endpoints": conflicts.get(model, [])
                })
        
        return models
    
    def set_model_alias(self, endpoint_name: str, model: str, alias: str) -> bool:
        """设置模型别名"""
        for ep in self.endpoints:
            if ep.name == endpoint_name:
                if model not in ep.models:
                    return False
                if alias:
                    ep.model_aliases[alias] = model
                else:
                    # 删除别名
                    ep.model_aliases = {k: v for k, v in ep.model_aliases.items() if v != model}
                return self.save_endpoints()
        return False
    
    def update_memory_settings(self, settings: MemorySettings) -> bool:
        """更新记忆设置"""
        self.memory_settings = settings
        return self.save_memory_settings()


# 全局配置实例
config = ConfigManager()


def debug_print(*args, **kwargs):
    """调试日志输出（向后兼容别名，内部使用 logging.debug）"""
    if config.memory_settings.debug_mode:
        omemo_logger.debug(" ".join(str(a) for a in args))


def generate_session_key() -> str:
    """生成一个随机的session key"""
    return secrets.token_urlsafe(32)


def hash_session_key(key: str) -> str:
    """对session key进行SHA256哈希"""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_session_key(key: str) -> bool:
    """验证session key是否正确"""
    if not config.memory_settings.login_enabled:
        return True  # 未启用登录时直接通过
    
    if not config.memory_settings.session_key_hash:
        return False  # 没有设置session key
    
    return hmac.compare_digest(hash_session_key(key), config.memory_settings.session_key_hash)


def set_session_key(key: str):
    """设置session key（保存哈希值）"""
    config.memory_settings.session_key_hash = hash_session_key(key)
    config.save_memory_settings()


def clear_session_key():
    """清除session key"""
    config.memory_settings.session_key_hash = None
    config.save_memory_settings()
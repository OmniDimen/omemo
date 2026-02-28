"""
配置管理模块
支持从环境变量和配置文件加载配置
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class EndpointConfig(BaseModel):
    """API端点配置"""
    name: str = Field(..., description="端点名称")
    url: str = Field(..., description="API基础URL")
    api_key: str = Field(..., description="API密钥")
    provider: str = Field(..., description="提供商: openai 或 anthropic")
    models: List[str] = Field(default_factory=list, description="支持的模型列表")
    enabled: bool = Field(default=True, description="是否启用")


class MemorySettings(BaseModel):
    """记忆功能设置"""
    # 调试模式
    debug_mode: bool = Field(default=False, description="调试模式，开启后打印详细日志")
    
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
    
    def _get_memory_settings_file(self) -> Path:
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
        """加载记忆设置"""
        file_path = self._get_memory_settings_file()
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.memory_settings = MemorySettings(**data)
            except Exception as e:
                print(f"加载记忆设置失败: {e}")
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
        """保存记忆设置"""
        file_path = self._get_memory_settings_file()
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
            print(f"保存记忆设置失败: {e}")
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
        """根据模型名称获取端点"""
        for ep in self.endpoints:
            if model in ep.models and ep.enabled:
                return ep
        return None
    
    def update_memory_settings(self, settings: MemorySettings) -> bool:
        """更新记忆设置"""
        self.memory_settings = settings
        return self.save_memory_settings()


# 全局配置实例
config = ConfigManager()


def debug_print(*args, **kwargs):
    """调试日志输出，仅在调试模式开启时打印"""
    if config.memory_settings.debug_mode:
        print(*args, **kwargs)
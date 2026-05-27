# 🧠 Omni Memory 极简启动指南 (v1.2.0)

> 写给未来的木木：换了新电脑？5 步重新跑起来！
> 最后更新：2026-04-07 by 🦊

---

## 这是什么？

Omni Memory（omemo）是一个 **API 代理服务**，架在你的应用和 LLM 之间，让模型拥有长期记忆能力。兼容 OpenAI 和 Anthropic API 格式，换个地址就能用。

```
你的应用 → omemo（自动注入/提取记忆）→ 你的 LLM
```

### v1.2.0 有什么新东西？

| 新特性 | 说明 |
|--------|------|
| 🔐 登录认证 | 可选的 Session Key 认证，保护你的记忆数据 |
| 🤖 MCP 支持 | 可作为 MCP 工具被 Claude Desktop 等客户端调用 |
| 🏷️ 模型别名 | 多个端点的同名模型可以设别名区分 |
| 🔄 配置迁移 | `memory_settings.json` 自动迁移为 `settings.json` |
| 🌐 Anthropic 原生 API | 新增 `/v1/messages` 端点，原生支持 Anthropic 格式 |
| 🎨 WebUI 大更新 | 登录页、模型管理、设置面板全面升级 |

---

## 第一步：获取项目

### 初次 clone

```bash
git clone https://github.com/OmniDimen/omemo.git
cd omemo
```

### 已有项目？拉取最新版本

```bash
# 如果你 fork 了项目，先确认有 upstream 远程
git remote -v

# 没有的话，加上 upstream
git remote add upstream https://github.com/OmniDimen/omemo.git

# 拉取最新代码
git fetch upstream
git merge upstream/main

# 推到你的 fork
git push origin main
```

---

## 第二步：安装依赖

### 前置要求

- **Python 3.10+**（推荐 3.11）
- **pip**

### Mac / Linux

```bash
# 推荐：使用虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

> 💡 如果遇到 SSL 证书报错：
> ```bash
> pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
> ```

### Windows

```bash
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

### Docker

```bash
docker build -t omemo .
docker run -d -p 8080:8080 -v ./data:/app/data -v ./config:/app/config omemo
```

> Docker 部署时记忆数据和配置文件通过 volume 挂载持久化，容器重启不会丢失

### 当前依赖清单

| 包名 | 用途 |
|------|------|
| fastapi + uvicorn | Web 框架和 ASGI 服务器 |
| pydantic + pydantic-settings | 数据模型和配置管理 |
| httpx | 异步 HTTP 客户端（调用上游 API） |
| aiohttp | 异步 HTTP（部分适配器使用） |
| anthropic | Anthropic API SDK |
| openai | OpenAI API SDK |
| jinja2 + aiofiles | 模板渲染和静态文件 |
| python-multipart | 表单解析 |
| python-dateutil | 日期处理 |

---

## 第三步：配置

启动前需要配置两个文件，都在 `config/` 目录下。首次启动时目录会自动创建。

### 3.1 配置上游 API 端点：`config/endpoints.json`

```json
[
  {
    "name": "my-openai",
    "url": "https://api.openai.com/v1",
    "api_key": "sk-你的密钥",
    "provider": "openai",
    "models": ["gpt-4o", "gpt-4o-mini"],
    "enabled": true,
    "model_aliases": {}
  },
  {
    "name": "my-anthropic",
    "url": "https://api.anthropic.com",
    "api_key": "sk-ant-你的密钥",
    "provider": "anthropic",
    "models": ["claude-3-5-sonnet-20241022"],
    "enabled": true,
    "model_aliases": {}
  },
  {
    "name": "celum-local",
    "url": "http://192.168.x.x:1234/v1",
    "api_key": "LMS-123",
    "provider": "openai",
    "models": ["qwen3.5-9b"],
    "enabled": true,
    "model_aliases": {}
  }
]
```

#### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | ✅ | 端点名称（必须唯一） |
| `url` | ✅ | 上游 API 地址 |
| `api_key` | ✅ | 上游 API 密钥 |
| `provider` | ✅ | 提供商类型：`openai` 或 `anthropic` |
| `models` | ✅ | 支持的模型列表 |
| `enabled` | ❌ | 是否启用，默认 `true` |
| `model_aliases` | ❌ | 模型别名映射（见下方说明），默认 `{}` |

#### 🏷️ 模型别名（v1.1.0 新增）

当多个端点有同名模型时，需要设别名来区分：

```json
{
  "name": "provider-a",
  "models": ["qwen-72b"],
  "model_aliases": {"qwen-72b-a": "qwen-72b"}
}
```

调用时使用 `qwen-72b-a` 即会路由到该端点，实际发给上游的仍是 `qwen-72b`。

### 3.2 配置记忆设置：`config/settings.json`

> ⚠️ 注意：v1.1.0 起配置文件从 `memory_settings.json` 更名为 `settings.json`。如果你有旧文件，首次启动会自动迁移。

```json
{
  "debug_mode": false,
  "login_enabled": false,
  "session_key_hash": null,
  "memory_mode": "builtin",
  "injection_mode": "full",
  "external_model_endpoint": null,
  "external_model_api_key": null,
  "external_model_name": null,
  "summary_interval": 5,
  "rag_max_memories": 10,
  "rag_model_endpoint": null,
  "rag_model": null,
  "memory_format": "<memory>\n{memories}\n</memory>"
}
```

#### 字段说明

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `debug_mode` | `false` | 调试模式，开启后打印详细日志 |
| `login_enabled` | `false` | 是否启用登录认证（v1.2.0 新增） |
| `session_key_hash` | `null` | Session Key 的哈希值（自动管理，不要手动写） |
| `memory_mode` | `"builtin"` | 记忆模式：`builtin`（内置）或 `external`（外接模型） |
| `injection_mode` | `"full"` | 注入方式：`full`（全量）或 `rag`（智能筛选） |
| `external_model_*` | `null` | 外接模型配置（external 模式专用） |
| `summary_interval` | `5` | 外接模式：每 N 轮对话总结一次 |
| `rag_max_memories` | `10` | RAG 模式：最多返回的记忆数量 |
| `rag_model_*` | `null` | RAG 专用模型配置 |
| `memory_format` | `<memory>...` | 记忆注入格式模板 |

### 3.3 环境变量配置（可选）：`.env`

```bash
# 可覆盖默认设置
HOST=0.0.0.0
PORT=8080
DEBUG=false
DATA_DIR=./data
```

---

## 第四步：启动服务

### 方法一：直接运行

```bash
python3 main.py
```

### 方法二：使用脚本

```bash
# Mac
chmod +x run.command
./run.command        # 或双击 Finder 中的 run.command

# Linux
chmod +x run.sh
./run.sh

# Windows
run.bat
```

### 启动成功后你会看到

```
🚀 Omni Memory 启动成功
📁 数据目录: ./data
🧠 记忆模式: builtin
💉 注入模式: full
```

### 访问地址

| 地址 | 用途 |
|------|------|
| `http://localhost:8080/` | WebUI 管理界面 |
| `http://localhost:8080/login` | 登录页面（启用认证时） |
| `http://localhost:8080/v1` | OpenAI 兼容 API |

---

## 第五步：使用

### 5.1 最简单的用法：改 base_url

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="any-key"  # 未启用登录时随便填
)

response = client.chat.completions.create(
    model="gpt-4o",  # 或你配置的任何模型名/别名
    messages=[
        {"role": "user", "content": "你好，我叫木木"}
    ]
)
print(response.choices[0].message.content)
```

### 5.2 启用登录认证后

如果你在 WebUI 中启用了登录认证，调用 API 时需要把生成的 Session Key 填入 `api_key`：

```python
client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="你的SessionKey"  # 启用登录后，这里填 Session Key
)
```

### 5.3 接入 AstrBot

详见 [AstrBot 接入指南](docs/ASTRBOT_GUIDE.md)

---

## 项目结构速览

```
omemo/
├── main.py              # 主应用文件（所有路由和核心逻辑）
├── config.py            # 配置管理（Pydantic 模型 + ConfigManager）
├── models.py            # 数据模型（请求/响应/记忆条目）
├── requirements.txt     # Python 依赖
├── .env                 # 环境变量（可选，被 .gitignore）
│
├── api/                 # API 适配器层
│   ├── openai_adapter.py    # OpenAI API 客户端
│   ├── anthropic_adapter.py # Anthropic API 客户端
│   └── converter.py         # 格式转换器（OpenAI ↔ Anthropic）
│
├── memory/              # 记忆管理层
│   ├── storage.py       # 记忆持久化（JSON文件）
│   ├── manager.py       # 记忆操作核心（提取/注入/CRUD）
│   ├── prompts.py       # 系统提示词模板
│   └── summarizer.py    # 外接模型总结器
│
├── config/              # 运行时配置（被 .gitignore）
│   ├── endpoints.json   # API 端点配置
│   └── settings.json    # 记忆设置
│
├── data/                # 数据存储（被 .gitignore）
│   └── memories.json    # 记忆数据
│
├── templates/           # Jinja2 HTML 模板
│   ├── index.html       # WebUI 主页
│   └── login.html       # 登录页面
│
├── static/              # 前端静态资源
│   ├── css/style.css    # 样式
│   └── js/app.js        # 前端逻辑
│
├── docs/                # 文档
│   └── ASTRBOT_GUIDE.md # AstrBot 接入指南
│
├── run.sh               # Linux 启动脚本
├── run.command           # macOS 启动脚本（可双击）
└── run.bat              # Windows 启动脚本
```

---

## API 接口速查

### OpenAI 兼容接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/v1/chat/completions` | 聊天完成（支持流式） |
| `GET` | `/v1/models` | 获取模型列表 |

### Anthropic 兼容接口（v1.2.0 新增）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/v1/messages` | Anthropic 原生格式聊天 |

### 记忆管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/memories` | 获取所有记忆 |
| `GET` | `/api/memories?keyword=xxx` | 搜索记忆 |
| `POST` | `/api/memories` | 添加记忆 |
| `PUT` | `/api/memories/{id}` | 更新记忆 |
| `DELETE` | `/api/memories/{id}` | 删除记忆 |
| `GET` | `/api/memories/stats` | 记忆统计 |

### 配置管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/config/endpoints` | 获取端点配置 |
| `POST` | `/api/config/endpoints` | 添加端点 |
| `PUT` | `/api/config/endpoints/{name}` | 更新端点 |
| `DELETE` | `/api/config/endpoints/{name}` | 删除端点 |
| `GET` | `/api/config/memory` | 获取记忆设置 |
| `POST` | `/api/config/memory` | 更新记忆设置 |

### 模型管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/models` | 获取所有模型（含冲突信息） |
| `GET` | `/api/models/conflicts` | 获取模型冲突列表 |
| `POST` | `/api/models/alias` | 设置模型别名 |
| `POST` | `/api/models/fetch` | 从端点拉取可用模型 |

### 认证 API（v1.2.0 新增）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/auth/status` | 获取认证状态 |
| `POST` | `/api/auth/login` | 登录验证 |
| `POST` | `/api/auth/enable` | 启用登录（生成 Session Key） |
| `POST` | `/api/auth/disable` | 禁用登录（销毁 Key） |
| `POST` | `/api/auth/reset-key` | 重置 Session Key |

### 调试 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/debug/preview-system-prompt` | 预览系统提示词 |

---

## 记忆模式详解

### 内置模式 (builtin) — 推荐

模型在回复末尾添加 `<memory>` 标签，代理自动解析、自动截断（不会返回给用户）：

```
你好木木！很高兴认识你！

<memory>
- [2026-04-07]用户名字是木木
</memory>
```

**记忆操作格式**：

| 操作 | 格式 | 示例 |
|------|------|------|
| 新增 | `- [日期]记忆内容` | `- [2026-04-07]用户喜欢摄影` |
| 更新 | `- [日期][UPDATE:编号]新内容` | `- [2026-04-07][UPDATE:3]用户更喜欢胶片摄影` |
| 删除 | `- [日期][DELETE:编号]` | `- [2026-04-07][DELETE:5]` |

### 外接模型模式 (external)

每隔 N 轮对话，使用独立的模型总结对话并生成记忆操作。适用于**不支持复杂指令的模型**。需要额外配置 `external_model_*` 字段。

### 注入方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| **full**（全量） | 所有记忆注入到系统提示词 | 记忆少（< 50 条），简单可靠 |
| **rag**（智能筛选） | 只注入与当前对话相关的记忆 | 记忆多时节省 token |

---

## 数据存储

记忆数据存储在 `data/memories.json`：

```json
[
  {
    "id": "mem_xxx",
    "content": "用户名字是木木",
    "created_at": "2026-04-07T10:30:00",
    "updated_at": "2026-04-07T10:30:00",
    "source": "builtin_extraction"
  }
]
```

> 💡 备份提示：迁移时只需要拷贝 `config/` 和 `data/` 两个目录即可恢复所有配置和记忆。

---

## 常见问题

### Q: 端口被占用了？
在 `.env` 文件中修改：
```bash
PORT=8888
```

### Q: 怎么同时用 OpenAI 和 Anthropic 的模型？
在 `endpoints.json` 中配置多个端点，设不同的 `provider` 即可。omemo 会根据请求的 model 名自动路由到对应的端点。

### Q: 两个端点有同名模型怎么办？
使用模型别名！在 WebUI 的模型管理页面设置，或在 `endpoints.json` 的 `model_aliases` 字段配置。

### Q: 思维链模型（如 DeepSeek、QwQ）会不会把思考过程当记忆？
不会。omemo 自动识别 `reasoning_content`（思维链内容），只对最终 `content` 进行记忆提取。

### Q: 如何从旧版升级？
1. `git pull` 拉取最新代码
2. `pip install -r requirements.txt` 更新依赖
3. 旧的 `config/memory_settings.json` 会自动迁移为 `config/settings.json`
4. `data/memories.json` 格式不变，直接兼容

---

## 注意事项

1. **API Key 安全**：`config/` 目录已在 `.gitignore` 中，不会被意外提交
2. **记忆数量**：全量注入模式下，记忆过多会增加 token 消耗，建议定期在 WebUI 清理
3. **备份**：迁移到新电脑时，拷贝 `config/` + `data/` 即可
4. **登录认证**：Session Key 只在生成时显示一次，请妥善保存

---

*🦊 by Omni & Folia | OmniTopia*

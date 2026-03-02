# 🧠 Omni Memory 极简启动指南

> 5 步上手，给你的 LLM 加上长期记忆！

---

## 这是什么？

Omni Memory 是一个 **API 代理服务**，架在你的应用和 LLM 之间，让模型拥有长期记忆能力。兼容 OpenAI API 格式，换个地址就能用。

```
你的应用 → omemo（自动注入/提取记忆）→ 你的 LLM
```

---

## 第一步：获取项目

```bash
git clone https://github.com/OmniDimen/omemo.git
cd omemo
```

## 第二步：安装依赖

### Mac / Linux

```bash
pip install -r requirements.txt
```

> 如果遇到 SSL 证书报错，加上：`--trusted-host pypi.org --trusted-host files.pythonhosted.org`

### Windows

```bash
pip install -r requirements.txt
```

### Docker

```bash
docker build -t omemo .
docker run -d -p 8080:8080 -v ./data:/app/data -v ./config:/app/config omemo
```

> Docker 部署时记忆数据和配置文件通过 volume 挂载持久化，容器重启不会丢失

## 第三步：启动服务

> Docker 用户跳过此步，容器启动时会自动运行

### Mac

双击 `run.command` 即可启动（首次运行会自动安装依赖）。

也可以在终端运行：

```bash
./run.sh
```

### Linux

```bash
./run.sh
```

### Windows

双击 `run.bat` 或在命令行运行：

```bash
run.bat
```

看到以下输出说明启动成功：

```
🚀 Omni Memory 启动成功
📁 数据目录: ./data
🧠 记忆模式: builtin
💉 注入模式: full
INFO:     Uvicorn running on http://0.0.0.0:8080
```

> 💡 想修改端口？在项目根目录创建环境变量文件 `.env`，写入 `PORT=你想要的端口号`：
>
> ```bash
> touch .env          # 创建环境变量文件
> echo "PORT=8082" > .env  # 写入端口配置
> ```

## 第四步：打开 Web UI 配置

浏览器访问 **http://localhost:8080**（如果改了端口则访问对应端口）

### 4.1 添加 API 端点

点击 **「添加端点」**，根据你的 LLM 类型填写：

**本地模型（LM Studio / Ollama 等）：**

- 名称：`my-local-llm`
- 提供商：`openai`
- API URL：`http://localhost:1234/v1`（LM Studio 默认端口）或 `http://localhost:11434/v1`（Ollama 默认端口）
- API Key：随便填（本地模型一般不校验）
- 模型列表：你加载的模型名称

**云端 API（OpenAI / Anthropic / DeepSeek / 硅基流动等）：**

- 名称：`my-cloud-api`
- 提供商：`openai`（大部分云端 API 兼容 OpenAI 格式）或 `anthropic`（Claude 系列）
- API URL：你的云端 API 地址（如 `https://api.example.com/v1`）
- API Key：你的 API 密钥
- 模型列表：你使用的模型名称

### 4.2 确认记忆设置

切换到 **「记忆设置」** 页面，默认配置即可：

- ✅ 记忆方式：**内置记忆**（模型自动记忆）
- ✅ 注入方式：**全量注入**（所有记忆都注入）

点 **「保存设置」**。

## 第五步：开始使用

将你的应用的 API 地址改为 omemo 的地址即可：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",  # 指向 omemo
    api_key="any-key"
)

response = client.chat.completions.create(
    model="qwen3-8b",  # 你配置的模型名
    messages=[{"role": "user", "content": "你好，我叫小明！"}]
)

print(response.choices[0].message.content)
```

模型会记住你说过的话，下一次对话自动带上之前的记忆 🎉

> 如果你使用 AstrBot 等机器人框架，请参阅 [ASTRBOT_GUIDE.md](./ASTRBOT_GUIDE.md) 获取详细接入指南

---

## 📋 常用操作

- **查看记忆**：Web UI → 记忆管理
- **手动添加记忆**：Web UI → 添加记忆
- **搜索记忆**：Web UI → 搜索框
- **删除记忆**：Web UI → 点击删除按钮

---

## 📂 项目结构一览

```
omemo/
├── main.py              # 主程序入口
├── config.py            # 配置管理
├── models.py            # 数据模型定义
├── requirements.txt     # Python 依赖
├── .env                 # 环境变量（自行创建）
├── config/              # 配置文件（启动后自动生成）
│   ├── endpoints.json   # API 端点配置
│   └── memory_settings.json  # 记忆设置
├── data/                # 数据存储（自动生成）
│   └── memories.json    # 记忆数据
├── memory/              # 记忆核心模块
├── api/                 # API 适配器
├── static/              # Web UI 静态资源
└── templates/           # Web UI 模板
```

---

*Apache License 2.0 · [OmniDimen/omemo](https://github.com/OmniDimen/omemo)*

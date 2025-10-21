# 聊天机器人项目 - Windows 运行指南

## 📋 项目简介

这是一个基于 FastAPI 的聊天机器人项目，具有长期记忆功能（使用 Qdrant 向量数据库）。

### 主要组件
- **后端服务**: FastAPI REST API (chat_server.py)
- **前端界面**: Streamlit Web UI (app.py)
- **向量数据库**: Qdrant (本地存储)
- **LLM**: 火山引擎豆包/DeepSeek 模型

---

## 🚀 快速开始

### 方式一：一键启动（推荐）⭐

#### 1. 启动服务
```powershell
.\start_services.ps1
```

这个脚本会自动：
- ✓ 激活 Anaconda 环境 `mem_minus`
- ✓ 创建必要的目录（logs, wks/qdrant）
- ✓ 启动后端 API 服务（端口 8082）
- ✓ 启动前端 Streamlit 界面（端口 8081）
- ✓ 自动打开浏览器

#### 2. 停止服务
```powershell
.\stop_services.ps1
```

这个脚本会自动停止所有相关服务并释放端口。

#### 3. 访问应用
- **前端界面**: http://localhost:8081
- **API 文档**: http://localhost:8082/docs

---

### 方式二：快速启动（已激活环境）

如果你已经激活了 `mem_minus` 环境：
```powershell
.\quick_start.ps1
```

---

### 方式二：手动启动

#### 1. 激活环境
```powershell
conda activate mem_minus
```

#### 2. 安装依赖（首次运行）
```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

#### 3. 创建必要目录
```powershell
mkdir logs
mkdir wks\qdrant
```

#### 4. 启动后端服务（新窗口）
```powershell
$env:PYTHONPATH="."
python server\chat_server.py --port 8082
```

#### 5. 启动前端界面（新窗口）
```powershell
streamlit run server\app.py --server.fileWatcherType none --server.port 8081
```

---

## 📁 项目结构

```
telegrambot/
├── server/                 # 服务端代码
│   ├── server.py          # 主 API 服务器
│   ├── chat_server.py     # 聊天服务器（推荐使用）
│   └── app.py             # Streamlit 前端界面
├── mem/                    # 记忆管理模块
│   ├── memory/            # 记忆核心逻辑
│   ├── vector_stores/     # 向量数据库
│   ├── llms/              # LLM 集成
│   └── embeddings/        # 嵌入模型
├── logs/                   # 日志文件目录
├── wks/                    # 工作空间
│   └── qdrant/            # Qdrant 数据库存储
├── requirements.txt        # Python 依赖
├── setup_and_install.ps1  # 环境设置脚本
├── start_services.ps1     # 服务启动脚本
└── activate_env.ps1       # 环境激活脚本
```

---

## ⚙️ 配置说明

### 1. LLM 配置
项目使用火山引擎的 API，配置位于 `server/chat_server.py`:

```python
"llm": {
    "provider": "openai",
    "config": {
        "api_key": "8b2dce0f-ed36-4d2b-898a-14845cc496c1",
        "model": "deepseek-v3-1-250821",
        "openai_base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "temperature": 0.5,
        "max_tokens": 1024,
    }
}
```

⚠️ **建议替换为你自己的 API 密钥！**

### 2. 向量数据库配置
默认使用本地 Qdrant 数据库:

```python
"vector_store": {
    "provider": "qdrant",
    "config": {
        "collection_name": "memory_test",
        "path": "./wks/qdrant",  # 本地存储路径
        "embedding_model_dims": 2560,
    }
}
```

### 3. 嵌入模型配置
```python
"embedder": {
    "provider": "openai",
    "config": {
        "model": "doubao-embedding-text-240715",
        "api_key": "8b2dce0f-ed36-4d2b-898a-14845cc496c1",
        "openai_base_url": "ark",
        "embedding_dims": 2560
    }
}
```

---

## 🧪 测试 API

### 使用 PowerShell 测试聊天接口
```powershell
$body = @{
    user_id = "test_user"
    message = "你好，我是小明"
    model = "deepseek-v3.1"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8082/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

### 使用 curl 测试
```powershell
curl -X POST "http://localhost:8082/chat" `
  -H "Content-Type: application/json" `
  -d '{\"user_id\":\"test_user\",\"message\":\"你好\"}'
```

---

## 📊 主要功能

### 1. 聊天对话
- 支持多轮对话
- 自动保存聊天历史
- 长期记忆功能

### 2. 记忆管理
- **创建记忆**: 基于对话自动提取记忆
- **检索记忆**: 根据用户 ID 获取相关记忆
- **搜索记忆**: 基于查询搜索存储的记忆
- **更新记忆**: 更新现有记忆
- **删除记忆**: 删除特定记忆

### 3. API 端点
访问 http://localhost:8082/docs 查看完整 API 文档

主要端点：
- `POST /chat` - 聊天对话
- `POST /memories` - 创建记忆
- `GET /memories` - 获取记忆
- `POST /memories/search` - 搜索记忆
- `PUT /memories/{memory_id}` - 更新记忆
- `DELETE /memories/{memory_id}` - 删除记忆

---

## 🐛 常见问题

### 1. 环境激活失败
**问题**: `conda activate mem_minus` 失败

**解决方案**:
```powershell
# 初始化 conda（首次使用）
conda init powershell

# 重启 PowerShell 后再试
conda activate mem_minus
```

### 2. 端口被占用
**问题**: 端口 8081 或 8082 已被占用

**解决方案**:
```powershell
# 修改端口号
python server\chat_server.py --port 8083
streamlit run server\app.py --server.port 8084
```

### 3. 模块导入错误
**问题**: `ModuleNotFoundError: No module named 'mem'`

**解决方案**:
```powershell
# 确保设置了 PYTHONPATH
$env:PYTHONPATH="."
```

### 4. API 密钥失效
**问题**: LLM API 调用失败

**解决方案**:
- 检查 API 密钥是否有效
- 替换为你自己的火山引擎 API 密钥
- 修改 `server/chat_server.py` 中的配置

### 5. Qdrant 数据库错误
**问题**: 向量数据库连接失败

**解决方案**:
```powershell
# 确保目录存在
mkdir wks\qdrant

# 删除旧数据重新初始化
Remove-Item -Recurse -Force wks\qdrant
mkdir wks\qdrant
```

---

## 📝 开发说明

### 修改配置
主要配置文件：
- `server/chat_server.py` - 聊天服务器配置
- `server/server.py` - 主服务器配置
- `server/app.py` - 前端界面配置

### 查看日志
```powershell
# 后端日志
Get-Content logs\chat_backend.log -Tail 50 -Wait

# 记忆系统日志
Get-Content logs\mem.log -Tail 50 -Wait
```

### 停止服务
直接关闭对应的 PowerShell 窗口，或按 `Ctrl+C`

---

## 📚 依赖包说明

主要依赖：
- `fastapi` - Web 框架
- `uvicorn` - ASGI 服务器
- `streamlit` - 前端界面
- `qdrant-client` - 向量数据库客户端
- `openai` - LLM API 客户端
- `langchain-community` - LangChain 集成
- `loguru` - 日志管理

完整依赖列表见 `requirements.txt`

---

## 🔗 相关链接

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Streamlit 文档](https://docs.streamlit.io/)
- [Qdrant 文档](https://qdrant.tech/documentation/)
- [火山引擎 API](https://www.volcengine.com/docs/82379)

---

## 📄 许可证

请参考原项目许可证

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**祝使用愉快！** 🎉


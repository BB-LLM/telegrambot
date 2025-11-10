# 日记总结模块

独立的日记总结功能模块，供 telegrambot 调用。

## 功能特性

- ✅ 根据当天记忆自动生成日记（使用 glm-4-flash）
- ✅ 满足需求文档 A10：每日一篇，唯一性保障（user_id + date）
- ✅ 支持今日日记查询，若无则回退昨日
- ✅ 返回格式：标题 + 3-6 行正文 + 2 个标签 + 按钮配置
- ✅ 独立 Demo 页面（开发测试用）

## 快速开始

### 1. 安装依赖

```bash
cd dairy
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置（API_KEY 等）

### 3. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8083` 启动

### 4. 访问 Demo 页面

打开浏览器访问：`http://localhost:8083/`

页面会自动加载模拟数据并生成日记展示。

## API 接口

### POST `/diary/generate`

生成或获取日记（幂等性保证）

**请求格式（与 telegrambot 一致）：**
```json
{
  "user_id": "tg_123456",
  "date": "2025-10-30",
  "timezone": "Asia/Shanghai",
  "messages": [
    {"role": "user", "content": "...", "time": "..."}
  ],
  "memories": {
    "facts": "...",
    "profile": "...",
    "style": "...",
    "commitments": "..."
  }
}
```

**响应格式：**
```json
{
  "created": true,
  "diary": {
    "user_id": "tg_123456",
    "date": "2025-10-30",
    "title": "今日反思",
    "body_lines": ["...", "...", "..."],
    "tags": ["tag1", "tag2"],
    "ui": {
      "inline_keyboard": [...]
    }
  }
}
```

### GET `/diary/today?user_id=xxx`

获取今日日记，若今日无则返回昨日日记。

**Headers:**
```
X-API-Key: your-secret-key-here
```

## 端口说明

- **8083**: 后端 API 服务（供 telegrambot 调用）
- Demo 页面也在 8083 端口（访问根路径 `/`）

## 后续接入 telegrambot

telegrambot 定时任务（21:00-22:00）调用：

```python
import requests

response = requests.post(
    "http://localhost:8083/diary/generate",
    headers={"X-API-Key": "your-secret-key-here"},
    json={
        "user_id": user_id,
        "date": today_date,
        "messages": daily_messages,
        "memories": daily_memories
    }
)

diary = response.json()["diary"]
# 在 telegrambot 的 Streamlit UI 或 Telegram 聊天中展示
```

## 需求文档合规

- ✅ A10: 每个用户每个自然日仅生成 1 篇日记
- ✅ A10: 唯一性保障（user_id + date UNIQUE 约束）
- ✅ A10: 标题 + 3-6 行正文 + 2 个标签
- ✅ A10: 按钮配置（♥ 保存 / ↩ 回复）
- ✅ L7/L20: 若当日日记未发布，显示昨日日记


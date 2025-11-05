# TelegramBot 对话质量评估系统

严格借鉴 pocket-souls-agents 的评估流程，对 TelegramBot 对话质量进行全面评估。

## 概述

### 两种评估方法

| 方法 | 目的 | 方法 | 适用场景 |
|--------|---------|----------|----------|
| **方法1：固定测试用例** | 标准化评估 | 使用预设测试用例进行单轮对话评估 | 基准测试、回归测试 |
| **方法2：动态对话** | 适应性测试 | 模拟真实用户进行多轮对话 | 真实场景模拟 |

## 快速开始

### 前置条件

在项目根目录的 .env 文件中设置环境变量：
```
OPENAI_API_KEY=your_openai_api_key_here
```

### 运行评估

```bash
cd telegrambot

# 方法1：固定测试用例
python evaluation/test_method1.py

# 方法2：动态对话
python evaluation/test_method2.py
```

## 方法1：固定测试用例

### 目的：使用一致的、可重复的输入进行标准化评估

### 工作流程

```
预定义输入 → TelegramBot 回复 → LLM 评判 → 分数 (0-10)
```

### 测试类别

- **情感支持** (40个测试) - 共情、安慰、理解
- **日常对话** (40个测试) - 闲聊、日常话题
- **个人成长** (25个测试) - 自我改进、发展
- **创意活动** (20个测试) - 艺术、写作、想象力
- **人际关系** (20个测试) - 社交联系、爱情
- **心理健康** (15个测试) - 焦虑、抑郁、健康

### 评估标准

**7个专业维度：**

1. **逻辑一致性** (15%) - 回复逻辑是否清晰、一致、合理
2. **语言流畅性** (15%) - 表达是否自然、语法正确、节奏恰当
3. **吸引力** (15%) - 回复是否有趣、引人入胜
4. **角色一致性** (20%) - 是否匹配AI伴侶人设、温暖关怀、合适边界
5. **动作描述质量** (15%) - 动作描述是否生动、匹配角色、支撑人设
6. **情感表达** (10%) - 情感是否真实自然、匹配情境、层次丰富
7. **游戏沉浸感** (10%) - 是否贴合世界观、增强玩家沉浸、体现AI伴侶价值

### 示例测试用例

```json
{
  "input": "我今天感觉很低落",
  "category": "emotional_support",
  "expected_themes": ["empathy", "reassurance", "practical_advice"]
}
```

## 方法2：动态对话

### 目的：测试AI在不同用户人格下的适应性和自然对话能力

### 工作流程

```
用户人设 → 开场消息 → 5轮对话 → LLM 评判
```

### 用户人格类型

| 人设 | 年龄 | 风格 | 沟通方式 | 示例开场 |
|---------|-----|-------|---------------|----------------|
| **Emma** | 19 | 社交达人 | 外向、潮流、表达丰富 | "hey! 最近怎么样？" |
| **Lily** | 21 | 创意梦想家 | 艺术、深思、诗意 | "hi... 我感觉最近缺乏灵感" |
| **Sophie** | 22 | 学术成就者 | 逻辑、目标导向、精确 | "hey，我想在个人发展上做些工作" |
| **Mia** | 18 | 焦虑深思者 | 敏感、需要支持 | "我最近感觉压力特别大..." |
| **Zoe** | 20 | 积极乐观派 | 正能量、激励、活跃 | "hey！我今天需要一些动力" |

### 评估维度

- **对话流畅性** (20%) - 对话是否自然流畅
- **用户参与度** (20%) - 是否能吸引用户继续对话
- **角色一致性** (15%) - 是否保持AI角色一致性
- **情感智能** (15%) - 是否能理解和响应情感
- **话题处理** (15%) - 是否能有效处理话题
- **适应性** (15%) - 是否能适应不同用户风格

### 核心创新

动态响应类型模拟自然对话：
- `react_and_share` - 对回复做反应 + 分享简短内容
- `just_react` - 简单回应
- `ask_follow_up` - 提出后续问题
- `share_experience` - 分享个人经历
- `simple_response` - 简短、自然的反应

## 项目结构

```
evaluation/
├── config/
│   └── evaluation_config.py      # 所有配置设置
├── methods/
│   ├── method1_fixed_test.py      # 固定测试实现
│   ├── user_agent.py              # 动态对话逻辑
│   └── llm_judge.py               # LLM评估逻辑
├── test_cases/
│   └── test_cases.json             # 预设测试用例
├── results/                       # 带时间戳的输出文件
├── test_method1.py               # 方法1运行器
└── test_method2.py               # 方法2运行器
```

## 配置

### 模型配置

```python
# 教师模型
AVAILABLE_TEACHER_MODELS = {
    "gpt-4-turbo": "最严格和平衡的评估（推荐）",
    "gpt-4o": "能力强但可能更宽松",
    "gpt-4": "经典GPT-4，可靠但较慢"
}

# 对话设置
DYNAMIC_CONVERSATION_CONFIG = {
    "conversation_rounds": 5,
    "temperature": 0.7,
    "max_tokens": 200
}
```

## 结果和分析

### 输出文件

- `results/method1_results_YYYYMMDD_HHMMSS.json` - 固定测试详细结果
- `results/method2_results_YYYYMMDD_HHMMSS.json` - 动态对话结果

### 关键指标

**方法1输出：**
```json
{
  "summary": {
    "total_tests": 60,
    "successful_tests": 58,
    "overall_average": 7.8,
    "category_scores": {
      "emotional_support": 8.2,
      "daily_conversation": 7.5
    }
  }
}
```

**方法2输出：**
```json
{
  "summary": {
    "total_conversations": 5,
    "overall_average": 7.6,
    "persona_performance": {
      "Emma (社交达人)": 8.1,
      "Lily (创意梦想家)": 7.2
    }
  }
}
```


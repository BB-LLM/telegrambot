import json
import time
import uuid
from typing import Dict, List, Optional, Union
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from loguru import logger
import uvicorn
from dotenv import load_dotenv

from mem.memory.configs import MemoryConfig
from mem.memory.memory import Memory
from mem.com.factory import LlmFactory
from mem.vector_stores.prompts import NOVA_PROMPT

# 加载环境变量
def setup_logger():
    """设置日志记录器"""
    logger.add('./logs/chat_backend.log', rotation="500 MB")

# 初始化应用
def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    app = FastAPI(
        title="Chatbot with Long Term Memory API",
        description="A REST API for chatbot with memory management",
        version="1.0.0",
    )
    
    # 聊天历史存储 - 使用字典存储每个用户的聊天历史
    chat_histories: Dict[str, List[Dict]] = {}
    
    # 记忆实例
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "memory_test",
                "embedding_model_dims": 2560,
                "client": None,
                "host": "",
                "port": 6333,
                "path": "/Users/zouwuhe/Desktop/src/telegrambot/wks/qdrant",
                "url": "https://d8a17329-41df-49fc-811f-c5e762a2b12e.europe-west3-0.gcp.cloud.qdrant.io:6333",
                "api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.zyODVTAKCSNpo0cBBh6yXMlf29A8nJAaz42KTTZP2hk",
                "on_disk": False
            }
        },
        "llm": {
            "provider": "openai",
            "config": {
                "api_key": "8b2dce0f-ed36-4d2b-898a-14845cc496c1",
                "model": "deepseek-v3-1-250821",
                "openai_base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "temperature": 0.5,
                "max_tokens": 1024,
                "top_p": 0.5,
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "doubao-embedding-text-240715",
                "api_key": "8b2dce0f-ed36-4d2b-898a-14845cc496c1",
                "openai_base_url": "ark",
                "embedding_dims": 2560
            }
        },
        "version": "v1.1",
        "custom_prompt": ""
    }
    
    config = MemoryConfig(**config)
    MEMORY_INSTANCE = Memory(config)
    
    # 模型配置
    model_configs = {
        "doubao-character": {
            "api_key": "8b2dce0f-ed36-4d2b-898a-14845cc496c1",
            "model": "doubao-1-5-pro-32k-character-250715",
            "openai_base_url": "https://ark.cn-beijing.volces.com/api/v3"
        },
        "deepseek-v3.1": {
            "api_key": "8b2dce0f-ed36-4d2b-898a-14845cc496c1",
            "model": "deepseek-v3-1-250821",
            "openai_base_url": "https://ark.cn-beijing.volces.com/api/v3"
        }
    }
    
    # 请求模型定义
    class Message(BaseModel):
        role: str = Field(..., description="Role of the message (user or assistant).")
        content: str = Field(..., description="Message content.")
        time: Optional[str] = None
    
    class ChatRequest(BaseModel):
        user_id: str = Field(..., description="User ID")
        message: str = Field(..., description="User's message")
        model: str = Field(default="doubao-character", description="Model to use")
        persona: Optional[str] = Field(default="", description="Bot persona")
        frequency: int = Field(default=1, description="Memory extraction frequency")
        summary_frequency: int = Field(default=10, description="Summary frequency")
    
    # 帮助函数
    def get_or_create_chat_history(user_id: str) -> List[Dict]:
        """获取或创建用户的聊天历史"""
        if user_id not in chat_histories:
            chat_histories[user_id] = []
        return chat_histories[user_id]
    
    def get_memories(chat_request: ChatRequest):
        """获取用户记忆"""
        params = {
            "user_id": chat_request.user_id,
        }
        
        # 并发获取不同类型的记忆
        with concurrent.futures.ThreadPoolExecutor() as executor:
            params.update({"filters": {"type": 'facts'}, "limit": 3})
            future_memories = executor.submit(MEMORY_INSTANCE.search, chat_request.message, **params)
            
            params.update({"filters": {"type": 'profile'}, "limit": 100})
            future_profile = executor.submit(MEMORY_INSTANCE.get_all, **params)
            
            params.update({"filters": {"type": 'style'}, "limit": 100})
            future_style = executor.submit(MEMORY_INSTANCE.get_all, **params)
            
            params.update({"filters": {"type": 'commitments'}, "limit": 100})
            future_commitments = executor.submit(MEMORY_INSTANCE.get_all, **params)
            
            concurrent.futures.wait([future_memories, future_profile, future_style, future_commitments])
            
            original_memories = future_memories.result()
            profile_memories = future_profile.result()
            style_memories = future_style.result()
            commitments_memories = future_commitments.result()
        
        # 格式化记忆
        memories_facts = "\n".join(f"- {entry['memory']}" for entry in original_memories.get("results", []))
        memories_profile = "\n".join(f"- {entry['memory']}" for entry in profile_memories.get("results", []))
        memories_style = "\n".join(f"- {entry['memory']}" for entry in style_memories.get("results", []))
        memories_commitments = "\n".join(f"- {entry['memory']}" for entry in commitments_memories.get("results", []))
        
        result = {"facts": memories_facts, "profile": memories_profile, "style": memories_style, "commitments": memories_commitments}
        return result
    
    # API 端点
    @app.post("/chat", summary="Chat with the bot")
    def chat(chat_request: ChatRequest):
        """与机器人聊天并管理聊天历史"""
        try:
            user_id = chat_request.user_id
            user_message = chat_request.message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 检查模型是否支持
            if chat_request.model not in model_configs:
                raise HTTPException(status_code=400, detail=f"Model {chat_request.model} not supported")
            
            # 获取或创建聊天历史
            chat_history = get_or_create_chat_history(user_id)
            
            # 添加用户消息到聊天历史
            user_message_obj = {
                "role": "user",
                "content": user_message,
                "time": timestamp
            }
            chat_history.append(user_message_obj)
            
            # 记录日志
            logger.info(f"User {user_id} sent message: {user_message}")
            
            # 获取用户记忆
            memories = get_memories(chat_request)
            logger.info(f"User {user_id} memories: {json.dumps(memories, ensure_ascii=False)}")
            
            # 构建记忆字符串
            memories_str = f"\n[memorable events]：\n{memories['facts']}" + \
                f"\n\n[player profile]：\n{memories['profile']}" + \
                f"\n\n[style notes Nova should mirror or avoid]：\n{memories['style']}" + \
                f"\n\n[tiny commitments the PLAYER made or agreed to]：\n{memories['commitments']}"
            
            # 构建系统提示
            system_prompt = "You are a role-playing expert. Based on the provided memory information, you will now assume the following role to chat with the user.\n" \
                + NOVA_PROMPT + "\n" + memories_str
            
            # 准备发送给LLM的消息（只取最近10条消息）
            messages_for_llm = [{"role": "system", "content": system_prompt}] + chat_history[-20:]
            
            # 创建LLM实例并获取响应
            llm = LlmFactory.create("openai", config=model_configs[chat_request.model])
            response = llm.generate_response(messages=messages_for_llm, response_format=None)
            
            # 处理响应格式
            if "：" in response[:5]:
                response = response.split("：")[1]
            
            # 添加助手回复到聊天历史
            assistant_message_obj = {
                "role": "assistant",
                "content": response,
                "time": timestamp
            }
            chat_history.append(assistant_message_obj)
            
            # 记录响应日志
            logger.info(f"Assistant response to user {user_id}: {response}")
            
            # 准备结果
            results = {'response': response, "used_memory": memories_str}
            
            # 根据频率提取记忆
            if len(chat_history) // 2 % chat_request.frequency == 0:
                memory_msg = chat_history[-chat_request.frequency * 2:]
                if len(chat_history) > chat_request.frequency * 2 + 1:
                    memory_msg = memory_msg + [{"role": "history", "content": chat_history[-(chat_request.frequency+1) * 2: -chat_request.frequency * 2 - 1]}]
                
                new_memory = MEMORY_INSTANCE.add(memory_msg, user_id=user_id)
                results['new_memory'] = new_memory.get('results', [])
                results["graph_memory"] = new_memory.get("relations", {})
                logger.info(f"New memory added for user {user_id}: {json.dumps(new_memory, ensure_ascii=False)}")
            
            # 根据频率生成总结
            if len(chat_history) // 2 % chat_request.summary_frequency == 0:
                summary = MEMORY_INSTANCE._create_summary(chat_history[-chat_request.summary_frequency * 2:], user_id=user_id)
                results["summary"] = summary
                logger.info(f"Summary created for user {user_id}: {json.dumps(summary, ensure_ascii=False)}")
            
            return results
            
        except Exception as e:
            logger.exception(f"Error in chat endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/chat_history/{user_id}", summary="Get chat history for a user")
    def get_chat_history(user_id: str):
        """获取指定用户的聊天历史"""
        try:
            chat_history = get_or_create_chat_history(user_id)
            return {"user_id": user_id, "chat_history": chat_history}
        except Exception as e:
            logger.exception(f"Error getting chat history: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/memories/{user_id}", summary="Get all memories for a user")
    def get_all_memories(user_id: str):
        """获取指定用户的所有记忆"""
        try:
            params = {"user_id": user_id}
            result = MEMORY_INSTANCE.get_all(**params)
            
            # 格式化记忆结果
            if result.get("results"):
                results = result["results"]
                # 分类记忆
                profile = []
                facts = []
                style = []
                commitments = []
                
                for mem in results:
                    mem_type = mem.get('metadata', {}).get('type')
                    memory_content = mem['memory']
                    if ':' in memory_content:
                        memory_content = memory_content.split(":")[1].strip()
                    
                    formatted_mem = {
                        'memory': memory_content,
                        'created_at': mem['created_at'],
                        'updated_at': mem.get('updated_at'),
                        'metadata': mem.get('metadata', {})
                    }
                    
                    if mem_type == "profile":
                        profile.append(formatted_mem)
                    elif mem_type == "style":
                        style.append(formatted_mem)
                    elif mem_type == "commitments":
                        commitments.append(formatted_mem)
                    else:
                        facts.append(formatted_mem)
                
                return {
                    "user_id": user_id,
                    "profile": profile,
                    "facts": facts,
                    "style": style,
                    "commitments": commitments,
                    "relations": result.get("relations", [])
                }
            
            return {"user_id": user_id, "profile": [], "facts": [], "style": [], "commitments": [], "relations": []}
            
        except Exception as e:
            logger.exception(f"Error getting memories: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/chat_history/{user_id}", summary="Clear chat history for a user")
    def clear_chat_history(user_id: str):
        """清除指定用户的聊天历史"""
        try:
            if user_id in chat_histories:
                del chat_histories[user_id]
                logger.info(f"Chat history cleared for user {user_id}")
            return {"message": "Chat history cleared successfully"}
        except Exception as e:
            logger.exception(f"Error clearing chat history: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)
    def home():
        """重定向到OpenAPI文档"""
        return RedirectResponse(url="/docs")
    
    return app

# 主函数
if __name__ == "__main__":
    import argparse
    import concurrent.futures
    
    # 设置日志
    setup_logger()
    
    # 创建应用
    app = create_app()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8082)
    args = parser.parse_args()
    
    # 运行应用
    uvicorn.run(app, host="0.0.0.0", port=args.port, timeout_keep_alive=5)

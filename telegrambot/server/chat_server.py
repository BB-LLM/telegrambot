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

# 导入情感主题检测模块
from emotional.detector import detect_themes_and_tone, build_emotional_prompt

# 导入性格分析模块
from personality.tracker import PersonalityTracker
from personality.profile import PersonalityProfile
from personality.adjuster import PersonalityPromptAdjuster
from personality.storage import PersonalityStorage
from personality.pocket_themes import PocketThemeAssessment

# 全局变量
POCKET_ASSESSMENT = None

# 模型配置
MODEL_CONFIGS = {
    "glm-4-flash": {
        "api_key": "0031af15104f4a49bb70e1e6bf1e4d72.nybmwLU1gf7U41fh",
        "model": "glm-4-flash",
        "openai_base_url": "https://open.bigmodel.cn/api/paas/v4/"
    },
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
                "path": "./wks/qdrant",  # 使用本地文件存储
                "on_disk": True  # 持久化到磁盘
                # 注释掉远程配置，使用本地存储
                # "url": "https://...",
                # "api_key": "...",
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
                "openai_base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "embedding_dims": 2560
            }
        },
        "version": "v1.1",
        "custom_prompt": ""
    }
    
    config = MemoryConfig(**config)
    MEMORY_INSTANCE = Memory(config)
    
    
    # 初始化性格存储
    PERSONALITY_STORAGE = PersonalityStorage(MEMORY_INSTANCE)
    
    # 请求模型定义
    class Message(BaseModel):
        role: str = Field(..., description="Role of the message (user or assistant).")
        content: str = Field(..., description="Message content.")
        time: Optional[str] = None
    
    class ChatRequest(BaseModel):
        user_id: str = Field(..., description="User ID")
        message: str = Field(..., description="User's message")
        model: str = Field(default="glm-4-flash", description="Model to use")
        persona: Optional[str] = Field(default="", description="Bot persona")
        frequency: int = Field(default=1, description="Memory extraction frequency")
        summary_frequency: int = Field(default=10, description="Summary frequency")
        scene: Optional[str] = Field(default="default", description="Selected situation scene (default/creative/contemplative/connection/growth/reflection)")
        assessment_mode: Optional[str] = Field(default="normal", description="Assessment mode: normal or pocket_themes")
    
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
        
        # 简化记忆检索，减少并发查询
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 只获取最重要的facts记忆
            params.update({"filters": {"type": 'facts'}, "limit": 2})
            future_memories = executor.submit(MEMORY_INSTANCE.search, chat_request.message, **params)
            
            # 其他记忆类型减少查询量
            params.update({"filters": {"type": 'profile'}, "limit": 5})
            future_profile = executor.submit(MEMORY_INSTANCE.get_all, **params)
            
            params.update({"filters": {"type": 'style'}, "limit": 5})
            future_style = executor.submit(MEMORY_INSTANCE.get_all, **params)
            
            params.update({"filters": {"type": 'commitments'}, "limit": 5})
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
    @app.post("/start_pocket_assessment", summary="Start Pocket theme assessment")
    def start_pocket_assessment(user_id: str, model: str = "glm-4-flash"):
        """开始Pocket五大主题性格评估"""
        try:
            # 初始化Pocket评估器（如果还没有）
            global POCKET_ASSESSMENT
            if POCKET_ASSESSMENT is None:
                analysis_llm = LlmFactory.create("openai", config=MODEL_CONFIGS[model])
                POCKET_ASSESSMENT = PocketThemeAssessment(analysis_llm)
            
            # 开始评估
            result = POCKET_ASSESSMENT.start_assessment(user_id)
            
            logger.info(f"Started Pocket assessment for user {user_id}")
            return result
            
        except Exception as e:
            logger.exception(f"Error starting Pocket assessment: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/pocket_assessment_response", summary="Process Pocket assessment response")
    def pocket_assessment_response(user_id: str, response: str, model: str = "glm-4-flash"):
        """处理Pocket评估回答"""
        try:
            # 确保Pocket评估器已初始化
            global POCKET_ASSESSMENT
            if POCKET_ASSESSMENT is None:
                analysis_llm = LlmFactory.create("openai", config=MODEL_CONFIGS[model])
                POCKET_ASSESSMENT = PocketThemeAssessment(analysis_llm)
            
            # 处理回答
            result = POCKET_ASSESSMENT.process_response(user_id, response)
            
            # 如果评估完成，生成性格档案
            if result.get("status") == "completed":
                personality_data = POCKET_ASSESSMENT.get_personality_data(user_id)
                if personality_data:
                    # 生成完整档案
                    complete_profile = PersonalityProfile.generate_from_big5(personality_data)
                    PERSONALITY_STORAGE.save(complete_profile)
                    
                    # 添加到结果中
                    result["personality_profile"] = {
                        "primary_traits": complete_profile.primary_traits,
                        "emotional_state": complete_profile.emotional_state,
                        "big5_scores": {
                            "openness": complete_profile.big5_assessment.openness.score,
                            "conscientiousness": complete_profile.big5_assessment.conscientiousness.score,
                            "extraversion": complete_profile.big5_assessment.extraversion.score,
                            "agreeableness": complete_profile.big5_assessment.agreeableness.score,
                            "neuroticism": complete_profile.big5_assessment.neuroticism.score
                        }
                    }
                    
                    logger.info(f"Pocket assessment completed for user {user_id}")
            
            return result
            
        except Exception as e:
            logger.exception(f"Error processing Pocket assessment response: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/pocket_assessment_status/{user_id}", summary="Get Pocket assessment status")
    def get_pocket_assessment_status(user_id: str):
        """获取Pocket评估状态"""
        try:
            global POCKET_ASSESSMENT
            if POCKET_ASSESSMENT is None:
                return {"status": "not_started"}
            
            return POCKET_ASSESSMENT.get_assessment_status(user_id)
            
        except Exception as e:
            logger.exception(f"Error getting Pocket assessment status: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/chat", summary="Chat with the bot")
    def chat(chat_request: ChatRequest):
        """与机器人聊天并管理聊天历史"""
        try:
            user_id = chat_request.user_id
            user_message = chat_request.message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 检查模型是否支持
            if chat_request.model not in MODEL_CONFIGS:
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
            
            # ========== 场景选择检测 ==========
            scene_label = "Default (No Scene)"
            if chat_request.scene and chat_request.scene != "default":
                try:
                    from scenes.configs import SCENE_PRESETS
                    scene_preset = SCENE_PRESETS.get(chat_request.scene, {})
                    scene_label = scene_preset.get("label", chat_request.scene)
                except Exception as _:
                    pass
            
            # 打印场景选择结果到终端和日志
            print("\n" + "="*60)
            print(f"[SCENE SELECTION] User: {user_id}")
            print(f"Selected Scene: {scene_label}")
            print("="*60 + "\n")
            
            logger.info(f"Scene Selection | User {user_id} | Selected Scene: {scene_label}")
            
            # ========== 情感主题检测 ==========
            # 简化情感检测，只在消息较长时进行
            if len(user_message) > 20:  # 只对较长的消息进行情感检测
                emotional_result = detect_themes_and_tone(
                    memory_text="",  # 不传入历史记忆
                    current_message=user_message
                )
                themes = emotional_result["themes"]
                emotional_tone = emotional_result["emotional_tone"]
            else:
                themes = []
                emotional_tone = "neutral"
            
            # 打印情感检测结果到终端和日志
            print("\n" + "="*60)
            print(f"[EMOTIONAL DETECTION] User: {user_id}")
            print(f"Message: {user_message[:100]}..." if len(user_message) > 100 else f"Message: {user_message}")
            print(f"Detected Themes: {', '.join(themes)}")
            print(f"Emotional Tone: {emotional_tone.lower()}")
            print("="*60 + "\n")
            
            logger.info(f"Emotional Themes | User {user_id} | Themes: {themes} | Tone: {emotional_tone.lower()}")
            
            # ========== 性格分析与跟踪 ==========
            personality_data = None
            pocket_assessment_mode = False
            
            # 检查是否是Pocket评估模式
            if chat_request.assessment_mode == "pocket_themes":
                pocket_assessment_mode = True
                # 在Pocket评估模式下，不进行常规性格分析
                personality_data = PERSONALITY_STORAGE.load(user_id)
                # 如果用户没有性格数据，创建一个默认的
                if not personality_data:
                    from personality.models import PersonalityData
                    personality_data = PersonalityData(user_id=user_id)
            else:
                # 常规模式：不再进行按轮数触发的性格分析与日志打印
                personality_data = PERSONALITY_STORAGE.load(user_id)
                
                # 如果用户没有性格数据，创建一个默认的
                if not personality_data:
                    from personality.models import PersonalityData
                    personality_data = PersonalityData(user_id=user_id)
            
            # 构建基础系统提示
            base_system_prompt = "You are a role-playing expert. Based on the provided memory information, you will now assume the following role to chat with the user.\n" \
                + NOVA_PROMPT + "\n" + memories_str
            
            # ========== 场景化提示增强（英文注释/提示词） ==========
            scene_section = ""
            if chat_request.scene and chat_request.scene != "default":
                try:
                    from scenes import ScenePromptAdjuster
                    scene_section = ScenePromptAdjuster.build_scene_section(chat_request.scene)
                except Exception as _:
                    # If scene module is unavailable, silently skip to avoid breaking chat
                    pass
            
            # 添加场景提示词
            system_prompt = base_system_prompt + scene_section
            
            # 添加情感主题指令
            emotional_prompt = build_emotional_prompt(themes, emotional_tone)
            system_prompt = system_prompt + emotional_prompt
            
            # 根据性格档案调整系统提示
            if personality_data and personality_data.big5_assessment.is_complete(min_confidence=40):
                system_prompt = PersonalityPromptAdjuster.adjust_system_prompt(
                    system_prompt,
                    personality_data
                )
                adaptation_summary = PersonalityPromptAdjuster.get_adaptation_summary(personality_data)
                logger.info(f"Personality Adaptation | User {user_id} | {adaptation_summary}")
            
            # 在Pocket评估模式下，不进行常规聊天
            if pocket_assessment_mode:
                # 返回Pocket评估模式的特殊响应
                response = "Pocket assessment mode is active. Please use the assessment interface to continue."
                
                # 添加助手回复到聊天历史
                assistant_message_obj = {
                    "role": "assistant",
                    "content": response,
                    "time": timestamp
                }
                chat_history.append(assistant_message_obj)
            else:
                # 常规聊天模式
                # 准备发送给LLM的消息（只取最近5条消息，减少处理时间）
                messages_for_llm = [{"role": "system", "content": system_prompt}] + chat_history[-10:]
                
                # 创建LLM实例并获取响应
                llm = LlmFactory.create("openai", config=MODEL_CONFIGS[chat_request.model])
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
            
            # 打印AI回复预览到终端
            response_preview = response[:200] + "..." if len(response) > 200 else response
            print(f"[AI RESPONSE] {response_preview}\n")
            
            # 准备结果（包含情感主题和性格状态信息）
            results = {
                'response': response, 
                "used_memory": memories_str,
                "emotional_themes": {
                    "themes": themes,
                    "tone": emotional_tone
                }
            }
            
            # 添加性格状态信息
            if personality_data:
                results["personality_state"] = {
                    "total_exchanges": personality_data.total_exchanges,
                    "primary_traits": personality_data.primary_traits[:3],
                    "emotional_state": personality_data.emotional_state,
                    "assessment_complete": personality_data.big5_assessment.is_complete(min_confidence=60)
                }
            
            # 根据频率提取记忆（异步执行，不阻塞响应）
            if len(chat_history) // 2 % chat_request.frequency == 0:
                memory_msg = chat_history[-chat_request.frequency * 2:]
                if len(chat_history) > chat_request.frequency * 2 + 1:
                    memory_msg = memory_msg + [{"role": "history", "content": chat_history[-(chat_request.frequency+1) * 2: -chat_request.frequency * 2 - 1]}]
                
                # 异步执行记忆存储，不阻塞响应
                def store_memory_async():
                    try:
                        new_memory = MEMORY_INSTANCE.add(memory_msg, user_id=user_id)
                        logger.info(f"New memory added for user {user_id}: {json.dumps(new_memory, ensure_ascii=False)}")
                    except Exception as e:
                        logger.error(f"Error storing memory for user {user_id}: {e}")
                
                # 在后台线程中执行
                import threading
                threading.Thread(target=store_memory_async, daemon=True).start()
                
                results['new_memory'] = []  # 立即返回空结果
                results["graph_memory"] = {}
            
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
    
    # ========== 集成日记模块 ==========
    from diary.diary_scheduler import start_diary_scheduler, _scheduler
    from diary.diary_service import diary_service
    
    @app.on_event("startup")
    async def startup_event():
        """应用启动时初始化日记调度器"""
        # 启动定时任务：每天21:00
        start_diary_scheduler(chat_histories, hour=17, minute=40)
        logger.info("Diary scheduler initialized")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭时停止日记调度器"""
        global _scheduler
        if _scheduler:
            _scheduler.shutdown()
            logger.info("Diary scheduler stopped")
    
    @app.get("/diary/{user_id}", summary="Get user's diary")
    async def get_user_diary(user_id: str):
        """
        用户发送 /diary 指令时查看日记
        
        根据需求文档L7：若当日日记未发布，显示昨日日记
        """
        try:
            diary_data = await diary_service.get_user_diary(user_id)
            
            if diary_data:
                return diary_data
            else:
                raise HTTPException(status_code=404, detail="Diary not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error getting diary for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/diary/generate/{user_id}", summary="Manually generate diary for a user")
    async def generate_diary_manual(user_id: str):
        """
        手动生成日记（用于测试或补发）
        
        根据需求文档：若用户处于离线状态，下次登录时补发
        """
        from datetime import datetime
        
        try:
            # 获取用户的聊天历史
            chat_history = get_or_create_chat_history(user_id)
            
            if not chat_history:
                raise HTTPException(
                    status_code=400, 
                    detail=f"No chat history found for user {user_id}. Please chat with the bot first."
                )
            
            # 筛选今天的消息
            today = datetime.now().strftime("%Y-%m-%d")
            today_messages = diary_service.filter_today_messages(chat_history, today)
            
            if not today_messages:
                raise HTTPException(
                    status_code=400,
                    detail=f"No messages found for user {user_id} on {today}. Please chat with the bot today first."
                )
            
            # 生成日记
            logger.info(f"[Manual Generate] Generating diary for user {user_id} with {len(today_messages)} messages")
            diary_data = await diary_service.generate_diary(
                user_id=user_id,
                date=today,
                messages=today_messages,
                timezone="Asia/Shanghai"
            )
            
            if diary_data:
                logger.info(f"[Manual Generate] Diary generated successfully for user {user_id}")
                return {
                    "success": True,
                    "message": "Diary generated successfully",
                    "diary": diary_data
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate diary. Please check the logs for details."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error manually generating diary for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
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

import os
import concurrent
from typing import Optional, List, Any, Dict, Union
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from mem.memory.configs import MemoryConfig
from mem.memory.memory import Memory
from mem.com.factory import LlmFactory
import argparse
import uvicorn
import time
import json
import pdb
from mem.vector_stores.prompts import NOVA_PROMPT

import shortuuid
from loguru import logger
logger.add('./logs/mem.log', rotation="500 MB")


# Load environment variables
load_dotenv()

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "memory_test",
            "embedding_model_dims": 2560,
            "client": None,
            "host": "", # http://7.34.73.70:6333/collections
            "port": 6333,
            "path": "/Users/zouwuhe/Desktop/src/mem_minus/wks/qdrant",
            "url": "https://d8a17329-41df-49fc-811f-c5e762a2b12e.europe-west3-0.gcp.cloud.qdrant.io:6333",
            "api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.zyODVTAKCSNpo0cBBh6yXMlf29A8nJAaz42KTTZP2hk",
            "on_disk": False
            }
    },
    "llm": {
        "provider": "openai",
        "config": {
            "api_key": "8b2dce0f-ed36-4d2b-898a-14845cc496c1",
            #"model": "doubao-1-5-pro-32k-character-250715",
            #"model": "doubao-1-5-pro-32k-250115",
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


app = FastAPI(
    title="GameMemory REST APIs",
    description="A REST API for managing and searching memories for your AI Agents and Apps.",
    version="1.0.0",
)


class Message(BaseModel):
    role: str = Field(..., description="Role of the message (user or assistant).")
    content: Union[str, List[Dict]] = Field(..., description="Message content.")
    time: Optional[str] = None


class MemoryCreate(BaseModel):
    sid: Optional[str] = "add:" + str(shortuuid.uuid())
    messages: List[Message] = Field(..., description="List of messages to store.")
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    memory_type: Optional[str] = "vector"


class SearchRequest(BaseModel):
    sid: Optional[str] = "search:" + str(shortuuid.uuid())
    query: str = Field(..., description="Search query.")
    user_id: Optional[str] = None
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 5


class ChatRequest(BaseModel):
    sid: Optional[str] = "chat:" + str(shortuuid.uuid())
    messages: list[dict] = Field(..., description="chat history")
    user_id: str = "default_user"
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    persona: str = Field(..., description="bot persona")
    frequency: int = 1
    summary_frequency: int = 10
    model: str = "doubao"


@app.post("/configure", summary="Configure Mem0")
def set_config(config: Dict[str, Any]):
    """Set memory configuration."""
    global MEMORY_INSTANCE
    MEMORY_INSTANCE = Memory.from_config(config)
    return {"message": "Configuration set successfully"}


@app.post("/add", summary="Create memories")
def add_memory(memory_create: MemoryCreate):
    """Store new memories."""
    if not any([memory_create.user_id, memory_create.agent_id, memory_create.run_id]):
        raise HTTPException(status_code=400, detail="At least one identifier (user_id, agent_id, run_id) is required.")

    params = {k: v for k, v in memory_create.model_dump().items() if v is not None and k != "messages"}
    logger.info(f"{memory_create.sid} | ADD Memory | params: {json.dumps(params, ensure_ascii=False)}")
    try:
        t0 = time.time()
        response = MEMORY_INSTANCE.add(messages=[m.model_dump() for m in memory_create.messages], **params)
        t1 = time.time()
        logger.info(f"{memory_create.sid} | ADD Memory | time cost: {round(t1 - t0, 2)}s")
        return JSONResponse(content=response)
    except Exception as e:
        logger.exception(f"{memory_create.sid} | Error in add_memory:")  # This will log the full traceback
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories", summary="Get memories")
def get_all_memories(
    sid: Optional[str] = None,
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    type: Optional[str] = None
):
    """Retrieve stored memories."""
    if not any([user_id, run_id, agent_id]):
        raise HTTPException(status_code=400, detail="At least one identifier is required.")
    try:
        params = {
            k: v for k, v in {"user_id": user_id, "run_id": run_id, "agent_id": agent_id}.items() if v is not None
        }
        logger.info(f"{sid} | Get Memory | params: {json.dumps(params, ensure_ascii=False)}")
        if type:
            params.update({"filters": {"type": type}})
        return MEMORY_INSTANCE.get_all(**params)
    except Exception as e:
        logger.exception(f"{sid} | Error in get_all_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}", summary="Get a memory")
def get_memory(memory_id: str):
    """Retrieve a specific memory by ID."""
    try:
        return MEMORY_INSTANCE.get(memory_id)
    except Exception as e:
        logger.exception("Error in get_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search_awm", summary="Search memories")
def search_memories_awm(search_req: SearchRequest):
    """Search for memories based on a query."""
    try:
        t0 = time.time()
        params = {k: v for k, v in search_req.model_dump().items() if v is not None and k != "query"}
        logger.info(f"{search_req.sid} | Search Memory AWM | params: {json.dumps(params, ensure_ascii=False)}")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_memories = executor.submit(MEMORY_INSTANCE.search, search_req.query, **params)

            params.update({"filters": {"type": 'profile'}, "limit": 100})
            future_profile = executor.submit(MEMORY_INSTANCE.get_all, **params)

            concurrent.futures.wait([future_memories, future_profile])

            original_memories = future_memories.result()
            profile_memories = future_profile.result()

        result = {"search": original_memories, "profile": profile_memories}
        t1 = time.time()
        logger.info(f"{search_req.sid} | Search Memory AWM| time cost: {round(t1 - t0, 2)}s")
        return result
    except Exception as e:
        logger.exception(f"{search_req.sid} | Error in search_memories_awm:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", summary="Search memories")
def search_memories(search_req: SearchRequest):
    """Search for memories based on a query."""
    try:
        t0 = time.time()
        params = {k: v for k, v in search_req.model_dump().items() if v is not None and k != "query"}
        logger.info(f"{search_req.sid} | Search Memory | params: {json.dumps(params, ensure_ascii=False)}")
        result = MEMORY_INSTANCE.search(query=search_req.query, **params)
        t1 = time.time()
        logger.info(f"{search_req.sid} | Search Memory | time cost: {round(t1 - t0, 2)}s")
        return  result
    except Exception as e:
        logger.exception(f"{search_req.sid} | Error in search_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/memories/{memory_id}", summary="Update a memory")
def update_memory(memory_id: str, updated_memory: Dict[str, Any]):
    """Update an existing memory."""
    try:
        return MEMORY_INSTANCE.update(memory_id=memory_id, data=updated_memory)
    except Exception as e:
        logger.exception("Error in update_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}/history", summary="Get memory history")
def memory_history(memory_id: str):
    """Retrieve memory history."""
    try:
        return MEMORY_INSTANCE.history(memory_id=memory_id)
    except Exception as e:
        logger.exception("Error in memory_history:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memories/{memory_id}", summary="Delete a memory")
def delete_memory(memory_id: str):
    """Delete a specific memory by ID."""
    try:
        MEMORY_INSTANCE.delete(memory_id=memory_id)
        return {"message": "Memory deleted successfully"}
    except Exception as e:
        logger.exception("Error in delete_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memories", summary="Delete all memories")
def delete_all_memories(
    sid: Optional[str] = None,
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """Delete all memories for a given identifier."""
    if not any([user_id, run_id, agent_id]):
        raise HTTPException(status_code=400, detail="At least one identifier is required.")
    try:
        params = {
            k: v for k, v in {"user_id": user_id, "run_id": run_id, "agent_id": agent_id}.items() if v is not None
        }
        logger.info(f"{sid} | Delete Memory | params: {json.dumps(params, ensure_ascii=False)}")
        MEMORY_INSTANCE.delete_all(**params)
        return {"message": "All relevant memories deleted"}
    except Exception as e:
        logger.exception(f"{sid} | Error in delete_all_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset", summary="Reset all memories")
def reset_memory():
    """Completely reset stored memories."""
    try:
        MEMORY_INSTANCE.reset()
        return {"message": "All memories reset"}
    except Exception as e:
        logger.exception("Error in reset_memory:")
        raise HTTPException(status_code=500, detail=str(e))

def get_memories(chat_request: ChatRequest):
    params = {
        "user_id": chat_request.user_id,
        "run_id": chat_request.run_id,
        "agent_id": chat_request.agent_id
    }
    raw_messages = chat_request.messages
    messages = raw_messages[-10:]
    current_input = messages[-1]['content']
    logger.info(f"{chat_request.sid} | Search Memory | params: {json.dumps(params, ensure_ascii=False)}")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        params.update({"filters": {"type": 'facts'}, "limit": 3})
        future_memories = executor.submit(MEMORY_INSTANCE.search, current_input, **params)

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

        memories_facts = "\n".join(f"- {entry['memory']}" for entry in original_memories["results"])
        memories_profile = "\n".join(f"- {entry['memory']}" for entry in profile_memories["results"])
        memories_style = "\n".join(f"- {entry['memory']}" for entry in style_memories["results"])
        memories_commitments = "\n".join(f"- {entry['memory']}" for entry in commitments_memories["results"])

    result = {"facts": memories_facts, "profile": memories_profile, "style": memories_style, "commitments": memories_commitments}
    return result

@app.post("/chat", summary="get chatbot response")
def chat(chat_request: ChatRequest):
    """complete chatbot pipeline"""
    try:
        logger.info(f"{chat_request.sid} | Chat request received | user_id: {chat_request.user_id}, model: {chat_request.model}")
        raw_messages = chat_request.messages
        logger.info(f"{chat_request.sid} | Messages count: {len(raw_messages)}")
        messages = raw_messages[-10:]
        # current_input = messages[-1]['content']
        memories = get_memories(chat_request)
        logger.info(f"{chat_request.sid} | Search Memory | memories: {json.dumps(memories, ensure_ascii=False)}")

        memories_str = f"\n[memorable events]：\n{memories['facts']}" + \
            f"\n\n[player profile]：\n{memories['profile']}" + \
            f"\n\n[style notes Nova should mirror or avoid]：\n{memories['style']}" + \
            f"\n\n[tiny commitments the PLAYER made or agreed to]：\n{memories['commitments']}"
        logger.info(f"{chat_request.sid} | Search Memory | memories_str: {memories_str}")

        system_prompt = "You are a role-playing expert. Based on the provided memory information, you will now assume the following role to chat with the user.\n" \
            + NOVA_PROMPT + memories_str

        messages = [{"role": "system", "content": system_prompt}] + messages
        # llm
        config = {
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
        logger.info(f"{chat_request.sid} | Creating LLM instance for model: {chat_request.model}")
        llm = LlmFactory.create("openai", config=config[chat_request.model])
        logger.info(f"{chat_request.sid} | LLM instance created successfully")
        logger.info(f"{chat_request.sid} | Calling LLM with {len(messages)} messages")
        # MEMORY_INSTANCE.llm = llm
        # MEMORY_INSTANCE.graph.llm = llm
        response = llm.generate_response(messages=messages, response_format=None)
        logger.info(f"{chat_request.sid} | LLM response received: {response[:100]}...")
        if "：" in response[:5]:
            response = response.split("：")[1]

        # get memory
        messages.append({"role": "assistant", "content": response}) # , "time": datetime.now().strftime("%Y-%m-%d")
        if len(messages[1:]) // 2 % chat_request.frequency == 0:
            memory_msg = messages[-chat_request.frequency * 2:]
            if len(messages) > chat_request.frequency * 2 + 1:
                memory_msg = memory_msg + [{"role": "history", "content": messages[-(chat_request.frequency+1) * 2: -chat_request.frequency * 2 - 1]}]
            new_memory = MEMORY_INSTANCE.add(memory_msg, user_id=chat_request.user_id)
            results = {'response': response, 'new_memory': new_memory['results'], "used_memory": memories_str, "graph_memory": new_memory.get("relations", {})}
        else:
            results = {'response': response, "used_memory": memories_str}

        # get_summary
        raw_messages.append({"role": "assistant", "content": response}) # , "time": datetime.now().strftime("%Y-%m-%d")
        if len(raw_messages) // 2 % chat_request.summary_frequency == 0:
            summary = MEMORY_INSTANCE._create_summary(raw_messages[-chat_request.summary_frequency * 2:], user_id=chat_request.user_id)
            results["summary"] = summary
        return results

    except Exception as e:
        logger.exception(f"{chat_request.sid} | Error in chat endpoint:")
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)
def home():
    """Redirect to the OpenAPI documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port, timeout_keep_alive=5)

# nohup python mem_minus/server/server.py --port 6030 &

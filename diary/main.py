"""Diary module main program - FastAPI application"""
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
from loguru import logger

from config import settings
from models import DiaryGenerateRequest, DiaryResponse
from diary_service import diary_service
from database import init_db

# Configure logger
import os
os.makedirs("./logs", exist_ok=True)
logger.add("./logs/diary_service.log", rotation="500 MB", level="DEBUG")


# Initialize application
app = FastAPI(
    title="Diary Summary API",
    description="Independent diary summary module - for telegrambot integration",
    version="1.0.0"
)

# Initialize database
init_db()


@app.post("/diary/generate", summary="Generate diary")
async def generate_diary(
    request: DiaryGenerateRequest
):
    """
    Generate or get diary (idempotency guaranteed)
    
    Format consistent with telegrambot:
    - Receives daily memories and messages
    - Returns diary content (title + 3-6 body lines + 2 tags + button config)
    - Meets requirement document A10: ensures uniqueness via user_id+date
    """
    import asyncio
    from datetime import datetime
    
    start_time = datetime.now()
    logger.info(f"[Diary Generate] Starting diary generation for user_id={request.user_id}, date={request.date}")
    logger.debug(f"[Diary Generate] Request: {len(request.messages)} messages, memories={'provided' if request.memories else 'not provided'}")
    
    try:
        # Use asyncio.to_thread to run synchronous function in async context
        # This prevents blocking the event loop
        logger.debug(f"[Diary Generate] Calling diary_service.generate_diary in thread pool")
        result = await asyncio.to_thread(diary_service.generate_diary, request)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"[Diary Generate] Successfully generated diary for user_id={request.user_id}, date={request.date}, elapsed={elapsed:.2f}s")
        
        response_data = {
            "created": True,
            "diary": result.model_dump()
        }
        logger.debug(f"[Diary Generate] Returning response with diary data")
        # 直接返回字典，让FastAPI自动序列化，避免JSONResponse可能导致的问题
        return response_data
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.exception(
            f"[Diary Generate] Failed to generate diary for user_id={request.user_id}, date={request.date}, "
            f"elapsed={elapsed:.2f}s, error={str(e)}, error_type={type(e).__name__}"
        )
        # 确保返回有效的HTTP响应，而不是让异常传播导致502
        raise HTTPException(status_code=500, detail=f"Failed to generate diary: {str(e)}")


@app.get("/diary/today", response_model=DiaryResponse, summary="Get today's diary")
async def get_today_diary(
    user_id: str
):
    """
    Get today's diary, if not available return yesterday's diary
    
    Meets requirement document L7/L20: if today's diary not published, show yesterday's
    """
    try:
        # Call synchronous function in async context (FastAPI handles this)
        import asyncio
        result = await asyncio.to_thread(diary_service.get_today_diary, user_id)
        if result:
            return JSONResponse(
                content={
                    "source_date": result.date,
                    "diary": result.model_dump()
                }
            )
        else:
            raise HTTPException(status_code=404, detail="Diary not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting diary for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get diary: {str(e)}")


# Demo frontend page (for development/testing)
@app.get("/", response_class=HTMLResponse)
async def demo_page():
    """Demo page - automatically loads mock data and displays"""
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diary Demo - 日记总结功能演示</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        .diary-card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            margin-bottom: 20px;
        }
        .diary-title {
            font-size: 2em;
            color: #667eea;
            margin-bottom: 20px;
            font-weight: 600;
        }
        .diary-body {
            font-size: 1.1em;
            line-height: 1.8;
            color: #333;
            margin-bottom: 20px;
        }
        .diary-body-line {
            margin-bottom: 12px;
        }
        .diary-tags {
            display: flex;
            gap: 10px;
            margin-bottom: 25px;
        }
        .tag {
            background: #f0f0f0;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.9em;
            color: #667eea;
            font-weight: 500;
        }
        .diary-buttons {
            display: flex;
            gap: 15px;
        }
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 25px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 500;
        }
        .btn-save {
            background: #667eea;
            color: white;
        }
        .btn-save:hover {
            background: #5568d3;
            transform: translateY(-2px);
        }
        .btn-reply {
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
        }
        .btn-reply:hover {
            background: #f5f5f5;
            transform: translateY(-2px);
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: white;
            font-size: 1.2em;
        }
        .error {
            background: #ff6b6b;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .info {
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📔 Diary Demo</h1>
            <p>Diary Summary Feature Demo</p>
        </div>
        
        <div class="info">
            💡 The page will automatically load mock data and generate diary after loading
        </div>
        
        <div id="diary-container">
            <div class="loading">Generating diary...</div>
        </div>
    </div>

    <script>
        const API_BASE = window.location.origin;

        // Load mock data and generate diary
        async function loadAndGenerateDiary() {
            try {
                // Load mock data
                const response = await fetch('/mock_memory.json');
                const mockData = await response.json();
                
                // Call generation API
                const generateResponse = await fetch('/diary/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(mockData)
                });
                
                if (!generateResponse.ok) {
                    throw new Error('Failed to generate diary');
                }
                
                const result = await generateResponse.json();
                const diary = result.diary;
                
                // Render diary card
                renderDiary(diary);
                
            } catch (error) {
                document.getElementById('diary-container').innerHTML = `
                    <div class="error">
                        <strong>Error:</strong>${error.message}<br>
                        Please ensure the backend service is running.
                    </div>
                `;
            }
        }
        
        function renderDiary(diary) {
            const container = document.getElementById('diary-container');
            const bodyLinesHtml = diary.body_lines.map(line => 
                `<div class="diary-body-line">${line}</div>`
            ).join('');
            
            const tagsHtml = diary.tags.map(tag => 
                `<span class="tag">#${tag}</span>`
            ).join('');
            
            container.innerHTML = `
                <div class="diary-card">
                    <div class="diary-title">${diary.title}</div>
                    <div class="diary-body">
                        ${bodyLinesHtml}
                    </div>
                    <div class="diary-tags">
                        ${tagsHtml}
                    </div>
                    <div class="diary-buttons">
                        <button class="btn btn-save">♥ Save</button>
                        <button class="btn btn-reply">↩ Reply</button>
                    </div>
                </div>
            `;
            
            // Button click events (demo only)
            document.querySelector('.btn-save').addEventListener('click', () => {
                alert('Save function (demo)');
            });
            document.querySelector('.btn-reply').addEventListener('click', () => {
                alert('Reply function (demo)');
            });
        }
        
        // Auto-execute on page load
        window.addEventListener('load', loadAndGenerateDiary);
    </script>
</body>
</html>
"""
    return html_content


# Provide static file (mock_memory.json)
@app.get("/mock_memory.json")
async def get_mock_memory():
    """Return mock memory data"""
    mock_file = Path(__file__).parent / "mock_memory.json"
    with open(mock_file, "r", encoding="utf-8") as f:
        return json.loads(f.read())


if __name__ == "__main__":
    import uvicorn
    import os
    # 生产环境关闭reload，避免reload时导致502错误
    # 开发环境可以通过环境变量 DIARY_RELOAD=true 启用reload
    enable_reload = os.getenv("DIARY_RELOAD", "false").lower() == "true"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=enable_reload
    )


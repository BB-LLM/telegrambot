"""
Soul MVP主应用
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api.routes_style import router as style_router
from app.api.routes_health import router as health_router
from app.api.routes_image import router as image_router
from app.api.routes_static import router as static_router, setup_static_files
from app.api.routes_tasks import router as tasks_router
from app.api.routes_video import router as video_router
from app.api.routes_wan_video import router as wan_video_router
from app.config import config
from app.data.dal import get_db

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 禁用uvicorn的访问日志
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Soul MVP应用启动中...")
    
    # 检查数据库连接
    try:
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("SELECT 1"))
        logger.info("数据库连接正常")
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise
    
    yield
    
    # 关闭时执行
    logger.info("Soul MVP应用关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title="Soul MVP",
    description="基于AI的Soul角色图像生成系统",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（必须在挂载静态文件之前注册，确保路由优先级）
app.include_router(style_router)
app.include_router(health_router)
app.include_router(image_router)
app.include_router(static_router)  # 静态文件路由必须在挂载之前注册
app.include_router(tasks_router)
app.include_router(video_router)
app.include_router(wan_video_router)

# 设置静态文件服务（挂载必须在路由之后，避免覆盖路由）
setup_static_files(app)


@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    from fastapi.responses import FileResponse
    import os
    
    # 返回前端页面
    frontend_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    else:
        return {
            "message": "Soul MVP API",
            "version": "1.0.0",
            "status": "running",
            "environment": config.ENVIRONMENT,
            "note": "前端页面未找到，请检查static/index.html文件"
        }


@app.get("/wan-video")
async def wan_video_page():
    """Wan视频生成页面"""
    from fastapi.responses import FileResponse
    import os
    
    # 返回Wan视频生成页面
    frontend_path = os.path.join(os.path.dirname(__file__), "static", "wan_video.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    else:
        return {
            "message": "Wan Video Page Not Found",
            "note": "请检查static/wan_video.html文件"
        }


@app.get("/info")
async def app_info():
    """应用信息"""
    return {
        "name": "Soul MVP",
        "version": "1.0.0",
        "environment": config.ENVIRONMENT,
        "debug": config.DEBUG,
        "database_url": config.DATABASE_URL.split("@")[-1] if "@" in config.DATABASE_URL else "hidden",
        "gcs_bucket": config.GCS_BUCKET_NAME,
        "features": [
            "Soul风格图像生成",
            "提示词缓存",
            "用户唯一交付",
            "自拍多样性",
            "LWW数据语义"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )

# python -m uvicorn main:app --host 0.0.0.0 --port 8888 --reload
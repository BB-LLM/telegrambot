#!/usr/bin/env python3
"""
Soul MVP 启动脚本
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn
    from app.config import config
    
    print("启动Soul MVP服务器...")
    print(f"项目根目录: {project_root}")
    print(f"API地址: http://{config.API_HOST}:{config.API_PORT}")
    print(f"前端页面: http://localhost:{config.API_PORT}")
    print(f"API文档: http://localhost:{config.API_PORT}/docs")
    
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )

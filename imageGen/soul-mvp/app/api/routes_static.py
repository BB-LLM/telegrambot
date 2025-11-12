"""
静态文件服务 - 提供生成的图像
"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

router = APIRouter(prefix="/static", tags=["静态文件"])

# 生成图像目录
GENERATED_IMAGES_DIR = "generated_images"
# 生成视频目录
GENERATED_VIDEOS_DIR = "generated_videos"


@router.get("/image/{filename}")
async def get_generated_image(filename: str):
    """
    获取生成的图像文件
    
    Args:
        filename: 文件名
        
    Returns:
        图像文件
    """
    file_path = Path(GENERATED_IMAGES_DIR) / filename
    
    # 检查文件是否存在
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"图像文件不存在: {filename}"
        )
    
    # 检查文件扩展名
    if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的文件类型"
        )
    
    return FileResponse(
        path=str(file_path),
        media_type="image/png" if filename.lower().endswith('.png') else "image/jpeg",
        filename=filename
    )


@router.get("/videos/{filename}")
async def get_generated_video(filename: str):
    """
    获取生成的视频文件（MP4或GIF）
    
    Args:
        filename: 文件名
        
    Returns:
        视频文件
    """
    file_path = Path(GENERATED_VIDEOS_DIR) / filename
    
    # 检查文件是否存在
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"视频文件不存在: {filename}"
        )
    
    # 检查文件扩展名
    if not filename.lower().endswith(('.mp4', '.gif')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的文件类型，仅支持MP4和GIF"
        )
    
    # 确定媒体类型
    if filename.lower().endswith('.mp4'):
        media_type = "video/mp4"
    else:
        media_type = "image/gif"
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename
    )


@router.get("/images")
async def list_generated_images():
    """
    列出所有生成的图像文件
    
    Returns:
        图像文件列表
    """
    images_dir = Path(GENERATED_IMAGES_DIR)
    
    if not images_dir.exists():
        return {"images": [], "total_count": 0}
    
    image_files = []
    for file_path in images_dir.glob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
            stat = file_path.stat()
            image_files.append({
                "filename": file_path.name,
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime
            })
    
    # 按修改时间排序
    image_files.sort(key=lambda x: x["modified_at"], reverse=True)
    
    return {
        "images": image_files,
        "total_count": len(image_files)
    }


def setup_static_files(app):
    """
    设置静态文件服务
    
    Args:
        app: FastAPI应用实例
    """
    # 确保目录存在
    os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)
    os.makedirs(GENERATED_VIDEOS_DIR, exist_ok=True)
    
    # 挂载前端静态文件目录
    # 注意：不要挂载 /static/videos，使用路由 /static/video/{filename} 来处理视频文件
    static_dir = Path(__file__).parent.parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # 单独挂载生成图像目录
    app.mount("/generated", StaticFiles(directory=GENERATED_IMAGES_DIR), name="generated")

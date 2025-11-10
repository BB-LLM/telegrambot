# PowerShell启动脚本（Windows）
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  启动日记总结模块" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否在正确目录
if (-not (Test-Path "main.py")) {
    Write-Host "错误: 请在 diary 目录下运行此脚本！" -ForegroundColor Red
    Write-Host "当前目录: $(Get-Location)" -ForegroundColor Yellow
    pause
    exit 1
}

# 检查环境变量文件
if (-not (Test-Path ".env")) {
    Write-Host "警告: 未找到 .env 文件，将使用默认配置" -ForegroundColor Yellow
    Write-Host "建议: 复制 .env.example 为 .env 并修改配置" -ForegroundColor Yellow
    Write-Host ""
}

# 检查数据库目录
if (-not (Test-Path "diary.db")) {
    Write-Host "数据库将在首次运行时创建" -ForegroundColor Green
}

Write-Host "正在启动服务..." -ForegroundColor Green
Write-Host ""
Write-Host "访问地址:" -ForegroundColor Cyan
Write-Host "  - Demo页面: http://localhost:8083/" -ForegroundColor White
Write-Host "  - API文档:   http://localhost:8083/docs" -ForegroundColor White
Write-Host "  - 健康检查: http://localhost:8083/diary/healthz" -ForegroundColor White
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 启动服务
python main.py


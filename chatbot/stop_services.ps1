# ========================================
# 停止聊天机器人服务脚本
# ========================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  停止聊天机器人服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 查找并停止后端服务
Write-Host "[1/2] 停止后端服务 (chat_server.py)..." -ForegroundColor Yellow
$backendProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*chat_server.py*"
}

if ($backendProcesses) {
    foreach ($proc in $backendProcesses) {
        Write-Host "  停止进程 PID: $($proc.Id)" -ForegroundColor Gray
        Stop-Process -Id $proc.Id -Force
    }
    Write-Host "  ✓ 后端服务已停止" -ForegroundColor Green
} else {
    Write-Host "  未找到运行中的后端服务" -ForegroundColor Gray
}

# 查找并停止前端服务
Write-Host ""
Write-Host "[2/2] 停止前端服务 (Streamlit)..." -ForegroundColor Yellow
$frontendProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*streamlit*"
}

if ($frontendProcesses) {
    foreach ($proc in $frontendProcesses) {
        Write-Host "  停止进程 PID: $($proc.Id)" -ForegroundColor Gray
        Stop-Process -Id $proc.Id -Force
    }
    Write-Host "  ✓ 前端服务已停止" -ForegroundColor Green
} else {
    Write-Host "  未找到运行中的前端服务" -ForegroundColor Gray
}

# 额外检查端口占用
Write-Host ""
Write-Host "检查端口占用..." -ForegroundColor Yellow

$ports = @(8081, 8082)
foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        $processId = $connection.OwningProcess
        Write-Host "  端口 $port 仍被进程 $processId 占用，尝试停止..." -ForegroundColor Yellow
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "  ✓ 端口 $port 已释放" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✓ 所有服务已停止" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "按任意键关闭此窗口..." -ForegroundColor Gray
pause


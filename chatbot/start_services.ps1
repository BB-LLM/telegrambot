Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Chatbot Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if in correct directory
if (-not (Test-Path "server\chat_server.py")) {
    Write-Host "Error: Please run this script from project root directory!" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    pause
    exit 1
}

# Check and create necessary directories
Write-Host "[1/3] Checking directories..." -ForegroundColor Green
$directories = @("logs", "wks\qdrant")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        Write-Host "  Creating directory: $dir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    } else {
        Write-Host "  Directory exists: $dir" -ForegroundColor Gray
    }
}

# Set environment variables
Write-Host ""
Write-Host "[2/3] Setting environment variables..." -ForegroundColor Green
$env:PYTHONPATH = "."
Write-Host "  PYTHONPATH = ." -ForegroundColor Gray

# Get current directory
$currentDir = Get-Location

# Start services
Write-Host ""
Write-Host "[3/3] Starting services..." -ForegroundColor Green
Write-Host ""

# Start backend service (new window)
Write-Host "  Starting backend API service (port 8082)..." -ForegroundColor Cyan
$backendCmd = "cd '$currentDir'; `$env:PYTHONPATH='.'; conda activate mem_minus; python server\chat_server.py --port 8082"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Wait for backend to start
Write-Host "  Waiting for backend service..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Start frontend service (new window)
Write-Host "  Starting frontend Streamlit UI (port 8081)..." -ForegroundColor Cyan
$frontendCmd = "cd '$currentDir'; conda activate mem_minus; streamlit run server\app.py --server.fileWatcherType none --server.port 8081"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# Wait for frontend to start
Write-Host "  Waiting for frontend service..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Services Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:8081" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8082/docs" -ForegroundColor White
Write-Host ""
Write-Host "Tips:" -ForegroundColor Yellow
Write-Host "  - Two service windows have been opened" -ForegroundColor Gray
Write-Host "  - Close windows or press Ctrl+C to stop services" -ForegroundColor Gray
Write-Host "  - Browser will open automatically" -ForegroundColor Gray
Write-Host ""

# Open browser
Start-Sleep -Seconds 2
Write-Host "Opening browser..." -ForegroundColor Cyan
Start-Process "http://localhost:8081"

Write-Host ""
Write-Host "Press any key to close this window..." -ForegroundColor Gray
pause


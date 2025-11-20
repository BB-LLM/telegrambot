#!/bin/bash

################################################################################
# diaryGen 一键启动脚本
# 功能: 启动 diaryGen 服务，所有输出写入日志文件
# 用法: ./start_diaryGen.sh
################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_DIR="/home/zouwuhe/telegrambot/diaryGen"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/diaryGen_$(date +%Y%m%d_%H%M%S).log"
VENV_DIR="/home/zouwuhe/telegrambot/bot"
API_PORT=8083

# 创建日志目录
mkdir -p "$LOG_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  diaryGen 服务启动${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 错误: 项目目录不存在: $PROJECT_DIR${NC}"
    exit 1
fi

echo -e "${YELLOW}📁 项目目录: $PROJECT_DIR${NC}"
echo -e "${YELLOW}🐍 虚拟环境: $VENV_DIR${NC}"
echo -e "${YELLOW}📝 日志文件: $LOG_FILE${NC}"
echo ""

# 检查虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ 错误: 虚拟环境不存在: $VENV_DIR${NC}"
    exit 1
fi

# 进入项目目录
cd "$PROJECT_DIR"

# 检查并清理端口 8083
echo -e "${YELLOW}🔍 检查端口 $API_PORT 是否被占用...${NC}"
EXISTING_PIDS=$(lsof -ti :$API_PORT 2>/dev/null || true)

if [ -n "$EXISTING_PIDS" ]; then
    echo -e "${YELLOW}⚠️  发现端口 $API_PORT 已被占用，正在清理旧进程...${NC}"
    for PID in $EXISTING_PIDS; do
        PROCESS_INFO=$(ps -p $PID -o cmd --no-headers 2>/dev/null || echo "未知进程")
        echo -e "${YELLOW}  停止进程 $PID: $PROCESS_INFO${NC}"
        kill -9 $PID 2>/dev/null || true
    done
    sleep 1
    echo -e "${GREEN}✅ 旧进程已清理${NC}"
else
    echo -e "${GREEN}✅ 端口 $API_PORT 可用${NC}"
fi
echo ""

# 初始化日志文件
echo "启动时间: $(date)" > "$LOG_FILE"
echo "虚拟环境: $VENV_DIR" >> "$LOG_FILE"
echo "项目目录: $PROJECT_DIR" >> "$LOG_FILE"
echo "服务端口: $API_PORT" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 启动服务（后台运行）
echo -e "${YELLOW}🚀 启动 diaryGen 服务 (port $API_PORT)...${NC}"

# 激活虚拟环境并启动服务（不使用临时脚本，避免被删除导致进程异常）
source "$VENV_DIR/bin/activate" 2>/dev/null || {
    echo -e "${RED}❌ 错误: 无法激活虚拟环境 '$VENV_DIR'${NC}"
    exit 1
}

# 设置环境变量，禁用 reload 模式
export DIARY_RELOAD=false

# 后台启动服务（使用 setsid 确保完全从终端分离）
setsid nohup python main.py >> "$LOG_FILE" 2>&1 &
SERVICE_PID=$!

# 等待服务启动
sleep 2

# 检查进程是否还在运行
if ! kill -0 $SERVICE_PID 2>/dev/null; then
    echo -e "${RED}❌ 服务启动失败！${NC}"
    echo -e "${RED}请查看日志: $LOG_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ diaryGen 服务已启动${NC}"
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  服务信息${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}进程号 (PID): $SERVICE_PID${NC}"
echo -e "${GREEN}服务地址: http://36.138.179.204:$API_PORT${NC}"
echo -e "${GREEN}API 文档: http://36.138.179.204:$API_PORT/docs${NC}"
echo -e "${GREEN}日志文件: $LOG_FILE${NC}"
echo ""
echo -e "${YELLOW}💡 提示:${NC}"
echo -e "  - 查看实时日志: tail -f $LOG_FILE"
echo -e "  - 停止服务: kill $SERVICE_PID"
echo -e "  - 查看进程: ps aux | grep $SERVICE_PID"
echo ""

# 保存进程号到文件
echo "$SERVICE_PID" > "${LOG_DIR}/diaryGen.pid"

echo -e "${GREEN}✨ 启动完成！${NC}"


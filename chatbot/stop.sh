#!/bin/bash

################################################################################
# chatbot 停止脚本
# 功能: 停止所有 chatbot 服务并清理资源
# 用法: ./stop.sh
################################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="/home/hongxda/telegrambot/chatbot"
LOG_DIR="/home/hongxda/telegrambot/logs"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  chatbot 服务停止${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 读取进程号文件
BACKEND_PID=""
FRONTEND_PID=""

if [ -f "${LOG_DIR}/chatbot_backend.pid" ]; then
    BACKEND_PID=$(cat "${LOG_DIR}/chatbot_backend.pid")
fi

if [ -f "${LOG_DIR}/chatbot_frontend.pid" ]; then
    FRONTEND_PID=$(cat "${LOG_DIR}/chatbot_frontend.pid")
fi

# 停止后端服务
if [ -n "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${YELLOW}🛑 停止后端服务 (PID: $BACKEND_PID)...${NC}"
    kill -9 $BACKEND_PID 2>/dev/null
    sleep 1
    echo -e "${GREEN}✅ 后端服务已停止${NC}"
else
    echo -e "${YELLOW}⚠️  后端服务未运行${NC}"
fi

# 停止前端服务
if [ -n "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${YELLOW}🛑 停止前端服务 (PID: $FRONTEND_PID)...${NC}"
    kill -9 $FRONTEND_PID 2>/dev/null
    sleep 1
    echo -e "${GREEN}✅ 前端服务已停止${NC}"
else
    echo -e "${YELLOW}⚠️  前端服务未运行${NC}"
fi

# 杀死所有相关进程（以防万一）
echo -e "${YELLOW}🧹 清理所有相关进程...${NC}"
pkill -f "python server/chat_server.py" 2>/dev/null || true
pkill -f "streamlit run server/app.py" 2>/dev/null || true
sleep 1

# 清理 Qdrant 锁定文件
echo -e "${YELLOW}🧹 清理 Qdrant 锁定文件...${NC}"
cd "$PROJECT_DIR"
rm -rf ./wks/qdrant/.lock 2>/dev/null || true

# 清理 PID 文件
rm -f "${LOG_DIR}/chatbot_backend.pid" "${LOG_DIR}/chatbot_frontend.pid"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✨ 所有服务已停止！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}💡 提示:${NC}"
echo -e "  - 重新启动: ./start.sh"
echo -e "  - 查看日志: tail -f /home/hongxda/telegrambot/logs/chatbot_backend_*.log"
echo ""


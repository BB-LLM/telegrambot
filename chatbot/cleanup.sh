#!/bin/bash

################################################################################
# chatbot 清理脚本
# 功能: 彻底清理所有旧进程、锁定文件和临时文件
# 用法: ./cleanup.sh
################################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="/home/hongxda/telegrambot/chatbot"
LOG_DIR="/home/hongxda/telegrambot/chatbot/logs"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  chatbot 完整清理${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 杀死所有相关进程
echo -e "${YELLOW}🛑 杀死所有相关进程...${NC}"
pkill -9 -f "python server/chat_server.py" 2>/dev/null || true
pkill -9 -f "streamlit run server/app.py" 2>/dev/null || true
pkill -9 -f "python main.py" 2>/dev/null || true
sleep 2
echo -e "${GREEN}✅ 进程已清理${NC}"

# 2. 清理 Qdrant 锁定文件
echo -e "${YELLOW}🧹 清理 Qdrant 锁定文件...${NC}"
cd "$PROJECT_DIR"
rm -rf ./wks/qdrant/.lock 2>/dev/null || true
echo -e "${GREEN}✅ Qdrant 锁定文件已清理${NC}"

# 3. 清理 PID 文件
echo -e "${YELLOW}🧹 清理 PID 文件...${NC}"
rm -f "${LOG_DIR}/chatbot_backend.pid" "${LOG_DIR}/chatbot_frontend.pid" 2>/dev/null || true
echo -e "${GREEN}✅ PID 文件已清理${NC}"

# 4. 清理临时文件
echo -e "${YELLOW}🧹 清理临时文件...${NC}"
rm -f /tmp/start_chatbot_*.sh 2>/dev/null || true
echo -e "${GREEN}✅ 临时文件已清理${NC}"

# 5. 验证清理结果
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  清理结果验证${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}检查运行中的进程:${NC}"
if ps aux | grep -E "python server/chat_server.py|streamlit run server/app.py" | grep -v grep > /dev/null; then
    echo -e "${RED}❌ 仍有进程在运行${NC}"
    ps aux | grep -E "python server/chat_server.py|streamlit run server/app.py" | grep -v grep
else
    echo -e "${GREEN}✅ 所有进程已清理${NC}"
fi

echo ""
echo -e "${YELLOW}检查 Qdrant 锁定文件:${NC}"
if [ -f "./wks/qdrant/.lock" ]; then
    echo -e "${RED}❌ Qdrant 锁定文件仍存在${NC}"
else
    echo -e "${GREEN}✅ Qdrant 锁定文件已清理${NC}"
fi

echo ""
echo -e "${YELLOW}检查 Qdrant 占用情况:${NC}"
if lsof +D ./wks/qdrant 2>/dev/null | grep -v "COMMAND" > /dev/null; then
    echo -e "${RED}❌ Qdrant 仍被占用${NC}"
    lsof +D ./wks/qdrant 2>/dev/null
else
    echo -e "${GREEN}✅ Qdrant 已释放${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✨ 清理完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}💡 接下来:${NC}"
echo -e "  - 启动服务: ./start.sh"
echo ""


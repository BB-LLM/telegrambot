#!/bin/bash

################################################################################
# chatbot 一键启动脚本
# 功能: 启动 chatbot 后端和前端服务，所有输出写入日志文件
# 用法: ./start_chatbot.sh
################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_DIR="/home/zouwuhe/telegrambot/chatbot"
LOG_DIR="/home/zouwuhe/telegrambot/logs"
LOG_FILE_BACKEND="${LOG_DIR}/chatbot_backend_$(date +%Y%m%d_%H%M%S).log"
LOG_FILE_FRONTEND="${LOG_DIR}/chatbot_frontend_$(date +%Y%m%d_%H%M%S).log"
VENV_DIR="/home/zouwuhe/telegrambot/bot"
BACKEND_PORT=8082
FRONTEND_PORT=8081

# 创建日志目录
mkdir -p "$LOG_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  chatbot 服务启动${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 错误: 项目目录不存在: $PROJECT_DIR${NC}"
    exit 1
fi

echo -e "${YELLOW}📁 项目目录: $PROJECT_DIR${NC}"
echo -e "${YELLOW}🐍 虚拟环境: $VENV_DIR${NC}"
echo -e "${YELLOW}📝 后端日志: $LOG_FILE_BACKEND${NC}"
echo -e "${YELLOW}📝 前端日志: $LOG_FILE_FRONTEND${NC}"
echo ""

# 检查虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ 错误: 虚拟环境不存在: $VENV_DIR${NC}"
    exit 1
fi

# 进入项目目录
cd "$PROJECT_DIR"

# 清理旧的 Qdrant 锁定文件
echo -e "${YELLOW}🧹 清理旧的 Qdrant 锁定文件...${NC}"
rm -rf ./wks/qdrant/.lock 2>/dev/null || true

# 杀死所有旧的 chatbot 进程
echo -e "${YELLOW}🧹 清理旧的 chatbot 进程...${NC}"
pkill -f "python server/chat_server.py" 2>/dev/null || true
pkill -f "streamlit run server/app.py" 2>/dev/null || true
sleep 2

# 初始化日志文件
echo "启动时间: $(date)" > "$LOG_FILE_BACKEND"
echo "虚拟环境: $VENV_DIR" >> "$LOG_FILE_BACKEND"
echo "项目目录: $PROJECT_DIR" >> "$LOG_FILE_BACKEND"
echo "服务: chatbot 后端 (port $BACKEND_PORT)" >> "$LOG_FILE_BACKEND"
echo "========================================" >> "$LOG_FILE_BACKEND"
echo "" >> "$LOG_FILE_BACKEND"

echo "启动时间: $(date)" > "$LOG_FILE_FRONTEND"
echo "虚拟环境: $VENV_DIR" >> "$LOG_FILE_FRONTEND"
echo "项目目录: $PROJECT_DIR" >> "$LOG_FILE_FRONTEND"
echo "服务: chatbot 前端 (port $FRONTEND_PORT)" >> "$LOG_FILE_FRONTEND"
echo "========================================" >> "$LOG_FILE_FRONTEND"
echo "" >> "$LOG_FILE_FRONTEND"

echo -e "${YELLOW}🔧 虚拟环境已就绪${NC}"

# 设置环境变量
export PYTHONPATH="."

# 创建临时启动脚本 - 后端
TEMP_BACKEND="/tmp/start_chatbot_backend_$$.sh"
cat > "$TEMP_BACKEND" << 'SCRIPT_EOF'
#!/bin/bash
source "$1/bin/activate"
cd "$2"
export PYTHONPATH="."
python server/chat_server.py --port "$3"
SCRIPT_EOF
chmod +x "$TEMP_BACKEND"

# 创建临时启动脚本 - 前端
TEMP_FRONTEND="/tmp/start_chatbot_frontend_$$.sh"
cat > "$TEMP_FRONTEND" << 'SCRIPT_EOF'
#!/bin/bash
source "$1/bin/activate"
cd "$2"
streamlit run server/app.py --server.fileWatcherType none --server.port "$3"
SCRIPT_EOF
chmod +x "$TEMP_FRONTEND"

# 启动后端服务
echo -e "${YELLOW}🚀 启动 chatbot 后端服务 (port $BACKEND_PORT)...${NC}"
bash "$TEMP_BACKEND" "$VENV_DIR" "$PROJECT_DIR" "$BACKEND_PORT" >> "$LOG_FILE_BACKEND" 2>&1 &
BACKEND_PID=$!

# 等待后端启动（Qdrant 初始化需要更多时间）
echo -e "${YELLOW}⏳ 等待后端服务初始化...${NC}"
sleep 5

# 检查后端进程
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}❌ 后端服务启动失败！${NC}"
    echo -e "${RED}请查看日志: $LOG_FILE_BACKEND${NC}"
    echo -e "${RED}最后 20 行日志:${NC}"
    tail -20 "$LOG_FILE_BACKEND"
    rm -f "$TEMP_BACKEND" "$TEMP_FRONTEND"
    exit 1
fi

echo -e "${GREEN}✅ 后端服务已启动 (PID: $BACKEND_PID)${NC}"

# 启动前端服务
echo -e "${YELLOW}🚀 启动 chatbot 前端服务 (port $FRONTEND_PORT)...${NC}"
bash "$TEMP_FRONTEND" "$VENV_DIR" "$PROJECT_DIR" "$FRONTEND_PORT" >> "$LOG_FILE_FRONTEND" 2>&1 &
FRONTEND_PID=$!

# 清理临时脚本（后台）
(sleep 5 && rm -f "$TEMP_BACKEND" "$TEMP_FRONTEND") &

# 等待前端启动
echo -e "${YELLOW}⏳ 等待前端服务初始化...${NC}"
sleep 5

# 检查前端进程
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}❌ 前端服务启动失败！${NC}"
    echo -e "${RED}请查看日志: $LOG_FILE_FRONTEND${NC}"
    echo -e "${RED}最后 20 行日志:${NC}"
    tail -20 "$LOG_FILE_FRONTEND"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}✅ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  服务信息${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}后端进程号 (PID): $BACKEND_PID${NC}"
echo -e "${GREEN}前端进程号 (PID): $FRONTEND_PID${NC}"
echo ""
echo -e "${GREEN}后端地址: http://36.138.179.204:$BACKEND_PORT${NC}"
echo -e "${GREEN}后端文档: http://36.138.179.204:$BACKEND_PORT/docs${NC}"
echo ""
echo -e "${GREEN}前端地址: http://36.138.179.204:$FRONTEND_PORT${NC}"
echo ""
echo -e "${GREEN}后端日志: $LOG_FILE_BACKEND${NC}"
echo -e "${GREEN}前端日志: $LOG_FILE_FRONTEND${NC}"
echo ""
echo -e "${YELLOW}💡 提示:${NC}"
echo -e "  - 查看后端日志: tail -f $LOG_FILE_BACKEND"
echo -e "  - 查看前端日志: tail -f $LOG_FILE_FRONTEND"
echo -e "  - 停止后端: kill $BACKEND_PID"
echo -e "  - 停止前端: kill $FRONTEND_PID"
echo -e "  - 停止所有: kill $BACKEND_PID $FRONTEND_PID"
echo ""

# 保存进程号到文件
echo "$BACKEND_PID" > "${LOG_DIR}/chatbot_backend.pid"
echo "$FRONTEND_PID" > "${LOG_DIR}/chatbot_frontend.pid"

echo -e "${GREEN}✨ 启动完成！${NC}"


#!/bin/bash

################################################################################
# diaryGen 停止脚本
# 功能: 停止 diaryGen 服务（杀掉端口 8083 的所有进程）
# 用法: ./stop.sh
################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
API_PORT=8083

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  停止 diaryGen 服务${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 查找占用端口的进程
echo -e "${YELLOW}🔍 查找占用端口 $API_PORT 的进程...${NC}"
PIDS=$(lsof -ti :$API_PORT 2>/dev/null || true)

if [ -z "$PIDS" ]; then
    echo -e "${GREEN}✅ 端口 $API_PORT 没有被占用${NC}"
    exit 0
fi

# 显示找到的进程
echo -e "${YELLOW}找到以下进程:${NC}"
for PID in $PIDS; do
    PROCESS_INFO=$(ps -p $PID -o pid,cmd --no-headers 2>/dev/null || echo "$PID (进程已结束)")
    echo -e "  ${YELLOW}PID: $PROCESS_INFO${NC}"
done
echo ""

# 杀掉进程
echo -e "${YELLOW}🔪 正在停止进程...${NC}"
for PID in $PIDS; do
    if kill -9 $PID 2>/dev/null; then
        echo -e "${GREEN}✅ 已停止进程 $PID${NC}"
    else
        echo -e "${RED}⚠️  无法停止进程 $PID (可能已结束)${NC}"
    fi
done

# 等待进程完全结束
sleep 1

# 再次检查
REMAINING=$(lsof -ti :$API_PORT 2>/dev/null || true)
if [ -z "$REMAINING" ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  diaryGen 服务已成功停止${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  警告: 仍有进程占用端口 $API_PORT${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi


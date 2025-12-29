#!/bin/bash
# ==============================================
# Rosetta 每日重启脚本
# 功能：检查代码更新并重启容器
# 建议定时执行：每天凌晨3点
# ==============================================

# 配置参数
GIT_REPO="https://github.com/HY-LiYihan/rosetta.git"
LOCAL_DIR="/opt/streamlit/rosetta"
DOCKER_CONTAINER="rosetta-app"  # 修改为实际的容器名称

# ==============================================
# 核心逻辑
# ==============================================
echo "===== Rosetta 每日重启脚本开始执行：$(date '+%Y-%m-%d %H:%M:%S') ====="

# 1. 进入本地代码目录（若目录不存在则克隆）
if [ ! -d "$LOCAL_DIR" ]; then
  echo "❌ 错误：本地目录 $LOCAL_DIR 不存在！"
  echo "请先运行部署脚本或手动克隆仓库。"
  exit 1
else
  echo "进入本地目录：$LOCAL_DIR"
  cd "$LOCAL_DIR" || exit 1
fi

# 2. 检查容器是否存在
if ! docker ps -a --format '{{.Names}}' | grep -q "^$DOCKER_CONTAINER$"; then
  echo "❌ 错误：容器 $DOCKER_CONTAINER 不存在！"
  echo "请先启动容器：docker-compose up -d"
  exit 1
fi

# 3. 检查容器是否正在运行
if ! docker ps --format '{{.Names}}' | grep -q "^$DOCKER_CONTAINER$"; then
  echo "⚠️ 警告：容器 $DOCKER_CONTAINER 已停止，正在启动..."
  docker start "$DOCKER_CONTAINER"
  if [ $? -eq 0 ]; then
    echo "✅ 容器启动成功！"
  else
    echo "❌ 容器启动失败！"
    exit 1
  fi
  exit 0
fi

# 4. 【关键修改】在拉取前，先记录当前的提交ID
echo "正在检查当前版本..."
BEFORE_PULL=$(git rev-parse HEAD 2>/dev/null)

# 5. 拉取远程最新代码
echo "拉取远程最新代码..."
# 使用 fetch + reset --hard 模式，比 git pull 更适合自动部署（防止本地冲突）
git fetch origin main
git reset --hard origin/main

# 6. 获取拉取后的提交ID
AFTER_PULL=$(git rev-parse HEAD 2>/dev/null)

# 7. 对比 ID
echo "更新前版本: ${BEFORE_PULL:0:8}"
echo "更新后版本: ${AFTER_PULL:0:8}"

if [ "$BEFORE_PULL" != "$AFTER_PULL" ]; then
  echo "检测到代码变更，正在重启 Streamlit 容器..."
  docker restart "$DOCKER_CONTAINER"
  if [ $? -eq 0 ]; then
    echo "✅ 容器重启成功！"
  else
    echo "❌ 容器重启失败，请检查容器名称 [$DOCKER_CONTAINER] 是否正确！"
    exit 1
  fi
else
  echo "⚪ 代码无更新，执行每日例行重启..."
  docker restart "$DOCKER_CONTAINER"
  if [ $? -eq 0 ]; then
    echo "✅ 容器每日重启成功！"
  else
    echo "❌ 容器重启失败！"
    exit 1
  fi
fi

# 8. 验证容器状态
echo "等待容器启动..."
sleep 5
if docker ps --format '{{.Names}}' | grep -q "^$DOCKER_CONTAINER$"; then
  echo "✅ 容器运行状态正常"
else
  echo "❌ 容器未运行，请检查日志：docker logs $DOCKER_CONTAINER"
  exit 1
fi

echo "===== 脚本执行结束：$(date '+%Y-%m-%d %H:%M:%S') ====="
echo "--------------------------------------------------"

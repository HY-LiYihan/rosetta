#!/bin/bash
# ==============================================
# Rosetta 每月重构镜像脚本
# 功能：每月重新构建 Docker 镜像并更新容器
# 建议定时执行：每月1号凌晨4点
# ==============================================

# 配置参数
LOCAL_DIR="/opt/streamlit/rosetta"
DOCKER_IMAGE="rosetta-app"
DOCKER_CONTAINER="rosetta-app"
COMPOSE_FILE="docker-compose.yml"

# ==============================================
# 核心逻辑
# ==============================================
echo "===== Rosetta 每月重构镜像脚本开始执行：$(date '+%Y-%m-%d %H:%M:%S') ====="

# 1. 进入本地代码目录
if [ ! -d "$LOCAL_DIR" ]; then
  echo "❌ 错误：本地目录 $LOCAL_DIR 不存在！"
  echo "请先运行部署脚本或手动克隆仓库。"
  exit 1
else
  echo "进入本地目录：$LOCAL_DIR"
  cd "$LOCAL_DIR" || exit 1
fi

# 2. 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
  echo "❌ 错误：Docker 服务未运行！"
  exit 1
fi

# 3. 拉取最新代码（确保使用最新代码构建）
echo "拉取最新代码..."
git fetch origin main
git reset --hard origin/main
echo "✅ 代码已更新到最新版本"

# 4. 检查 Dockerfile 是否存在
if [ ! -f "Dockerfile" ]; then
  echo "❌ 错误：Dockerfile 不存在！"
  exit 1
fi

# 5. 停止当前容器
echo "停止当前容器..."
if docker ps --format '{{.Names}}' | grep -q "^$DOCKER_CONTAINER$"; then
  docker stop "$DOCKER_CONTAINER"
  if [ $? -eq 0 ]; then
    echo "✅ 容器停止成功"
  else
    echo "❌ 容器停止失败，尝试强制停止..."
    docker stop "$DOCKER_CONTAINER" || true
  fi
else
  echo "⚪ 容器未运行，无需停止"
fi

# 6. 删除旧容器
echo "删除旧容器..."
docker rm "$DOCKER_CONTAINER" 2>/dev/null && echo "✅ 旧容器已删除" || echo "⚪ 无旧容器可删除"

# 7. 删除旧镜像（可选，避免镜像堆积）
echo "清理旧镜像..."
OLD_IMAGES=$(docker images "$DOCKER_IMAGE" --format "{{.ID}}" 2>/dev/null | tail -n +3)
if [ -n "$OLD_IMAGES" ]; then
  echo "删除旧镜像：$OLD_IMAGES"
  docker rmi $OLD_IMAGES 2>/dev/null || echo "⚠️ 部分旧镜像删除失败（可能被其他容器引用）"
else
  echo "⚪ 无旧镜像可清理"
fi

# 8. 构建新镜像（使用 --network=host 解决网络问题）
echo "开始构建新镜像（使用 --network=host）..."
docker build --network=host -t "$DOCKER_IMAGE" .

if [ $? -eq 0 ]; then
  echo "✅ 镜像构建成功"
else
  echo "❌ 镜像构建失败！"
  echo "尝试不使用 --network=host 重新构建..."
  docker build -t "$DOCKER_IMAGE" .
  if [ $? -ne 0 ]; then
    echo "❌ 镜像构建失败，请检查错误信息"
    exit 1
  fi
  echo "✅ 镜像构建成功（不使用 --network=host）"
fi

# 9. 启动新容器
echo "启动新容器..."
if [ -f "$COMPOSE_FILE" ]; then
  echo "使用 Docker Compose 启动..."
  docker-compose up -d
else
  echo "使用 Docker 命令启动..."
  docker run -d \
    --name "$DOCKER_CONTAINER" \
    -p 8501:8501 \
    -v /opt/streamlit/rosetta:/app:ro \
    --restart unless-stopped \
    "$DOCKER_IMAGE"
fi

if [ $? -eq 0 ]; then
  echo "✅ 容器启动成功"
else
  echo "❌ 容器启动失败！"
  exit 1
fi

# 10. 验证容器状态
echo "等待容器启动..."
sleep 10

if docker ps --format '{{.Names}}' | grep -q "^$DOCKER_CONTAINER$"; then
  echo "✅ 容器运行状态正常"
  
  # 检查应用健康状态
  echo "检查应用健康状态..."
  if curl -s -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo "✅ 应用健康检查通过"
  else
    echo "⚠️ 应用健康检查失败，但容器正在运行"
    echo "查看日志：docker logs $DOCKER_CONTAINER"
  fi
else
  echo "❌ 容器未运行，请检查日志：docker logs $DOCKER_CONTAINER"
  exit 1
fi

# 11. 显示构建信息
echo ""
echo "==================== 构建完成 ===================="
echo "镜像信息："
docker images "$DOCKER_IMAGE" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"
echo ""
echo "容器信息："
docker ps --filter "name=$DOCKER_CONTAINER" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "构建时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "下次建议重构时间：$(date -d '+1 month' '+%Y-%m-%d')"
echo "=================================================="

echo "===== 脚本执行结束：$(date '+%Y-%m-%d %H:%M:%S') ====="

# 设置执行权限提示
echo "提示：请确保脚本有执行权限：chmod +x $(realpath "$0")"

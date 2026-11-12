#!/bin/sh
# 小码后端容器启动脚本。
#
# 1. 安全校验：宿主机绑定地址不是本机时，必须同时提供访问密码，
#    并显式设置 XIAOMA_ALLOW_REMOTE=true；否则拒绝启动。
# 2. 自动执行幂等数据库迁移与种子数据，首次启动即可使用。
# 3. 启动 uvicorn。容器内监听 0.0.0.0 仅供 frontend 容器通过内部网络
#    访问；宿主机是否可达由 docker-compose 的 BIND_ADDRESS 端口映射决定。
set -eu

BIND_ADDRESS="${XIAOMA_BIND_ADDRESS:-127.0.0.1}"

case "$BIND_ADDRESS" in
  127.0.0.1|localhost|::1)
    ;;
  *)
    if [ -z "${XIAOMA_ACCESS_PASSWORD:-}" ]; then
      echo "错误：BIND_ADDRESS=${BIND_ADDRESS} 将服务开放给本机以外的网络，" >&2
      echo "但未设置 XIAOMA_ACCESS_PASSWORD。请先在 .env 中设置强访问密码；" >&2
      echo "拒绝以无保护方式启动。" >&2
      exit 1
    fi
    if [ "${XIAOMA_ALLOW_REMOTE:-false}" != "true" ]; then
      echo "错误：BIND_ADDRESS=${BIND_ADDRESS} 需要同时设置" >&2
      echo "XIAOMA_ALLOW_REMOTE=true，以明确确认开放远程访问。" >&2
      exit 1
    fi
    ;;
esac

# 显式传入命令时（如 docker compose run ... restore-db），直接执行，
# 不执行迁移/种子，便于在停服状态下恢复数据库。
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

echo "正在执行数据库迁移..."
python -m app.cli init-db

echo "正在写入课程种子数据（幂等）..."
python -m app.cli seed-courses

# 教材正文与知识点（幂等）。这 6 条命令缺一不可：
# seed-courses 只写课程目录与「零基础入门」的旧版结构，不含其余课程的
# 知识点与任何正文；漏跑会让界面显示「该课程没有可学习的知识点」。
echo "正在写入零基础入门教材（幂等）..."
python -m app.cli seed-textbook

echo "正在写入进阶与数据库教材（幂等）..."
python -m app.cli seed-phase4a

echo "正在写入 FastAPI 后端开发教材（幂等）..."
python -m app.cli seed-phase4b

echo "正在写入大模型 API 应用开发教材（幂等）..."
python -m app.cli seed-phase4c

echo "正在写入 LangGraph Agent 开发教材（幂等）..."
python -m app.cli seed-phase4d

echo "正在写入软件工程与项目部署教材（幂等）..."
python -m app.cli seed-phase4e

echo "正在写入内置题库（幂等）..."
python -m app.cli seed-questions

echo "启动小码后端..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

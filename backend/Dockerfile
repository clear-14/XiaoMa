# 小码后端镜像（Python 3.14）
FROM python:3.14-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Alembic 迁移环境：容器启动时执行数据库迁移所需
COPY alembic.ini ./
COPY alembic ./alembic

# 启动脚本负责安全校验、迁移、种子数据与启动 uvicorn
COPY entrypoint.sh /app/entrypoint.sh

# 数据库文件目录（由 docker-compose 的命名卷挂载持久化，不落在容器临时目录）
RUN mkdir -p /app/data

EXPOSE 8000

# 通过 sh 调用，避免 Windows 检出时文件权限/换行符导致无法执行
ENTRYPOINT ["sh", "/app/entrypoint.sh"]

# 小码后端镜像（Python 3.14）
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Alembic 迁移环境：容器内执行数据库初始化（python -m app.cli init-db）所需
COPY alembic.ini ./
COPY alembic ./alembic

# 数据库文件目录（由 docker-compose 的命名卷挂载持久化，不落在容器临时目录）
RUN mkdir -p /app/data

EXPOSE 8000

# 容器内监听所有接口；对外暴露范围由宿主机端口映射控制
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

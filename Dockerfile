# 单镜像：同一镜像通过 ROLE 环境变量切换为 web / worker 进程。
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装依赖，利用层缓存
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# 再拷源码
COPY app ./app
COPY alembic.ini ./
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000

# ROLE=web (默认) 启动 API；ROLE=worker 启动异步任务消费
ENV ROLE=web
ENTRYPOINT ["entrypoint.sh"]

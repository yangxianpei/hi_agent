FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先拷贝依赖描述，利用 Docker 层缓存
COPY pyproject.toml README.md ./

# 安装项目依赖
RUN pip install --upgrade pip && pip install .

# 再拷贝项目代码
COPY app ./app
COPY run.py ./

EXPOSE 3000

# 生产模式不使用 --reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]

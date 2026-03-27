FROM python:3.11-slim

WORKDIR /app

# 升级 pip（可选）
RUN pip install --upgrade pip

# 安装 uv
RUN pip install uv

# 配置 uv 镜像源（关键）
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV UV_EXTRA_INDEX_URL=https://pypi.org/simple/

# 复制依赖文件（利用缓存）
COPY pyproject.toml uv.lock* /app/

# 安装依赖
RUN uv sync

# 复制代码
COPY . /app

ENV ENV=dev

CMD ["uv", "run", "main.py"]
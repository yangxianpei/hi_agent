FROM python:3.12-slim

WORKDIR /app

# ===================== 关键：配置 Debian 国内阿里云源 =====================
RUN sed -i "s@deb.debian.org@mirrors.aliyun.com@g" /etc/apt/sources.list.d/debian.sources && \
    apt update && \
    apt install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*  # 清理缓存，不占磁盘

# pip 国内源
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

RUN pip install --upgrade pip

# 安装 uv
RUN pip install uv

# uv 国内源
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# 复制依赖
COPY pyproject.toml uv.lock /app/

# 安装依赖
# RUN uv sync

# 复制代码
COPY . /app

# CMD ["uv", "run", "run.py"]
CMD ["sh", "-c", "uv sync --no-dev && uv run run.py"]
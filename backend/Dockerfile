FROM python:3.11-slim

WORKDIR /app

# 安装 curl（必须）
RUN apt-get update && apt-get install -y curl

# 安装 uv（官方推荐方式）
RUN curl -Ls https://astral.sh/uv/install.sh | sh

# 把 uv 加到 PATH
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock* /app/

RUN uv sync --frozen --index-url https://mirrors.aliyun.com/pypi/simple/

COPY . /app

CMD ["uv", "run", "main.py"]
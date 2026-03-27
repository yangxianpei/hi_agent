FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl

# 安装 uv
RUN curl -Ls https://astral.sh/uv/install.sh | sh

# 直接用绝对路径
RUN /root/.local/bin/uv --version

COPY pyproject.toml uv.lock* /app/

# 用绝对路径执行
RUN /root/.local/bin/uv sync --frozen --index-url https://mirrors.aliyun.com/pypi/simple/

COPY . /app

CMD ["/root/.local/bin/uv", "run", "main.py"]
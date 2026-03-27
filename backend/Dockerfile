FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl ca-certificates

# 安装 uv
RUN curl -Ls https://astral.sh/uv/install.sh | sh

# 可选：加入 PATH（方便调试）
ENV PATH="/root/.local/bin:$PATH"

# 验证 uv
RUN /root/.local/bin/uv --version

# 先拷贝依赖文件（利用缓存）
COPY pyproject.toml uv.lock* /app/

# 安装依赖
RUN /root/.local/bin/uv sync --frozen --index-url https://mirrors.aliyun.com/pypi/simple/

# 再拷贝代码
COPY . /app

CMD ["/root/.local/bin/uv", "run", "main.py"]
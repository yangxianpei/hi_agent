FROM python:3.11-slim

WORKDIR /app

# 先换国内源 + 升级 pip
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip install --upgrade pip

# 安装 uv（官方正确方式）
RUN pip install uv

# 安装依赖
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen

# 复制代码
COPY . .

ENV ENV=dev
CMD ["uv", "run", "main.py"]
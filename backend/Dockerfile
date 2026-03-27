FROM python:3.11-slim

WORKDIR /app

# 换国内源 + 升级 pip
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip install --upgrade pip

# 安装 uv
RUN pip install uv

# 复制配置
COPY pyproject.toml ./

# 关键！不加 --frozen，自动生成 lockfile
RUN uv sync

# 复制代码
COPY . .

ENV ENV=dev
CMD ["uv", "run", "main.py"]
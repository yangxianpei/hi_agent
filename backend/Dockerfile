FROM python:3.12-slim

WORKDIR /app

# pip 国内源（给 pip / 构建依赖用）
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

RUN pip install --upgrade pip

# 安装 uv
RUN pip install uv

# uv 国内源（给 uv 用，关键！）
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# 复制依赖文件（利用缓存）
COPY pyproject.toml uv.lock /app/

# 安装依赖（锁版本）
# RUN uv sync

# 复制代码
COPY . /app

CMD ["uv", "run", "run.py"]
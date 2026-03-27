# 使用轻量 Python 镜像
FROM python

WORKDIR /app

# 先复制依赖文件，利用缓存
COPY pyproject.toml uv.lock* /app/

# 安装 uv
RUN pip install --no-cache-dir uv

# 安装依赖
RUN uv sync --frozen --index-url https://mirrors.aliyun.com/pypi/simple/

# 再复制代码
COPY . /app

# 设置默认环境变量为 dev，可在启动时覆盖
ENV ENV=dev

# 使用 uvicorn 运行
CMD ["uv", "run", "main.py"]
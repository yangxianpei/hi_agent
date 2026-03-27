FROM python:3.11-slim

WORKDIR /app

# 关键！换成国内 pip 源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
RUN pip config set install.trusted-host mirrors.aliyun.com

COPY requirements.txt .
COPY pyproject.toml .

# 安装依赖（现在用国内源，飞快）
RUN pip install --upgrade pip && pip install .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8000"]
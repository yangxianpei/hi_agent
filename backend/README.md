# Backend (FastAPI)

## 本地运行

1. 安装依赖：
   - `pip install -e .`
2. 启动服务：
   - `python run.py`
3. 打开文档：
   - Swagger UI: `http://127.0.0.1:3000/docs`
   - ReDoc: `http://127.0.0.1:3000/redoc`

## Docker 部署

### 使用 Docker Compose（推荐）

1. 准备环境变量文件：
   - 在项目根目录放置 `.env`
2. 构建并启动：
   - `docker compose up -d --build`
3. 查看日志：
   - `docker compose logs -f backend`
4. 停止服务：
   - `docker compose down`

### 仅使用 Docker 命令

1. 构建镜像：
   - `docker build -t hi-agent-backend:latest .`
2. 启动容器：
   - `docker run -d --name hi-agent-backend -p 3000:3000 --env-file .env hi-agent-backend:latest`

服务启动后访问：
- `http://127.0.0.1:3000/docs`
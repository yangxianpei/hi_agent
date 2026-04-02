from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# 固定从 backend/.env 加载，避免 cwd 不同导致读不到
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.router.chat import router as chat_router
from app.router.video import router as video_router
from fastapi.staticfiles import StaticFiles  # 必须导入
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动事件"""
    print("📚 API文档: http://localhost:3000/docs")
    print("📖 ReDoc文档: http://localhost:8000/redoc")
    print("=" * 60 + "\n")
    yield
    print("stopping...")

app = FastAPI(docs_url=None, redoc_url=None, title="Backend API", version="0.1.0", lifespan=lifespan)

# 项目根目录（backend）下的 output，避免受运行时 cwd 影响
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router, prefix="/api")
app.include_router(video_router, prefix="/api")
@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "FastAPI is running"}



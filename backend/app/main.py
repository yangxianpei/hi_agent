from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.router.chat import router as chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动事件"""
    print("📚 API文档: http://localhost:3000/docs")
    print("📖 ReDoc文档: http://localhost:8000/redoc")
    print("=" * 60 + "\n")
    yield
    print("stopping...")


app = FastAPI(title="Backend API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router, prefix="/api")

@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "FastAPI is running"}



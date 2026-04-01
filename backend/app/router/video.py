
import asyncio
import json
import shutil
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from concurrent.futures import ThreadPoolExecutor

from app.service.process_video import process_video
from app.utils.video_task_events import emit, snapshot

executor = ThreadPoolExecutor(max_workers=4)
router = APIRouter(prefix="/v1", tags=["视频"])
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
SSE_POLL_INTERVAL_SEC = 0.2
MAX_TASK_DOCS = 5


def _safe_task_key(task_key: str) -> None:
    if not task_key or ".." in task_key or "/" in task_key or "\\" in task_key:
        raise HTTPException(status_code=400, detail="invalid task_key")


_MARKDOWN_BY_KIND: dict[str, str] = {
    "origin": "origin_result.md",
    "ai": "Ai_result.md",
    "ai_video_cut": "Ai_video_cut_result.md",
}


def _cleanup_old_task_dirs(keep: int = MAX_TASK_DOCS, protect: str | None = None) -> None:
    if not OUTPUT_DIR.exists():
        return
    task_dirs = [p for p in OUTPUT_DIR.iterdir() if p.is_dir()]
    if protect:
        task_dirs = [p for p in task_dirs if p.name != protect]
    if len(task_dirs) <= keep:
        return
    task_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    to_delete = task_dirs[keep:]
    for old_dir in to_delete:
        shutil.rmtree(old_dir, ignore_errors=True)


@router.post("/video/upload")
async def video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    file_extension = Path(file.filename).suffix.lower()
    video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}
    if file_extension not in video_extensions:
        raise HTTPException(status_code=400, detail="文件格式不对")

    file_content = await file.read()
    if len(file_content) == 0:
        raise HTTPException(status_code=400, detail="文件为空") 
    task_id = str(uuid.uuid4())[:16]
    file_name = f"{task_id}_{Path(file.filename).stem}"
    display_name = f"{file_name}{file_extension}"
    output_display_name = f"{file_name}.wav"
    #创建output目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)



    output_dir = OUTPUT_DIR / file_name
    output_dir.mkdir(parents=True, exist_ok=True)
    executor.submit(_cleanup_old_task_dirs, MAX_TASK_DOCS, file_name)
    wav_file_path = output_dir / output_display_name
    file_path = output_dir / display_name
    with open(file_path, "wb") as f:
        f.write(file_content)

    emit(file_name, "queued", "任务已入队，等待处理", {"task_key": file_name})
    executor.submit(process_video, str(file_path), str(wav_file_path), str(output_dir))

    return JSONResponse(
        {
            "message": "File uploaded successfully",
            "status_code": 200,
            "task_key": file_name,
        }
    )


@router.get("/video/tasks/{task_key}/events")
async def video_task_events(task_key: str):
    """SSE：按阶段推送视频处理进度；事件同时落在 output/{task_key}/sse_events.jsonl。"""
    _safe_task_key(task_key)
    events_file = OUTPUT_DIR / task_key / "sse_events.jsonl"

    async def event_gen():
        if not events_file.is_file():
            yield f"data: {json.dumps({'stage': 'not_found', 'message': 'sse_events.jsonl not found'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return
        last = 0
        terminal_stages = {"error", "finished"}
        while True:
            events = snapshot(task_key)
            n = len(events)
            while last < n:
                ev = events[last]
                last += 1
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                if ev.get("stage") in terminal_stages:
                    yield "data: [DONE]\n\n"
                    return
            await asyncio.sleep(SSE_POLL_INTERVAL_SEC)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/video/tasks/{task_key}/markdown")
def get_task_markdown(
    task_key: str,
    kind: Literal["origin", "ai", "ai_video_cut"] = Query(
        "origin",
        description="origin=识别原文；ai=AI解读；ai_video_cut=带视频帧的AI稿",
    ),
):
    """根据任务目录 id（task_key）返回对应 markdown 正文。"""
    _safe_task_key(task_key)
    filename = _MARKDOWN_BY_KIND.get(kind)
    if not filename:
        raise HTTPException(status_code=400, detail="invalid kind")
    base = OUTPUT_DIR / task_key
    if not base.is_dir():
        raise HTTPException(status_code=404, detail="task not found")
    path = base / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"file not found: {filename}")
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {
        "task_key": task_key,
        "kind": kind,
        "filename": filename,
        "content": content,
    }


@router.get("/video/test")
def video_test():
    return {"message": "OK", "status_code": 200}

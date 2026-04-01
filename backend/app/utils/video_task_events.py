"""
视频任务阶段事件：供 SSE 推送；内存保留一份，同时追加写入 output/{task_key}/sse_events.jsonl。
线程安全，可从 ThreadPoolExecutor 中的 process_video 调用。
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = _PROJECT_ROOT / "output"

_lock = threading.Lock()
_histories: dict[str, list[dict[str, Any]]] = {}


def _jsonl_path(task_key: str) -> Path:
    return OUTPUT_DIR / task_key / "sse_events.jsonl"


def _load_from_disk_if_needed(task_key: str) -> None:
    path = _jsonl_path(task_key)
    if not path.is_file():
        return
    with _lock:
        if _histories.get(task_key):
            return
        events: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        _histories[task_key] = events


def emit(
    task_key: str,
    stage: str,
    message: str = "",
    data: dict[str, Any] | None = None,
    *,
    persist: bool = True,
) -> dict[str, Any]:
    ev: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "message": message,
        "data": data or {},
    }
    out_dir = OUTPUT_DIR / task_key
    with _lock:
        _histories.setdefault(task_key, []).append(ev)

    if persist:
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(out_dir / "sse_events.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        except OSError:
            pass
    return ev


def snapshot(task_key: str) -> list[dict[str, Any]]:
    """返回当前任务全部事件（会先尝试从磁盘加载，便于重启后 SSE 续看）。"""
    _load_from_disk_if_needed(task_key)
    with _lock:
        return list(_histories.get(task_key, []))

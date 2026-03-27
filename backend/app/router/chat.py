from __future__ import annotations

import json
import queue
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# from app.utils.llm import LLM
from app.utils.llm2 import LLM2
router = APIRouter(prefix="/v1", tags=["聊天"])

_llm = LLM2()


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, description="用户输入")


from app.utils.emit import add_tool_event, get_tool_event,clear_tool_event





@router.post(
    "/chat",
    summary="聊天（SSE流式）",
    description="将 LLM 的 stream 输出以 SSE 方式返回",
)
def chat(req: ChatRequest) -> StreamingResponse:
    def _extract_text(chunk: Any) -> str | None:
        if chunk is None:
            return None
        if isinstance(chunk, bytes):
            return chunk.decode("utf-8", errors="ignore")
        if isinstance(chunk, str):
            return chunk
        if isinstance(chunk, dict):
            for k in ("content", "text", "delta"):
                v = chunk.get(k)
                if isinstance(v, str) and v:
                    return v
        for attr in ("content", "text", "delta"):
            v = getattr(chunk, attr, None)
            if isinstance(v, str) and v:
                return v
        return None

    def sse_gen():
        yield f"data: {json.dumps({'type': 'start', 'content': ''}, ensure_ascii=False)}\n\n"
        try:
            for chunk in _llm.chat(req.text):
                for tool_event in get_tool_event():
                    payload = {
                            "type": "tool_status",
                            "name": tool_event.get("name"),
                            "status": tool_event.get("status"),
                        }
                    print("payload",payload)
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                text = _extract_text(chunk)
                if not text:
                    continue
                content_sent = True
                yield f"data: {json.dumps({'type': 'content', 'content': text}, ensure_ascii=False)}\n\n"

            # 兜底：若工具事件在最后一个chunk后才入队，也只补发一次状态
            # if not tool_status_sent:
                # for tool_event in events:
                #     if (
                #         tool_event.get("phase") == "start"
                #         and tool_event.get("tool_name") != "mcp_preflight"
                #     ):
                #         is_mcp = tool_event.get("source") == "mcp"
                #         payload = {
                #             "type": "tool_status",
                #             "status": "mcp_calling" if is_mcp else "tool_calling",
                #         }
                #         if is_mcp:
                #             payload["tools_function"] = _llm.get_tools_function()
                #         yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                #         break

            if not content_sent:
                yield f"data: {json.dumps({'type': 'content', 'content': '当前未生成内容，请稍后重试。'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        clear_tool_event()
    return StreamingResponse(
        sse_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
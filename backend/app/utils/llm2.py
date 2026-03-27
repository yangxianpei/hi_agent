import asyncio
import json
import logging
import os
import queue
import re
import time
import threading
from collections import deque
from datetime import timedelta
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler
from app.utils.emit import add_tool_event, get_tool_event
load_dotenv()
logger = logging.getLogger("app.llm2")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class ToolTraceHandler(BaseCallbackHandler):
    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> Any:
        print(f"[tool_start] name={serialized.get('name')}")
        add_tool_event({
            "name": serialized.get('name'),
            "status":'start'
        })

    def on_tool_end(self, output: Any, **kwargs: Any) -> Any:
        print(f"[tool_end] output={str(output)[:120]}")
        add_tool_event({
            "name": kwargs.get("name", "done"),
            "status":'done'
        })

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> Any:
        print(f"[tool_error] error={error}")


def _root_error_message(exc: BaseException) -> str:
    """提取 ExceptionGroup 的最底层错误，方便定位根因。"""
    if isinstance(exc, ExceptionGroup):
        messages: list[str] = []
        stack: list[BaseException] = list(exc.exceptions)
        while stack:
            cur = stack.pop(0)
            if isinstance(cur, ExceptionGroup):
                stack = list(cur.exceptions) + stack
                continue
            messages.append(f"{type(cur).__name__}: {cur}")
        if messages:
            return " | ".join(messages[:3])
    return f"{type(exc).__name__}: {exc}"


def _extract_ai_text(msg: Any) -> str:
    """仅提取模型消息文本，避免把ToolMessage原文透传给前端。"""
    if not isinstance(msg, (AIMessage, AIMessageChunk)):
        return ""
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
        return "".join(parts)
    return ""


def _resolve_reply_style(user_message: str) -> str:
    """根据用户意图动态选择回复风格。"""
    base_style = os.getenv("LLM_REPLY_STYLE", "compact").strip().lower()
    content = (user_message or "").lower()
    detailed_keywords = (
        "详细",
        "完整",
        "专业版",
        "展开",
        "细节",
        "具体一点",
        "给全",
        "完整版",
    )
    compact_keywords = ("简洁", "简短", "一句话", "精简", "概括", "短一点")
    if any(k in content for k in detailed_keywords):
        return "detailed"
    if any(k in content for k in compact_keywords):
        return "compact"
    return base_style


def _build_system_prompt(style: str) -> str:
    if style in {"detailed", "professional"}:
        return (
            "请用中文专业回答，信息完整、结构清晰。"
            "优先使用分节结构：结论、方案、步骤、注意事项。"
            "在每个主段落前可适度使用1个emoji增强可读性。"
            "如果涉及菜谱/计划类问题，默认给出可执行版本（食材量、步骤、时间、替代建议）。"
            "普通段落不要频繁硬换行。"
        )
    return (
        "请用中文简洁回答。优先给结论，不要长篇解释。"
        "除非用户要求详细，默认控制在4-8行内。"
        "段落内不要手动频繁换行，普通说明尽量写成自然段。"
        "可适度使用文字图标(emoji)增强可读性，例如✅🍽️📌。"
        "在小标题或要点前可加1个emoji，但不要每行都加。"
    )


def _looks_like_mcp_request(message: str) -> bool:
    text = (message or "").lower()
    keywords = ("调用mcp", "调用 mcp", "美食", "菜谱", "吃什么", "推荐菜", "食谱")
    return any(k in text for k in keywords)


def _compact_text(text: str) -> str:
    """压缩输出长度，避免前端展示过长。"""
    max_chars = int(os.getenv("LLM_REPLY_MAX_CHARS", "320"))
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    merged: list[str] = []
    in_code_block = False

    def _is_md_block_line(line: str) -> bool:
        return bool(
            re.match(r"^(#{1,6}\s|[-*+]\s|\d+\.\s|>\s|\|)", line)
            or line.startswith("```")
        )

    # 合并普通段落中的硬换行，避免前端 Markdown 渲染成“短句频繁换行”
    for line in lines:
        if line.startswith("```"):
            in_code_block = not in_code_block
            merged.append(line)
            continue
        if in_code_block:
            merged.append(line)
            continue
        if not merged:
            merged.append(line)
            continue

        prev = merged[-1]
        if (not _is_md_block_line(prev)) and (not _is_md_block_line(line)):
            merged[-1] = f"{prev} {line}"
        else:
            merged.append(line)

    normalized = "\n".join(merged)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1] + "…"


def _chunk_text(text: str):
    """把完整文本切成小块，便于 SSE 逐段推送。"""
    chunk_size = int(os.getenv("LLM_STREAM_CHUNK_SIZE", "80"))
    if chunk_size <= 0:
        chunk_size = 80
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


def _to_text(value: Any) -> str:
    """把任意工具输出规整为字符串，避免上游接口拒绝非字符串 content。"""
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _run_coro_sync(coro):
    """在同步上下文安全执行协程；若当前线程已有事件循环，则切到新线程执行。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result_box: dict[str, Any] = {}
    error_box: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result_box["value"] = asyncio.run(coro)
        except BaseException as e:
            error_box["error"] = e

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join()

    if "error" in error_box:
        raise error_box["error"]
    return result_box.get("value")


class LLM2:
    """基于 LangChain + MCP 的聊天封装（兼容现有 chat.py 调用方式）。"""

    def __init__(self):
        self._tool_events: deque[dict[str, Any]] = deque()
        self._tools_function: list[dict[str, Any]] = []
        self._tool_wrappers: list[Any] = []
        self._mcp_next_retry_at: float = 0.0
        self._mcp_retry_backoff_seconds: int = int(os.getenv("MCP_RETRY_INITIAL_SECONDS", "5"))
        self._mcp_retry_max_seconds: int = int(os.getenv("MCP_RETRY_MAX_SECONDS", "60"))
        self._mcp_error_log_cooldown_seconds: int = int(os.getenv("MCP_ERROR_LOG_COOLDOWN_SECONDS", "30"))
        self._mcp_last_error_text: str = ""
        self._mcp_last_error_log_at: float = 0.0
        self._llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL_ID", "deepseek-chat"),
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        )
        self.agent = None
        _run_coro_sync(self._async_init())

    async def _async_init(self) -> None:
        try:
            raw_tools = await self._load_mcp_tools()
            wrapped_tools = [self._wrap_mcp_tool(t) for t in raw_tools]
        except Exception as e:
            logger.exception(
                "初始化MCP工具失败，回退为无工具模式: %s",
                _root_error_message(e),
            )
            wrapped_tools = []

        self._tool_wrappers = wrapped_tools
        self._tools_function = [
            {"name": t.name, "description": t.description or ""} for t in wrapped_tools
        ]
        self.agent = create_agent(model=self._llm, tools=wrapped_tools)

    async def _ensure_tools_loaded(self) -> None:
        """运行期兜底：若启动时MCP异常，后续请求按退避策略重试加载。"""
        if self._tool_wrappers:
            return

        now = time.time()
        if now < self._mcp_next_retry_at:
            return

        try:
            raw_tools = await self._load_mcp_tools()
            wrapped_tools = [self._wrap_mcp_tool(t) for t in raw_tools]
        except Exception as e:
            err_text = _root_error_message(e)
            should_log = (
                err_text != self._mcp_last_error_text
                or (now - self._mcp_last_error_log_at) >= self._mcp_error_log_cooldown_seconds
            )
            if should_log:
                logger.warning("重试加载MCP工具失败: %s", err_text)
                self._mcp_last_error_text = err_text
                self._mcp_last_error_log_at = now

            self._mcp_next_retry_at = now + self._mcp_retry_backoff_seconds
            self._mcp_retry_backoff_seconds = min(
                self._mcp_retry_backoff_seconds * 2,
                self._mcp_retry_max_seconds,
            )
            return

        self._tool_wrappers = wrapped_tools
        self._tools_function = [
            {"name": t.name, "description": t.description or ""} for t in wrapped_tools
        ]
        self.agent = create_agent(model=self._llm, tools=wrapped_tools)
        self._mcp_next_retry_at = 0.0
        self._mcp_retry_backoff_seconds = int(os.getenv("MCP_RETRY_INITIAL_SECONDS", "5"))
        self._mcp_last_error_text = ""
        self._mcp_last_error_log_at = 0.0
        logger.info("MCP工具重试加载成功: %s个", len(wrapped_tools))

    async def _load_mcp_tools(self):
        mcp_url = os.getenv("MCP_SERVER_URL", "").strip()
        if not mcp_url:
            raise RuntimeError("未配置 MCP_SERVER_URL")
        client = MultiServerMCPClient(
            {
                "howtocook-cn-mcp-server": {
                    "transport": "streamable_http",
                    "url": mcp_url,
                    "timeout": timedelta(seconds=int(os.getenv("MCP_TIMEOUT_SECONDS", "30"))),
                    "sse_read_timeout": timedelta(seconds=int(os.getenv("MCP_SSE_TIMEOUT_SECONDS", "30"))),
                },
                # "bing-cn-mcp-server": {
                #     "transport": "streamable_http",
                #     "url": "https://mcp.api-inference.modelscope.net/397fabbd558d45/mcp",
                # },
                # "fetch": {
                #     "transport": "streamable_http",
                #     "url": "https://mcp.api-inference.modelscope.net//mcp",
                # },
                "tavily-mcp": {
                    "transport": "streamable_http",
                    "url": "https://mcp.api-inference.modelscope.net/397fabbd558d45/mcp",
                },
                "amap-maps": {
                    "transport": "streamable_http",
                    "url": "https://mcp.api-inference.modelscope.net/f0a52fdd975e49/mcp",
                },
            }
        )
        return await client.get_tools()

    def _wrap_mcp_tool(self, tool):
        async def _arun(**kwargs):
            start = time.perf_counter()
            logger.info("[MCP调用开始] tool=%s", tool.name)

            logger.info(
                "[MCP调用入参] %s",
                json.dumps(kwargs, ensure_ascii=False, default=str),
            )

            try:
                tool_timeout = int(os.getenv("MCP_TOOL_TIMEOUT_SECONDS", "120"))
                result = await asyncio.wait_for(tool.ainvoke(kwargs), timeout=tool_timeout)
                text = _to_text(result)
            except Exception as e:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                self._tool_events.append(
                    {
                        "phase": "error",
                        "source": "mcp",
                        "tool_name": tool.name,
                        "error": str(e),
                    }
                )
                logger.exception(
                    "[MCP调用失败] tool=%s elapsed=%sms error=%s",
                    tool.name,
                    elapsed_ms,
                    e,
                )
                raise

            elapsed_ms = int((time.perf_counter() - start) * 1000)
            preview = text[:200] + ("..." if len(text) > 200 else "")
            logger.info("[MCP调用完成] tool=%s elapsed=%sms", tool.name, elapsed_ms)
            logger.info("[MCP返回预览] %s", preview)
            return text

        return StructuredTool.from_function(
            coroutine=_arun,
            name=tool.name,
            description=tool.description or f"MCP tool: {tool.name}",
            args_schema=getattr(tool, "args_schema", None),
        )

    def pop_tool_events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while self._tool_events:
            events.append(self._tool_events.popleft())
        return events

    def get_tools_function(self) -> list[dict[str, Any]]:
        return self._tools_function

    def _iter_agent_stream_sync(self, payload: dict[str, Any]):
        """把 agent.astream(异步)桥接为同步迭代，避免 sync tool invoke 报错。"""
        q: queue.Queue[tuple[str, Any]] = queue.Queue()

        async def _producer() -> None:
            try:
                async for item in self.agent.astream(payload, stream_mode="messages", config={"callbacks": [ToolTraceHandler()]},):
                    q.put(("item", item))
            except BaseException as e:
                q.put(("error", e))
            finally:
                q.put(("done", None))

        def _runner() -> None:
            asyncio.run(_producer())

        t = threading.Thread(target=_runner, daemon=True)
        t.start()

        while True:
            try:
                kind, value = q.get(timeout=0.2)
            except queue.Empty:
                # 给上游一个心跳tick，便于路由层及时 pop_tool_events 发 tool_status
                yield None
                continue
            if kind == "item":
                yield value
                continue
            if kind == "error":
                raise value
            break

    def chat(self, message: str):
        if self.agent is None:
            raise RuntimeError("Agent 未初始化完成")
        _run_coro_sync(self._ensure_tools_loaded())
        style = _resolve_reply_style(message)
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": _build_system_prompt(style),
                },
                {"role": "user", "content": message},
            ],
            "tool_choice": "auto",
        }
        emitted = False
        max_chars = int(os.getenv("LLM_REPLY_MAX_CHARS", "320"))
        sent_chars = 0
        try:
            for stream_item in self._iter_agent_stream_sync(payload):
                msg = stream_item[0] if isinstance(stream_item, tuple) else stream_item
                tool_calls = getattr(msg, "tool_calls", None)
                if isinstance(tool_calls, list) and tool_calls:
                    first = tool_calls[0] if isinstance(tool_calls[0], dict) else {}
                    name = first.get("name", "mcp_tool")
                    self._tool_events.append(
                        {
                            "phase": "start",
                            "source": "mcp" if str(name).startswith("mcp_") else "tool",
                            "tool_name": name,
                            "arguments": first.get("args", {}),
                        }
                    )
                content = _extract_ai_text(msg)
                if not content:
                    continue
                for piece in _chunk_text(content):
                    remain = max_chars - sent_chars
                    if remain <= 0:
                        if emitted:
                            yield "…"
                        return
                    out = piece[:remain]
                    if out:
                        emitted = True
                        sent_chars += len(out)
                        yield out
        except Exception:
            logger.exception("agent.stream失败，回退到ainvoke")

        if emitted:
            return

        # 回退：流式失败时返回一次性结果，避免前端空白
        result = _run_coro_sync(asyncio.wait_for(self.agent.ainvoke(payload), timeout=90))
        messages = result.get("messages", [])
        if not messages:
            yield "未收到模型回复。"
            return
        content = getattr(messages[-1], "content", "")
        compacted = _compact_text(_to_text(content))
        for piece in _chunk_text(compacted):
            yield piece

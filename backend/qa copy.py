import asyncio
import json
import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

load_dotenv()
logging.getLogger("mcp").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)


@tool
def get_today_date() -> str:
    """获取今天日期与星期（北京时间）2。"""
    now = datetime.now()
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return f"今天是 {now:%Y-%m-%d}，星期{weekdays[now.weekday()]}"


def _normalize_tool_output(value):
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _wrap_tool_as_string(tool_obj):
    async def _arun(**kwargs):
        tool_name = getattr(tool_obj, "name", "unknown_tool")
        last_error = None
        for attempt in range(1, 3):
            try:
                result = await asyncio.wait_for(tool_obj.ainvoke(kwargs), timeout=20.0)
                return _normalize_tool_output(result)
            except Exception as e:
                last_error = e
                if not _is_retryable_error(e) or attempt >= 2:
                    break
                wait = 0.6 * attempt
                print(f"[retry {attempt}] tool {tool_name} 失败，{wait:.1f}s 后重试")
                await asyncio.sleep(wait)
        return _friendly_error_text(last_error) if last_error else "MCP 调用失败，请稍后重试。"

    def _run(**kwargs):
        try:
            result = tool_obj.invoke(kwargs)
            return _normalize_tool_output(result)
        except Exception as e:
            tool_name = getattr(tool_obj, "name", "unknown_tool")
            return f"工具 {tool_name} 调用失败: {e}"

    return StructuredTool(
        name=tool_obj.name,
        description=getattr(tool_obj, "description", "") or "",
        args_schema=getattr(tool_obj, "args_schema", None),
        func=_run,
        coroutine=_arun,
    )


def _is_retryable_error(err: Exception) -> bool:
    if isinstance(err, asyncio.TimeoutError):
        return True
    msg = str(err).lower()
    return (
        "remoteprotocolerror" in msg
        or "peer closed connection" in msg
        or "readtimeout" in msg
        or "timeout" in msg
        or "connection reset" in msg
    )


def _friendly_error_text(err: Exception) -> str:
    if isinstance(err, asyncio.TimeoutError):
        return "MCP 超时，请稍后重试。"
    msg = str(err).lower()
    if (
        "remoteprotocolerror" in msg
        or "peer closed connection" in msg
        or "readtimeout" in msg
        or "timeout" in msg
        or "connection reset" in msg
    ):
        return "MCP 超时，请稍后重试。"
    return "MCP 调用失败，请稍后重试。"


async def _retry_async(
    call_name: str,
    fn,
    max_attempts: int = 3,
    per_try_timeout_seconds: float = 35.0,
):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await asyncio.wait_for(fn(), timeout=per_try_timeout_seconds)
        except Exception as e:
            last_error = e
            if not _is_retryable_error(e) or attempt >= max_attempts:
                break
            wait = 0.8 * attempt
            print(f"[retry {attempt}] {call_name} 失败，{wait:.1f}s 后重试")
            await asyncio.sleep(wait)
    raise RuntimeError(f"{call_name} 调用失败: {last_error}") from last_error


def _extract_final_text(result) -> str:
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for m in reversed(messages):
        content = getattr(m, "content", "")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    txt = item.get("text", "")
                    if txt:
                        parts.append(txt)
            if parts:
                return "\n".join(parts)
    return ""


def _did_call_mcp(result, raw_tools) -> bool:
    tool_names = {t.name for t in raw_tools}
    for m in result.get("messages", []):
        name = getattr(m, "name", None)
        if getattr(m, "type", None) == "tool" and name in tool_names:
            return True
        tool_calls = getattr(m, "tool_calls", None) or []
        for tc in tool_calls:
            if tc.get("name", "") in tool_names:
                return True
    return False


async def main():
    # 对应 mcpServers 配置
    client = MultiServerMCPClient(
        {
            "bing-cn-mcp-server": {
                "transport": "streamable_http",
                "url": "https://mcp.api-inference.modelscope.net/397fabbd558d45/mcp",
                "timeout": timedelta(seconds=30),
                "sse_read_timeout": timedelta(seconds=30),
            }
        }
    )

    raw_tools = []
    tools = [get_today_date]
    mcp_available = False
    try:
        raw_tools = await _retry_async(
            "MCP get_tools", client.get_tools, per_try_timeout_seconds=25.0
        )
        print("Loaded MCP tools:", [t.name for t in raw_tools])
        tools += [_wrap_tool_as_string(t) for t in raw_tools]
        mcp_available = len(raw_tools) > 0
    except Exception as e:
        print(f"[degrade] {_friendly_error_text(e)} 已降级到本地工具。")

    model = ChatOpenAI(
        model=os.getenv("LLM_MODEL_ID", "deepseek-chat"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )
    agent = create_agent(model=model, tools=tools)

    request_payload = {
        "messages": [
            {
                "role": "user",
                "content": f"今日国内和国际要闻来3条",
            }
        ]
    }

    try:
        result = await _retry_async(
            "agent.ainvoke",
            lambda: agent.ainvoke(request_payload, config={"recursion_limit": 6}),
            per_try_timeout_seconds=45.0,
        )
        if mcp_available and not _did_call_mcp(result, raw_tools):
            preferred_tool = "bing_search"
            available_names = [t.name for t in raw_tools]
            if preferred_tool not in available_names and available_names:
                preferred_tool = available_names[0]
            force_payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"必须调用 MCP 工具 `{preferred_tool}` 进行搜索后再回答。"
                            "请先调用工具，再基于工具结果给出今日热点。"
                        ),
                    }
                ]
            }
            print("[force] 首轮未调用 MCP，触发强制工具调用重试。")
            result = await _retry_async(
                "agent.ainvoke.force_mcp",
                lambda: agent.ainvoke(force_payload, config={"recursion_limit": 6}),
                per_try_timeout_seconds=45.0,
            )
    except Exception as e:
        print(f"[degrade] {_friendly_error_text(e)} 已切换纯模型回答。")
        fallback = await _retry_async(
            "model.ainvoke",
            lambda: model.ainvoke(request_payload["messages"]),
            per_try_timeout_seconds=25.0,
        )
        result = {"messages": [fallback]}

    print("\n=== Agent Message Trace ===")
    mcp_called = False
    for i, m in enumerate(result.get("messages", [])):
        role = getattr(m, "type", None) or getattr(m, "role", "unknown")
        name = getattr(m, "name", None)
        tool_calls = getattr(m, "tool_calls", None)
        content = getattr(m, "content", "")

        print(f"[{i}] role={role} name={name}")
        if tool_calls:
            print("  tool_calls =", tool_calls)
            for tc in tool_calls:
                tc_name = tc.get("name", "")
                if tc_name in [t.name for t in raw_tools]:
                    mcp_called = True
        if role == "tool" and name in [t.name for t in raw_tools]:
            mcp_called = True

        preview = str(content)
        if len(preview) > 300:
            preview = preview[:300] + "..."
        print("  content =", preview)

    print("\n=== MCP Called ===")
    print(mcp_called)
    print("=== MCP Available ===")
    print(mcp_available)

    print("\n=== Final Answer ===")
    final_text = _extract_final_text(result)
    if not final_text:
        final_text = "当前搜索服务不稳定，已降级返回结果，请稍后重试。"
    print(final_text)

if __name__ == "__main__":
    asyncio.run(main())
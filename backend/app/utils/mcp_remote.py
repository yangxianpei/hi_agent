from __future__ import annotations

import re
from typing import Any, Callable

from hello_agents.protocols.mcp.client import MCPClient
from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.builtin.mcp_wrapper_tool import MCPWrappedTool


class RemoteMCPTool(Tool):
    """
    远程 MCP 网关工具（Streamable HTTP / SSE / 等）

    - 连接远程 MCP Server（URL）
    - 自动发现 tools，并在 auto_expand=True 时展开为独立工具注册到 ToolRegistry
    """

    def __init__(
        self,
        *,
        name: str,
        url: str,
        transport_type: str = "http",
        auto_expand: bool = True,
        headers: dict[str, str] | None = None,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.url = url
        self.transport_type = transport_type
        self.auto_expand = auto_expand
        self.prefix = f"{name}_" if auto_expand else ""
        self._headers = headers or {}
        self._event_callback = event_callback

        self._available_tools: list[dict[str, Any]] = []
        self._tool_name_map: dict[str, str] = {}
        self._discover_tools()

        desc = (
            f"远程 MCP 网关（{transport_type}）：{url}。"
            + (f"已发现 {len(self._available_tools)} 个工具。" if self._available_tools else "")
        )
        super().__init__(name=name, description=desc, expandable=auto_expand)

    def _emit_event(self, payload: dict[str, Any]) -> None:
        if self._event_callback is None:
            return
        try:
            self._event_callback(payload)
        except Exception:
            pass

    def _discover_tools(self) -> None:
        try:
            import asyncio
            import concurrent.futures
            import time

            async def discover():
                async with MCPClient(
                    self.url, transport_type=self.transport_type, headers=self._headers
                ) as client:
                    return await client.list_tools()

            try:
                asyncio.get_running_loop()

                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(discover())
                    finally:
                        new_loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    self._available_tools = executor.submit(run_in_thread).result()
            except RuntimeError:
                self._available_tools = asyncio.run(discover())
        except Exception:
            self._available_tools = []

    @staticmethod
    def _sanitize_tool_name(name: str, index: int) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", (name or "").strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        if not cleaned:
            cleaned = f"tool_{index}"
        return cleaned

    def get_expanded_tools(self) -> list[Tool]:  # type: ignore[override]
        if not self.auto_expand:
            return []

        expanded: list[Tool] = []
        used_names: set[str] = set()
        for i, tool_info in enumerate(self._available_tools):
            original_name = tool_info.get("name", "")
            safe_name = self._sanitize_tool_name(original_name, i)
            base_name = safe_name
            suffix = 1
            while safe_name in used_names:
                suffix += 1
                safe_name = f"{base_name}_{suffix}"
            used_names.add(safe_name)
            self._tool_name_map[safe_name] = original_name

            exposed_tool_info = dict(tool_info)
            exposed_tool_info["name"] = safe_name
            expanded.append(
                MCPWrappedTool(
                    mcp_tool=self,  # MCPWrappedTool 会回调 self.run({"action":...})
                    tool_info=exposed_tool_info,
                    prefix=self.prefix,
                )
            )
        return expanded

    def run(self, params: dict[str, Any]) -> str:  # type: ignore[override]
        """
        MCPWrappedTool 会用以下结构调用：
          {"action":"call_tool","tool_name":"xxx","arguments":{...}}
        """
        action = (params.get("action") or "").lower()
        if action != "call_tool":
            return "错误：RemoteMCPTool 仅支持 call_tool"

        tool_name = params.get("tool_name")
        arguments = params.get("arguments", {})
        if not tool_name:
            return "错误：必须提供 tool_name"
        actual_tool_name = self._tool_name_map.get(str(tool_name), str(tool_name))
        self._emit_event(
            {
                "phase": "start",
                "source": "mcp",
                "tool_name": actual_tool_name,
                "arguments": arguments,
            }
        )

        try:
            import asyncio
            import concurrent.futures

            async def call():
                async with MCPClient(
                    self.url, transport_type=self.transport_type, headers=self._headers
                ) as client:
                    return await client.call_tool(actual_tool_name, arguments)

            result = None
            last_error: Exception | None = None
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    try:
                        asyncio.get_running_loop()

                        def run_in_thread():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                return new_loop.run_until_complete(call())
                            finally:
                                new_loop.close()

                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            result = executor.submit(run_in_thread).result()
                    except RuntimeError:
                        result = asyncio.run(call())
                    last_error = None
                    break
                except Exception as e:
                    last_error = e
                    msg = str(e)
                    retryable = (
                        "RemoteProtocolError" in msg
                        or "peer closed connection" in msg.lower()
                        or "ReadTimeout" in msg
                    )
                    if not retryable or attempt >= max_attempts:
                        break
                    self._emit_event(
                        {
                            "phase": "retry",
                            "source": "mcp",
                            "tool_name": actual_tool_name,
                            "attempt": attempt,
                            "reason": msg,
                        }
                    )
                    time.sleep(0.4 * attempt)

            if last_error is not None:
                raise last_error
        except Exception as e:
            self._emit_event(
                {
                    "phase": "error",
                    "source": "mcp",
                    "tool_name": actual_tool_name,
                    "error": str(e),
                }
            )
            return f"错误：调用远程 MCP 工具失败：{e}"

        self._emit_event(
            {
                "phase": "result",
                "source": "mcp",
                "tool_name": actual_tool_name,
                "result": result,
            }
        )
        formatted = self._format_result_for_markdown(actual_tool_name, result)
        return formatted

    @staticmethod
    def _format_result_for_markdown(tool_name: str, result: Any) -> str:
        """将常见 MCP 结果转换为更适合前端 Markdown 渲染的文本。"""
        if isinstance(result, dict):
            # 针对 bing_search 等搜索结果结构做友好展示
            items = result.get("results")
            query = result.get("query")
            total = result.get("totalResults")
            if isinstance(items, list):
                lines: list[str] = []
                if query:
                    lines.append(f"### 搜索结果：{query}")
                else:
                    lines.append("### 搜索结果")
                if total is not None:
                    lines.append(f"- 共约 `{total}` 条结果")
                lines.append("")

                for i, item in enumerate(items[:10], 1):
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get("title", "无标题")).strip()
                    url = str(item.get("url", "")).strip()
                    snippet = str(item.get("snippet", "")).strip()
                    if url:
                        lines.append(f"{i}. [{title}]({url})")
                    else:
                        lines.append(f"{i}. {title}")
                    if snippet:
                        lines.append(f"   - {snippet}")
                return "\n".join(lines)

        return f"工具 `{tool_name}` 执行结果：\n\n```json\n{result}\n```"

    def get_tools_function(self) -> list[dict[str, Any]]:
        # 使用实际暴露给 Agent 的安全名称（避免与 OpenAI function name 规则冲突）
        if self._tool_name_map:
            origin_to_tool = {t.get("name", ""): t for t in self._available_tools}
            result: list[dict[str, Any]] = []
            for safe_name, origin_name in self._tool_name_map.items():
                tool = origin_to_tool.get(origin_name, {})
                result.append(
                    {
                        "name": safe_name,
                        "origin_name": origin_name,
                        "description": tool.get("description", ""),
                        "input_schema": tool.get("input_schema", {}),
                    }
                )
            return result

        return [
            {
                "name": self._sanitize_tool_name(t.get("name", ""), i),
                "origin_name": t.get("name", ""),
                "description": t.get("description", ""),
                "input_schema": t.get("input_schema", {}),
            }
            for i, t in enumerate(self._available_tools)
        ]

    def get_parameters(self) -> list[ToolParameter]:  # type: ignore[override]
        return [
            ToolParameter(
                name="action",
                type="string",
                description="仅支持 call_tool",
                required=True,
            ),
            ToolParameter(
                name="tool_name",
                type="string",
                description="远程 MCP 工具名",
                required=True,
            ),
            ToolParameter(
                name="arguments",
                type="object",
                description="工具参数",
                required=False,
            ),
        ]


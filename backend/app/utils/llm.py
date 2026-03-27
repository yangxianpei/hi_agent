import os
from collections import deque
import re
from typing import Any

from dotenv import load_dotenv
# from hello_agents import  HelloAgentsLLM, ToolRegistry
# from app.utils.mcp_remote import RemoteMCPTool

load_dotenv()


class LLM:
    def __init__(self):
        pass
        # self._tool_events: deque[dict[str, Any]] = deque()
        # self._remote_mcp: RemoteMCPTool | None = None

        # llm = HelloAgentsLLM(
        #     model=os.getenv("LLM_MODEL_ID"),
        #     api_key=os.getenv("LLM_API_KEY"),
        #     base_url=os.getenv("LLM_BASE_URL"),
        # )

        # registry = ToolRegistry()
        # registry.register_function(
        #     func=self._get_weather_tool,
        #     name="get_weather",
        #     description="根据城市名查询天气，input 填城市名",
        # )
        # registry.register_function(
        #     func=self._get_today_date_tool,
        #     name="get_today_date",
        #     description="查询今天日期，查询今天时间等",
        # )

        # 加载远程 MCP（streamable_http）

        # self._remote_mcp = RemoteMCPTool(
        #     name="cn_search_mcp",
        #     url="https://mcp.api-inference.modelscope.net/397fabbd558d45/mcp",
        #     transport_type="http",
        #     auto_expand=True,
        #     event_callback=self._on_tool_event,
        # )
        # registry.register_tool(self._remote_mcp, auto_expand=True)
        # self.agent = FunctionCallAgent(
        #     llm=llm,
        #     name="chat",
        #     tool_registry=registry,
        #     system_prompt="你是智能助手。先判断用户意图，优先调用最相关的工具；无相关工具时再直接回答。",
        # )

    def _on_tool_event(self, event: dict[str, Any]) -> None:
        self._tool_events.append(event)

    def _get_weather_tool(self, input: str) -> str:
        self._tool_events.append(
            {"phase": "start", "tool_name": "get_weather", "input": input}
        )
        result = self.get_weather(input)
        self._tool_events.append(
            {"phase": "result", "tool_name": "get_weather", "result": result}
        )
        return result

    def _get_today_date_tool(self, input: str) -> str:
        self._tool_events.append(
            {"phase": "start", "tool_name": "get_today_date", "input": input}
        )
        result = self.get_today_date(input)
        self._tool_events.append(
            {"phase": "result", "tool_name": "get_today_date", "result": result}
        )
        return result

    def pop_tool_events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while self._tool_events:
            events.append(self._tool_events.popleft())
        return events

    def get_tools_function(self) -> list[dict[str, Any]]:
        if self._remote_mcp is None:
            return []
        return self._remote_mcp.get_tools_function()

    def chat(self, message: str, tool_choice: str | dict[str, Any] = "auto"):
        for chunk in self.agent.stream_run(message, tool_choice=tool_choice):
            if isinstance(chunk, str):
                yield self._execute_dsml_if_needed(chunk)
            else:
                yield chunk

    def _execute_dsml_if_needed(self, text: str) -> str:
        # 兜底兼容：部分模型会输出 DSML function_calls，而不是原生 tool_calls
        if "<｜DSML｜function_calls>" not in text:
            return text

        tool_registry = getattr(self.agent, "tool_registry", None)
        if tool_registry is None:
            return "检测到工具调用请求，但当前未配置工具注册表。"

        invoke_pattern = re.compile(
            r"<｜DSML｜invoke name=\"([^\"]+)\">(.*?)</｜DSML｜invoke>",
            re.S,
        )
        param_pattern = re.compile(
            r"<｜DSML｜parameter name=\"([^\"]+)\" string=\"(true|false)\">(.*?)</｜DSML｜parameter>",
            re.S,
        )

        outputs: list[str] = []
        for tool_name, invoke_body in invoke_pattern.findall(text):
            tool = tool_registry.get_tool(tool_name)
            if tool is None:
                outputs.append(f"工具不存在: {tool_name}")
                continue

            params: dict[str, Any] = {}
            for key, is_string, raw_value in param_pattern.findall(invoke_body):
                value = raw_value.strip()
                if is_string == "false":
                    try:
                        if "." in value:
                            params[key] = float(value)
                        else:
                            params[key] = int(value)
                    except ValueError:
                        if value.lower() in ("true", "false"):
                            params[key] = value.lower() == "true"
                        else:
                            params[key] = value
                else:
                    params[key] = value

            # 稳定性保护：远端搜索结果太大时容易触发 streamable_http 断流，限制返回条数
            if tool_name.endswith("bing_search"):
                count = params.get("count")
                if isinstance(count, (int, float)) and count > 5:
                    params["count"] = 5

            try:
                self._tool_events.append(
                    {"phase": "start", "source": "mcp", "tool_name": tool_name, "arguments": params}
                )
                result = tool.run(params)
                self._tool_events.append(
                    {"phase": "result", "source": "mcp", "tool_name": tool_name, "result": result}
                )
                outputs.append(f"[{tool_name}] {result}")
            except Exception as e:
                self._tool_events.append(
                    {"phase": "error", "source": "mcp", "tool_name": tool_name, "error": str(e)}
                )
                outputs.append(f"[{tool_name}] 调用失败: {e}")

        if not outputs:
            return "检测到 DSML 工具调用，但未解析到可执行的 invoke 节点。"
        return "\n\n".join(outputs)

    @staticmethod
    def get_weather(input: str) -> str:
        city = (input or "").strip() or "未知城市"
        fake_db = {
            "上海": "多云 24C，东南风 3级",
            "北京": "晴 18C，北风 2级",
            "深圳": "小雨 27C，南风 2级",
        }
        return f"{city}天气：{fake_db.get(city, '暂无数据')}"

    @staticmethod
    def get_today_date(input: str) -> str:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        return (
            f"今天是 {now:%Y-%m-%d}，"
            f"星期{['一', '二', '三', '四', '五', '六', '日'][now.weekday()]}"
            f"现在是 {now:%H:%M:%S}"
        )
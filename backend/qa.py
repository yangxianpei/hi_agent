import asyncio
from typing import Any

from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
load_dotenv()
# 1) 定义一个工具
@tool
def get_weather(city: str) -> str:
    """根据城市查询天气"""
    return f"{city}：晴，25C"


# 2) 定义“中间件”回调
class ToolTraceHandler(BaseCallbackHandler):
    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> Any:
        print(f"[tool_start] name={serialized.get('name')} input={input_str}")

    def on_tool_end(self, output: Any, **kwargs: Any) -> Any:
        print(f"[tool_end] output={str(output)[:120]}")

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> Any:
        print(f"[tool_error] error={error}")


async def main() -> None:
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL_ID", "deepseek-chat"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    agent = create_agent(
        model=llm,
        tools=[get_weather],
    )

    payload = {
        "messages": [
            {"role": "user", "content": "帮我查一下上海天气"},
        ]
    }

    # 3) 在调用时挂 callbacks（这就是 create_agent 的“中间件入口”）
    result = await agent.ainvoke(
        payload,
        config={"callbacks": [ToolTraceHandler()]},
    )

    # print("agent result:", result)


if __name__ == "__main__":
    asyncio.run(main())


import os
from langchain_openai import ChatOpenAI
class GenerateHeading:
    def __init__(self):
        self._llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL_ID", "deepseek-chat"),
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        )
    def generate_heading(self, text):
        prompt = f"请根据以下文本生成一个标题二级标题简短的标题，不要超过10个字,只返回标题，不要返回其他内容：{text}"
        response = self._llm.invoke(prompt)
        return response.content

    def generate_Ai_think(self, heading, text):
        prompt = f"请根据以下内容，围绕主题「{heading}」进行梳理，并给出专业、精炼的总结性答案：\n{text}"
        response = self._llm.invoke(prompt)
        return response.content

generate_heading = GenerateHeading()
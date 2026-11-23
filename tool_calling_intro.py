import os

import requests
from dotenv import load_dotenv

load_dotenv()

URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# 一张"工具菜单"：告诉模型你手上有哪些函数、每个函数干什么、要什么参数
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_candidate",
            "description": "按候选人姓名查询他的简历信息（学历、工作年限、城市、投递时间）",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "候选人姓名，例如：张三"}
                },
                "required": ["name"],
            },
        },
    }
]


def ask(messages):
    key = os.getenv("DEEPSEEK_API_KEY")
    body = {"model": MODEL, "messages": messages, "tools": TOOLS}
    resp = requests.post(
        URL,
        headers={"Authorization": f"Bearer {key}"},
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]


if __name__ == "__main__":
    message = ask([{"role": "user", "content": "张三有多少年工作经验？"}])
    print(message)

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "resumes.json"

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
    },
    {
        "type": "function",
        "function": {
            "name": "list_candidates_by_city",
            "description": "列出某个城市的所有候选人姓名",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，例如：上海"}
                },
                "required": ["city"],
            },
        },
    },
    {
        "type":"function",
        "function":{
            "name": "filter_candidates",
            "description": "按城市和最低工作年限筛选候选人，返回符合条件的人数与姓名",
            "parameters": {
                "type": "object",
                "properties":{
                    "city": {"type": "string", "description": "城市名，例如：上海"},
                    "min_years": {"type": "integer", "description": "最低工作年限，例如：2"}
                },
                "required": ["city", "min_years"]
                }
            }
        }
]


def get_candidate(name):
    resumes = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    for r in resumes:
        if r["name"] == name:
            return r
    return {"error": f"没有找到候选人 {name}"}


def list_candidates_by_city(city):
    resumes = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    names = [r["name"] for r in resumes if r["address"] == city]
    return {"city": city, "names": names}

def filter_candidates(city, min_years):
    resumes = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    names = [r["name"] for r in resumes if r["address"] == city and r["years"] >= min_years]
    return {"city": city, "min_years": min_years, "names": names}

def run_tool(name, arguments):
    if name == "get_candidate":
        args = json.loads(arguments)
        return get_candidate(args["name"])
    if name == "list_candidates_by_city":
        args = json.loads(arguments)
        return list_candidates_by_city(args["city"])
    if name == "filter_candidates":
        args = json.loads(arguments)
        return filter_candidates(args["city"], args["min_years"])
    return {"error": f"未知工具 {name}"}


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


MAX_ROUNDS = 5


def run_agent(messages):
    for i in range(MAX_ROUNDS):
        message = ask(messages)

        if "tool_calls" not in message:
            messages.append({"role": "assistant", "content": message["content"]})
            return message["content"]

        messages.append(
            {
                "role": "assistant",
                "content": message.get("content") or "",
                "tool_calls": message["tool_calls"],
            }
        )

        for call in message["tool_calls"]:
            result = run_tool(call["function"]["name"], call["function"]["arguments"])
            print(f"  第 {i + 1} 轮，调用 {call['function']['name']}，得到：{result}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return "轮次太多，先停一下"


if __name__ == "__main__":
    messages = [
        {"role": "system", "content": "你是招聘助手。回答简洁，只回答被问到的内容，不超过 60 字。"}
    ]
    print("输入 exit 退出")
    while True:
        text = input("你：")
        if text == "exit":
            break
        messages.append({"role": "user", "content": text})
        answer = run_agent(messages)
        print(f"助手：{answer}")

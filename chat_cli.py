import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

BASE = Path(__file__).parent
RESULT_FILE = BASE / "output" / "screening_result.json"

HISTORY_LIMIT = 6


def load_background():
    if not RESULT_FILE.exists():
        return ""
    return RESULT_FILE.read_text(encoding="utf-8")


def ask(messages):
    key = os.getenv("DEEPSEEK_API_KEY")
    body = {"model": MODEL, "messages": messages}
    resp = requests.post(
        URL,
        headers={"Authorization": f"Bearer {key}"},
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def main():
    system_text = "你是招聘助手，回答简洁，不超过 50 字。"
    background = load_background()
    if background:
        system_text += f"\n以下是最近的简历筛选结果，回答以它为准：\n{background}"
    messages = [{"role": "system", "content": system_text}]
    print("输入 exit 退出")
    while True:
        text = input("你：")
        if text == "exit":
            break
        messages.append({"role": "user", "content": text})
        answer = ask([messages[0]] + messages[-HISTORY_LIMIT:])
        print(f"助手：{answer}")
        messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()

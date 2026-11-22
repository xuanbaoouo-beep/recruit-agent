import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

INPUT_PRICE = 2 / 1_000_000
OUTPUT_PRICE = 8 / 1_000_000


def ask(question, timeout=60):
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        print("错误：.env 里没有 DEEPSEEK_API_KEY")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {key}"}
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是一个说话很冲的面试官，回答不超过15个字。"},
            {"role": "user", "content": question},
        ],
    }

    try:
        r = requests.post(URL, headers=headers, json=body, timeout=timeout)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        print("错误：请求超时，检查网络")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"错误：请求失败 {e}")
        sys.exit(1)

    return r.json()


def main():
    if len(sys.argv) < 2:
        print("用法：python ask_llm.py 你的问题")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    data = ask(question)

    print(data["choices"][0]["message"]["content"])

    usage = data["usage"]
    cost = usage["prompt_tokens"] * INPUT_PRICE + usage["completion_tokens"] * OUTPUT_PRICE
    print(f"\n[tokens] 输入 {usage['prompt_tokens']}，输出 {usage['completion_tokens']}，合计 {usage['total_tokens']}")
    print(f"[成本] 约 {cost:.6f} 元")


if __name__ == "__main__":
    main()

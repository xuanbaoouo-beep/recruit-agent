import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

BASE = Path(__file__).parent
JD_FILE = BASE / "data" / "jd.txt"


def make_questions(jd, resume_text=""):
    key = os.getenv("DEEPSEEK_API_KEY")
    user_text = f"岗位要求：\n{jd}"
    if resume_text:
        user_text += f"\n\n候选人简历：\n{resume_text}"
    body = {
        "model": MODEL,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": '你是面试官。根据岗位要求出 5 道面试题；如果同时给了候选人简历，题目要针对这位候选人的经历和技能缺口来问。只输出 JSON 对象，不要任何其他文字，格式：{"questions": ["题目1", "题目2", "题目3", "题目4", "题目5"]}',
            },
            {"role": "user", "content": user_text},
        ],
    }
    resp = requests.post(
        URL,
        headers={"Authorization": f"Bearer {key}"},
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return json.loads(data["choices"][0]["message"]["content"]), data["usage"]


def main():
    jd = JD_FILE.read_text(encoding="utf-8")
    result, usage = make_questions(jd)
    for q in result["questions"]:
        print(f"- {q}")
    print(f"\n[tokens] 输入 {usage['prompt_tokens']}，输出 {usage['completion_tokens']}")

    today = datetime.now().strftime("%Y-%m-%d")
    out_file = BASE / "output" / f"interview_questions_{today}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入：{out_file}")


if __name__ == "__main__":
    main()

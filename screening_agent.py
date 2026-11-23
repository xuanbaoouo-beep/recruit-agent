import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

from interview_questions import make_questions

load_dotenv()

URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

INPUT_PRICE = 2 / 1_000_000
OUTPUT_PRICE = 8 / 1_000_000

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "resumes.json"
OUTPUT_FILE = BASE / "output" / "screening_result.json"
CSV_FILE = BASE / "output" / "screening_result.csv"
LOG_DIR = BASE / "logs"


def write_log(text):
    now = datetime.now()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{now.strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{now.strftime('%H:%M:%S')}] {text}\n")


def resume_to_text(r):
    return (
        f"姓名：{r['name']}\n"
        f"学历：{r['degree']}\n"
        f"工作年限：{r['years']} 年\n"
        f"城市：{r['address']}\n"
        f"投递时间：{r['applied_at']}"
    )


def screen(r, jd):
    key = os.getenv("DEEPSEEK_API_KEY")
    body = {
        "model": MODEL,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": '你是招聘筛选助手。根据岗位要求判断候选人是否合适。只输出一个 JSON 对象，不要任何其他文字，格式：{"match": true 或 false, "reason": "一句理由"}。',
            },
            {"role": "user", "content": f"岗位要求：{jd}\n\n候选人简历：\n{resume_to_text(r)}"},
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
    usage = data["usage"]
    return json.loads(data["choices"][0]["message"]["content"]), usage


def screen_with_retry(r, jd):
    for i in range(3):
        try:
            return screen(r, jd)
        except Exception as e:
            print(f"  {r['name']} 第 {i + 1} 次失败：{e}")
            write_log(f"{r['name']} 第 {i + 1} 次失败：{e}")
    return {"match": False, "reason": "重试 3 次仍失败"}, {"prompt_tokens": 0, "completion_tokens": 0}


def main():
    if len(sys.argv) > 1:
        jd = sys.argv[1]
    else:
        jd = "数据分析师：硕士及以上学历，2 年以上经验，工作地点上海。"

    with open(DATA_FILE, encoding="utf-8") as f:
        resumes = json.load(f)

    write_log(f"开始筛选，共 {len(resumes)} 份简历，JD：{jd}")

    total_input = 0
    total_output = 0

    results = []
    interview_items = []
    for r in resumes:
        result, usage = screen_with_retry(r, jd)
        total_input += usage["prompt_tokens"]
        total_output += usage["completion_tokens"]
        if result["match"]:
            label = "匹配"
        else:
            label = "不匹配"
        results.append({"name": r["name"], "match": result["match"], "reason": result["reason"]})
        print(f"{r['name']}：{label}（{result['reason']}）")
        write_log(f"{r['name']}：{label}（{result['reason']}）")

        if result["match"]:
            q_result, q_usage = make_questions(jd, resume_to_text(r))
            total_input += q_usage["prompt_tokens"]
            total_output += q_usage["completion_tokens"]
            interview_items.append({"name": r["name"], "questions": q_result["questions"]})
            print(f"  已为 {r['name']} 生成 {len(q_result['questions'])} 道面试题")
            write_log(f"已为 {r['name']} 生成 {len(q_result['questions'])} 道面试题")

    results.sort(key=lambda x: x["match"], reverse=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"已写入：{OUTPUT_FILE}")

    with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["姓名", "是否匹配", "理由"])
        for item in results:
            writer.writerow([item["name"], item["match"], item["reason"]])
    print(f"已写入：{CSV_FILE}")

    if interview_items:
        today = datetime.now().strftime("%Y-%m-%d")
        interview_file = BASE / "output" / f"interview_questions_{today}.json"
        interview_file.write_text(
            json.dumps(interview_items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"已写入：{interview_file}")

    cost = total_input * INPUT_PRICE + total_output * OUTPUT_PRICE
    print(f"[成本] 输入 {total_input} tokens，输出 {total_output} tokens，约 {cost:.6f} 元")
    write_log(f"筛选结束，输入 {total_input} tokens，输出 {total_output} tokens，约 {cost:.6f} 元")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        write_log(f"程序异常退出：{e}")
        print(f"出错了：{e}")
        print(f"详情已写入 {LOG_DIR}")
        sys.exit(1)

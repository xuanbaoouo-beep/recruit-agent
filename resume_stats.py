import json
from pathlib import Path

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "resumes.json"
OUTPUT_FILE = BASE / "output" / "summary.json"

# 把json文件读取出来  并从str转为它原有的格式
def load_resumes(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[警告] 找不到文件：{path}，已按空名单处理")
        return []


def count_degrees(resumes):
    counts = {}
    for r in resumes:
        degree = r["degree"]
        counts[degree] = counts.get(degree, 0) + 1 #counts{"degree" : 0}
    return counts


def top_by_years(resumes, limit=5):
    ordered = sorted(resumes, key=lambda r: r["years"], reverse=True)
    return [f'{r["name"]}({r["years"]})' for r in ordered[:limit]]


def main():
    resumes = load_resumes(DATA_FILE)
    print(f"总人数：{len(resumes)}")

    degrees = count_degrees(resumes)
    print("学历分布：" + "，".join(f"{k} {v} 人" for k, v in degrees.items()))

    print("按年限排序：" + " ".join(top_by_years(resumes)))

    summary = {
        "total": len(resumes),
        "degrees": degrees,
        "top": top_by_years(resumes),
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2) # json.dump是把其他格式转为json格式
    print(f"已写入：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()


# with open("./data.json", encoding="utf-8") as f:
#     text = f.read()

# data = json.loads(text)
# print(data[0])
# print(type(data))

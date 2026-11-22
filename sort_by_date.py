import json

with open("data/resumes.json", encoding="utf-8") as f:
    data = json.load(f)

ordered = sorted(data, key=lambda r: r["applied_at"])

lines = [f'{r["applied_at"]} {r["name"]}' for r in ordered]
print("\n".join(lines))

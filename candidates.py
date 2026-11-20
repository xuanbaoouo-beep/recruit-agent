candidates = [
    {"name":"张三", "degree":"本科","years":3,"address":"北京"},
    {"name":"李四", "degree":"硕士","years":2,"address":"上海"},
    {"name":"王五", "degree":"大专","years":1,"address":"北京"}
]

for i, c in enumerate(candidates, start=1):
    print(f"{i}. {c['name']} | {c['degree']} | {c['years']}年 | {c['address']}")

print(f"共 {len(candidates)}人")
print(candidates[0]["name"])
for i, c in enumerate(candidates, start=1):
    if i ==1:
        print(c["name"])

for c in candidates:
    if c["degree"] == "本科":
        print(c["name"])
    
candidates[0]["email"] = "a@b.com"
print(candidates[0]["email"])


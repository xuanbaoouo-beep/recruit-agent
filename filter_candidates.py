candidates = [
    {"name":"张三", "degree":"本科","years":3,"address":"北京"},
    {"name":"李四", "degree":"硕士","years":2,"address":"上海"},
    {"name":"王五", "degree":"大专","years":1,"address":"北京"},
    {"name":"赵六", "degree":"本科","years":3,"address":"上海"},

]

matched =[]
for c in candidates:
    if c['degree'] == "本科" and c.get("years", 0) >=3:
        matched.append(c)
name = "-".join(c["name"] for c in matched)
print(f"符合条件：{name}")
print(f"符合 {len(matched)} 人，不符合 {len(candidates) - len(matched)} 人")


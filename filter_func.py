def filter_candidates(cands, degree="本科", min_years=3):
    res = []
    for c in cands:
        if c['degree'] == degree and c.get("years", 0) >= min_years:
            res.append(c)
    return res

def summarize(matched:[], total:int):
    return f"符合条件{len(matched)}人, 不符合条件{total - len(matched)}人"

candidates = [
    {"name":"张三", "degree":"本科","years":3,"address":"北京"},
    {"name":"李四", "degree":"硕士","years":2,"address":"上海"},
    {"name":"王五", "degree":"大专","years":1,"address":"北京"},
    {"name":"赵六", "degree":"本科","years":3,"address":"上海"},
]

def main():
    bachelor = filter_candidates(candidates)                         
    masters = filter_candidates(candidates, "硕士", 2)               
    fresh = filter_candidates(candidates, min_years=0)               
    print("-".join(c["name"] for c in bachelor))
    print("-".join(c["name"] for c in masters))
    print("-".join(c["name"] for c in fresh))

    print(summarize(bachelor, len(candidates)))


if __name__ == "__main__":
    main()
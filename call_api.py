import requests

resp = requests.post(
    "http://localhost:8000/ask",
    json={"question": "张三几年经验？"},
    timeout=60,
)
print("状态码：", resp.status_code)
print("结果：", resp.json())

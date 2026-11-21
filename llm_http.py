import os
import requests
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("DEEPSEEK_API_KEY")

#手写用http调llm
url = "https://api.deepseek.com/chat/completions"
headers = {"Authorization": f"Bearer {key}"}
body = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "用一句话解释什么是 AI Agent"}],
}

r = requests.post(url, headers=headers, json=body, timeout=60)
print(r.status_code)
print(r.json())
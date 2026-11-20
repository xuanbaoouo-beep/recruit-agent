import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "用一句话解释什么是 AI Agent"}],
    temperature=1.3,
)
print(resp.choices[0].message.content)
print("tokens:", resp.usage.total_tokens)

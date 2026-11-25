import requests

URL = "http://localhost:8000/ask"


def ask(session_id, question):
    resp = requests.post(
        URL,
        json={"session_id": session_id, "question": question},
        timeout=60,
    )
    print(f"[{session_id}] 问：{question}")
    print(f"[{session_id}] 答：{resp.json()}")
    print()


ask("u001", "张三几年经验？")
ask("u001", "那他学历是什么？")
ask("u002", "那他学历是什么？")

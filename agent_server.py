import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent_with_tools import run_agent
from screening_agent import write_log

app = FastAPI()

SYSTEM_TEXT = "你是招聘助手。回答简洁，只回答被问到的内容，不超过 60 字。"

SESSIONS = {}

HISTORY_LIMIT = 8


class AskRequest(BaseModel):
    session_id: str = "default"
    question: str


@app.get("/")
def home():
    return {"message": "招聘 Agent 服务已启动"}


@app.post("/ask")
def ask_agent(payload: AskRequest):
    start = time.time()
    messages = SESSIONS.setdefault(
        payload.session_id,
        [{"role": "system", "content": SYSTEM_TEXT}],
    )
    messages.append({"role": "user", "content": payload.question})

    to_send = [messages[0]] + messages[-HISTORY_LIMIT:]

    try:
        answer = run_agent(to_send)
    except Exception as e:
        write_log(f"/ask 失败：{e}")
        raise HTTPException(status_code=500, detail="Agent 调用失败，请稍后再试")

    messages.append({"role": "assistant", "content": answer})

    used = time.time() - start
    write_log(
        f"/ask 会话：{payload.session_id}｜问题：{payload.question}｜"
        f"耗时 {used:.1f} 秒｜存了 {len(messages)} 条，本次发送 {len(to_send)} 条｜"
        f"回答 {len(answer)} 字"
    )
    return {"answer": answer, "session_id": payload.session_id}

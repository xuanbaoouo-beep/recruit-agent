import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent_with_tools import run_agent
from screening_agent import write_log

app = FastAPI()


class AskRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {"message": "招聘 Agent 服务已启动"}


@app.post("/ask")
def ask_agent(payload: AskRequest):
    start = time.time()
    messages = [
        {"role": "system", "content": "你是招聘助手。回答简洁，只回答被问到的内容，不超过 60 字。"},
        {"role": "user", "content": payload.question},
    ]
    try:
        answer = run_agent(messages)
    except Exception as e:
        write_log(f"/ask 失败：{e}")
        raise HTTPException(status_code=500, detail="Agent 调用失败，请稍后再试")

    used = time.time() - start
    write_log(f"/ask 问题：{payload.question}｜耗时 {used:.1f} 秒｜回答 {len(answer)} 字")
    return {"answer": answer}

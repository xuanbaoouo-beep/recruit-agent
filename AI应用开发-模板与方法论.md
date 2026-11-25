# AI 应用开发：模板与方法论总结（第 1–10 周）

> 项目：`recruit-agent`（简历筛选 + 面试题生成 + 工具调用 Agent + HTTP 服务 + 网页聊天界面）
> 适用：调用大模型 API 做业务自动化。所有模板都来自你自己写过的代码，可直接复制改造。

---

## 一、能力地图（你现在会的东西）

| 能力 | 在项目里用在哪 | 对应文件 |
|---|---|---|
| 变量、list、dict、if、函数 | 所有逻辑 | 全部 |
| 读文件 / 写文件 / JSON 互转 | 读简历、写结果 | `screening_agent.py` |
| try / except + 重试 | 接口失败兜底 | `screening_agent.py` |
| requests 发 HTTP 请求 | 调 DeepSeek | `ask_llm.py` |
| venv + 依赖锁版本 | 环境隔离 | `requirements.txt` |
| sorted(key=lambda) | 匹配的排前面 | `screening_agent.py` |
| 列表推导、join | 文本拼接 | 多个文件 |
| 自己写模块 + import | 出题复用 | `chat_cli.py` ← `interview_questions.py` |
| datetime + 追加写日志 | 运行记录 | `screening_agent.py` |
| messages 多轮对话 + 上下文裁剪 | 招聘助手追问 | `chat_cli.py` |
| 参数默认值 | 出题函数两用 | `interview_questions.py` |
| 切片 `[-6:]` | 控制上下文长度 | `chat_cli.py` |
| 工具调用（`tools` / `tool_calls`） | 模型自己选工具查数据 | `agent_with_tools.py` |
| Agent 循环 + 跨轮共享历史 | 追问式招聘助手 | `agent_with_tools.py` |
| FastAPI 起服务 + 自动文档 | 让别人调你的接口 | `agent_server.py` |
| BaseModel 请求校验（422） | 不合规请求自动拦截 | `agent_server.py` |
| 接口异常处理 + 耗时日志 | 上线后能排障 | `agent_server.py` |
| git 提交 + SSH 推送到 GitHub | 代码进仓库 | `.git/config`、`README.md` |
| 服务端会话记忆（`session_id` + dict） | 接口能记住上下文 | `agent_server.py` |
| 服务端历史裁剪 | 控制 token 与超长 | `agent_server.py` |
| SQLite 建库 + 参数化查询 | 简历查询换成查表 | `init_db.py`、`agent_with_tools.py` |
| HTML / CSS / JS + `fetch` | 网页对话框 | `web/chat.html` |
| `localStorage` 存会话号 | 每人一条独立对话 | `web/chat.html` |
| `--host 0.0.0.0` 局域网访问 | 手机调你的服务 | 启动命令 |

---

## 二、总方法论：调大模型永远是这五步

不管需求是筛选、出题、问答、分类、摘要，代码骨架都是同一个：

```
1. 准备输入      → 把业务数据拼成字符串
2. 组装 messages → system 放规则，user 放数据
3. 发 POST       → requests.post(URL, headers=带key, json=body)
4. 取结果        → data["choices"][0]["message"]["content"]
5. 解析 + 落地   → json.loads(...) → 写文件 / 判断 / 继续下一步
```

**一句话记住：规则放 system，数据放 user，结果从 `choices` 里挖。**

你三个脚本（`ask_llm.py`、`screening_agent.py`、`interview_questions.py`）本质是同一段代码，只换了 prompt 和 JSON 格式。

---

## 三、可复用模板

### 模板 1：最小调用（所有项目的起点）

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()
URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


def ask(question):
    key = os.getenv("DEEPSEEK_API_KEY")
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是助手，回答不超过 50 字。"},
            {"role": "user", "content": question},
        ],
    }
    resp = requests.post(URL, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
```

要点：
- key 只从 `.env` 读，绝不写死在代码里，`.env` 进 `.gitignore`
- `timeout=60` 必写，否则网络卡住程序永远不返回
- `raise_for_status()` 让 4xx/5xx 变成异常，才能被 try/except 抓到

### 模板 2：结构化输出（要程序能用，就要 JSON）

```python
body = {
    "model": MODEL,
    "response_format": {"type": "json_object"},   # 强制只返回 JSON 对象
    "messages": [
        {"role": "system", "content": '只输出 JSON，格式：{"match": true 或 false, "reason": "一句理由"}'},
        {"role": "user", "content": f"岗位要求：{jd}\n\n候选人简历：\n{resume_text}"},
    ],
}
result = json.loads(resp.json()["choices"][0]["message"]["content"])
```

三条铁律：
1. `response_format` 开 JSON 模式
2. prompt 里**明确写出字段名和类型**，最好给一个示例
3. 一定 `json.loads`，不要用字符串切分去猜

### 模板 3：失败重试 + 兜底（不重试的脚本不能上线）

```python
def screen_with_retry(r, jd):
    for i in range(3):
        try:
            return screen(r, jd)
        except Exception as e:
            print(f"  第 {i + 1} 次失败：{e}")
    return {"match": False, "reason": "重试 3 次仍失败"}, {"prompt_tokens": 0, "completion_tokens": 0}
```

原则：**失败要给一个"能继续往下走"的默认值**，不能让一个人失败就整批停掉。

### 模板 4：成本核算（每个调用都要算钱）

```python
INPUT_PRICE = 2 / 1_000_000     # 元 / token
OUTPUT_PRICE = 8 / 1_000_000
usage = data["usage"]
cost = usage["prompt_tokens"] * INPUT_PRICE + usage["completion_tokens"] * OUTPUT_PRICE
```

批量任务里累加 `total_input / total_output`，跑完打印总成本。**知道一次跑多少钱，才敢放开跑。**

### 模板 5：批量处理（遍历 + 收集 + 排序）

```python
results = []
for r in resumes:
    result, usage = screen_with_retry(r, jd)
    total_input += usage["prompt_tokens"]
    total_output += usage["completion_tokens"]
    results.append({"name": r["name"], "match": result["match"], "reason": result["reason"]})

results.sort(key=lambda x: x["match"], reverse=True)   # 匹配的排前面
```

### 模板 6：结果落地（JSON + CSV 双份）

```python
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["姓名", "是否匹配", "理由"])
    for item in results:
        writer.writerow([item["name"], item["match"], item["reason"]])
```

- JSON 给程序读，CSV 给 HR 用 Excel 打开
- CSV 必须 `utf-8-sig`，否则 Excel 中文乱码

### 模板 7：多轮对话（历史就是一个不断变长的列表）

```python
messages = [{"role": "system", "content": system_text}]
while True:
    text = input("你：")
    if text == "exit":
        break
    messages.append({"role": "user", "content": text})
    answer = ask(messages)
    print(f"助手：{answer}")
    messages.append({"role": "assistant", "content": answer})
```

**模型自己零记忆**：每次请求都把整个 `messages` 重新发一遍，它才"记得"。

### 模板 8：上下文裁剪（控制成本与长度）

```python
HISTORY_LIMIT = 6
answer = ask([messages[0]] + messages[-HISTORY_LIMIT:])   # system 永远保留 + 最近 6 条
```

- `messages[0]` 是 system，单独拼回来，否则被切掉模型就失忆成通用机器人
- 结论：**关键背景放 system（永不裁），闲聊放对话（可裁）**

### 模板 9：背景资料注入（RAG 雏形）

```python
background = RESULT_FILE.read_text(encoding="utf-8") if RESULT_FILE.exists() else ""
system_text = "你是招聘助手。以下是最近的筛选结果，回答以它为准：\n" + background
```

先找资料 → 塞进 prompt → 让模型基于资料答。这就是最小版 RAG。

### 模板 10：运行日志（追加写，一天一个文件）

```python
def write_log(text):
    now = datetime.now()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{now.strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{now.strftime('%H:%M:%S')}] {text}\n")
```

- `"a"` 追加，`"w"` 覆盖 —— 日志必须用 `"a"`
- 终端会关，日志不会

### 模板 11：入口兜底（整程序级 try/except）

```python
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        write_log(f"程序异常退出：{e}")
        print(f"出错了：{e}")
        sys.exit(1)
```

`sys.exit(1)` 告诉外部"这次失败"，将来放服务器定时跑时靠它报警。

### 模板 12：文件读写四件套

| 场景 | 写法 |
|---|---|
| 读纯文本 | `Path(...).read_text(encoding="utf-8")` |
| 写纯文本 | `Path(...).write_text(s, encoding="utf-8")` |
| 读 JSON 文件 | `with open(...) as f: json.load(f)` |
| 写 JSON 文件 | `with open(...) as f: json.dump(x, f, ensure_ascii=False)` |
| 数据和字符串互转 | `json.dumps(x)` / `json.loads(s)` |

记忆：**带 s 的处理字符串，不带 s 的处理文件。**

### 模板 13：复用自己写的代码（模块拆分）

```python
from interview_questions import make_questions
```

- 文件名去掉 `.py` 就是模块名
- 被 import 时只执行顶层代码，`if __name__ == "__main__"` 下面的 `main()` 不会跑
- 一个文件既"能单独运行"又"能被别人调用"，靠的就是这行判断

### 模板 14：工具菜单（`tools` 参数）

```python
TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_candidate",
        "description": "按姓名查候选人简历，返回学历、年限、城市、投递时间",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "候选人姓名，例如：张三"}
            },
            "required": ["name"],
        },
    },
}]

body = {"model": MODEL, "messages": messages, "tools": TOOLS}
```

三条铁律：
1. `description` 不是注释，**是给模型的说明书**，写歪了它就选错工具
2. `required` 里的参数模型必须填；没填它就不敢调（所以"先查名单再按名字查"只能分两轮）
3. 类型写准：`string` / `integer`，别全写成 string

### 模板 15：执行点单并回传（`role=tool`）

```python
def run_tool(name, arguments):
    if name == "get_candidate":
        args = json.loads(arguments)      # 坑：arguments 是字符串，不是 dict
        return get_candidate(args["name"])
    return {"error": f"未知工具 {name}"}

messages.append({                          # ① 模型那份点单，原样入历史
    "role": "assistant",
    "content": message.get("content") or "",
    "tool_calls": message["tool_calls"],
})
for call in message["tool_calls"]:         # ② 一轮可能要多个工具，必须 for
    result = run_tool(call["function"]["name"], call["function"]["arguments"])
    messages.append({
        "role": "tool",                    # ③ 新角色，专放工具结果
        "tool_call_id": call["id"],        # ④ 对号，一次多个调用时靠它分清
        "content": json.dumps(result, ensure_ascii=False),
    })
```

模型**从不执行你的代码**，它只输出"我要调什么、参数填什么"，真正干活的是 `run_tool`。

### 模板 16：Agent 循环（跑到模型不要工具为止）

```python
MAX_ROUNDS = 5

def run_agent(messages):
    for _ in range(MAX_ROUNDS):
        message = ask(messages)
        if "tool_calls" not in message:                    # 唯一的正常出口
            messages.append({"role": "assistant", "content": message["content"]})
            return message["content"]
        # 点单入历史 → 逐个执行 → 结果入历史（同模板 15）
    return "轮次太多，先停一下"                             # 保险丝
```

- 内层 `for` 转完 ≠ 结束，它只干完"这一轮的活"
- 跳出条件不是你说 exit，是**模型自己说"我够了"**
- `MAX_ROUNDS` 防死循环烧钱，别省

### 模板 17：FastAPI 最小服务

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")                       # GET：浏览器地址栏能直接打开
def home():
    return {"message": "服务已启动"}

@app.post("/ask")                   # POST：必须带请求体，地址栏打不开（405）
def ask_agent(payload: AskRequest):
    ...
```

```powershell
.\.venv\Scripts\python.exe -m uvicorn agent_server:app --reload --port 8000
```

- `agent_server:app` = 文件里的 `app` 变量，所以**必须在项目目录下启动**
- `/docs` 自带交互式文档，同事不用你写说明书
- 返回 dict 自动变 JSON，不用 `json.dumps`
- 服务是**无状态**的：每次请求都是新人，多轮对话要靠 `session_id` 自己存

### 模板 18：请求校验（BaseModel + 422）

```python
from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str
```

| 状态码 | 谁的错 | 谁产生 |
|---|---|---|
| 200 | 正常 | 你的函数 |
| 422 | **调用方**传错/少传 | FastAPI 自动，一行 if 都不用写 |
| 500 | **你的程序**崩了 | 你的 except 主动 raise |

### 模板 19：接口日志 + 异常处理

```python
try:
    answer = run_agent(messages)
except Exception as e:
    write_log(f"/ask 失败：{e}")                  # 细节记给自己
    raise HTTPException(status_code=500, detail="服务内部错误，请稍后再试")

write_log(f"/ask 问题：{payload.question}｜耗时 {used:.1f} 秒")
```

**对用户说人话，对自己留证据。** 异常原文里可能有文件路径、key 片段，绝不能直接返回给调用方。

### 模板 20：服务端会话记忆（`session_id` + 柜子）

```python
SESSIONS = {}                                  # 储物柜：键=会话号，值=messages

class AskRequest(BaseModel):
    session_id: str = "default"                # 默认值 = 不传也能跑（会产生串台风险）
    question: str

messages = SESSIONS.setdefault(
    payload.session_id,
    [{"role": "system", "content": SYSTEM_TEXT}],
)                                              # 有抽屉就取出，没有就新建并放回
messages.append({"role": "user", "content": payload.question})
```

- 模型**看不到** `session_id`，它只看到 `messages`
- 键里放什么由你定：放用户 id = 一人一线；放会话 id = 一人多线
- **存在内存里**：uvicorn 一重启全清空，多进程也互不可见 → 真上线要换 Redis/数据库

### 模板 21：服务端裁剪（存全量，发窗口）

```python
HISTORY_LIMIT = 8

to_send = [messages[0]] + messages[-HISTORY_LIMIT:]   # 新列表：system + 最近 8 条
answer = run_agent(to_send)
messages.append({"role": "assistant", "content": answer})   # 必须自己存回柜子
```

**关键坑**：`run_agent` 内部的 `append` 只落在你传进去的 `to_send` 上，用完就扔。不自已补这一行，柜子里就只有 user 没有 assistant，下一轮模型会看到"问了没人答"。

好处：工具调用中间消息（`tool_calls`、`role=tool`）也一起被丢掉，柜子只留人话，省 token。

### 模板 22：SQLite 建库 + 参数化查询

```python
import sqlite3

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS candidates (
    name TEXT PRIMARY KEY,
    degree TEXT,
    years INTEGER,
    address TEXT,
    applied_at TEXT
)
""")
cur.execute("DELETE FROM candidates")          # 让脚本可重复跑
rows = [(r["name"], r["degree"], r["years"], r["address"], r["applied_at"]) for r in resumes]
cur.executemany("INSERT INTO candidates VALUES (?, ?, ?, ?, ?)", rows)
conn.commit()
conn.close()
```

```python
def query(sql, params=()):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row             # 不加这行，结果只能 r[0] 不能 r["name"]
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

cur.execute("SELECT name FROM candidates WHERE address = ? AND years >= ?", ("上海", 2))
```

- `?` 占位符防 SQL 注入，也免去引号转义，**永远别用字符串拼接 SQL**
- 单元素元组必须带逗号：`(name,)`
- 写入必须 `commit()`
- `*.db` 进 `.gitignore`：数据库可再生产，仓库里放生成它的代码

### 模板 23：网页聊天（HTML + `fetch`）

```javascript
async function askAgent(text) {
  const resp = await fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sid, question: text }),
  });
  if (!resp.ok) return "服务出错了，状态码 " + resp.status;
  const data = await resp.json();
  return data.answer;
}
```

| JavaScript | Python 对应物 |
|---|---|
| `fetch(url, {...})` | `requests.post(url, ...)` |
| `JSON.stringify(x)` | `json.dumps(x)` |
| `await resp.json()` | `resp.json()` |
| `async` / `await` | "这里要等网络"，**必须成对出现** |
| `document.getElementById("id")` | 按 id 抓住页面元素 |
| `el.textContent = s` | 塞纯文本（**别用 innerHTML，会执行 HTML，XSS 来源**） |

```javascript
let sid = localStorage.getItem("sid");
if (!sid) { sid = "web-" + Math.random().toString(36).slice(2, 8); localStorage.setItem("sid", sid); }
```

- `localStorage` 存在浏览器里，关掉再开还在，只能存字符串
- "新对话"按钮 = 换个新 `sid` + 清空消息区，服务端那头历史自然断掉
- 前端传来的 `sid` 用户能改，**不能当登录凭证用**

### 模板 24：让别的设备访问（局域网）

```powershell
.\.venv\Scripts\python.exe -m uvicorn agent_server:app --reload --host 0.0.0.0 --port 8000
```

- `127.0.0.1` 只有本机能连；`0.0.0.0` 网卡上的所有地址都听
- 手机连同一 WiFi，访问 `http://<本机IP>:8000/chat`
- 查本机 IP：`Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, IPAddress`
- 打不开先看防火墙入站规则，再看是不是校园网的"客户端隔离"

---

## 四、方法论：拿到一个新需求，按这 6 步做

```
① 定输入输出    输入是什么（文本/JSON/表格）？输出要什么字段？（先写在纸上）
② 写 prompt     规则放 system，数据放 user；要求 JSON 就给示例
③ 单条跑通      先用 1 条数据跑，肉眼确认结果对不对
④ 代码落地      解析 JSON → 判断/汇总 → 写文件
⑤ 加防护        重试 + 兜底 + 入口 try/except + 日志
⑥ 加成本        统计 token 和费用，确认能承受再批量跑
```

顺序不能反：**先用一条数据把质量调对，再谈批量和性能。** 反过来做会浪费钱。

**什么时候该上工具调用，而不是把数据塞进 prompt？** 满足任意一条就值得：

1. 数据量超过 prompt 能舒服装下的量（几百份简历、几万行表）
2. 数据会变、要查实时值（数据库、别人的接口、今天的库存）
3. 参数依赖上一步结果（先查有哪些人，再逐个查详情）
4. 要精确计算或精确查找（数数、求和、按 id 取记录）

反例：只有一段几百字的固定背景，直接塞 system 就行，别为工具而工具。

---

## 五、踩过的坑（都是真实踩过的）

| 坑 | 现象 | 解法 |
|---|---|---|
| 没锁定依赖版本 | 换机器就报错 | `requirements.txt` 写死版本号 |
| key 写进代码 | 提交到 GitHub 泄露 | 放 `.env` + `.gitignore` |
| 没写 timeout | 网络卡住永远不返回 | `timeout=60` |
| 中文乱码（编辑器） | VS Code 显示鬼画符 | 右下角 → Reopen with Encoding → UTF-8 |
| 中文乱码（终端） | `Get-Content` 输出鬼画符 | `Get-Content ... -Encoding UTF8` |
| Excel 打开 CSV 乱码 | 中文变问号 | `encoding="utf-8-sig"` |
| 日志用 `"w"` | 每次运行覆盖历史 | 用 `"a"` |
| 上下文无限增长 | 越聊越贵，最终超长报错 | 裁剪 `[-N:]`，背景放 system |
| 直接 `read_text` 不判存在 | 文件缺失直接崩 | 先 `.exists()` |
| 一次讲一堆新语法 | 学不动 | 一次只加一个新概念 |
| `arguments` 当 dict 用 | `TypeError` / 切片乱码 | 它返回的是**字符串**，先 `json.loads` |
| 只把工具结果入历史，忘了 assistant 点单 | 第二次请求报错或模型发懵 | 两条都要 append，缺一不可 |
| 一轮要多个工具却只执行一个 | 答案只覆盖一半人 | `for call in message["tool_calls"]` |
| 没设 `MAX_ROUNDS` | 模型反复要工具，死循环烧钱 | 设上限，到顶返回兜底话术 |
| 浏览器直接打开 POST 接口 | `405 Method Not Allowed` | 地址栏只会 GET，用 `/docs` 或写客户端 |
| 接口报 500 就把异常原文返回 | 泄露路径/key 片段 | `except` 里记日志，对外只说人话 |
| import 自己的模块时主逻辑被执行 | 一启动服务就卡住等输入 | 主逻辑包在 `if __name__ == "__main__"` |
| GitHub HTTPS 推送 `Connection was reset` | 永远推不上去 | 远程改 SSH 走 443：`ssh://git@ssh.github.com:443/...` |
| 公钥加了却仍 `Permission denied` | 钥匙不是这台机器的/加到了别的账号 | 比对指纹；Key type 必须是 Authentication Key |
| 所有人共用一个 `session_id` | 别人的对话串进来 | 前端按浏览器生成独立 id，存 `localStorage` |
| 以为会话存在服务器上 | uvicorn 一重启全失忆 | 内存柜子只适合演示，上线换 Redis/数据库 |
| 裁剪时忘了把回答存回柜子 | 下一轮模型看到"问了没人答" | 发出去用 `to_send`，存回去用 `messages` |
| SQL 用 f-string 拼条件 | 注入风险 + 引号报错 | 一律 `?` 占位符传参 |
| 单元素元组漏逗号 `(name)` | `Incorrect number of bindings` | 写成 `(name,)` |
| 用 `addEventListener` 却起 `127.0.0.1` | 手机连不上 | 启动加 `--host 0.0.0.0` + 放行防火墙 |
| JS 写了 `async` 忘 `await` | 拿到的是 Promise 对象不是结果 | 两者必须成对出现 |
| 用 `innerHTML` 插入用户输入 | 脚本被当代码执行（XSS） | 用 `textContent` |

---

## 六、项目文件地图

```
recruit-agent/
├── .env                  # API key（不进仓库）
├── .gitignore            # 忽略 .venv/ .env output/ logs/
├── requirements.txt      # 依赖锁版本
├── data/
│   ├── resumes.json      # 5 份简历（原始数据）
│   ├── recruit.db        # SQLite 数据库（不进仓库，用 init_db.py 生成）
│   └── jd.txt            # 岗位要求
├── output/               # 运行产物（不进仓库）
│   ├── screening_result.json / .csv
│   └── interview_questions_日期.json
├── logs/                 # 每天一个日志文件（不进仓库）
├── ask_llm.py            # 第2周：最小调用
├── screening_agent.py    # 项目1：筛选 + 重试 + 成本 + 日志 + 出题
├── interview_questions.py# 项目2：JD → 面试题
├── chat_cli.py           # 第5周：多轮对话 + 背景注入 + 上下文裁剪
├── tool_calling_intro.py # 第6周：只看模型怎么"点单"
├── agent_with_tools.py   # 第6周：工具菜单 + 执行 + 循环 + 多轮
├── agent_server.py       # 第7周：FastAPI 服务（/ask + 校验 + 日志 + 会话记忆）
├── call_api.py           # 第7周：调用 /ask 的客户端示例
├── init_db.py            # 第9周：把 JSON 导入 SQLite
├── web/
│   └── chat.html         # 第10周：网页聊天界面（HTML/CSS/JS + fetch）
└── README.md             # 第8周：项目说明（怎么跑、设计取舍、已知限制）
```

---

## 七、下一步

前 10 周已完成：会调模型 → 会结构化输出 → 会多轮 → 会工具调用 → 会包服务 → 会写 README 并推 GitHub → 会做会话记忆 / 数据入库 / 网页界面 / 局域网访问。

还差的（按性价比排序）：

1. **公网部署**：买 VPS → `git clone` → `systemd` 或 Docker 常驻 → Nginx + 域名 + HTTPS
2. **登录鉴权**：前端 session_id 不可信，要发 token 并在服务端校验
3. **会话持久化**：内存柜子换 Redis / 数据库，重启不丢
4. **成本与限流**：按用户累计 token、加超时与并发上限，防刷
5. **流式输出**：`stream=True`，字一个个冒出来，体验从"等 3 秒"变"立刻有反应"

---

## 八、自查清单（每次写完新功能，问自己）

1. key 是从 `.env` 读的吗？
2. 有 `timeout` 吗？有重试吗？失败有兜底值吗？
3. 输出要 JSON 吗？字段写清楚了吗？`json.loads` 了吗？
4. 关键背景放 system 了吗？对话会被裁剪吗？
5. 写文件都带 `encoding="utf-8"` 了吗？CSV 是 `utf-8-sig` 吗？
6. 记日志了吗？记了 token 和成本吗？
7. 文件不存在会崩吗？
8. 代码能换一份数据、换一个 JD 直接跑吗？
9. 工具的 `description` 写成"模型能看懂的一句话"了吗？必填参数标进 `required` 了吗？
10. `arguments` 有 `json.loads` 吗？循环有 `MAX_ROUNDS` 吗？
11. 接口出错时，对外只说人话、细节进日志了吗？422 和 500 分得清吗？
12. 会话历史有上限吗？裁剪后有没有把回答存回柜子？
13. 查数据库用了 `?` 占位符吗？改了库之后跑过 `init_db.py` 吗？
14. 前端是 `textContent` 还是 `innerHTML`？`async` 和 `await` 成对了吗？
15. 只能在你自己电脑上访问，还是别的设备也能用？

# 招聘自动化 Agent

用大模型 API 把招聘里重复性的活自动化：读简历、按 JD 判断是否匹配、给匹配的人出面试题、支持追问对话，并把这些能力包装成 HTTP 接口和网页界面。

## 功能

| 功能 | 入口 | 说明 |
|---|---|---|
| 简历批量筛选 | `screening_agent.py` | 逐份判断是否匹配 JD，输出 JSON + CSV |
| 面试题生成 | `interview_questions.py` | 根据 JD 和候选人简历生成 5 道面试题 |
| 多轮对话助手 | `chat_cli.py` | 命令行聊天，注入筛选结果作为背景，裁剪上下文控制成本 |
| 工具调用 Agent | `agent_with_tools.py` | 模型自己决定调哪个工具（查简历、列城市候选人、按条件筛选），工具内部查 SQLite |
| HTTP 服务 | `agent_server.py` | FastAPI 暴露 `POST /ask`，带会话记忆、请求校验、异常兜底与日志 |
| 网页聊天界面 | `web/chat.html` | 手机/电脑打开 `/chat` 即可对话，会话号存在浏览器本地 |

## 技术栈

- Python 3.13 + venv
- DeepSeek `deepseek-chat`（OpenAI 兼容协议，用 `requests` 直接发 POST）
- FastAPI + uvicorn + pydantic
- SQLite（Python 内置 `sqlite3`）
- 原生 HTML / CSS / JavaScript（`fetch`，无框架）
- 依赖版本见 `requirements.txt`

## 目录结构

```
recruit-agent/
├── data/
│   ├── resumes.json          # 候选人数据（原始）
│   ├── recruit.db            # SQLite 数据库（运行 init_db.py 生成，不进仓库）
│   └── jd.txt                # 岗位描述
├── output/                   # 运行产物（JSON / CSV / 面试题）
├── logs/                     # 每天一个日志文件
├── web/
│   └── chat.html             # 网页聊天界面
├── ask_llm.py                # 最小调用示例
├── screening_agent.py        # 简历筛选：重试、成本统计、日志
├── interview_questions.py    # JD + 简历 → 面试题
├── chat_cli.py               # 多轮对话 + 背景注入 + 上下文裁剪
├── agent_with_tools.py       # 工具调用：菜单、执行、循环、查询 SQLite
├── agent_server.py           # FastAPI 服务：/ask + 会话记忆 + 校验 + 日志
├── call_api.py               # 调用 /ask 的客户端示例
├── init_db.py                # 把 resumes.json 导入 SQLite
├── AI应用开发-模板与方法论.md  # 开发方法论、可复用模板、踩坑记录
└── requirements.txt
```

## 快速开始

1. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. 配置密钥。在项目根目录建 `.env`（已在 `.gitignore` 中，不会提交）：

```
DEEPSEEK_API_KEY=你的key
```

3. 初始化数据库（简历进 SQLite）

```powershell
.\.venv\Scripts\python.exe init_db.py
```

4. 运行脚本

```powershell
.\.venv\Scripts\python.exe screening_agent.py
.\.venv\Scripts\python.exe chat_cli.py
.\.venv\Scripts\python.exe agent_with_tools.py
```

5. 启动服务（在 `recruit-agent` 目录下）

```powershell
# 仅本机访问
.\.venv\Scripts\python.exe -m uvicorn agent_server:app --reload --port 8000

# 局域网可访问（手机同 WiFi 也能用）
.\.venv\Scripts\python.exe -m uvicorn agent_server:app --reload --host 0.0.0.0 --port 8000
```

- 网页聊天：`http://localhost:8000/chat`（手机用 `http://<本机IP>:8000/chat`）
- 交互式文档：`http://localhost:8000/docs`

## 接口

`POST /ask`

请求：

```json
{"session_id": "u001", "question": "上海两年以上的有谁？"}
```

响应：

```json
{"answer": "李四和赵六……", "session_id": "u001"}
```

`session_id` 可省略（默认 `default`），传同一个值就接着上一次的对话继续；换一个值就是新会话。网页端会自动生成独立 id 存在浏览器本地。

调用方式：

```powershell
.\.venv\Scripts\python.exe call_api.py
```

状态码约定：`200` 正常，`422` 请求参数不合规（框架自动校验），`500` 服务内部异常（细节写日志，对外只返回提示语）。

## 设计要点

- **结构化输出**：筛选和出题都开 `response_format={"type": "json_object"}`，prompt 里写死字段名和类型，拿到结果必走 `json.loads`。
- **失败兜底**：单条简历失败重试 3 次，仍失败给默认值，不让一份数据拖垮整批。
- **成本核算**：累计 `prompt_tokens` / `completion_tokens`，按输入 2 元、输出 8 元每一百万 token 估算。
- **上下文控制**：system 消息永不裁剪，只保留最近 6 条对话，避免越聊越贵。
- **工具调用**：菜单写在 `TOOLS`，模型返回 `tool_calls` 后由代码执行，结果以 `role=tool` 回传，循环直到模型不再要工具；`MAX_ROUNDS` 防止死循环。
- **可观测**：请求、失败、耗时都写 `logs/YYYY-MM-DD.log`，追加模式，一天一个文件。
- **会话记忆**：服务端用 `SESSIONS` 字典按 `session_id` 存 `messages`，同一个 id 接着聊，不同 id 互不干扰。
- **两套历史**：柜子里存全量，发给模型只带 system + 最近 8 条，兼顾"记得"和"不烧钱"。
- **数据层**：简历从 JSON 迁到 SQLite，查询走参数化 `?` 占位符，避免全量读文件和 SQL 注入。
- **前后端分离**：`/chat` 返回静态页面，页面用 `fetch` 调 `/ask`，纯原生实现，不引入框架。

## 已知限制

- 会话历史存在进程内存里，服务重启即清空，多进程间也不共享；生产环境应换成 Redis 或数据库。
- 仅支持局域网访问，未做公网部署（域名 / HTTPS / 常驻进程）。
- 没有登录鉴权，前端传来的 `session_id` 不可信，不能当身份凭证。
- 没有按用户计费与限流，接口可被无限调用。
- 未做流式输出，响应需等模型生成完毕才返回。
- 日志按天拆分，未做轮转和归档。
- 仅按文本与结构化字段筛选，未接入向量检索。

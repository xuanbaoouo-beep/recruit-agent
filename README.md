# 招聘自动化 Agent

用大模型 API 把招聘里重复性的活自动化：读简历、按 JD 判断是否匹配、给匹配的人出面试题、支持追问对话，并把这些能力包装成 HTTP 接口。

## 功能

| 功能 | 入口 | 说明 |
|---|---|---|
| 简历批量筛选 | `screening_agent.py` | 逐份判断是否匹配 JD，输出 JSON + CSV |
| 面试题生成 | `interview_questions.py` | 根据 JD 和候选人简历生成 5 道面试题 |
| 多轮对话助手 | `chat_cli.py` | 命令行聊天，注入筛选结果作为背景，裁剪上下文控制成本 |
| 工具调用 Agent | `agent_with_tools.py` | 模型自己决定调哪个工具（查简历、列城市候选人、按条件筛选） |
| HTTP 服务 | `agent_server.py` | FastAPI 暴露 `POST /ask`，别人可以用 requests 调用 |

## 技术栈

- Python 3.13 + venv
- DeepSeek `deepseek-chat`（OpenAI 兼容协议，用 `requests` 直接发 POST）
- FastAPI + uvicorn + pydantic
- 依赖版本见 `requirements.txt`

## 目录结构

```
recruit-agent/
├── data/
│   ├── resumes.json          # 候选人数据
│   └── jd.txt                # 岗位描述
├── output/                   # 运行产物（JSON / CSV / 面试题）
├── logs/                     # 每天一个日志文件
├── ask_llm.py                # 最小调用示例
├── screening_agent.py        # 简历筛选：重试、成本统计、日志
├── interview_questions.py    # JD + 简历 → 面试题
├── chat_cli.py               # 多轮对话 + 背景注入 + 上下文裁剪
├── agent_with_tools.py       # 工具调用：菜单、执行、循环、多轮
├── agent_server.py           # FastAPI 服务
├── call_api.py               # 调用 /ask 的客户端示例
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

3. 运行脚本

```powershell
.\.venv\Scripts\python.exe screening_agent.py
.\.venv\Scripts\python.exe chat_cli.py
.\.venv\Scripts\python.exe agent_with_tools.py
```

4. 启动服务（在 `recruit-agent` 目录下）

```powershell
.\.venv\Scripts\python.exe -m uvicorn agent_server:app --reload --port 8000
```

交互式文档：`http://localhost:8000/docs`

## 接口

`POST /ask`

请求：

```json
{"question": "上海两年以上的有谁？"}
```

响应：

```json
{"answer": "李四和赵六……"}
```

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

## 已知限制

- 简历数据是本地 JSON，未接入数据库。
- 服务无状态，每次请求独立，暂不支持跨请求的多轮会话。
- 日志按天拆分，未做轮转和归档。
- 仅按文本规则筛选，未接入向量检索。

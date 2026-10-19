# Minimal Agent Runtime

从零实现的最小可用 Agent Runtime。项目不依赖 LangChain、LangGraph、OpenHands、OpenClaw 或其他 Agent 框架；仅使用 OpenAI Python SDK 作为 DeepSeek API 的 HTTP 客户端。

它实现一个可运行的工具调用循环：接收用户输入、由 LLM 根据工具 Schema 决策、执行工具、把工具结果回填给 LLM，并得到最终回复。

## 功能对应题目

| 要求 | 实现位置 |
|---|---|
| LLM 自主决定直接回答或调工具 | `app/runtime.py`，每轮将 `ToolRegistry.openai_schemas()` 传给 DeepSeek |
| 工具注册 + 名称/描述/参数 Schema | `app/tools/registry.py` |
| 至少三个工具，todo 必须实现 | `todo`、`calculator`、`weather`、`search` 四个工具 |
| 解析最终答复、工具调用、可选思考字段 | `app/llm_client.py` / `app/runtime.py` |
| 同用户不同窗口隔离 | `(user_id, session_id)` 对应独立 JSON state 文件 |
| 多轮纯对话与工具追问 | 保存近期消息、工具结果和结构化 todo state |
| context 压缩 | `ContextBuilder` 的近期窗口 + rolling summary |
| 最大轮次、异常、trace | `max_tool_rounds`、规范化错误结果、JSONL trace |
| 测试 | `tests/`，默认 Fake LLM；另有真实 API smoke test |

## 安装与运行

需要 Python 3.10+。

```bash
git clone <your-github-repository-url>
cd minimal-agent-runtime
python -m venv .venv
source .venv/bin/activate
pip install -e . pytest
cp .env.example .env
```

编辑 `.env`，填入一次真实 API Key：

```bash
DEEPSEEK_API_KEY=your-key
DEEPSEEK_MODEL=deepseek-chat
```

程序启动时会自动读取当前项目目录下的 `.env`，并且 `.gitignore` 已排除它；不要把 `.env` 提交到 Git。你也可以使用 `export DEEPSEEK_API_KEY=...`，环境变量会优先于 `.env`，适合临时替换 Key 或 CI。

运行一次对话：

```bash
python -m app.cli --user A --session weather '查广州明天天气，并提醒我带伞'
```

同一窗口追问：

```bash
python -m app.cli --user A --session weather '列出我的待办'
```

另一个窗口独立工作：

```bash
python -m app.cli --user A --session weekly '帮我记一个待办：周五前写完周报'
python -m app.cli --user A --session weekly '列出我的待办'
```

session 保存在 `data/sessions/A/weather.json` 和 `data/sessions/A/weekly.json`，完整事件记录在 `data/traces/`。两个窗口的消息、待办、摘要和 trace 均不会相互读取。

## 系统设计

```text
CLI -> ChatService -> SessionStore + AgentRuntime
                                   ├-> ContextBuilder
                                   ├-> DeepSeekClient
                                   ├-> ToolRegistry / ToolExecutor
                                   └-> JsonlTraceRecorder
```

`AgentRuntime.run()` 是核心循环：

1. 将用户消息写入当前 session；
2. ContextBuilder 按预算构造模型上下文；
3. LLM 返回最终文本，直接结束；或返回一个/多个 `tool_calls`；
4. Runtime 校验参数并执行工具，将标准化结果作为 `role=tool` 追加；
5. 回到 LLM，直到得到最终文本或达到最大 6 个工具轮次。

工具调用并非基于关键词硬编码；模型只看到工具名称、说明与 JSON Schema，自主选择是否调用和调用哪个工具。

## Memory 的召回时机与放置方式

Session 是唯一的短期 memory 边界，key 为 `(user_id, session_id)`。每次请求前加载该 key 的 state，因此用户可以离开后继续某个窗口；同一用户另开窗口则没有旧窗口的任何 state。

每次调用模型的 context 按以下顺序放置：

1. system prompt；
2. 结构化 active todos；
3. 早期对话的 rolling summary；
4. 最近 12 条 user / assistant / tool 消息。

超过 16 条消息时，早期消息被压缩成确定性 summary，最近 12 条保留原文。todo 永远从 `SessionState.todos` 注入，不依赖摘要，也不让模型从自然语言中猜测待办状态。

如果 DeepSeek thinking mode 返回 `reasoning_content`，adapter 会在同一次工具循环内按 provider 协议回传它；它不会进入长期 session memory、rolling summary 或 CLI 输出。trace 只记录是否存在及长度，以避免将内部推理当作业务事实或泄露到用户侧。

## 工具

| 工具 | 行为 |
|---|---|
| `todo` | `add`、`list`、`complete`，读写当前 session 的结构化待办 |
| `calculator` | AST 白名单解析四则运算，不使用 `eval` |
| `weather` | 本地 mock 天气，验证工具调用链 |
| `search` | 本地 mock 搜索，验证通用查询工具 |

## Trace 与错误处理

每个 LLM response、工具完成、工具拒绝、模型错误和最大轮次中止都会写入 JSONL trace。记录包括轮次、工具、参数、结果摘要、耗时和错误码；不记录 API Key 或完整 reasoning 内容。

未知工具、坏 JSON、Schema 不匹配、工具异常和 LLM 网络异常都会被转换为可读错误，而不是让进程崩溃。对可恢复的工具调用错误，Runtime 将 error result 回填给模型，模型可修正参数或换一种方案。

## 测试

默认测试不调用网络：

```bash
python -m unittest discover -s tests -v
```

真实 DeepSeek 冒烟测试需要 Key，且显式指定环境变量：

```bash
RUN_REAL_LLM=1 python -m unittest tests.test_real_llm -v
```

测试覆盖工具注册、calculator 安全性、todo 持久化、直接回答、工具循环、纯对话追问、工具追问、session 隔离、context 压缩、异常处理和最大轮次。

## 设计取舍与限制

- 使用 JSON 文件而非数据库，方便最小项目展示和检查；生产环境可替换为 Redis/PostgreSQL 并为同一 session 加锁。
- 多个工具调用顺序执行，保证最小实现中状态变更可预测；生产化后可对无依赖只读工具并发执行。
- `weather` 与 `search` 为 mock，避免外部 API 不稳定掩盖 Runtime 行为。
- 本项目没有实现异步工具完成通知、队列或多 Agent，这些是下一阶段 runtime 设计问题，不是本题最小闭环所必需。

更详细的设计见 [docs/design.md](docs/design.md)，AI 辅助与人工验证过程见 [docs/ai-usage.md](docs/ai-usage.md)。

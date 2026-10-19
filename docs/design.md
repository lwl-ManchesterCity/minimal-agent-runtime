# 设计说明

该项目的设计目标是把 Agent 框架通常隐藏的 runtime 行为显式写出来：工具注册、模型决策、工具执行、结果回填、session state、context budget 与可观测性。

核心状态为：

```text
SessionState = messages + rolling_summary + todos + timestamps
Session identity = (user_id, session_id)
```

`todos` 是 session 的结构化事实源；聊天消息与 summary 仅用于自然语言理解。这样“窗口 1 的带伞”和“窗口 2 的写周报”从存储层、context 层和工具层都被隔离。

本项目采用 provider adapter：Runtime 只依赖 `LLMClient.chat(messages, tools)`，DeepSeek 的 SDK/字段差异被限制在 `DeepSeekClient` 中。因此单测可以使用脚本式 Fake LLM，真实 API 仅用于 smoke test。

当 API 返回 tool calls 时，Runtime 会先把 assistant tool-call message 追加到本次 API history，再按 call ID 写入 tool result。随后再请求模型，因此模型可基于真实结果决定继续调用或最终回答。最大轮次是运行时护栏，不依赖模型自觉停止。

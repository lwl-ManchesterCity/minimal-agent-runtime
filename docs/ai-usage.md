# AI Prompt 与问题解决记录

## 使用原则

本项目使用 AI 协助梳理 API 文档、提出边界条件和审查测试遗漏，但由作者决定架构、实现代码、执行测试并核对实际行为。AI 生成的建议不会未经验证直接作为结论。

## 关键 Prompt 示例

### 1. 范围控制

> 为一个两天内完成的最小 Agent Runtime 面试题划分必须实现与明确不实现的能力。目标是展示 tool loop、session、context、trace 与测试，而不是做 UI。

采用结果：CLI + JSON session + 四个本地工具；不加入 Web UI、数据库、多 Agent、RAG。

### 2. Context 设计

> 在有限 token 预算下，哪些信息必须以结构化 state 保存，哪些保留为最近消息，哪些应该压缩？请给出可测试的最小策略。

采用结果：todo 是结构化 state；最近 12 条消息保留原文；超过阈值的旧消息进入 rolling summary；工具 Schema 通过 API tools 字段传递，不重复拼入消息正文。

### 3. DeepSeek tool calling 协议核验

> 核验 DeepSeek OpenAI-compatible function calling 中 tool_call ID、tool result 和 thinking mode reasoning 字段的回传要求，并列出可能导致 400 的情况。

人工核验：阅读官方 DeepSeek Tool Calls 与 Thinking Mode 文档。结论是工具结果必须带回对应 call ID；启用 thinking mode 时，工具循环中的 `reasoning_content` 要按 provider 约定回传。因此 adapter 支持该字段，但不把它写入长期 memory。

### 4. 测试审查

> 对一个 Agent Runtime 的测试计划做反例审查：哪些情况会让“看起来能跑”但实际 session、工具循环或异常处理不正确？

采用结果：补充了同用户双窗口隔离、坏 JSON、未知工具、工具异常、LLM 异常、最大轮次、context 压缩后的追问等测试。

## 人工验证清单

- 阅读并理解每个模块的输入输出与依赖方向。
- 使用 Fake LLM 跑确定性测试，确保测试验证的是 Runtime 而不是模型随机性。
- 使用自己的 DeepSeek Key 跑真实 API smoke test，不提交 Key 或调用输出中的敏感信息。
- 手动运行 README 的两个 session 演示，检查待办没有串窗。
- 查看 JSONL trace，确认工具参数、结果、错误和轮次记录完整。

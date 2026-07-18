# ChatLearning 沙箱智能体设计方案

## 目标

让 App 内的 ChatLearning 在解数学一/408 题时能真正执行代码验算，不再"硬算瞎编"；
中间过程（思考、代码、运行结果）在聊天界面里做成可展开/折叠的卡片，默认收起，像 ChatGPT 那样。

## 一、整体流程

```
用户提问（可带图）
    ↓
后端把消息 + 工具定义发给 gpt-5.5（function calling）
    ↓
模型若需要验算 → 返回 tool_call: run_python(code)
    ↓
后端在受限沙箱里执行代码（≤15s、≤256MB、禁网络）
    ↓
把 stdout/异常回传给模型（最多循环 5 轮）
    ↓
模型给出最终回答
    ↓
最终回答 + 全部中间步骤一起入库、下发给安卓
```

## 二、沙箱执行器（后端）

- 实现：`subprocess` 启动独立 `python3 -I`（隔离模式），不引入新容器（2C2G 单人够用）
- 限制：
  - CPU 时间 ≤15 秒（`resource.RLIMIT_CPU` + 总超时 kill）
  - 内存 ≤256MB（`RLIMIT_AS`）
  - 输出截断 8KB
  - 禁网络：进程内屏蔽 `socket`（预加载 sitecustomize 移除），后端容器本身继续保留网络（要访问 AI API）
  - 无文件写入：工作目录只读 tmpfs，`RLIMIT_FSIZE=0`
- 预装库：`sympy`、`numpy`（加入后端镜像，约 +80MB）
- 每次执行是全新进程，无状态残留

## 三、Function calling 循环（后端）

- `ai/client.py` 增加 `complete_chat_with_tools(messages, tools)`：请求带 `tools`，
  响应若含 `tool_calls` 则返回给调用方，由 chat 服务执行后追加 `role:"tool"` 消息再请求
- 工具定义（只此一个，安全面最小）：

```json
{
  "name": "run_python",
  "description": "在沙箱中执行 Python 验算，可用 sympy/numpy。",
  "parameters": {"code": "string"}
}
```

- 最多 5 轮工具调用，超过则要求模型直接作答
- system prompt 增加指引：数学/408 计算题先用 run_python 验证再回答

## 四、数据模型与 API

- `chat_messages` 表加一列 `steps JSON`（默认 `[]`），存中间步骤：

```json
[
  {"type": "reasoning", "content": "……模型的思考摘要……"},
  {"type": "code", "content": "import sympy…"},
  {"type": "output", "content": "结果: 2*pi"}
]
```

- `ChatMessageRead` 增加 `steps` 字段；一次 Alembic 迁移（加列，无破坏）
- reasoning 来源：中转站响应里的 `reasoning_content`（上次实测有返回）

## 五、安卓聊天界面

- assistant 消息若带 steps：气泡上方显示一个折叠条「🔧 已运行 N 段验算 ▸」
- 点击展开：依次显示思考摘要（灰字）、代码块（等宽字体）、运行输出
- 默认收起，不打扰正常阅读；Room 里 `steps` 存 JSON 字符串

## 六、风险与边界

- 响应变慢：带验算的问题一次要 2~4 次模型往返 + 代码执行，预计 20~60 秒；纯闲聊不受影响
- 中转站需支持 function calling（gpt-5.5 官方支持，部署后实测，不支持则报错降级为普通回答）
- 沙箱逃逸风险低（单用户自用 + 无网 + 资源限制），不做企业级隔离
- 判题/识题接口暂不接工具，先只改 ChatLearning，稳定后再扩展

## 七、实施顺序

1. 沙箱执行器 + 单元测试（超时/内存/禁网/正常算例）
2. function calling 循环 + steps 入库 + 迁移 + OpenAPI 同步
3. 安卓折叠卡片 UI
4. 部署（镜像加 sympy/numpy），实测中转站 function calling
5. 通过后重装 APK

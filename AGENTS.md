# AGENTS.md

## 项目原则

本项目是 TechLeveler 技术体感闯关学习系统。

不要使用 mock 作为主路径。
不要绕开真实 MySQL、Redis、Celery、真实 LLM。
不要为了跑通测试删除真实链路。
不要大重构，优先做最小修复。

## 环境规则

local 模式：
- MySQL: 127.0.0.1
- Redis: 127.0.0.1
- backend: http://localhost:8000
- frontend: http://localhost:5173

docker 模式：
- MySQL: mysql
- Redis: redis
- backend: backend
- frontend: frontend

不要混用 local 和 docker 配置。

## .env 规则

复杂类型必须使用 JSON 格式。

正确：
CORS_ORIGINS=["http://localhost:5173","http://frontend:5173"]

错误：
CORS_ORIGINS=http://localhost:5173,http://frontend:5173

DATABASE_URL、REDIS_URL、CELERY_BROKER_URL、CELERY_RESULT_BACKEND 必须分行。

## LLM JSON 规则

真实 LLM 输出不可信，必须容错：

- 可能多字段
- 可能少字段
- 可能字段名不同
- 可能输出 markdown ```json
- 可能在 JSON 前后输出解释文本
- 可能因为 max_tokens 不够而截断

所有 LLM JSON 解析必须走统一 parser（`app/llm/json_parser.py`）。
必须保留 raw_response preview 方便排查。
Pydantic schema 尽量 extra=ignore。
常见字段名差异要加 alias。
不能兜底时要明确失败并记录错误。

## 异步任务规则

不能假设 Celery 任务一定一次跑完。

必须考虑：
- worker 被 Ctrl+C 停掉
- worker 崩溃
- async_tasks 卡在 running
- learning_sessions 卡在 generating
- 部分 knowledge_points/examples/levels 已经生成
- 重新执行时不能重复生成已有内容

生成任务应该支持 resume：
- 先查数据库已有产物
- 已有的不重复生成
- 缺什么补什么
- 单个 level 失败不能让整个 session 永久卡死

## 修改要求

每次只解决一个明确问题。
修改前先说明影响文件。
修改后必须运行验证命令。
没有实际运行就写"未运行"，不能写通过。

# TechLeveler

TechLeveler 是一个技术体感闯关学习系统。本仓库当前只包含第一步项目骨架、依赖、启动配置和健康检查接口。

## 技术栈

- Backend: FastAPI, SQLAlchemy 2.x, Alembic, MySQL
- Async tasks: Celery, Redis
- Frontend: React, Vite, TypeScript
- LLM: OpenAI-compatible API, 通过环境变量配置

## 启动前准备

项目会默认读取 `.env.example`，所以可以直接用 Docker Compose 启动。需要覆盖配置时，复制环境变量示例文件：

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

如需后续调用真实 LLM，请在 `backend/.env` 中配置：

```bash
LLM_BASE_URL=https://your-compatible-endpoint/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
```

## 使用 Docker Compose 启动

确认 Docker Desktop 已启动后运行：

```bash
docker compose up --build
```

服务地址：

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Backend docs: http://localhost:8000/docs
- MySQL: localhost:3306
- Redis: localhost:6379

## 验证

后端健康检查：

```bash
curl http://localhost:8000/health
```

预期返回：

```json
{"status":"ok"}
```

数据库健康检查：

```bash
curl http://localhost:8000/health/db
```

预期返回：

```json
{"status":"ok"}
```

Celery worker 启动后会连接 Redis。当前只包含一个内部 ping 任务，后续业务任务会在生成链路实现时接入。

## 数据库迁移

启动 MySQL 后运行初始迁移：

```bash
docker compose exec backend alembic upgrade head
```

本地已安装后端依赖时，也可以在 `backend/` 目录运行：

```bash
alembic upgrade head
```

当前初始迁移会创建 TechLeveler 的核心业务表，不包含任何假数据或默认学习内容。

## LLM JSON 调试接口

先在 `backend/.env` 配置真实 OpenAI-compatible API：

```bash
LLM_BASE_URL=https://your-compatible-endpoint/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
```

启动后测试结构化 JSON 调用：

```bash
curl -X POST http://localhost:8000/api/debug/llm-json \
  -H "Content-Type: application/json" \
  -d "{\"tech_name\":\"FastAPI\"}"
```

成功时会返回：

```json
{
  "model": "your-model-name",
  "data": {
    "tech_name": "FastAPI",
    "official_summary": "...",
    "official_example": "...",
    "source_url": "...",
    "chunks": ["...", "..."]
  }
}
```

## 官方资料获取接口

官方文档来源维护在 `backend/app/data/official_sources.yaml`，当前第一批包含 LangGraph、Redis、RabbitMQ、Prometheus。接口不会让模型生成官方链接，保存时会强制使用 YAML 中的 `source_url`。

抓取并总结官方资料：

```bash
curl -X POST http://localhost:8000/api/materials/fetch \
  -H "Content-Type: application/json" \
  -d "{\"tech_name\":\"LangGraph\"}"
```

强制刷新缓存：

```bash
curl -X POST http://localhost:8000/api/materials/fetch \
  -H "Content-Type: application/json" \
  -d "{\"tech_name\":\"LangGraph\",\"force_refresh\":true}"
```

读取已保存资料：

```bash
curl http://localhost:8000/api/materials/LangGraph
```

## 技术关系与边界对比接口

技术关系维护在 `backend/app/data/tech_relations.yaml`，用于限制对比候选，避免让模型自由扩展无关技术。

查询技术关系：

```bash
curl http://localhost:8000/api/relations/LangGraph
```

生成边界对比前，需要已有学习会话和官方资料。当前阶段还未实现学习会话创建接口，可以临时通过 MySQL 创建一条真实会话用于联调：

```bash
docker compose exec mysql mysql -utechleveler -ptechleveler techleveler \
  -e "INSERT INTO learning_sessions (tech_name, status) VALUES ('LangGraph', 'pending'); SELECT LAST_INSERT_ID();"
```

抓取官方资料：

```bash
curl -X POST http://localhost:8000/api/materials/fetch \
  -H "Content-Type: application/json" \
  -d "{\"tech_name\":\"LangGraph\"}"
```

生成技术边界对比，将 `session_id` 替换为上一步插入得到的 ID：

```bash
curl -X POST http://localhost:8000/api/comparisons/generate \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":1,\"tech_name\":\"LangGraph\"}"
```

查询某个学习会话的对比结果：

```bash
curl http://localhost:8000/api/comparisons/session/1
```

## 学习 Session 与异步生成任务

启动 MySQL、Redis、后端和 Celery worker，并确保已运行迁移、已配置真实 LLM：

```bash
docker compose up -d mysql redis backend celery
docker compose exec backend alembic upgrade head
```

创建学习 Session。接口会立即返回 `session_id` 和 `task_id`，不会等待 LLM 生成完成：

```bash
curl -X POST http://localhost:8000/api/learning-sessions \
  -H "Content-Type: application/json" \
  -d "{\"tech_name\":\"LangGraph\",\"user_level\":\"beginner\",\"learning_goal\":\"Understand when to use LangGraph instead of plain Python control flow\"}"
```

查询 Session 详情：

```bash
curl http://localhost:8000/api/learning-sessions/1
```

查询异步生成状态：

```bash
curl http://localhost:8000/api/learning-sessions/1/status
```

查询知识点拆解结果：

```bash
curl http://localhost:8000/api/learning-sessions/1/knowledge-points
```

查询某个知识点的体感样例，将 ID 替换为知识点 ID：

```bash
curl http://localhost:8000/api/knowledge-points/1/examples
```

查询某个知识点的关卡：

```bash
curl http://localhost:8000/api/knowledge-points/1/levels
```

查询单个关卡：

```bash
curl http://localhost:8000/api/levels/1
```

提交关卡答案：

```bash
curl -X POST http://localhost:8000/api/levels/1/answers \
  -H "Content-Type: application/json" \
  -d "{\"answer_text\":\"I think this level is asking me to compare the baseline flow with the target technology behavior.\"}"
```

查询答案反馈：

```bash
curl http://localhost:8000/api/answers/1/feedback
```

生成实战 Boss 题。只有当该 Session 的所有 `must_learn` 关卡都有 `pass` 反馈后才允许生成：

```bash
curl -X POST http://localhost:8000/api/learning-sessions/1/practice-task
```

查询实战 Boss 题：

```bash
curl http://localhost:8000/api/learning-sessions/1/practice-task
```

生成技术卡片：

```bash
curl -X POST http://localhost:8000/api/learning-sessions/1/learning-card
```

查询技术卡片：

```bash
curl http://localhost:8000/api/learning-sessions/1/learning-card
```

后台任务会按顺序执行：

```text
fetch_official_material
generate_comparison
generate_knowledge_points
generate_examples
generate_levels
```

任务失败时，`learning_sessions.status` 会变为 `failed`，错误原因记录在 `async_tasks.error_message`。

## 本阶段范围

当前已创建：

- `backend/` FastAPI 项目骨架
- `frontend/` Vite React TypeScript 项目骨架
- MySQL / Redis / Backend / Celery / Frontend 的 Docker Compose 配置
- `.env.example`
- 健康检查接口

暂未实现复杂业务，包括学习会话、LLM 生成链路、官方资料抓取、关卡、反馈、实战题和技术卡片。

# 🧠 记忆系统集成说明（长期记忆）

本目录新增了一个「用户长期记忆」系统：AI 助手会自动从对话中提取关于用户的关键信息（事实/偏好/事件/人物/上下文），在后续对话中检索并注入系统提示词，实现个性化回答。

## 架构（提取-存储-检索-淘汰 四阶段流水线）

```
用户消息
  │
  ├─ 对话前：get_relevant_memories()  → 关键词匹配 + 高重要性补充 → 注入系统提示词
  │
  ├─ 对话中：Router Agent 正常处理（调用 todo / 会议 / 天气 / 知识库工具）
  │
  └─ 对话后：extract_memories_from_conversation()  → LLM 提取新记忆 → 存储（后台任务，不阻塞响应）
        │
        └─ 超过 200 条上限时自动淘汰低重要性、久未访问的记忆
```

记忆同时覆盖 **非流式**（`POST /api/v1/chat/`）和 **流式**（`POST /api/v1/chat/stream`，前端实际使用的接口）两条路径。
流式路径的记忆提取在独立数据库会话的后台任务中执行，**不会延迟 `[DONE]`**。

## 新增/修改文件

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `backend/app/models/user_memory.py` | ✚ 新增 | `UserMemory` ORM 模型 |
| `backend/app/services/memory_service.py` | ✚ 新增 | 记忆服务（提取/存储/检索/淘汰/统计） |
| `backend/app/api/endpoints/memory.py` | ✚ 新增 | 记忆管理 API |
| `backend/app/agents/router_agent.py` | ✎ 修改 | 对话前后注入记忆检索与提取（含流式路径） |
| `backend/app/models/__init__.py` | ✎ 修改 | 注册 `UserMemory`（使 `create_all` 自动建表） |
| `backend/app/api/router.py` | ✎ 修改 | 注册 `/memory` 路由 |
| `backend/migrations/002_add_user_memories.sql` | ✚ 新增 | 增量迁移脚本（含 CHECK 约束/触发器/全文索引） |
| `backend/migrations/init.sql` | ✎ 修改 | 新建库时自带 `user_memories` 表 |
| `backend/pyproject.toml` / `.python-version` | ✚ 新增 | uv 本地开发配置（Python 3.11） |
| `frontend/src/api/memory.js` | ✚ 新增 | 前端记忆 API 客户端 |

> 没有引入新的 Python 依赖（`langchain` / `langchain-openai` 项目已有）。

## 数据库迁移（建表）

应用启动时 `init_db()` → `Base.metadata.create_all()` 会**自动创建** `user_memories` 表，因此本地与 Docker 都无需手动迁移即可使用。

如需更完整的数据库约束（CHECK 约束、`updated_at` 触发器、`pg_trgm` 全文索引），可手动执行增量脚本（幂等，可重复执行）：

```bash
# 已有数据库
docker exec -i ai_employee_postgres psql -U postgres -d ai_employee \
  < backend/migrations/002_add_user_memories.sql
```

## API 接口（均需 Bearer Token）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/memory/memories` | 获取记忆列表（可 `?memory_type=&category=&limit=`） |
| GET | `/api/v1/memory/memories/search?q=` | 关键词搜索 |
| GET | `/api/v1/memory/memories/stats` | 记忆统计（总数/分类/平均重要性/容量） |
| DELETE | `/api/v1/memory/memories/{id}` | 软删除一条记忆 |

## 本地运行（uv）

```bash
cd backend
uv sync                                   # 创建 .venv 并安装依赖（Python 3.11）
uv run uvicorn main:app --reload --port 8000
```

> 系统默认 Python 为 3.14，与项目旧版 `langchain==0.1.0` 不兼容，因此 uv 固定使用 3.11（会自动下载）。

## Docker 运行

无需改动，`docker-compose up -d` 即可。后端镜像基于 `python:3.11-slim`，启动后 `create_all` 自动建表。

## 调优

在 `backend/app/services/memory_service.py` 顶部调整：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `MAX_MEMORIES_PER_USER` | 200 | 每用户最大记忆数，超出自动淘汰 |
| `MAX_MEMORIES_IN_CONTEXT` | 15 | 每次对话注入的最大记忆数 |

`router_agent.py` 中的 `_is_extraction_worthy()` 会跳过「你好/谢谢」等无意义短语，避免每轮都触发提取 LLM 调用，节省成本。

## 验证

已在本地 PostgreSQL 15 通过完整端到端测试：建表（`init.sql` + `create_all` 幂等）、记忆创建/检索/搜索/统计/删除、以及 `/api/v1/memory/*` 全部 HTTP 接口（含鉴权拦截）均正常。

## 后续可扩展

- 🔮 向量化检索（pgvector，替代关键词匹配，中文效果更好）
- 🔄 记忆合并去重（新旧记忆描述同一事实时自动合并）
- ⏰ 时间感知记忆（事件类记忆随时间衰减/过期）
- 🧩 前端记忆管理面板（`frontend/src/api/memory.js` 已就绪，可接 UI）

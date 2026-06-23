# 用户长期记忆系统 — 技术报告

> **项目**：AI 数字员工系统  
> **模块**：用户长期记忆（Long-term Memory）  
> **版本**：v1.0  
> **日期**：2026-06

---

## 1. 概述

### 1.1 背景

传统 AI 对话系统是无状态的——每次对话都是全新开始，无法"记住"用户之前透露过的偏好、习惯或关键信息。用户不得不反复说明自己的需求背景，体验碎片化。

本系统引入**长期记忆模块**，使 AI 助手能够：

- **自动提取**：从对话中识别关于用户的关键信息（事实、偏好、事件、人物、上下文）
- **持久存储**：将提取的记忆写入 PostgreSQL，跨会话保留
- **智能检索**：在后续对话开始时，检索与当前问题相关的记忆，注入系统提示词
- **自动淘汰**：当记忆数超过上限时，优先淘汰低重要性、久未访问的记忆

### 1.2 设计目标

| 目标 | 说明 |
|------|------|
| 无侵入 | 记忆逻辑不改变原有对话流程，仅在"对话前检索 + 对话后提取"两个切面插入 |
| 不阻塞 | 记忆提取在后台异步执行，不影响流式响应的 `[DONE]` 时序 |
| 可控成本 | 过滤无意义短语（你好/谢谢等），避免每轮都触发 LLM 提取调用 |
| 用户可见 | 提供前端管理页面，用户可查看、搜索、删除自己的记忆 |

---

## 2. 系统架构

### 2.1 四阶段流水线

```
用户发送消息
  │
  ├─ 阶段 1：检索（Retrieval）
  │    get_relevant_memories()
  │    ├─ 关键词模糊匹配（ilike %kw%）
  │    └─ 高重要性记忆补充（importance >= 7）
  │    → 注入系统提示词 {user_memories}
  │
  ├─ 阶段 2：对话（Conversation）
  │    Router Agent 正常处理
  │    调用 todo / 会议 / 天气 / 知识库 工具
  │    返回响应（流式/非流式）
  │
  ├─ 阶段 3：提取（Extraction）
  │    _schedule_memory_extraction()
  │    ├─ 判断消息是否值得提取（_is_extraction_worthy）
  │    └─ asyncio.create_task → 后台任务
  │         ├─ 构建提取提示词（含已有记忆，避免重复）
  │         ├─ 调用 LLM 解析对话 → JSON 数组
  │         └─ 批量存储新记忆
  │
  └─ 阶段 4：淘汰（Eviction）
       _cleanup_old_memories()
       当记忆数 > 200 → 软删除低重要性 + 久未访问的记忆
```

### 2.2 数据流

```
┌─────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────┐
│  用户    │────▶│  Router Agent │────▶│  LLM 提取器    │────▶│ PostgreSQL│
│  消息    │     │  (含记忆注入)  │     │  (后台异步)    │     │ user_     │
└─────────┘     └──────────────┘     └───────────────┘     │ memories  │
                      │                                      └──────────┘
                      │  对话前检索                                ▲
                      └──────────────────────────────────────────┘
```

### 2.3 双路径覆盖

| 对话模式 | 端点 | 记忆检索 | 记忆提取 |
|----------|------|---------|---------|
| 非流式 | `POST /api/v1/chat/` | `process_message()` 中同步检索 | `_schedule_memory_extraction()` 后台异步 |
| 流式（前端实际使用） | `POST /api/v1/chat/stream` | `stream_message()` 中同步检索 | `_schedule_memory_extraction()` 后台异步 |

---

## 3. 数据模型

### 3.1 表结构 `user_memories`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK, `gen_random_uuid()` | 记忆唯一标识 |
| `user_id` | UUID | FK → `users(id)` ON DELETE CASCADE | 所属用户 |
| `memory_type` | VARCHAR(20) | NOT NULL, DEFAULT `'fact'`, CHECK IN (fact/preference/event/person/context) | 记忆类型 |
| `category` | VARCHAR(50) | NULL | 分类标签 (work/tech/health/life/learning) |
| `content` | TEXT | NOT NULL | 记忆内容（简洁陈述句） |
| `context` | TEXT | NULL | 提取时的原始对话上下文 |
| `source_conversation_id` | UUID | NULL | 来源会话 ID |
| `importance` | INTEGER | NOT NULL, DEFAULT 5, CHECK [1,10] | 重要性评分 |
| `confidence` | REAL | NOT NULL, DEFAULT 0.8, CHECK [0,1] | 置信度 |
| `access_count` | INTEGER | NOT NULL, DEFAULT 0 | 访问次数 |
| `last_accessed` | TIMESTAMPTZ | NULL | 最后访问时间 |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | 软删除标记 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 更新时间（触发器自动维护） |

### 3.2 索引

| 索引名 | 列 | 用途 |
|--------|-----|------|
| `idx_user_memories_user_type` | `(user_id, memory_type)` | 按用户+类型查询 |
| `idx_user_memories_user_active` | `(user_id, is_active)` | 按用户+活跃状态查询 |
| `idx_user_memories_importance` | `(user_id, importance)` | 重要性排序/补充检索 |
| `idx_user_memories_updated` | `(user_id, updated_at DESC)` | 按更新时间排序 |
| `idx_user_memories_content_trgm` | GIN `(content gin_trgm_ops)` | 全文模糊搜索（依赖 pg_trgm） |

### 3.3 记忆类型说明

| 类型 | 标识 | 示例 |
|------|------|------|
| 事实 | `fact` | "张三在字节跳动工作" |
| 偏好 | `preference` | "喜欢用 Python 编程" |
| 事件 | `event` | "下周要去北京出差" |
| 人物 | `person` | "李四是直属上级" |
| 上下文 | `context` | "正在做毕业设计" |

---

## 4. 后端实现

### 4.1 模块结构

```
backend/
├── app/
│   ├── models/
│   │   └── user_memory.py          # ORM 模型
│   ├── services/
│   │   └── memory_service.py       # 核心服务（提取/存储/检索/淘汰/统计）
│   ├── api/endpoints/
│   │   └── memory.py               # REST API 端点
│   └── agents/
│       └── router_agent.py         # Agent 集成（对话前检索 + 对话后提取）
├── migrations/
│   └── 002_add_user_memories.sql   # 增量迁移脚本（幂等）
└── MEMORY_INTEGRATION.md           # 本文档
```

### 4.2 核心服务 MemoryService

| 方法 | 说明 |
|------|------|
| `create_memory()` | 创建单条记忆，并触发容量检查 |
| `create_memories_batch()` | 批量创建记忆 |
| `get_user_memories()` | 获取用户记忆列表（支持类型/分类/重要性筛选） |
| `search_memories()` | 关键词搜索（ilike 模糊匹配） |
| `get_relevant_memories()` | 获取与当前问题相关的记忆（双策略：关键词 + 高重要性补充） |
| `delete_memory()` | 软删除一条记忆 |
| `update_memory()` | 更新记忆属性 |
| `format_memories_for_prompt()` | 将记忆格式化为可注入系统提示词的文本 |
| `extract_memories_from_conversation()` | 调用 LLM 从对话中提取记忆 |
| `_cleanup_old_memories()` | 超容量时自动淘汰 |
| `get_memory_stats()` | 获取记忆统计 |

### 4.3 记忆提取流程

```
对话消息 → _is_extraction_worthy()?
  │ No  → 跳过（节省 LLM 调用成本）
  │ Yes
  └─→ _build_messages_for_extraction()
      ├─ 收集最近 4 轮对话历史
      └─ 追加当前 user + assistant 消息
       │
       └─→ asyncio.create_task(_extract_memories_background)
            │
            ├─ 打开独立数据库会话（async_session_maker）
            ├─ 获取已有记忆（去重参考）
            ├─ 调用 LLM 提取 → JSON 数组
            │    ├─ 解析成功 → create_memories_batch()
            │    └─ 解析失败 → 记录 warn 日志，静默丢弃
            └─ commit & close
```

**关键设计决策**：

- 使用独立数据库会话（`async_session_maker()`）而非请求会话，避免会话生命周期冲突
- 后台任务引用保存在 `_bg_extraction_tasks` 集合中，防止被 GC 回收
- 任务完成后自动从集合中移除（`task.add_done_callback(_bg_extraction_tasks.discard)`）

### 4.4 记忆检索策略

```python
# 第一步：关键词模糊匹配
keywords = query.split()[:5]  # 取前 5 个关键词
for kw in keywords:
    if len(kw) >= 2:          # 忽略单字
        conditions.append(content.ilike(f"%{kw}%"))

# 第二步：高重要性补充（如果关键词匹配不足）
if len(keyword_memories) < limit:
    补充 importance >= 7 的记忆（排除已选）

# 第三步：更新访问计数
for mem in selected:
    mem.access_count += 1
    mem.last_accessed = now()
```

### 4.5 系统提示词注入

在 Router Agent 的系统提示词中预留 `{user_memories}` 占位符：

```
## 关于该用户（长期记忆）
{user_memories}

## 你的能力
...
## 工作原则
1. 个性化服务：利用「关于该用户」中的记忆来提供个性化回答
   - 如果用户之前说过自己的偏好，请记住并应用
   - 如果用户提到过相关事件或人物，适当关联
...
```

### 4.6 API 接口

所有接口需要 Bearer Token 认证。

| 方法 | 路径 | 说明 | 参数 |
|------|------|------|------|
| GET | `/api/v1/memory/memories` | 获取记忆列表 | `memory_type`, `category`, `limit` (1-200) |
| GET | `/api/v1/memory/memories/search` | 关键词搜索 | `q` (必填), `limit` (1-50) |
| GET | `/api/v1/memory/memories/stats` | 记忆统计 | — |
| DELETE | `/api/v1/memory/memories/{id}` | 软删除 | — |

---

## 5. 前端实现

### 5.1 模块结构

```
frontend/src/
├── api/
│   └── memory.js                   # API 客户端封装
├── views/
│   └── MemoryView.vue              # 记忆管理页面
├── router/
│   └── index.js                    # 路由配置（/memory）
└── views/
    ├── ChatView.vue                # 侧边栏导航入口
    └── DashboardView.vue           # 头部按钮入口
```

### 5.2 记忆管理页面 MemoryView

页面布局从上到下：

1. **页面头部**：标题 + 返回按钮 + 刷新 + 主题切换
2. **统计卡片区**（4 列 grid）：
   - 记忆总数（含上限标签）
   - 平均重要性（/10）
   - 容量使用率（含进度条）
   - 类型覆盖数
3. **工具栏**：
   - 左侧：类型筛选下拉 + 分类筛选下拉
   - 右侧：搜索输入框 + 搜索按钮
4. **记忆卡片列表**（响应式 grid，最小 340px 自适应列数）：
   - 卡片头：类型标签（emoji + 文字）+ 分类 tag + 删除按钮（悬停显示）
   - 卡片体：记忆内容文本
   - 卡片底：重要性星级 + 置信度百分比 + 相对时间
5. **加载更多**：分页加载
6. **空状态**：引导用户去聊天

### 5.3 交互功能

| 功能 | 交互方式 |
|------|---------|
| 筛选 | 类型/分类下拉框，选择后自动刷新列表 |
| 搜索 | 输入关键词 + 回车或点击搜索按钮；清空自动恢复列表 |
| 删除 | 悬停卡片显示删除图标 → 确认弹窗 → 删除后从列表移除 + 刷新统计 |
| 加载更多 | 滚动到底部点击按钮，增量加载 PAGE_SIZE 条 |
| 刷新 | 重置所有筛选条件，重新加载列表和统计 |

### 5.4 导航入口

| 位置 | 组件 | 入口形式 |
|------|------|---------|
| 聊天页侧边栏 | `ChatView.vue` | 导航链接（Coin 图标 + "记忆管理"） |
| 数据看板页头部 | `DashboardView.vue` | 按钮（Coin 图标 + "记忆管理"） |

### 5.5 主题适配

所有组件完全适配深色/浅色主题，使用 CSS 变量（`var(--bg-base)`, `var(--primary-color)` 等），与项目整体风格一致。

---

## 6. 配置参数

### 6.1 记忆服务常量

在 `backend/app/services/memory_service.py` 中定义：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `MAX_MEMORIES_PER_USER` | 200 | 每用户最大记忆数，超出自动淘汰 |
| `MAX_MEMORIES_IN_CONTEXT` | 15 | 每次对话注入的最大记忆数 |
| `MEMORY_EXTRACTION_WINDOW` | 10 | 每隔 N 轮对话触发一次提取（预留） |
| `EXTRACTION_BATCH_SIZE` | 5 | 每次提取时处理的最近消息数 |

### 6.2 Agent 层过滤

在 `backend/app/agents/router_agent.py` 中定义：

| 参数 | 说明 |
|------|------|
| `MAX_MEMORIES_IN_CONTEXT` | 15，每次对话注入的最大记忆数 |
| `_TRIVIAL_KEYWORDS` | `{"你好", "您好", "hi", "hello", "谢谢", ...}` — 跳过提取的关键词集合 |

---

## 7. 数据库迁移

### 7.1 自动建表

应用启动时 `init_db()` → `Base.metadata.create_all()` 会自动创建 `user_memories` 表，本地与 Docker 均无需手动迁移。

### 7.2 增量迁移

如需更完整的数据库约束（CHECK 约束、`updated_at` 触发器、`pg_trgm` 全文索引），可手动执行增量脚本（幂等，可重复执行）：

```bash
# 已有数据库
docker exec -i ai_employee_postgres psql -U postgres -d ai_employee \
  < backend/migrations/002_add_user_memories.sql
```

### 7.3 全新数据库

`backend/migrations/init.sql` 末尾已包含 `user_memories` 表定义，全新部署自动包含。

---

## 8. 依赖

### 8.1 后端

无新增 Python 依赖——`langchain` 和 `langchain-openai` 项目已有。

### 8.2 前端

无新增 npm 依赖——使用项目已有的 Element Plus 组件。

---

## 9. 已知限制与后续改进

| 优先级 | 改进项 | 说明 |
|--------|--------|------|
| 高 | 流式路径 `conversation_id` 丢失 | `stream_message()` 中 `del conversation_id`，导致记忆无法溯源到具体会话 |
| 高 | `create_memories_batch` 逐条 commit | 循环中每条记忆单独 commit，批量时应改为 `add_all` + 单次 commit |
| 中 | 检索策略较简单 | 当前仅 `ilike` 关键词匹配，语义相近但用词不同的记忆无法命中；后续可引入 pgvector 向量检索 |
| 中 | 记忆提取无重试 | JSON 解析失败直接丢弃，可增加 1-2 次重试 |
| 低 | 记忆合并去重 | 新旧记忆描述同一事实时，应自动合并而非共存 |
| 低 | 时间感知衰减 | 事件类记忆（如"下周出差"）应随时间自动降低重要性或归档 |

---

## 10. 文件清单

### 10.1 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/models/user_memory.py` | `UserMemory` ORM 模型 |
| `backend/app/services/memory_service.py` | 记忆核心服务 |
| `backend/app/api/endpoints/memory.py` | 记忆管理 API |
| `backend/migrations/002_add_user_memories.sql` | 增量迁移脚本 |
| `frontend/src/api/memory.js` | 前端 API 客户端 |
| `frontend/src/views/MemoryView.vue` | 前端记忆管理页面 |

### 10.2 修改文件

| 文件 | 修改内容 |
|------|---------|
| `backend/app/agents/router_agent.py` | 对话前后注入记忆检索与提取（含流式路径） |
| `backend/app/models/__init__.py` | 注册 `UserMemory`（使 `create_all` 自动建表） |
| `backend/app/api/router.py` | 注册 `/memory` 路由 |
| `backend/migrations/init.sql` | 新建库时自带 `user_memories` 表 |
| `frontend/src/router/index.js` | 新增 `/memory` 路由 |
| `frontend/src/views/ChatView.vue` | 侧边栏新增记忆管理导航链接 |
| `frontend/src/views/DashboardView.vue` | 头部新增记忆管理按钮入口 |
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

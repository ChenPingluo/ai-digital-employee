-- ============================================
-- 用户长期记忆表迁移 (增量脚本)
--
-- 适用场景：
--   1. 已有数据库上手动执行：psql -U postgres -d ai_employee -f 002_add_user_memories.sql
--   2. 全新数据库：backend/migrations/init.sql 末尾已包含相同表结构，
--      且应用启动时 Base.metadata.create_all() 也会自动建表，二者均幂等。
--
-- 说明：
--   - 本脚本完全幂等（CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS）。
--   - CHECK 约束、触发器、注释是 ORM (create_all) 不会生成的部分，
--     手动执行本脚本可获得更完整的数据库约束。
-- ============================================

-- 全文检索扩展（用于 content 的 trigram 模糊匹配索引；可选）
-- 若环境无权创建扩展，下面 DO 块会安全跳过。
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
EXCEPTION WHEN insufficient_privilege OR feature_not_supported THEN
    RAISE NOTICE '跳过 pg_trgm 扩展（无权限或不支持），将不影响基础记忆功能。';
END $$;

-- 创建 user_memories 表
CREATE TABLE IF NOT EXISTS user_memories (
    -- 主键
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 用户关联（外键 + 级联删除）
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 记忆元数据
    memory_type VARCHAR(20) NOT NULL DEFAULT 'fact'
        CHECK (memory_type IN ('fact', 'preference', 'event', 'person', 'context')),
    category VARCHAR(50),

    -- 核心内容
    content TEXT NOT NULL,
    context TEXT,
    source_conversation_id UUID,

    -- 质量评分
    importance INTEGER NOT NULL DEFAULT 5 CHECK (importance >= 1 AND importance <= 10),
    confidence REAL NOT NULL DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),

    -- 访问统计
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed TIMESTAMPTZ,

    -- 状态
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_user_memories_user_type
    ON user_memories(user_id, memory_type);

CREATE INDEX IF NOT EXISTS idx_user_memories_user_active
    ON user_memories(user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_user_memories_importance
    ON user_memories(user_id, importance);

CREATE INDEX IF NOT EXISTS idx_user_memories_updated
    ON user_memories(user_id, updated_at DESC);

-- 全文搜索索引（依赖 pg_trgm；若扩展未启用则该语句报错，可注释掉）
CREATE INDEX IF NOT EXISTS idx_user_memories_content_trgm
    ON user_memories USING gin (content gin_trgm_ops);

-- 更新时间触发器（复用 init.sql 中已定义的 update_updated_at_column() 函数）
-- 若该函数不存在则先创建，保证脚本可独立运行。
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_user_memories_updated_at ON user_memories;
CREATE TRIGGER trigger_user_memories_updated_at
    BEFORE UPDATE ON user_memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 注释
COMMENT ON TABLE user_memories IS '用户长期记忆表 - 自动从对话中提取';
COMMENT ON COLUMN user_memories.memory_type IS '记忆类型: fact/preference/event/person/context';
COMMENT ON COLUMN user_memories.importance IS '重要性评分 (1-10)';
COMMENT ON COLUMN user_memories.confidence IS '置信度 (0.0-1.0)';
COMMENT ON COLUMN user_memories.is_active IS '软删除标记';

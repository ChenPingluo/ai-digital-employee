-- ============================================================================
-- AI数字员工系统 第二迭代 - 数据库验证脚本
--
-- 用途：验证第二迭代新增功能的数据正确性
-- 使用方式：连接 PostgreSQL 后逐段执行，或一次性执行全部
-- ============================================================================

-- ============================================================================
-- 1. 基础表结构验证（确认新增表已创建）
-- ============================================================================

-- 1.1 验证 conversations 表存在
SELECT 'conversations表' AS 验证项,
       CASE WHEN EXISTS (
           SELECT 1 FROM information_schema.tables 
           WHERE table_name = 'conversations'
       ) THEN '存在' ELSE '不存在' END AS 结果;

-- 1.2 验证 chat_messages 表存在
SELECT 'chat_messages表' AS 验证项,
       CASE WHEN EXISTS (
           SELECT 1 FROM information_schema.tables 
           WHERE table_name = 'chat_messages'
       ) THEN '存在' ELSE '不存在' END AS 结果;

-- 1.3 验证所有6张表均存在
SELECT table_name AS 表名, '存在' AS 状态
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('users', 'todos', 'meeting_rooms', 'reservations', 'conversations', 'chat_messages')
ORDER BY table_name;


-- ============================================================================
-- 2. 用户数据验证
-- ============================================================================

-- 2.1 验证测试账户存在
SELECT username AS 用户名, email AS 邮箱, department AS 部门, role AS 角色, is_active AS 激活状态
FROM users
WHERE username IN ('test', 'admin')
ORDER BY username;


-- ============================================================================
-- 3. 会议室数据验证
-- ============================================================================

-- 3.1 验证会议室种子数据
SELECT name AS 会议室名称, location AS 位置, capacity AS 容量, 
       array_to_string(equipment, ', ') AS 设备, is_available AS 可用
FROM meeting_rooms
ORDER BY name;


-- ============================================================================
-- 4. 待办事项数据验证
-- ============================================================================

-- 4.1 待办事项总览（按用户分组）
SELECT u.username AS 用户, COUNT(t.id) AS 待办总数,
       SUM(CASE WHEN t.status = 'pending' THEN 1 ELSE 0 END) AS 待处理,
       SUM(CASE WHEN t.status = 'in_progress' THEN 1 ELSE 0 END) AS 进行中,
       SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) AS 已完成,
       SUM(CASE WHEN t.status = 'cancelled' THEN 1 ELSE 0 END) AS 已取消
FROM users u
LEFT JOIN todos t ON t.user_id = u.id
GROUP BY u.username
ORDER BY u.username;

-- 4.2 查看最新创建的待办事项（验证Postman测试创建的数据）
SELECT t.title AS 标题, t.priority AS 优先级, t.status AS 状态, 
       t.created_at AS 创建时间, u.username AS 用户
FROM todos t
JOIN users u ON t.user_id = u.id
ORDER BY t.created_at DESC
LIMIT 5;


-- ============================================================================
-- 5. 会议室预约数据验证（第二迭代重点）
-- ============================================================================

-- 5.1 预约记录总览
SELECT r.title AS 会议主题, m.name AS 会议室, u.username AS 预约人,
       r.start_time AS 开始时间, r.end_time AS 结束时间,
       r.status AS 状态, r.created_at AS 创建时间
FROM reservations r
JOIN meeting_rooms m ON r.room_id = m.id
JOIN users u ON r.user_id = u.id
ORDER BY r.created_at DESC
LIMIT 10;

-- 5.2 按会议室统计预约次数和总时长（与统计API对齐）
SELECT m.name AS 会议室名称,
       COUNT(r.id) AS 预约次数,
       COALESCE(ROUND(SUM(EXTRACT(EPOCH FROM (r.end_time - r.start_time)) / 3600)::numeric, 1), 0) AS 总时长_小时
FROM meeting_rooms m
LEFT JOIN reservations r ON r.room_id = m.id AND r.status = 'confirmed'
GROUP BY m.name
ORDER BY m.name;

-- 5.3 验证时间冲突约束（EXCLUDE约束）
-- 此查询应返回0行，表示没有同一会议室的时间重叠预约
SELECT r1.id AS 预约1, r2.id AS 预约2, m.name AS 会议室,
       r1.start_time AS 预约1开始, r1.end_time AS 预约1结束,
       r2.start_time AS 预约2开始, r2.end_time AS 预约2结束
FROM reservations r1
JOIN reservations r2 ON r1.room_id = r2.room_id AND r1.id < r2.id
JOIN meeting_rooms m ON r1.room_id = m.id
WHERE r1.status = 'confirmed' AND r2.status = 'confirmed'
  AND tstzrange(r1.start_time, r1.end_time) && tstzrange(r2.start_time, r2.end_time);


-- ============================================================================
-- 6. 会话与消息数据验证（第二迭代重点）
-- ============================================================================

-- 6.1 会话列表（按用户分组统计）
SELECT u.username AS 用户, COUNT(c.id) AS 会话数,
       MAX(c.updated_at) AS 最后更新
FROM users u
LEFT JOIN conversations c ON c.user_id = u.id
GROUP BY u.username
ORDER BY u.username;

-- 6.2 查看最近的会话及其消息数
SELECT c.title AS 会话标题, u.username AS 用户,
       COUNT(m.id) AS 消息数,
       c.created_at AS 创建时间, c.updated_at AS 更新时间
FROM conversations c
JOIN users u ON c.user_id = u.id
LEFT JOIN chat_messages m ON m.conversation_id = c.id
GROUP BY c.id, c.title, u.username, c.created_at, c.updated_at
ORDER BY c.updated_at DESC
LIMIT 10;

-- 6.3 查看最近会话的消息详情（验证消息持久化）
SELECT c.title AS 会话标题, m.role AS 角色, 
       LEFT(m.content, 80) AS 内容摘要,
       m.created_at AS 时间
FROM chat_messages m
JOIN conversations c ON m.conversation_id = c.id
ORDER BY m.created_at DESC
LIMIT 20;

-- 6.4 验证消息角色分布
SELECT role AS 消息角色, COUNT(*) AS 数量
FROM chat_messages
GROUP BY role
ORDER BY role;


-- ============================================================================
-- 7. 数据闭环验证
-- ============================================================================

-- 7.1 闭环验证：通过AI对话创建的待办是否落库
-- 查找标题中包含特定关键词的待办（AI对话创建的通常有自然语言特征）
SELECT t.title AS 待办标题, t.status AS 状态, t.priority AS 优先级,
       t.created_at AS 创建时间, u.username AS 所属用户
FROM todos t
JOIN users u ON t.user_id = u.id
WHERE t.created_at >= NOW() - INTERVAL '1 day'
ORDER BY t.created_at DESC;

-- 7.2 闭环验证：通过AI对话创建的预约是否落库
SELECT r.title AS 会议主题, m.name AS 会议室, r.status AS 状态,
       r.start_time AS 开始时间, r.end_time AS 结束时间,
       r.created_at AS 创建时间
FROM reservations r
JOIN meeting_rooms m ON r.room_id = m.id
WHERE r.created_at >= NOW() - INTERVAL '1 day'
ORDER BY r.created_at DESC;


-- ============================================================================
-- 8. 汇总统计（快速确认系统数据状态）
-- ============================================================================

SELECT '用户数' AS 指标, COUNT(*)::text AS 值 FROM users
UNION ALL
SELECT '待办事项数', COUNT(*)::text FROM todos
UNION ALL
SELECT '会议室数', COUNT(*)::text FROM meeting_rooms
UNION ALL
SELECT '预约记录数', COUNT(*)::text FROM reservations
UNION ALL
SELECT '会话数', COUNT(*)::text FROM conversations
UNION ALL
SELECT '聊天消息数', COUNT(*)::text FROM chat_messages
ORDER BY 指标;

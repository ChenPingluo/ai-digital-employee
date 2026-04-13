-- ============================================================================
-- AI数字员工系统 - 数据库初始化脚本
-- 
-- 本脚本包含系统所需的所有数据库表结构定义，包括：
-- 1. 用户表 (users) - 存储系统用户信息
-- 2. 待办事项表 (todos) - 存储用户的待办任务
-- 3. 会议室表 (meeting_rooms) - 存储会议室资源信息
-- 4. 预约表 (reservations) - 存储会议室预约记录
--
-- 执行前请确保：
-- 1. 已创建数据库 ai_employee
-- 2. 当前用户具有创建表和扩展的权限
-- ============================================================================

-- ============================================================================
-- 启用必要的 PostgreSQL 扩展
-- ============================================================================

-- uuid-ossp 扩展：用于生成 UUID 主键
-- 提供 uuid_generate_v4() 函数，生成随机 UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- btree_gist 扩展：用于支持 EXCLUDE 约束中的时间范围排除
-- 允许在 GiST 索引中使用 btree 操作符，配合 tstzrange 防止时间重叠
CREATE EXTENSION IF NOT EXISTS btree_gist;


-- ============================================================================
-- 用户表 (users)
-- 
-- 存储系统用户的基本信息，包括认证凭据和组织归属。
-- 支持基于角色的访问控制 (RBAC)。
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    -- 主键：使用 UUID 作为主键，自动生成
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 用户名：唯一标识符，用于登录
    username VARCHAR(50) UNIQUE NOT NULL,
    
    -- 电子邮箱：唯一，用于通知和找回密码
    email VARCHAR(100) UNIQUE NOT NULL,
    
    -- 哈希密码：使用 bcrypt 加密存储
    hashed_password VARCHAR(255) NOT NULL,
    
    -- 部门：用户所属部门，可为空
    department VARCHAR(100),
    
    -- 角色：用户角色，默认为普通用户
    -- 可选值：user（普通用户）, admin（管理员）, manager（经理）
    role VARCHAR(20) DEFAULT 'user',
    
    -- 账户状态：是否激活
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 创建时间：记录创建时的时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 更新时间：每次更新时自动刷新
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户表索引
-- 用户名索引：加速登录时的用户名查询
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- 邮箱索引：加速邮箱相关查询（如找回密码）
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 部门索引：加速按部门筛选用户
CREATE INDEX IF NOT EXISTS idx_users_department ON users(department);

-- 添加表和字段注释
COMMENT ON TABLE users IS '系统用户表，存储用户账户信息和认证凭据';
COMMENT ON COLUMN users.id IS '用户唯一标识符，UUID格式';
COMMENT ON COLUMN users.username IS '用户登录名，系统内唯一';
COMMENT ON COLUMN users.email IS '用户电子邮箱，用于通知和身份验证';
COMMENT ON COLUMN users.hashed_password IS 'bcrypt加密的用户密码';
COMMENT ON COLUMN users.department IS '用户所属部门名称';
COMMENT ON COLUMN users.role IS '用户角色：user/admin/manager';
COMMENT ON COLUMN users.is_active IS '账户是否激活，FALSE表示已禁用';


-- ============================================================================
-- 待办事项表 (todos)
-- 
-- 存储用户的待办任务，支持优先级、状态和截止日期管理。
-- ============================================================================
CREATE TABLE IF NOT EXISTS todos (
    -- 主键：使用 UUID 作为主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 外键：关联用户表，级联删除
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 任务标题：简短描述任务内容
    title VARCHAR(200) NOT NULL,
    
    -- 任务描述：详细说明任务要求
    description TEXT,
    
    -- 优先级：0-3，分别对应 低/中/高/紧急
    -- 使用 CHECK 约束确保值在有效范围内
    priority SMALLINT DEFAULT 0 CHECK (priority >= 0 AND priority <= 3),
    
    -- 任务状态：pending（待处理）, in_progress（进行中）, completed（已完成）, cancelled（已取消）
    status VARCHAR(20) DEFAULT 'pending',
    
    -- 截止日期：任务应完成的时间
    due_date TIMESTAMPTZ,
    
    -- 创建时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 更新时间
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 待办事项表索引
-- 复合索引：加速按用户和状态筛选任务
CREATE INDEX IF NOT EXISTS idx_todos_user_status ON todos(user_id, status);

-- 截止日期索引：加速查询即将到期的任务
CREATE INDEX IF NOT EXISTS idx_todos_due_date ON todos(due_date);

-- 优先级索引：加速按优先级排序和筛选
CREATE INDEX IF NOT EXISTS idx_todos_priority ON todos(priority);

-- 添加表和字段注释
COMMENT ON TABLE todos IS '待办事项表，存储用户的任务列表';
COMMENT ON COLUMN todos.id IS '任务唯一标识符';
COMMENT ON COLUMN todos.user_id IS '任务所属用户ID';
COMMENT ON COLUMN todos.title IS '任务标题';
COMMENT ON COLUMN todos.description IS '任务详细描述';
COMMENT ON COLUMN todos.priority IS '任务优先级：0-低，1-中，2-高，3-紧急';
COMMENT ON COLUMN todos.status IS '任务状态：pending/in_progress/completed/cancelled';
COMMENT ON COLUMN todos.due_date IS '任务截止日期';


-- ============================================================================
-- 会议室表 (meeting_rooms)
-- 
-- 存储会议室资源信息，包括位置、容量和设备配置。
-- ============================================================================
CREATE TABLE IF NOT EXISTS meeting_rooms (
    -- 主键：使用 UUID 作为主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 会议室名称：唯一标识，如"A栋301会议室"
    name VARCHAR(100) UNIQUE NOT NULL,
    
    -- 会议室位置：详细地址描述
    location VARCHAR(200),
    
    -- 容纳人数：会议室最大容量
    capacity INTEGER NOT NULL,
    
    -- 设备列表：会议室配备的设备，如投影仪、白板、视频会议设备等
    -- 使用 PostgreSQL 数组类型存储
    equipment TEXT[],
    
    -- 可用状态：是否可预约
    is_available BOOLEAN DEFAULT TRUE,
    
    -- 创建时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 更新时间
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 会议室表索引
-- 可用状态索引：加速查询可预约的会议室
CREATE INDEX IF NOT EXISTS idx_rooms_available ON meeting_rooms(is_available);

-- 容量索引：加速按容量筛选会议室
CREATE INDEX IF NOT EXISTS idx_rooms_capacity ON meeting_rooms(capacity);

-- 添加表和字段注释
COMMENT ON TABLE meeting_rooms IS '会议室资源表，存储会议室信息';
COMMENT ON COLUMN meeting_rooms.id IS '会议室唯一标识符';
COMMENT ON COLUMN meeting_rooms.name IS '会议室名称';
COMMENT ON COLUMN meeting_rooms.location IS '会议室位置描述';
COMMENT ON COLUMN meeting_rooms.capacity IS '会议室最大容纳人数';
COMMENT ON COLUMN meeting_rooms.equipment IS '会议室设备列表';
COMMENT ON COLUMN meeting_rooms.is_available IS '会议室是否可预约';


-- ============================================================================
-- 会议室预约表 (reservations)
-- 
-- 存储会议室预约记录，使用排除约束防止时间冲突。
-- ============================================================================
CREATE TABLE IF NOT EXISTS reservations (
    -- 主键：使用 UUID 作为主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 外键：关联会议室表，级联删除
    room_id UUID NOT NULL REFERENCES meeting_rooms(id) ON DELETE CASCADE,
    
    -- 外键：关联用户表，级联删除
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 会议标题：会议主题
    title VARCHAR(200) NOT NULL,
    
    -- 开始时间：会议开始时间
    start_time TIMESTAMPTZ NOT NULL,
    
    -- 结束时间：会议结束时间
    end_time TIMESTAMPTZ NOT NULL,
    
    -- 预约状态：confirmed（已确认）, cancelled（已取消）, completed（已完成）
    status VARCHAR(20) DEFAULT 'confirmed',
    
    -- 创建时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 更新时间
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- CHECK 约束：确保结束时间晚于开始时间
    CONSTRAINT chk_reservation_time CHECK (end_time > start_time),
    
    -- EXCLUDE 约束：防止同一会议室在相同时间段被重复预约
    -- 仅对状态为 'confirmed' 的预约生效
    -- 使用 tstzrange 表示时间范围，&& 操作符检测重叠
    CONSTRAINT excl_room_time_overlap EXCLUDE USING gist (
        room_id WITH =,
        tstzrange(start_time, end_time) WITH &&
    ) WHERE (status = 'confirmed')
);

-- 预约表索引
-- 复合索引：加速查询特定会议室在特定时间段的预约
CREATE INDEX IF NOT EXISTS idx_reservations_room_time ON reservations(room_id, start_time, end_time);

-- 用户索引：加速查询用户的所有预约
CREATE INDEX IF NOT EXISTS idx_reservations_user ON reservations(user_id);

-- 状态索引：加速按状态筛选预约
CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status);

-- 添加表和字段注释
COMMENT ON TABLE reservations IS '会议室预约表，存储预约记录';
COMMENT ON COLUMN reservations.id IS '预约唯一标识符';
COMMENT ON COLUMN reservations.room_id IS '预约的会议室ID';
COMMENT ON COLUMN reservations.user_id IS '预约人用户ID';
COMMENT ON COLUMN reservations.title IS '会议主题';
COMMENT ON COLUMN reservations.start_time IS '会议开始时间';
COMMENT ON COLUMN reservations.end_time IS '会议结束时间';
COMMENT ON COLUMN reservations.status IS '预约状态：confirmed/cancelled/completed';


-- ============================================================================
-- 创建更新时间触发器
-- 
-- 自动更新 updated_at 字段，确保数据变更时间准确
-- ============================================================================

-- 创建更新时间戳的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    -- 将 updated_at 字段设置为当前时间
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为 users 表添加更新时间触发器
DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 为 todos 表添加更新时间触发器
DROP TRIGGER IF EXISTS trigger_todos_updated_at ON todos;
CREATE TRIGGER trigger_todos_updated_at
    BEFORE UPDATE ON todos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 为 meeting_rooms 表添加更新时间触发器
DROP TRIGGER IF EXISTS trigger_meeting_rooms_updated_at ON meeting_rooms;
CREATE TRIGGER trigger_meeting_rooms_updated_at
    BEFORE UPDATE ON meeting_rooms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 为 reservations 表添加更新时间触发器
DROP TRIGGER IF EXISTS trigger_reservations_updated_at ON reservations;
CREATE TRIGGER trigger_reservations_updated_at
    BEFORE UPDATE ON reservations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 插入测试数据
-- ============================================================================

-- 插入测试用户（密码为 123456，使用 bcrypt 加密）
INSERT INTO users (username, email, hashed_password, department, role)
VALUES (
    'test',
    'test@example.com',
    '$2b$12$pssmKdwnn355gK9jTECfXu6cn29a3EkVKm7Ob.HNhrlAfy1d79QB6',
    '技术部',
    'user'
) ON CONFLICT (username) DO NOTHING;

-- 插入管理员用户（密码为 admin123，使用 bcrypt 加密）
INSERT INTO users (username, email, hashed_password, department, role)
VALUES (
    'admin',
    'admin@example.com',
    '$2b$12$pssmKdwnn355gK9jTECfXu6cn29a3EkVKm7Ob.HNhrlAfy1d79QB6',
    '管理部',
    'admin'
) ON CONFLICT (username) DO NOTHING;

-- 插入测试会议室
INSERT INTO meeting_rooms (name, location, capacity, equipment, is_available)
VALUES 
    ('A栋301会议室', 'A栋3楼', 10, ARRAY['投影仪', '白板', '视频会议设备'], TRUE),
    ('A栋302会议室', 'A栋3楼', 6, ARRAY['投影仪', '白板'], TRUE),
    ('B栋201会议室', 'B栋2楼', 20, ARRAY['投影仪', '白板', '视频会议设备', '音响'], TRUE)
ON CONFLICT (name) DO NOTHING;


-- ============================================================================
-- 初始化完成
-- ============================================================================
-- 脚本执行完成后，数据库将包含以下表：
-- 1. users - 用户表
-- 2. todos - 待办事项表
-- 3. meeting_rooms - 会议室表
-- 4. reservations - 预约表
-- 
-- 测试账户：
-- - 普通用户：test / 123456
-- - 管理员：admin / 123456
--
-- 所有表都配置了适当的索引、约束和触发器，可直接用于生产环境。
-- ============================================================================

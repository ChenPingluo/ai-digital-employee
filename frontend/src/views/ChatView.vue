<!--
  聊天视图组件 ChatView.vue

  AI 数字员工对话主界面，提供：
  - 左侧可折叠侧边栏（导航链接）
  - 消息列表展示与自动滚动
  - 消息输入与发送
  - 消息气泡（用户/AI）
  - 加载状态动画
  - 空状态欢迎语
  - 响应式设计
-->

<template>
  <div class="chat-view">
    <!-- 侧边栏 -->
    <aside
      class="sidebar"
      :class="{ 'sidebar-collapsed': isSidebarCollapsed }"
    >
      <!-- 侧边栏头部 -->
      <div class="sidebar-header">
        <div class="logo" v-show="!isSidebarCollapsed">
          <el-icon :size="28" color="#409EFF">
            <Monitor />
          </el-icon>
          <span class="logo-text">AI 助手</span>
        </div>
        <!-- 折叠按钮 -->
        <el-button
          class="collapse-btn"
          :icon="isSidebarCollapsed ? Expand : Fold"
          text
          @click="toggleSidebar"
        />
      </div>

      <!-- 导航菜单 -->
      <nav class="sidebar-nav">
        <router-link
          to="/"
          class="nav-item"
          :class="{ active: $route.path === '/' }"
        >
          <el-icon :size="20"><ChatDotRound /></el-icon>
          <span v-show="!isSidebarCollapsed">对话</span>
        </router-link>

        <router-link
          to="/dashboard"
          class="nav-item"
          :class="{ active: $route.path === '/dashboard' }"
        >
          <el-icon :size="20"><DataLine /></el-icon>
          <span v-show="!isSidebarCollapsed">数据看板</span>
        </router-link>

        <router-link
          to="/memory"
          class="nav-item"
          :class="{ active: $route.path === '/memory' }"
        >
          <el-icon :size="20"><Coin /></el-icon>
          <span v-show="!isSidebarCollapsed">记忆管理</span>
        </router-link>
      </nav>

      <!-- 新建话题按钮 -->
      <div class="new-topic-section">
        <el-button
          class="new-topic-btn"
          type="primary"
          :icon="Plus"
          @click="chatStore.createNewConversation()"
        >
          <span v-show="!isSidebarCollapsed">新建话题</span>
        </el-button>
      </div>

      <!-- 对话历史列表 -->
      <div class="conversation-list" v-show="!isSidebarCollapsed">
        <div class="conversation-list-header">
          <span>历史对话</span>
        </div>
        <div class="conversation-list-body">
          <div
            v-for="conv in chatStore.conversations"
            :key="conv.id"
            class="conversation-item"
            :class="{ active: chatStore.currentConversationId === conv.id }"
            @click="chatStore.switchConversation(conv.id)"
          >
            <div class="conversation-info">
              <span class="conversation-title">{{ conv.title || '新对话' }}</span>
              <span class="conversation-time">{{ formatRelativeTime(conv.updated_at || conv.created_at) }}</span>
            </div>
            <el-button
              class="conversation-delete-btn"
              :icon="Delete"
              text
              size="small"
              @click.stop="handleDeleteConversation(conv.id)"
            />
          </div>
          <div v-if="chatStore.conversations.length === 0" class="conversation-empty">
            暂无历史对话
          </div>
        </div>
      </div>

      <!-- 侧边栏底部 -->
      <div class="sidebar-footer">
        <!-- 用户信息 -->
        <div class="footer-top">
          <div class="user-info" v-show="!isSidebarCollapsed">
            <el-avatar :size="36" class="user-avatar">
              <el-icon><User /></el-icon>
            </el-avatar>
            <div class="user-detail">
              <span class="user-name">{{ userStore.displayName || '用户' }}</span>
              <span class="user-role">在线</span>
            </div>
          </div>

          <el-button
            class="theme-toggle-btn"
            text
            @click="themeStore.toggleTheme()"
          >
            <el-icon>
              <component :is="isDarkTheme ? Sunny : Moon" />
            </el-icon>
            <span v-show="!isSidebarCollapsed">{{ isDarkTheme ? '浅色界面' : '深色界面' }}</span>
          </el-button>
        </div>

        <!-- 退出按钮 -->
        <el-button
          class="logout-btn"
          :icon="SwitchButton"
          text
          @click="handleLogout"
        >
          <span v-show="!isSidebarCollapsed">退出</span>
        </el-button>
      </div>
    </aside>

    <!-- 移动端侧边栏遮罩 -->
    <div
      v-if="isMobileMenuOpen"
      class="sidebar-overlay"
      @click="isMobileMenuOpen = false"
    ></div>

    <!-- 主内容区 -->
    <main class="chat-main">
      <!-- 移动端头部 -->
      <header class="mobile-header">
        <el-button
          :icon="Menu"
          text
          @click="isMobileMenuOpen = true"
        />
        <h1>AI 数字员工</h1>
        <div style="width: 32px;"></div>
      </header>

      <!-- 消息列表区域 -->
      <div class="message-area" ref="messageAreaRef">
        <!-- 空状态欢迎语 -->
        <div v-if="messages.length === 0" class="welcome-section">
          <div class="welcome-icon">
            <el-icon :size="64" color="#409EFF">
              <ChatDotRound />
            </el-icon>
          </div>
          <h2>欢迎使用 AI 数字员工系统</h2>
          <p class="welcome-desc">我是您的智能办公助手，可以帮助您：</p>

          <!-- 功能介绍卡片 -->
          <div class="feature-cards">
            <div
              class="feature-card"
              v-for="feature in features"
              :key="feature.title"
              @click="handleFeatureClick(feature.example)"
            >
              <el-icon :size="24" :color="feature.color">
                <component :is="feature.icon" />
              </el-icon>
              <div class="feature-content">
                <h3>{{ feature.title }}</h3>
                <p>{{ feature.desc }}</p>
              </div>
            </div>
          </div>

          <!-- 快捷示例 -->
          <div class="quick-examples">
            <p>试试这些指令：</p>
            <div class="example-tags">
              <el-tag
                v-for="example in quickExamples"
                :key="example"
                class="example-tag"
                effect="plain"
                @click="handleFeatureClick(example)"
              >
                {{ example }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <div v-else class="message-list">
          <ChatMessage
            v-for="msg in messages"
            :key="msg.id"
            :message="msg"
          />

          <!-- 思考中动画 -->
          <div v-if="isLoading && !hasStreamingMessage" class="thinking-indicator">
            <div class="thinking-avatar">
              <el-avatar :size="36" class="avatar-ai">
                <el-icon :size="20"><Monitor /></el-icon>
              </el-avatar>
            </div>
            <div class="thinking-bubble">
              <span class="thinking-text">思考中</span>
              <span class="thinking-dots">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-section">
        <ChatInput
          ref="chatInputRef"
          :disabled="isLoading"
          placeholder="输入您的问题或指令..."
          @send="handleSendMessage"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
/**
 * 聊天视图组件
 *
 * AI 对话的主界面，核心功能组件
 */

import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  Monitor,
  ChatDotRound,
  DataLine,
  Coin,
  User,
  SwitchButton,
  Menu,
  Fold,
  Expand,
  List,
  Calendar,
  Cloudy,
  Setting,
  Plus,
  Delete,
  Moon,
  Sunny
} from '@element-plus/icons-vue'

// 导入组件
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'

// 导入 Store
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'

// ==================== 路由和状态 ====================

const router = useRouter()
const chatStore = useChatStore()
const userStore = useUserStore()
const themeStore = useThemeStore()

// ==================== 响应式数据 ====================

/**
 * 侧边栏是否折叠
 */
const isSidebarCollapsed = ref(false)

/**
 * 移动端菜单是否打开
 */
const isMobileMenuOpen = ref(false)

/**
 * 消息区域 DOM 引用
 */
const messageAreaRef = ref(null)

/**
 * 输入框组件引用
 */
const chatInputRef = ref(null)

// ==================== 计算属性 ====================

/**
 * 消息列表（从 store 获取）
 */
const messages = computed(() => chatStore.messages)

/**
 * 加载状态
 */
const isLoading = computed(() => chatStore.isLoading)

/**
 * 当前流式内容
 */
const streamingContent = computed(() => chatStore.streamingContent)

/**
 * 是否存在正在流式生成的消息
 */
const hasStreamingMessage = computed(() => {
  return messages.value.some((msg) => msg.isStreaming)
})

const isDarkTheme = computed(() => themeStore.isDark)

// ==================== 功能介绍数据 ====================

/**
 * 功能介绍卡片数据
 */
const features = [
  {
    icon: List,
    title: '待办管理',
    desc: '创建、查看、完成待办事项',
    color: '#409EFF',
    example: '帮我创建一个待办：下午3点开会'
  },
  {
    icon: Calendar,
    title: '会议预约',
    desc: '预约会议室、管理会议日程',
    color: '#67C23A',
    example: '预约明天上午10点的会议室'
  },
  {
    icon: Cloudy,
    title: '天气查询',
    desc: '查询任意城市的天气信息',
    color: '#E6A23C',
    example: '查询北京今天的天气'
  },
  {
    icon: Setting,
    title: '智能助手',
    desc: '回答问题、提供建议和帮助',
    color: '#909399',
    example: '有什么可以帮助你的吗'
  }
]

/**
 * 快捷示例
 */
const quickExamples = [
  '查看我今天的待办',
  '创建一个待办事项',
  '预约会议室',
  '今天天气怎么样'
]

// ==================== 方法 ====================

/**
 * 切换侧边栏折叠状态
 */
const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

/**
 * 发送消息
 * @param {string} content - 消息内容
 */
const handleSendMessage = async (content) => {
  if (!content.trim()) return

  // 使用流式接口发送消息
  await chatStore.sendMessageWithStream(content)

  // 滚动到底部
  scrollToBottom()
}

/**
 * 点击功能卡片或示例
 * @param {string} example - 示例文本
 */
const handleFeatureClick = (example) => {
  handleSendMessage(example)
}

/**
 * 滚动到底部
 */
const scrollToBottom = () => {
  nextTick(() => {
    if (messageAreaRef.value) {
      messageAreaRef.value.scrollTop = messageAreaRef.value.scrollHeight
    }
  })
}

/**
 * 处理退出登录
 */
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要退出登录吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 清空聊天记录
    chatStore.clearMessages()

    // 退出登录
    userStore.logout()
  } catch {
    // 用户取消
  }
}

/**
 * 删除会话（带确认）
 * @param {string} conversationId - 会话 ID
 */
const handleDeleteConversation = async (conversationId) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个对话吗？删除后无法恢复。',
      '删除对话',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    await chatStore.deleteConversation(conversationId)
  } catch {
    // 用户取消
  }
}

/**
 * 格式化相对时间
 * @param {string} timestamp - ISO 时间字符串
 * @returns {string} 相对时间文本
 */
const formatRelativeTime = (timestamp) => {
  if (!timestamp) return ''
  const now = new Date()
  const date = new Date(timestamp)
  const diff = now - date
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  return `${month}-${day}`
}

// ==================== 生命周期 ====================

onMounted(() => {
  // 初始化用户信息
  userStore.initializeAuth()

  // 加载会话列表
  chatStore.loadConversations()

  // 聚焦到输入框
  nextTick(() => {
    chatInputRef.value?.focus()
  })
})

// ==================== 监听器 ====================

// 监听消息变化，自动滚动到底部
watch(
  () => messages.value.length,
  () => {
    scrollToBottom()
  }
)

watch(
  () => streamingContent.value,
  () => {
    scrollToBottom()
  }
)

// 监听移动端菜单状态
watch(isMobileMenuOpen, (isOpen) => {
  if (isOpen) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})
</script>

<style scoped>
/* ==================== 主容器布局 ==================== */

.chat-view {
  display: flex;
  height: 100vh;
  background-color: var(--bg-base);
  overflow: hidden;
}

/* ==================== 侧边栏样式 ==================== */

.sidebar {
  width: 240px;
  background: var(--bg-light);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-base);
  transition: width var(--transition-base);
  z-index: 100;
}

.sidebar-collapsed {
  width: 64px;
}

/* 侧边栏头部 */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border-base);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo :deep(.el-icon) {
  color: var(--primary-color) !important;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.collapse-btn {
  padding: 8px;
  color: var(--text-secondary) !important;
  background: var(--bg-white) !important;
  border: 1px solid var(--border-base) !important;
  border-radius: var(--radius-base) !important;
  transition: all var(--transition-fast);
}

.collapse-btn:hover {
  color: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  background: rgba(0, 212, 255, 0.08) !important;
}

/* 导航菜单 */
.sidebar-nav {
  padding: 16px 8px 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-base);
  color: var(--text-secondary);
  margin-bottom: 4px;
  transition: all var(--transition-fast);
  text-decoration: none;
}

.nav-item:hover {
  background-color: rgba(0, 212, 255, 0.08);
  color: var(--primary-color);
}

.nav-item.active {
  background-color: rgba(0, 212, 255, 0.12);
  color: var(--primary-color);
  font-weight: 500;
}

.sidebar-collapsed .nav-item {
  justify-content: center;
  padding: 12px;
}

/* ==================== 新建话题按钮 ==================== */

.new-topic-section {
  padding: 4px 8px 8px;
}

.new-topic-btn {
  width: 100%;
  border-radius: var(--radius-base);
  background: transparent !important;
  border: 1px dashed var(--border-base) !important;
  color: var(--text-secondary) !important;
  transition: all var(--transition-fast);
}

.new-topic-btn:hover {
  border-color: var(--primary-color) !important;
  background: rgba(0, 212, 255, 0.05) !important;
  color: var(--primary-color) !important;
}

.sidebar-collapsed .new-topic-btn {
  padding: 8px;
}

.sidebar-collapsed .new-topic-btn :deep(.el-icon) {
  margin-right: 0;
}

/* ==================== 对话历史列表 ==================== */

.conversation-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-top: 1px solid var(--border-base);
  padding: 0 8px;
}

.conversation-list-header {
  padding: 10px 8px 6px;
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  flex-shrink: 0;
}

.conversation-list-body {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 8px;
}

/* 滚动条深色样式 */
.conversation-list-body::-webkit-scrollbar {
  width: 4px;
}

.conversation-list-body::-webkit-scrollbar-track {
  background: transparent;
}

.conversation-list-body::-webkit-scrollbar-thumb {
  background: var(--border-base);
  border-radius: 2px;
}

.conversation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 10px;
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: 2px;
  background: transparent;
}

.conversation-item:hover {
  background-color: rgba(0, 212, 255, 0.05);
}

.conversation-item.active {
  background-color: rgba(0, 212, 255, 0.08);
  border-left: 3px solid var(--primary-color);
  padding-left: 7px;
}

.conversation-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.conversation-title {
  font-size: 13px;
  color: var(--text-regular);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-item.active .conversation-title {
  color: var(--text-primary);
  font-weight: 500;
}

.conversation-time {
  font-size: 11px;
  color: var(--text-secondary);
}

.conversation-delete-btn {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity var(--transition-fast);
  color: var(--danger-color) !important;
  padding: 4px;
  margin-left: 4px;
}

.conversation-item:hover .conversation-delete-btn {
  opacity: 1;
}

.conversation-empty {
  text-align: center;
  padding: 20px 0;
  font-size: 12px;
  color: var(--text-secondary);
}

/* 侧边栏底部 */
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-base);
  background: var(--bg-light);
}

.footer-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.user-avatar {
  background: var(--gradient-tech) !important;
  color: white;
}

.user-detail {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.user-role {
  font-size: 12px;
  color: var(--success-color);
}

.theme-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  color: var(--text-secondary) !important;
  background: var(--bg-white) !important;
  border: 1px solid var(--border-base) !important;
  border-radius: var(--radius-base) !important;
  padding: 8px 10px !important;
}

.theme-toggle-btn:hover {
  color: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  background: rgba(0, 212, 255, 0.08) !important;
}

.sidebar-collapsed .theme-toggle-btn {
  width: 100%;
  justify-content: center;
}

.logout-btn {
  width: 100%;
  justify-content: flex-start;
  color: var(--text-secondary) !important;
  transition: color var(--transition-fast);
}

.logout-btn:hover {
  color: var(--danger-color) !important;
}

.sidebar-collapsed .logout-btn {
  justify-content: center;
}

/* ==================== 主内容区 ==================== */

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg-base);
}

/* 移动端头部 */
.mobile-header {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-light);
  border-bottom: 1px solid var(--border-base);
}

.mobile-header h1 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.mobile-header :deep(.el-button) {
  color: var(--text-secondary) !important;
}

/* ==================== 消息区域 ==================== */

.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* 消息区域滚动条 */
.message-area::-webkit-scrollbar {
  width: 6px;
}

.message-area::-webkit-scrollbar-track {
  background: transparent;
}

.message-area::-webkit-scrollbar-thumb {
  background: var(--border-base);
  border-radius: 3px;
}

.message-area::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}

/* 欢迎区域 */
.welcome-section {
  max-width: 700px;
  margin: 0 auto;
  text-align: center;
  padding: 40px 20px;
}

.welcome-icon {
  margin-bottom: 20px;
}

.welcome-icon :deep(.el-icon) {
  color: var(--primary-color) !important;
}

.welcome-section h2 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.welcome-desc {
  font-size: 16px;
  color: var(--text-secondary);
  margin: 0 0 32px 0;
}

/* 功能卡片 */
.feature-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.feature-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 20px;
  background: var(--bg-light);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-large);
  cursor: pointer;
  transition: all var(--transition-base);
  text-align: left;
}

.feature-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 212, 255, 0.3);
  box-shadow: var(--glow-primary);
}

.feature-card :deep(.el-icon) {
  color: var(--primary-color) !important;
}

.feature-content h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.feature-content p {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}

/* 快捷示例 */
.quick-examples {
  margin-top: 24px;
}

.quick-examples > p {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.example-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.example-tag {
  cursor: pointer;
  transition: all var(--transition-fast);
  background-color: var(--bg-white) !important;
  color: var(--primary-color) !important;
  border-color: var(--border-base) !important;
}

.example-tag:hover {
  background-color: rgba(0, 212, 255, 0.1) !important;
  color: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
}

/* 消息列表 */
.message-list {
  max-width: 900px;
  margin: 0 auto;
}

/* 思考中动画 */
.thinking-indicator {
  display: flex;
  gap: 12px;
  padding: 0 16px;
  margin-bottom: 20px;
}

.thinking-avatar .avatar-ai {
  background: var(--gradient-tech) !important;
  color: white;
}

.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background-color: var(--bg-light);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-large);
  border-top-left-radius: var(--radius-small);
}

.thinking-text {
  font-size: 14px;
  color: var(--text-secondary);
}

.thinking-dots {
  display: flex;
  gap: 4px;
}

.thinking-dots .dot {
  width: 6px;
  height: 6px;
  background-color: var(--primary-color);
  border-radius: 50%;
  animation: thinking-bounce 1.4s infinite ease-in-out both;
}

.thinking-dots .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.thinking-dots .dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes thinking-bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

/* ==================== 输入区域 ==================== */

.input-section {
  padding: 16px 24px 24px;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

/* ==================== 移动端遮罩 ==================== */

.sidebar-overlay {
  display: none;
}

/* ==================== 响应式适配 ==================== */

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: -240px;
    top: 0;
    height: 100vh;
    transition: left var(--transition-base);
  }

  .sidebar-collapsed {
    width: 240px;
    left: -240px;
  }

  /* 移动端菜单打开时 */
  .chat-view:has(.sidebar-overlay) .sidebar {
    left: 0;
  }

  .sidebar-overlay {
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 99;
    backdrop-filter: blur(4px);
  }

  .mobile-header {
    display: flex;
  }

  .message-area {
    padding: 16px;
  }

  .input-section {
    padding: 12px 16px 16px;
  }

  .feature-cards {
    grid-template-columns: 1fr;
  }

  .footer-top {
    margin-bottom: 10px;
  }

  .welcome-section {
    padding: 20px 0;
  }

  .welcome-section h2 {
    font-size: 20px;
  }
}

/* 侧边栏在移动端打开时的样式 */
@media (max-width: 768px) {
  .chat-view.mobile-menu-open .sidebar {
    left: 0;
  }
}
</style>

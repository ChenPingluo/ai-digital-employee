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
      </nav>
      
      <!-- 侧边栏底部 -->
      <div class="sidebar-footer">
        <!-- 用户信息 -->
        <div class="user-info" v-show="!isSidebarCollapsed">
          <el-avatar :size="36" class="user-avatar">
            <el-icon><User /></el-icon>
          </el-avatar>
          <div class="user-detail">
            <span class="user-name">{{ userStore.displayName || '用户' }}</span>
            <span class="user-role">在线</span>
          </div>
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
          <div v-if="isLoading" class="thinking-indicator">
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
  User,
  SwitchButton,
  Menu,
  Fold,
  Expand,
  List,
  Calendar,
  Cloudy,
  Setting
} from '@element-plus/icons-vue'

// 导入组件
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'

// 导入 Store
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'

// ==================== 路由和状态 ====================

const router = useRouter()
const chatStore = useChatStore()
const userStore = useUserStore()

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
  
  // 发送消息
  await chatStore.sendMessage(content)
  
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

// ==================== 生命周期 ====================

onMounted(() => {
  // 初始化用户信息
  userStore.initializeAuth()
  
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
  background-color: #f5f7fa;
  overflow: hidden;
}

/* ==================== 侧边栏样式 ==================== */

.sidebar {
  width: 240px;
  background: white;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
  transition: width 0.3s ease;
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
  border-bottom: 1px solid #ebeef5;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.collapse-btn {
  padding: 8px;
}

/* 导航菜单 */
.sidebar-nav {
  flex: 1;
  padding: 16px 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  color: #606266;
  margin-bottom: 4px;
  transition: all 0.2s ease;
  text-decoration: none;
}

.nav-item:hover {
  background-color: #f5f7fa;
  color: #409EFF;
}

.nav-item.active {
  background-color: #ecf5ff;
  color: #409EFF;
  font-weight: 500;
}

.sidebar-collapsed .nav-item {
  justify-content: center;
  padding: 12px;
}

/* 侧边栏底部 */
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #ebeef5;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.user-avatar {
  background: linear-gradient(135deg, #409EFF 0%, #53a8ff 100%);
  color: white;
}

.user-detail {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.user-role {
  font-size: 12px;
  color: #67C23A;
}

.logout-btn {
  width: 100%;
  justify-content: flex-start;
  color: #909399;
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
}

/* 移动端头部 */
.mobile-header {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.mobile-header h1 {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

/* ==================== 消息区域 ==================== */

.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
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

.welcome-section h2 {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px 0;
}

.welcome-desc {
  font-size: 16px;
  color: #909399;
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
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.feature-content h3 {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 4px 0;
}

.feature-content p {
  font-size: 13px;
  color: #909399;
  margin: 0;
}

/* 快捷示例 */
.quick-examples {
  margin-top: 24px;
}

.quick-examples > p {
  font-size: 14px;
  color: #909399;
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
  transition: all 0.2s ease;
}

.example-tag:hover {
  background-color: #ecf5ff;
  color: #409EFF;
  border-color: #409EFF;
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
  background: linear-gradient(135deg, #409EFF 0%, #53a8ff 100%);
  color: white;
}

.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background-color: #f4f4f5;
  border-radius: 12px;
  border-top-left-radius: 4px;
}

.thinking-text {
  font-size: 14px;
  color: #909399;
}

.thinking-dots {
  display: flex;
  gap: 4px;
}

.thinking-dots .dot {
  width: 6px;
  height: 6px;
  background-color: #909399;
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
    transition: left 0.3s ease;
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
    background: rgba(0, 0, 0, 0.5);
    z-index: 99;
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

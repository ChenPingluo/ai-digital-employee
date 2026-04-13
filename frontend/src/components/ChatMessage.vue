<!--
  消息气泡组件 ChatMessage.vue
  
  用于展示单条聊天消息，支持：
  - 用户消息和 AI 回复的不同样式
  - 头像显示
  - 时间戳格式化
  - 简单的 Markdown 渲染
-->

<template>
  <!-- 消息容器，根据角色添加不同的类名 -->
  <div 
    class="chat-message"
    :class="{
      'user-message': message.role === 'user',
      'assistant-message': message.role === 'assistant',
      'error-message': message.isError,
      'streaming': message.isStreaming
    }"
  >
    <!-- 头像区域 -->
    <div class="message-avatar">
      <!-- AI 头像 -->
      <el-avatar 
        v-if="message.role === 'assistant'" 
        :size="36" 
        class="avatar-ai"
      >
        <el-icon :size="20"><Monitor /></el-icon>
      </el-avatar>
      <!-- 用户头像 -->
      <el-avatar 
        v-else 
        :size="36" 
        class="avatar-user"
      >
        <el-icon :size="20"><User /></el-icon>
      </el-avatar>
    </div>
    
    <!-- 消息内容区域 -->
    <div class="message-body">
      <!-- 消息气泡 -->
      <div class="message-bubble">
        <!-- 渲染消息内容（支持简单 Markdown） -->
        <div 
          class="message-content"
          v-html="renderContent(message.content)"
        ></div>
        
        <!-- 流式加载指示器 -->
        <span v-if="message.isStreaming" class="typing-indicator">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </span>
      </div>
      
      <!-- 时间戳 -->
      <div class="message-time">
        {{ formatTime(message.timestamp) }}
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 消息气泡组件
 * 
 * 展示单条聊天消息，支持用户和 AI 两种角色的不同样式
 */

import { Monitor, User } from '@element-plus/icons-vue'

// ==================== Props 定义 ====================

/**
 * 组件属性
 * message: 消息对象，包含以下字段：
 *   - id: 消息唯一标识
 *   - role: 角色 ('user' | 'assistant')
 *   - content: 消息内容
 *   - timestamp: 时间戳 (ISO 格式字符串)
 *   - isError: 是否为错误消息（可选）
 *   - isStreaming: 是否正在流式生成（可选）
 */
defineProps({
  message: {
    type: Object,
    required: true,
    validator: (value) => {
      return value.role && value.content !== undefined
    }
  }
})

// ==================== 方法定义 ====================

/**
 * 格式化时间戳
 * 将 ISO 格式时间转换为更友好的显示格式
 * 
 * @param {string} timestamp - ISO 格式的时间字符串
 * @returns {string} 格式化后的时间字符串
 */
function formatTime(timestamp) {
  if (!timestamp) return ''
  
  const date = new Date(timestamp)
  const now = new Date()
  
  // 判断是否为今天
  const isToday = date.toDateString() === now.toDateString()
  
  // 格式化时间部分（时:分）
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const timeStr = `${hours}:${minutes}`
  
  if (isToday) {
    // 今天只显示时间
    return timeStr
  } else {
    // 其他日期显示月-日 时:分
    const month = (date.getMonth() + 1).toString().padStart(2, '0')
    const day = date.getDate().toString().padStart(2, '0')
    return `${month}-${day} ${timeStr}`
  }
}

/**
 * 渲染消息内容
 * 实现简单的 Markdown 解析：
 * - 将换行符转换为 <br>
 * - 将 `code` 转换为 <code> 标签
 * - 将 **bold** 转换为 <strong> 标签
 * - 转义 HTML 特殊字符防止 XSS
 * 
 * @param {string} content - 原始消息内容
 * @returns {string} 渲染后的 HTML 字符串
 */
function renderContent(content) {
  if (!content) return ''
  
  // 首先转义 HTML 特殊字符，防止 XSS 攻击
  let html = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
  
  // 处理代码块（```code```）
  html = html.replace(
    /```([\s\S]*?)```/g, 
    '<pre class="code-block"><code>$1</code></pre>'
  )
  
  // 处理行内代码（`code`）
  html = html.replace(
    /`([^`]+)`/g, 
    '<code class="inline-code">$1</code>'
  )
  
  // 处理粗体（**text**）
  html = html.replace(
    /\*\*([^*]+)\*\*/g, 
    '<strong>$1</strong>'
  )
  
  // 处理斜体（*text*）
  html = html.replace(
    /\*([^*]+)\*/g, 
    '<em>$1</em>'
  )
  
  // 将换行符转换为 <br>
  html = html.replace(/\n/g, '<br>')
  
  return html
}
</script>

<style scoped>
/* ==================== 消息容器 ==================== */

.chat-message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 0 16px;
}

/* 用户消息：头像和内容顺序反转，靠右对齐 */
.user-message {
  flex-direction: row-reverse;
}

/* ==================== 头像样式 ==================== */

.message-avatar {
  flex-shrink: 0;
}

/* AI 头像样式 */
.avatar-ai {
  background: linear-gradient(135deg, #409EFF 0%, #53a8ff 100%);
  color: white;
}

/* 用户头像样式 */
.avatar-user {
  background: linear-gradient(135deg, #67C23A 0%, #85ce61 100%);
  color: white;
}

/* ==================== 消息内容区域 ==================== */

.message-body {
  max-width: 70%;
  display: flex;
  flex-direction: column;
}

/* 用户消息内容右对齐 */
.user-message .message-body {
  align-items: flex-end;
}

/* AI 消息内容左对齐 */
.assistant-message .message-body {
  align-items: flex-start;
}

/* ==================== 消息气泡 ==================== */

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  word-wrap: break-word;
  word-break: break-word;
  line-height: 1.6;
}

/* AI 消息气泡样式 */
.assistant-message .message-bubble {
  background-color: #f4f4f5;
  color: #303133;
  border-top-left-radius: 4px;
}

/* 用户消息气泡样式 */
.user-message .message-bubble {
  background: linear-gradient(135deg, #409EFF 0%, #53a8ff 100%);
  color: white;
  border-top-right-radius: 4px;
}

/* 错误消息样式 */
.error-message .message-bubble {
  background-color: #fef0f0;
  color: #f56c6c;
}

/* ==================== 消息内容 ==================== */

.message-content {
  font-size: 14px;
}

/* 代码块样式 */
.message-content :deep(.code-block) {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  margin: 8px 0;
  overflow-x: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
}

/* 行内代码样式 */
.message-content :deep(.inline-code) {
  background-color: rgba(0, 0, 0, 0.06);
  color: #c7254e;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
}

/* 用户消息中的行内代码 */
.user-message .message-content :deep(.inline-code) {
  background-color: rgba(255, 255, 255, 0.2);
  color: white;
}

/* ==================== 时间戳 ==================== */

.message-time {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
  padding: 0 4px;
}

/* ==================== 流式加载动画 ==================== */

.typing-indicator {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
}

.typing-indicator .dot {
  width: 6px;
  height: 6px;
  background-color: #909399;
  border-radius: 50%;
  animation: typing-bounce 1.4s infinite ease-in-out both;
}

.typing-indicator .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator .dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typing-bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

/* ==================== 响应式适配 ==================== */

@media (max-width: 768px) {
  .message-body {
    max-width: 85%;
  }
  
  .chat-message {
    padding: 0 12px;
  }
  
  .message-bubble {
    padding: 10px 14px;
  }
}
</style>

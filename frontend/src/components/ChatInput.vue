<!--
  聊天输入框组件 ChatInput.vue
  
  提供消息输入功能：
  - textarea 多行输入
  - Shift+Enter 换行
  - Enter 发送消息
  - 发送按钮
  - 加载状态禁用
-->

<template>
  <div class="chat-input">
    <!-- 输入区域 -->
    <div class="input-wrapper">
      <!-- 文本输入框 -->
      <textarea
        ref="textareaRef"
        v-model="inputValue"
        class="input-textarea"
        :placeholder="placeholder"
        :disabled="disabled"
        :rows="rows"
        @keydown="handleKeydown"
        @input="handleInput"
      ></textarea>
    </div>
    
    <!-- 底部操作栏 -->
    <div class="input-actions">
      <!-- 提示文字 -->
      <div class="input-hint">
        <span>按 Enter 发送，Shift + Enter 换行</span>
      </div>
      
      <!-- 发送按钮 -->
      <el-button
        type="primary"
        :icon="Promotion"
        :disabled="!canSend"
        :loading="disabled"
        @click="handleSend"
      >
        {{ disabled ? '发送中...' : '发送' }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
/**
 * 聊天输入框组件
 * 
 * 提供消息输入和发送功能
 */

import { ref, computed, nextTick } from 'vue'
import { Promotion } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { validateInput } from '@/utils/security'

// ==================== Props 定义 ====================

const props = defineProps({
  /**
   * 占位符文本
   */
  placeholder: {
    type: String,
    default: '输入您的问题或指令...'
  },
  
  /**
   * 是否禁用（加载状态）
   */
  disabled: {
    type: Boolean,
    default: false
  },
  
  /**
   * 默认显示行数
   */
  rows: {
    type: Number,
    default: 2
  },
  
  /**
   * 最大字符数
   */
  maxLength: {
    type: Number,
    default: 2000
  }
})

// ==================== Emits 定义 ====================

const emit = defineEmits([
  /**
   * 发送消息事件
   * @param {string} content - 消息内容
   */
  'send'
])

// ==================== 响应式数据 ====================

/**
 * 输入框引用
 */
const textareaRef = ref(null)

/**
 * 输入框内容
 */
const inputValue = ref('')

/** 防抖定时器 */
let inputTimer = null

// ==================== 计算属性 ====================

/**
 * 是否可以发送
 * 条件：输入内容不为空 且 未禁用
 */
const canSend = computed(() => {
  return inputValue.value.trim().length > 0 && !props.disabled
})

// ==================== 方法定义 ====================

/**
 * 处理键盘事件
 * Enter 发送，Shift+Enter 换行
 * 
 * @param {KeyboardEvent} event - 键盘事件
 */
function handleKeydown(event) {
  // 检测是否按下 Enter 键
  if (event.key === 'Enter') {
    // Ctrl/Cmd+Enter 始终发送
    if (event.ctrlKey || event.metaKey) {
      event.preventDefault()
      handleSend()
      return
    }
    // 如果同时按下 Shift 键，允许换行
    if (event.shiftKey) {
      return // 默认行为：换行
    }

    // 单独按 Enter，阻止默认换行并发送消息
    event.preventDefault()
    handleSend()
  }
}

/**
 * 处理输入事件
 * 用于限制最大字符数
 * 
 * @param {Event} event - 输入事件
 */
function handleInput(event) {
  // 防抖：延迟检查最大长度，避免高频截断
  if (inputTimer) {
    clearTimeout(inputTimer)
  }
  inputTimer = setTimeout(() => {
    if (inputValue.value.length > props.maxLength) {
      inputValue.value = inputValue.value.slice(0, props.maxLength)
    }
    inputTimer = null
  }, 300)
}

/**
 * 发送消息
 */
async function handleSend() {
  // 检查是否可以发送
  if (!canSend.value) {
    return
  }

  // 获取原始输入
  const rawContent = inputValue.value.trim()

  // 安全验证
  const { sanitized, isClean, matches } = validateInput(rawContent)

  if (!isClean) {
    // 弹窗警告敏感内容
    const matchList = matches.map(m => `· ${m.label}：${m.text}`).join('<br/>')
    try {
      await ElMessageBox.confirm(
        `<div>您的输入包含以下敏感内容：<br/><br/>${matchList}<br/><br/>是否仍要发送？</div>`,
        '内容安全提醒',
        {
          confirmButtonText: '仍然发送',
          cancelButtonText: '返回修改',
          type: 'warning',
          dangerouslyUseHTMLString: true
        }
      )
    } catch {
      // 用户取消，保留输入内容
      return
    }
  }

  // 清空输入框
  inputValue.value = ''

  // 触发发送事件（使用清理后的内容）
  emit('send', sanitized)

  // 重新聚焦到输入框
  nextTick(() => {
    textareaRef.value?.focus()
  })
}

/**
 * 聚焦到输入框
 * 供父组件调用
 */
function focus() {
  textareaRef.value?.focus()
}

/**
 * 清空输入框
 * 供父组件调用
 */
function clear() {
  inputValue.value = ''
}

// ==================== 暴露方法给父组件 ====================

defineExpose({
  focus,
  clear
})
</script>

<style scoped>
/* ==================== 容器样式 ==================== */

.chat-input {
  display: flex;
  flex-direction: column;
  background: var(--bg-light);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-large);
  padding: 16px;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.chat-input:focus-within {
  border-color: var(--primary-color);
  box-shadow: var(--glow-primary);
}

/* ==================== 输入区域 ==================== */

.input-wrapper {
  position: relative;
  margin-bottom: 12px;
}

.input-textarea {
  width: 100%;
  min-height: 60px;
  max-height: 200px;
  padding: 12px 16px;
  border: none;
  border-radius: var(--radius-base);
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
  background: transparent;
  resize: none;
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s ease;
  box-sizing: border-box;
}

.input-textarea:focus {
  border-color: transparent;
  box-shadow: none;
}

.input-textarea:disabled {
  background-color: rgba(255, 255, 255, 0.03);
  cursor: not-allowed;
  color: var(--text-placeholder);
}

.input-textarea::placeholder {
  color: var(--text-placeholder);
}

/* ==================== 操作栏 ==================== */

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 提示文字 */
.input-hint {
  font-size: 12px;
  color: var(--text-secondary);
}

/* ==================== 发送按钮 ==================== */

.input-actions :deep(.el-button--primary) {
  background: transparent;
  border: 1px solid var(--primary-color);
  color: var(--primary-color);
  border-radius: var(--radius-round);
  transition: all 0.3s ease;
}

.input-actions :deep(.el-button--primary:hover) {
  background: rgba(0, 212, 255, 0.15);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.input-actions :deep(.el-button--primary:active) {
  background: rgba(0, 212, 255, 0.25);
}

.input-actions :deep(.el-button.is-disabled) {
  background: transparent;
  border-color: var(--border-base);
  color: var(--text-placeholder);
}

.input-actions :deep(.el-button--primary .el-icon) {
  color: inherit;
}

/* ==================== 响应式适配 ==================== */

@media (max-width: 768px) {
  .chat-input {
    padding: 12px;
  }
  
  .input-textarea {
    padding: 10px 12px;
    font-size: 16px; /* 防止 iOS 自动缩放 */
  }
  
  .input-hint {
    display: none; /* 移动端隐藏提示 */
  }
}
</style>

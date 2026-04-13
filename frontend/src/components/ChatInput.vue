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
  // 如果超过最大长度，截断
  if (inputValue.value.length > props.maxLength) {
    inputValue.value = inputValue.value.slice(0, props.maxLength)
  }
}

/**
 * 发送消息
 */
function handleSend() {
  // 检查是否可以发送
  if (!canSend.value) {
    return
  }
  
  // 获取并清理输入内容
  const content = inputValue.value.trim()
  
  // 清空输入框
  inputValue.value = ''
  
  // 触发发送事件
  emit('send', content)
  
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
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 16px;
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
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  resize: none;
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s ease;
}

.input-textarea:focus {
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

.input-textarea:disabled {
  background-color: #f5f7fa;
  cursor: not-allowed;
  color: #c0c4cc;
}

.input-textarea::placeholder {
  color: #c0c4cc;
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
  color: #909399;
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

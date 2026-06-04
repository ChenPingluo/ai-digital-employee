/**
 * 聊天状态管理 Store
 * 
 * 使用 Pinia 管理 AI 对话相关的状态：
 * - 消息列表管理
 * - 发送消息
 * - 加载状态
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  sendMessage as sendMessageApi,
  sendMessageStream as sendMessageStreamApi,
  getConversations as getConversationsApi,
  getConversationMessages as getConversationMessagesApi,
  createConversation as createConversationApi,
  deleteConversation as deleteConversationApi
} from '@/api/chat'
import { useStatisticsStore } from '@/stores/statistics'
import { ElMessage } from 'element-plus'

// ==================== 定义 Store ====================

/**
 * 聊天 Store
 * 
 * 使用 Composition API 风格定义
 * 提供消息管理和发送功能
 */
export const useChatStore = defineStore('chat', () => {
  // ==================== 状态定义 ====================
  
  /**
   * 消息列表
   * 每条消息包含：id, role, content, timestamp
   * role: 'user' 用户消息 | 'assistant' AI 回复
   */
  const messages = ref([])
  
  /**
   * 发送消息加载状态
   * 用于在等待 AI 响应时显示加载动画
   */
  const isLoading = ref(false)
  
  /**
   * 当前正在生成的消息内容（用于流式显示）
   */
  const streamingContent = ref('')
  
  /**
   * 当前会话 ID
   */
  const currentConversationId = ref(null)
  
  /**
   * 会话列表
   */
  const conversations = ref([])
  
  // ==================== 辅助函数 ====================
  
  /**
   * 生成唯一消息 ID
   * 使用时间戳和随机数组合
   */
  function generateMessageId() {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
  
  /**
   * 获取当前时间戳
   */
  function getCurrentTimestamp() {
    return new Date().toISOString()
  }

  /**
   * 聊天中的工具调用可能会变更待办/会议数据。
   * 异步刷新统计，避免用户切换到看板时看到旧的 Pinia 快照。
   */
  function refreshDashboardStats() {
    const statisticsStore = useStatisticsStore()
    statisticsStore.fetchAllStats().catch((error) => {
      console.error('刷新看板统计失败:', error)
    })
  }
  
  // ==================== 方法定义 ====================
  
  /**
   * 发送消息
   * 
   * @param {string} content - 用户消息内容
   * @returns {Promise<void>}
   */
  async function sendMessage(content) {
    // 验证消息内容
    if (!content || !content.trim()) {
      return
    }
    
    // 创建用户消息
    const userMessage = {
      id: generateMessageId(),
      role: 'user',
      content: content.trim(),
      timestamp: getCurrentTimestamp()
    }
    
    // 添加用户消息到列表
    messages.value.push(userMessage)
    
    // 设置加载状态
    isLoading.value = true
    streamingContent.value = ''
    
    try {
      // 调用 API 发送消息（传递当前会话 ID）
      const response = await sendMessageApi(content.trim(), currentConversationId.value)
      
      // 从响应中更新会话 ID
      if (response.conversation_id) {
        currentConversationId.value = response.conversation_id
      }
      
      // 创建 AI 回复消息
      const assistantMessage = {
        id: generateMessageId(),
        role: 'assistant',
        content: response.content || response.message || '收到您的消息',
        timestamp: getCurrentTimestamp()
      }
      
      // 添加 AI 回复到列表
      messages.value.push(assistantMessage)
      
      // 刷新会话列表（可能新建了会话或标题有变化）
      loadConversations()
      refreshDashboardStats()
      
    } catch (error) {
      console.error('发送消息失败:', error)
      
      // 添加错误消息
      const errorMessage = {
        id: generateMessageId(),
        role: 'assistant',
        content: '抱歉，发送消息时出现错误，请稍后重试。',
        timestamp: getCurrentTimestamp(),
        isError: true
      }
      
      messages.value.push(errorMessage)
      
      // 显示错误提示
      ElMessage.error('发送消息失败，请重试')
      
    } finally {
      // 重置加载状态
      isLoading.value = false
      streamingContent.value = ''
    }
  }
  
  /**
   * 发送消息（流式响应）
   * 
   * 使用 SSE 实现实时显示 AI 响应
   * 
   * @param {string} content - 用户消息内容
   * @returns {Promise<void>}
   */
  async function sendMessageWithStream(content) {
    // 验证消息内容
    if (!content || !content.trim()) {
      return
    }
    
    // 创建用户消息
    const userMessage = {
      id: generateMessageId(),
      role: 'user',
      content: content.trim(),
      timestamp: getCurrentTimestamp()
    }
    
    // 添加用户消息到列表
    messages.value.push(userMessage)
    
    // 设置加载状态
    isLoading.value = true
    streamingContent.value = ''
    
    // 创建占位的 AI 消息
    const assistantMessageId = generateMessageId()
    const assistantMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: getCurrentTimestamp(),
      isStreaming: true
    }
    
    messages.value.push(assistantMessage)
    let streamError = ''
    
    try {
      // 调用流式 API（传递当前会话 ID）
      await sendMessageStreamApi(content.trim(), (chunk) => {
        // 从响应中提取并更新 conversation_id
        if (chunk.conversation_id) {
          currentConversationId.value = chunk.conversation_id
        }

        if (chunk.error) {
          streamError = chunk.error
          const msgIndex = messages.value.findIndex(m => m.id === assistantMessageId)
          if (msgIndex !== -1) {
            messages.value[msgIndex].content = chunk.error
            messages.value[msgIndex].isError = true
            messages.value[msgIndex].isStreaming = false
          }
          return
        }
        
        // 更新流式内容
        const text = chunk.content || chunk.text || ''
        streamingContent.value += text
        
        // 更新消息内容
        const msgIndex = messages.value.findIndex(m => m.id === assistantMessageId)
        if (msgIndex !== -1) {
          messages.value[msgIndex].content = streamingContent.value
        }
      }, currentConversationId.value)
      
      // 流式传输完成，移除标记
      const msgIndex = messages.value.findIndex(m => m.id === assistantMessageId)
      if (msgIndex !== -1) {
        messages.value[msgIndex].isStreaming = false
      }
      
      // 刷新会话列表（可能新建了会话或标题有变化）
      await loadConversations()
      refreshDashboardStats()

      if (streamError) {
        ElMessage.error(streamError)
      }
      
    } catch (error) {
      console.error('发送消息失败:', error)
      
      // 更新消息为错误状态
      const msgIndex = messages.value.findIndex(m => m.id === assistantMessageId)
      if (msgIndex !== -1) {
        messages.value[msgIndex].content = '抱歉，发送消息时出现错误，请稍后重试。'
        messages.value[msgIndex].isError = true
        messages.value[msgIndex].isStreaming = false
      }
      
      ElMessage.error('发送消息失败，请重试')
      
    } finally {
      isLoading.value = false
      streamingContent.value = ''
    }
  }
  
  /**
   * 清空消息列表
   */
  function clearMessages() {
    messages.value = []
    streamingContent.value = ''
    currentConversationId.value = null
  }
  
  /**
   * 添加系统消息
   * 
   * @param {string} content - 消息内容
   */
  function addSystemMessage(content) {
    const message = {
      id: generateMessageId(),
      role: 'system',
      content,
      timestamp: getCurrentTimestamp()
    }
    messages.value.push(message)
  }
  
  // ==================== 会话管理方法 ====================
  
  /**
   * 加载会话列表
   */
  async function loadConversations() {
    try {
      const res = await getConversationsApi()
      conversations.value = res
    } catch (error) {
      console.error('加载会话列表失败:', error)
    }
  }
  
  /**
   * 切换会话
   * @param {string} conversationId - 目标会话 ID
   */
  async function switchConversation(conversationId) {
    currentConversationId.value = conversationId
    try {
      const res = await getConversationMessagesApi(conversationId)
      // 将后端返回的消息转换为前端消息格式
      messages.value = res.map(msg => ({
        id: msg.id || generateMessageId(),
        role: msg.role,
        content: msg.content,
        timestamp: msg.created_at
      }))
    } catch (error) {
      console.error('加载会话消息失败:', error)
    }
  }
  
  /**
   * 新建话题（清空当前会话）
   */
  function createNewConversation() {
    currentConversationId.value = null
    messages.value = []
    streamingContent.value = ''
  }
  
  /**
   * 删除会话
   * @param {string} conversationId - 要删除的会话 ID
   */
  async function deleteConversation(conversationId) {
    try {
      await deleteConversationApi(conversationId)
      // 如果删除的是当前会话，清空消息
      if (currentConversationId.value === conversationId) {
        currentConversationId.value = null
        messages.value = []
      }
      // 刷新会话列表
      await loadConversations()
    } catch (error) {
      console.error('删除会话失败:', error)
    }
  }
  
  // ==================== 返回暴露的内容 ====================
  
  return {
    // 状态
    messages,
    isLoading,
    streamingContent,
    currentConversationId,
    conversations,
    
    // 方法
    sendMessage,
    sendMessageWithStream,
    clearMessages,
    addSystemMessage,
    loadConversations,
    switchConversation,
    createNewConversation,
    deleteConversation
  }
})

// ==================== 导出 ====================

export default useChatStore

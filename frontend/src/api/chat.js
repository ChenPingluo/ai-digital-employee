/**
 * 对话 API 接口
 * 
 * 提供 AI 对话相关的 API 调用：
 * - 发送消息（普通模式）
 * - 发送消息（流式响应模式，使用 SSE）
 */

import request from './request'

// ==================== 发送消息（普通模式） ====================

/**
 * 发送消息到 AI 助手
 * 
 * @param {string} message - 用户发送的消息内容
 * @returns {Promise<Object>} 返回 AI 的响应
 * 
 * @example
 * const response = await sendMessage('帮我创建一个待办事项')
 * // response: { content: '好的，我已经为您创建了待办事项...', ... }
 */
export function sendMessage(message, conversationId = null) {
  return request({
    url: '/chat/',
    method: 'POST',
    data: {
      message: message,
      conversation_id: conversationId
    }
  })
}

// ==================== 会话管理 ====================

/**
 * 获取用户的所有会话
 * @returns {Promise<Array>} 会话列表
 */
export function getConversations() {
  return request({
    url: '/chat/conversations',
    method: 'GET'
  })
}

/**
 * 获取会话的消息历史
 * @param {string} conversationId - 会话 ID
 * @returns {Promise<Array>} 消息列表
 */
export function getConversationMessages(conversationId) {
  return request({
    url: `/chat/conversations/${conversationId}/messages`,
    method: 'GET'
  })
}

/**
 * 创建新会话
 * @param {string|null} title - 会话标题
 * @returns {Promise<Object>} 新建的会话
 */
export function createConversation(title = null) {
  return request({
    url: '/chat/conversations',
    method: 'POST',
    data: { title }
  })
}

/**
 * 删除会话
 * @param {string} conversationId - 会话 ID
 * @returns {Promise<Object>} 删除结果
 */
export function deleteConversation(conversationId) {
  return request({
    url: `/chat/conversations/${conversationId}`,
    method: 'DELETE'
  })
}

// ==================== 发送消息（流式响应模式） ====================

/**
 * 发送消息并使用 SSE 流式接收响应
 * 
 * 使用原生 fetch API 实现服务器发送事件（SSE）的流式接收，
 * 适用于需要实时显示 AI 响应的场景。
 * 
 * @param {string} message - 用户发送的消息内容
 * @param {Function} onChunk - 接收每个数据块的回调函数
 * @returns {Promise<void>} 完成时 resolve
 * 
 * @example
 * await sendMessageStream('给我讲个故事', (chunk) => {
 *   console.log('收到数据块:', chunk)
 *   // 实时更新 UI 显示
 * })
 */
export async function sendMessageStream(message, onChunk, conversationId = null) {
  // 从 localStorage 获取认证令牌
  const token = localStorage.getItem('access_token')
  
  // 使用 fetch API 发送请求
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // 如果有 token，添加认证头
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify({ 
      message,
      conversation_id: conversationId 
    })
  })
  
  // 检查响应状态
  if (!response.ok) {
    // 根据状态码处理错误
    if (response.status === 401) {
      // 未授权，清除 token 并抛出错误
      localStorage.removeItem('access_token')
      throw new Error('登录已过期，请重新登录')
    }
    throw new Error(`请求失败: ${response.status}`)
  }
  
  // 获取响应体的 reader，用于流式读取
  const reader = response.body.getReader()
  
  // 创建文本解码器，将字节流转换为文本
  const decoder = new TextDecoder('utf-8')
  
  // 用于存储不完整的数据行
  let buffer = ''
  
  try {
    // 循环读取数据流
    while (true) {
      // 读取下一个数据块
      const { done, value } = await reader.read()
      
      // 如果读取完成，退出循环
      if (done) {
        break
      }
      
      // 将字节数据解码为文本
      const text = decoder.decode(value, { stream: true })
      
      // 将新数据添加到缓冲区
      buffer += text
      
      // 按行分割数据（SSE 格式每条消息以换行符分隔）
      const lines = buffer.split('\n')
      
      // 保留最后一个可能不完整的行
      buffer = lines.pop() || ''
      
      // 处理每一行数据
      for (const line of lines) {
        // 跳过空行
        if (!line.trim()) continue
        
        // SSE 格式：以 "data: " 开头
        if (line.startsWith('data: ')) {
          // 提取实际数据内容
          const data = line.slice(6)
          
          // 检查是否为结束标记
          if (data === '[DONE]') {
            return
          }
          
          try {
            // 尝试解析 JSON 数据
            const parsed = JSON.parse(data)
            // 调用回调函数处理数据块
            onChunk(parsed)
          } catch (e) {
            // 如果不是 JSON，直接传递文本
            onChunk({ content: data })
          }
        }
      }
    }
    
    // 处理缓冲区中剩余的数据
    if (buffer.trim()) {
      if (buffer.startsWith('data: ')) {
        const data = buffer.slice(6)
        if (data !== '[DONE]') {
          try {
            const parsed = JSON.parse(data)
            onChunk(parsed)
          } catch (e) {
            onChunk({ content: data })
          }
        }
      }
    }
  } finally {
    // 确保释放 reader
    reader.releaseLock()
  }
}

// ==================== 导出所有接口 ====================

export default {
  sendMessage,
  sendMessageStream,
  getConversations,
  getConversationMessages,
  createConversation,
  deleteConversation
}

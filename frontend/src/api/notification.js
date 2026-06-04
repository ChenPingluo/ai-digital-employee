/**
 * 提醒推送 API 接口
 *
 * 提供提醒列表查询和 SSE 推送连接能力。
 */

import request from './request'

export function getPendingReminders() {
  return request({
    url: '/notifications/pending',
    method: 'GET'
  })
}

export async function streamReminderNotifications({ onOpen, onEvent, signal } = {}) {
  const token = localStorage.getItem('access_token')

  const response = await fetch('/api/v1/notifications/stream', {
    method: 'GET',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    signal
  })

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')
      throw new Error('登录已过期，请重新登录')
    }

    throw new Error(`提醒流连接失败: ${response.status}`)
  }

  if (!response.body) {
    throw new Error('当前浏览器不支持提醒流')
  }

  onOpen?.()

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const rawLine of lines) {
        const line = rawLine.trimEnd()

        if (!line || line.startsWith(':')) {
          continue
        }

        if (!line.startsWith('data: ')) {
          continue
        }

        const payload = line.slice(6)
        if (!payload) {
          continue
        }

        try {
          onEvent?.(JSON.parse(payload))
        } catch (error) {
          onEvent?.({ type: 'message', data: payload })
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export default {
  getPendingReminders,
  streamReminderNotifications
}

/**
 * 提醒推送状态管理 Store
 *
 * 负责建立提醒 SSE 连接、去重提醒事件和展示全局通知。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'

import router from '@/router'
import { streamReminderNotifications } from '@/api/notification'
import { useUserStore } from '@/stores/user'

const SHOWN_REMINDER_CACHE_KEY = 'shown_reminder_ids'
const SHOWN_REMINDER_TTL_MS = 24 * 60 * 60 * 1000
const RECONNECT_DELAY_MS = 5000

function loadShownReminderMap() {
  try {
    const cached = localStorage.getItem(SHOWN_REMINDER_CACHE_KEY)
    return cached ? JSON.parse(cached) : {}
  } catch (error) {
    console.error('解析提醒缓存失败:', error)
    return {}
  }
}

function saveShownReminderMap(reminderMap) {
  localStorage.setItem(
    SHOWN_REMINDER_CACHE_KEY,
    JSON.stringify(reminderMap)
  )
}

function pruneShownReminderMap(reminderMap) {
  const now = Date.now()
  const entries = Object.entries(reminderMap).filter(([, timestamp]) => {
    return now - Number(timestamp) < SHOWN_REMINDER_TTL_MS
  })

  return Object.fromEntries(entries)
}

function mapNotificationType(severity) {
  if (severity === 'error') {
    return 'error'
  }

  if (severity === 'warning') {
    return 'warning'
  }

  return 'info'
}

export const useNotificationStore = defineStore('notification', () => {
  const connected = ref(false)
  const connecting = ref(false)
  const lastEventAt = ref(null)

  let reconnectTimer = null
  let streamAbortController = null

  function clearReconnectTimer() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function hasShownReminder(reminderId) {
    const reminderMap = pruneShownReminderMap(loadShownReminderMap())
    saveShownReminderMap(reminderMap)
    return Boolean(reminderMap[reminderId])
  }

  function markReminderAsShown(reminderId) {
    const reminderMap = pruneShownReminderMap(loadShownReminderMap())
    reminderMap[reminderId] = Date.now()
    saveShownReminderMap(reminderMap)
  }

  function showReminder(item) {
    if (!item?.reminder_id || hasShownReminder(item.reminder_id)) {
      return
    }

    ElNotification({
      title: item.title,
      message: item.message,
      type: mapNotificationType(item.severity),
      duration: 12000,
      position: 'top-right'
    })

    if (
      document.hidden &&
      'Notification' in window &&
      Notification.permission === 'granted'
    ) {
      new Notification(item.title, {
        body: item.message
      })
    }

    markReminderAsShown(item.reminder_id)
    lastEventAt.value = new Date()
  }

  function scheduleReconnect() {
    if (reconnectTimer || !localStorage.getItem('access_token')) {
      return
    }

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, RECONNECT_DELAY_MS)
  }

  async function connect() {
    if (connected.value || connecting.value || streamAbortController) {
      return
    }

    if (!localStorage.getItem('access_token')) {
      return
    }

    clearReconnectTimer()

    const abortController = new AbortController()
    streamAbortController = abortController
    connecting.value = true

    let shouldReconnect = true

    try {
      await streamReminderNotifications({
        signal: abortController.signal,
        onOpen: () => {
          connected.value = true
          connecting.value = false
        },
        onEvent: (event) => {
          if (event?.type === 'reminder' && event.item) {
            showReminder(event.item)
          }
        }
      })
    } catch (error) {
      if (abortController.signal.aborted) {
        shouldReconnect = false
        return
      }

      if (error?.message === '登录已过期，请重新登录') {
        shouldReconnect = false
        const userStore = useUserStore()
        ElMessage.error(error.message)
        userStore.handleAuthExpired()
        return
      }

      console.error('提醒流连接失败:', error)
    } finally {
      if (streamAbortController === abortController) {
        streamAbortController = null
      }

      connected.value = false
      connecting.value = false

      if (shouldReconnect) {
        scheduleReconnect()
      }
    }
  }

  function disconnect() {
    clearReconnectTimer()

    if (streamAbortController) {
      streamAbortController.abort()
      streamAbortController = null
    }

    connected.value = false
    connecting.value = false
  }

  function openReminderCenter() {
    router.push({ name: 'Dashboard' })
  }

  return {
    connected,
    connecting,
    lastEventAt,
    connect,
    disconnect,
    openReminderCenter
  }
})

export default useNotificationStore

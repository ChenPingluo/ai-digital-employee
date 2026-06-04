/**
 * 统计状态管理 Store
 * 
 * 使用 Pinia 管理统计数据：
 * - 待办事项统计
 * - 会议室使用统计
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getTodoStats, getMeetingStats } from '@/api/statistics'

// ==================== 定义 Store ====================

/**
 * 统计 Store
 * 
 * 使用 Composition API 风格定义
 * 提供统计数据的获取和管理
 */
export const useStatisticsStore = defineStore('statistics', () => {
  // ==================== 状态定义 ====================
  
  /**
   * 待办事项统计数据
   * {
   *   pending: number,      // 待处理数量
   *   in_progress: number,  // 进行中数量
   *   completed: number,    // 已完成数量
   *   cancelled: number,    // 已取消数量
   *   total: number         // 总数
   * }
   */
  const todoStats = ref({
    pending: 0,
    in_progress: 0,
    completed: 0,
    cancelled: 0,
    total: 0
  })
  
  /**
   * 会议室使用统计数据
   * Array<{
   *   room_id: number,
   *   room_name: string,
   *   reservation_count: number,  // 预约次数
   *   total_hours: number         // 总使用时长
   * }>
   */
  const meetingStats = ref([])
  
  /**
   * 数据加载状态
   */
  const loading = ref(false)
  
  /**
   * 最后更新时间
   */
  const lastUpdated = ref(null)

  function normalizeMeetingRoomStat(room) {
    const totalHours = Number(
      room?.total_hours ?? room?.total_duration_hours ?? 0
    )

    return {
      ...room,
      total_hours: totalHours,
      total_duration_hours: totalHours
    }
  }
  
  // ==================== 计算属性 ====================
  
  /**
   * 待办总数
   */
  const totalTodos = computed(() => todoStats.value.total || 0)
  
  /**
   * 进行中的任务数
   */
  const activeTodos = computed(() => 
    (todoStats.value.pending || 0) + (todoStats.value.in_progress || 0)
  )
  
  /**
   * 会议室总预约次数
   */
  const totalReservations = computed(() => 
    meetingStats.value.reduce((sum, room) => sum + (room.reservation_count || 0), 0)
  )
  
  /**
   * 会议室总使用时长
   */
  const totalMeetingHours = computed(() =>
    meetingStats.value.reduce(
      (sum, room) => sum + (room.total_hours || room.total_duration_hours || 0),
      0
    )
  )
  
  // ==================== 方法定义 ====================
  
  /**
   * 获取待办事项统计数据
   * 
   * @returns {Promise<Object>} 返回统计数据
   */
  async function fetchTodoStats(options = {}) {
    const { updateLoading = true } = options
    try {
      if (updateLoading) {
        loading.value = true
      }
      const resp = await getTodoStats()
      // 后端返回 { status, data: { pending, in_progress, completed, cancelled, total } }
      const stats = resp.data || {}
      todoStats.value = {
        pending: stats.pending || 0,
        in_progress: stats.in_progress || 0,
        completed: stats.completed || 0,
        cancelled: stats.cancelled || 0,
        total: stats.total || 0
      }
      return todoStats.value
    } catch (error) {
      console.error('获取待办统计失败:', error)
      // 返回当前状态，不抛出错误
      return todoStats.value
    } finally {
      if (updateLoading) {
        loading.value = false
      }
    }
  }
  
  /**
   * 获取会议室使用统计数据
   * 
   * @returns {Promise<Array>} 返回统计数据数组
   */
  async function fetchMeetingStats(options = {}) {
    const { updateLoading = true } = options
    try {
      if (updateLoading) {
        loading.value = true
      }
      const resp = await getMeetingStats()
      // 后端返回 { status, data: { rooms: [...], total_reservations, total_duration_hours } }
      const stats = resp.data || {}
      meetingStats.value = (stats.rooms || []).map(normalizeMeetingRoomStat)
      return meetingStats.value
    } catch (error) {
      console.error('获取会议室统计失败:', error)
      // 返回当前状态，不抛出错误
      return meetingStats.value
    } finally {
      if (updateLoading) {
        loading.value = false
      }
    }
  }
  
  /**
   * 获取所有统计数据
   * 
   * 同时获取待办和会议室统计
   */
  async function fetchAllStats() {
    loading.value = true
    
    try {
      // 并行获取所有统计数据
      await Promise.all([
        fetchTodoStats({ updateLoading: false }),
        fetchMeetingStats({ updateLoading: false })
      ])
      
      // 更新最后获取时间
      lastUpdated.value = new Date()
      
    } catch (error) {
      console.error('获取统计数据失败:', error)
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 重置统计数据
   */
  function resetStats() {
    todoStats.value = {
      pending: 0,
      in_progress: 0,
      completed: 0,
      cancelled: 0,
      total: 0
    }
    meetingStats.value = []
    lastUpdated.value = null
  }
  
  // ==================== 返回暴露的内容 ====================
  
  return {
    // 状态
    todoStats,
    meetingStats,
    loading,
    lastUpdated,
    
    // 计算属性
    totalTodos,
    activeTodos,
    totalReservations,
    totalMeetingHours,
    
    // 方法
    fetchTodoStats,
    fetchMeetingStats,
    fetchAllStats,
    resetStats
  }
})

// ==================== 导出 ====================

export default useStatisticsStore

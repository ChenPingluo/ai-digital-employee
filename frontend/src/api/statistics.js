/**
 * 统计 API 接口
 * 
 * 提供数据统计相关的 API 调用：
 * - 获取待办事项统计
 * - 获取会议室使用统计
 */

import request from './request'

// ==================== 待办统计接口 ====================

/**
 * 获取待办事项统计数据
 * 
 * 返回各状态的待办数量统计，用于仪表盘展示
 * 
 * @returns {Promise<Object>} 返回待办统计数据
 * 
 * @example
 * const stats = await getTodoStats()
 * // stats: {
 * //   pending: 5,        // 待处理
 * //   in_progress: 3,    // 进行中
 * //   completed: 10,     // 已完成
 * //   cancelled: 2,      // 已取消
 * //   total: 20          // 总计
 * // }
 */
export function getTodoStats() {
  return request({
    url: '/statistics/todo-stats',
    method: 'GET'
  })
}

// ==================== 会议室统计接口 ====================

/**
 * 获取会议室使用统计数据
 * 
 * 返回各会议室的使用情况统计，用于仪表盘图表展示
 * 
 * @returns {Promise<Array>} 返回会议室统计数组
 * 
 * @example
 * const stats = await getMeetingStats()
 * // stats: [
 * //   {
 * //     room_id: 1,
 * //     room_name: '会议室A',
 * //     reservation_count: 15,    // 预约次数
 * //     total_hours: 22.5         // 总使用时长（小时）
 * //   },
 * //   {
 * //     room_id: 2,
 * //     room_name: '会议室B',
 * //     reservation_count: 8,
 * //     total_hours: 12
 * //   }
 * // ]
 */
export function getMeetingStats() {
  return request({
    url: '/statistics/meeting-stats',
    method: 'GET'
  })
}

// ==================== 导出所有接口 ====================

export default {
  getTodoStats,
  getMeetingStats
}

/**
 * 会议室 API 接口
 * 
 * 提供会议室管理相关的 API 调用：
 * - 获取会议室列表
 * - 获取预约列表
 * - 创建预约
 * - 取消预约
 */

import request from './request'

// ==================== 获取会议室列表 ====================

/**
 * 获取所有会议室列表
 * 
 * @returns {Promise<Array>} 返回会议室数组
 * 
 * @example
 * const rooms = await getMeetingRooms()
 * // rooms: [
 * //   { id: 1, name: '会议室A', capacity: 10, equipment: '投影仪, 白板' },
 * //   { id: 2, name: '会议室B', capacity: 6, equipment: '电视, 视频会议' }
 * // ]
 */
export function getMeetingRooms() {
  return request({
    url: '/meetings/rooms',
    method: 'GET'
  })
}

// ==================== 获取预约列表 ====================

/**
 * 获取会议室预约列表
 * 
 * 可选择性地传入筛选参数来过滤预约记录
 * 
 * @param {Object} [params] - 可选的筛选参数
 * @param {string} [params.date] - 按日期筛选，格式：YYYY-MM-DD
 * @param {number} [params.room_id] - 按会议室 ID 筛选
 * @returns {Promise<Array>} 返回预约记录数组
 * 
 * @example
 * // 获取所有预约
 * const allReservations = await getReservations()
 * 
 * // 获取特定日期的预约
 * const todayReservations = await getReservations({ date: '2024-03-25' })
 * 
 * // 获取特定会议室的预约
 * const roomReservations = await getReservations({ room_id: 1 })
 */
export function getReservations(params) {
  return request({
    url: '/meetings/reservations',
    method: 'GET',
    params
  })
}

// ==================== 创建预约 ====================

/**
 * 创建会议室预约
 * 
 * @param {Object} data - 预约信息
 * @param {number} data.room_id - 会议室 ID
 * @param {string} data.title - 会议主题
 * @param {string} data.start_time - 开始时间，ISO 格式
 * @param {string} data.end_time - 结束时间，ISO 格式
 * @param {string} [data.description] - 会议描述（可选）
 * @param {Array<number>} [data.attendees] - 参会人员 ID 列表（可选）
 * @returns {Promise<Object>} 返回创建的预约记录
 * 
 * @example
 * const reservation = await createReservation({
 *   room_id: 1,
 *   title: '项目周会',
 *   start_time: '2024-03-25T14:00:00',
 *   end_time: '2024-03-25T15:00:00',
 *   description: '讨论本周进度和下周计划'
 * })
 */
export function createReservation(data) {
  return request({
    url: '/meetings/reservations',
    method: 'POST',
    data
  })
}

// ==================== 取消预约 ====================

/**
 * 取消会议室预约
 * 
 * @param {number|string} id - 预约记录 ID
 * @returns {Promise<void>} 取消成功时 resolve
 * 
 * @example
 * await cancelReservation(1)
 * console.log('预约已取消')
 */
export function cancelReservation(id) {
  return request({
    url: `/meetings/reservations/${id}`,
    method: 'DELETE'
  })
}

// ==================== 导出所有接口 ====================

export default {
  getMeetingRooms,
  getReservations,
  createReservation,
  cancelReservation
}

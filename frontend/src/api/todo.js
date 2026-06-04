/**
 * 待办事项 API 接口
 * 
 * 提供待办事项的 CRUD 操作：
 * - 获取待办列表
 * - 创建待办
 * - 更新待办
 * - 删除待办
 */

import request from './request'

// ==================== 获取待办列表 ====================

/**
 * 获取待办事项列表
 * 
 * @param {string|Object} [options] - 筛选条件或状态值（可选）
 *   - 'pending': 待处理
 *   - 'in_progress': 进行中
 *   - 'completed': 已完成
 *   - 'cancelled': 已取消
 *   - 不传则获取所有状态
 * @returns {Promise<Array>} 返回待办事项数组
 * 
 * @example
 * // 获取所有待办
 * const allTodos = await getTodos()
 * 
 * // 获取进行中的待办
 * const inProgressTodos = await getTodos('in_progress')
 *
 * // 获取指定分页的待办
 * const firstPageTodos = await getTodos({ status: 'pending', page_size: 5 })
 */
export function getTodos(options) {
  const params = typeof options === 'string'
    ? { status: options }
    : { ...(options || {}) }

  return request({
    url: '/todos',
    method: 'GET',
    params
  })
}

// ==================== 创建待办 ====================

/**
 * 创建新的待办事项
 * 
 * @param {Object} data - 待办事项数据
 * @param {string} data.title - 待办标题
 * @param {string} [data.description] - 待办描述（可选）
 * @param {string} [data.due_date] - 截止日期，ISO 格式（可选）
 * @param {string} [data.priority] - 优先级：low/medium/high（可选）
 * @returns {Promise<Object>} 返回创建的待办事项
 * 
 * @example
 * const todo = await createTodo({
 *   title: '完成项目文档',
 *   description: '编写项目的技术文档',
 *   due_date: '2024-03-30T18:00:00',
 *   priority: 'high'
 * })
 */
export function createTodo(data) {
  return request({
    url: '/todos',
    method: 'POST',
    data
  })
}

// ==================== 更新待办 ====================

/**
 * 更新待办事项
 * 
 * @param {number|string} id - 待办事项 ID
 * @param {Object} data - 要更新的字段
 * @param {string} [data.title] - 待办标题
 * @param {string} [data.description] - 待办描述
 * @param {string} [data.status] - 状态
 * @param {string} [data.due_date] - 截止日期
 * @param {string} [data.priority] - 优先级
 * @returns {Promise<Object>} 返回更新后的待办事项
 * 
 * @example
 * // 标记待办为已完成
 * const todo = await updateTodo(1, { status: 'completed' })
 * 
 * // 更新待办标题和描述
 * const todo = await updateTodo(1, {
 *   title: '新标题',
 *   description: '新描述'
 * })
 */
export function updateTodo(id, data) {
  return request({
    url: `/todos/${id}`,
    method: 'PUT',
    data
  })
}

// ==================== 删除待办 ====================

/**
 * 删除待办事项
 * 
 * @param {number|string} id - 待办事项 ID
 * @returns {Promise<void>} 删除成功时 resolve
 * 
 * @example
 * await deleteTodo(1)
 * console.log('待办已删除')
 */
export function deleteTodo(id) {
  return request({
    url: `/todos/${id}`,
    method: 'DELETE'
  })
}

// ==================== 导出所有接口 ====================

export default {
  getTodos,
  createTodo,
  updateTodo,
  deleteTodo
}

/**
 * 记忆管理 API 接口
 *
 * 对应后端 /api/v1/memory/* 端点：
 * - 获取用户长期记忆列表（可按类型/分类筛选）
 * - 关键词搜索记忆
 * - 记忆统计
 * - 删除记忆（软删除）
 */

import request from './request'

/**
 * 获取用户记忆列表
 * @param {Object} params - 查询参数
 * @param {string} [params.memory_type] - fact/preference/event/person/context
 * @param {string} [params.category] - work/tech/health/life/learning
 * @param {number} [params.limit=50] - 返回数量上限
 * @returns {Promise<Array>} 记忆列表
 */
export function getMemories(params = {}) {
  return request({
    url: '/memory/memories',
    method: 'GET',
    params
  })
}

/**
 * 搜索记忆
 * @param {string} q - 搜索关键词
 * @param {number} [limit=10] - 返回数量上限
 * @returns {Promise<Array>} 匹配的记忆列表
 */
export function searchMemories(q, limit = 10) {
  return request({
    url: '/memory/memories/search',
    method: 'GET',
    params: { q, limit }
  })
}

/**
 * 获取记忆统计
 * @returns {Promise<Object>} { total, by_type, avg_importance, max_capacity, usage_percent }
 */
export function getMemoryStats() {
  return request({
    url: '/memory/memories/stats',
    method: 'GET'
  })
}

/**
 * 删除记忆（软删除）
 * @param {string} memoryId - 记忆 ID
 * @returns {Promise<Object>} { success: true }
 */
export function deleteMemory(memoryId) {
  return request({
    url: `/memory/memories/${memoryId}`,
    method: 'DELETE'
  })
}

export default {
  getMemories,
  searchMemories,
  getMemoryStats,
  deleteMemory
}

/**
 * 认证 API 接口
 * 
 * 提供用户认证相关的 API 调用：
 * - 用户登录
 * - 用户注册
 * - 获取当前用户信息
 */

import request from './request'

// ==================== 登录接口 ====================

/**
 * 用户登录
 * 
 * @param {string} username - 用户名
 * @param {string} password - 密码
 * @returns {Promise<Object>} 返回包含 access_token 的响应数据
 * 
 * @example
 * const result = await login('admin', 'password123')
 * // result: { access_token: 'xxx', token_type: 'bearer' }
 */
export function login(username, password) {
  // 使用 JSON 格式发送登录请求（与后端 Pydantic 模型匹配）
  return request({
    url: '/auth/login',
    method: 'POST',
    data: {
      username,
      password
    }
  })
}

// ==================== 注册接口 ====================

/**
 * 用户注册
 * 
 * @param {Object} data - 注册信息
 * @param {string} data.username - 用户名
 * @param {string} data.email - 邮箱地址
 * @param {string} data.password - 密码
 * @param {string} [data.full_name] - 用户全名（可选）
 * @returns {Promise<Object>} 返回创建的用户信息
 * 
 * @example
 * const user = await register({
 *   username: 'newuser',
 *   email: 'user@example.com',
 *   password: 'password123',
 *   full_name: '张三'
 * })
 */
export function register(data) {
  return request({
    url: '/auth/register',
    method: 'POST',
    data: {
      username: data.username,
      email: data.email,
      password: data.password,
      full_name: data.full_name || ''
    }
  })
}

// ==================== 获取当前用户接口 ====================

/**
 * 获取当前登录用户信息
 * 
 * @returns {Promise<Object>} 返回当前用户的详细信息
 * 
 * @example
 * const user = await getCurrentUser()
 * // user: { id: 1, username: 'admin', email: 'admin@example.com', ... }
 */
export function getCurrentUser() {
  return request({
    url: '/auth/me',
    method: 'GET'
  })
}

// ==================== 导出所有接口 ====================

export default {
  login,
  register,
  getCurrentUser
}

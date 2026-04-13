/**
 * Axios 实例封装
 * 
 * 创建一个统一配置的 axios 实例，用于所有 API 请求：
 * - 统一的基础 URL 配置
 * - 请求拦截器：自动注入认证 Token
 * - 响应拦截器：统一错误处理、401 自动跳转登录
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// ==================== 创建 Axios 实例 ====================

/**
 * 创建自定义 axios 实例
 * 所有 API 请求都应使用此实例
 */
const request = axios.create({
  // API 基础路径，所有请求都会自动拼接此前缀
  baseURL: '/api/v1',
  // 请求超时时间：30秒
  timeout: 30000,
  // 请求头默认配置
  headers: {
    'Content-Type': 'application/json'
  }
})

// ==================== 请求拦截器 ====================

/**
 * 请求拦截器
 * 在每个请求发送前执行，用于：
 * - 自动注入 Authorization Bearer Token
 * - 可以在这里添加其他通用请求处理逻辑
 */
request.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取认证令牌
    const token = localStorage.getItem('access_token')
    
    // 如果存在 token，将其添加到请求头
    if (token) {
      // 使用 Bearer Token 认证方式
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 返回处理后的配置
    return config
  },
  (error) => {
    // 请求配置出错时的处理
    console.error('请求配置错误:', error)
    return Promise.reject(error)
  }
)

// ==================== 响应拦截器 ====================

/**
 * 响应拦截器
 * 在收到响应后执行，用于：
 * - 统一处理响应数据格式
 * - 统一处理错误状态码
 * - 401 未授权自动跳转登录页
 */
request.interceptors.response.use(
  (response) => {
    // 请求成功，直接返回响应数据
    // 后端返回的数据在 response.data 中
    return response.data
  },
  (error) => {
    // 获取错误响应信息
    const { response } = error
    
    // 根据不同的 HTTP 状态码进行处理
    if (response) {
      const { status, data } = response
      
      switch (status) {
        case 401:
          // 未授权：Token 过期或无效
          // 清除本地存储的认证信息
          localStorage.removeItem('access_token')
          localStorage.removeItem('user_info')
          
          // 显示提示信息
          ElMessage.error('登录已过期，请重新登录')
          
          // 跳转到登录页，并保存当前路径用于登录后重定向
          router.push({
            name: 'Login',
            query: { redirect: router.currentRoute.value.fullPath }
          })
          break
          
        case 403:
          // 禁止访问：权限不足
          ElMessage.error('没有权限执行此操作')
          break
          
        case 404:
          // 资源不存在
          ElMessage.error('请求的资源不存在')
          break
          
        case 422:
          // 请求参数验证失败
          // 尝试获取后端返回的详细错误信息
          const validationError = data?.detail || '请求参数错误'
          ElMessage.error(validationError)
          break
          
        case 500:
          // 服务器内部错误
          ElMessage.error('服务器错误，请稍后重试')
          break
          
        default:
          // 其他错误
          const errorMessage = data?.detail || data?.message || '请求失败'
          ElMessage.error(errorMessage)
      }
    } else if (error.code === 'ECONNABORTED') {
      // 请求超时
      ElMessage.error('请求超时，请检查网络连接')
    } else if (!window.navigator.onLine) {
      // 网络断开
      ElMessage.error('网络连接已断开，请检查网络')
    } else {
      // 其他网络错误
      ElMessage.error('网络错误，请稍后重试')
    }
    
    // 返回 rejected promise，让调用方可以继续处理错误
    return Promise.reject(error)
  }
)

// ==================== 导出 ====================

// 导出配置好的 axios 实例
export default request

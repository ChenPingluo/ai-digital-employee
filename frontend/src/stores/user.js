/**
 * 用户状态管理 Store
 * 
 * 使用 Pinia 管理用户认证相关的状态：
 * - 用户登录/登出
 * - Token 管理
 * - 用户信息存储
 * - 登录状态持久化
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getCurrentUser } from '@/api/auth'
import { ElMessage } from 'element-plus'
import router from '@/router'

// ==================== 定义 Store ====================

/**
 * 用户 Store
 * 
 * 使用 Composition API 风格定义
 * 提供用户认证和状态管理功能
 */
export const useUserStore = defineStore('user', () => {
  // ==================== 状态定义 ====================
  
  /**
   * 用户认证令牌
   * 初始化时从 localStorage 读取
   */
  const token = ref(localStorage.getItem('access_token') || '')
  
  /**
   * 用户信息对象
   * 包含 id, username, email, full_name 等字段
   */
  const userInfo = ref(null)
  
  /**
   * 加载状态
   * 用于在异步操作时显示加载指示器
   */
  const loading = ref(false)
  
  // ==================== 计算属性 ====================
  
  /**
   * 是否已登录
   * 根据 token 是否存在判断
   */
  const isLoggedIn = computed(() => !!token.value)
  
  /**
   * 获取用户名
   * 优先显示全名，其次是用户名
   */
  const displayName = computed(() => {
    if (userInfo.value) {
      return userInfo.value.full_name || userInfo.value.username
    }
    return ''
  })
  
  // ==================== 方法定义 ====================
  
  /**
   * 用户登录
   * 
   * @param {string} username - 用户名
   * @param {string} password - 密码
   * @returns {Promise<boolean>} 登录是否成功
   */
  async function login(username, password) {
    loading.value = true
    
    try {
      // 调用登录 API
      const response = await loginApi(username, password)
      
      // 保存 token 到状态和本地存储
      token.value = response.access_token
      localStorage.setItem('access_token', response.access_token)
      
      // 获取用户信息
      await fetchUserInfo()
      
      // 登录成功提示
      ElMessage.success('登录成功')
      
      return true
    } catch (error) {
      // 登录失败，错误信息由响应拦截器处理
      console.error('登录失败:', error)
      return false
    } finally {
      loading.value = false
    }
  }

  function clearAuthState() {
    token.value = ''
    userInfo.value = null

    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
  }
  
  /**
   * 用户登出
   * 
   * 清除所有认证状态并跳转到登录页
   */
  function logout() {
    clearAuthState()
    
    // 提示信息
    ElMessage.success('已退出登录')
    
    // 跳转到登录页
    router.push({ name: 'Login' })
  }

  /**
   * 处理认证过期
   *
   * 清理登录状态并跳回登录页，同时保留当前页面用于登录后返回。
   */
  function handleAuthExpired() {
    clearAuthState()
    router.push({
      name: 'Login',
      query: { redirect: router.currentRoute.value.fullPath }
    })
  }
  
  /**
   * 获取当前用户信息
   * 
   * 从服务器获取并更新用户信息
   */
  async function fetchUserInfo() {
    // 如果没有 token，不执行请求
    if (!token.value) {
      return
    }
    
    try {
      // 调用 API 获取用户信息
      const user = await getCurrentUser()
      
      // 更新状态
      userInfo.value = user
      
      // 缓存到本地存储（用于页面刷新后快速恢复显示）
      localStorage.setItem('user_info', JSON.stringify(user))
    } catch (error) {
      // 获取失败，可能是 token 过期
      console.error('获取用户信息失败:', error)
      
      // 如果是 401 错误，会被响应拦截器处理
      // 这里不需要额外处理
    }
  }
  
  /**
   * 初始化用户状态
   * 
   * 在应用启动时调用，用于恢复登录状态
   */
  function initializeAuth() {
    // 如果有 token，尝试从本地缓存恢复用户信息
    if (token.value) {
      const cachedUserInfo = localStorage.getItem('user_info')
      if (cachedUserInfo) {
        try {
          userInfo.value = JSON.parse(cachedUserInfo)
        } catch (e) {
          console.error('解析用户信息缓存失败:', e)
        }
      }
      
      // 异步获取最新的用户信息
      fetchUserInfo()
    }
  }
  
  // ==================== 返回暴露的内容 ====================
  
  return {
    // 状态
    token,
    userInfo,
    loading,
    
    // 计算属性
    isLoggedIn,
    displayName,
    
    // 方法
    login,
    logout,
    clearAuthState,
    handleAuthExpired,
    fetchUserInfo,
    initializeAuth
  }
})

// ==================== 导出 ====================

export default useUserStore

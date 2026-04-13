/**
 * Vue Router 路由配置
 * 
 * 定义应用的路由规则，包括：
 * - 聊天页面（首页）
 * - 仪表盘页面
 * - 登录页面
 * - 路由守卫（认证检查）
 */

import { createRouter, createWebHistory } from 'vue-router'

// ==================== 路由懒加载组件 ====================
// 使用动态导入实现路由组件的懒加载，优化首屏加载速度

// 聊天视图 - AI 对话主界面
const ChatView = () => import('@/views/ChatView.vue')

// 仪表盘视图 - 数据概览和统计
const DashboardView = () => import('@/views/DashboardView.vue')

// 登录视图 - 用户认证
const LoginView = () => import('@/views/LoginView.vue')


// ==================== 路由配置 ====================

const routes = [
  {
    // 首页 - 聊天界面
    path: '/',
    name: 'Chat',
    component: ChatView,
    meta: {
      // 页面标题
      title: 'AI 助手',
      // 是否需要登录
      requiresAuth: true
    }
  },
  {
    // 仪表盘页面
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardView,
    meta: {
      title: '工作台',
      requiresAuth: true
    }
  },
  {
    // 登录页面
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: {
      title: '登录',
      // 登录页不需要认证
      requiresAuth: false,
      // 已登录用户访问登录页时重定向到首页
      redirectIfAuth: true
    }
  },
  {
    // 404 页面 - 匹配所有未定义的路由
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/'
  }
]


// ==================== 创建路由实例 ====================

const router = createRouter({
  // 使用 HTML5 History 模式
  // 需要服务器配置支持，将所有请求重定向到 index.html
  history: createWebHistory(import.meta.env.BASE_URL),
  // 路由配置
  routes,
  // 滚动行为：每次导航时滚动到页面顶部
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      // 如果有保存的滚动位置（浏览器后退/前进），恢复该位置
      return savedPosition
    } else {
      // 否则滚动到页面顶部
      return { top: 0 }
    }
  }
})


// ==================== 全局前置守卫 ====================

router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title 
    ? `${to.meta.title} - AI 数字员工系统` 
    : 'AI 数字员工系统'
  
  // 从本地存储获取认证令牌
  const token = localStorage.getItem('access_token')
  const isAuthenticated = !!token
  
  // 检查是否需要认证
  if (to.meta.requiresAuth && !isAuthenticated) {
    // 需要认证但未登录，重定向到登录页
    // 保存原始目标路径，登录后可以重定向回来
    next({
      name: 'Login',
      query: { redirect: to.fullPath }
    })
  } else if (to.meta.redirectIfAuth && isAuthenticated) {
    // 已登录用户访问登录页，重定向到首页
    next({ name: 'Chat' })
  } else {
    // 正常导航
    next()
  }
})


// ==================== 全局后置钩子 ====================

router.afterEach((to, from) => {
  // 可以在这里添加页面访问统计等逻辑
  // console.log(`导航完成: ${from.path} -> ${to.path}`)
})


// 导出路由实例
export default router

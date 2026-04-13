/**
 * Vue 应用入口文件
 * 
 * 创建 Vue 应用实例，配置并挂载全局插件：
 * - Vue Router：路由管理
 * - Pinia：状态管理
 * - Element Plus：UI 组件库
 */

// 导入 Vue 核心
import { createApp } from 'vue'

// 导入根组件
import App from './App.vue'

// 导入路由配置
import router from './router'

// 导入 Pinia 状态管理
import { createPinia } from 'pinia'

// 导入 Element Plus 组件库
import ElementPlus from 'element-plus'
// 导入 Element Plus 样式
import 'element-plus/dist/index.css'
// 导入 Element Plus 中文语言包
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

// 导入全局样式
import '@/styles/global.css'

// ==================== 创建 Vue 应用实例 ====================
const app = createApp(App)

// ==================== 创建 Pinia 实例 ====================
const pinia = createPinia()

// ==================== 注册插件 ====================

// 注册 Pinia 状态管理
// Pinia 是 Vue 3 推荐的状态管理库，替代 Vuex
app.use(pinia)

// 注册 Vue Router
// 用于管理单页应用的路由
app.use(router)

// 注册 Element Plus
// 配置中文语言和组件尺寸
app.use(ElementPlus, {
  // 使用中文语言包
  locale: zhCn,
  // 默认组件尺寸
  size: 'default',
  // z-index 起始值
  zIndex: 3000
})

// ==================== 全局错误处理 ====================

// 捕获 Vue 组件中的错误
app.config.errorHandler = (err, vm, info) => {
  // 在开发环境打印错误信息
  console.error('Vue Error:', err)
  console.error('Error Info:', info)
  // 生产环境可以将错误上报到监控系统
}

// ==================== 挂载应用 ====================

// 将 Vue 应用挂载到 #app 元素
app.mount('#app')

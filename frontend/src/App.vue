<!--
  根组件 App.vue
  
  作为 Vue 应用的根组件，包含：
  - 全局布局结构
  - router-view 路由出口
  - 全局样式定义
-->

<template>
  <!-- 应用根容器 -->
  <div id="app-container">
    <!-- 
      路由出口
      所有路由匹配的组件都会渲染在这里
    -->
    <router-view v-slot="{ Component }">
      <!-- 路由过渡动画 -->
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<script setup>
/**
 * App 根组件
 * 
 * 使用 Vue 3 的 <script setup> 语法糖，
 * 提供更简洁的组件定义方式。
 */

// 导入 Vue 组合式 API
import { computed, onBeforeMount, onMounted, onUnmounted, watch } from 'vue'
import { useThemeStore } from '@/stores/theme'
import { useUserStore } from '@/stores/user'
import { useNotificationStore } from '@/stores/notification'

const themeStore = useThemeStore()
const userStore = useUserStore()
const notificationStore = useNotificationStore()

const isLoggedIn = computed(() => userStore.isLoggedIn)

// ==================== 生命周期钩子 ====================

onBeforeMount(() => {
  themeStore.initializeTheme()
  userStore.initializeAuth()
})

onMounted(() => {
  // 应用挂载完成
  console.log('AI 数字员工系统已启动')
})

onUnmounted(() => {
  notificationStore.disconnect()
})

watch(
  isLoggedIn,
  (loggedIn) => {
    if (loggedIn) {
      notificationStore.connect()
      return
    }

    notificationStore.disconnect()
  },
  { immediate: true }
)
</script>

<style>
/* ==================== 全局样式重置 ==================== */

/* 清除默认边距和内边距 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* HTML 根元素样式 */
html {
  /* 基础字体大小，用于 rem 单位计算 */
  font-size: 16px;
  /* 平滑滚动 */
  scroll-behavior: smooth;
}

/* Body 样式 */
body {
  /* 字体栈：优先使用系统字体 */
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
               'Helvetica Neue', Arial, 'Noto Sans', sans-serif,
               'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol';
  /* 字体抗锯齿 */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  /* 背景色 */
  background-color: var(--bg-base);
  /* 文字颜色 */
  color: var(--text-primary);
  /* 行高 */
  line-height: 1.5;
}

/* 链接样式 */
a {
  color: var(--primary-color);
  text-decoration: none;
}

a:hover {
  color: var(--primary-light);
}

/* ==================== 应用容器样式 ==================== */

#app-container {
  /* 最小高度占满视口 */
  min-height: 100vh;
  /* 宽度占满 */
  width: 100%;
  /* 深色底色 */
  background-color: var(--bg-base);
}

/* ==================== 路由过渡动画 ==================== */

/* 淡入淡出过渡效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ==================== 滚动条样式（WebKit 浏览器） ==================== */

/* 滚动条整体 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

/* 滚动条轨道 */
::-webkit-scrollbar-track {
  background-color: var(--bg-light);
  border-radius: 4px;
}

/* 滚动条滑块 */
::-webkit-scrollbar-thumb {
  background-color: var(--border-base);
  border-radius: 4px;
}

/* 滚动条滑块悬停状态 */
::-webkit-scrollbar-thumb:hover {
  background-color: var(--text-secondary);
}

/* ==================== Element Plus 样式覆盖 ==================== */

/* 确保 Element Plus 弹窗层级正确 */
.el-overlay {
  z-index: 3000 !important;
}
</style>

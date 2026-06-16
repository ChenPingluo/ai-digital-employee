/**
 * Vite 配置文件
 * 
 * 配置 Vue 插件和开发服务器代理，用于前端开发环境。
 * 代理配置将 /api 请求转发到后端服务器。
 */

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  // 配置 Vue 插件
  plugins: [
    vue()
  ],
  
  // 路径别名配置
  resolve: {
    alias: {
      // @ 指向 src 目录
      '@': resolve(__dirname, 'src')
    }
  },
  
  // 开发服务器配置
  server: {
    // 开发服务器端口
    port: 3000,
    // 自动打开浏览器
    open: true,
    // 代理配置
    proxy: {
      // 将 /api 开头的请求代理到后端服务器
      '/api': {
        // 后端服务器地址
        target: 'http://localhost:8000',
        // 修改请求头中的 Origin
        changeOrigin: true,
        // 支持 WebSocket
        ws: true,
        // 不重写路径，保持 /api 前缀
        // 如果后端 API 不带 /api 前缀，可以取消下面的注释
        // rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  
  // 构建配置
  build: {
    // 输出目录
    outDir: 'dist',
    // 静态资源目录
    assetsDir: 'assets',
    // 生成 sourcemap（生产环境可以关闭）
    sourcemap: false,
    // 代码压缩选项
    minify: 'terser',
    terserOptions: {
      compress: {
        // 生产环境移除 console
        drop_console: true,
        // 生产环境移除 debugger
        drop_debugger: true
      }
    },
    // 代码分割，将大型库拆分为独立 chunk
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus', 'element-plus/dist/locale/zh-cn.mjs'],
          'echarts': ['echarts'],
          'vue-vendor': ['vue', 'vue-router', 'pinia', 'axios']
        }
      }
    }
  }
})

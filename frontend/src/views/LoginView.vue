<!--
  登录视图组件 LoginView.vue
  
  用户登录/注册页面，提供：
  - 登录表单（用户名/密码）
  - 注册表单（用户名/邮箱/密码）
  - 表单验证
  - 登录/注册模式切换
  - 响应式设计
-->

<template>
  <div class="login-view">
    <!-- 背景装饰 -->
    <div class="login-bg">
      <div class="bg-shape shape-1"></div>
      <div class="bg-shape shape-2"></div>
      <div class="bg-shape shape-3"></div>
    </div>
    
    <!-- 登录卡片 -->
    <el-card class="login-card" shadow="always">
      <!-- 标题区域 -->
      <div class="login-header">
        <!-- Logo 图标 -->
        <div class="login-logo">
          <el-icon :size="48" color="#409EFF">
            <Monitor />
          </el-icon>
        </div>
        <h1>AI 数字员工系统</h1>
        <p>{{ isRegisterMode ? '创建新账号' : '智能办公助手，提升工作效率' }}</p>
      </div>
      
      <!-- 登录表单 -->
      <el-form
        v-if="!isRegisterMode"
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <!-- 用户名输入 -->
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名或邮箱"
            :prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>
        
        <!-- 密码输入 -->
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <!-- 记住我 & 忘记密码 -->
        <div class="login-options">
          <el-checkbox v-model="rememberMe">记住我</el-checkbox>
          <el-link type="primary" :underline="false" disabled>
            忘记密码？
          </el-link>
        </div>
        
        <!-- 登录按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="submit-button"
            :loading="isLoading"
            @click="handleLogin"
          >
            {{ isLoading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <!-- 注册表单 -->
      <el-form
        v-else
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        class="login-form"
        @submit.prevent="handleRegister"
      >
        <!-- 用户名输入 -->
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>
        
        <!-- 邮箱输入 -->
        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="邮箱地址"
            :prefix-icon="Message"
            size="large"
            clearable
          />
        </el-form-item>
        
        <!-- 全名输入（可选） -->
        <el-form-item prop="full_name">
          <el-input
            v-model="registerForm.full_name"
            placeholder="姓名（可选）"
            :prefix-icon="UserFilled"
            size="large"
            clearable
          />
        </el-form-item>
        
        <!-- 密码输入 -->
        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="密码（至少6位）"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        
        <!-- 确认密码 -->
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="确认密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleRegister"
          />
        </el-form-item>
        
        <!-- 注册按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="submit-button"
            :loading="isLoading"
            @click="handleRegister"
          >
            {{ isLoading ? '注册中...' : '注 册' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <!-- 底部切换 -->
      <div class="login-footer">
        <template v-if="!isRegisterMode">
          <span>还没有账号？</span>
          <el-link type="primary" :underline="false" @click="toggleMode">
            立即注册
          </el-link>
        </template>
        <template v-else>
          <span>已有账号？</span>
          <el-link type="primary" :underline="false" @click="toggleMode">
            返回登录
          </el-link>
        </template>
      </div>
    </el-card>
    
    <!-- 版权信息 -->
    <div class="copyright">
      © 2024 AI 数字员工系统 · 智能办公新体验
    </div>
  </div>
</template>

<script setup>
/**
 * 登录视图组件
 * 
 * 处理用户登录和注册逻辑
 */

import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  User, 
  Lock, 
  Message, 
  UserFilled,
  Monitor 
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { register as registerApi } from '@/api/auth'

// ==================== 路由和状态 ====================

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// ==================== 响应式数据 ====================

/**
 * 是否为注册模式
 */
const isRegisterMode = ref(false)

/**
 * 登录表单引用
 */
const loginFormRef = ref(null)

/**
 * 注册表单引用
 */
const registerFormRef = ref(null)

/**
 * 登录表单数据
 */
const loginForm = reactive({
  username: '',
  password: ''
})

/**
 * 注册表单数据
 */
const registerForm = reactive({
  username: '',
  email: '',
  full_name: '',
  password: '',
  confirmPassword: ''
})

/**
 * 记住我选项
 */
const rememberMe = ref(false)

/**
 * 加载状态
 */
const isLoading = ref(false)

// ==================== 表单验证规则 ====================

/**
 * 登录表单验证规则
 */
const loginRules = {
  username: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度应为 3-50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
  ]
}

/**
 * 确认密码验证器
 */
const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

/**
 * 注册表单验证规则
 */
const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 30, message: '用户名长度应为 3-30 个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  full_name: [
    { max: 50, message: '姓名长度不能超过 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度应为 6-50 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

// ==================== 方法 ====================

/**
 * 处理登录
 */
const handleLogin = async () => {
  // 验证表单
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return
  
  isLoading.value = true
  
  try {
    // 调用 store 的登录方法
    const success = await userStore.login(loginForm.username, loginForm.password)
    
    if (success) {
      // 跳转到原目标页面或首页
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    }
  } catch (error) {
    console.error('登录错误:', error)
  } finally {
    isLoading.value = false
  }
}

/**
 * 处理注册
 */
const handleRegister = async () => {
  // 验证表单
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid) return
  
  isLoading.value = true
  
  try {
    // 调用注册 API
    await registerApi({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
      full_name: registerForm.full_name
    })
    
    // 注册成功提示
    ElMessage.success('注册成功，请登录')
    
    // 切换到登录模式
    isRegisterMode.value = false
    
    // 预填用户名
    loginForm.username = registerForm.username
    
    // 清空注册表单
    resetRegisterForm()
    
  } catch (error) {
    console.error('注册错误:', error)
    // 错误信息由响应拦截器处理
  } finally {
    isLoading.value = false
  }
}

/**
 * 切换登录/注册模式
 */
const toggleMode = () => {
  isRegisterMode.value = !isRegisterMode.value
  
  // 清空表单
  if (isRegisterMode.value) {
    resetLoginForm()
  } else {
    resetRegisterForm()
  }
}

/**
 * 重置登录表单
 */
const resetLoginForm = () => {
  loginForm.username = ''
  loginForm.password = ''
  loginFormRef.value?.resetFields()
}

/**
 * 重置注册表单
 */
const resetRegisterForm = () => {
  registerForm.username = ''
  registerForm.email = ''
  registerForm.full_name = ''
  registerForm.password = ''
  registerForm.confirmPassword = ''
  registerFormRef.value?.resetFields()
}
</script>

<style scoped>
/* ==================== 登录视图容器 ==================== */

.login-view {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #0A0E14 0%, #0D1520 50%, #0A0E14 100%);
}

/* 网格线叠加效果 */
.login-view::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(0, 212, 255, 0.03) 0px, transparent 1px, transparent 60px),
    repeating-linear-gradient(90deg, rgba(0, 212, 255, 0.03) 0px, transparent 1px, transparent 60px);
  pointer-events: none;
  z-index: 0;
}

/* ==================== 背景装饰 ==================== */

.login-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  pointer-events: none;
}

.bg-shape {
  position: absolute;
  border-radius: 50%;
  background: rgba(0, 212, 255, 0.06);
}

.shape-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
  background: rgba(0, 212, 255, 0.05);
  animation: float 6s ease-in-out infinite;
}

.shape-2 {
  width: 300px;
  height: 300px;
  bottom: -50px;
  left: -50px;
  background: rgba(0, 212, 255, 0.08);
  animation: float 8s ease-in-out infinite reverse;
}

.shape-3 {
  width: 200px;
  height: 200px;
  top: 50%;
  left: 10%;
  background: rgba(0, 212, 255, 0.1);
  animation: float 7s ease-in-out infinite 1s;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

/* ==================== 登录卡片 ==================== */

.login-card {
  width: 100%;
  max-width: 420px;
  border-radius: var(--radius-large);
  z-index: 1;
  background: rgba(13, 17, 23, 0.8) !important;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 212, 255, 0.15) !important;
  box-shadow: var(--shadow-base);
  transition: border-color var(--transition-base);
}

.login-card:hover {
  border-color: rgba(0, 212, 255, 0.3) !important;
}

.login-card :deep(.el-card__body) {
  padding: 40px;
}

/* 覆盖 el-card 默认背景与边框 */
:deep(.el-card) {
  background: transparent;
  border: none;
}

/* ==================== 标题区域 ==================== */

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.login-header h1 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: var(--text-primary);
  font-weight: 600;
}

.login-header p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
}

/* ==================== 表单样式 ==================== */

.login-form {
  margin-bottom: 16px;
}

/* 输入框深色适配 */
.login-form :deep(.el-input__wrapper) {
  padding: 8px 12px;
  background-color: var(--bg-white);
  border: 1px solid var(--border-base);
  box-shadow: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.login-form :deep(.el-input__wrapper):hover {
  border-color: var(--primary-dark);
}

.login-form :deep(.el-input__wrapper.is-focus),
.login-form :deep(.el-input__wrapper:focus) {
  border-color: var(--primary-color) !important;
  box-shadow: var(--glow-primary) !important;
}

.login-form :deep(.el-input__inner) {
  color: var(--text-primary);
}

.login-form :deep(.el-input__inner::placeholder) {
  color: var(--text-placeholder);
}

.login-form :deep(.el-input__prefix .el-icon) {
  color: var(--text-secondary);
}

.login-form :deep(.el-input__suffix .el-icon) {
  color: var(--text-secondary);
}

/* 表单标签 */
.login-form :deep(.el-form-item__label) {
  color: var(--text-regular);
}

/* 表单验证错误信息 */
.login-form :deep(.el-form-item__error) {
  color: var(--danger-color);
}

/* 登录选项 */
.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

/* Checkbox 深色适配 */
.login-options :deep(.el-checkbox__label) {
  color: var(--text-regular);
}

.login-options :deep(.el-checkbox__inner) {
  background-color: var(--bg-white);
  border-color: var(--border-base);
}

.login-options :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}

.login-options :deep(.el-checkbox__input.is-checked + .el-checkbox__label) {
  color: var(--primary-color);
}

/* 忘记密码链接 */
.login-options :deep(.el-link--primary) {
  color: var(--primary-color);
}

.login-options :deep(.el-link--primary:hover) {
  color: var(--primary-light);
}

.login-options :deep(.el-link.is-disabled) {
  color: var(--text-placeholder);
}

/* 提交按钮 */
.submit-button {
  width: 100%;
  height: 46px;
  font-size: 16px;
  border-radius: var(--radius-base);
  background: var(--gradient-tech) !important;
  border: none !important;
  color: #fff !important;
  transition: box-shadow var(--transition-base), transform var(--transition-fast);
}

.submit-button:hover {
  box-shadow: var(--glow-strong) !important;
}

.submit-button:active {
  transform: scale(0.98);
}

/* ==================== 底部提示 ==================== */

.login-footer {
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
}

.login-footer span {
  color: var(--text-secondary);
}

.login-footer :deep(.el-link--primary) {
  color: var(--primary-color);
  margin-left: 4px;
  font-size: 14px;
}

.login-footer :deep(.el-link--primary:hover) {
  color: var(--primary-light);
}

/* ==================== 版权信息 ==================== */

.copyright {
  position: absolute;
  bottom: 20px;
  color: var(--text-secondary);
  font-size: 12px;
  z-index: 1;
}

/* ==================== 响应式适配 ==================== */

@media (max-width: 480px) {
  .login-card :deep(.el-card__body) {
    padding: 30px 24px;
  }
  
  .login-header h1 {
    font-size: 20px;
  }
  
  .bg-shape {
    display: none;
  }
}
</style>

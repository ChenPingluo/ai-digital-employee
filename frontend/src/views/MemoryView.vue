<!--
  记忆管理视图组件 MemoryView.vue

  展示 AI 从对话中自动提取的用户长期记忆：
  - 顶部统计卡片（总数、类型分布、容量使用率）
  - 筛选工具栏（按类型、分类、关键词搜索）
  - 记忆卡片列表（支持删除）
  - 响应式布局 + 深色/浅色主题适配
-->

<template>
  <div class="memory-view">
    <!-- 页面头部 -->
    <header class="memory-header">
      <div class="header-content">
        <div class="header-left">
          <el-button
            class="back-btn"
            :icon="ArrowLeft"
            text
            @click="$router.push('/')"
          />
          <div>
            <h1>记忆管理</h1>
            <p class="header-subtitle">
              AI 从对话中自动提取的关于您的长期记忆
            </p>
          </div>
        </div>
        <div class="header-right">
          <el-button
            :icon="Refresh"
            :loading="isLoading"
            @click="refreshAll"
          >
            刷新
          </el-button>
          <el-button
            :icon="isDarkTheme ? Sunny : Moon"
            @click="themeStore.toggleTheme()"
          >
            {{ isDarkTheme ? '浅色界面' : '深色界面' }}
          </el-button>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="memory-main">
      <!-- 统计卡片区域 -->
      <div class="stats-section">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon icon-total">
            <el-icon :size="28"><Coin /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.total }}</span>
            <span class="stat-label">记忆总数</span>
          </div>
          <div class="stat-trend">
            <el-tag type="info" size="small" effect="plain">
              上限 {{ stats.max_capacity }}
            </el-tag>
          </div>
        </el-card>

        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon icon-importance">
            <el-icon :size="28"><Star /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.avg_importance }}</span>
            <span class="stat-label">平均重要性</span>
          </div>
          <div class="stat-trend">
            <el-tag type="warning" size="small" effect="plain">
              / 10
            </el-tag>
          </div>
        </el-card>

        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon icon-usage">
            <el-icon :size="28"><DataBoard /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.usage_percent }}%</span>
            <span class="stat-label">容量使用率</span>
          </div>
          <div class="stat-trend">
            <el-progress
              :percentage="stats.usage_percent"
              :stroke-width="8"
              :show-text="false"
              :color="usageBarColor"
              style="width: 80px"
            />
          </div>
        </el-card>

        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon icon-types">
            <el-icon :size="28"><Collection /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ typeCountDisplay }}</span>
            <span class="stat-label">类型覆盖</span>
          </div>
          <div class="stat-trend">
            <el-tag size="small" effect="plain">
              {{ Object.keys(stats.by_type || {}).length }} 种
            </el-tag>
          </div>
        </el-card>
      </div>

      <!-- 工具栏 -->
      <div class="toolbar-section">
        <div class="toolbar-left">
          <!-- 类型筛选 -->
          <el-select
            v-model="filterType"
            placeholder="全部类型"
            clearable
            size="default"
            @change="handleFilterChange"
          >
            <el-option
              v-for="item in typeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            >
              <span>{{ item.emoji }} {{ item.label }}</span>
            </el-option>
          </el-select>

          <!-- 分类筛选 -->
          <el-select
            v-model="filterCategory"
            placeholder="全部分类"
            clearable
            size="default"
            @change="handleFilterChange"
          >
            <el-option
              v-for="item in categoryOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </div>

        <!-- 搜索 -->
        <div class="toolbar-right">
          <el-input
            v-model="searchQuery"
            placeholder="搜索记忆内容..."
            :prefix-icon="Search"
            clearable
            size="default"
            @keyup.enter="handleSearch"
            @clear="handleClearSearch"
          />
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>
      </div>

      <!-- 记忆列表 -->
      <div class="memory-list" v-loading="isLoading">
        <transition-group name="memory-card" tag="div" class="memory-grid">
          <div
            v-for="mem in memories"
            :key="mem.id"
            class="memory-card"
          >
            <div class="memory-card-header">
              <div class="memory-type-badge">
                <span class="type-emoji">{{ getTypeEmoji(mem.memory_type) }}</span>
                <span class="type-text">{{ getTypeLabel(mem.memory_type) }}</span>
              </div>
              <div class="memory-actions">
                <el-tag
                  v-if="mem.category"
                  size="small"
                  effect="plain"
                  class="category-tag"
                >
                  {{ mem.category }}
                </el-tag>
                <el-button
                  :icon="Delete"
                  text
                  size="small"
                  class="delete-btn"
                  @click="handleDeleteMemory(mem)"
                />
              </div>
            </div>

            <div class="memory-card-body">
              <p class="memory-content">{{ mem.content }}</p>
            </div>

            <div class="memory-card-footer">
              <div class="memory-meta">
                <el-rate
                  :model-value="mem.importance / 2"
                  disabled
                  :max="5"
                  size="small"
                  :colors="['#FFD700', '#FFD700', '#FFD700']"
                />
                <span class="importance-text">{{ mem.importance }}/10</span>
              </div>
              <div class="memory-meta-right">
                <span class="confidence-text" :title="`置信度 ${Math.round(mem.confidence * 100)}%`">
                  置信度 {{ Math.round(mem.confidence * 100) }}%
                </span>
                <span class="memory-time" :title="formatFullDate(mem.created_at)">
                  {{ formatRelativeTime(mem.created_at) }}
                </span>
              </div>
            </div>
          </div>
        </transition-group>

        <!-- 空状态 -->
        <el-empty
          v-if="!isLoading && memories.length === 0"
          :description="emptyDescription"
          :image-size="120"
        >
          <el-button type="primary" @click="$router.push('/')">
            去和 AI 聊天
          </el-button>
        </el-empty>
      </div>

      <!-- 加载更多的提示 -->
      <div v-if="!isLoading && memories.length > 0 && memories.length >= currentLimit" class="load-more">
        <el-button text type="primary" @click="loadMore">
          加载更多
        </el-button>
      </div>
    </main>
  </div>
</template>

<script setup>
/**
 * 记忆管理视图组件
 *
 * 展示用户长期记忆，支持筛选、搜索和删除。
 */

import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Refresh,
  Search,
  Delete,
  Coin,
  Star,
  DataBoard,
  Collection,
  Moon,
  Sunny
} from '@element-plus/icons-vue'

import { getMemories, searchMemories, getMemoryStats, deleteMemory } from '@/api/memory'
import { useThemeStore } from '@/stores/theme'

// ==================== Store ====================

const themeStore = useThemeStore()
const isDarkTheme = computed(() => themeStore.isDark)

// ==================== 常量 ====================

const typeOptions = [
  { value: 'fact', label: '事实', emoji: '📌' },
  { value: 'preference', label: '偏好', emoji: '⭐' },
  { value: 'event', label: '事件', emoji: '📅' },
  { value: 'person', label: '人物', emoji: '👤' },
  { value: 'context', label: '上下文', emoji: '💡' }
]

const categoryOptions = [
  { value: 'work', label: '工作' },
  { value: 'tech', label: '技术' },
  { value: 'health', label: '健康' },
  { value: 'life', label: '生活' },
  { value: 'learning', label: '学习' },
  { value: 'other', label: '其他' }
]

const PAGE_SIZE = 20

// ==================== 响应式状态 ====================

const isLoading = ref(false)
const memories = ref([])
const stats = ref({
  total: 0,
  by_type: {},
  avg_importance: 0,
  max_capacity: 200,
  usage_percent: 0
})

const filterType = ref('')
const filterCategory = ref('')
const searchQuery = ref('')
const currentLimit = ref(PAGE_SIZE)
const isSearchMode = ref(false)

// ==================== 计算属性 ====================

const usageBarColor = computed(() => {
  const pct = stats.value.usage_percent
  if (pct >= 80) return '#F56C6C'
  if (pct >= 50) return '#E6A23C'
  return '#67C23A'
})

const typeCountDisplay = computed(() => {
  const types = stats.value.by_type || {}
  return Object.keys(types).length
})

const emptyDescription = computed(() => {
  if (isSearchMode.value) return '没有匹配的记忆'
  if (filterType.value || filterCategory.value) return '当前筛选条件下没有记忆'
  return '还没有记忆，和 AI 多聊聊天吧'
})

// ==================== 方法 ====================

/**
 * 加载统计数据
 */
async function fetchStats() {
  try {
    const data = await getMemoryStats()
    stats.value = data
  } catch (error) {
    console.error('获取记忆统计失败:', error)
  }
}

/**
 * 加载记忆列表
 */
async function fetchMemories(append = false) {
  if (!append) {
    memories.value = []
    currentLimit.value = PAGE_SIZE
  }

  isLoading.value = true
  try {
    const params = { limit: currentLimit.value }
    if (filterType.value) params.memory_type = filterType.value
    if (filterCategory.value) params.category = filterCategory.value

    const data = await getMemories(params)
    memories.value = Array.isArray(data) ? data : []
    isSearchMode.value = false
  } catch (error) {
    console.error('获取记忆列表失败:', error)
    ElMessage.error('获取记忆列表失败')
    memories.value = []
  } finally {
    isLoading.value = false
  }
}

/**
 * 搜索记忆
 */
async function handleSearch() {
  const q = searchQuery.value.trim()
  if (!q) {
    handleClearSearch()
    return
  }

  isLoading.value = true
  isSearchMode.value = true
  try {
    const data = await searchMemories(q, 50)
    memories.value = Array.isArray(data) ? data : []
  } catch (error) {
    console.error('搜索记忆失败:', error)
    ElMessage.error('搜索记忆失败')
    memories.value = []
  } finally {
    isLoading.value = false
  }
}

/**
 * 清除搜索
 */
function handleClearSearch() {
  searchQuery.value = ''
  isSearchMode.value = false
  fetchMemories()
}

/**
 * 筛选变化
 */
function handleFilterChange() {
  searchQuery.value = ''
  isSearchMode.value = false
  fetchMemories()
}

/**
 * 加载更多
 */
function loadMore() {
  currentLimit.value += PAGE_SIZE
  fetchMemories()
}

/**
 * 删除记忆
 */
async function handleDeleteMemory(mem) {
  try {
    await ElMessageBox.confirm(
      `确定要删除这条记忆吗？\n\n「${mem.content}」`,
      '删除记忆',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )

    await deleteMemory(mem.id)
    ElMessage.success('记忆已删除')

    // 从列表中移除
    memories.value = memories.value.filter(m => m.id !== mem.id)
    // 刷新统计
    fetchStats()
  } catch (error) {
    if (error !== 'cancel' && error?.toString() !== 'cancel') {
      console.error('删除记忆失败:', error)
      ElMessage.error('删除失败，请重试')
    }
  }
}

/**
 * 刷新所有数据
 */
function refreshAll() {
  searchQuery.value = ''
  filterType.value = ''
  filterCategory.value = ''
  isSearchMode.value = false
  fetchStats()
  fetchMemories()
}

// ==================== 工具函数 ====================

function getTypeEmoji(type) {
  const map = { fact: '📌', preference: '⭐', event: '📅', person: '👤', context: '💡' }
  return map[type] || '📌'
}

function getTypeLabel(type) {
  const map = { fact: '事实', preference: '偏好', event: '事件', person: '人物', context: '上下文' }
  return map[type] || type
}

function formatRelativeTime(timestamp) {
  if (!timestamp) return ''
  const now = new Date()
  const date = new Date(timestamp)
  const diff = now - date
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  if (hours < 24) return `${hours} 小时前`
  if (days < 7) return `${days} 天前`
  if (days < 30) return `${Math.floor(days / 7)} 周前`
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  return `${month}-${day}`
}

function formatFullDate(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

// ==================== 生命周期 ====================

onMounted(() => {
  refreshAll()
})
</script>


<style scoped>
/* ==================== 页面容器 ==================== */

.memory-view {
  min-height: 100vh;
  background-color: var(--bg-base);
}

/* ==================== 页面头部 ==================== */

.memory-header {
  background: var(--bg-light);
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-base);
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  color: var(--text-secondary) !important;
  font-size: 18px;
}

.back-btn:hover {
  color: var(--primary-color) !important;
}

.header-left h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-subtitle {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.header-right {
  display: flex;
  gap: 12px;
}

.header-right :deep(.el-button) {
  background: var(--bg-white);
  border-color: var(--border-base);
  color: var(--text-secondary);
}

.header-right :deep(.el-button:hover) {
  color: var(--primary-color);
  border-color: var(--primary-color);
  background: rgba(0, 212, 255, 0.08);
}

/* ==================== 主内容区 ==================== */

.memory-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

/* ==================== 统计卡片 ==================== */

.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

:deep(.stat-card.el-card) {
  background: var(--bg-light);
  border: 1px solid var(--border-base);
  --el-card-bg-color: var(--bg-light);
  transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}

:deep(.stat-card.el-card:hover) {
  transform: translateY(-4px);
  border-color: rgba(0, 212, 255, 0.3);
  box-shadow: var(--glow-primary);
}

.stat-card :deep(.el-card__body) {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-total {
  background: rgba(0, 212, 255, 0.1);
  color: var(--primary-color);
}

.icon-importance {
  background: rgba(255, 215, 0, 0.12);
  color: #FFD700;
}

.icon-usage {
  background: rgba(0, 255, 163, 0.1);
  color: var(--success-color);
}

.icon-types {
  background: rgba(255, 77, 106, 0.1);
  color: var(--danger-color);
}

.stat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--primary-color);
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.stat-trend {
  flex-shrink: 0;
}

.stat-trend :deep(.el-tag) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  color: var(--text-regular);
}

.stat-trend :deep(.el-tag--warning) {
  background: rgba(255, 184, 0, 0.1);
  border-color: rgba(255, 184, 0, 0.2);
  color: var(--warning-color);
}

.stat-trend :deep(.el-tag--info) {
  background: rgba(125, 133, 144, 0.1);
  border-color: rgba(125, 133, 144, 0.2);
  color: var(--text-secondary);
}

/* el-progress 深色适配 */
.stat-trend :deep(.el-progress-bar__outer) {
  background-color: var(--border-light);
}

/* ==================== 工具栏 ==================== */

.toolbar-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 筛选下拉框深色适配 */
.toolbar-left :deep(.el-input__wrapper) {
  background: var(--bg-white);
  border: 1px solid var(--border-base);
  box-shadow: none;
}

.toolbar-left :deep(.el-input__wrapper:hover) {
  border-color: var(--primary-color);
}

.toolbar-left :deep(.el-input__inner) {
  color: var(--text-regular);
}

/* 搜索框深色适配 */
.toolbar-right :deep(.el-input__wrapper) {
  background: var(--bg-white);
  border: 1px solid var(--border-base);
  box-shadow: none;
}

.toolbar-right :deep(.el-input__wrapper:hover),
.toolbar-right :deep(.el-input__wrapper.is-focus) {
  border-color: var(--primary-color);
}

.toolbar-right :deep(.el-input__inner) {
  color: var(--text-regular);
}

.toolbar-right :deep(.el-input__prefix .el-icon) {
  color: var(--text-secondary);
}

.toolbar-right :deep(.el-button--primary) {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: var(--bg-base);
}

.toolbar-right :deep(.el-button--primary:hover) {
  background: var(--primary-light);
  border-color: var(--primary-light);
}

/* ==================== 记忆列表 ==================== */

.memory-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.memory-card {
  background: var(--bg-light);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-large);
  padding: 20px;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.memory-card:hover {
  border-color: rgba(0, 212, 255, 0.25);
  box-shadow: var(--shadow-base);
  transform: translateY(-2px);
}

/* 卡片头 */
.memory-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.memory-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(0, 212, 255, 0.08);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: var(--radius-base);
}

.type-emoji {
  font-size: 14px;
}

.type-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--primary-color);
}

.memory-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.category-tag {
  font-size: 11px;
}

:deep(.category-tag.el-tag) {
  background: rgba(255, 184, 0, 0.1);
  border-color: rgba(255, 184, 0, 0.2);
  color: var(--warning-color);
}

.delete-btn {
  opacity: 0;
  transition: opacity 0.2s ease, color 0.2s ease;
  color: var(--text-secondary) !important;
  padding: 4px;
}

.memory-card:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: var(--danger-color) !important;
}

/* 卡片体 */
.memory-card-body {
  flex: 1;
}

.memory-content {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-regular);
  margin: 0;
  word-break: break-word;
}

/* 卡片底 */
.memory-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
  gap: 8px;
}

.memory-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.importance-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.memory-meta-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.confidence-text {
  font-size: 11px;
  color: var(--text-secondary);
  opacity: 0.8;
}

.memory-time {
  font-size: 11px;
  color: var(--text-secondary);
}

/* el-rate 深色背景适配 */
.memory-meta :deep(.el-rate__icon) {
  font-size: 14px;
}

/* ==================== 加载更多 ==================== */

.load-more {
  display: flex;
  justify-content: center;
  padding: 24px 0;
}

.load-more :deep(.el-button) {
  color: var(--text-secondary);
}

.load-more :deep(.el-button:hover) {
  color: var(--primary-color);
}

/* ==================== 空状态 ==================== */

:deep(.el-empty__description p) {
  color: var(--text-secondary);
}

/* ==================== 过渡动画 ==================== */

.memory-card-enter-active {
  transition: all 0.4s ease;
}

.memory-card-leave-active {
  transition: all 0.3s ease;
}

.memory-card-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.memory-card-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.memory-card-move {
  transition: transform 0.4s ease;
}

/* ==================== loading 深色适配 ==================== */

:deep(.el-loading-mask) {
  background-color: rgba(10, 14, 20, 0.6);
}

[data-theme='light'] :deep(.el-loading-mask) {
  background-color: rgba(244, 247, 251, 0.6);
}

/* ==================== 响应式适配 ==================== */

@media (max-width: 1200px) {
  .stats-section {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .memory-header {
    padding: 16px;
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-right {
    width: 100%;
    justify-content: flex-end;
  }

  .memory-main {
    padding: 16px;
  }

  .stats-section {
    grid-template-columns: 1fr;
  }

  .toolbar-section {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left {
    flex-wrap: wrap;
  }

  .toolbar-right {
    flex: 1;
  }

  .toolbar-right :deep(.el-input) {
    flex: 1;
  }

  .memory-grid {
    grid-template-columns: 1fr;
  }

  .memory-card-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>

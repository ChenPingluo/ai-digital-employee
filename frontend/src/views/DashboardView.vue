<!--
  仪表盘视图组件 DashboardView.vue

  数据看板页面，展示：
  - 顶部统计卡片
  - 任务状态饼图
  - 会议室使用柱状图
  - 响应式布局
-->

<template>
  <div class="dashboard-view">
    <!-- 页面头部 -->
    <header class="dashboard-header">
      <div class="header-content">
        <div class="header-left">
          <h1>数据看板</h1>
          <p class="header-subtitle">
            {{ currentDateStr }}
          </p>
        </div>
        <div class="header-right">
          <el-button
            type="primary"
            :icon="ChatDotRound"
            @click="$router.push('/')"
          >
            AI 助手
          </el-button>
          <el-button
            :icon="Coin"
            @click="$router.push('/memory')"
          >
            记忆管理
          </el-button>
          <el-button
            :icon="Refresh"
            :loading="isLoading"
            @click="refreshData"
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
    <main class="dashboard-main">
      <!-- 统计卡片区域 -->
      <div class="stats-section">
        <!-- 待办总数卡片 -->
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon icon-todo">
            <el-icon :size="28"><List /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ todoStats.total }}</span>
            <span class="stat-label">待办总数</span>
          </div>
          <div class="stat-trend">
            <el-tag
              class="stat-action-tag"
              type="info"
              size="small"
              effect="plain"
              @click="openTodoDialog"
            >
              全部任务
            </el-tag>
          </div>
        </el-card>

        <!-- 已完成卡片 -->
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon icon-completed">
            <el-icon :size="28"><CircleCheck /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ todoStats.completed }}</span>
            <span class="stat-label">已完成</span>
          </div>
          <div class="stat-trend">
            <el-tag type="success" size="small" effect="plain">
              {{ completionRate }}%
            </el-tag>
          </div>
        </el-card>

        <!-- 进行中卡片 -->
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon icon-progress">
            <el-icon :size="28"><Timer /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ todoStats.in_progress }}</span>
            <span class="stat-label">进行中</span>
          </div>
          <div class="stat-trend">
            <el-tag type="primary" size="small" effect="plain">
              处理中
            </el-tag>
          </div>
        </el-card>

        <!-- 会议预约卡片 -->
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon icon-meeting">
            <el-icon :size="28"><Calendar /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ totalReservations }}</span>
            <span class="stat-label">会议预约</span>
          </div>
          <div class="stat-trend">
            <el-tag type="warning" size="small" effect="plain">
              {{ totalMeetingHours.toFixed(1) }}h
            </el-tag>
          </div>
        </el-card>
      </div>

      <!-- 图表区域 -->
      <div class="charts-section">
        <el-row :gutter="20">
          <!-- 任务统计图表 -->
          <el-col :xs="24" :sm="24" :md="12" :lg="12">
            <el-card class="chart-card" shadow="hover">
              <TaskChart :data="todoStats" />
            </el-card>
          </el-col>

          <!-- 会议室使用图表 -->
          <el-col :xs="24" :sm="24" :md="12" :lg="12">
            <el-card class="chart-card" shadow="hover">
              <MeetingChart :data="meetingStats" />
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 详情区域 -->
      <div class="details-section">
        <el-row :gutter="20">
          <!-- 最近待办 -->
          <el-col :xs="24" :sm="24" :md="12" :lg="12">
            <el-card class="detail-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-title">
                    <el-icon><List /></el-icon>
                    待办事项
                  </span>
                  <el-button text type="primary" @click="$router.push('/')">
                    <span>通过 AI 管理</span>
                    <el-icon class="el-icon--right"><ArrowRight /></el-icon>
                  </el-button>
                </div>
              </template>

              <!-- 待办列表 -->
              <div class="todo-list">
                <div
                  v-for="item in recentTodos"
                  :key="item.id"
                  class="todo-item"
                >
                  <el-tag
                    :type="getStatusType(item.status)"
                    size="small"
                    effect="plain"
                  >
                    {{ getStatusLabel(item.status) }}
                  </el-tag>
                  <span class="todo-title">{{ item.title }}</span>
                </div>

                <!-- 空状态 -->
                <el-empty
                  v-if="recentTodos.length === 0"
                  description="暂无待办事项"
                  :image-size="80"
                />
              </div>
            </el-card>
          </el-col>

          <!-- 会议室列表 -->
          <el-col :xs="24" :sm="24" :md="12" :lg="12">
            <el-card class="detail-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-title">
                    <el-icon><OfficeBuilding /></el-icon>
                    会议室
                  </span>
                  <el-button text type="primary" @click="$router.push('/')">
                    <span>预约会议室</span>
                    <el-icon class="el-icon--right"><ArrowRight /></el-icon>
                  </el-button>
                </div>
              </template>

              <!-- 会议室列表 -->
              <div class="room-list">
                <div
                  v-for="room in meetingStats"
                  :key="room.room_id"
                  class="room-item"
                >
                  <div class="room-info">
                    <span class="room-name">{{ room.room_name }}</span>
                    <span class="room-count">
                      {{ room.reservation_count }} 次预约
                    </span>
                  </div>
                  <el-progress
                    :percentage="Math.min(room.reservation_count * 10, 100)"
                    :stroke-width="8"
                    :show-text="false"
                    :color="getProgressColor(room.reservation_count)"
                  />
                </div>

                <!-- 空状态 -->
                <el-empty
                  v-if="meetingStats.length === 0"
                  description="暂无会议室数据"
                  :image-size="80"
                />
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </main>

    <el-dialog
      v-model="isTodoDialogVisible"
      title="全部任务"
      width="760px"
      class="todo-dialog"
    >
      <div class="todo-dialog-toolbar">
        <span class="todo-dialog-summary">共 {{ todoDialogTotal }} 条任务</span>
      </div>

      <el-table
        v-loading="isTodoDialogLoading"
        :data="allTodos"
        stripe
        empty-text="暂无任务"
      >
        <el-table-column prop="title" label="任务" min-width="240" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag
              :type="getStatusType(row.status)"
              size="small"
              effect="plain"
            >
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="100">
          <template #default="{ row }">
            {{ getPriorityLabel(row.priority) }}
          </template>
        </el-table-column>
        <el-table-column label="截止时间" min-width="180">
          <template #default="{ row }">
            {{ formatTodoDate(row.due_date) }}
          </template>
        </el-table-column>
      </el-table>

      <div class="todo-dialog-pagination">
        <el-pagination
          background
          layout="prev, pager, next"
          :current-page="todoDialogPage"
          :page-size="TODO_DIALOG_PAGE_SIZE"
          :total="todoDialogTotal"
          @current-change="handleTodoDialogPageChange"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 仪表盘视图组件
 *
 * 展示统计数据和图表
 */

import { ref, computed, onMounted, watch } from 'vue'
import {
  ChatDotRound,
  Refresh,
  List,
  CircleCheck,
  Timer,
  Calendar,
  Moon,
  Sunny,
  ArrowRight,
  OfficeBuilding,
  Coin
} from '@element-plus/icons-vue'

// 导入组件
import TaskChart from '@/components/TaskChart.vue'
import MeetingChart from '@/components/MeetingChart.vue'

// 导入 Store
import { useStatisticsStore } from '@/stores/statistics'
import { useThemeStore } from '@/stores/theme'
import { getTodos } from '@/api/todo'

// ==================== Store ====================

const statisticsStore = useStatisticsStore()
const themeStore = useThemeStore()

// ==================== 响应式数据 ====================

/**
 * 加载状态
 */
const isLoading = computed(() => statisticsStore.loading)

/**
 * 待办统计数据
 */
const todoStats = computed(() => statisticsStore.todoStats)

/**
 * 会议室统计数据
 */
const meetingStats = computed(() => statisticsStore.meetingStats)

/**
 * 总预约次数
 */
const totalReservations = computed(() => statisticsStore.totalReservations)

/**
 * 总会议时长
 */
const totalMeetingHours = computed(() => statisticsStore.totalMeetingHours)
const isDarkTheme = computed(() => themeStore.isDark)

/**
 * 完成率
 */
const completionRate = computed(() => {
  const { total, completed } = todoStats.value
  if (total === 0) return 0
  return Math.round((completed / total) * 100)
})

/**
 * 当前日期字符串
 */
const currentDateStr = computed(() => {
  const now = new Date()
  const options = {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  }
  return now.toLocaleDateString('zh-CN', options)
})

const recentTodos = ref([])
const allTodos = ref([])
const isTodoDialogVisible = ref(false)
const isTodoDialogLoading = ref(false)
const todoDialogPage = ref(1)
const todoDialogTotal = ref(0)
let hasCompletedInitialRefresh = false
let isRefreshingDashboard = false

const DASHBOARD_TODO_LIMIT = 6
const TODO_DIALOG_PAGE_SIZE = 10

// ==================== 方法 ====================

/**
 * 刷新数据
 */
const refreshData = async () => {
  isRefreshingDashboard = true
  try {
    await Promise.all([
      statisticsStore.fetchAllStats(),
      fetchRecentTodos()
    ])
  } finally {
    isRefreshingDashboard = false
  }
}

function sortTodosForDashboard(a, b) {
  if (a.due_date && b.due_date) {
    return new Date(a.due_date).getTime() - new Date(b.due_date).getTime()
  }

  if (a.due_date) {
    return -1
  }

  if (b.due_date) {
    return 1
  }

  return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
}

async function fetchRecentTodos() {
  try {
    const [pendingResp, progressResp] = await Promise.all([
      getTodos({ status: 'pending', page_size: DASHBOARD_TODO_LIMIT }),
      getTodos({ status: 'in_progress', page_size: DASHBOARD_TODO_LIMIT })
    ])

    const activeTodos = [
      ...(pendingResp.items || []),
      ...(progressResp.items || [])
    ]

    recentTodos.value = activeTodos
      .sort(sortTodosForDashboard)
      .slice(0, DASHBOARD_TODO_LIMIT)
  } catch (error) {
    console.error('获取看板待办列表失败:', error)
    recentTodos.value = []
  }
}

async function fetchAllTodos(page = 1) {
  try {
    isTodoDialogLoading.value = true
    const response = await getTodos({
      page,
      page_size: TODO_DIALOG_PAGE_SIZE
    })

    allTodos.value = response.items || []
    todoDialogTotal.value = response.total || 0
    todoDialogPage.value = response.page || page
  } catch (error) {
    console.error('获取全部任务失败:', error)
    allTodos.value = []
    todoDialogTotal.value = 0
  } finally {
    isTodoDialogLoading.value = false
  }
}

async function openTodoDialog() {
  isTodoDialogVisible.value = true
  await fetchAllTodos(1)
}

async function handleTodoDialogPageChange(page) {
  await fetchAllTodos(page)
}

/**
 * 获取状态对应的 tag 类型
 * @param {string} status - 状态值
 */
const getStatusType = (status) => {
  const map = {
    pending: 'warning',
    in_progress: 'primary',
    completed: 'success',
    cancelled: 'info'
  }
  return map[status] || 'info'
}

/**
 * 获取状态对应的标签文本
 * @param {string} status - 状态值
 */
const getStatusLabel = (status) => {
  const map = {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消'
  }
  return map[status] || status
}

const getPriorityLabel = (priority) => {
  const map = {
    0: '低',
    1: '中',
    2: '高',
    3: '紧急'
  }
  return map[priority] || '未知'
}

const formatTodoDate = (value) => {
  if (!value) return '未设置'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '未设置'
  }

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

/**
 * 获取进度条颜色
 * @param {number} count - 预约次数
 */
const getProgressColor = (count) => {
  if (count >= 8) return '#F56C6C'
  if (count >= 5) return '#E6A23C'
  return '#67C23A'
}

// ==================== 生命周期 ====================

onMounted(() => {
  // 加载统计数据
  refreshData().finally(() => {
    hasCompletedInitialRefresh = true
  })
})

watch(
  () => statisticsStore.lastUpdated,
  () => {
    if (!hasCompletedInitialRefresh || isRefreshingDashboard) return
    fetchRecentTodos()
  }
)
</script>

<style scoped>
/* ==================== 页面容器 ==================== */

.dashboard-view {
  min-height: 100vh;
  background-color: var(--bg-base);
}

/* ==================== 页面头部 ==================== */

.dashboard-header {
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

/* 头部按钮深色适配 */
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

.header-right :deep(.el-button--primary) {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: var(--bg-base);
}

.header-right :deep(.el-button--primary:hover) {
  background: var(--primary-light);
  border-color: var(--primary-light);
  color: var(--bg-base);
}

/* ==================== 主内容区 ==================== */

.dashboard-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

/* ==================== 统计卡片区域 ==================== */

.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
}

/* el-card 深色适配 */
.stat-card:deep(.el-card) {
  background: var(--bg-light);
  border: 1px solid var(--border-base);
}

:deep(.stat-card.el-card) {
  background: var(--bg-light);
  border: 1px solid var(--border-base);
  --el-card-bg-color: var(--bg-light);
}

:deep(.stat-card.el-card:hover) {
  border-color: rgba(0, 212, 255, 0.3);
  box-shadow: var(--glow-primary);
}

.stat-card :deep(.el-card__body) {
  padding: 0;
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(0, 212, 255, 0.1);
  color: var(--primary-color);
}

.icon-todo {
  background: rgba(0, 212, 255, 0.1);
  color: var(--primary-color);
}

.icon-completed {
  background: rgba(0, 255, 163, 0.1);
  color: var(--success-color);
}

.icon-progress {
  background: rgba(255, 184, 0, 0.1);
  color: var(--warning-color);
}

.icon-meeting {
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

/* stat-trend el-tag 深色适配 */
.stat-trend :deep(.el-tag) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  color: var(--text-regular);
}

.stat-trend :deep(.el-tag--success) {
  background: rgba(0, 255, 163, 0.1);
  border-color: rgba(0, 255, 163, 0.2);
  color: var(--success-color);
}

.stat-trend :deep(.el-tag--primary) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  color: var(--primary-color);
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

.stat-action-tag {
  cursor: pointer;
}

/* ==================== 图表区域 ==================== */

.charts-section {
  margin-bottom: 24px;
}

.chart-card {
  height: 380px;
}

:deep(.chart-card.el-card) {
  background: var(--bg-light);
  border: 1px solid var(--border-base);
  --el-card-bg-color: var(--bg-light);
}

.chart-card :deep(.el-card__body) {
  height: 100%;
  padding: 20px;
}

/* ==================== 详情区域 ==================== */

.detail-card {
  min-height: 320px;
}

:deep(.detail-card.el-card) {
  background: var(--bg-light);
  border: 1px solid var(--border-base);
  --el-card-bg-color: var(--bg-light);
}

:deep(.detail-card.el-card .el-card__header) {
  border-bottom: 1px solid var(--border-base);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-header :deep(.el-button) {
  color: var(--text-secondary);
}

.card-header :deep(.el-button:hover) {
  color: var(--primary-color);
}

/* 待办列表 */
.todo-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-light);
  border-radius: var(--radius-base);
  transition: background-color 0.2s ease;
}

.todo-item:nth-child(even) {
  background: var(--bg-white);
}

.todo-item:hover {
  background: rgba(0, 212, 255, 0.05);
}

/* 待办事项 el-tag 深色适配 */
.todo-item :deep(.el-tag) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  color: var(--primary-color);
}

.todo-item :deep(.el-tag--warning) {
  background: rgba(255, 184, 0, 0.1);
  border-color: rgba(255, 184, 0, 0.2);
  color: var(--warning-color);
}

.todo-item :deep(.el-tag--success) {
  background: rgba(0, 255, 163, 0.1);
  border-color: rgba(0, 255, 163, 0.2);
  color: var(--success-color);
}

.todo-item :deep(.el-tag--info) {
  background: rgba(125, 133, 144, 0.1);
  border-color: rgba(125, 133, 144, 0.2);
  color: var(--text-secondary);
}

.todo-title {
  flex: 1;
  font-size: 14px;
  color: var(--text-regular);
}

/* 会议室列表 */
.room-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.room-item {
  padding: 12px;
  background: var(--bg-light);
  border-radius: var(--radius-base);
  transition: background-color 0.2s ease;
}

.room-item:nth-child(even) {
  background: var(--bg-white);
}

.room-item:hover {
  background: rgba(0, 212, 255, 0.05);
}

.room-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.room-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.room-count {
  font-size: 12px;
  color: var(--text-secondary);
}

.todo-dialog-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.todo-dialog-summary {
  font-size: 13px;
  color: var(--text-secondary);
}

.todo-dialog-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

/* el-progress 深色适配 */
.room-item :deep(.el-progress-bar__outer) {
  background-color: var(--border-light);
}

/* el-empty 深色适配 */
:deep(.el-empty__description p) {
  color: var(--text-secondary);
}

/* ==================== 响应式适配 ==================== */

@media (max-width: 1200px) {
  .stats-section {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .dashboard-header {
    padding: 16px;
  }

  .header-content {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }

  .header-right {
    width: 100%;
    justify-content: flex-end;
  }

  .dashboard-main {
    padding: 16px;
  }

  .stats-section {
    grid-template-columns: 1fr;
  }

  .stat-card {
    padding: 16px;
  }

  .chart-card {
    margin-bottom: 16px;
  }

  .detail-card {
    margin-bottom: 16px;
  }
}

/* ==================== 详情卡片间距修复 ==================== */

.details-section .el-col {
  margin-bottom: 20px;
}

@media (min-width: 768px) {
  .details-section .el-col {
    margin-bottom: 0;
  }
}
</style>

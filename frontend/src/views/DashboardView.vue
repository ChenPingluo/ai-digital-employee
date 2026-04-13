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
            :icon="Refresh"
            :loading="isLoading"
            @click="refreshData"
          >
            刷新
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
            <el-tag type="info" size="small" effect="plain">
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
  </div>
</template>

<script setup>
/**
 * 仪表盘视图组件
 * 
 * 展示统计数据和图表
 */

import { ref, computed, onMounted } from 'vue'
import {
  ChatDotRound,
  Refresh,
  List,
  CircleCheck,
  Timer,
  Calendar,
  ArrowRight,
  OfficeBuilding
} from '@element-plus/icons-vue'

// 导入组件
import TaskChart from '@/components/TaskChart.vue'
import MeetingChart from '@/components/MeetingChart.vue'

// 导入 Store
import { useStatisticsStore } from '@/stores/statistics'

// ==================== Store ====================

const statisticsStore = useStatisticsStore()

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

/**
 * 模拟的最近待办数据
 */
const recentTodos = ref([
  { id: 1, title: '完成项目周报', status: 'in_progress' },
  { id: 2, title: '准备会议材料', status: 'pending' },
  { id: 3, title: '代码审查', status: 'completed' },
  { id: 4, title: '更新文档', status: 'pending' }
])

// ==================== 方法 ====================

/**
 * 刷新数据
 */
const refreshData = async () => {
  await statisticsStore.fetchAllStats()
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
  refreshData()
})
</script>

<style scoped>
/* ==================== 页面容器 ==================== */

.dashboard-view {
  min-height: 100vh;
  background-color: #f5f7fa;
}

/* ==================== 页面头部 ==================== */

.dashboard-header {
  background: white;
  padding: 20px 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
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
  color: #303133;
}

.header-subtitle {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: #909399;
}

.header-right {
  display: flex;
  gap: 12px;
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
  transition: transform 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
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
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-todo {
  background: #ecf5ff;
  color: #409EFF;
}

.icon-completed {
  background: #f0f9eb;
  color: #67C23A;
}

.icon-progress {
  background: #fdf6ec;
  color: #E6A23C;
}

.icon-meeting {
  background: #fef0f0;
  color: #F56C6C;
}

.stat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.stat-trend {
  flex-shrink: 0;
}

/* ==================== 图表区域 ==================== */

.charts-section {
  margin-bottom: 24px;
}

.chart-card {
  height: 380px;
}

.chart-card :deep(.el-card__body) {
  height: 100%;
  padding: 20px;
}

/* ==================== 详情区域 ==================== */

.detail-card {
  min-height: 320px;
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
  color: #303133;
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
  background: #f9fafc;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.todo-item:hover {
  background: #f0f2f5;
}

.todo-title {
  flex: 1;
  font-size: 14px;
  color: #606266;
}

/* 会议室列表 */
.room-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.room-item {
  padding: 12px;
  background: #f9fafc;
  border-radius: 8px;
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
  color: #303133;
}

.room-count {
  font-size: 12px;
  color: #909399;
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

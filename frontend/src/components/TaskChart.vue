<!--
  任务统计图表组件 TaskChart.vue
  
  使用 Echarts 绘制饼图展示待办事项各状态的占比：
  - pending: 待处理
  - in_progress: 进行中
  - completed: 已完成
  - cancelled: 已取消
-->

<template>
  <div class="task-chart">
    <!-- 图表标题 -->
    <div class="chart-title">
      <span>任务状态分布</span>
    </div>
    
    <!-- 图表容器 -->
    <div 
      ref="chartRef" 
      class="chart-container"
    ></div>
    
    <!-- 无数据提示 -->
    <div v-if="!hasData" class="no-data">
      <el-empty description="暂无数据" :image-size="80" />
    </div>
  </div>
</template>

<script setup>
/**
 * 任务统计图表组件
 * 
 * 使用 Echarts 绘制饼图展示待办事项统计
 */

import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

// ==================== Props 定义 ====================

const props = defineProps({
  /**
   * 统计数据
   * {
   *   pending: number,      // 待处理
   *   in_progress: number,  // 进行中
   *   completed: number,    // 已完成
   *   cancelled: number     // 已取消
   * }
   */
  data: {
    type: Object,
    default: () => ({
      pending: 0,
      in_progress: 0,
      completed: 0,
      cancelled: 0
    })
  }
})

// ==================== 响应式数据 ====================

/**
 * 图表容器 DOM 引用
 */
const chartRef = ref(null)

/**
 * Echarts 实例
 */
let chartInstance = null

// ==================== 计算属性 ====================

/**
 * 是否有数据
 */
const hasData = computed(() => {
  const { pending, in_progress, completed, cancelled } = props.data
  return (pending || 0) + (in_progress || 0) + (completed || 0) + (cancelled || 0) > 0
})

// ==================== 颜色配置 ====================

/**
 * 状态颜色配置
 */
const colorMap = {
  pending: '#E6A23C',      // 警告色 - 待处理
  in_progress: '#409EFF',  // 主色 - 进行中
  completed: '#67C23A',    // 成功色 - 已完成
  cancelled: '#F56C6C'     // 危险色 - 已取消
}

/**
 * 状态标签配置
 */
const labelMap = {
  pending: '待处理',
  in_progress: '进行中',
  completed: '已完成',
  cancelled: '已取消'
}

// ==================== 方法定义 ====================

/**
 * 初始化图表
 */
function initChart() {
  if (!chartRef.value) return
  
  // 创建 Echarts 实例
  chartInstance = echarts.init(chartRef.value)
  
  // 设置图表配置
  updateChart()
}

/**
 * 更新图表数据和配置
 */
function updateChart() {
  if (!chartInstance) return
  
  // 准备图表数据
  const chartData = [
    { value: props.data.pending || 0, name: labelMap.pending, itemStyle: { color: colorMap.pending } },
    { value: props.data.in_progress || 0, name: labelMap.in_progress, itemStyle: { color: colorMap.in_progress } },
    { value: props.data.completed || 0, name: labelMap.completed, itemStyle: { color: colorMap.completed } },
    { value: props.data.cancelled || 0, name: labelMap.cancelled, itemStyle: { color: colorMap.cancelled } }
  ].filter(item => item.value > 0) // 过滤掉数值为 0 的项
  
  // Echarts 配置项
  const option = {
    // 提示框配置
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: {
        color: '#303133'
      }
    },
    
    // 图例配置
    legend: {
      orient: 'horizontal',
      bottom: '5%',
      left: 'center',
      itemWidth: 12,
      itemHeight: 12,
      itemGap: 16,
      textStyle: {
        fontSize: 12,
        color: '#606266'
      }
    },
    
    // 饼图系列配置
    series: [
      {
        name: '任务状态',
        type: 'pie',
        // 饼图大小和位置
        radius: ['40%', '65%'],
        center: ['50%', '45%'],
        // 避免标签重叠
        avoidLabelOverlap: true,
        // 标签配置
        label: {
          show: true,
          formatter: '{b}\n{c}',
          fontSize: 12,
          color: '#606266'
        },
        // 标签引导线
        labelLine: {
          show: true,
          length: 10,
          length2: 15
        },
        // 高亮状态
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.2)'
          }
        },
        // 数据
        data: chartData
      }
    ]
  }
  
  // 应用配置
  chartInstance.setOption(option)
}

/**
 * 处理窗口大小变化
 * 响应式调整图表大小
 */
function handleResize() {
  chartInstance?.resize()
}

// ==================== 生命周期 ====================

onMounted(() => {
  // 初始化图表
  nextTick(() => {
    initChart()
  })
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  // 移除事件监听
  window.removeEventListener('resize', handleResize)
  
  // 销毁图表实例
  chartInstance?.dispose()
  chartInstance = null
})

// ==================== 监听数据变化 ====================

watch(
  () => props.data,
  () => {
    nextTick(() => {
      updateChart()
    })
  },
  { deep: true }
)
</script>

<style scoped>
/* ==================== 容器样式 ==================== */

.task-chart {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* ==================== 标题样式 ==================== */

.chart-title {
  padding: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

/* ==================== 图表容器 ==================== */

.chart-container {
  flex: 1;
  min-height: 280px;
}

/* ==================== 无数据提示 ==================== */

.no-data {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

/* ==================== 响应式适配 ==================== */

@media (max-width: 768px) {
  .chart-container {
    min-height: 240px;
  }
}
</style>

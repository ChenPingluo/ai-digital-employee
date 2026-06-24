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

let echarts = null
async function getECharts() {
  if (!echarts) {
    echarts = await import('echarts')
  }
  return echarts
}

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

function getCssVar(name) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim()
}

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
  pending: '#00D4FF',      // 电光蓝 - 待处理
  in_progress: '#00FFA3',  // 亮绿 - 进行中
  completed: '#FFB800',    // 亮橙 - 已完成
  cancelled: '#FF4D6A'     // 亮红 - 已取消
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
async function initChart() {
  if (!chartRef.value) return

  // 动态加载 ECharts
  const echartModule = await getECharts()

  // 创建 Echarts 实例
  chartInstance = echartModule.init(chartRef.value)
  
  // 设置图表配置
  updateChart()
}

/**
 * 更新图表数据和配置
 */
function updateChart() {
  if (!chartInstance) return

  const tooltipBg = getCssVar('--tooltip-bg')
  const tooltipBorder = getCssVar('--tooltip-border')
  const tooltipText = getCssVar('--tooltip-text')
  const labelColor = getCssVar('--chart-label-color')
  
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
      backgroundColor: tooltipBg,
      borderColor: tooltipBorder,
      borderWidth: 1,
      textStyle: {
        color: tooltipText
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
        color: labelColor
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
          color: labelColor
        },
        // 标签引导线
        labelLine: {
          show: true,
          length: 10,
          length2: 15,
          lineStyle: {
            color: tooltipBorder
          }
        },
        // 高亮状态
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
            color: tooltipText
          },
          itemStyle: {
            shadowBlur: 20,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 212, 255, 0.4)'
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

function handleThemeChange() {
  updateChart()
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
  window.addEventListener('app-theme-change', handleThemeChange)
})

onUnmounted(() => {
  // 移除事件监听
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('app-theme-change', handleThemeChange)
  
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
  color: var(--text-primary);
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

.no-data :deep(.el-empty__description p) {
  color: var(--text-secondary);
}

/* ==================== 响应式适配 ==================== */

@media (max-width: 768px) {
  .chart-container {
    min-height: 240px;
  }
}
</style>

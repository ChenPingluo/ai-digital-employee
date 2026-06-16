<!--
  会议室使用率图表组件 MeetingChart.vue
  
  使用 Echarts 绘制柱状图展示会议室使用情况：
  - X轴：会议室名称
  - Y轴左：预约次数（柱状图）
  - Y轴右：总时长（折线图）
-->

<template>
  <div class="meeting-chart">
    <!-- 图表标题 -->
    <div class="chart-title">
      <span>会议室使用统计</span>
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
 * 会议室使用率图表组件
 * 
 * 使用 Echarts 绘制混合图表（柱状图 + 折线图）
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
   * 会议室统计数据数组
   * Array<{
   *   room_name: string,         // 会议室名称
   *   reservation_count: number, // 预约次数
   *   total_hours: number        // 总使用时长（小时）
   * }>
   */
  data: {
    type: Array,
    default: () => []
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
  return props.data && props.data.length > 0
})

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
  const axisColor = getCssVar('--chart-axis-color')
  const gridColor = getCssVar('--chart-grid-color')
  const labelColor = getCssVar('--chart-label-color')
  const surfaceColor = getCssVar('--chart-surface-color')
  
  // 提取数据
  const roomNames = props.data.map(item => item.room_name || '未命名')
  const reservationCounts = props.data.map(item => item.reservation_count || 0)
  const totalHours = props.data.map(
    item => item.total_hours || item.total_duration_hours || 0
  )
  
  // Echarts 配置项
  const option = {
    // 提示框配置
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: {
          color: axisColor
        }
      },
      backgroundColor: tooltipBg,
      borderColor: tooltipBorder,
      borderWidth: 1,
      textStyle: {
        color: tooltipText
      },
      formatter: function(params) {
        let result = `<strong>${params[0].axisValue}</strong><br/>`
        params.forEach(param => {
          const unit = param.seriesIndex === 0 ? '次' : '小时'
          result += `${param.marker} ${param.seriesName}: ${param.value} ${unit}<br/>`
        })
        return result
      }
    },
    
    // 图例配置
    legend: {
      data: ['预约次数', '使用时长'],
      bottom: '5%',
      left: 'center',
      itemWidth: 16,
      itemHeight: 10,
      textStyle: {
        fontSize: 12,
        color: labelColor
      }
    },
    
    // 网格配置
    grid: {
      left: '3%',
      right: '4%',
      bottom: '18%',
      top: '10%',
      containLabel: true
    },
    
    // X轴配置
    xAxis: {
      type: 'category',
      data: roomNames,
      axisPointer: {
        type: 'shadow'
      },
      axisLabel: {
        color: axisColor,
        fontSize: 12,
        rotate: roomNames.length > 5 ? 30 : 0,
        interval: 0
      },
      axisLine: {
        lineStyle: {
          color: tooltipBorder
        }
      }
    },
    
    // Y轴配置（双Y轴）
    yAxis: [
      {
        // 左侧 Y 轴 - 预约次数
        type: 'value',
        name: '预约次数',
        position: 'left',
        alignTicks: true,
        axisLabel: {
          formatter: '{value}',
          color: axisColor
        },
        axisLine: {
          show: true,
          lineStyle: {
            color: tooltipBorder
          }
        },
        splitLine: {
          lineStyle: {
            color: gridColor,
            type: 'dashed'
          }
        }
      },
      {
        // 右侧 Y 轴 - 使用时长
        type: 'value',
        name: '时长(小时)',
        position: 'right',
        alignTicks: true,
        axisLabel: {
          formatter: '{value}h',
          color: axisColor
        },
        axisLine: {
          show: true,
          lineStyle: {
            color: tooltipBorder
          }
        },
        splitLine: {
          show: false
        }
      }
    ],
    
    // 数据系列
    series: [
      {
        name: '预约次数',
        type: 'bar',
        yAxisIndex: 0,
        barWidth: '40%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#00D4FF' },
            { offset: 1, color: 'rgba(0, 212, 255, 0.2)' }
          ]),
          borderRadius: [4, 4, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#33DDFF' },
              { offset: 1, color: 'rgba(0, 212, 255, 0.4)' }
            ])
          }
        },
        data: reservationCounts
      },
      {
        name: '使用时长',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: {
          width: 3,
          color: '#00FFA3'
        },
        itemStyle: {
          color: '#00FFA3',
          borderWidth: 2,
          borderColor: surfaceColor
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 255, 163, 0.1)' },
            { offset: 1, color: 'rgba(0, 255, 163, 0)' }
          ])
        },
        data: totalHours
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

.meeting-chart {
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

/**
 * 触摸滑动手势 Composable
 *
 * 检测目标元素上的左右滑动手势，
 * 区分横向滑动与纵向滚动。
 *
 * @param {Ref<HTMLElement>} elRef - 目标元素引用
 * @param {(direction: 'left'|'right') => void} onSwipe - 滑动回调
 * @param {{ threshold?: number }} options
 */
import { onMounted, onUnmounted } from 'vue'

export function useSwipe(elRef, onSwipe, { threshold = 80 } = {}) {
  let touchStartX = 0
  let touchStartY = 0
  let touchStartTime = 0

  function handleTouchStart(event) {
    const touch = event.touches[0]
    touchStartX = touch.clientX
    touchStartY = touch.clientY
    touchStartTime = Date.now()
  }

  function handleTouchEnd(event) {
    const touch = event.changedTouches[0]
    const deltaX = touch.clientX - touchStartX
    const deltaY = touch.clientY - touchStartY
    const elapsed = Date.now() - touchStartTime

    // 忽略长时间按压（> 500ms）
    if (elapsed > 500) return

    // 忽略对角线滑动（优先竖向滚动）
    if (Math.abs(deltaY) > Math.abs(deltaX) * 1.5) return

    // 横向滑动距离必须超过阈值
    if (Math.abs(deltaX) < threshold) return

    const direction = deltaX > 0 ? 'right' : 'left'

    // 右滑仅在页面已滚动到顶部时响应（避免与滚动冲突）
    if (direction === 'right' && elRef.value) {
      if (elRef.value.scrollTop > 5) return
    }

    onSwipe(direction)
  }

  onMounted(() => {
    if (elRef.value) {
      elRef.value.addEventListener('touchstart', handleTouchStart, { passive: true })
      elRef.value.addEventListener('touchend', handleTouchEnd, { passive: true })
    }
  })

  onUnmounted(() => {
    if (elRef.value) {
      elRef.value.removeEventListener('touchstart', handleTouchStart)
      elRef.value.removeEventListener('touchend', handleTouchEnd)
    }
  })
}

/**
 * 键盘快捷键 Composable
 *
 * 注册全局键盘快捷键，自动管理生命周期。
 * 支持 Ctrl/Meta 组合键，智能区分输入框内外场景。
 *
 * @param {Array<{ key: string, ctrl?: boolean, meta?: boolean, handler: Function, allowInInput?: boolean }>} shortcuts
 */
import { onMounted, onUnmounted } from 'vue'

export function useKeyboardShortcuts(shortcuts) {
  function handleKeydown(event) {
    const target = event.target
    const isInputFocused =
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable

    for (const shortcut of shortcuts) {
      // 检查按键是否匹配
      if (event.key.toLowerCase() !== shortcut.key.toLowerCase()) {
        continue
      }

      // 检查 Ctrl/Cmd 修饰键
      const needsCtrl = shortcut.ctrl || shortcut.meta
      const hasModifier = event.ctrlKey || event.metaKey
      if (needsCtrl && !hasModifier) continue
      if (!needsCtrl && hasModifier && shortcut.key === 'Escape') {
        // Escape 允许带 Ctrl
      } else if (!needsCtrl && hasModifier) {
        continue
      }

      // 输入框内只触发明确允许的快捷键
      if (isInputFocused && !shortcut.allowInInput) {
        continue
      }

      event.preventDefault()
      shortcut.handler(event)
      return
    }
  }

  onMounted(() => {
    document.addEventListener('keydown', handleKeydown)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeydown)
  })
}

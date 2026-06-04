/**
 * 主题状态管理 Store
 *
 * 提供深色/浅色界面切换能力，并持久化到本地存储。
 */

import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const STORAGE_KEY = 'ui_theme'
const DEFAULT_THEME = 'dark'
const VALID_THEMES = new Set(['dark', 'light'])

function normalizeTheme(theme) {
  return VALID_THEMES.has(theme) ? theme : DEFAULT_THEME
}

function applyThemeToDocument(theme) {
  const nextTheme = normalizeTheme(theme)
  document.documentElement.setAttribute('data-theme', nextTheme)
  document.documentElement.style.colorScheme = nextTheme
}

function notifyThemeChanged(theme) {
  window.dispatchEvent(
    new CustomEvent('app-theme-change', {
      detail: { theme }
    })
  )
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref(normalizeTheme(localStorage.getItem(STORAGE_KEY)))

  const isDark = computed(() => theme.value === 'dark')

  function setTheme(nextTheme) {
    const normalizedTheme = normalizeTheme(nextTheme)
    theme.value = normalizedTheme
    localStorage.setItem(STORAGE_KEY, normalizedTheme)
    applyThemeToDocument(normalizedTheme)
    notifyThemeChanged(normalizedTheme)
  }

  function toggleTheme() {
    setTheme(isDark.value ? 'light' : 'dark')
  }

  function initializeTheme() {
    setTheme(theme.value)
  }

  return {
    theme,
    isDark,
    setTheme,
    toggleTheme,
    initializeTheme
  }
})

export default useThemeStore

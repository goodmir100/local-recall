import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import en from '../locales/en.json'
import ru from '../locales/ru.json'

export type Language = 'en' | 'ru'
export type Theme = 'light' | 'dark'
type Key = keyof typeof en

const storedTheme = localStorage.getItem('local-recall-theme')
const storedLanguage = localStorage.getItem('local-recall-language')
const media = window.matchMedia('(prefers-color-scheme: dark)')

export const usePreferencesStore = defineStore('preferences', () => {
  const theme = ref<Theme>(storedTheme === 'light' || storedTheme === 'dark' ? storedTheme : media.matches ? 'dark' : 'light')
  const language = ref<Language>(storedLanguage === 'ru' ? 'ru' : 'en')
  const followsSystem = ref(!storedTheme)
  const locale = computed(() => language.value === 'ru' ? 'ru-RU' : 'en-US')

  function t(key: Key, params?: Record<string, string | number>) {
    const dictionary = language.value === 'ru' ? ru : en
    let value: string = dictionary[key] ?? en[key]
    for (const [name, replacement] of Object.entries(params ?? {})) {
      value = value.split(`{${name}}`).join(String(replacement))
    }
    return value
  }
  function setTheme(value: Theme) {
    followsSystem.value = false
    theme.value = value
    localStorage.setItem('local-recall-theme', value)
  }
  function toggleTheme() { setTheme(theme.value === 'dark' ? 'light' : 'dark') }
  function setLanguage(value: Language) {
    language.value = value
    localStorage.setItem('local-recall-language', value)
  }
  function onSystemChange(event: MediaQueryListEvent) {
    if (followsSystem.value) theme.value = event.matches ? 'dark' : 'light'
  }
  media.addEventListener('change', onSystemChange)
  watch(theme, value => {
    document.documentElement.classList.toggle('dark', value === 'dark')
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', value === 'dark' ? '#0b1018' : '#f5f8f7')
  }, { immediate: true })
  watch(language, value => { document.documentElement.lang = value }, { immediate: true })

  return { theme, language, locale, t, setTheme, toggleTheme, setLanguage }
})

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Archive, Bot, ChevronRight, Command, LockKeyhole, Menu, Moon, Search, Settings2, ShieldCheck, Sun, X } from 'lucide-vue-next'
import SearchBar from './components/SearchBar.vue'
import Timeline from './components/Timeline.vue'
import ScreenshotViewer from './components/ScreenshotViewer.vue'
import SpotlightModal from './components/SpotlightModal.vue'
import AIChat from './components/AIChat.vue'
import Settings from './components/Settings.vue'
import { api, type Capture, type Settings as SettingsType } from './services/api'
import { usePreferencesStore } from './stores/preferences'

const preferences = usePreferencesStore()
const page = ref<'history'|'chat'>('history')
const query = ref(''), items = ref<Capture[]>([]), settings = ref<SettingsType|null>(null)
const selected = ref<{id:number}|null>(null), selectedHour = ref<number|null>(null)
const error = ref<''|'serviceUnavailable'|'captureError'|'settingsError'>(''), loading = ref(true), showSettings = ref(false), showSpotlight = ref(false), drawerOpen = ref(false)
const errorMessage = computed(() => error.value ? preferences.t(error.value) : '')
const mobileQuery = window.matchMedia('(max-width: 800px)')
const isMobile = ref(mobileQuery.matches)
const drawerCloseButton = ref<HTMLButtonElement|null>(null)
const menuButton = ref<HTMLButtonElement|null>(null)
const isSearching = computed(() => query.value.trim().length > 0)
const searchMode = ref<'semantic'|'text'>('semantic')
let timer:number|undefined, debounce:number|undefined, loadId = 0

function hourRange(hour:number):[string,string] {
  const start = new Date()
  start.setHours(hour,0,0,0)
  const end = new Date(start)
  end.setHours(end.getHours()+1)
  return [start.toISOString(),end.toISOString()]
}
async function load() {
  const current = ++loadId
  loading.value = true
  try {
    let result:Capture[]
    if (isSearching.value) result = await api.search(query.value,50,searchMode.value)
    else if (selectedHour.value !== null) result = await api.timeline(...hourRange(selectedHour.value))
    else result = await api.timeline()
    if (current === loadId) { items.value = result; error.value = '' }
  } catch {
    if (current === loadId) error.value = 'serviceUnavailable'
  } finally { if (current === loadId) loading.value = false }
}
async function refresh() { try { settings.value = await api.settings() } catch { /* Local status is reflected by unavailable controls. */ } }
async function toggleCapture() {
  if (!settings.value) return
  try { settings.value = await api.update({capture_enabled:!settings.value.capture_enabled}); if (settings.value.capture_enabled) await load() }
  catch { error.value = 'captureError' }
}
async function save(value:Partial<SettingsType>) {
  try { settings.value = await api.update(value); showSettings.value = false }
  catch { error.value = 'settingsError' }
}
function scrub(hour:number|null) { selectedHour.value = hour; query.value = ''; load() }
function navigate(destination:'history'|'chat') { page.value = destination; drawerOpen.value = false }
function trapDrawerFocus(event:KeyboardEvent) {
  if (event.key !== 'Tab' || !isMobile.value) return
  const focusable = Array.from(document.querySelectorAll<HTMLElement>('.sidebar button'))
  const first = focusable[0], last = focusable[focusable.length-1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}
function handleKeyDown(event:KeyboardEvent) {
  if ((event.altKey && event.code === 'Space') || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k')) {
    event.preventDefault()
    showSpotlight.value = !showSpotlight.value
  }
  if (event.key === 'Escape') { selected.value = null; showSettings.value = false; showSpotlight.value = false; drawerOpen.value = false }
}
watch(query,() => { clearTimeout(debounce); debounce = window.setTimeout(load,220) })
watch(searchMode,() => { if (isSearching.value) load() })
watch(drawerOpen, async open => { if (open) { await nextTick(); drawerCloseButton.value?.focus() } else if (isMobile.value) menuButton.value?.focus() })
function onMobileChange(event:MediaQueryListEvent) { isMobile.value = event.matches; if (!event.matches) drawerOpen.value = false }
onMounted(() => { load(); refresh(); timer = window.setInterval(() => { if (page.value === 'history' && !isSearching.value) load(); refresh() },10000); window.addEventListener('keydown',handleKeyDown,true); mobileQuery.addEventListener('change',onMobileChange) })
onUnmounted(() => { clearInterval(timer); clearTimeout(debounce); window.removeEventListener('keydown',handleKeyDown,true); mobileQuery.removeEventListener('change',onMobileChange) })
</script>

<template>
  <div class="app-shell min-h-screen">
    <Transition name="fade"><button v-if="drawerOpen" class="drawer-scrim" :aria-label="preferences.t('navClose')" @click="drawerOpen=false"></button></Transition>
    <aside class="sidebar" :class="{'drawer-open':drawerOpen}" :inert="isMobile && !drawerOpen" @keydown="trapDrawerFocus">
      <div class="brand-row"><div class="brand"><span class="brand-mark"><Archive :size="20" :stroke-width="2.2"/></span><span>local<span class="brand-light"> recall</span></span></div><button ref="drawerCloseButton" class="icon-button drawer-close" :aria-label="preferences.t('navClose')" @click="drawerOpen=false"><X :size="19"/></button></div>
      <div class="side-label">{{preferences.t('navWorkspace')}}</div>
      <nav :aria-label="preferences.t('navWorkspace')" class="side-nav">
        <button class="nav-item" :class="{active:page==='history'}" :aria-current="page==='history'?'page':undefined" @click="navigate('history')"><Archive :size="18"/><span>{{preferences.t('navTimeline')}}</span><span class="nav-count">{{items.length}}</span></button>
        <button class="nav-item" :class="{active:page==='chat'}" :aria-current="page==='chat'?'page':undefined" @click="navigate('chat')"><Bot :size="18"/><span>{{preferences.t('navAssistant')}}</span><ChevronRight :size="15" class="nav-chevron"/></button>
      </nav>
      <div class="privacy-note rounded-xl border border-white/10 backdrop-blur-md"><span class="privacy-icon"><LockKeyhole :size="17"/></span><strong>{{preferences.t('privacyTitle')}}</strong><p>{{preferences.t('privacyBody')}}</p><span class="local-status"><span class="status-dot"></span>{{preferences.t('localOnly')}}</span></div>
      <div class="sidebar-bottom"><button class="nav-item" @click="showSettings=true;drawerOpen=false"><Settings2 :size="18"/><span>{{preferences.t('navSettings')}}</span></button><div class="version">LOCAL RECALL <span>v0.2</span></div></div>
    </aside>
    <main class="main">
      <header class="topbar backdrop-blur-md"><div class="topbar-start"><button ref="menuButton" class="icon-button menu-toggle" :aria-label="preferences.t('navOpen')" :aria-expanded="drawerOpen" @click="drawerOpen=true"><Menu :size="21"/></button><div class="breadcrumb">{{preferences.t('navWorkspace')}} <span>/</span> <b>{{preferences.t(page==='history'?'navTimeline':'navAssistant')}}</b></div></div><div class="top-actions"><span class="local-pill"><ShieldCheck :size="16"/>{{preferences.t('onDevice')}}</span><label class="language-picker"><span class="sr-only">{{preferences.t('language')}}</span><select :value="preferences.language" :aria-label="preferences.t('language')" @change="preferences.setLanguage(($event.target as HTMLSelectElement).value as 'en'|'ru')"><option value="en">EN</option><option value="ru">RU</option></select></label><button class="icon-button theme-toggle" :aria-label="preferences.t('toggleTheme')" :title="preferences.t('toggleTheme')" @click="preferences.toggleTheme()"><Sun v-if="preferences.theme==='dark'" :size="18"/><Moon v-else :size="18"/></button><button class="capture-toggle" :class="{recording:settings?.capture_enabled}" :disabled="!settings" :title="settings ? preferences.t(settings.capture_enabled?'pauseCapture':'startCapture') : preferences.t('offline')" @click="toggleCapture"><span class="status-dot"></span><span>{{preferences.t(!settings?'offline':settings.capture_enabled?'live':'paused')}}</span></button></div></header>
      <section v-show="page==='history'" class="content"><div class="hero rounded-xl border border-white/10 backdrop-blur-md"><div class="hero-copy"><div class="eyebrow"><span class="eyebrow-line"></span>{{preferences.t('heroEyebrow')}}</div><h1>{{preferences.t('heroTitle')}}</h1><p>{{preferences.t('heroDescription')}}</p><div class="hero-meta"><span><LockKeyhole :size="15"/>{{preferences.t('heroPrivate')}}</span><span class="hero-meta-separator"></span><span>{{preferences.t('heroLocal')}}</span></div></div><button class="hero-search" @click="showSpotlight=true"><span class="hero-search-icon"><Search :size="21"/></span><span><strong>{{preferences.t('heroShortcut')}}</strong><small>{{preferences.t('heroShortcutHint')}}</small></span><kbd><Command :size="12"/> K</kbd></button></div>
        <SearchBar v-model="query" @open-spotlight="showSpotlight=true"/>
        <div class="search-filters" role="group" :aria-label="preferences.t('searchMode')"><button :class="{active:searchMode==='semantic'}" :aria-pressed="searchMode==='semantic'" @click="searchMode='semantic'">{{preferences.t('semantic')}}</button><button :class="{active:searchMode==='text'}" :aria-pressed="searchMode==='text'" @click="searchMode='text'">{{preferences.t('text')}}</button></div>
        <div class="section-heading"><div><h2>{{preferences.t(isSearching?'searchResults':selectedHour===null?'recentCaptures':'todayAt',selectedHour===null?undefined:{hour:String(selectedHour).padStart(2,'0')})}}</h2><span>{{isSearching?preferences.t('matches',{count:items.length}):preferences.t(selectedHour===null?'privateTimeline':'framesThisHour')}}</span></div><button v-if="isSearching" class="text-button" @click="query=''">{{preferences.t('clearSearch')}}</button><span v-else class="today"><span class="status-dot"></span>{{preferences.t('updating')}}</span></div>
        <div v-if="errorMessage" class="error-banner" role="alert">{{errorMessage}}</div><Timeline :items="items" :loading="loading" :show-slider="!isSearching" :selected-hour="selectedHour" @select="selected=$event" @scrub="scrub"/><footer><LockKeyhole :size="14"/>{{preferences.t('storedLocally')}}</footer></section>
      <AIChat v-show="page==='chat'" @select="selected=$event"/>
    </main>
    <ScreenshotViewer :capture="selected" @close="selected=null"/>
    <SpotlightModal :open="showSpotlight" @close="showSpotlight=false" @select="selected=$event"/>
    <Transition name="modal"><Settings v-if="showSettings" :settings="settings" @save="save" @close="showSettings=false"/></Transition>
  </div>
</template>

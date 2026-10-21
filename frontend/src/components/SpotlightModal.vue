<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { Search, X } from 'lucide-vue-next'
import { api, type Capture } from '../services/api'
import { usePreferencesStore } from '../stores/preferences'
const preferences = usePreferencesStore()

const props = defineProps<{open:boolean}>()
const emit = defineEmits<{close:[];select:[item:Capture]}>()
const query = ref('')
const results = ref<Capture[]>([])
const pending = ref(false)
const active = ref(0)
const inputRef = ref<HTMLInputElement|null>(null)
const dialog = ref<HTMLElement|null>(null)
let debounce:number|undefined
let requestId = 0
let priorFocus:Element|null = null

watch(() => props.open, async open => {
  if (open) {
    priorFocus = document.activeElement
    query.value = ''
    results.value = []
    await nextTick()
    inputRef.value?.focus()
  } else if (priorFocus instanceof HTMLElement) priorFocus.focus()
})
watch(query, value => {
  clearTimeout(debounce)
  const current = ++requestId
  results.value = []
  active.value = 0
  pending.value = Boolean(value.trim())
  if (!value.trim()) return
  debounce = window.setTimeout(async () => {
    try {
      const found = await api.search(value,8)
      if (current === requestId) results.value = found
    } catch { if (current === requestId) results.value = [] }
    finally { if (current === requestId) pending.value = false }
  },180)
})
function select(item:Capture) { emit('select',item); emit('close') }
function keydown(event:KeyboardEvent) {
  if (event.key === 'Tab') {
    const focusable = Array.from(dialog.value?.querySelectorAll<HTMLElement>('input,button') || [])
    const first = focusable[0], last = focusable[focusable.length-1]
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
  }
  if (event.key === 'ArrowDown') { event.preventDefault(); active.value = Math.min(active.value+1,results.value.length-1) }
  if (event.key === 'ArrowUp') { event.preventDefault(); active.value = Math.max(active.value-1,0) }
  if (event.key === 'Enter' && results.value[active.value]) { event.preventDefault(); select(results.value[active.value]) }
  if (event.key === 'Escape') { event.preventDefault(); emit('close') }
}
</script>

<template>
  <Transition name="modal"><div v-if="open" class="spotlight-backdrop" @click.self="emit('close')">
    <section ref="dialog" class="spotlight" role="dialog" aria-modal="true" :aria-label="preferences.t('spotlightTitle')" @keydown="keydown">
      <div class="spotlight-input"><Search :size="20" aria-hidden="true"/><input ref="inputRef" v-model="query" :aria-label="preferences.t('searchLabel')" :placeholder="preferences.t('spotlightPlaceholder')" autocomplete="off" aria-controls="spotlight-results" :aria-expanded="results.length>0"><button class="icon-button" :aria-label="preferences.t('closeQuickSearch')" @click="emit('close')"><X :size="18"/></button></div>
      <div id="spotlight-results" class="spotlight-results" role="listbox">
        <p v-if="pending" class="spotlight-message">{{preferences.t('spotlightSearching')}}</p>
        <p v-else-if="query && !results.length" class="spotlight-message">{{preferences.t('spotlightNoMatches')}}</p>
        <p v-else-if="!query" class="spotlight-message">{{preferences.t('spotlightInstructions')}}</p>
        <button v-for="(item,index) in results" :key="item.id" class="spotlight-result" :class="{active:active===index}" role="option" :aria-selected="active===index" @mouseenter="active=index" @click="select(item)"><img :src="api.image(item.id)" alt=""><span><strong>{{item.window_title || item.process_name || preferences.t('untitledWindow')}}</strong><small>{{new Date(item.captured_at).toLocaleString(preferences.locale)}} · {{item.process_name}}</small></span></button>
      </div>
      <div class="spotlight-footer"><span>{{preferences.t('navigate')}}</span><span>{{preferences.t('enterOpen')}}</span><span>{{preferences.t('escClose')}}</span></div>
    </section>
  </div></Transition>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { Capture } from '../services/api'
import { api } from '../services/api'
import { Clock3 } from 'lucide-vue-next'
import { usePreferencesStore } from '../stores/preferences'
const preferences = usePreferencesStore()

const props = defineProps<{items:Capture[];loading:boolean;showSlider:boolean;selectedHour:number|null}>()
const emit = defineEmits<{select:[item:Capture];scrub:[hour:number|null]}>()
const hours = ref<number[]>(Array(24).fill(0))
const thumb = ref(new Date().getHours())
let interval:number|undefined

function dayRange() {
  const start = new Date()
  start.setHours(0,0,0,0)
  const end = new Date(start)
  end.setDate(end.getDate()+1)
  return {start:start.toISOString(),end:end.toISOString()}
}
async function refreshActivity() {
  const {start,end} = dayRange()
  try { hours.value = (await api.activity(start,end,-new Date().getTimezoneOffset())).hours } catch { /* Timeline remains usable without histogram */ }
}
function scrub(event:Event) {
  thumb.value = Number((event.target as HTMLInputElement).value)
  emit('scrub',thumb.value)
}
function label(hour:number) { return `${String(hour).padStart(2,'0')}:00` }

watch(() => props.showSlider, visible => { if (visible) refreshActivity() })
onMounted(() => { refreshActivity(); interval = window.setInterval(refreshActivity,30000) })
onUnmounted(() => clearInterval(interval))
</script>

<template>
  <section class="timeline">
    <div v-if="showSlider" class="time-travel">
      <div class="time-travel-heading"><div><strong><Clock3 :size="17"/>{{preferences.t('exploreToday')}}</strong><span>{{preferences.t('activityByHour')}}</span></div><button v-if="selectedHour!==null" class="text-button" @click="emit('scrub',null)">{{preferences.t('showRecent')}}</button><span v-else class="time-prompt">{{preferences.t('dragToHour')}}</span></div>
      <div class="heatmap" aria-hidden="true"><span v-for="(count,index) in hours" :key="index" :style="{height:`${Math.max(8,count/Math.max(...hours,1)*100)}%`}" :class="{selected:selectedHour===index}" :title="`${label(index)}: ${preferences.t('frames',{count})}`"></span></div>
      <input class="time-range" type="range" min="0" max="23" step="1" :value="selectedHour ?? thumb" :aria-valuetext="label(selectedHour ?? thumb)" :aria-label="preferences.t('jumpToHour')" @input="scrub">
      <div class="time-ticks"><span>00:00</span><span>{{selectedHour===null?preferences.t('today'):`${label(selectedHour)}–${label((selectedHour+1)%24)}`}}</span><span>23:00</span></div>
    </div>
    <div v-if="loading" class="empty"><span class="spinner"></span><p>{{preferences.t('readingHistory')}}</p></div>
    <div v-else-if="items.length" class="capture-grid"><button v-for="item in items" :key="item.id" class="capture transition-all duration-200 hover:scale-[1.02]" @click="emit('select',item)"><img :src="api.image(item.id)" alt="" loading="lazy"><div class="capture-copy"><time>{{new Date(item.captured_at).toLocaleTimeString(preferences.locale, {hour:'2-digit',minute:'2-digit'})}}</time><strong>{{item.window_title || item.process_name || preferences.t('untitledWindow')}}</strong><span>{{item.process_name}}</span></div></button></div>
    <div v-else class="empty"><Clock3 :size="30"/><h2>{{preferences.t(selectedHour===null?'timelineEmpty':'hourEmpty')}}</h2><p>{{preferences.t(selectedHour===null?'timelineEmptyHint':'hourEmptyHint')}}</p></div>
  </section>
</template>

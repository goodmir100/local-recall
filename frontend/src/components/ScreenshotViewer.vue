<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Copy, X } from 'lucide-vue-next'
import { api, type CaptureDetails, type OCRBlock } from '../services/api'
import { usePreferencesStore } from '../stores/preferences'
const preferences = usePreferencesStore()

const props = defineProps<{capture:{id:number}|null}>()
const emit = defineEmits<{close:[]}>()
const details = ref<CaptureDetails|null>(null)
const imageSize = ref({width:1,height:1})
const loading = ref(false)
const error = ref('')
const toast = ref('')
const closeButton = ref<HTMLButtonElement|null>(null)
const viewer = ref<HTMLElement|null>(null)
const renderedWidth = ref(0)
let toastTimer:number|undefined
let requestId = 0
let priorFocus:Element|null = null

watch(() => props.capture?.id, async id => {
  const current = ++requestId
  details.value = null
  renderedWidth.value = 0
  error.value = ''
  if (!id) { if (priorFocus instanceof HTMLElement) priorFocus.focus(); priorFocus = null; return }
  priorFocus = document.activeElement
  loading.value = true
  await nextTick()
  closeButton.value?.focus()
  try {
    const result = await api.details(id)
    if (current === requestId) details.value = result
  } catch (cause) {
    if (current === requestId) error.value = cause instanceof Error ? cause.message : preferences.t('couldNotLoadScreenshot')
  } finally {
    if (current === requestId) loading.value = false
  }
}, {immediate:true})

function imageLoaded(event:Event) {
  const image = event.target as HTMLImageElement
  imageSize.value = {width:image.naturalWidth,height:image.naturalHeight}
  resizeImage()
}
function resizeImage() {
  const {width,height} = imageSize.value
  if (width <= 1 || height <= 1) return
  renderedWidth.value = Math.min(width,Math.max(1,(viewer.value?.clientWidth ?? window.innerWidth*.9)-44),window.innerHeight*.6*width/height)
}
onMounted(() => window.addEventListener('resize',resizeImage))
onUnmounted(() => { window.removeEventListener('resize',resizeImage); clearTimeout(toastTimer) })
async function copy(text:string) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    toast.value = preferences.t('copied')
  } catch {
    toast.value = preferences.t('clipboardUnavailable')
  }
  clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => toast.value = '', 2500)
}
function box(block:OCRBlock) {
  const [x1,y1,x2,y2] = block.bbox
  return {x:x1,y:y1,width:Math.max(x2-x1,1),height:Math.max(y2-y1,1)}
}
function trapFocus(event:KeyboardEvent) {
  if (event.key !== 'Tab') return
  const focusable = Array.from(viewer.value?.querySelectorAll<HTMLElement>('button,[tabindex="0"]') || [])
  const first = focusable[0], last = focusable[focusable.length-1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}
</script>

<template>
  <Transition name="modal"><div v-if="capture" class="viewer-backdrop" @click.self="emit('close')">
    <section ref="viewer" class="viewer" role="dialog" aria-modal="true" :aria-label="preferences.t('screenshotDetails')" @keydown="trapFocus">
      <button ref="closeButton" class="icon-button close" :aria-label="preferences.t('closeDetails')" @click="emit('close')"><X :size="18"/></button>
      <div v-if="loading" class="viewer-state">{{preferences.t('loadingScreenshot')}}</div>
      <div v-else-if="error" class="error-banner">{{error}}</div>
      <template v-else-if="details">
        <div class="viewer-image-wrap">
          <div class="viewer-image" :style="{width:renderedWidth ? `${renderedWidth}px` : '100%'}">
            <img :src="api.image(details.id)" :alt="preferences.t('capturedScreen')" @load="imageLoaded">
            <svg v-if="details.ocr_blocks.length" class="ocr-overlay" :viewBox="`0 0 ${imageSize.width} ${imageSize.height}`" preserveAspectRatio="none" :aria-label="preferences.t('recognizedRegions')">
              <rect v-for="(block,index) in details.ocr_blocks" :key="index" v-bind="box(block)" role="button" tabindex="0" :aria-label="preferences.t('copyText',{text:block.text})" @click="copy(block.text)" @keydown.enter.prevent="copy(block.text)" @keydown.space.prevent="copy(block.text)"><title>{{block.text}}</title></rect>
            </svg>
          </div>
        </div>
        <div class="viewer-info"><div><h2>{{details.window_title || details.process_name || preferences.t('untitledWindow')}}</h2><p class="muted">{{new Date(details.captured_at).toLocaleString(preferences.locale)}} · {{details.process_name}}</p></div><button class="primary" :disabled="!details.ocr_text" @click="copy(details.ocr_text)"><Copy :size="14"/> {{preferences.t('copyAll')}}</button></div>
        <p class="viewer-hint">{{preferences.t('copyHint')}}</p>
        <pre>{{details.ocr_text || preferences.t('noRecognizedText')}}</pre>
      </template>
      <div v-if="toast" class="copy-toast" role="status">{{toast}}</div>
    </section>
  </div></Transition>
</template>

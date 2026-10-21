<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { Bot, Send, Square } from 'lucide-vue-next'
import { api, type SourceScreenshot } from '../services/api'
import { usePreferencesStore } from '../stores/preferences'
const preferences = usePreferencesStore()

type Message = { role:'user'|'assistant'; text:string; sources:SourceScreenshot[]; pending?:boolean }
const emit = defineEmits<{select:[source:SourceScreenshot]}>()
const models = ref<string[]>([])
const model = ref('')
const modelError = ref('')
const prompt = ref('')
const messages = ref<Message[]>([])
const sending = ref(false)
const thread = ref<HTMLElement|null>(null)
let controller:AbortController|null = null

async function loadModels() {
  modelError.value = ''
  try {
    models.value = (await api.models()).models
    if (!models.value.length) modelError.value = preferences.t('noModels')
    else if (!models.value.includes(model.value)) model.value = models.value[0]
  } catch (error) { modelError.value = error instanceof TypeError ? preferences.t('startServices') : error instanceof Error ? error.message : preferences.t('ollamaUnavailable') }
}
function scrollEnd() { requestAnimationFrame(() => { if (thread.value) thread.value.scrollTop = thread.value.scrollHeight }) }
async function send() {
  const query = prompt.value.trim()
  if (!query || sending.value || !model.value) return
  prompt.value = ''
  messages.value.push({role:'user',text:query,sources:[]})
  const reply = reactive<Message>({role:'assistant',text:'',sources:[],pending:true})
  messages.value.push(reply)
  sending.value = true
  controller = new AbortController()
  scrollEnd()
  try {
    await api.chat(query,model.value,(event,data) => {
      if (event==='sources') reply.sources = (data as {source_screenshots:SourceScreenshot[]}).source_screenshots
      if (event==='token') reply.text += data as string
      if (event==='error') reply.text += `\n${String(data)}`
      scrollEnd()
    },controller.signal)
  } catch (error) {
    if ((error as Error).name !== 'AbortError') reply.text += `\n${error instanceof Error ? error.message : preferences.t('chatFailed')}`
  } finally {
    const wasAborted = controller?.signal.aborted
    reply.pending = false
    sending.value = false
    controller = null
    if (!reply.text.trim()) reply.text = preferences.t(wasAborted ? 'stopped' : 'noAnswer')
    scrollEnd()
  }
}
function stop() { controller?.abort() }
onMounted(loadModels)
onUnmounted(stop)
</script>

<template>
  <section class="chat-page">
    <header class="chat-heading"><div><div class="eyebrow"><span class="eyebrow-line"></span>{{preferences.t('assistantEyebrow')}}</div><h1>{{preferences.t('assistantTitle')}}</h1><p>{{preferences.t('assistantDescription')}}</p></div><label class="model-picker">{{preferences.t('model')}}<select v-model="model" :disabled="!models.length"><option v-for="item in models" :key="item" :value="item">{{item}}</option></select></label></header>
    <div v-if="modelError" class="error-banner">{{modelError}} <button class="text-button" @click="loadModels">{{preferences.t('retry')}}</button></div>
    <div ref="thread" class="chat-thread" aria-live="polite">
      <div v-if="!messages.length" class="chat-welcome"><span class="chat-welcome-icon"><Bot :size="29"/></span><h2>{{preferences.t('assistantWelcome')}}</h2><p>{{preferences.t('assistantExample')}}</p></div>
      <article v-for="(message,index) in messages" :key="index" class="chat-message" :class="message.role"><div class="chat-avatar"><Bot v-if="message.role==='assistant'" :size="17"/><span v-else>{{preferences.t('you')}}</span></div><div class="chat-body"><div class="chat-text">{{message.text || (message.pending?preferences.t('thinking'):'')}}</div><div v-if="message.sources.length" class="chat-sources"><span>{{preferences.t('sources')}}</span><button v-for="source in message.sources" :key="source.id" class="source-card" @click="emit('select',source)"><img :src="api.image(source.id)" alt=""><span><strong>{{source.window_title || source.process_name || preferences.t('screenshot')}}</strong><small>{{new Date(source.captured_at).toLocaleString(preferences.locale)}}</small></span></button></div></div></article>
    </div>
    <form class="chat-compose" @submit.prevent="send"><textarea v-model="prompt" :aria-label="preferences.t('askLabel')" :placeholder="preferences.t('askPlaceholder')" rows="2" :disabled="!model" @keydown.enter.exact.prevent="send"></textarea><button v-if="sending" type="button" class="primary" :aria-label="preferences.t('stopGenerating')" @click="stop"><Square :size="15"/> {{preferences.t('stop')}}</button><button v-else type="submit" class="primary" :disabled="!prompt.trim() || !model"><Send :size="15"/> {{preferences.t('send')}}</button></form>
  </section>
</template>

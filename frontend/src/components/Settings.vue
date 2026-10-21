<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import type { Settings as SettingsType } from '../services/api'
import { Moon, Sun, X } from 'lucide-vue-next'
import { usePreferencesStore } from '../stores/preferences'
const preferences = usePreferencesStore()
const props=defineProps<{settings:SettingsType|null}>()
const emit=defineEmits<{save:[settings:Partial<SettingsType>];close:[]}>()
const interval=ref(5), ignored=ref('1Password.exe, KeePass.exe, KeePassXC.exe')
const panel = ref<HTMLElement|null>(null)
const closeButton = ref<HTMLButtonElement|null>(null)
let priorFocus:Element|null = null
watch(()=>props.settings,value=>{if(value){interval.value=value.capture_interval_seconds;ignored.value=value.ignored_processes.join(', ')}},{immediate:true})
function save(){emit('save',{capture_interval_seconds:interval.value,ignored_processes:ignored.value.split(',').map(s=>s.trim()).filter(Boolean)})}
function trapFocus(event:KeyboardEvent){
  if(event.key!=='Tab') return
  const focusable=Array.from(panel.value?.querySelectorAll<HTMLElement>('button,input,textarea,select')||[])
  const first=focusable[0],last=focusable[focusable.length-1]
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus()}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus()}
}
onMounted(async()=>{priorFocus=document.activeElement;await nextTick();closeButton.value?.focus()})
onUnmounted(()=>{if(priorFocus instanceof HTMLElement)priorFocus.focus()})
</script>
<template><div class="viewer-backdrop" @click.self="$emit('close')"><section ref="panel" class="settings-panel" role="dialog" aria-modal="true" aria-labelledby="settings-title" @keydown="trapFocus"><header><div><span class="eyebrow">{{preferences.t('preferences')}}</span><h2 id="settings-title">{{preferences.t('navSettings')}}</h2><p>{{preferences.t('settingsDescription')}}</p></div><button ref="closeButton" class="icon-button" :aria-label="preferences.t('closeSettings')" @click="$emit('close')"><X :size="20"/></button></header><div class="settings-group"><h3>{{preferences.t('theme')}}</h3><p class="help">{{preferences.t('appearanceDescription')}}</p><div class="theme-options"><button :class="{active:preferences.theme==='light'}" :aria-pressed="preferences.theme==='light'" @click="preferences.setTheme('light')"><Sun :size="17"/>{{preferences.t('light')}}</button><button :class="{active:preferences.theme==='dark'}" :aria-pressed="preferences.theme==='dark'" @click="preferences.setTheme('dark')"><Moon :size="17"/>{{preferences.t('dark')}}</button></div><label class="field">{{preferences.t('language')}}<select :value="preferences.language" @change="preferences.setLanguage(($event.target as HTMLSelectElement).value as 'en'|'ru')"><option value="en">English</option><option value="ru">Русский</option></select></label></div><div class="settings-group"><h3>{{preferences.t('captureSettings')}}</h3><label class="field">{{preferences.t('captureInterval')}} <span><input v-model.number="interval" type="number" min="1" max="3600"> {{preferences.t('seconds')}}</span></label><p class="help">{{preferences.t('intervalHelp')}}</p><label class="field">{{preferences.t('ignoredApps')}} <textarea v-model="ignored" rows="3" :placeholder="preferences.t('ignoredPlaceholder')"></textarea></label><p class="help">{{preferences.t('ignoredHelp')}}</p></div><button class="primary save" @click="save">{{preferences.t('saveSettings')}}</button></section></div></template>

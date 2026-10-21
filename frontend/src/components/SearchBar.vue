<script setup lang="ts">
import { Search, X } from 'lucide-vue-next'
import { usePreferencesStore } from '../stores/preferences'
const preferences = usePreferencesStore()
defineProps<{modelValue:string}>()
defineEmits<{ 'update:modelValue':[value:string]; 'open-spotlight':[] }>()
</script>
<template><div class="search-box"><Search :size="19" aria-hidden="true"/><input :value="modelValue" @input="$emit('update:modelValue',($event.target as HTMLInputElement).value)" :placeholder="preferences.t('searchPlaceholder')" :aria-label="preferences.t('searchLabel')"><button v-if="modelValue" class="icon-button clear" :aria-label="preferences.t('clearSearch')" @click="$emit('update:modelValue','')"><X :size="16"/></button><button v-else type="button" class="shortcut-button" :aria-label="preferences.t('openSearch')" @click="$emit('open-spotlight')"><kbd>Ctrl K</kbd></button></div></template>

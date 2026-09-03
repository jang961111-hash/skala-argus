<script setup>
import { computed } from 'vue'
import { STATUS, STATUS_META, STEP_STATUS, STEP_META, DECISION_META } from '../constants/domain'

// WorkRequestStatus · AgentStepStatus · ApprovalDecision 공용 칩.
// 라벨·색은 전부 constants/domain.js 에서 온다. 여기에 문자열을 박지 않는다.
const props = defineProps({
  status: { type: String, required: true },
})

const MAP = { ...STATUS_META, ...STEP_META, ...DECISION_META }

const meta = computed(() => MAP[props.status] || { label: props.status, tone: 'neutral' })
const pulsing = computed(() => props.status === STATUS.AI_RUNNING || props.status === STEP_STATUS.RUNNING)
</script>

<template>
  <span class="chip" :class="meta.tone">
    <i v-if="pulsing" class="dot pulse"></i>
    {{ meta.label }}
  </span>
</template>

<style scoped>
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; white-space: nowrap;
}
.neutral { background: #eef0f3; color: #4b5563; }
.info { background: var(--info-soft); color: var(--info); }
.primary { background: var(--primary-soft); color: var(--primary); }
.warning { background: var(--warning-soft); color: var(--warning); }
.success { background: var(--success-soft); color: var(--success); }
.danger { background: var(--danger-soft); color: var(--danger); }
.dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.pulse { animation: pulse 1s infinite ease-in-out; }
@keyframes pulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
</style>

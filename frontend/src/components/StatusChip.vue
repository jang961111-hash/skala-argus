<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
})

// CONTRACT.md 상태값 → 라벨/색상. work_requests.status, agent_runs.overall_status, step.status 공용.
const MAP = {
  REQUESTED: { label: '요청됨', tone: 'neutral' },
  RUNNING: { label: '에이전트 실행 중', tone: 'info' },
  REVIEW: { label: '검토 대기', tone: 'primary' },
  PENDING_APPROVAL: { label: '승인 대기', tone: 'warning' },
  APPROVED: { label: '승인', tone: 'success' },
  REJECTED: { label: '반려', tone: 'danger' },
  DONE: { label: '완료', tone: 'success' },
  PENDING: { label: '대기', tone: 'neutral' },
  FAILED: { label: '실패', tone: 'danger' },
  APPROVE: { label: '승인', tone: 'success' },
  REJECT: { label: '반려', tone: 'danger' },
  REQUEST_INFO: { label: '보완요청', tone: 'warning' },
}

const meta = computed(() => MAP[props.status] || { label: props.status, tone: 'neutral' })
</script>

<template>
  <span class="chip" :class="meta.tone">
    <i v-if="status === 'RUNNING'" class="dot pulse"></i>
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

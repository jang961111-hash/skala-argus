<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import api from '../api/client'
import {
  AGENTS, STEP_STATUS, RUN_STATUS, AGENT_CODE, DEFAULT_POLL_INTERVAL_MS, errorText,
} from '../constants/domain'
import StatusChip from './StatusChip.vue'

/**
 * E_03 에이전트 3종(A1·A2·A3) 카드 + 폴링.
 * 폴링 주기는 서버가 내려주는 pollIntervalMs 를 쓴다(계약 §4-12). 하드코딩하지 않는다.
 * step 실패는 HTTP 200 + 해당 step 만 FAILED + errorMessage — 전체를 실패로 처리하지 않는다.
 */
const props = defineProps({
  workRequestId: { type: String, required: true },
  run: { type: Object, default: null },
  canStart: { type: Boolean, default: false },
})
const emit = defineEmits(['updated', 'all-done'])

const current = ref(props.run)
const starting = ref(false)
const error = ref('')
let timer = null

const pollMs = computed(() => current.value?.pollIntervalMs || DEFAULT_POLL_INTERVAL_MS)

function stopPolling() {
  if (timer) { clearTimeout(timer); timer = null }
}

// 폴링 응답(API 12)에는 results 가 없다. 상세(API 7)로 받아둔 결과를 잃지 않도록 유지한다.
function mergeRun(incoming) {
  if (!incoming) return incoming
  const kept = current.value?.results || []
  if ((incoming.results?.length || 0) >= kept.length) return incoming
  return { ...incoming, results: kept }
}

async function pollOnce() {
  if (!current.value?.id) return
  try {
    const run = mergeRun(await api.getAgentRun(current.value.id))
    current.value = run
    emit('updated', run)
    if (run.allDone) {
      stopPolling()
      emit('all-done', run)
      return
    }
    if (run.status === RUN_STATUS.FAILED) { stopPolling(); return }
    schedule()
  } catch (e) {
    error.value = errorText(e)
    stopPolling()
  }
}

// setTimeout 체인이라 서버가 주기를 바꾸면 다음 호출부터 바로 반영된다.
function schedule() {
  stopPolling()
  timer = setTimeout(pollOnce, pollMs.value)
}

async function startRun() {
  starting.value = true
  error.value = ''
  try {
    const run = mergeRun(await api.startAgentRun(props.workRequestId))
    current.value = run
    emit('updated', run)
    if (!run.allDone) schedule()
  } catch (e) {
    error.value = errorText(e)
  } finally {
    starting.value = false
  }
}

watch(
  () => props.run,
  (run) => {
    // 부모가 상세를 다시 읽어 results 를 더 채워 넘겨주면 같은 run 이라도 받아들인다.
    // (폴링 응답에는 results 가 없으므로 개수가 늘었는지로 판단한다)
    const richer = (run?.results?.length || 0) > (current.value?.results?.length || 0)
    if (run && (run.id !== current.value?.id || richer)) {
      current.value = run
    }
    if (current.value && !current.value.allDone && current.value.status === RUN_STATUS.RUNNING && !timer) schedule()
  },
  { immediate: true },
)
onBeforeUnmount(stopPolling)

const stepOf = (code) => (current.value?.steps || []).find((s) => s.agentCode === code) || null
const resultOf = (code) => (current.value?.results || []).find((r) => r.agentCode === code) || null

const doneCount = computed(() => (current.value?.steps || []).filter((s) => s.status === STEP_STATUS.DONE).length)
const showStart = computed(() => !current.value && props.canStart)

function preview(code) {
  const r = resultOf(code)
  if (!r) return []
  if (code === AGENT_CODE.A3) return (r.payloadJson.documents || []).map((d) => d.name)
  return (r.payloadJson.items || []).map((i) => i.text)
}

const fmtTime = (iso) => (iso ? new Date(iso).toLocaleTimeString('ko-KR') : '')
</script>

<template>
  <section class="card stack" style="gap: 14px">
    <div class="row between">
      <div>
        <h2>AI 에이전트 3종</h2>
        <p class="muted small">
          <template v-if="current">
            <StatusChip :status="current.status" /> ·
            {{ doneCount }}/{{ AGENTS.length }} 완료
            <span class="mono"> · {{ current.id }}</span>
          </template>
          <template v-else>아직 실행되지 않았습니다.</template>
        </p>
      </div>
      <button v-if="showStart" class="primary" :disabled="starting" @click="startRun">
        {{ starting ? '요청 중…' : 'AI 검증 시작' }}
      </button>
    </div>

    <div v-if="error" class="alert error">{{ error }}</div>
    <div v-if="current && !current.allDone && current.status === RUN_STATUS.RUNNING" class="alert info">
      에이전트 3종이 순차 실행 중입니다. 서버가 지정한 <strong>{{ pollMs }}ms</strong> 간격으로
      <code>GET /agent-runs/{{ current.id }}</code> 를 폴링합니다.
    </div>

    <div class="agent-grid">
      <div
        v-for="a in AGENTS"
        :key="a.code"
        class="agent"
        :class="(stepOf(a.code)?.status || STEP_STATUS.WAITING).toLowerCase()"
      >
        <div class="agent-head">
          <span class="code">{{ a.code }}</span>
          <div class="agent-title">
            <strong>{{ a.title }}</strong>
            <span class="muted small">{{ a.desc }}</span>
          </div>
        </div>

        <div class="row between">
          <span class="state-text">{{ stepOf(a.code)?.message || '' }}</span>
          <StatusChip :status="stepOf(a.code)?.status || STEP_STATUS.WAITING" />
        </div>

        <!-- 실패한 step 만 오류를 보여주고 나머지는 계속 진행한다 -->
        <p v-if="stepOf(a.code)?.status === STEP_STATUS.FAILED" class="alert error small">
          {{ stepOf(a.code).errorMessage || '이 에이전트 실행이 실패했습니다.' }}
        </p>

        <ul v-else-if="preview(a.code).length" class="mini">
          <li v-for="(t, i) in preview(a.code)" :key="i">{{ t }}</li>
        </ul>

        <div v-if="stepOf(a.code)?.finishedAt" class="small muted done-at">
          {{ fmtTime(stepOf(a.code).finishedAt) }}
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.agent-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.agent {
  border: 1px solid var(--border); border-radius: var(--radius); padding: 14px;
  background: var(--surface); display: flex; flex-direction: column; gap: 10px; min-height: 160px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.agent.running { border-color: var(--info); box-shadow: 0 0 0 3px var(--info-soft); }
.agent.done { border-color: var(--success); background: #fbfefc; }
.agent.failed { border-color: var(--danger); background: #fffbfb; }
.agent.waiting { opacity: 0.75; }
.agent-head { display: flex; gap: 10px; align-items: flex-start; }
.code {
  font-size: 12px; font-weight: 700; color: var(--primary); background: var(--primary-soft);
  border-radius: 6px; padding: 3px 8px; white-space: nowrap;
}
.agent-title { display: flex; flex-direction: column; gap: 2px; }
.state-text { font-size: 12px; color: var(--muted); }
.mini {
  margin: 0; padding-left: 16px; font-size: 12px; color: var(--muted);
  display: flex; flex-direction: column; gap: 3px;
  border-top: 1px dashed var(--border); padding-top: 8px;
}
.done-at { margin-top: auto; }
@media (max-width: 900px) { .agent-grid { grid-template-columns: 1fr; } }
</style>

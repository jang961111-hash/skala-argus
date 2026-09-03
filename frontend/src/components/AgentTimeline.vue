<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import api from '../api/client'
import StatusChip from './StatusChip.vue'

const props = defineProps({
  workRequest: { type: Object, required: true },
})
const emit = defineEmits(['run-changed'])

// 기획서 6장: A1 규격·호환 / A2 법령 / A3 안전서류 / A4 벤더
const AGENTS = [
  { key: 'SPEC', code: 'A1', title: '규격·호환 분석', desc: '현재 부품 규격 확인, 호환품·유독가스 허용 여부' },
  { key: 'LEGAL', code: 'A2', title: '법령 검토', desc: '적용 법령 조문 인용, 작업 전/후 필수 절차' },
  { key: 'SAFETY_DOC', code: 'A3', title: '안전서류 초안', desc: '작업허가서·위험성평가 초안 생성, 누락 항목' },
  { key: 'VENDOR', code: 'A4', title: '벤더 견적(RFQ)', desc: '견적·납기 요청 초안, 구매 이력' },
]

const run = ref(props.workRequest.latest_run || null)
const starting = ref(false)
const error = ref('')
const expanded = ref(null)
let timer = null

const POLL_MS = 3000

function stopPolling() {
  if (timer) { clearInterval(timer); timer = null }
}

async function pollOnce() {
  if (!run.value) return
  try {
    const r = await api.getAgentRun(run.value.run_id)
    run.value = r
    if (r.overall_status !== 'RUNNING') {
      stopPolling()
      emit('run-changed', r)
    }
  } catch (e) {
    error.value = e.message
    stopPolling()
  }
}

function startPolling() {
  stopPolling()
  timer = setInterval(pollOnce, POLL_MS)
}

async function startRun() {
  starting.value = true
  error.value = ''
  try {
    const res = await api.startAgentRun(props.workRequest.id)
    run.value = {
      run_id: res.run_id,
      work_request_id: props.workRequest.id,
      overall_status: res.overall_status,
      steps: AGENTS.map((a) => ({ agent: a.key, status: 'PENDING', result: null })),
    }
    emit('run-changed', run.value)
    startPolling()
  } catch (e) {
    error.value = e.status === 409 ? '이미 승인/완료된 요청은 재실행할 수 없습니다.' : e.message
  } finally {
    starting.value = false
  }
}

// 상세 재조회로 latest_run 이 갱신되면 반영. 진행 중이면 폴링 재개.
watch(
  () => props.workRequest.latest_run,
  (lr) => {
    if (lr && (!run.value || lr.run_id !== run.value.run_id || lr.overall_status !== 'RUNNING')) run.value = lr
    if (run.value?.overall_status === 'RUNNING' && !timer) startPolling()
  },
  { immediate: true },
)
onBeforeUnmount(stopPolling)

const stepMap = computed(() => {
  const m = {}
  for (const s of run.value?.steps || []) m[s.agent] = s
  return m
})
const doneCount = computed(() => Object.values(stepMap.value).filter((s) => s.status === 'DONE').length)
const canStart = computed(() =>
  !['APPROVED', 'DONE'].includes(props.workRequest.status) && run.value?.overall_status !== 'RUNNING',
)

function toggle(key) {
  expanded.value = expanded.value === key ? null : key
}
function fmtTime(iso) {
  return iso ? new Date(iso).toLocaleTimeString('ko-KR') : ''
}
</script>

<template>
  <section class="card stack" style="gap: 14px">
    <div class="row between">
      <div>
        <h2>에이전트 타임라인</h2>
        <p class="muted small">
          <template v-if="run">
            {{ run.run_id }} ·
            <StatusChip :status="run.overall_status" /> ·
            {{ doneCount }}/4 완료
            <span v-if="run.model_name"> · {{ run.model_name }} / {{ run.prompt_version }}</span>
          </template>
          <template v-else>아직 실행되지 않았습니다.</template>
        </p>
      </div>
      <button class="primary" :disabled="!canStart || starting" @click="startRun">
        {{ starting ? '요청 중…' : run ? '에이전트 재실행' : '에이전트 실행' }}
      </button>
    </div>

    <div v-if="error" class="alert error">{{ error }}</div>
    <div v-if="run?.overall_status === 'RUNNING'" class="alert info">
      에이전트 4개가 순차 실행 중입니다. 3초마다 <code>GET /agent-runs/{{ run.run_id }}</code> 를 폴링합니다.
    </div>

    <div class="timeline">
      <div
        v-for="a in AGENTS"
        :key="a.key"
        class="step"
        :class="[(stepMap[a.key]?.status || 'PENDING').toLowerCase(), { open: expanded === a.key }]"
        @click="stepMap[a.key]?.result && toggle(a.key)"
      >
        <div class="step-head">
          <span class="code">{{ a.code }}</span>
          <div class="step-title">
            <strong>{{ a.title }}</strong>
            <span class="muted small">{{ a.desc }}</span>
          </div>
          <div class="step-meta">
            <StatusChip :status="stepMap[a.key]?.status || 'PENDING'" />
            <span v-if="stepMap[a.key]?.completed_at" class="small muted">{{ fmtTime(stepMap[a.key].completed_at) }}</span>
          </div>
        </div>

        <!-- 결과 요약 -->
        <div v-if="stepMap[a.key]?.result" class="step-body" @click.stop>
          <!-- SPEC -->
          <template v-if="a.key === 'SPEC'">
            <div class="row">
              <span :class="stepMap.SPEC.result.spec_match ? 'ok' : 'ng'">{{ stepMap.SPEC.result.spec_match ? '규격 일치' : '규격 불일치' }}</span>
              <span class="mono">{{ stepMap.SPEC.result.current_part }}</span>
            </div>
            <table v-if="expanded === a.key && stepMap.SPEC.result.alternatives?.length" class="inner">
              <thead><tr><th>호환품</th><th>등급</th><th>차이</th><th>유독가스</th></tr></thead>
              <tbody>
                <tr v-for="alt in stepMap.SPEC.result.alternatives" :key="alt.part_no">
                  <td class="mono">{{ alt.part_no }}</td>
                  <td>{{ alt.grade }}</td>
                  <td>{{ alt.diff }}</td>
                  <td :class="alt.allowed_for_toxic_gas ? 'ok' : 'ng'">{{ alt.allowed_for_toxic_gas ? '허용' : '불가' }}</td>
                </tr>
              </tbody>
            </table>
            <div v-else class="small muted">호환품 {{ stepMap.SPEC.result.alternatives?.length || 0 }}건 — 클릭하여 호환표 보기</div>
          </template>

          <!-- LEGAL -->
          <template v-else-if="a.key === 'LEGAL'">
            <div class="small">적용 법령 {{ stepMap.LEGAL.result.applicable_laws?.length || 0 }}건 · 필수 절차 {{ stepMap.LEGAL.result.required_procedures?.length || 0 }}건</div>
            <template v-if="expanded === a.key">
              <ul class="laws">
                <li v-for="l in stepMap.LEGAL.result.applicable_laws" :key="l.law + l.article">
                  <strong>{{ l.law }} {{ l.article }}</strong> — {{ l.title }}
                  <blockquote v-if="l.quote">{{ l.quote }}</blockquote>
                </li>
              </ul>
              <ul class="procs">
                <li v-for="p in stepMap.LEGAL.result.required_procedures" :key="p.name">
                  <span class="phase">{{ p.phase === 'BEFORE' ? '작업 전' : p.phase === 'AFTER' ? '작업 후' : '작업 중' }}</span>
                  {{ p.name }}
                  <span v-if="p.required" class="req">필수</span>
                </li>
              </ul>
            </template>
            <div v-else class="small muted">클릭하여 조문 인용·절차 보기</div>
          </template>

          <!-- SAFETY_DOC -->
          <template v-else-if="a.key === 'SAFETY_DOC'">
            <ul class="docs">
              <li v-for="d in stepMap.SAFETY_DOC.result.documents" :key="d.doc_id || d.type">
                <span class="mono">{{ d.doc_id }}</span> {{ d.type }}
                <span v-if="d.missing?.length" class="ng">누락: {{ d.missing.join(', ') }}</span>
                <span v-else class="ok">완비</span>
              </li>
            </ul>
          </template>

          <!-- VENDOR -->
          <template v-else-if="a.key === 'VENDOR'">
            <div>{{ stepMap.VENDOR.result.rfq_summary || stepMap.VENDOR.result.rfq_draft }}</div>
            <div class="small muted">
              예상 납기 {{ stepMap.VENDOR.result.lead_time_est_days }}일 · 최근 구매 {{ stepMap.VENDOR.result.last_purchase }}
              <span v-if="stepMap.VENDOR.result.rfq_doc_id"> · <span class="mono">{{ stepMap.VENDOR.result.rfq_doc_id }}</span></span>
            </div>
          </template>
        </div>
      </div>
    </div>

    <div v-if="run?.summary" class="summary">
      <label>에이전트 종합 요약</label>
      <p>{{ run.summary }}</p>
      <p class="small muted" style="margin-top: 4px">승인 필요: {{ run.approval_required_by }}</p>
    </div>
  </section>
</template>

<style scoped>
.timeline { display: flex; flex-direction: column; gap: 10px; position: relative; }
.step {
  border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 14px;
  border-left: 4px solid #cbd2dc; transition: border-color 0.2s, background 0.2s;
}
.step.running { border-left-color: var(--info); background: #f6fbfd; }
.step.done { border-left-color: var(--success); }
.step.failed { border-left-color: var(--danger); }
.step.done:hover { cursor: pointer; background: #fafcff; }
.step-head { display: flex; align-items: center; gap: 12px; }
.code {
  width: 30px; height: 30px; border-radius: 8px; background: #eef0f3; color: #4b5563;
  display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: 12px; flex: none;
}
.step.done .code { background: var(--success-soft); color: var(--success); }
.step.running .code { background: var(--info-soft); color: var(--info); }
.step-title { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.step-meta { display: flex; align-items: center; gap: 8px; }
.step-body { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--border); font-size: 13px; cursor: default; }
.ok { color: var(--success); font-weight: 600; }
.ng { color: var(--danger); font-weight: 600; }
table.inner { margin-top: 8px; font-size: 12px; }
table.inner th, table.inner td { padding: 6px 8px; }
.laws, .procs, .docs { margin: 6px 0 0; padding-left: 18px; }
.laws li, .procs li, .docs li { margin-bottom: 4px; }
blockquote { margin: 4px 0 0; padding: 6px 10px; border-left: 3px solid var(--primary-soft); background: #f8faff; color: #374151; font-size: 12px; }
.phase { display: inline-block; font-size: 11px; background: #eef0f3; padding: 1px 6px; border-radius: 4px; margin-right: 4px; }
.req { font-size: 11px; color: var(--danger); margin-left: 4px; }
.summary { background: var(--primary-soft); border-radius: var(--radius); padding: 12px 14px; }
.summary label { color: var(--primary); font-weight: 600; }
code { background: #eef0f3; padding: 0 4px; border-radius: 4px; }
</style>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import api from '../api/client'
import StatusChip from './StatusChip.vue'

const props = defineProps({
  workRequest: { type: Object, required: true },
  role: { type: String, required: true }, // ENGINEER | SAFETY_MANAGER | ...
  user: { type: Object, required: true },
  run: { type: Object, default: null },
})
const emit = defineEmits(['changed'])

// CONTRACT.md 승인 규칙: 4항목 모두 true 가 아니면 APPROVE 는 409
const CHECKLIST = [
  { key: 'WORK_PERMIT', label: '작업허가서 확인', hint: '가스 배관 작업 허가서 결재 완료' },
  { key: 'RISK_ASSESSMENT', label: '위험성평가 확인', hint: '위험성평가 결과 검토' },
  { key: 'LOTO_GAS_ISOLATION', label: 'LOTO·가스 차단·퍼지', hint: '잠금장치·표지판, 가스 차단 및 퍼지 완료' },
  { key: 'GAS_DETECTOR_CHECK', label: '가스 감지기 정상 확인', hint: '작업 후 감지기 정상 동작' },
]

const checklist = reactive({ WORK_PERMIT: false, RISK_ASSESSMENT: false, LOTO_GAS_ISOLATION: false, GAS_DETECTOR_CHECK: false })
const comment = ref('')
const busy = ref(false)
const error = ref('')

const run = computed(() => props.workRequest.latest_run)
const legal = computed(() => run.value?.steps?.find((s) => s.agent === 'LEGAL')?.result)
const docs = computed(() => run.value?.steps?.find((s) => s.agent === 'SAFETY_DOC')?.result?.documents || [])
const approvals = computed(() => props.workRequest.approvals || [])

const status = computed(() => props.workRequest.status)
const runReady = computed(() => run.value?.overall_status === 'REVIEW')
const isSafetyManager = computed(() => props.role === 'SAFETY_MANAGER')
const isEngineer = computed(() => props.role === 'ENGINEER')

// 안전관리자는 REVIEW / PENDING_APPROVAL 에서만 결정 가능
const canDecide = computed(() => isSafetyManager.value && ['REVIEW', 'PENDING_APPROVAL'].includes(status.value))
const allChecked = computed(() => CHECKLIST.every((c) => checklist[c.key]))
const canApprove = computed(() => canDecide.value && allChecked.value && !busy.value)

// 엔지니어: run 완료(REVIEW) 이면 승인 요청 가능
const canSubmit = computed(() => isEngineer.value && status.value === 'REVIEW' && runReady.value && !busy.value)

watch(() => props.workRequest.id, () => {
  CHECKLIST.forEach((c) => (checklist[c.key] = false))
  comment.value = ''
  error.value = ''
})

async function submitForApproval() {
  busy.value = true
  error.value = ''
  try {
    // 에이전트가 만든 서류에 누락 항목이 있으면 먼저 보완값을 받아 함께 전송 (422 방지)
    const docs = (props.run?.steps || []).find((s) => s.agent === 'SAFETY_DOC')?.result?.documents || []
    const missingItems = [...new Set(docs.flatMap((d) => d.missing || []))]
    const missing_info = {}
    for (const item of missingItems) {
      const v = window.prompt(`서류 누락 항목을 입력하세요: ${item}`, '')
      if (v === null) { busy.value = false; return }
      missing_info[item] = v
    }
    await api.submitApproval(props.workRequest.id, Object.keys(missing_info).length ? { missing_info } : {})
    emit('changed', '승인 요청을 보냈습니다. 안전관리자 계정으로 전환하여 승인하세요.')
  } catch (e) {
    error.value = e.status === 409 ? '에이전트 실행이 완료되어야 승인 요청할 수 있습니다.' : e.status === 422 ? `누락 정보: ${e.message}` : e.message
  } finally {
    busy.value = false
  }
}

async function decide(decision) {
  if (decision !== 'APPROVE' && !comment.value.trim()) {
    error.value = '반려/보완요청 시 코멘트를 입력하세요 (엔지니어에게 바로 전달됩니다).'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await api.createApproval(props.workRequest.id, {
      work_request_id: props.workRequest.id,
      approver_id: props.user.id,
      decision,
      checklist: { ...checklist },
      comment: comment.value.trim(),
    })
    const msg = { APPROVE: '승인되었습니다.', REJECT: '반려되었습니다.', REQUEST_INFO: '보완요청을 보냈습니다.' }[decision]
    comment.value = ''
    emit('changed', msg)
  } catch (e) {
    error.value = e.status === 409 ? '필수 체크리스트 4항목을 모두 확인해야 승인할 수 있습니다.' : e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <aside class="card stack panel" style="gap: 14px">
    <div class="row between">
      <h2>승인 패널</h2>
      <StatusChip :status="status" />
    </div>

    <div v-if="error" class="alert error">{{ error }}</div>

    <!-- 에이전트 미완료 -->
    <div v-if="!runReady" class="alert info">
      에이전트 실행이 완료되면 적용 법령·체크리스트가 표시됩니다.
    </div>

    <template v-else>
      <!-- 적용 법령 -->
      <div>
        <label>적용 법령</label>
        <ul class="laws">
          <li v-for="l in legal?.applicable_laws || []" :key="l.law + l.article">
            <a :href="`https://www.law.go.kr/법령/${encodeURIComponent(l.law)}`" target="_blank" rel="noopener">{{ l.law }} {{ l.article }}</a>
            <span class="muted small"> — {{ l.title }}</span>
          </li>
        </ul>
      </div>

      <!-- 서류 초안 -->
      <div>
        <label>서류 초안</label>
        <ul class="docs">
          <li v-for="d in docs" :key="d.doc_id || d.type" class="row between">
            <span><span class="mono">{{ d.doc_id }}</span> {{ d.type }}</span>
            <span v-if="d.missing?.length" class="ng small">누락 {{ d.missing.length }}</span>
            <span v-else class="ok small">완비</span>
          </li>
          <li v-if="!docs.length" class="muted small">없음</li>
        </ul>
      </div>

      <!-- 필수 절차 체크리스트 -->
      <div>
        <label>필수 절차 체크리스트 <span class="muted">(미체크 시 승인 불가)</span></label>
        <ul class="checks">
          <li v-for="c in CHECKLIST" :key="c.key">
            <label class="check">
              <input type="checkbox" v-model="checklist[c.key]" :disabled="!canDecide" />
              <span>
                <strong>{{ c.label }}</strong>
                <span class="muted small">{{ c.hint }}</span>
              </span>
            </label>
          </li>
        </ul>
      </div>
    </template>

    <!-- 역할별 액션 -->
    <div class="actions stack">
      <!-- 엔지니어 -->
      <template v-if="isEngineer">
        <button v-if="status === 'REVIEW'" class="primary" :disabled="!canSubmit" @click="submitForApproval">
          {{ busy ? '요청 중…' : '승인 요청' }}
        </button>
        <div v-else-if="status === 'PENDING_APPROVAL'" class="alert info">안전관리자 승인 대기 중입니다.</div>
        <div v-else-if="status === 'APPROVED'" class="alert success">승인 완료 — 작업을 진행하세요.</div>
        <div v-else-if="status === 'REJECTED'" class="alert error">반려됨 — 코멘트를 확인하세요.</div>
        <div v-else class="muted small">에이전트 실행 후 승인 요청할 수 있습니다.</div>
      </template>

      <!-- 안전관리자 -->
      <template v-else-if="isSafetyManager">
        <template v-if="canDecide">
          <div>
            <label>코멘트 (엔지니어에게 바로 전달)</label>
            <textarea v-model="comment" placeholder="예) 작업자 명단 확인 완료. 승인."></textarea>
          </div>
          <button class="success" :disabled="!canApprove" @click="decide('APPROVE')">
            {{ busy ? '처리 중…' : allChecked ? '승인' : `승인 (체크리스트 ${CHECKLIST.filter((c) => checklist[c.key]).length}/4)` }}
          </button>
          <div class="row">
            <button class="warning" style="flex: 1" :disabled="busy" @click="decide('REQUEST_INFO')">보완요청</button>
            <button class="danger" style="flex: 1" :disabled="busy" @click="decide('REJECT')">반려</button>
          </div>
        </template>
        <div v-else-if="status === 'APPROVED'" class="alert success">이미 승인된 요청입니다.</div>
        <div v-else-if="status === 'REJECTED'" class="alert error">반려된 요청입니다.</div>
        <div v-else class="muted small">검토 대기(REVIEW) 또는 승인 대기(PENDING_APPROVAL) 상태에서 결정할 수 있습니다.</div>
      </template>

      <div v-else class="muted small">현재 역할({{ role }})은 승인 권한이 없습니다.</div>
    </div>

    <!-- 승인 이력 -->
    <div v-if="approvals.length">
      <label>승인 이력</label>
      <ul class="history">
        <li v-for="a in approvals" :key="a.approval_id">
          <div class="row between">
            <span><StatusChip :status="a.decision" /> <span class="small muted">{{ a.approver_id }}</span></span>
            <span class="small muted">{{ new Date(a.decided_at).toLocaleString('ko-KR') }}</span>
          </div>
          <div v-if="a.comment" class="small comment">{{ a.comment }}</div>
        </li>
      </ul>
    </div>
  </aside>
</template>

<style scoped>
.panel { position: sticky; top: 72px; }
.laws, .docs, .checks, .history { list-style: none; margin: 4px 0 0; padding: 0; }
.laws li, .docs li { padding: 4px 0; border-bottom: 1px dashed var(--border); font-size: 13px; }
.checks li { padding: 6px 0; }
.check { display: flex; align-items: flex-start; gap: 8px; cursor: pointer; margin: 0; color: var(--text); font-size: 13px; }
.check input { width: 16px; height: 16px; margin-top: 2px; flex: none; }
.check span { display: flex; flex-direction: column; }
.ok { color: var(--success); font-weight: 600; }
.ng { color: var(--danger); font-weight: 600; }
.actions { padding-top: 10px; border-top: 1px solid var(--border); }
.history li { padding: 6px 0; border-bottom: 1px dashed var(--border); }
.comment { margin-top: 4px; padding: 6px 8px; background: #f8fafc; border-radius: 6px; }
</style>

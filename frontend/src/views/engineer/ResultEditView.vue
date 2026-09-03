<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import {
  AGENTS, AGENT_CODE, STATUS, DOC_TYPES, SUBMITTABLE_STATUSES,
  productTypeLabel, specSummary, operatingConditionText, errorText,
} from '../../constants/domain'
import StatusChip from '../../components/StatusChip.vue'
import PhotoStrip from '../../components/PhotoStrip.vue'

/**
 * WRA_E_04 AI 결과 확인·수정.
 * PATCH /agent-results/{id} 는 전체 치환이다(계약 §4-13):
 *   배열에 없는 itemId/docId → 삭제, id 없는 항목 → 신규(서버 채번).
 * 화면은 편집 중인 배열을 그대로 보내고, 삭제는 배열에서 빼는 것으로 표현한다.
 */
const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()

const wr = ref(null)
const loading = ref(true)
const error = ref('')
const notice = ref('')
const busy = ref(false)
const engineerNote = ref('')

// resultId → 편집 중인 배열 사본
const drafts = reactive({})

const clone = (v) => JSON.parse(JSON.stringify(v ?? null))

const run = computed(() => wr.value?.agentRun || null)
const resultOf = (code) => (run.value?.results || []).find((r) => r.agentCode === code) || null
// 편집 가능 여부는 서버가 내려준 editable 을 따른다. 역할로 직접 판단하지 않는다.
const canEdit = computed(() => (run.value?.results || []).some((r) => r.editable))
const canSubmit = computed(() => wr.value && SUBMITTABLE_STATUSES.includes(wr.value.status))
const rejection = computed(() =>
  wr.value?.status === STATUS.REJECTED && wr.value?.approval?.decision === 'REJECT' ? wr.value.approval : null,
)

function loadDrafts() {
  for (const r of run.value?.results || []) {
    drafts[r.id] = r.agentCode === AGENT_CODE.A3
      ? clone(r.payloadJson.documents || [])
      : clone(r.payloadJson.items || [])
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const detail = await api.getWorkRequest(props.id)
    wr.value = detail
    engineerNote.value = detail.engineerNote || ''
    loadDrafts()
    if (detail.status === STATUS.AI_RUNNING) router.replace(`/requests/${props.id}/run`)
    else if (detail.status === STATUS.DRAFT) router.replace(`/requests/new?id=${props.id}`)
  } catch (e) {
    error.value = errorText(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ---------- 편집 조작 ----------
const addItem = (rid) => drafts[rid].push({ text: '' })                       // itemId 없음 = 신규
const addDocument = (rid) => drafts[rid].push({ type: DOC_TYPES[0].value, name: '', content: '' })
const removeAt = (rid, i) => drafts[rid].splice(i, 1)                          // 배열에서 빠지면 서버가 삭제 처리

async function saveResult(result) {
  error.value = ''
  notice.value = ''
  const rows = drafts[result.id] || []
  if (result.agentCode !== AGENT_CODE.A3 && rows.some((r) => !String(r.text || '').trim())) {
    error.value = '빈 항목은 저장할 수 없습니다. 내용을 채우거나 삭제하세요.'
    return
  }
  busy.value = true
  try {
    const body = result.agentCode === AGENT_CODE.A3
      ? { documents: rows.map((d) => ({ docId: d.docId, type: d.type, name: d.name, content: d.content })) }
      : { items: rows.map((i) => ({ itemId: i.itemId, text: i.text })) }
    await api.updateAgentResult(result.id, body)
    wr.value = await api.getWorkRequest(props.id)   // 서버가 채번한 id·edited 를 반영
    loadDrafts()
    notice.value = `${result.agentCode} 결과를 저장했습니다.`
  } catch (e) {
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}

// 엔지니어 설명 저장 (PATCH /work-requests/{id})
async function saveNote() {
  error.value = ''
  notice.value = ''
  busy.value = true
  try {
    await api.updateWorkRequest(props.id, { engineerNote: engineerNote.value })
    notice.value = '엔지니어 설명을 임시 저장했습니다.'
  } catch (e) {
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}

// 제출 — 서버 검증 4가지 실패 시 422 SUBMIT_REQUIRED_FIELD_MISSING
async function submit() {
  error.value = ''
  notice.value = ''
  if (!engineerNote.value.trim()) {
    error.value = '엔지니어 설명을 입력해야 제출할 수 있습니다. (안전관리자에게 전달되는 필수 항목)'
    return
  }
  const a2 = resultOf(AGENT_CODE.A2)
  if (!(a2?.payloadJson?.items || []).length) {
    error.value = 'A2 적용 법령이 1건 이상 있어야 제출할 수 있습니다.'
    return
  }
  busy.value = true
  try {
    await api.updateWorkRequest(props.id, { engineerNote: engineerNote.value })
    await api.submitApproval(props.id)
    notice.value = '안전관리자에게 제출했습니다. 상태가 승인 대기로 전환되었습니다.'
    await load()
  } catch (e) {
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}

const agentTitle = (code) => AGENTS.find((a) => a.code === code)?.title || code
</script>

<template>
  <div class="form-col stack" style="gap: 16px">
    <div class="row between">
      <div>
        <h1>AI 결과 확인 · 수정</h1>
        <p class="muted small mono">{{ wr?.requestNo || id }}</p>
      </div>
      <StatusChip v-if="wr" :status="wr.status" />
    </div>

    <p v-if="loading" class="muted">불러오는 중…</p>
    <div v-if="error" class="alert error">{{ error }}</div>
    <div v-if="notice" class="alert success">{{ notice }}</div>

    <template v-if="wr">
      <div v-if="rejection" class="alert error stack" style="gap: 4px">
        <strong>
          거절 사유
          <span v-if="rejection.reasonCategory">[{{ rejection.reasonCategory }}]</span>
          — {{ rejection.approverName }}
        </strong>
        <span>{{ rejection.reason }}</span>
        <span class="small">결과를 보완한 뒤 다시 제출하면 승인 대기로 복귀합니다.</span>
      </div>

      <section class="card summary">
        <div><label>설비 / 라인</label><strong>{{ wr.equipment || '—' }} / {{ wr.line || '—' }}</strong></div>
        <div><label>제품명 / 유형</label><strong>{{ wr.productName || '—' }} / {{ productTypeLabel(wr.productType) }}</strong></div>
        <div><label>스펙</label><strong>{{ specSummary(wr) }}</strong></div>
        <div><label>물질 / 운전 조건</label><strong>{{ wr.substance || '—' }} / {{ operatingConditionText(wr.operatingCondition) }}</strong></div>
      </section>

      <p v-if="!run" class="alert info">AI 실행 이력이 없습니다.</p>

      <section v-for="a in AGENTS" v-else :key="a.code" class="card stack" style="gap: 12px">
        <div class="row between">
          <div class="row" style="gap: 8px">
            <span class="code">{{ a.code }}</span>
            <h2>{{ a.title }}</h2>
            <span v-if="resultOf(a.code)?.edited" class="edited">수정됨</span>
          </div>
          <span class="muted small">{{ resultOf(a.code)?.editable ? '✎ 수정 가능' : '읽기 전용' }}</span>
        </div>

        <p v-if="!resultOf(a.code)" class="muted small">아직 결과가 없습니다.</p>

        <template v-else>
          <!-- A3: 문서형 -->
          <template v-if="a.code === AGENT_CODE.A3">
            <div v-for="(d, i) in drafts[resultOf(a.code).id] || []" :key="d.docId || 'new-' + i" class="item">
              <div class="grid2">
                <select v-model="d.type" :disabled="!resultOf(a.code).editable">
                  <option v-for="t in DOC_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
                </select>
                <input v-model="d.name" placeholder="문서 이름" :disabled="!resultOf(a.code).editable" />
              </div>
              <textarea v-model="d.content" rows="3" placeholder="문서 초안 내용" :disabled="!resultOf(a.code).editable"></textarea>
              <div class="row between">
                <span v-if="d.edited" class="edited sm">엔지니어 수정</span><span v-else></span>
                <button v-if="resultOf(a.code).editable" class="sm danger" @click="removeAt(resultOf(a.code).id, i)">✕ 삭제</button>
              </div>
            </div>
          </template>

          <!-- A1·A2: 항목형 -->
          <template v-else>
            <div v-for="(it, i) in drafts[resultOf(a.code).id] || []" :key="it.itemId || 'new-' + i" class="item">
              <textarea v-model="it.text" rows="2" placeholder="항목 내용" :disabled="!resultOf(a.code).editable"></textarea>
              <div class="row between">
                <span v-if="it.edited" class="edited sm">엔지니어 수정</span><span v-else></span>
                <button v-if="resultOf(a.code).editable" class="sm danger" @click="removeAt(resultOf(a.code).id, i)">✕ 삭제</button>
              </div>
            </div>
          </template>

          <div v-if="resultOf(a.code).editable" class="row between">
            <button v-if="a.code === AGENT_CODE.A3" class="sm" @click="addDocument(resultOf(a.code).id)">＋ 서류 추가</button>
            <button v-else class="sm" @click="addItem(resultOf(a.code).id)">＋ 항목 추가</button>
            <button class="sm primary" :disabled="busy" @click="saveResult(resultOf(a.code))">
              {{ a.code }} 저장
            </button>
          </div>
        </template>
      </section>

      <PhotoStrip v-if="wr.photos?.length" :photos="wr.photos" />

      <section class="card stack" style="gap: 10px">
        <h2>엔지니어 설명 <span class="req">*</span></h2>
        <p class="muted small">안전관리자에게 전달됩니다. 비어 있으면 제출이 차단됩니다.</p>
        <textarea
          v-model="engineerNote"
          rows="4"
          :disabled="!canSubmit"
          placeholder="예: 압력 등급 상향 반영, 제92조 작업허가 필요 판단. 호환품은 유독가스 라인이라 배제."
        ></textarea>
      </section>

      <div v-if="canSubmit" class="row" style="justify-content: flex-end; gap: 8px">
        <button :disabled="busy" @click="saveNote">임시 저장</button>
        <button class="primary" :disabled="busy" @click="submit">
          {{ wr.status === STATUS.REJECTED ? '보완 후 재제출 ▶' : '안전관리자에게 제출 ▶' }}
        </button>
      </div>
      <div v-else class="alert info">
        현재 상태에서는 결과를 수정하거나 제출할 수 없습니다.
        <span v-if="!canEdit">(승인 대기·승인 상태는 잠깁니다)</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.form-col { max-width: 860px; margin: 0 auto; }
.summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.summary > div { display: flex; flex-direction: column; gap: 4px; }
.grid2 { display: grid; grid-template-columns: 200px 1fr; gap: 10px; }
.code {
  font-size: 12px; font-weight: 700; color: var(--primary); background: var(--primary-soft);
  border-radius: 6px; padding: 2px 8px;
}
.edited { font-size: 11px; font-weight: 600; background: var(--warning-soft); color: var(--warning); padding: 2px 8px; border-radius: 999px; }
.edited.sm { padding: 1px 6px; }
.item {
  border: 1px solid var(--border); border-left: 3px solid var(--primary-soft);
  border-radius: 8px; padding: 10px; display: flex; flex-direction: column; gap: 8px; background: #fcfdff;
}
.req { color: var(--danger); }
@media (max-width: 900px) { .summary { grid-template-columns: repeat(2, 1fr); } .grid2 { grid-template-columns: 1fr; } }
</style>

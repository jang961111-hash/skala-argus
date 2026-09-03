<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/client'
import {
  STATUS, DECISION, REJECT_REASON_MIN, REJECT_REASON_CATEGORIES,
  productTypeLabel, specSummary, operatingConditionText, errorText,
} from '../../constants/domain'
import StatusChip from '../../components/StatusChip.vue'
import AiResultReadonly from '../../components/AiResultReadonly.vue'
import PhotoStrip from '../../components/PhotoStrip.vue'

// WRA_S_02 요청 상세 확인 (승인 / 거절)
// AI 결과는 읽기 전용 — 상세 응답의 agentRun.results[].editable 이 false 로 온다.
const props = defineProps({ id: { type: String, required: true } })

const wr = ref(null)
const loading = ref(true)
const error = ref('')
const notice = ref('')
const busy = ref(false)
const decision = ref('')
const reason = ref('')
const reasonCategory = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    wr.value = await api.getWorkRequest(props.id)
  } catch (e) {
    error.value = errorText(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const canDecide = computed(() => wr.value?.status === STATUS.PENDING)
const isReject = computed(() => decision.value === DECISION.REJECT)
const reasonLength = computed(() => reason.value.trim().length)
const reasonTooShort = computed(() => isReject.value && reasonLength.value < REJECT_REASON_MIN)

async function confirm() {
  error.value = ''
  notice.value = ''
  if (!decision.value) {
    error.value = '승인 또는 거절을 선택하세요.'
    return
  }
  // 거절 사유 10자 이상 (계약 §4-15). 서버에 보내기 전에 화면에서도 막는다.
  if (reasonTooShort.value) {
    error.value = `거절 사유는 ${REJECT_REASON_MIN}자 이상 입력해야 합니다. (현재 ${reasonLength.value}자)`
    return
  }
  busy.value = true
  try {
    const body = { workRequestId: props.id, decision: decision.value }
    if (reason.value.trim()) body.reason = reason.value.trim()
    if (isReject.value && reasonCategory.value) body.reasonCategory = reasonCategory.value
    await api.createApproval(body)
    notice.value = decision.value === DECISION.APPROVE
      ? '승인 처리했습니다. 요청 상태가 승인으로 전환되었습니다.'
      : '거절 처리했습니다. 사유가 요청자에게 전달됩니다.'
    decision.value = ''
    reason.value = ''
    reasonCategory.value = ''
    await load()
  } catch (e) {
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="stack" style="gap: 16px">
    <div class="row between">
      <div>
        <h1>요청 상세 확인</h1>
        <p class="muted small mono">{{ wr?.requestNo || id }}</p>
      </div>
      <div class="row" style="gap: 8px">
        <StatusChip v-if="wr" :status="wr.status" />
        <RouterLink to="/manage/requests"><button class="sm">← 목록</button></RouterLink>
      </div>
    </div>

    <p v-if="loading" class="muted">불러오는 중…</p>
    <div v-if="error" class="alert error">{{ error }}</div>
    <div v-if="notice" class="alert success">{{ notice }}</div>

    <div v-if="wr" class="cols">
      <div class="stack" style="gap: 16px">
        <section class="card stack" style="gap: 14px">
          <h2>요청 정보</h2>
          <div class="info">
            <div><label>설비 / 라인</label><strong>{{ wr.equipment || '—' }} / {{ wr.line || '—' }}</strong></div>
            <div><label>제품명 / 유형</label><strong>{{ wr.productName || '—' }} / {{ productTypeLabel(wr.productType) }}</strong></div>
            <div><label>스펙</label><strong>{{ specSummary(wr) }}</strong></div>
            <div><label>물질 / 운전 조건</label><strong>{{ wr.substance || '—' }} / {{ operatingConditionText(wr.operatingCondition) }}</strong></div>
            <div><label>요청자</label><strong>{{ wr.requesterName }}</strong></div>
            <div><label>제출일시</label><strong>{{ wr.submittedAt ? new Date(wr.submittedAt).toLocaleString('ko-KR') : '—' }}</strong></div>
          </div>
          <div>
            <label>증상 / 현장 확인 메모</label>
            <p class="small">{{ wr.symptom || '—' }}</p>
            <p class="small muted">{{ wr.siteMemo || '' }}</p>
          </div>
          <PhotoStrip :photos="wr.photos || []" />
        </section>

        <AiResultReadonly :run="wr.agentRun" />

        <section class="card stack" style="gap: 8px">
          <h2>엔지니어 설명</h2>
          <p v-if="wr.engineerNote" class="note">{{ wr.engineerNote }}</p>
          <p v-else class="muted small">작성된 설명이 없습니다.</p>
        </section>
      </div>

      <aside class="stack" style="gap: 16px">
        <section class="card stack" style="gap: 12px">
          <h2>승인 처리</h2>

          <template v-if="canDecide">
            <div class="choices">
              <button class="choice" :class="{ on: decision === DECISION.APPROVE }" @click="decision = DECISION.APPROVE">승인</button>
              <button class="choice reject" :class="{ on: isReject }" @click="decision = DECISION.REJECT">거절</button>
            </div>

            <div v-if="isReject">
              <label for="cat">거절 사유 분류</label>
              <select id="cat" v-model="reasonCategory">
                <option value="">선택 안 함</option>
                <option v-for="c in REJECT_REASON_CATEGORIES" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>

            <div>
              <label for="reason">
                거절 사유
                <span v-if="isReject" class="req">(필수 · {{ REJECT_REASON_MIN }}자 이상)</span>
                <span v-else class="muted">(승인 시 선택)</span>
              </label>
              <textarea id="reason" v-model="reason" rows="4" placeholder="거절 사유 입력…"></textarea>
              <p v-if="isReject" class="small" :class="reasonTooShort ? 'ng' : 'ok'">
                {{ reasonLength }} / {{ REJECT_REASON_MIN }}자
              </p>
            </div>

            <button class="primary" :disabled="busy" @click="confirm">
              {{ busy ? '처리 중…' : '결정 확정' }}
            </button>
            <p class="muted small">체크리스트 게이트 없이 승인 / 거절+사유로 처리합니다.</p>
          </template>

          <template v-else>
            <div class="alert info">승인 대기 상태의 요청만 처리할 수 있습니다.</div>
          </template>
        </section>

        <section v-if="wr.approval" class="card stack" style="gap: 10px">
          <h2>최근 결정</h2>
          <div class="row between">
            <StatusChip :status="wr.approval.decision" />
            <span class="muted small">{{ new Date(wr.approval.decidedAt).toLocaleString('ko-KR') }}</span>
          </div>
          <p v-if="wr.approval.reasonCategory" class="small"><strong>[{{ wr.approval.reasonCategory }}]</strong></p>
          <p class="small">{{ wr.approval.reason || '사유 없음' }}</p>
          <p class="muted small">{{ wr.approval.approverName }}</p>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.cols { display: grid; grid-template-columns: 1fr 340px; gap: 20px; align-items: start; }
.info { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.info > div { display: flex; flex-direction: column; gap: 3px; }
.note { background: var(--primary-soft); padding: 10px 12px; border-radius: 8px; font-size: 13px; }
.choices { display: flex; gap: 8px; }
.choice { flex: 1; padding: 10px; font-weight: 600; }
.choice.on { background: var(--success); border-color: var(--success); color: #fff; }
.choice.reject.on { background: var(--danger); border-color: var(--danger); color: #fff; }
.req { color: var(--danger); }
.ok { color: var(--success); }
.ng { color: var(--danger); }
@media (max-width: 1000px) { .cols { grid-template-columns: 1fr; } .info { grid-template-columns: 1fr; } }
</style>

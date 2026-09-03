<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import {
  STATUS, productTypeLabel, specSummary, operatingConditionText, errorText,
} from '../../constants/domain'
import AgentTimeline from '../../components/AgentTimeline.vue'
import StatusChip from '../../components/StatusChip.vue'

// WRA_E_03 AI 검증 진행 — :id 는 UUID, 화면 표시는 requestNo
const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()

const wr = ref(null)
const error = ref('')
const loading = ref(true)
const allDone = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    wr.value = await api.getWorkRequest(props.id)
    allDone.value = Boolean(wr.value.agentRun?.allDone)
  } catch (e) {
    error.value = errorText(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

function onUpdated(run) {
  allDone.value = Boolean(run.allDone)
}

async function onAllDone() {
  // 마지막 step 이 끝나면 서버가 AI_DONE 으로 전환하므로 요약을 다시 읽는다.
  try { wr.value = await api.getWorkRequest(props.id) } catch { /* 요약 갱신 실패는 무시 */ }
  allDone.value = true
}

// 아직 run 이 없고 아직 제출 전이면 이 화면에서 시작할 수 있다.
const canStart = computed(() => wr.value && !wr.value.agentRun && wr.value.status === STATUS.DRAFT)

const goResult = () => router.push(`/requests/${props.id}/result`)
</script>

<template>
  <div class="stack" style="gap: 16px">
    <div>
      <h1>AI 검증 진행</h1>
      <p class="muted small mono">{{ wr?.requestNo || id }}</p>
    </div>

    <div v-if="error" class="alert error">{{ error }}</div>
    <p v-if="loading" class="muted">불러오는 중…</p>

    <template v-if="wr">
      <section class="card summary">
        <div>
          <label>설비 / 라인</label>
          <strong>{{ wr.equipment || '—' }} / {{ wr.line || '—' }}</strong>
        </div>
        <div>
          <label>제품명 / 유형</label>
          <strong>{{ wr.productName || '—' }} / {{ productTypeLabel(wr.productType) }}</strong>
        </div>
        <div>
          <label>스펙</label>
          <strong>{{ specSummary(wr) }}</strong>
        </div>
        <div>
          <label>물질 / 운전 조건</label>
          <strong>{{ wr.substance || '—' }} / {{ operatingConditionText(wr.operatingCondition) }}</strong>
        </div>
        <div>
          <label>상태</label>
          <StatusChip :status="wr.status" />
        </div>
      </section>

      <AgentTimeline
        :work-request-id="wr.id"
        :run="wr.agentRun"
        :can-start="canStart"
        @updated="onUpdated"
        @all-done="onAllDone"
      />

      <div class="row" style="justify-content: flex-end; gap: 8px">
        <span v-if="!allDone" class="muted small">3종이 모두 완료되면 결과 확인이 열립니다.</span>
        <button class="primary" :disabled="!allDone" @click="goResult">결과 확인 →</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.summary { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; }
.summary > div { display: flex; flex-direction: column; gap: 4px; }
@media (max-width: 1100px) { .summary { grid-template-columns: repeat(2, 1fr); } }
</style>

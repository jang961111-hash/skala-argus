<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import { ENGINEER_KPIS, productTypeLabel, nextActionMeta, errorText } from '../../constants/domain'
import StatusChip from '../../components/StatusChip.vue'

// WRA_E_01 엔지니어 메인
// v2.0 화면정의서에서 평균 승인 소요시간 KPI 와 진행률 컬럼이 제거됐다. 다시 넣지 말 것.
const router = useRouter()

const summary = ref(null)
const items = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [s, list] = await Promise.all([
      api.getDashboardSummary('engineer'),
      api.listWorkRequests({ mine: true, page: 0, size: 20 }),
    ])
    summary.value = s
    items.value = list.content
  } catch (e) {
    error.value = errorText(e, '불러오기 실패')
  } finally {
    loading.value = false
  }
}
onMounted(load)

const kpis = computed(() =>
  summary.value ? ENGINEER_KPIS.map((k) => ({ ...k, value: summary.value[k.key] ?? 0 })) : [],
)

const recent = computed(() => items.value.slice(0, 5))

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }) : '—')

// 행 클릭 분기는 서버가 계산한 nextAction 을 따른다 (계약 §4-6).
function openRow(it) {
  router.push(nextActionMeta(it.nextAction).path(it.id))
}
</script>

<template>
  <div class="stack" style="gap: 20px">
    <div class="row between">
      <div>
        <h1>엔지니어 메인</h1>
        <p class="muted small">내 교체 요청 현황과 최근 요청을 확인합니다.</p>
      </div>
      <RouterLink to="/requests/new"><button class="primary">＋ 신규 교체 요청</button></RouterLink>
    </div>

    <div v-if="error" class="alert error">{{ error }}</div>

    <div class="kpis">
      <div v-for="k in kpis" :key="k.key" class="card kpi" :class="k.tone">
        <span class="muted small">{{ k.label }}</span>
        <strong class="value">{{ k.value }}</strong>
      </div>
      <div v-if="!kpis.length" class="card kpi"><span class="muted small">불러오는 중…</span></div>
    </div>

    <section class="card" style="padding: 0">
      <div class="row between" style="padding: 14px 16px">
        <h2>최근 내 요청</h2>
        <RouterLink to="/my/requests" class="small">전체 보기 →</RouterLink>
      </div>
      <table>
        <thead>
          <tr>
            <th>설비 / 제품</th>
            <th>제품 유형</th>
            <th>상태</th>
            <th>제출일</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in recent" :key="it.id" class="clickable" @click="openRow(it)">
            <td>
              <strong>{{ it.equipment || '—' }}</strong>
              <span class="muted"> / {{ it.productName || '—' }}</span>
              <div class="muted small mono">{{ it.requestNo }}</div>
            </td>
            <td>{{ productTypeLabel(it.productType) }}</td>
            <td><StatusChip :status="it.status" /></td>
            <td>{{ fmtDate(it.submittedAt) }}</td>
          </tr>
          <tr v-if="!recent.length && !loading">
            <td colspan="4" class="empty">아직 등록한 요청이 없습니다. ‘신규 교체 요청’으로 시작하세요.</td>
          </tr>
          <tr v-if="loading && !recent.length"><td colspan="4" class="empty">불러오는 중…</td></tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi { display: flex; flex-direction: column; gap: 6px; }
.value { font-size: 28px; font-weight: 700; line-height: 1.1; }
.kpi.info .value { color: var(--info); }
.kpi.warning .value { color: var(--warning); }
.kpi.danger .value { color: var(--danger); }
@media (max-width: 900px) { .kpis { grid-template-columns: repeat(2, 1fr); } }
</style>

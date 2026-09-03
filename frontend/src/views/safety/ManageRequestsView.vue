<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import { STATUS, SAFETY_KPIS, productTypeLabel, errorText } from '../../constants/domain'

// WRA_S_01 요청 관리 (승인 대기)
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
      api.getDashboardSummary('safety'),
      api.listWorkRequests({ status: STATUS.PENDING, page: 0, size: 100, sort: 'submittedAt,desc' }),
    ])
    summary.value = s
    items.value = list.content
  } catch (e) {
    error.value = errorText(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const kpis = computed(() =>
  summary.value ? SAFETY_KPIS.map((k) => ({ ...k, value: summary.value[k.key] ?? 0 })) : [],
)

const rejectTop = computed(() => summary.value?.rejectReasonsTop || [])
const maxCount = computed(() => Math.max(1, ...rejectTop.value.map((r) => r.count)))

const fmtDateTime = (iso) =>
  iso ? new Date(iso).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'
</script>

<template>
  <div class="stack" style="gap: 20px">
    <div>
      <h1>요청 관리</h1>
      <p class="muted small">승인 대기 중인 부품 교체 요청을 검토합니다. (체크리스트 blocking 없음)</p>
    </div>

    <div v-if="error" class="alert error">{{ error }}</div>

    <div class="kpis">
      <div v-for="k in kpis" :key="k.key" class="card kpi" :class="k.tone">
        <span class="muted small">{{ k.label }}</span>
        <strong class="value">{{ k.value }}</strong>
      </div>
      <div v-if="!kpis.length" class="card kpi"><span class="muted small">불러오는 중…</span></div>
    </div>

    <div class="cols">
      <section class="card" style="padding: 0">
        <div class="row between" style="padding: 14px 16px">
          <h2>승인 대기 목록</h2>
          <span class="muted small">{{ items.length }}건</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>설비 / 제품</th>
              <th>제품 유형</th>
              <th>요청자</th>
              <th>제출일시</th>
              <th style="width: 80px"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="it in items"
              :key="it.id"
              class="clickable"
              @click="router.push(`/manage/requests/${it.id}`)"
            >
              <td>
                <strong>{{ it.equipment || '—' }}</strong>
                <span class="muted"> / {{ it.productName || '—' }}</span>
                <div class="muted small mono">{{ it.requestNo }}</div>
              </td>
              <td>{{ productTypeLabel(it.productType) }}</td>
              <td>{{ it.requesterName }}</td>
              <td>{{ fmtDateTime(it.submittedAt) }}</td>
              <td><button class="sm">검토 →</button></td>
            </tr>
            <tr v-if="!items.length && !loading">
              <td colspan="5" class="empty">승인 대기 요청이 없습니다.</td>
            </tr>
            <tr v-if="loading && !items.length"><td colspan="5" class="empty">불러오는 중…</td></tr>
          </tbody>
        </table>
      </section>

      <section class="card stack" style="gap: 10px">
        <h2>거절 사유 TOP 5</h2>
        <p v-if="!rejectTop.length" class="muted small">거절 이력이 없습니다.</p>
        <div v-for="r in rejectTop" :key="r.reason" class="reason">
          <div class="row between">
            <span class="small">{{ r.reason }}</span>
            <strong class="small">{{ r.count }}</strong>
          </div>
          <div class="bar"><i :style="{ width: Math.round((r.count / maxCount) * 100) + '%' }"></i></div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi { display: flex; flex-direction: column; gap: 6px; }
.value { font-size: 28px; font-weight: 700; line-height: 1.1; }
.kpi.warning .value { color: var(--warning); }
.kpi.success .value { color: var(--success); }
.kpi.danger .value { color: var(--danger); }
.cols { display: grid; grid-template-columns: 1fr 300px; gap: 20px; align-items: start; }
.reason { display: flex; flex-direction: column; gap: 4px; }
.bar { height: 6px; background: #e9ecf1; border-radius: 3px; overflow: hidden; }
.bar > i { display: block; height: 100%; background: var(--danger); }
@media (max-width: 1000px) { .cols { grid-template-columns: 1fr; } .kpis { grid-template-columns: repeat(2, 1fr); } }
</style>

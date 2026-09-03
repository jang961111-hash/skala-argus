<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import { STATUS, productTypeLabel, nextActionMeta, errorText } from '../../constants/domain'
import StatusChip from '../../components/StatusChip.vue'

// WRA_E_05 내 요청 목록 (마이페이지)
// status 는 콤마 다중 지정이 가능하다 (계약 §4-6). 탭은 그 값을 그대로 쿼리에 넘긴다.
const router = useRouter()

const TABS = [
  { key: 'ALL', label: '전체', status: null },
  { key: 'DRAFT', label: '작성 중', status: STATUS.DRAFT },
  { key: 'PROGRESS', label: '진행 중', status: `${STATUS.AI_RUNNING},${STATUS.AI_DONE}` },
  { key: 'PENDING', label: '승인 대기', status: STATUS.PENDING },
  { key: 'REJECTED', label: '거절 · 보완', status: STATUS.REJECTED },
]

const active = ref('ALL')
const items = ref([])
const loading = ref(false)
const error = ref('')
const reasonFor = ref(null)

const currentTab = computed(() => TABS.find((t) => t.key === active.value) || TABS[0])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { mine: true, page: 0, size: 100 }
    if (currentTab.value.status) params.status = currentTab.value.status
    const list = await api.listWorkRequests(params)
    items.value = list.content
  } catch (e) {
    error.value = errorText(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(active, load)

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }) : '—')

function go(it) {
  // 거절 건은 사유부터 보여주고, 나머지는 서버가 준 nextAction 대로 이동한다.
  if (it.status === STATUS.REJECTED) return showReason(it)
  router.push(nextActionMeta(it.nextAction).path(it.id))
}

const actionLabel = (it) => (it.status === STATUS.REJECTED ? '사유 보기' : nextActionMeta(it.nextAction).label)

async function showReason(it) {
  error.value = ''
  try {
    const detail = await api.getWorkRequest(it.id)
    reasonFor.value = {
      id: it.id,
      requestNo: it.requestNo,
      reason: detail.approval?.reason || '기록된 거절 사유가 없습니다.',
      category: detail.approval?.reasonCategory || '',
      approver: detail.approval?.approverName || '',
    }
  } catch (e) {
    error.value = errorText(e)
  }
}
</script>

<template>
  <div class="stack" style="gap: 16px">
    <div class="row between">
      <div>
        <h1>내 요청 목록</h1>
        <p class="muted small">상태별로 내 교체 요청을 확인하고 이어서 진행합니다.</p>
      </div>
      <RouterLink to="/requests/new"><button class="primary">＋ 신규 교체 요청</button></RouterLink>
    </div>

    <div v-if="error" class="alert error">{{ error }}</div>

    <div class="tabs">
      <button
        v-for="t in TABS"
        :key="t.key"
        class="tab"
        :class="{ on: active === t.key }"
        @click="active = t.key"
      >{{ t.label }}</button>
    </div>

    <section class="card" style="padding: 0">
      <table>
        <thead>
          <tr>
            <th>설비 / 제품</th>
            <th>제품 유형</th>
            <th>상태</th>
            <th>제출일</th>
            <th style="width: 110px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in items" :key="it.id">
            <td>
              <strong>{{ it.equipment || '—' }}</strong>
              <span class="muted"> / {{ it.productName || '—' }}</span>
              <div class="muted small mono">{{ it.requestNo }}</div>
            </td>
            <td>{{ productTypeLabel(it.productType) }}</td>
            <td><StatusChip :status="it.status" /></td>
            <td>{{ fmtDate(it.submittedAt) }}</td>
            <td><button class="sm" @click="go(it)">{{ actionLabel(it) }}</button></td>
          </tr>
          <tr v-if="!items.length && !loading">
            <td colspan="5" class="empty">해당 상태의 요청이 없습니다.</td>
          </tr>
          <tr v-if="loading && !items.length"><td colspan="5" class="empty">불러오는 중…</td></tr>
        </tbody>
      </table>
    </section>

    <div v-if="reasonFor" class="modal-backdrop" @click="reasonFor = null">
      <div class="modal card stack" @click.stop>
        <div class="row between">
          <h2>거절 사유</h2>
          <button class="sm" @click="reasonFor = null">닫기</button>
        </div>
        <p class="muted small mono">{{ reasonFor.requestNo }} · {{ reasonFor.approver }}</p>
        <div class="alert error">
          <strong v-if="reasonFor.category">[{{ reasonFor.category }}] </strong>{{ reasonFor.reason }}
        </div>
        <div class="row" style="justify-content: flex-end; gap: 8px">
          <button class="primary" @click="router.push(`/requests/${reasonFor.id}/result`)">수정 후 재제출 →</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.tab { border-radius: 999px; padding: 6px 14px; font-size: 13px; }
.tab.on { background: var(--primary-soft); border-color: var(--primary); color: var(--primary); font-weight: 600; }
</style>

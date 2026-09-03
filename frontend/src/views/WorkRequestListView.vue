<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/client'
import { session } from '../store/session'
import StatusChip from '../components/StatusChip.vue'

const router = useRouter()

const summary = ref(null)
const items = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const statusFilter = ref('')

const STATUSES = ['REQUESTED', 'RUNNING', 'REVIEW', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'DONE']

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [s, list] = await Promise.all([
      api.getDashboardSummary(),
      api.listWorkRequests({ status: statusFilter.value || undefined, page: 1, size: 50 }),
    ])
    summary.value = s
    items.value = list.items
    total.value = list.total
  } catch (e) {
    error.value = e.message || '불러오기 실패'
  } finally {
    loading.value = false
  }
}
onMounted(load)

const kpis = computed(() => {
  const s = summary.value
  if (!s) return []
  return [
    { label: '진행 중', value: s.in_progress, unit: '건' },
    { label: '승인 대기', value: s.pending_approval, unit: '건', tone: 'warning' },
    {
      label: '평균 승인 소요시간', value: s.avg_approval_hours, unit: 'h',
      sub: `As-Is ${s.as_is_baseline_hours}h → ${Math.round((1 - s.avg_approval_hours / s.as_is_baseline_hours) * 100)}% 단축`,
      tone: 'success',
    },
    { label: '이번 달 완료', value: s.completed_this_month, unit: '건' },
  ]
})

function progressOf(item) {
  const p = item.agent_progress || { done: 0, total: 4 }
  return { done: p.done ?? 0, total: p.total ?? 4, pct: Math.round(((p.done ?? 0) / (p.total ?? 4)) * 100) }
}

// ---------- 새 작업요청 모달 ----------
const showCreate = ref(false)
const equipments = ref([])
const parts = ref([])
const form = reactive({ equipment_id: '', part_id: '', symptom: '', site_check_note: '' })
const submitting = ref(false)
const createError = ref('')

async function openCreate() {
  showCreate.value = true
  createError.value = ''
  if (!equipments.value.length) {
    try {
      ;[equipments.value, parts.value] = await Promise.all([api.listEquipments(), api.listParts()])
      form.equipment_id = form.equipment_id || equipments.value[0]?.id || ''
      form.part_id = form.part_id || parts.value[0]?.id || ''
    } catch (e) {
      createError.value = e.message
    }
  }
}

async function submitCreate() {
  if (!form.equipment_id || !form.part_id || !form.symptom.trim()) {
    createError.value = '설비, 부품, 증상은 필수입니다.'
    return
  }
  submitting.value = true
  createError.value = ''
  try {
    const wr = await api.createWorkRequest({
      tenant_id: 'T-001',
      equipment_id: form.equipment_id,
      part_id: form.part_id,
      symptom: form.symptom.trim(),
      site_check_note: form.site_check_note.trim(),
      requested_by: session.user.value.id,
    })
    showCreate.value = false
    form.symptom = ''
    form.site_check_note = ''
    router.push({ name: 'work-request-detail', params: { id: wr.id } })
  } catch (e) {
    createError.value = e.message || '생성 실패'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="stack" style="gap: 20px">
    <div class="row between">
      <div>
        <h1>작업요청 목록 / 대시보드</h1>
        <p class="muted small">반도체 설비 부품 교체 요청 → 에이전트 분석 → 안전관리자 승인</p>
      </div>
      <button class="primary" @click="openCreate">+ 새 작업요청</button>
    </div>

    <div v-if="error" class="alert error">{{ error }}</div>

    <!-- KPI -->
    <section class="kpis">
      <div v-for="k in kpis" :key="k.label" class="card kpi" :class="k.tone">
        <div class="muted small">{{ k.label }}</div>
        <div class="kpi-value">{{ k.value }}<span class="unit">{{ k.unit }}</span></div>
        <div v-if="k.sub" class="small kpi-sub">{{ k.sub }}</div>
      </div>
      <div v-if="summary" class="card kpi">
        <div class="muted small">반려 사유 TOP</div>
        <ul class="reasons">
          <li v-for="r in summary.reject_reasons_top" :key="r.reason">
            <span>{{ r.reason }}</span><strong>{{ r.count }}</strong>
          </li>
          <li v-if="!summary.reject_reasons_top?.length" class="muted">없음</li>
        </ul>
      </div>
    </section>

    <!-- 목록 -->
    <section class="card" style="padding: 0">
      <div class="row between" style="padding: 12px 16px">
        <h2>요청 목록 <span class="muted small">총 {{ total }}건</span></h2>
        <div class="row">
          <select v-model="statusFilter" style="width: 170px" @change="load">
            <option value="">전체 상태</option>
            <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
          </select>
          <button class="sm" :disabled="loading" @click="load">새로고침</button>
        </div>
      </div>
      <div style="overflow-x: auto">
        <table>
          <thead>
            <tr>
              <th>요청 ID</th>
              <th>설비</th>
              <th>부품</th>
              <th>증상</th>
              <th>상태</th>
              <th>에이전트 진행률</th>
              <th>승인자</th>
              <th>요청일시</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading && !items.length"><td colspan="8" class="empty">불러오는 중…</td></tr>
            <tr v-else-if="!items.length"><td colspan="8" class="empty">작업요청이 없습니다.</td></tr>
            <tr
              v-for="it in items"
              :key="it.id"
              class="clickable"
              @click="router.push({ name: 'work-request-detail', params: { id: it.id } })"
            >
              <td class="mono">{{ it.id }}</td>
              <td>{{ it.equipment_name || it.equipment_id }}<div class="muted small mono">{{ it.equipment_id }}</div></td>
              <td class="mono">{{ it.part_no || it.part_id }}</td>
              <td class="symptom">{{ it.symptom }}</td>
              <td><StatusChip :status="it.status" /></td>
              <td>
                <div class="row">
                  <div class="progress"><i :style="{ width: progressOf(it).pct + '%' }"></i></div>
                  <span class="small muted">{{ progressOf(it).done }}/{{ progressOf(it).total }}</span>
                </div>
              </td>
              <td class="small">{{ it.approver_id || '—' }}</td>
              <td class="small muted">{{ new Date(it.created_at).toLocaleString('ko-KR') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 새 작업요청 모달 -->
    <div v-if="showCreate" class="modal-backdrop" @click.self="showCreate = false">
      <div class="card modal stack" style="gap: 12px">
        <div class="row between">
          <h2>새 작업요청</h2>
          <button class="sm" @click="showCreate = false">닫기</button>
        </div>
        <div v-if="createError" class="alert error">{{ createError }}</div>
        <div class="grid2">
          <div>
            <label>설비</label>
            <select v-model="form.equipment_id">
              <option v-for="e in equipments" :key="e.id" :value="e.id">{{ e.name }} ({{ e.id }}{{ e.substance ? ', ' + e.substance : '' }})</option>
            </select>
          </div>
          <div>
            <label>부품</label>
            <select v-model="form.part_id">
              <option v-for="p in parts" :key="p.id" :value="p.id">{{ p.part_no }} [{{ p.grade }}] 재고 {{ p.stock }}</option>
            </select>
          </div>
        </div>
        <div>
          <label>증상 *</label>
          <input v-model="form.symptom" placeholder="예) 가스 유량 이상, 밸브 누설 의심" />
        </div>
        <div>
          <label>현장 확인 메모</label>
          <textarea v-model="form.site_check_note" placeholder="예) 현장 확인 결과 밸브 시트 마모"></textarea>
        </div>
        <div class="row" style="justify-content: flex-end">
          <button @click="showCreate = false">취소</button>
          <button class="primary" :disabled="submitting" @click="submitCreate">{{ submitting ? '생성 중…' : '요청 생성' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kpis { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
@media (max-width: 960px) { .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.kpi-value { font-size: 28px; font-weight: 700; margin-top: 4px; }
.kpi-value .unit { font-size: 13px; font-weight: 500; color: var(--muted); margin-left: 3px; }
.kpi.warning .kpi-value { color: var(--warning); }
.kpi.success .kpi-value { color: var(--success); }
.kpi-sub { color: var(--success); }
.reasons { list-style: none; margin: 6px 0 0; padding: 0; }
.reasons li { display: flex; justify-content: space-between; padding: 2px 0; font-size: 13px; }
.symptom { max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
</style>

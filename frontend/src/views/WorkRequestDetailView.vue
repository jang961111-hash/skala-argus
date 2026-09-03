<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../api/client'
import { session } from '../store/session'
import StatusChip from '../components/StatusChip.vue'
import AgentTimeline from '../components/AgentTimeline.vue'
import ApprovalPanel from '../components/ApprovalPanel.vue'

const props = defineProps({ id: { type: String, required: true } })

const wr = ref(null)
const equipments = ref([])
const parts = ref([])
const loading = ref(false)
const error = ref('')
const notice = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    wr.value = await api.getWorkRequest(props.id)
    if (!equipments.value.length) {
      ;[equipments.value, parts.value] = await Promise.all([api.listEquipments(), api.listParts()])
    }
  } catch (e) {
    error.value = e.status === 404 ? '작업요청을 찾을 수 없습니다.' : e.message
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => props.id, load)

const equipment = computed(() => equipments.value.find((e) => e.id === wr.value?.equipment_id))
const part = computed(() => parts.value.find((p) => p.id === wr.value?.part_id))

// AgentTimeline 이 run 완료(REVIEW) 또는 실행 시작 시 상세를 다시 읽어 status 동기화
function onRunChanged() {
  load()
}
function onApprovalDone(msg) {
  notice.value = msg
  load()
  setTimeout(() => (notice.value = ''), 4000)
}
</script>

<template>
  <div v-if="error" class="stack">
    <div class="alert error">{{ error }}</div>
    <RouterLink to="/">← 목록으로</RouterLink>
  </div>
  <div v-else-if="!wr" class="empty">불러오는 중…</div>
  <div v-else class="stack" style="gap: 16px">
    <!-- 헤더: 요청 정보 -->
    <section class="card">
      <div class="row between" style="align-items: flex-start">
        <div>
          <RouterLink to="/" class="small">← 작업요청 목록</RouterLink>
          <div class="row" style="margin-top: 6px">
            <h1 class="mono">{{ wr.id }}</h1>
            <StatusChip :status="wr.status" />
          </div>
        </div>
        <div class="small muted" style="text-align: right">
          요청자 {{ wr.requested_by }}<br />
          {{ new Date(wr.created_at).toLocaleString('ko-KR') }}
        </div>
      </div>
      <div class="info-grid">
        <div>
          <label>설비</label>
          <div>{{ equipment?.name || wr.equipment_id }} <span class="muted small mono">{{ wr.equipment_id }}</span></div>
          <div v-if="equipment?.substance" class="small muted">물질: {{ equipment.substance }} · 유형: {{ equipment.type }}</div>
        </div>
        <div>
          <label>부품</label>
          <div class="mono">{{ part?.part_no || wr.part_id }}</div>
          <div v-if="part" class="small muted">{{ part.grade }} · 재고 {{ part.stock }} · 유독가스 {{ part.toxic_gas_allowed ? '허용' : '불가' }}</div>
        </div>
        <div>
          <label>증상</label>
          <div>{{ wr.symptom }}</div>
        </div>
        <div>
          <label>현장 확인 메모</label>
          <div>{{ wr.site_check_note || '—' }}</div>
        </div>
      </div>
    </section>

    <div v-if="notice" class="alert success">{{ notice }}</div>

    <div class="layout">
      <!-- 중앙: 에이전트 타임라인 -->
      <AgentTimeline
        :work-request="wr"
        @run-changed="onRunChanged"
      />

      <!-- 우측: 승인 패널 -->
      <ApprovalPanel
        :work-request="wr"
        :run="wr.latest_run"
        :role="session.state.role"
        :user="session.user.value"
        @changed="onApprovalDone"
      />
    </div>
  </div>
</template>

<style scoped>
.info-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-top: 14px; }
@media (max-width: 960px) { .info-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 16px; align-items: start; }
@media (max-width: 1024px) { .layout { grid-template-columns: 1fr; } }
</style>

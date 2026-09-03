<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import { STATUS, productTypeLabel, errorText } from '../../constants/domain'
import StatusChip from '../../components/StatusChip.vue'

// 안전관리자 GNB "처리 이력" — 승인·거절이 끝난 요청 (status 콤마 다중 지정)
const router = useRouter()

const items = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const list = await api.listWorkRequests({
      status: `${STATUS.APPROVED},${STATUS.REJECTED}`, page: 0, size: 100,
    })
    items.value = list.content
  } catch (e) {
    error.value = errorText(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const fmtDateTime = (iso) =>
  iso ? new Date(iso).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'
</script>

<template>
  <div class="stack" style="gap: 16px">
    <div>
      <h1>처리 이력</h1>
      <p class="muted small">승인·거절이 완료된 요청 기록입니다.</p>
    </div>

    <div v-if="error" class="alert error">{{ error }}</div>

    <section class="card" style="padding: 0">
      <table>
        <thead>
          <tr>
            <th>설비 / 제품</th>
            <th>제품 유형</th>
            <th>요청자</th>
            <th>결과</th>
            <th>처리일시</th>
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
            <td><StatusChip :status="it.status" /></td>
            <td>{{ fmtDateTime(it.updatedAt) }}</td>
          </tr>
          <tr v-if="!items.length && !loading"><td colspan="5" class="empty">처리 이력이 없습니다.</td></tr>
          <tr v-if="loading && !items.length"><td colspan="5" class="empty">불러오는 중…</td></tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { AGENTS, AGENT_CODE, docTypeLabel } from '../constants/domain'

// S_02 전용 — 안전관리자는 AI 결과를 읽기만 한다 (results[].editable === false).
// 엔지니어가 수정한 항목은 "엔지니어 수정" 배지로 AI 원본과 구분한다.
const props = defineProps({
  run: { type: Object, default: null },
})

const resultOf = (code) => (props.run?.results || []).find((r) => r.agentCode === code) || null

const AGENT_CODE_A3 = AGENT_CODE.A3
const hasRun = computed(() => Boolean(props.run))
</script>

<template>
  <section class="card stack" style="gap: 14px">
    <div class="row between">
      <h2>AI 결과물 (읽기 전용)</h2>
      <span class="muted small mono">{{ run?.id || '실행 이력 없음' }}</span>
    </div>

    <p v-if="!hasRun" class="muted small">AI 검증 결과가 없습니다.</p>

    <div v-for="a in AGENTS" v-else :key="a.code" class="block">
      <div class="row" style="gap: 8px">
        <span class="code">{{ a.code }}</span>
        <strong>{{ a.title }}</strong>
        <span v-if="resultOf(a.code)?.edited" class="edited">엔지니어 수정</span>
      </div>

      <p v-if="!resultOf(a.code)" class="muted small">결과 없음</p>

      <!-- A3: 문서형 -->
      <ul v-else-if="a.code === AGENT_CODE_A3" class="list">
        <li v-for="d in resultOf(a.code).payloadJson.documents || []" :key="d.docId">
          <div class="row" style="gap: 6px">
            📄 <strong>{{ d.name }}</strong>
            <span class="type">{{ docTypeLabel(d.type) }}</span>
            <span v-if="d.edited" class="edited sm">수정</span>
          </div>
          <p class="content">{{ d.content }}</p>
        </li>
      </ul>

      <!-- A1·A2: 항목형 -->
      <ul v-else class="list">
        <li v-for="it in resultOf(a.code).payloadJson.items || []" :key="it.itemId">
          {{ it.text }}
          <span v-if="it.edited" class="edited sm">수정</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.block { border-top: 1px solid var(--border); padding-top: 12px; display: flex; flex-direction: column; gap: 8px; }
.block:first-of-type { border-top: 0; padding-top: 0; }
.code {
  font-size: 12px; font-weight: 700; color: var(--primary); background: var(--primary-soft);
  border-radius: 6px; padding: 2px 8px;
}
.edited { font-size: 11px; font-weight: 600; background: var(--warning-soft); color: var(--warning); padding: 2px 8px; border-radius: 999px; }
.edited.sm { padding: 1px 6px; margin-left: 6px; }
.type { font-size: 11px; background: #eef0f3; color: #4b5563; border-radius: 4px; padding: 1px 6px; }
.list { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 6px; font-size: 13px; }
.content { color: var(--muted); font-size: 12px; margin-top: 2px; }
</style>

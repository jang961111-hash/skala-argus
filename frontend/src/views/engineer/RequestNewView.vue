<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../../api/client'
import {
  PRODUCT_TYPES, PRODUCT_TYPE, specFieldsFor, LINES, EQUIPMENT_SUGGESTIONS,
  PHOTO, STATUS, errorText,
} from '../../constants/domain'
import PhotoStrip from '../../components/PhotoStrip.vue'

// WRA_E_02 부품 교체 요청 등록
// ?id=<uuid> 로 진입하면 DRAFT 이어쓰기.
// 사진은 요청 생성 이후에만 올릴 수 있어(계약 §8-7) 저장 시 DRAFT 를 먼저 만들고 업로드한다.
const router = useRouter()
const route = useRoute()

const error = ref('')
const notice = ref('')
const busy = ref(false)
const existing = ref(null)          // { id, requestNo, status }
const uploadedPhotos = ref([])

const form = reactive({
  equipment: '', line: '', substance: '',
  operatingCondition: { temperature: '', pressure: '' },
  productName: '', productType: PRODUCT_TYPE.VALVE, specJson: {},
  symptom: '', siteMemo: '',
})

// 제품 유형이 바뀌면 specJson 키가 통째로 바뀐다 (계약 §2 스키마 검증 대상).
const specFields = computed(() => specFieldsFor(form.productType))
function syncSpecKeys() {
  const allowed = new Set(specFields.value.map((f) => f.key))
  for (const k of Object.keys(form.specJson)) if (!allowed.has(k)) delete form.specJson[k]
  for (const f of specFields.value) if (!(f.key in form.specJson)) form.specJson[f.key] = ''
}
watch(() => form.productType, syncSpecKeys)

// ---------- 사진 (업로드 전 로컬 대기) ----------
const staged = ref([]) // { file, name, size, dataUrl }
const dragOver = ref(false)
const photoCount = computed(() => uploadedPhotos.value.length + staged.value.length)

function addFiles(fileList) {
  error.value = ''
  for (const file of Array.from(fileList || [])) {
    if (!PHOTO.ACCEPT.includes(file.type)) { error.value = 'jpg · png · webp 이미지만 첨부할 수 있습니다.'; continue }
    if (file.size > PHOTO.MAX_SIZE) { error.value = `${file.name}: 파일당 10MB 이하만 첨부할 수 있습니다.`; continue }
    if (photoCount.value >= PHOTO.MAX_COUNT) { error.value = `사진은 요청당 최대 ${PHOTO.MAX_COUNT}장입니다.`; break }
    const reader = new FileReader()
    reader.onload = () => {
      file.__dataUrl = reader.result // Mock 썸네일용. 실제 서버는 thumbnailUrl 을 내려준다.
      staged.value.push({ file, name: file.name, size: file.size, dataUrl: reader.result })
    }
    reader.readAsDataURL(file)
  }
}
function onDrop(e) {
  dragOver.value = false
  addFiles(e.dataTransfer?.files)
}
const removeStaged = (i) => staged.value.splice(i, 1)
const fmtSize = (n) => (n >= 1048576 ? `${(n / 1048576).toFixed(1)}MB` : `${Math.max(1, Math.round(n / 1024))}KB`)

onMounted(async () => {
  syncSpecKeys()
  const id = route.query.id
  if (typeof id === 'string' && id) {
    try {
      const wr = await api.getWorkRequest(id)
      if (wr.status !== STATUS.DRAFT) { router.replace(`/requests/${id}/result`); return }
      existing.value = { id: wr.id, requestNo: wr.requestNo, status: wr.status }
      Object.assign(form, {
        equipment: wr.equipment || '', line: wr.line || '', substance: wr.substance || '',
        productName: wr.productName || '', productType: wr.productType || PRODUCT_TYPE.VALVE,
        symptom: wr.symptom || '', siteMemo: wr.siteMemo || '',
      })
      form.operatingCondition = {
        temperature: wr.operatingCondition?.temperature || '',
        pressure: wr.operatingCondition?.pressure || '',
      }
      form.specJson = { ...(wr.specJson || {}) }
      syncSpecKeys()
      uploadedPhotos.value = wr.photos || []
      notice.value = `작성 중이던 ${wr.requestNo} 를 이어서 편집합니다.`
    } catch (e) {
      error.value = errorText(e)
    }
  } else {
    form.line = LINES[0]
  }
})

function payload() {
  const specJson = {}
  for (const f of specFields.value) specJson[f.key] = String(form.specJson[f.key] || '').trim()
  return {
    equipment: form.equipment.trim(), line: form.line, substance: form.substance.trim(),
    operatingCondition: {
      temperature: form.operatingCondition.temperature.trim(),
      pressure: form.operatingCondition.pressure.trim(),
    },
    productName: form.productName.trim(), productType: form.productType, specJson,
    symptom: form.symptom.trim(), siteMemo: form.siteMemo.trim(),
  }
}

// 필수 검증은 서버(draft=false)가 하지만, 화면에서도 먼저 막아 왕복을 줄인다.
function localMissing() {
  const missing = []
  if (!form.equipment.trim()) missing.push('설비')
  if (!form.line) missing.push('라인')
  if (!form.substance.trim()) missing.push('물질')
  if (!form.operatingCondition.temperature.trim()) missing.push('운전 조건(온도)')
  if (!form.operatingCondition.pressure.trim()) missing.push('운전 조건(압력)')
  if (!form.productName.trim()) missing.push('제품명')
  for (const f of specFields.value) if (!String(form.specJson[f.key] || '').trim()) missing.push(f.label)
  return missing
}

// 요청이 없으면 만들고, 있으면 갱신한다. 사진 업로드 대상 id 를 돌려준다.
async function persist(draft) {
  if (existing.value) {
    const wr = await api.updateWorkRequest(existing.value.id, payload())
    existing.value = { id: wr.id, requestNo: wr.requestNo, status: wr.status }
    return wr
  }
  const wr = await api.createWorkRequest(payload(), draft)
  existing.value = { id: wr.id, requestNo: wr.requestNo, status: wr.status }
  return wr
}

async function uploadStaged(id) {
  if (!staged.value.length) return
  const files = staged.value.map((s) => s.file)
  const created = await api.uploadPhotos(id, files)
  uploadedPhotos.value.push(...created)
  staged.value = []
}

// 임시 저장 → DRAFT (필수 검증 생략)
async function saveDraft() {
  error.value = ''
  notice.value = ''
  busy.value = true
  try {
    const wr = await persist(true)
    await uploadStaged(wr.id)
    notice.value = `임시 저장했습니다. (${wr.requestNo} · 작성 중)`
  } catch (e) {
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}

// 필수 완료 → 요청 확정 + POST /agent-runs → E_03
async function startVerification() {
  error.value = ''
  notice.value = ''
  const missing = localMissing()
  if (missing.length) {
    error.value = `필수 항목을 입력하세요: ${missing.join(', ')}`
    return
  }
  busy.value = true
  try {
    const wr = await persist(false)
    await uploadStaged(wr.id)
    await api.startAgentRun(wr.id)
    router.push(`/requests/${wr.id}/run`)
  } catch (e) {
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="form-col stack" style="gap: 16px">
    <div>
      <h1>부품 교체 요청 등록</h1>
      <p class="muted small">
        ‘AI 검증 시작’ 시 서버가 입력 전체(설비·라인·물질·운전 조건·제품명·유형·스펙·사진 메타)로 스냅샷을 구성해 에이전트에 전달합니다.
      </p>
      <p v-if="existing" class="muted small mono">{{ existing.requestNo }}</p>
    </div>

    <div v-if="notice" class="alert info">{{ notice }}</div>
    <div v-if="error" class="alert error">{{ error }}</div>

    <section class="card stack" style="gap: 12px">
      <h2>요청 기본 정보</h2>
      <div class="grid2">
        <div>
          <label for="eq">설비 <span class="req">*</span></label>
          <input id="eq" v-model="form.equipment" list="equipment-list" placeholder="예: 가스캐비닛#2" />
          <datalist id="equipment-list">
            <option v-for="e in EQUIPMENT_SUGGESTIONS" :key="e" :value="e" />
          </datalist>
        </div>
        <div>
          <label for="ln">라인 <span class="req">*</span></label>
          <select id="ln" v-model="form.line">
            <option value="">라인 선택</option>
            <option v-for="l in LINES" :key="l" :value="l">{{ l }}</option>
          </select>
        </div>
        <div>
          <label for="sb">물질 <span class="req">*</span></label>
          <input id="sb" v-model="form.substance" placeholder="예: SiH4" />
        </div>
        <div>
          <label for="temp">운전 조건 · 온도 <span class="req">*</span></label>
          <input id="temp" v-model="form.operatingCondition.temperature" placeholder="예: 상온" />
        </div>
      </div>
      <div>
        <label for="press">운전 조건 · 압력 <span class="req">*</span></label>
        <input id="press" v-model="form.operatingCondition.pressure" placeholder="예: 3000 psi" />
      </div>
    </section>

    <section class="card stack" style="gap: 12px">
      <h2>제품 정보</h2>
      <div class="grid2">
        <div>
          <label for="pn">제품명 <span class="req">*</span> <span class="hint">→ AI 전송 핵심 키</span></label>
          <input id="pn" v-model="form.productName" placeholder="예: SS-8-VCR" />
        </div>
        <div>
          <label for="pty">제품 유형 <span class="req">*</span></label>
          <select id="pty" v-model="form.productType">
            <option v-for="t in PRODUCT_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
      </div>

      <div class="dyn">
        <p class="small muted">유형별 스펙 — 선택한 유형에 따라 필드가 바뀝니다. (서버가 유형별 스키마를 검증합니다)</p>
        <div class="grid2">
          <div v-for="f in specFields" :key="f.key">
            <label :for="'spec-' + f.key">{{ f.label }} <span class="req">*</span></label>
            <input :id="'spec-' + f.key" v-model="form.specJson[f.key]" :placeholder="f.placeholder" />
          </div>
        </div>
      </div>
    </section>

    <section class="card stack" style="gap: 12px">
      <h2>제품 사진 <span class="muted small">(현장사진 아님 · 최대 {{ PHOTO.MAX_COUNT }}장 · 파일당 10MB)</span></h2>
      <label
        class="dropzone"
        :class="{ over: dragOver, full: photoCount >= PHOTO.MAX_COUNT }"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
      >
        <input
          type="file"
          :accept="PHOTO.ACCEPT_ATTR"
          multiple
          hidden
          :disabled="photoCount >= PHOTO.MAX_COUNT"
          @change="addFiles($event.target.files)"
        />
        <template v-if="photoCount >= PHOTO.MAX_COUNT">첨부 한도({{ PHOTO.MAX_COUNT }}장)에 도달했습니다</template>
        <template v-else>📷 제품 사진 업로드 — 드래그하거나 클릭해 선택 ({{ photoCount }}/{{ PHOTO.MAX_COUNT }})</template>
      </label>

      <div v-if="staged.length" class="strip">
        <figure v-for="(s, i) in staged" :key="s.name + i" class="thumb">
          <img :src="s.dataUrl" :alt="s.name" />
          <figcaption class="small">
            {{ s.name }}<br /><span class="muted">{{ fmtSize(s.size) }}</span>
            <button class="sm" type="button" @click="removeStaged(i)">삭제</button>
          </figcaption>
        </figure>
      </div>
      <PhotoStrip v-if="uploadedPhotos.length" :photos="uploadedPhotos" title="업로드 완료" />
    </section>

    <section class="card stack" style="gap: 12px">
      <h2>증상 · 메모</h2>
      <div>
        <label for="sy">증상</label>
        <textarea id="sy" v-model="form.symptom" placeholder="고장 증상"></textarea>
      </div>
      <div>
        <label for="sm">현장 확인 메모</label>
        <textarea id="sm" v-model="form.siteMemo" placeholder="점검 결과"></textarea>
      </div>
    </section>

    <div class="row" style="justify-content: flex-end; gap: 8px">
      <button :disabled="busy" @click="saveDraft">임시 저장</button>
      <button class="primary" :disabled="busy" @click="startVerification">
        {{ busy ? '처리 중…' : 'AI 검증 시작 ▶' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
/* 폼형 화면 컬럼: 최대 폭 760px (figma_build_guide §1) */
.form-col { max-width: 760px; margin: 0 auto; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.req { color: var(--danger); }
.hint { color: var(--primary); font-weight: 600; }
.dyn { border-top: 1px dashed var(--border); padding-top: 12px; display: flex; flex-direction: column; gap: 8px; }
.dropzone {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  border: 1px dashed var(--border); border-radius: 10px; padding: 26px; cursor: pointer;
  color: var(--muted); background: #fafbfc; margin: 0; font-size: 13px;
}
.dropzone.over { border-color: var(--primary); background: var(--primary-soft); color: var(--primary); }
.dropzone.full { cursor: not-allowed; opacity: 0.6; }
.strip { display: flex; flex-wrap: wrap; gap: 10px; }
.thumb { margin: 0; width: 130px; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.thumb img { width: 100%; height: 86px; object-fit: cover; display: block; }
figcaption { padding: 6px 8px; word-break: break-all; display: flex; flex-direction: column; gap: 6px; }
@media (max-width: 700px) { .grid2 { grid-template-columns: 1fr; } }
</style>

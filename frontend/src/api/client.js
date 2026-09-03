/**
 * API 클라이언트 — FE 가 백엔드에 대해 아는 유일한 것은 CONTRACT.md 의 JSON 계약뿐이다.
 *
 * - 기본: axios 로 /api/v1 호출 (개발 시 vite proxy → FastAPI:8000)
 * - VITE_USE_MOCK=true: HTTP 대신 src/mock/data.js 기반 인메모리 Mock 이 같은 계약(경로·상태코드·스키마)으로 응답.
 *   Mock 은 CONTRACT.md 의 "Mock 동작" 을 그대로 시뮬레이션한다:
 *   POST …/agent-runs 직후 steps 4개 모두 PENDING → GET /agent-runs/{id} 호출마다 다음 step 하나 DONE
 *   (SPEC→LEGAL→SAFETY_DOC→VENDOR) → 4개 DONE 이면 overall_status=REVIEW, work_request.status=REVIEW.
 */
import axios from 'axios'
import * as mock from '../mock/data'

export const USE_MOCK = String(import.meta.env.VITE_USE_MOCK).toLowerCase() === 'true'
const BASE_URL = import.meta.env.VITE_API_BASE || '/api/v1'

// ---------------------------------------------------------------------------
// HTTP 구현
// ---------------------------------------------------------------------------
const http = axios.create({ baseURL: BASE_URL, timeout: 15000 })

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail || err.response?.data?.message || err.message
    return Promise.reject(Object.assign(new Error(detail), { status, data: err.response?.data }))
  },
)

const httpApi = {
  getDashboardSummary: () => http.get('/dashboard/summary'),
  listWorkRequests: (params = {}) => http.get('/work-requests', { params }),
  createWorkRequest: (body) => http.post('/work-requests', body),
  getWorkRequest: (id) => http.get(`/work-requests/${id}`),
  startAgentRun: (id) => http.post(`/work-requests/${id}/agent-runs`),
  getAgentRun: (runId) => http.get(`/agent-runs/${runId}`),
  submitApproval: (id, body = {}) => http.patch(`/work-requests/${id}/submit-approval`, body),
  createApproval: (id, body) => http.post(`/work-requests/${id}/approvals`, body),
  getDocument: (docId) => http.get(`/documents/${docId}`),
  searchLaws: (params) => http.get('/laws/search', { params }),
  listEquipments: () => http.get('/equipments'),
  listParts: () => http.get('/parts'),
}

// ---------------------------------------------------------------------------
// Mock 구현 (동일 계약)
// ---------------------------------------------------------------------------
const clone = (v) => JSON.parse(JSON.stringify(v))
const delay = (ms = 250) => new Promise((r) => setTimeout(r, ms))
const nowIso = () => new Date().toISOString()

function apiError(status, detail) {
  return Object.assign(new Error(detail), { status, data: { detail } })
}

const db = {
  workRequests: clone(mock.workRequests),
  runs: {},
  dashboard: clone(mock.dashboardSummary),
  seq: { wr: 12, run: 42, ap: 7 },
}
// 기존 샘플 run 등록
for (const wr of db.workRequests) if (wr.latest_run) db.runs[wr.latest_run.run_id] = wr.latest_run

const findWr = (id) => db.workRequests.find((w) => w.id === id)

function toSummary(wr) {
  const eq = mock.equipments.find((e) => e.id === wr.equipment_id)
  const part = mock.parts.find((p) => p.id === wr.part_id)
  const steps = wr.latest_run?.steps || []
  const done = steps.filter((s) => s.status === 'DONE').length
  const approval = wr.approvals?.[wr.approvals.length - 1]
  return {
    id: wr.id,
    equipment_id: wr.equipment_id,
    equipment_name: eq?.name || wr.equipment_id,
    part_id: wr.part_id,
    part_no: part?.part_no || wr.part_id,
    symptom: wr.symptom,
    status: wr.status,
    agent_progress: { done, total: 4 },
    approver_id: approval?.approver_id || (wr.latest_run ? 'U-002' : null),
    requested_by: wr.requested_by,
    created_at: wr.created_at,
    updated_at: wr.updated_at,
  }
}

const mockApi = {
  async getDashboardSummary() {
    await delay()
    return clone(db.dashboard)
  },

  async listWorkRequests(params = {}) {
    await delay()
    let items = db.workRequests
    if (params.status) items = items.filter((w) => w.status === params.status)
    const page = Number(params.page || 1)
    const size = Number(params.size || 20)
    const total = items.length
    items = items.slice((page - 1) * size, page * size).map(toSummary)
    return { items, total }
  },

  async createWorkRequest(body) {
    await delay()
    const ts = nowIso()
    const id = `WR-${ts.slice(0, 10).replace(/-/g, '')}-${String(db.seq.wr++).padStart(3, '0')}`
    const wr = {
      id, tenant_id: 'T-001',
      equipment_id: body.equipment_id, part_id: body.part_id,
      symptom: body.symptom, site_check_note: body.site_check_note || '',
      requested_by: body.requested_by || 'U-001',
      status: 'REQUESTED', created_at: ts, updated_at: ts,
      latest_run: null, approvals: [],
    }
    db.workRequests.unshift(wr)
    db.dashboard.in_progress += 1
    const { latest_run, approvals, ...plain } = wr
    return clone(plain)
  },

  async getWorkRequest(id) {
    await delay()
    const wr = findWr(id)
    if (!wr) throw apiError(404, `work request ${id} not found`)
    return clone(wr)
  },

  async startAgentRun(id) {
    await delay()
    const wr = findWr(id)
    if (!wr) throw apiError(404, `work request ${id} not found`)
    if (['APPROVED', 'DONE'].includes(wr.status)) throw apiError(409, `이미 ${wr.status} 상태입니다`)
    const runId = `RUN-${String(db.seq.run++).padStart(4, '0')}`
    const run = mock.makeRun(runId, id, 0, 'RUNNING')
    run.created_at = nowIso()
    run.steps.forEach((s) => { s.status = 'PENDING'; s.started_at = null; s.completed_at = null; s.result = null })
    db.runs[runId] = run
    wr.latest_run = run
    wr.status = 'RUNNING'
    wr.updated_at = nowIso()
    return { run_id: runId, overall_status: 'RUNNING' }
  },

  // 호출마다 다음 step 하나가 DONE 으로 전이 → 타임라인이 "살아 움직이게"
  async getAgentRun(runId) {
    await delay()
    const run = db.runs[runId]
    if (!run) throw apiError(404, `agent run ${runId} not found`)
    if (run.overall_status === 'RUNNING') {
      const idx = run.steps.findIndex((s) => s.status !== 'DONE')
      if (idx >= 0) {
        const done = mock.completedSteps[idx]
        const ts = nowIso()
        run.steps[idx] = { ...clone(done), started_at: run.steps[idx].started_at || ts, completed_at: ts }
        if (run.steps[idx + 1]) { run.steps[idx + 1].status = 'RUNNING'; run.steps[idx + 1].started_at = ts }
      }
      if (run.steps.every((s) => s.status === 'DONE')) {
        run.overall_status = 'REVIEW'
        run.summary = mock.runSummary
        run.completed_at = nowIso()
        const wr = findWr(run.work_request_id)
        if (wr) { wr.status = 'REVIEW'; wr.updated_at = nowIso() }
      }
    }
    return clone(run)
  },

  async submitApproval(id) {
    await delay()
    const wr = findWr(id)
    if (!wr) throw apiError(404, `work request ${id} not found`)
    if (!wr.latest_run || wr.latest_run.overall_status !== 'REVIEW') throw apiError(409, '에이전트 실행이 완료되지 않았습니다')
    if (!wr.symptom || !wr.site_check_note) throw apiError(422, '증상·현장 확인 메모가 필요합니다')
    wr.status = 'PENDING_APPROVAL'
    wr.updated_at = nowIso()
    db.dashboard.pending_approval += 1
    const { latest_run, approvals, ...plain } = wr
    return clone(plain)
  },

  async createApproval(id, body) {
    await delay()
    const wr = findWr(id)
    if (!wr) throw apiError(404, `work request ${id} not found`)
    const keys = ['WORK_PERMIT', 'RISK_ASSESSMENT', 'LOTO_GAS_ISOLATION', 'GAS_DETECTOR_CHECK']
    const allChecked = keys.every((k) => body.checklist?.[k] === true)
    if (body.decision === 'APPROVE' && !allChecked) throw apiError(409, '필수 체크리스트 4항목을 모두 확인해야 승인할 수 있습니다')
    const approval = {
      approval_id: `AP-${String(db.seq.ap++).padStart(4, '0')}`,
      work_request_id: id,
      approver_id: body.approver_id || 'U-002',
      decision: body.decision,
      checklist: { ...body.checklist },
      comment: body.comment || '',
      decided_at: nowIso(),
    }
    wr.approvals.push(approval)
    if (body.decision === 'APPROVE') {
      wr.status = 'APPROVED'
      db.dashboard.pending_approval = Math.max(0, db.dashboard.pending_approval - 1)
      db.dashboard.in_progress = Math.max(0, db.dashboard.in_progress - 1)
      db.dashboard.completed_this_month += 1
      // 데모: 승인 시간 갱신 (요청 생성 → 승인까지 시간 반영)
      const hours = Math.max(0.1, (Date.now() - new Date(wr.created_at).getTime()) / 36e5)
      db.dashboard.avg_approval_hours = Math.round(((db.dashboard.avg_approval_hours * 4 + hours) / 5) * 10) / 10
    } else if (body.decision === 'REJECT') {
      wr.status = 'REJECTED'
      db.dashboard.pending_approval = Math.max(0, db.dashboard.pending_approval - 1)
      const reason = db.dashboard.reject_reasons_top.find((r) => r.reason === '서류 누락')
      if (reason) reason.count += 1
    } else {
      // REQUEST_INFO: 보완요청 → 엔지니어가 다시 승인 요청할 수 있도록 REVIEW 로 되돌림
      wr.status = 'REVIEW'
      db.dashboard.pending_approval = Math.max(0, db.dashboard.pending_approval - 1)
    }
    wr.updated_at = nowIso()
    return clone(approval)
  },

  async getDocument(docId) {
    await delay()
    const types = { 'DOC-0101': 'WORK_PERMIT', 'DOC-0102': 'RISK_ASSESSMENT', 'DOC-0103': 'RFQ' }
    if (!types[docId]) throw apiError(404, `document ${docId} not found`)
    return { doc_id: docId, type: types[docId], draft_uri: `/docs/${docId}.md`, content: `[${types[docId]}] 초안 — Mock 문서 본문` }
  },

  async searchLaws(params = {}) {
    await delay()
    const q = (params.q || '').trim()
    const items = mock.laws.filter((l) => !q || l.law.includes(q) || l.title.includes(q) || l.article.includes(q))
    return { items: clone(items) }
  },

  async listEquipments() { await delay(); return clone(mock.equipments) },
  async listParts() { await delay(); return clone(mock.parts) },
}

const api = USE_MOCK ? mockApi : httpApi
export default api

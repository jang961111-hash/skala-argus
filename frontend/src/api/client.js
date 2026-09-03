/**
 * API 클라이언트 — FE 가 백엔드에 대해 아는 유일한 것은 CONTRACT.md v3.0 의 계약뿐이다.
 *
 * - 기본: axios 로 /api/v1 호출 (개발 시 vite proxy → FastAPI:8000), Authorization: Bearer {accessToken}
 * - VITE_USE_MOCK=true: HTTP 대신 src/mock/data.js 기반 인메모리 Mock 이 같은 계약으로 응답
 *
 * mockApi 와 httpApi 는 시그니처가 동일하다. 화면은 어느 쪽이 붙었는지 몰라야 한다.
 *
 * 오류는 양쪽 모두 Error 에 {status, code, message, fieldErrors} 를 실어 reject 한다 (계약 §1.1).
 */
import axios from 'axios'
import * as mock from '../mock/data'
import { session } from '../store/session'
import {
  STATUS, RUN_STATUS, STEP_STATUS, AGENT_CODE, AGENT_CODES, ROLE, DECISION,
  NEXT_ACTION, ERROR_CODE, IMMUTABLE_STATUSES, SUBMITTABLE_STATUSES,
  DEFAULT_POLL_INTERVAL_MS, PHOTO, REJECT_REASON_MIN, FALLBACK_REDIRECT, specFieldsFor,
} from '../constants/domain'

export const USE_MOCK = String(import.meta.env.VITE_USE_MOCK).toLowerCase() === 'true'
const BASE_URL = import.meta.env.VITE_API_BASE || '/api/v1'

// ---------------------------------------------------------------------------
// HTTP 구현
// ---------------------------------------------------------------------------
const http = axios.create({ baseURL: BASE_URL, timeout: 15000 })

http.interceptors.request.use((config) => {
  const token = session.state.accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err.response?.status
    const body = err.response?.data || {}
    return Promise.reject(
      Object.assign(new Error(body.message || err.message), {
        status,
        code: body.code || null,
        fieldErrors: body.fieldErrors || null,
      }),
    )
  },
)

const httpApi = {
  // 1~3 인증
  signup: (body) => http.post('/auth/signup', body),
  login: (body) => http.post('/auth/login', body),
  me: () => http.get('/auth/me'),

  // 4 대시보드
  getDashboardSummary: (role) => http.get('/dashboard/summary', { params: { role } }),

  // 5~8 작업요청
  createWorkRequest: (body, draft = false) => http.post('/work-requests', body, { params: { draft } }),
  listWorkRequests: (params = {}) => http.get('/work-requests', { params }),
  getWorkRequest: (id) => http.get(`/work-requests/${id}`),
  updateWorkRequest: (id, body) => http.patch(`/work-requests/${id}`, body),

  // 9~10 사진 — 파트명은 files (배열)
  uploadPhotos: (id, files) => {
    const fd = new FormData()
    for (const f of files) fd.append('files', f)
    return http.post(`/work-requests/${id}/photos`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  listPhotos: (id) => http.get(`/work-requests/${id}/photos`),

  // 11~13 에이전트 — POST /agent-runs 는 최상위 경로, body 에 workRequestId
  startAgentRun: (workRequestId) => http.post('/agent-runs', { workRequestId }),
  getAgentRun: (runId) => http.get(`/agent-runs/${runId}`),
  updateAgentResult: (resultId, payload) => http.patch(`/agent-results/${resultId}`, payload),

  // 14 제출
  submitApproval: (id) => http.patch(`/work-requests/${id}/submit-approval`),

  // 15 승인 — 최상위 경로, body 에 workRequestId
  createApproval: (body) => http.post('/approvals', body),
}

// ---------------------------------------------------------------------------
// Mock 구현 (동일 계약)
// ---------------------------------------------------------------------------
const clone = (v) => JSON.parse(JSON.stringify(v))
const delay = (ms = 180) => new Promise((r) => setTimeout(r, ms))
const nowIso = () => {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}+09:00`
}

function apiError(status, code, message, fieldErrors) {
  return Object.assign(new Error(message), { status, code, fieldErrors: fieldErrors || null })
}

const db = {
  users: clone(mock.users),
  workRequests: clone(mock.workRequests),
  safety: clone(mock.safetyStats),
  requestNoSeq: mock.requestNoSeq,
}

// Mock 은 토큰에서 사용자를 복원한다. 형식: mock-token-<userId>
let currentUser = null
const tokenFor = (u) => `mock-token-${u.id}`
const userFromToken = (t) => db.users.find((u) => tokenFor(u) === t) || null
const publicUser = (u) => {
  const { password, ...rest } = u
  return clone(rest)
}

function actor() {
  if (currentUser) return currentUser
  const restored = userFromToken(session.state.accessToken)
  if (!restored) throw apiError(401, ERROR_CODE.TOKEN_INVALID, '인증이 필요합니다')
  currentUser = restored
  return restored
}

const findWr = (id) => db.workRequests.find((w) => w.id === id)
const userName = (id) => db.users.find((u) => u.id === id)?.name || '알 수 없음'
const latestRun = (wr) => wr.runs?.[wr.runs.length - 1] || null
const latestApproval = (wr) => wr.approvals?.[wr.approvals.length - 1] || null

function ownedOrThrow(wr, me) {
  // ENGINEER 는 본인 요청만, SAFETY_MANAGER 는 PENDING 이상 전체 (계약 §1 권한)
  if (me.role === ROLE.ENGINEER && wr.requesterId !== me.id) {
    throw apiError(403, ERROR_CODE.FORBIDDEN_NOT_OWNER, '본인 요청만 조회할 수 있습니다')
  }
  if (me.role === ROLE.SAFETY_MANAGER && wr.status === STATUS.DRAFT) {
    throw apiError(403, ERROR_CODE.FORBIDDEN_NOT_OWNER, '작성 중인 요청은 조회할 수 없습니다')
  }
}

// 서버가 계산해 목록에 실어 보내는 값 (계약 §4-6)
function nextActionOf(status) {
  if (status === STATUS.DRAFT) return NEXT_ACTION.CONTINUE
  if (status === STATUS.AI_RUNNING) return NEXT_ACTION.RUN
  if (status === STATUS.AI_DONE) return NEXT_ACTION.RESULT
  return NEXT_ACTION.DETAIL
}

function toListItem(wr) {
  return {
    id: wr.id,
    requestNo: wr.requestNo,
    equipment: wr.equipment,
    line: wr.line,
    productName: wr.productName,
    productType: wr.productType,
    status: wr.status,
    requesterId: wr.requesterId,
    requesterName: userName(wr.requesterId),
    nextAction: nextActionOf(wr.status),
    createdAt: wr.createdAt,
    updatedAt: wr.updatedAt,
    submittedAt: wr.submittedAt,
  }
}

const allStepsDone = (run) => Boolean(run) && run.steps.every((s) => s.status === STEP_STATUS.DONE)

// SAFETY_MANAGER 조회 시 editable 은 항상 false (계약 §4-7)
function serializeRun(run, wr, me, withResults = true) {
  if (!run) return null
  const editable =
    me.role === ROLE.ENGINEER &&
    wr.requesterId === me.id &&
    !IMMUTABLE_STATUSES.includes(wr.status)
  const payload = {
    id: run.id,
    workRequestId: run.workRequestId,
    status: run.status,
    allDone: allStepsDone(run),
    pollIntervalMs: DEFAULT_POLL_INTERVAL_MS,
    startedAt: run.startedAt,
    finishedAt: run.finishedAt,
    steps: clone(run.steps),
  }
  // 계약 §4-12: 폴링 응답에는 steps·allDone·pollIntervalMs 만 온다. results 는 상세(API 7)에서만.
  // Mock 이 계약보다 후하면 실연동에서만 깨지는 구멍이 생기므로 여기서 동일하게 맞춘다.
  if (withResults) payload.results = run.results.map((r) => ({ ...clone(r), editable }))
  return payload
}

function toDetail(wr, me) {
  const { runs, approvals, photos, ...plain } = wr
  return {
    ...clone(plain),
    requesterName: userName(wr.requesterId),
    photos: clone(photos || []),
    agentRun: serializeRun(latestRun(wr), wr, me),
    approval: latestApproval(wr) ? clone(latestApproval(wr)) : null,
  }
}

// 전역에서 result 를 찾는다 (PATCH /agent-results/{id} 는 최상위 경로다)
function findResult(resultId) {
  for (const wr of db.workRequests) {
    for (const run of wr.runs || []) {
      const result = run.results.find((r) => r.id === resultId)
      if (result) return { wr, run, result }
    }
  }
  return null
}

// 한 step 을 완료 처리하고 결과 행을 만든다 (Mock 진행 엔진)
function advanceRun(run, wr) {
  const idx = run.steps.findIndex((s) => s.status !== STEP_STATUS.DONE)
  if (idx < 0) return
  const step = run.steps[idx]
  const ts = nowIso()
  step.status = STEP_STATUS.DONE
  step.startedAt = step.startedAt || ts
  step.finishedAt = ts
  step.message = `${step.agentCode} 검토 완료`
  if (!run.results.some((r) => r.agentCode === step.agentCode)) {
    run.results.push({
      id: mock.uuid(),
      agentCode: step.agentCode,
      payloadJson: mock.buildPayload(step.agentCode, wr),
      edited: false,
      updatedAt: ts,
    })
  }
  const next = run.steps[idx + 1]
  if (next) { next.status = STEP_STATUS.RUNNING; next.startedAt = ts }
}

function missingRequiredFields(body) {
  const missing = []
  if (!body.equipment?.trim()) missing.push({ field: 'equipment', message: '설비는 필수입니다' })
  if (!body.line?.trim()) missing.push({ field: 'line', message: '라인은 필수입니다' })
  if (!body.substance?.trim()) missing.push({ field: 'substance', message: '물질은 필수입니다' })
  if (!body.operatingCondition?.temperature?.trim() || !body.operatingCondition?.pressure?.trim()) {
    missing.push({ field: 'operatingCondition', message: '운전 조건(온도·압력)은 필수입니다' })
  }
  if (!body.productName?.trim()) missing.push({ field: 'productName', message: '제품명은 필수입니다' })
  if (!body.productType) missing.push({ field: 'productType', message: '제품 유형은 필수입니다' })
  return missing
}

// 유형별 specJson 스키마 검증 → 불일치 시 400 SPEC_SCHEMA_MISMATCH (계약 §2)
function assertSpecSchema(productType, specJson) {
  const required = specFieldsFor(productType)
  const bad = required.filter((f) => !String(specJson?.[f.key] || '').trim())
  if (bad.length) {
    throw apiError(400, ERROR_CODE.SPEC_SCHEMA_MISMATCH, '제품 유형에 맞는 스펙 값이 아닙니다',
      bad.map((f) => ({ field: `specJson.${f.key}`, message: `${f.label}은(는) 필수입니다` })))
  }
}

const mockApi = {
  // ---------- 1 signup ----------
  async signup(body) {
    await delay()
    const email = String(body?.email || '').trim().toLowerCase()
    const fieldErrors = []
    if (!body?.name?.trim() || body.name.trim().length < 2 || body.name.trim().length > 20) {
      fieldErrors.push({ field: 'name', message: '이름은 2~20자입니다' })
    }
    if (!email) fieldErrors.push({ field: 'email', message: '이메일은 필수입니다' })
    if (!body?.password || body.password.length < 8) {
      fieldErrors.push({ field: 'password', message: '비밀번호는 8자 이상, 영문+숫자+특수문자' })
    }
    if (!body?.role) fieldErrors.push({ field: 'role', message: '역할을 선택하세요' })
    if (fieldErrors.length) throw apiError(400, ERROR_CODE.VALIDATION_FAILED, '입력값을 확인하세요', fieldErrors)
    if (body.password !== body.passwordConfirm) {
      throw apiError(400, ERROR_CODE.PASSWORD_MISMATCH, '비밀번호가 일치하지 않습니다',
        [{ field: 'passwordConfirm', message: '비밀번호가 일치하지 않습니다' }])
    }
    if (db.users.some((u) => u.email === email)) {
      throw apiError(409, ERROR_CODE.EMAIL_ALREADY_EXISTS, '이미 사용 중인 이메일입니다')
    }
    const u = { id: mock.uuid(), name: body.name.trim(), email, role: body.role, password: body.password, createdAt: nowIso() }
    db.users.push(u)
    return publicUser(u)
  },

  // ---------- 2 login ----------
  async login(body) {
    await delay()
    const email = String(body?.email || '').trim().toLowerCase()
    const u = db.users.find((x) => x.email === email)
    if (!u || u.password !== body?.password) {
      throw apiError(401, ERROR_CODE.INVALID_CREDENTIALS, '이메일 또는 비밀번호가 올바르지 않습니다')
    }
    currentUser = u
    // redirectPath 는 서버가 정한다. 프론트는 이 값을 그대로 쓴다.
    return { accessToken: tokenFor(u), role: u.role, redirectPath: FALLBACK_REDIRECT[u.role] }
  },

  // ---------- 3 me ----------
  async me() {
    await delay(80)
    const u = userFromToken(session.state.accessToken)
    if (!u) throw apiError(401, ERROR_CODE.TOKEN_INVALID, '인증 정보가 유효하지 않습니다')
    currentUser = u
    return publicUser(u)
  },

  // ---------- 4 dashboard ----------
  async getDashboardSummary(role) {
    await delay()
    const me = actor()
    const wanted = role === 'safety' ? ROLE.SAFETY_MANAGER : ROLE.ENGINEER
    if (me.role !== wanted) throw apiError(403, ERROR_CODE.FORBIDDEN_ROLE, '역할이 일치하지 않습니다')

    if (role === 'engineer') {
      const mine = db.workRequests.filter((w) => w.requesterId === me.id)
      const count = (s) => mine.filter((w) => w.status === s).length
      return {
        draft: count(STATUS.DRAFT),
        aiRunning: count(STATUS.AI_RUNNING),
        pending: count(STATUS.PENDING),
        rejected: count(STATUS.REJECTED),
      }
    }
    return {
      pending: db.workRequests.filter((w) => w.status === STATUS.PENDING).length,
      todayProcessed: db.safety.todayProcessed,
      monthApproved: db.safety.monthApproved,
      monthRejected: db.safety.monthRejected,
      rejectReasonsTop: clone(db.safety.rejectReasonsTop).sort((a, b) => b.count - a.count).slice(0, 5),
    }
  },

  // ---------- 5 create ----------
  async createWorkRequest(body, draft = false) {
    await delay()
    const me = actor()
    if (me.role !== ROLE.ENGINEER) throw apiError(403, ERROR_CODE.FORBIDDEN_ROLE, '엔지니어만 요청을 등록할 수 있습니다')

    if (!draft) {
      const missing = missingRequiredFields(body)
      if (missing.length) throw apiError(400, ERROR_CODE.VALIDATION_FAILED, '필수 입력이 누락되었습니다', missing)
      assertSpecSchema(body.productType, body.specJson)
    }
    const ts = nowIso()
    const wr = {
      id: mock.uuid(),
      requestNo: `WR-${ts.slice(0, 10).replace(/-/g, '')}-${String(db.requestNoSeq++).padStart(3, '0')}`,
      requesterId: me.id,
      equipment: body.equipment || '', line: body.line || '', substance: body.substance || '',
      operatingCondition: { temperature: body.operatingCondition?.temperature || '', pressure: body.operatingCondition?.pressure || '' },
      productName: body.productName || '', productType: body.productType, specJson: clone(body.specJson || {}),
      symptom: body.symptom || '', siteMemo: body.siteMemo || '', engineerNote: '',
      status: STATUS.DRAFT,
      createdAt: ts, updatedAt: ts, submittedAt: null,
      photos: [], runs: [], approvals: [],
    }
    db.workRequests.unshift(wr)
    return toDetail(wr, me)
  },

  // ---------- 6 list ----------
  async listWorkRequests(params = {}) {
    await delay()
    const me = actor()
    let items = db.workRequests

    if (me.role === ROLE.ENGINEER) items = items.filter((w) => w.requesterId === me.id)
    else items = items.filter((w) => w.status !== STATUS.DRAFT) // SAFETY_MANAGER 는 PENDING 이상만

    if (params.mine === true || params.mine === 'true') items = items.filter((w) => w.requesterId === me.id)
    if (params.status) {
      const wanted = String(params.status).split(',').map((s) => s.trim()).filter(Boolean)
      items = items.filter((w) => wanted.includes(w.status))
    }
    items = [...items].sort((a, b) => (b.submittedAt || b.createdAt).localeCompare(a.submittedAt || a.createdAt))

    const number = Number(params.page ?? 0) // 0-base
    const size = Number(params.size ?? 20)
    const totalElements = items.length
    return {
      content: items.slice(number * size, (number + 1) * size).map(toListItem),
      page: { number, size, totalElements, totalPages: Math.max(1, Math.ceil(totalElements / size)) },
    }
  },

  // ---------- 7 detail ----------
  async getWorkRequest(id) {
    await delay()
    const me = actor()
    const wr = findWr(id)
    if (!wr) throw apiError(404, ERROR_CODE.WORK_REQUEST_NOT_FOUND, '요청을 찾을 수 없습니다')
    ownedOrThrow(wr, me)
    return toDetail(wr, me)
  },

  // ---------- 8 patch ----------
  async updateWorkRequest(id, body) {
    await delay()
    const me = actor()
    const wr = findWr(id)
    if (!wr) throw apiError(404, ERROR_CODE.WORK_REQUEST_NOT_FOUND, '요청을 찾을 수 없습니다')
    if (me.role !== ROLE.ENGINEER || wr.requesterId !== me.id) {
      throw apiError(403, ERROR_CODE.FORBIDDEN_NOT_OWNER, '본인 요청만 수정할 수 있습니다')
    }
    if (IMMUTABLE_STATUSES.includes(wr.status)) {
      throw apiError(409, ERROR_CODE.IMMUTABLE_STATUS, `${wr.status} 상태의 요청은 수정할 수 없습니다`)
    }
    const editable = ['equipment', 'line', 'substance', 'operatingCondition', 'productName',
      'productType', 'specJson', 'symptom', 'siteMemo', 'engineerNote']
    if ('specJson' in body || 'productType' in body) {
      const type = body.productType ?? wr.productType
      const spec = body.specJson ?? wr.specJson
      // DRAFT 는 부분 입력을 허용하므로 스키마 검증을 걸지 않는다
      if (wr.status !== STATUS.DRAFT) assertSpecSchema(type, spec)
    }
    for (const k of editable) if (k in body) wr[k] = typeof body[k] === 'object' && body[k] !== null ? clone(body[k]) : body[k]
    wr.updatedAt = nowIso()
    return toDetail(wr, me)
  },

  // ---------- 9 photos upload ----------
  async uploadPhotos(id, files) {
    await delay(150)
    const me = actor()
    const wr = findWr(id)
    if (!wr) throw apiError(404, ERROR_CODE.WORK_REQUEST_NOT_FOUND, '요청을 찾을 수 없습니다')
    if (wr.requesterId !== me.id) throw apiError(403, ERROR_CODE.FORBIDDEN_NOT_OWNER, '본인 요청만 수정할 수 있습니다')

    const list = Array.from(files || [])
    for (const f of list) {
      if (!PHOTO.ACCEPT.includes(f.type)) {
        throw apiError(400, ERROR_CODE.UNSUPPORTED_FILE_TYPE, 'jpg · png · webp 만 업로드할 수 있습니다')
      }
      if (f.size > PHOTO.MAX_SIZE) {
        throw apiError(413, ERROR_CODE.FILE_TOO_LARGE, '파일당 10MB 를 초과했습니다')
      }
    }
    if ((wr.photos.length + list.length) > PHOTO.MAX_COUNT) {
      throw apiError(409, ERROR_CODE.PHOTO_LIMIT_EXCEEDED, `사진은 요청당 최대 ${PHOTO.MAX_COUNT}장입니다`)
    }
    const created = list.map((f) => ({
      id: mock.uuid(),
      fileName: f.name,
      size: f.size,
      // 실제 서버는 EXIF 제거 + 320px 썸네일을 만들어 URL 두 개를 내려준다.
      thumbnailUrl: f.__dataUrl || null,
      originalUrl: f.__dataUrl || null,
      uploadedAt: nowIso(),
    }))
    wr.photos.push(...created)
    wr.updatedAt = nowIso()
    return clone(created)
  },

  // ---------- 10 photos list ----------
  async listPhotos(id) {
    await delay(80)
    const me = actor()
    const wr = findWr(id)
    if (!wr) throw apiError(404, ERROR_CODE.WORK_REQUEST_NOT_FOUND, '요청을 찾을 수 없습니다')
    ownedOrThrow(wr, me)
    return clone(wr.photos || [])
  },

  // ---------- 11 agent-runs ----------
  async startAgentRun(workRequestId) {
    await delay()
    const me = actor()
    const wr = findWr(workRequestId)
    if (!wr) throw apiError(404, ERROR_CODE.WORK_REQUEST_NOT_FOUND, '요청을 찾을 수 없습니다')
    if (wr.requesterId !== me.id) throw apiError(403, ERROR_CODE.FORBIDDEN_NOT_OWNER, '본인 요청만 실행할 수 있습니다')
    if (latestRun(wr)?.status === RUN_STATUS.RUNNING) {
      throw apiError(409, ERROR_CODE.RUN_ALREADY_IN_PROGRESS, '이미 AI 검증이 진행 중입니다')
    }
    const missing = missingRequiredFields(wr)
    if (missing.length) throw apiError(400, ERROR_CODE.WORK_REQUEST_INCOMPLETE, '필수 입력이 완료되지 않았습니다', missing)
    assertSpecSchema(wr.productType, wr.specJson)

    // append-only: 재실행은 갱신이 아니라 run 을 추가한다 (ERD 설계 원칙 3)
    const run = mock.makeRun(wr, 0, RUN_STATUS.RUNNING)
    run.steps[0].status = STEP_STATUS.RUNNING
    run.steps[0].startedAt = nowIso()
    run.startedAt = nowIso()
    run.finishedAt = null
    wr.runs.push(run)
    wr.status = STATUS.AI_RUNNING
    wr.updatedAt = nowIso()
    return serializeRun(run, wr, me, false)
  },

  // ---------- 12 polling ----------
  // 호출마다 step 하나가 DONE 으로 전이한다 (Mock 진행 엔진).
  async getAgentRun(runId) {
    await delay()
    const me = actor()
    let hit = null
    for (const wr of db.workRequests) {
      const run = (wr.runs || []).find((r) => r.id === runId)
      if (run) { hit = { wr, run }; break }
    }
    if (!hit) throw apiError(404, ERROR_CODE.AGENT_RUN_NOT_FOUND, 'AI 실행 이력을 찾을 수 없습니다')
    const { wr, run } = hit
    ownedOrThrow(wr, me)

    if (run.status === RUN_STATUS.RUNNING) {
      advanceRun(run, wr)
      if (allStepsDone(run)) {
        run.status = RUN_STATUS.DONE
        run.finishedAt = nowIso()
        if (wr.status === STATUS.AI_RUNNING) { wr.status = STATUS.AI_DONE; wr.updatedAt = nowIso() }
      }
    }
    return serializeRun(run, wr, me, false)
  },

  // ---------- 13 agent-results patch (전체 치환) ----------
  async updateAgentResult(resultId, payload) {
    await delay(150)
    const me = actor()
    const hit = findResult(resultId)
    if (!hit) throw apiError(404, ERROR_CODE.AGENT_RUN_NOT_FOUND, '결과를 찾을 수 없습니다')
    const { wr, run, result } = hit
    if (me.role !== ROLE.ENGINEER || wr.requesterId !== me.id) {
      throw apiError(403, ERROR_CODE.FORBIDDEN_NOT_OWNER, '본인 요청만 수정할 수 있습니다')
    }
    if (IMMUTABLE_STATUSES.includes(wr.status)) {
      throw apiError(409, ERROR_CODE.RESULT_LOCKED, '현재 상태에서는 결과를 수정할 수 없습니다')
    }

    // 배열 전체 치환: 빠진 id 는 삭제, id 없는 항목은 신규 채번
    const ts = nowIso()
    if (result.agentCode === AGENT_CODE.A3) {
      const before = new Map((result.payloadJson.documents || []).map((d) => [d.docId, d]))
      result.payloadJson = {
        documents: (payload.documents || []).map((d) => {
          const prev = d.docId ? before.get(d.docId) : null
          const changed = !prev || prev.type !== d.type || prev.name !== d.name || prev.content !== d.content
          return {
            docId: d.docId || `d-${mock.uuid().slice(0, 8)}`,
            type: d.type, name: d.name, content: d.content,
            edited: prev ? prev.edited || changed : true,
          }
        }),
      }
    } else {
      const before = new Map((result.payloadJson.items || []).map((i) => [i.itemId, i]))
      result.payloadJson = {
        items: (payload.items || []).map((i) => {
          const prev = i.itemId ? before.get(i.itemId) : null
          const changed = !prev || prev.text !== i.text
          return {
            itemId: i.itemId || `i-${mock.uuid().slice(0, 8)}`,
            text: i.text,
            edited: prev ? prev.edited || changed : true,
          }
        }),
      }
    }
    result.edited = true
    result.updatedAt = ts
    wr.updatedAt = ts
    return serializeRun(run, wr, me).results.find((r) => r.id === resultId)
  },

  // ---------- 14 submit-approval ----------
  async submitApproval(id) {
    await delay()
    const me = actor()
    const wr = findWr(id)
    if (!wr) throw apiError(404, ERROR_CODE.WORK_REQUEST_NOT_FOUND, '요청을 찾을 수 없습니다')
    if (me.role !== ROLE.ENGINEER || wr.requesterId !== me.id) {
      throw apiError(403, ERROR_CODE.FORBIDDEN_NOT_OWNER, '본인 요청만 제출할 수 있습니다')
    }

    // 서버 검증 4가지 (계약 §4-14)
    const run = latestRun(wr)
    const fieldErrors = []
    const haveAll = AGENT_CODES.every((c) => run?.results.some((r) => r.agentCode === c))
    if (!haveAll) fieldErrors.push({ field: 'agentResults', message: 'A1·A2·A3 결과가 모두 있어야 합니다' })
    if (!String(wr.engineerNote || '').trim()) {
      fieldErrors.push({ field: 'engineerNote', message: '엔지니어 설명을 입력하세요' })
    }
    const a2 = run?.results.find((r) => r.agentCode === AGENT_CODE.A2)
    if (!(a2?.payloadJson?.items || []).length) {
      fieldErrors.push({ field: 'A2', message: 'A2 적용 법령이 1건 이상 있어야 합니다' })
    }
    if (!SUBMITTABLE_STATUSES.includes(wr.status)) {
      fieldErrors.push({ field: 'status', message: '결과 확인 대기 또는 거절 상태에서만 제출할 수 있습니다' })
    }
    if (fieldErrors.length) {
      throw apiError(422, ERROR_CODE.SUBMIT_REQUIRED_FIELD_MISSING, '제출 필수 항목이 누락되었습니다', fieldErrors)
    }

    wr.status = STATUS.PENDING
    wr.submittedAt = nowIso()
    wr.updatedAt = wr.submittedAt
    return toDetail(wr, me)
  },

  // ---------- 15 approvals ----------
  async createApproval(body) {
    await delay()
    const me = actor()
    if (me.role !== ROLE.SAFETY_MANAGER) throw apiError(403, ERROR_CODE.FORBIDDEN_ROLE, '안전관리자만 승인·거절할 수 있습니다')
    const wr = findWr(body?.workRequestId)
    if (!wr) throw apiError(404, ERROR_CODE.WORK_REQUEST_NOT_FOUND, '요청을 찾을 수 없습니다')
    if (wr.status !== STATUS.PENDING) throw apiError(409, ERROR_CODE.NOT_PENDING, '승인 대기 상태의 요청만 처리할 수 있습니다')
    if (body.decision === DECISION.REJECT && String(body.reason || '').trim().length < REJECT_REASON_MIN) {
      throw apiError(400, ERROR_CODE.REJECT_REASON_REQUIRED, `거절 사유는 ${REJECT_REASON_MIN}자 이상이어야 합니다`,
        [{ field: 'reason', message: `${REJECT_REASON_MIN}자 이상 입력하세요` }])
    }

    // append-only: 재제출 후 재결정도 행을 추가한다
    const approval = {
      id: mock.uuid(),
      approverId: me.id,
      approverName: me.name,
      decision: body.decision,
      reason: body.reason || '',
      reasonCategory: body.reasonCategory || null,
      decidedAt: nowIso(),
    }
    wr.approvals.push(approval)
    wr.status = body.decision === DECISION.APPROVE ? STATUS.APPROVED : STATUS.REJECTED
    wr.updatedAt = approval.decidedAt

    db.safety.todayProcessed += 1
    if (body.decision === DECISION.APPROVE) db.safety.monthApproved += 1
    else {
      db.safety.monthRejected += 1
      const key = body.reasonCategory || String(approval.reason).split(/[:.\n]/)[0].trim().slice(0, 20)
      const found = db.safety.rejectReasonsTop.find((r) => r.reason === key)
      if (found) found.count += 1
      else if (key) db.safety.rejectReasonsTop.push({ reason: key, count: 1 })
    }
    return clone(approval)
  },
}

const api = USE_MOCK ? mockApi : httpApi
export default api

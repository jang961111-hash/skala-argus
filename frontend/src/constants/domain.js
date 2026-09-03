/**
 * CONTRACT.md v3.0 §2 도메인 Enum · 화면 라벨 · 오류 코드 — 단일 출처.
 *
 * 계약이 다시 바뀌면 이 파일 하나만 고친다. 화면·Mock·클라이언트 어디에도
 * 상태값·에이전트 코드·필드명 문자열을 직접 박지 않는다.
 */

// ---------------------------------------------------------------------------
// Role
// ---------------------------------------------------------------------------
export const ROLE = { ENGINEER: 'ENGINEER', SAFETY_MANAGER: 'SAFETY_MANAGER' }

export const ROLE_LABEL = {
  [ROLE.ENGINEER]: '엔지니어',
  [ROLE.SAFETY_MANAGER]: '안전관리자',
}

// 회원가입에서 고를 수 있는 역할 (계약 §2 Role 은 2종뿐)
export const SIGNUP_ROLES = [
  { value: ROLE.ENGINEER, label: ROLE_LABEL[ROLE.ENGINEER] },
  { value: ROLE.SAFETY_MANAGER, label: ROLE_LABEL[ROLE.SAFETY_MANAGER] },
]

// 로그인 응답의 redirectPath 가 없을 때만 쓰는 폴백. 정상 경로는 서버 값을 그대로 쓴다.
export const FALLBACK_REDIRECT = {
  [ROLE.ENGINEER]: '/home',
  [ROLE.SAFETY_MANAGER]: '/manage/requests',
}

// ---------------------------------------------------------------------------
// WorkRequestStatus (6종 — DONE 없음)
// ---------------------------------------------------------------------------
export const STATUS = {
  DRAFT: 'DRAFT',
  AI_RUNNING: 'AI_RUNNING',
  AI_DONE: 'AI_DONE',
  PENDING: 'PENDING',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
}

export const STATUS_META = {
  [STATUS.DRAFT]: { label: '작성 중', tone: 'neutral' },
  [STATUS.AI_RUNNING]: { label: 'AI 검증중', tone: 'info' },
  [STATUS.AI_DONE]: { label: '결과 확인 대기', tone: 'primary' },
  [STATUS.PENDING]: { label: '승인 대기', tone: 'warning' },
  [STATUS.APPROVED]: { label: '승인', tone: 'success' },
  [STATUS.REJECTED]: { label: '거절·보완', tone: 'danger' },
}

// PENDING·APPROVED 에서는 요청·결과 모두 수정 불가 (계약 §3)
export const IMMUTABLE_STATUSES = [STATUS.PENDING, STATUS.APPROVED]
// 제출 가능한 출발 상태
export const SUBMITTABLE_STATUSES = [STATUS.AI_DONE, STATUS.REJECTED]

// ---------------------------------------------------------------------------
// AgentCode / AgentStepStatus / RunStatus
// ---------------------------------------------------------------------------
export const AGENT_CODE = { A1: 'A1', A2: 'A2', A3: 'A3' }

// A1·A2 는 항목형(items), A3 는 문서형(documents)
export const AGENTS = [
  { code: AGENT_CODE.A1, title: '규격·호환', desc: '입력 스펙 기반 규격 적합·호환품 판정', shape: 'items' },
  { code: AGENT_CODE.A2, title: '법령·조문', desc: '적용 법령 조문·필수 절차', shape: 'items' },
  { code: AGENT_CODE.A3, title: '안전서류', desc: '작업허가서·위험성평가 초안', shape: 'documents' },
]

export const AGENT_CODES = AGENTS.map((a) => a.code)
export const agentMeta = (code) => AGENTS.find((a) => a.code === code) || { code, title: code, desc: '', shape: 'items' }

export const STEP_STATUS = { WAITING: 'WAITING', RUNNING: 'RUNNING', DONE: 'DONE', FAILED: 'FAILED' }

export const STEP_META = {
  [STEP_STATUS.WAITING]: { label: '대기', tone: 'neutral' },
  [STEP_STATUS.RUNNING]: { label: '실행 중', tone: 'info' },
  [STEP_STATUS.DONE]: { label: '완료', tone: 'success' },
  [STEP_STATUS.FAILED]: { label: '실패', tone: 'danger' },
}

export const RUN_STATUS = { RUNNING: 'RUNNING', DONE: 'DONE', FAILED: 'FAILED' }

// 서버가 pollIntervalMs 를 내려주지만, 응답 전/누락 시 쓸 폴백 (계약 §4-12 기준값)
export const DEFAULT_POLL_INTERVAL_MS = 2500

// A3 문서 유형
export const DOC_TYPES = [
  { value: 'WORK_PERMIT', label: '작업허가서' },
  { value: 'RISK_ASSESSMENT', label: '위험성평가' },
  { value: 'LOTO_CHECKLIST', label: 'LOTO 체크리스트' },
]
export const docTypeLabel = (v) => DOC_TYPES.find((d) => d.value === v)?.label || v

// ---------------------------------------------------------------------------
// ProductType → specJson 필수 키 (계약 §2)
// ---------------------------------------------------------------------------
export const PRODUCT_TYPE = {
  VALVE: 'VALVE',
  FITTING_TUBE: 'FITTING_TUBE',
  REGULATOR: 'REGULATOR',
  FILTER: 'FILTER',
  ETC: 'ETC',
}

export const PRODUCT_TYPES = [
  { value: PRODUCT_TYPE.VALVE, label: '밸브' },
  { value: PRODUCT_TYPE.FITTING_TUBE, label: '피팅·튜브' },
  { value: PRODUCT_TYPE.REGULATOR, label: '레귤레이터' },
  { value: PRODUCT_TYPE.FILTER, label: '필터' },
  { value: PRODUCT_TYPE.ETC, label: '기타' },
]

export const productTypeLabel = (v) => PRODUCT_TYPES.find((p) => p.value === v)?.label || v || '-'

export const SPEC_FIELDS = {
  [PRODUCT_TYPE.VALVE]: [{ key: 'pressureRating', label: '압력 등급', placeholder: '예: 3000 psi' }],
  [PRODUCT_TYPE.FITTING_TUBE]: [
    { key: 'connectionStandard', label: '연결 규격', placeholder: '예: 1/4 in VCR' },
    { key: 'material', label: '재질', placeholder: '예: SUS316L' },
  ],
  [PRODUCT_TYPE.REGULATOR]: [{ key: 'pressureRating', label: '압력 등급', placeholder: '예: 250 psi' }],
  [PRODUCT_TYPE.FILTER]: [{ key: 'substanceType', label: '물질 종류', placeholder: '예: N2' }],
  [PRODUCT_TYPE.ETC]: [{ key: 'freeSpec', label: '자유 스펙', placeholder: '예: 씰킷 세트, 내열 200℃' }],
}

export const specFieldsFor = (productType) => SPEC_FIELDS[productType] || []

export function specSummary(wr) {
  if (!wr) return '-'
  const parts = specFieldsFor(wr.productType)
    .map((f) => (wr.specJson?.[f.key] ? `${f.label} ${wr.specJson[f.key]}` : null))
    .filter(Boolean)
  return parts.length ? parts.join(' · ') : '-'
}

export function operatingConditionText(oc) {
  if (!oc) return '-'
  const parts = [oc.temperature, oc.pressure].filter(Boolean)
  return parts.length ? parts.join(' / ') : '-'
}

// 설비·라인은 마스터 API 가 계약에 없다(Phase 2). 선택 편의를 위한 화면 상수.
export const EQUIPMENT_SUGGESTIONS = ['가스캐비닛#2', '공정가스 밸브#7', '스크러버#1', '압축기 C-201', '펌프 P-114']
export const LINES = ['A라인', 'B라인', 'C라인', 'D라인']

// ---------------------------------------------------------------------------
// nextAction — 서버가 계산해 목록 항목마다 내려준다 (계약 §4-6).
// 프론트는 값 → 라벨/경로만 매핑하고 상태로 직접 분기하지 않는다.
// ---------------------------------------------------------------------------
export const NEXT_ACTION = { CONTINUE: 'CONTINUE', RUN: 'RUN', RESULT: 'RESULT', DETAIL: 'DETAIL' }

export const NEXT_ACTION_META = {
  [NEXT_ACTION.CONTINUE]: { label: '이어서 →', path: (id) => `/requests/new?id=${id}` },
  [NEXT_ACTION.RUN]: { label: '진행 →', path: (id) => `/requests/${id}/run` },
  [NEXT_ACTION.RESULT]: { label: '결과 →', path: (id) => `/requests/${id}/result` },
  [NEXT_ACTION.DETAIL]: { label: '상세 →', path: (id) => `/requests/${id}/result` },
}

export const nextActionMeta = (v) => NEXT_ACTION_META[v] || NEXT_ACTION_META[NEXT_ACTION.DETAIL]

// ---------------------------------------------------------------------------
// 대시보드 KPI — 응답 키가 계약 본문에 명시돼 있지 않아 여기 한 곳에 모았다.
// BE 확정값과 다르면 이 배열의 key 만 고치면 화면 전체가 따라온다.
// ---------------------------------------------------------------------------
export const ENGINEER_KPIS = [
  { key: 'draft', label: '작성 중', tone: 'neutral' },
  { key: 'aiRunning', label: '진행 중(AI)', tone: 'info' },
  { key: 'pending', label: '승인 대기', tone: 'warning' },
  { key: 'rejected', label: '반려 · 보완', tone: 'danger' },
]

export const SAFETY_KPIS = [
  { key: 'pending', label: '승인 대기', tone: 'warning' },
  { key: 'todayProcessed', label: '오늘 처리', tone: 'neutral' },
  { key: 'monthApproved', label: '이번 달 승인', tone: 'success' },
  { key: 'monthRejected', label: '이번 달 거절', tone: 'danger' },
]

// ---------------------------------------------------------------------------
// 승인 / 거절
// ---------------------------------------------------------------------------
export const DECISION = { APPROVE: 'APPROVE', REJECT: 'REJECT' }

export const DECISION_META = {
  [DECISION.APPROVE]: { label: '승인', tone: 'success' },
  [DECISION.REJECT]: { label: '거절', tone: 'danger' },
}

export const REJECT_REASON_MIN = 10 // 계약 §4-15: 거절 사유 10자 이상

// reasonCategory 는 계약 §8-6 에서 "고정 enum vs 자유 입력" 미확정.
// 선택 항목으로 두되 값은 S_01 거절 사유 TOP5 와 같은 어휘를 쓴다.
export const REJECT_REASON_CATEGORIES = [
  '규격 부적합', '법령 미충족', '안전서류 미흡', '설명 불충분', '운전 조건 불일치',
]

// ---------------------------------------------------------------------------
// 사진 제약 (계약 §4-9)
// ---------------------------------------------------------------------------
export const PHOTO = {
  MAX_COUNT: 5,
  MAX_SIZE: 10 * 1024 * 1024,
  ACCEPT: ['image/jpeg', 'image/png', 'image/webp'],
  ACCEPT_ATTR: 'image/jpeg,image/png,image/webp',
}

// ---------------------------------------------------------------------------
// 오류 코드 (계약 §6) — 화면에서 분기가 필요한 것만 한글 문구를 둔다.
// ---------------------------------------------------------------------------
export const ERROR_CODE = {
  VALIDATION_FAILED: 'VALIDATION_FAILED',
  PASSWORD_MISMATCH: 'PASSWORD_MISMATCH',
  SPEC_SCHEMA_MISMATCH: 'SPEC_SCHEMA_MISMATCH',
  REJECT_REASON_REQUIRED: 'REJECT_REASON_REQUIRED',
  UNSUPPORTED_FILE_TYPE: 'UNSUPPORTED_FILE_TYPE',
  WORK_REQUEST_INCOMPLETE: 'WORK_REQUEST_INCOMPLETE',
  INVALID_CREDENTIALS: 'INVALID_CREDENTIALS',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',
  TOKEN_INVALID: 'TOKEN_INVALID',
  FORBIDDEN_ROLE: 'FORBIDDEN_ROLE',
  FORBIDDEN_NOT_OWNER: 'FORBIDDEN_NOT_OWNER',
  WORK_REQUEST_NOT_FOUND: 'WORK_REQUEST_NOT_FOUND',
  AGENT_RUN_NOT_FOUND: 'AGENT_RUN_NOT_FOUND',
  EMAIL_ALREADY_EXISTS: 'EMAIL_ALREADY_EXISTS',
  RUN_ALREADY_IN_PROGRESS: 'RUN_ALREADY_IN_PROGRESS',
  IMMUTABLE_STATUS: 'IMMUTABLE_STATUS',
  RESULT_LOCKED: 'RESULT_LOCKED',
  ALREADY_DECIDED: 'ALREADY_DECIDED',
  NOT_PENDING: 'NOT_PENDING',
  PHOTO_LIMIT_EXCEEDED: 'PHOTO_LIMIT_EXCEEDED',
  FILE_TOO_LARGE: 'FILE_TOO_LARGE',
  SUBMIT_REQUIRED_FIELD_MISSING: 'SUBMIT_REQUIRED_FIELD_MISSING',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
}

const ERROR_MESSAGE = {
  [ERROR_CODE.INVALID_CREDENTIALS]: '이메일 또는 비밀번호가 올바르지 않습니다.',
  [ERROR_CODE.EMAIL_ALREADY_EXISTS]: '이미 가입된 이메일입니다.',
  [ERROR_CODE.PASSWORD_MISMATCH]: '비밀번호가 일치하지 않습니다.',
  [ERROR_CODE.VALIDATION_FAILED]: '입력값을 확인하세요.',
  [ERROR_CODE.SPEC_SCHEMA_MISMATCH]: '제품 유형에 맞는 스펙 항목을 모두 입력하세요.',
  [ERROR_CODE.REJECT_REASON_REQUIRED]: `거절 사유는 ${REJECT_REASON_MIN}자 이상 입력해야 합니다.`,
  [ERROR_CODE.SUBMIT_REQUIRED_FIELD_MISSING]: '제출 필수 항목이 누락되었습니다. (AI 결과 3종 · 엔지니어 설명 · A2 법령 1건 이상)',
  [ERROR_CODE.IMMUTABLE_STATUS]: '승인 대기·승인 상태의 요청은 수정할 수 없습니다.',
  [ERROR_CODE.RESULT_LOCKED]: '현재 상태에서는 AI 결과를 수정할 수 없습니다.',
  [ERROR_CODE.RUN_ALREADY_IN_PROGRESS]: '이미 AI 검증이 진행 중입니다.',
  [ERROR_CODE.WORK_REQUEST_INCOMPLETE]: '필수 입력이 완료되어야 AI 검증을 시작할 수 있습니다.',
  [ERROR_CODE.FILE_TOO_LARGE]: '파일당 10MB 이하만 업로드할 수 있습니다.',
  [ERROR_CODE.UNSUPPORTED_FILE_TYPE]: 'jpg · png · webp 이미지만 업로드할 수 있습니다.',
  [ERROR_CODE.PHOTO_LIMIT_EXCEEDED]: `사진은 요청당 최대 ${PHOTO.MAX_COUNT}장까지 첨부할 수 있습니다.`,
  [ERROR_CODE.FORBIDDEN_ROLE]: '이 작업을 수행할 권한이 없습니다.',
  [ERROR_CODE.FORBIDDEN_NOT_OWNER]: '본인이 등록한 요청만 조회·수정할 수 있습니다.',
  [ERROR_CODE.ALREADY_DECIDED]: '이미 처리된 요청입니다.',
  [ERROR_CODE.NOT_PENDING]: '승인 대기 상태의 요청만 처리할 수 있습니다.',
  [ERROR_CODE.WORK_REQUEST_NOT_FOUND]: '요청을 찾을 수 없습니다.',
  [ERROR_CODE.AGENT_RUN_NOT_FOUND]: 'AI 실행 이력을 찾을 수 없습니다.',
  [ERROR_CODE.TOKEN_EXPIRED]: '로그인이 만료되었습니다. 다시 로그인하세요.',
  [ERROR_CODE.TOKEN_INVALID]: '인증 정보가 유효하지 않습니다. 다시 로그인하세요.',
  [ERROR_CODE.INTERNAL_ERROR]: '서버 오류가 발생했습니다.',
}

// 오류 객체({status, code, message, fieldErrors}) → 화면에 띄울 문장
export function errorText(e, fallback = '요청을 처리하지 못했습니다.') {
  if (!e) return fallback
  const known = ERROR_MESSAGE[e.code]
  const fieldMsg = e.fieldErrors?.map((f) => f.message).filter(Boolean).join(', ')
  if (known) return fieldMsg ? `${known} (${fieldMsg})` : known
  return e.message || fieldMsg || fallback
}

export const isAuthError = (e) =>
  e?.status === 401 || [ERROR_CODE.TOKEN_EXPIRED, ERROR_CODE.TOKEN_INVALID].includes(e?.code)

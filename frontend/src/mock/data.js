// CONTRACT.md 의 샘플 데이터. Mock 모드에서 src/api/client.js 가 이 데이터를 그대로 사용한다.
// 모든 산출물(BE·Postman·FE)이 같은 샘플을 공유한다.

export const tenant = { id: 'T-001', name: '○○반도체(하이닉스 2차 협력사)' }

export const users = [
  { id: 'U-001', name: '김민준', role: 'ENGINEER' },
  { id: 'U-002', name: '이정호', role: 'SAFETY_MANAGER' },
  { id: 'U-003', name: '박수진', role: 'BUYER' },
  { id: 'U-004', name: '관리자', role: 'ADMIN' },
]

export const equipments = [
  { id: 'EQ-GC-02', name: '가스캐비닛#2', type: 'GAS_CABINET', substance: 'SiH4' },
  { id: 'EQ-VLV-07', name: '공정가스 밸브#7', type: 'VALVE', substance: 'NH3' },
  { id: 'EQ-SCR-01', name: '스크러버#1', type: 'SCRUBBER', substance: null },
]

export const parts = [
  { id: 'P-VLV-001', part_no: 'VLV-SS316-1/4-NC', name: '가스 밸브 SS316 1/4" NC', grade: 'OEM', toxic_gas_allowed: true, stock: 2 },
  { id: 'P-VLV-002', part_no: 'VLV-SS316-1/4-NC-EQ', name: '가스 밸브 호환품', grade: 'EQUIVALENT', toxic_gas_allowed: false, stock: 5 },
  { id: 'P-REG-001', part_no: 'REG-2S', name: '압력조정기 REG-2S', grade: 'OEM', toxic_gas_allowed: true, stock: 1 },
  { id: 'P-FLT-001', part_no: 'FLT-INL-01', name: '인라인 필터', grade: 'EQUIVALENT', toxic_gas_allowed: true, stock: 8 },
]

export const laws = [
  { law: '산업안전보건기준에 관한 규칙', article: '제91조', title: '고장난 기계의 정비 등', quote: '' },
  { law: '산업안전보건기준에 관한 규칙', article: '제92조', title: '정비등의 작업 시의 운전정지 등', quote: '…운전을 정지하고 … 잠금장치 및 표지판을…' },
  { law: '산업안전보건기준에 관한 규칙', article: '제93조', title: '방호장치의 해체 금지', quote: '' },
  { law: '산업안전보건기준에 관한 규칙', article: '제319조', title: '정전전로에서의 전기작업', quote: '' },
  { law: '화학물질관리법', article: '제24조', title: '취급시설의 설치·관리 기준', quote: '' },
  { law: '고압가스 안전관리법 시행규칙', article: '별표', title: '특정고압가스 사용시설 기준', quote: '' },
]

// 완료된 AgentRun 의 steps (CONTRACT.md 샘플 그대로). Mock 진행 시 이 result 를 순서대로 채운다.
export const completedSteps = [
  {
    agent: 'SPEC', status: 'DONE', started_at: '2026-09-02T15:10:02+09:00', completed_at: '2026-09-02T15:10:20+09:00',
    result: {
      spec_match: true,
      current_part: 'VLV-SS316-1/4-NC',
      alternatives: [
        { part_no: 'VLV-SS316-1/4-NC-EQ', grade: 'EQUIVALENT', diff: '시트 재질 PCTFE→PTFE', allowed_for_toxic_gas: false },
      ],
    },
  },
  {
    agent: 'LEGAL', status: 'DONE', started_at: '2026-09-02T15:10:20+09:00', completed_at: '2026-09-02T15:10:45+09:00',
    result: {
      applicable_laws: [
        { law: '산업안전보건기준에 관한 규칙', article: '제92조', title: '정비등의 작업 시의 운전정지 등', quote: '…운전을 정지하고 … 잠금장치 및 표지판을…' },
        { law: '화학물질관리법', article: '제24조', title: '취급시설의 설치·관리 기준', quote: '' },
        { law: '고압가스 안전관리법 시행규칙', article: '별표', title: '특정고압가스 사용시설 기준', quote: '' },
      ],
      required_procedures: [
        { name: '작업허가서(가스 배관 작업)', phase: 'BEFORE', required: true },
        { name: '위험성평가', phase: 'BEFORE', required: true },
        { name: 'LOTO·가스 차단·퍼지 확인', phase: 'BEFORE', required: true },
        { name: '가스 감지기 정상 확인', phase: 'AFTER', required: true },
      ],
    },
  },
  {
    agent: 'SAFETY_DOC', status: 'DONE', started_at: '2026-09-02T15:10:45+09:00', completed_at: '2026-09-02T15:11:10+09:00',
    result: {
      documents: [
        { doc_id: 'DOC-0101', type: 'WORK_PERMIT', missing: ['작업자 2명 이름'] },
        { doc_id: 'DOC-0102', type: 'RISK_ASSESSMENT', missing: [] },
      ],
    },
  },
  {
    agent: 'VENDOR', status: 'DONE', started_at: '2026-09-02T15:11:10+09:00', completed_at: '2026-09-02T15:11:30+09:00',
    result: {
      rfq_doc_id: 'DOC-0103',
      rfq_summary: 'VLV-SS316-1/4-NC 2EA 견적·납기 요청',
      lead_time_est_days: 3,
      last_purchase: '2026-02-14',
    },
  },
]

export const runSummary =
  'OEM 동일 규격 밸브 교체. 유독가스 라인이라 호환품 불가. 작업허가·위험성평가·LOTO 필수. 서류 초안 2건 생성, 작업자 명단만 보완 필요.'

function makeRun(runId, wrId, doneCount, overall) {
  const steps = completedSteps.map((s, i) => {
    if (i < doneCount) return JSON.parse(JSON.stringify(s))
    if (i === doneCount && overall === 'RUNNING') return { agent: s.agent, status: 'RUNNING', started_at: s.started_at, completed_at: null, result: null }
    return { agent: s.agent, status: 'PENDING', started_at: null, completed_at: null, result: null }
  })
  return {
    run_id: runId,
    work_request_id: wrId,
    overall_status: overall,
    steps,
    summary: overall === 'REVIEW' ? runSummary : null,
    approval_required_by: 'SAFETY_MANAGER',
    model_name: 'mock-v1',
    prompt_version: 'replaceflow-v0.1',
    created_at: '2026-09-02T15:10:02+09:00',
    completed_at: overall === 'REVIEW' ? '2026-09-02T15:11:30+09:00' : null,
  }
}

// work_requests 5건 (REQUESTED 1, RUNNING 1, REVIEW 1, PENDING_APPROVAL 1, APPROVED 1)
export const workRequests = [
  {
    id: 'WR-20260902-011', tenant_id: 'T-001', equipment_id: 'EQ-GC-02', part_id: 'P-VLV-001',
    symptom: '가스 유량 이상, 밸브 누설 의심', site_check_note: '현장 확인 결과 밸브 시트 마모', requested_by: 'U-001',
    status: 'REQUESTED', created_at: '2026-09-02T15:00:00+09:00', updated_at: '2026-09-02T15:00:00+09:00',
    latest_run: null, approvals: [],
  },
  {
    id: 'WR-20260902-010', tenant_id: 'T-001', equipment_id: 'EQ-VLV-07', part_id: 'P-REG-001',
    symptom: '2차압 불안정, 압력조정기 히스테리시스 증가', site_check_note: '다이어프램 손상 추정', requested_by: 'U-001',
    status: 'RUNNING', created_at: '2026-09-02T13:20:00+09:00', updated_at: '2026-09-02T13:25:00+09:00',
    latest_run: makeRun('RUN-0041', 'WR-20260902-010', 2, 'RUNNING'), approvals: [],
  },
  {
    id: 'WR-20260901-009', tenant_id: 'T-001', equipment_id: 'EQ-SCR-01', part_id: 'P-FLT-001',
    symptom: '차압 상승, 인라인 필터 막힘', site_check_note: '필터 육안 확인 시 파티클 다량', requested_by: 'U-001',
    status: 'REVIEW', created_at: '2026-09-01T16:40:00+09:00', updated_at: '2026-09-01T16:52:00+09:00',
    latest_run: makeRun('RUN-0040', 'WR-20260901-009', 4, 'REVIEW'), approvals: [],
  },
  {
    id: 'WR-20260901-008', tenant_id: 'T-001', equipment_id: 'EQ-GC-02', part_id: 'P-VLV-001',
    symptom: '밸브 개폐 지연', site_check_note: '액추에이터 공압 정상, 밸브 본체 이상', requested_by: 'U-001',
    status: 'PENDING_APPROVAL', created_at: '2026-09-01T10:05:00+09:00', updated_at: '2026-09-01T10:30:00+09:00',
    latest_run: makeRun('RUN-0039', 'WR-20260901-008', 4, 'REVIEW'), approvals: [],
  },
  {
    id: 'WR-20260831-007', tenant_id: 'T-001', equipment_id: 'EQ-VLV-07', part_id: 'P-VLV-001',
    symptom: 'NH3 라인 밸브 누설 감지', site_check_note: '감지기 알람 2회, 시트 교체 필요', requested_by: 'U-001',
    status: 'APPROVED', created_at: '2026-08-31T09:00:00+09:00', updated_at: '2026-08-31T14:20:00+09:00',
    latest_run: makeRun('RUN-0038', 'WR-20260831-007', 4, 'REVIEW'),
    approvals: [
      {
        approval_id: 'AP-0006', work_request_id: 'WR-20260831-007', approver_id: 'U-002', decision: 'APPROVE',
        checklist: { WORK_PERMIT: true, RISK_ASSESSMENT: true, LOTO_GAS_ISOLATION: true, GAS_DETECTOR_CHECK: true },
        comment: '작업자 명단 확인 완료. 승인.', decided_at: '2026-08-31T14:20:00+09:00',
      },
    ],
  },
]

export const dashboardSummary = {
  in_progress: 5,
  pending_approval: 2,
  avg_approval_hours: 26.5,
  as_is_baseline_hours: 168,
  completed_this_month: 12,
  reject_reasons_top: [
    { reason: '서류 누락', count: 3 },
    { reason: '호환품 부적합', count: 1 },
  ],
}

export const sampleApproval = {
  approval_id: 'AP-0007', work_request_id: 'WR-20260902-011', approver_id: 'U-002', decision: 'APPROVE',
  checklist: { WORK_PERMIT: true, RISK_ASSESSMENT: true, LOTO_GAS_ISOLATION: true, GAS_DETECTOR_CHECK: true },
  comment: '작업자 명단 확인 완료. 승인.', decided_at: '2026-09-02T16:20:00+09:00',
}

export { makeRun }

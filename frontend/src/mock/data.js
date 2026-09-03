// CONTRACT.md v3.0 기준 시드 데이터. Mock 모드에서 src/api/client.js 가 이 데이터를 서버처럼 굴린다.
// 필드 표기는 camelCase, ID 는 UUID v4, 화면 표시 번호는 requestNo 로 분리한다.

import {
  STATUS, AGENT_CODE, AGENT_CODES, STEP_STATUS, RUN_STATUS, PRODUCT_TYPE, ROLE, DECISION,
} from '../constants/domain'

export const uuid = () =>
  globalThis.crypto?.randomUUID?.() ??
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })

// 시드 ID 는 고정값이라 새로고침해도 URL 이 유지된다.
const U = {
  engineer: '11111111-1111-4111-8111-111111111111',
  safety: '22222222-2222-4222-8222-222222222222',
}

// password 는 Mock 인증 전용이다. 실제 API 응답(User)에는 절대 포함되지 않는다.
export const users = [
  { id: U.engineer, name: '김민준', email: 'engineer@replaceflow.test', role: ROLE.ENGINEER, password: 'Passw0rd!', createdAt: '2026-08-01T09:00:00+09:00' },
  { id: U.safety, name: '이정호', email: 'safety@replaceflow.test', role: ROLE.SAFETY_MANAGER, password: 'Passw0rd!', createdAt: '2026-08-01T09:00:00+09:00' },
]

// ---------------------------------------------------------------------------
// 에이전트 결과 payload — A1·A2 는 items, A3 는 documents (계약 §4-13)
// ---------------------------------------------------------------------------
const item = (id, text) => ({ itemId: id, text, edited: false })

export function buildPayload(agentCode, wr) {
  const spec = wr?.specJson || {}
  const inputSpec = spec.pressureRating || spec.connectionStandard || spec.substanceType || spec.freeSpec || '입력 스펙 없음'

  if (agentCode === AGENT_CODE.A1) {
    return {
      items: [
        item('i-a1-1', `규격 적합: 입력 ${inputSpec} ≥ 요구 2500 psi`),
        item('i-a1-2', `현재 부품 VLV-SS316-1/4-NC (OEM) — ${wr?.productName || '제품명 미상'} 대체 대상`),
        item('i-a1-3', '대체 호환 VLV-SS316-1/4-NC-EQ — EQUIVALENT, 시트 재질 PCTFE→PTFE, 유독가스 라인 사용 불가'),
      ],
    }
  }
  if (agentCode === AGENT_CODE.A2) {
    return {
      items: [
        item('i-a2-1', '산업안전보건기준에 관한 규칙 제92조 — 정비등의 작업 시의 운전정지 등 (잠금장치·표지판 필수)'),
        item('i-a2-2', '화학물질관리법 제24조 — 취급시설의 설치·관리 기준'),
        item('i-a2-3', '고압가스 안전관리법 시행규칙 별표 — 특정고압가스 사용시설 기준'),
        item('i-a2-4', '작업 전 필수 절차: 작업허가서 · 위험성평가 · LOTO/가스 차단·퍼지'),
      ],
    }
  }
  return {
    documents: [
      {
        docId: 'd-01', type: 'WORK_PERMIT', name: '작업허가서 초안', edited: false,
        content: `가스 배관 작업 허가서 초안 — 대상 ${wr?.equipment || '설비 미상'} / ${wr?.line || '라인 미상'}. 작업자 2명 이름 보완 필요.`,
      },
      {
        docId: 'd-02', type: 'RISK_ASSESSMENT', name: '위험성평가서 초안', edited: false,
        content: `취급 물질 ${wr?.substance || '미상'} 누출 위험 평가. 가스 감지기 정상 확인 후 작업 개시.`,
      },
    ],
  }
}

const STEP_MESSAGE = {
  [AGENT_CODE.A1]: '입력 스펙 기준 규격 적합성 판정 완료',
  [AGENT_CODE.A2]: '적용 법령 조문·필수 절차 정리 완료',
  [AGENT_CODE.A3]: '작업허가서·위험성평가 초안 생성 완료',
}

// doneCount 만큼 진행된 run 을 만든다. results 는 완료된 step 에 대해서만 생성한다.
export function makeRun(wr, doneCount, runStatus) {
  const now = '2026-09-03T15:10:00+09:00'
  const steps = AGENT_CODES.map((code, i) => {
    let status = STEP_STATUS.WAITING
    if (i < doneCount) status = STEP_STATUS.DONE
    else if (i === doneCount && runStatus === RUN_STATUS.RUNNING) status = STEP_STATUS.RUNNING
    return {
      id: uuid(),
      agentCode: code,
      status,
      message: status === STEP_STATUS.DONE ? STEP_MESSAGE[code] : null,
      errorMessage: null,
      startedAt: status === STEP_STATUS.WAITING ? null : now,
      finishedAt: status === STEP_STATUS.DONE ? now : null,
    }
  })
  const results = AGENT_CODES.slice(0, doneCount).map((code) => ({
    id: uuid(),
    agentCode: code,
    payloadJson: buildPayload(code, wr),
    edited: false,
    updatedAt: now,
  }))
  return {
    id: uuid(),
    workRequestId: wr.id,
    status: runStatus,
    startedAt: now,
    finishedAt: runStatus === RUN_STATUS.DONE ? now : null,
    steps,
    results,
  }
}

// ---------------------------------------------------------------------------
// work_requests 6건 — 상태 6종 각 1건
// ---------------------------------------------------------------------------
function wrSeed(overrides) {
  return {
    id: uuid(),
    requesterId: U.engineer,
    equipment: '', line: '', substance: '',
    operatingCondition: { temperature: '', pressure: '' },
    productName: '', productType: PRODUCT_TYPE.VALVE, specJson: {},
    symptom: '', siteMemo: '', engineerNote: '',
    status: STATUS.DRAFT,
    createdAt: '2026-09-03T09:00:00+09:00',
    updatedAt: '2026-09-03T09:00:00+09:00',
    submittedAt: null,
    photos: [], runs: [], approvals: [],
    ...overrides,
  }
}

function withRun(wr, doneCount, runStatus) {
  wr.runs = [makeRun(wr, doneCount, runStatus)]
  return wr
}

export const workRequests = [
  withRun(wrSeed({
    requestNo: 'WR-20260903-006',
    equipment: '가스캐비닛#2', line: 'A라인', substance: 'SiH4',
    operatingCondition: { temperature: '상온', pressure: '3000 psi' },
    productName: 'SS-8-VCR', productType: PRODUCT_TYPE.VALVE, specJson: { pressureRating: '3000 psi' },
    symptom: '가스 유량 이상, 밸브 누설 의심', siteMemo: '현장 확인 결과 밸브 시트 마모',
    status: STATUS.AI_RUNNING,
    createdAt: '2026-09-03T15:00:00+09:00', updatedAt: '2026-09-03T15:10:00+09:00',
  }), 1, RUN_STATUS.RUNNING),

  wrSeed({
    requestNo: 'WR-20260903-005',
    equipment: '스크러버#1', line: 'C라인', substance: 'N2',
    operatingCondition: { temperature: '상온', pressure: '250 psi' },
    productName: 'REG-2S', productType: PRODUCT_TYPE.REGULATOR, specJson: { pressureRating: '250 psi' },
    symptom: '2차압 불안정',
    status: STATUS.DRAFT,
    createdAt: '2026-09-03T14:10:00+09:00', updatedAt: '2026-09-03T14:10:00+09:00',
  }),

  withRun(wrSeed({
    requestNo: 'WR-20260903-004',
    equipment: '스크러버#1', line: 'B라인', substance: 'SiH4',
    operatingCondition: { temperature: '상온', pressure: '상압' },
    productName: 'FLT-INL-01', productType: PRODUCT_TYPE.FILTER, specJson: { substanceType: 'SiH4' },
    symptom: '차압 상승, 인라인 필터 막힘', siteMemo: '필터 육안 확인 시 파티클 다량',
    status: STATUS.AI_DONE,
    createdAt: '2026-09-03T11:40:00+09:00', updatedAt: '2026-09-03T11:52:00+09:00',
  }), 3, RUN_STATUS.DONE),

  withRun(wrSeed({
    requestNo: 'WR-20260903-003',
    equipment: '공정가스 밸브#7', line: 'A라인', substance: 'NH3',
    operatingCondition: { temperature: '상온', pressure: '3000 psi' },
    productName: 'V-2', productType: PRODUCT_TYPE.VALVE, specJson: { pressureRating: '3000 psi' },
    symptom: '밸브 개폐 지연', siteMemo: '액추에이터 공압 정상, 밸브 본체 이상',
    engineerNote: '압력 등급 상향 반영, 제92조 작업허가 필요 판단. 호환품은 유독가스 라인이라 배제.',
    status: STATUS.PENDING,
    createdAt: '2026-09-03T10:05:00+09:00', updatedAt: '2026-09-03T10:30:00+09:00',
    submittedAt: '2026-09-03T10:30:00+09:00',
  }), 3, RUN_STATUS.DONE),

  withRun(wrSeed({
    requestNo: 'WR-20260902-002',
    equipment: '공정가스 밸브#7', line: 'A라인', substance: 'NH3',
    operatingCondition: { temperature: '상온', pressure: '3000 psi' },
    productName: 'SS-8-VCR', productType: PRODUCT_TYPE.VALVE, specJson: { pressureRating: '3000 psi' },
    symptom: 'NH3 라인 밸브 누설 감지', siteMemo: '감지기 알람 2회, 시트 교체 필요',
    engineerNote: 'OEM 동일 규격으로 교체. 작업허가서 초안 보완 완료.',
    status: STATUS.APPROVED,
    createdAt: '2026-09-02T09:00:00+09:00', updatedAt: '2026-09-02T14:20:00+09:00',
    submittedAt: '2026-09-02T13:00:00+09:00',
    approvals: [{
      id: uuid(), approverId: U.safety, approverName: '이정호',
      decision: DECISION.APPROVE, reason: '작업자 명단 확인 완료. 승인합니다.', reasonCategory: null,
      decidedAt: '2026-09-02T14:20:00+09:00',
    }],
  }), 3, RUN_STATUS.DONE),

  withRun(wrSeed({
    requestNo: 'WR-20260902-001',
    equipment: '가스캐비닛#2', line: 'D라인', substance: 'SiH4',
    operatingCondition: { temperature: '상온', pressure: '3000 psi' },
    productName: 'GSK-330', productType: PRODUCT_TYPE.FITTING_TUBE,
    specJson: { connectionStandard: '1/4 in VCR', material: 'SUS316L' },
    symptom: '가스켓 열화로 미세 누설', siteMemo: '토크 재체결 후에도 누설 지속',
    engineerNote: '호환품으로 교체 요청.',
    status: STATUS.REJECTED,
    createdAt: '2026-09-02T08:10:00+09:00', updatedAt: '2026-09-02T11:05:00+09:00',
    submittedAt: '2026-09-02T09:40:00+09:00',
    approvals: [{
      id: uuid(), approverId: U.safety, approverName: '이정호',
      decision: DECISION.REJECT,
      reason: '규격 부적합: 유독가스(SiH4) 라인에 EQUIVALENT 등급 호환품은 사용할 수 없습니다. OEM 등급으로 다시 제출하세요.',
      reasonCategory: '규격 부적합',
      decidedAt: '2026-09-02T11:05:00+09:00',
    }],
  }), 3, RUN_STATUS.DONE),
]

// 안전관리자 대시보드 누적 지표. pending 은 런타임에 실제 건수로 계산한다.
export const safetyStats = {
  todayProcessed: 7,
  monthApproved: 42,
  monthRejected: 6,
  rejectReasonsTop: [
    { reason: '규격 부적합', count: 9 },
    { reason: '법령 미충족', count: 7 },
    { reason: '안전서류 미흡', count: 5 },
    { reason: '설명 불충분', count: 3 },
    { reason: '운전 조건 불일치', count: 2 },
  ],
}

// 다음 requestNo 채번용 시퀀스 (서버 채번을 흉내낸다)
export const requestNoSeq = 7

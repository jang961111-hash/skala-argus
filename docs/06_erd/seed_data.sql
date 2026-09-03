-- ============================================================
-- ReplaceFlow — 샘플 데이터 (CONTRACT.md "샘플 데이터" 절과 동일)
-- 실행 순서: schema_postgres.sql 실행 후 본 파일 실행
-- 모든 시각은 KST(+09:00). 법령 text 는 [요약] — 원문은 source_uri 참조
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. tenants
-- ------------------------------------------------------------
INSERT INTO tenants (id, name, plan, created_at) VALUES
  ('T-001', '○○반도체(하이닉스 2차 협력사)', 'STANDARD', '2026-08-01T09:00:00+09:00');

-- ------------------------------------------------------------
-- 2. users (4)
-- ------------------------------------------------------------
INSERT INTO users (id, tenant_id, name, email, role, is_active, created_at) VALUES
  ('U-001', 'T-001', '김민준', 'mj.kim@oo-semi.example',    'ENGINEER',       TRUE, '2026-08-01T09:00:00+09:00'),
  ('U-002', 'T-001', '이정호', 'jh.lee@oo-semi.example',    'SAFETY_MANAGER', TRUE, '2026-08-01T09:00:00+09:00'),
  ('U-003', 'T-001', '박수진', 'sj.park@oo-semi.example',   'BUYER',          TRUE, '2026-08-01T09:00:00+09:00'),
  ('U-004', 'T-001', '관리자', 'admin@oo-semi.example',     'ADMIN',          TRUE, '2026-08-01T09:00:00+09:00');

-- ------------------------------------------------------------
-- 3. equipments (3)
-- ------------------------------------------------------------
INSERT INTO equipments (id, tenant_id, name, type, line, substances, created_at) VALUES
  ('EQ-GC-02',  'T-001', '가스캐비닛#2',      'GAS_CABINET', 'FAB1-L2', '["SiH4"]'::jsonb,        '2026-08-01T09:00:00+09:00'),
  ('EQ-VLV-07', 'T-001', '공정가스 밸브#7',   'VALVE',       'FAB1-L2', '["NH3"]'::jsonb,         '2026-08-01T09:00:00+09:00'),
  ('EQ-SCR-01', 'T-001', '스크러버#1',        'SCRUBBER',    'FAB1-SUB', '["SiH4","NH3"]'::jsonb, '2026-08-01T09:00:00+09:00');

-- ------------------------------------------------------------
-- 4. parts (4)
-- ------------------------------------------------------------
INSERT INTO parts (id, tenant_id, part_no, name, spec, grade, toxic_gas_allowed, stock, created_at) VALUES
  ('P-VLV-001', 'T-001', 'VLV-SS316-1/4-NC',    '다이어프램 밸브 SS316 1/4" NC',
     '{"material":"SS316","size":"1/4","actuation":"NC","seat":"PCTFE","max_pressure_bar":20}'::jsonb,
     'OEM', TRUE, 2, '2026-08-01T09:00:00+09:00'),
  ('P-VLV-002', 'T-001', 'VLV-SS316-1/4-NC-EQ', '다이어프램 밸브 SS316 1/4" NC (호환품)',
     '{"material":"SS316","size":"1/4","actuation":"NC","seat":"PTFE","max_pressure_bar":20}'::jsonb,
     'EQUIVALENT', FALSE, 5, '2026-08-01T09:00:00+09:00'),
  ('P-REG-001', 'T-001', 'REG-2S',              '압력조정기 REG-2S',
     '{"stages":2,"inlet_bar":150,"outlet_bar":7,"body":"SS316L"}'::jsonb,
     'OEM', TRUE, 1, '2026-08-01T09:00:00+09:00'),
  ('P-FLT-001', 'T-001', 'FLT-IL-0.003',        '인라인 필터 0.003um',
     '{"rating_um":0.003,"body":"SS316L","connection":"1/4 VCR"}'::jsonb,
     'EQUIVALENT', FALSE, 8, '2026-08-01T09:00:00+09:00');

-- ------------------------------------------------------------
-- 5. equipment_parts (N:M equipments ↔ parts)
-- ------------------------------------------------------------
INSERT INTO equipment_parts (equipment_id, part_id, installed_at, last_replaced_at, qty) VALUES
  ('EQ-GC-02',  'P-VLV-001', '2024-03-10T10:00:00+09:00', '2026-02-14T14:00:00+09:00', 2),
  ('EQ-GC-02',  'P-REG-001', '2024-03-10T10:00:00+09:00', NULL,                        1),
  ('EQ-VLV-07', 'P-VLV-001', '2024-05-20T10:00:00+09:00', '2025-11-03T09:30:00+09:00', 1),
  ('EQ-SCR-01', 'P-FLT-001', '2024-01-15T10:00:00+09:00', '2026-06-01T11:00:00+09:00', 2);

-- ------------------------------------------------------------
-- 6. part_compatibility (N:M parts ↔ parts)
-- ------------------------------------------------------------
INSERT INTO part_compatibility (part_id, alt_part_id, diff, allowed_for_toxic_gas) VALUES
  ('P-VLV-001', 'P-VLV-002', '시트 재질 PCTFE→PTFE', FALSE);

-- ------------------------------------------------------------
-- 7. law_index (6) — [요약] 표기: 원문 그대로가 아닌 요약 적재. 출처 URL 은 법제처
-- ------------------------------------------------------------
INSERT INTO law_index (id, law, article, title, text, equipment_type, substance, effective_date, source_uri) VALUES
  (1, '산업안전보건기준에 관한 규칙', '제91조', '고장난 기계의 정비 등',
   '[요약] 사업주는 기계 또는 방호장치의 결함이 발견된 경우 반드시 정비한 후에 근로자가 사용하도록 하여야 한다. 정비가 완료될 때까지는 해당 기계 및 방호장치 등의 사용을 금지하여야 하며, 그 뜻을 알리는 표지를 부착하여야 한다.',
   NULL, NULL, '2024-06-28', 'https://www.law.go.kr/법령/산업안전보건기준에관한규칙/제91조'),
  (2, '산업안전보건기준에 관한 규칙', '제92조', '정비등의 작업 시의 운전정지 등',
   '[요약] 사업주는 공작기계·수송기계·건설기계 등의 정비·청소·급유·검사·수리·교체 또는 조정 작업 시 근로자가 위험해질 우려가 있으면 해당 기계의 운전을 정지하여야 한다. 운전을 정지한 경우 다른 사람이 그 기계를 운전하는 것을 방지하기 위하여 기동장치에 잠금장치를 하고 그 열쇠를 별도로 관리하거나 표지판을 설치하는 등 필요한 방호 조치를 하여야 한다. 작업의 성질상 운전이 필요한 경우에는 근로자가 위험해질 우려가 없도록 필요한 안전조치를 하여야 한다.',
   NULL, NULL, '2024-06-28', 'https://www.law.go.kr/법령/산업안전보건기준에관한규칙/제92조'),
  (3, '산업안전보건기준에 관한 규칙', '제93조', '방호장치의 해체 금지',
   '[요약] 사업주는 기계·기구 또는 설비에 설치한 방호장치를 해체하거나 사용을 정지해서는 아니 된다. 다만 방호장치의 수리·조정 또는 교체 등의 작업을 하는 경우에는 그러하지 아니하며, 이 경우 필요한 안전조치를 하고 작업이 끝난 후 지체 없이 원상으로 회복시켜야 한다. 근로자는 방호장치가 해체·정지된 것을 발견한 경우 즉시 사업주에게 신고하여야 한다.',
   NULL, NULL, '2024-06-28', 'https://www.law.go.kr/법령/산업안전보건기준에관한규칙/제93조'),
  (4, '산업안전보건기준에 관한 규칙', '제319조', '정전전로에서의 전기작업',
   '[요약] 사업주는 근로자가 노출된 충전부 또는 그 부근에서 작업함으로써 감전될 우려가 있는 경우에는 작업에 들어가기 전에 해당 전로를 차단하여야 한다. 전로를 차단하는 경우 전기기기등에 공급되는 모든 전원을 차단하고, 개폐기에 잠금장치 및 꼬리표를 부착하며, 잔류전하를 방전시키고, 검전기로 충전 여부를 확인한 후 단락 접지기구를 설치하여야 한다. 작업 종료 후에는 근로자 안전 확인 및 잠금장치·꼬리표 제거 절차를 거쳐 전원을 공급한다.',
   NULL, NULL, '2024-06-28', 'https://www.law.go.kr/법령/산업안전보건기준에관한규칙/제319조'),
  (5, '화학물질관리법', '제24조', '취급시설의 설치·관리 기준 등',
   '[요약] 유해화학물질 취급시설을 설치·운영하려는 자는 환경부령으로 정하는 설치 및 관리 기준에 따라야 한다. 취급시설을 설치·운영하는 자는 설치 후 검사기관으로부터 검사를 받아야 하고, 이후 정기검사 및 수시검사를 받아야 하며, 검사 결과 안전상 위해가 우려되는 경우 안전진단을 받아야 한다. 검사 결과는 기준 적합 여부를 확인하여 관리대장에 기록·보존한다.',
   NULL, 'SiH4', '2025-08-07', 'https://www.law.go.kr/법령/화학물질관리법/제24조'),
  (6, '고압가스 안전관리법 시행규칙', '별표 8', '특정고압가스 사용시설의 시설·기술·검사 기준',
   '[요약] 특정고압가스(실란·암모니아 등 독성·가연성 가스) 사용시설의 저장설비·배관·밸브 등은 해당 가스에 적합한 재료를 사용하고 기밀시험에 합격한 것이어야 한다. 독성가스 사용시설에는 가스누출검지경보장치를 설치하여 정상 작동 상태를 유지하여야 하며, 실린더 캐비닛 내부는 음압 및 배기가 유지되어야 한다. 배관·밸브의 교체 등 개방 작업 전에는 가스 공급을 차단하고 불활성가스로 치환(퍼지)하여 잔류가스를 제거한 후 작업하여야 하며, 작업 후 기밀 및 누출검지기 정상 여부를 확인하여야 한다.',
   'GAS_CABINET', 'SiH4', '2025-01-01', 'https://www.law.go.kr/법령/고압가스안전관리법시행규칙/별표8');

SELECT setval(pg_get_serial_sequence('law_index', 'id'), (SELECT max(id) FROM law_index));

-- ------------------------------------------------------------
-- 8. work_requests (5) — 상태 5종
-- ------------------------------------------------------------
INSERT INTO work_requests (id, tenant_id, equipment_id, part_id, symptom, site_check_note, requested_by, status, created_at, updated_at) VALUES
  -- CONTRACT 대표 샘플: 요청(15:00) → 실행(15:10) → 승인(16:20) → 현재 APPROVED
  ('WR-20260902-011', 'T-001', 'EQ-GC-02',  'P-VLV-001', '가스 유량 이상, 밸브 누설 의심',        '현장 확인 결과 밸브 시트 마모',            'U-001', 'APPROVED',         '2026-09-02T15:00:00+09:00', '2026-09-02T16:20:00+09:00'),
  ('WR-20260902-012', 'T-001', 'EQ-VLV-07', 'P-VLV-001', 'NH3 라인 밸브 작동 지연, 개폐 시간 증가', NULL,                                       'U-001', 'REQUESTED',        '2026-09-02T16:40:00+09:00', '2026-09-02T16:40:00+09:00'),
  ('WR-20260902-013', 'T-001', 'EQ-SCR-01', 'P-FLT-001', '스크러버 인라인 필터 차압 상승 경보',    '차압 게이지 0.8bar, 필터 막힘 추정',        'U-001', 'RUNNING',          '2026-09-02T16:50:00+09:00', '2026-09-02T16:52:00+09:00'),
  ('WR-20260901-009', 'T-001', 'EQ-GC-02',  'P-REG-001', '압력조정기 2차측 출력 불안정',          '출력압 7bar 설정에 5~9bar 진동',            'U-001', 'REVIEW',           '2026-09-01T10:00:00+09:00', '2026-09-01T10:13:00+09:00'),
  ('WR-20260901-010', 'T-001', 'EQ-VLV-07', 'P-VLV-001', '밸브 다이어프램 파손 의심, 미세 누설',   '누출검지기 1ppm 간헐 감지, 밸브 본체 체결부', 'U-001', 'PENDING_APPROVAL', '2026-09-01T14:00:00+09:00', '2026-09-01T14:25:00+09:00');

-- ------------------------------------------------------------
-- 9. agent_runs
--    RUN-0042: CONTRACT AgentRun 그대로(완료, REVIEW)  ← 대표 샘플
--    RUN-0043: 실행 중(RUNNING) / RUN-0041, RUN-0040: 완료(REVIEW) 축약본
-- ------------------------------------------------------------
INSERT INTO agent_runs (id, work_request_id, overall_status, steps_json, summary, approval_required_by, model_name, prompt_version, created_at, completed_at) VALUES
  ('RUN-0042', 'WR-20260902-011', 'REVIEW',
   '[
     { "agent": "SPEC", "status": "DONE", "started_at": "2026-09-02T15:10:02+09:00", "completed_at": "2026-09-02T15:10:20+09:00",
       "result": { "spec_match": true, "current_part": "VLV-SS316-1/4-NC",
         "alternatives": [ { "part_no": "VLV-SS316-1/4-NC-EQ", "grade": "EQUIVALENT", "diff": "시트 재질 PCTFE→PTFE", "allowed_for_toxic_gas": false } ] } },
     { "agent": "LEGAL", "status": "DONE", "started_at": "2026-09-02T15:10:20+09:00", "completed_at": "2026-09-02T15:10:48+09:00",
       "result": {
         "applicable_laws": [
           { "law": "산업안전보건기준에 관한 규칙", "article": "제92조", "title": "정비등의 작업 시의 운전정지 등", "quote": "…운전을 정지하고 … 잠금장치 및 표지판을…" },
           { "law": "화학물질관리법", "article": "제24조", "title": "취급시설의 설치·관리 기준", "quote": "" },
           { "law": "고압가스 안전관리법 시행규칙", "article": "별표", "title": "특정고압가스 사용시설 기준", "quote": "" } ],
         "required_procedures": [
           { "name": "작업허가서(가스 배관 작업)", "phase": "BEFORE", "required": true },
           { "name": "위험성평가", "phase": "BEFORE", "required": true },
           { "name": "LOTO·가스 차단·퍼지 확인", "phase": "BEFORE", "required": true },
           { "name": "가스 감지기 정상 확인", "phase": "AFTER", "required": true } ] } },
     { "agent": "SAFETY_DOC", "status": "DONE", "started_at": "2026-09-02T15:10:48+09:00", "completed_at": "2026-09-02T15:11:10+09:00",
       "result": { "documents": [
         { "doc_id": "DOC-0101", "type": "WORK_PERMIT", "missing": ["작업자 2명 이름"] },
         { "doc_id": "DOC-0102", "type": "RISK_ASSESSMENT", "missing": [] } ] } },
     { "agent": "VENDOR", "status": "DONE", "started_at": "2026-09-02T15:11:10+09:00", "completed_at": "2026-09-02T15:11:30+09:00",
       "result": { "rfq_doc_id": "DOC-0103", "rfq_summary": "VLV-SS316-1/4-NC 2EA 견적·납기 요청", "lead_time_est_days": 3, "last_purchase": "2026-02-14" } }
   ]'::jsonb,
   'OEM 동일 규격 밸브 교체. 유독가스 라인이라 호환품 불가. 작업허가·위험성평가·LOTO 필수. 서류 초안 2건 생성, 작업자 명단만 보완 필요.',
   'SAFETY_MANAGER', 'mock-v1', 'replaceflow-v0.1', '2026-09-02T15:10:02+09:00', '2026-09-02T15:11:30+09:00'),

  ('RUN-0043', 'WR-20260902-013', 'RUNNING',
   '[
     { "agent": "SPEC",       "status": "DONE",    "started_at": "2026-09-02T16:52:00+09:00", "completed_at": "2026-09-02T16:52:15+09:00",
       "result": { "spec_match": true, "current_part": "FLT-IL-0.003", "alternatives": [] } },
     { "agent": "LEGAL",      "status": "RUNNING", "started_at": "2026-09-02T16:52:15+09:00", "completed_at": null, "result": null },
     { "agent": "SAFETY_DOC", "status": "PENDING", "started_at": null, "completed_at": null, "result": null },
     { "agent": "VENDOR",     "status": "PENDING", "started_at": null, "completed_at": null, "result": null }
   ]'::jsonb,
   NULL, NULL, 'mock-v1', 'replaceflow-v0.1', '2026-09-02T16:52:00+09:00', NULL),

  ('RUN-0041', 'WR-20260901-009', 'REVIEW',
   '[
     { "agent": "SPEC",       "status": "DONE", "started_at": "2026-09-01T10:10:00+09:00", "completed_at": "2026-09-01T10:10:20+09:00",
       "result": { "spec_match": true, "current_part": "REG-2S", "alternatives": [] } },
     { "agent": "LEGAL",      "status": "DONE", "started_at": "2026-09-01T10:10:20+09:00", "completed_at": "2026-09-01T10:10:50+09:00",
       "result": { "applicable_laws": [ { "law": "산업안전보건기준에 관한 규칙", "article": "제92조", "title": "정비등의 작업 시의 운전정지 등", "quote": "…운전을 정지하고 … 잠금장치 및 표지판을…" } ],
                   "required_procedures": [ { "name": "작업허가서(가스 배관 작업)", "phase": "BEFORE", "required": true }, { "name": "LOTO·가스 차단·퍼지 확인", "phase": "BEFORE", "required": true } ] } },
     { "agent": "SAFETY_DOC", "status": "DONE", "started_at": "2026-09-01T10:10:50+09:00", "completed_at": "2026-09-01T10:11:20+09:00",
       "result": { "documents": [] } },
     { "agent": "VENDOR",     "status": "DONE", "started_at": "2026-09-01T10:11:20+09:00", "completed_at": "2026-09-01T10:13:00+09:00",
       "result": { "rfq_doc_id": null, "rfq_summary": "REG-2S 1EA 재고 보유, 견적 불필요", "lead_time_est_days": 0, "last_purchase": "2025-12-02" } }
   ]'::jsonb,
   'OEM 압력조정기 교체. 재고 1EA 보유. 작업허가·LOTO 필수. 서류 초안은 검토 후 생성 예정.',
   'SAFETY_MANAGER', 'mock-v1', 'replaceflow-v0.1', '2026-09-01T10:10:00+09:00', '2026-09-01T10:13:00+09:00'),

  ('RUN-0040', 'WR-20260901-010', 'REVIEW',
   '[
     { "agent": "SPEC",       "status": "DONE", "started_at": "2026-09-01T14:05:00+09:00", "completed_at": "2026-09-01T14:05:20+09:00",
       "result": { "spec_match": true, "current_part": "VLV-SS316-1/4-NC",
         "alternatives": [ { "part_no": "VLV-SS316-1/4-NC-EQ", "grade": "EQUIVALENT", "diff": "시트 재질 PCTFE→PTFE", "allowed_for_toxic_gas": false } ] } },
     { "agent": "LEGAL",      "status": "DONE", "started_at": "2026-09-01T14:05:20+09:00", "completed_at": "2026-09-01T14:05:50+09:00",
       "result": { "applicable_laws": [ { "law": "산업안전보건기준에 관한 규칙", "article": "제92조", "title": "정비등의 작업 시의 운전정지 등", "quote": "…운전을 정지하고 … 잠금장치 및 표지판을…" },
                                        { "law": "고압가스 안전관리법 시행규칙", "article": "별표", "title": "특정고압가스 사용시설 기준", "quote": "" } ],
                   "required_procedures": [ { "name": "작업허가서(가스 배관 작업)", "phase": "BEFORE", "required": true },
                                            { "name": "위험성평가", "phase": "BEFORE", "required": true },
                                            { "name": "LOTO·가스 차단·퍼지 확인", "phase": "BEFORE", "required": true },
                                            { "name": "가스 감지기 정상 확인", "phase": "AFTER", "required": true } ] } },
     { "agent": "SAFETY_DOC", "status": "DONE", "started_at": "2026-09-01T14:05:50+09:00", "completed_at": "2026-09-01T14:06:20+09:00",
       "result": { "documents": [] } },
     { "agent": "VENDOR",     "status": "DONE", "started_at": "2026-09-01T14:06:20+09:00", "completed_at": "2026-09-01T14:07:00+09:00",
       "result": { "rfq_doc_id": null, "rfq_summary": "VLV-SS316-1/4-NC 1EA 재고 사용", "lead_time_est_days": 0, "last_purchase": "2026-02-14" } }
   ]'::jsonb,
   'NH3 라인 OEM 밸브 교체. 호환품 불가. 승인 요청 완료, 안전관리자 판단 대기.',
   'SAFETY_MANAGER', 'mock-v1', 'replaceflow-v0.1', '2026-09-01T14:05:00+09:00', '2026-09-01T14:07:00+09:00');

-- ------------------------------------------------------------
-- 10. legal_findings — RUN-0042 LEGAL step 결과에서 승격 (조문 3 × 절차 4 → 4행)
--     law/article/title/quote 는 steps_json 과 동일 문자열(스냅샷), law_index_id 는 원문 참조
-- ------------------------------------------------------------
INSERT INTO legal_findings (agent_run_id, law_index_id, law, article, title, quote, procedure_name, phase, required) VALUES
  ('RUN-0042', 2, '산업안전보건기준에 관한 규칙', '제92조', '정비등의 작업 시의 운전정지 등', '…운전을 정지하고 … 잠금장치 및 표지판을…', '작업허가서(가스 배관 작업)', 'BEFORE', TRUE),
  ('RUN-0042', 2, '산업안전보건기준에 관한 규칙', '제92조', '정비등의 작업 시의 운전정지 등', '…운전을 정지하고 … 잠금장치 및 표지판을…', 'LOTO·가스 차단·퍼지 확인',   'BEFORE', TRUE),
  ('RUN-0042', 5, '화학물질관리법',               '제24조', '취급시설의 설치·관리 기준',        '',                                      '위험성평가',                 'BEFORE', TRUE),
  ('RUN-0042', 6, '고압가스 안전관리법 시행규칙', '별표',   '특정고압가스 사용시설 기준',        '',                                      '가스 감지기 정상 확인',       'AFTER',  TRUE);

-- ------------------------------------------------------------
-- 11. documents (3) — RUN-0042 산출
-- ------------------------------------------------------------
INSERT INTO documents (id, agent_run_id, type, title, body, missing_json, version, created_at) VALUES
  ('DOC-0101', 'RUN-0042', 'WORK_PERMIT', '작업허가서 — 가스캐비닛#2 밸브 교체',
'# 작업허가서 (가스 배관 작업)

- 작업요청: WR-20260902-011
- 설비: 가스캐비닛#2 (EQ-GC-02, FAB1-L2) / 취급물질: SiH4
- 작업내용: 다이어프램 밸브 VLV-SS316-1/4-NC 2EA 교체 (OEM 동일 규격)
- 작업일시: 2026-09-03 09:00 ~ 12:00
- 작업책임자: 김민준 (U-001)
- 작업자: [작업자 1 이름], [작업자 2 이름]

## 사전 조치
1. SiH4 공급 차단 및 실린더 밸브 잠금 (LOTO) — 산안규칙 제92조
2. N2 퍼지 3회 이상, 잔류가스 0ppm 확인
3. 가스누출검지경보장치 정상 작동 확인 — 고압가스법 시행규칙 별표 8
4. 보호구: 내화학 장갑, 보안면, 송기마스크 대기

## 승인
- 안전관리자: 이정호 (U-002) — 승인 대기',
   '["작업자 2명 이름"]'::jsonb, 1, '2026-09-02T15:11:05+09:00'),

  ('DOC-0102', 'RUN-0042', 'RISK_ASSESSMENT', '위험성평가 — 가스캐비닛#2 밸브 교체',
'# 위험성평가

- 대상 작업: 가스캐비닛#2 SiH4 라인 밸브 교체 (WR-20260902-011)
- 평가일: 2026-09-02 / 평가자: 김민준, 검토: 이정호

| 유해위험요인 | 가능성 | 중대성 | 위험성 | 감소대책 |
|---|---|---|---|---|
| 잔류 SiH4 누출·자연발화 | 2 | 4 | 8 | 공급차단 + N2 퍼지 3회, 잔류가스 측정 후 개방 |
| 배관 체결부 개방 시 압력 분출 | 2 | 3 | 6 | 압력계 0 확인, 서서히 개방 |
| 호환품 오장착(PTFE 시트) | 1 | 4 | 4 | OEM 품번 VLV-SS316-1/4-NC 육안·바코드 대조 |
| 작업 후 누설 | 2 | 3 | 6 | He 누설검사, 가스감지기 정상 확인 후 공급 재개 |

결론: 감소대책 적용 시 허용 가능 수준. 안전관리자 승인 후 작업.',
   '[]'::jsonb, 1, '2026-09-02T15:11:08+09:00'),

  ('DOC-0103', 'RUN-0042', 'RFQ', '견적요청서 — VLV-SS316-1/4-NC 2EA',
'# 견적 요청 (RFQ)

수신: OEM 밸브 공급사 영업 담당
발신: ○○반도체 구매팀 박수진 (U-003)

1. 품목: VLV-SS316-1/4-NC (다이어프램 밸브, SS316, 1/4", NC, PCTFE 시트)
2. 수량: 2 EA
3. 요청 납기: 2026-09-05 이내 (긴급 교체 건)
4. 최근 구매 이력: 2026-02-14, 동일 품번 2 EA
5. 요청 사항: 단가·납기·재고 회신, Mill Sheet 및 기밀시험 성적서 첨부

회신 기한: 2026-09-03 12:00',
   '[]'::jsonb, 1, '2026-09-02T15:11:28+09:00');

-- ------------------------------------------------------------
-- 12. approvals (1) — CONTRACT Approval 샘플
-- ------------------------------------------------------------
INSERT INTO approvals (id, work_request_id, approver_id, decision, checklist_json, comment, decided_at) VALUES
  ('AP-0007', 'WR-20260902-011', 'U-002', 'APPROVE',
   '{"WORK_PERMIT": true, "RISK_ASSESSMENT": true, "LOTO_GAS_ISOLATION": true, "GAS_DETECTOR_CHECK": true}'::jsonb,
   '작업자 명단 확인 완료. 승인.', '2026-09-02T16:20:00+09:00');

-- ------------------------------------------------------------
-- 13. ai_configs (4) — 에이전트별, 온프레미스 기본값
-- ------------------------------------------------------------
INSERT INTO ai_configs (tenant_id, agent_type, provider, model_name, prompt_version, egress_allowed, updated_at) VALUES
  ('T-001', 'SPEC',       'LOCAL_LLM', 'mock-v1', 'replaceflow-v0.1', FALSE, '2026-08-01T09:00:00+09:00'),
  ('T-001', 'LEGAL',      'LOCAL_LLM', 'mock-v1', 'replaceflow-v0.1', FALSE, '2026-08-01T09:00:00+09:00'),
  ('T-001', 'SAFETY_DOC', 'LOCAL_LLM', 'mock-v1', 'replaceflow-v0.1', FALSE, '2026-08-01T09:00:00+09:00'),
  ('T-001', 'VENDOR',     'LOCAL_LLM', 'mock-v1', 'replaceflow-v0.1', FALSE, '2026-08-01T09:00:00+09:00');

-- ------------------------------------------------------------
-- 14. audit_logs (2)
-- ------------------------------------------------------------
INSERT INTO audit_logs (tenant_id, user_id, entity, entity_id, action, before_json, after_json, created_at) VALUES
  ('T-001', 'U-001', 'work_requests', 'WR-20260902-011', 'STATUS_CHANGE',
   '{"status": "REVIEW"}'::jsonb, '{"status": "PENDING_APPROVAL"}'::jsonb, '2026-09-02T15:30:00+09:00'),
  ('T-001', 'U-002', 'approvals', 'AP-0007', 'APPROVE',
   '{"work_request_status": "PENDING_APPROVAL"}'::jsonb,
   '{"work_request_status": "APPROVED", "decision": "APPROVE", "checklist_all_true": true}'::jsonb,
   '2026-09-02T16:20:00+09:00');

COMMIT;

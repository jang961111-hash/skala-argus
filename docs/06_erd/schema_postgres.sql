-- ============================================================
-- ReplaceFlow — PostgreSQL DDL (Supabase SQL Editor 에서 그대로 실행)
-- 기준: docs/CONTRACT.md, 기획서 9장 ERD, docs/06_erd/replaceflow.dbml
-- 실행 순서: schema_postgres.sql → seed_data.sql
-- ============================================================

SET client_min_messages = WARNING;

-- ------------------------------------------------------------
-- 0. 재실행을 위한 정리 (개발 환경 전용; 운영에서는 주석 처리)
-- ------------------------------------------------------------
DROP TABLE IF EXISTS audit_logs          CASCADE;
DROP TABLE IF EXISTS ai_configs          CASCADE;
DROP TABLE IF EXISTS approvals           CASCADE;
DROP TABLE IF EXISTS documents           CASCADE;
DROP TABLE IF EXISTS legal_findings      CASCADE;
DROP TABLE IF EXISTS agent_runs          CASCADE;
DROP TABLE IF EXISTS work_requests       CASCADE;
DROP TABLE IF EXISTS law_index           CASCADE;
DROP TABLE IF EXISTS part_compatibility  CASCADE;
DROP TABLE IF EXISTS equipment_parts     CASCADE;
DROP TABLE IF EXISTS parts               CASCADE;
DROP TABLE IF EXISTS equipments          CASCADE;
DROP TABLE IF EXISTS users               CASCADE;
DROP TABLE IF EXISTS tenants             CASCADE;

DROP TYPE IF EXISTS work_request_status;
DROP TYPE IF EXISTS agent_run_status;
DROP TYPE IF EXISTS step_status;
DROP TYPE IF EXISTS agent_type;
DROP TYPE IF EXISTS user_role;
DROP TYPE IF EXISTS approval_decision;
DROP TYPE IF EXISTS document_type;
DROP TYPE IF EXISTS part_grade;
DROP TYPE IF EXISTS ai_provider;

-- ------------------------------------------------------------
-- 1. ENUM 타입 (CONTRACT.md 상태값 문자열과 동일)
-- ------------------------------------------------------------
CREATE TYPE work_request_status AS ENUM ('REQUESTED', 'RUNNING', 'REVIEW', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'DONE');
CREATE TYPE agent_run_status    AS ENUM ('RUNNING', 'REVIEW', 'FAILED');
CREATE TYPE step_status         AS ENUM ('PENDING', 'RUNNING', 'DONE', 'FAILED');   -- steps_json 내부 값 (문서화용)
CREATE TYPE agent_type          AS ENUM ('SPEC', 'LEGAL', 'SAFETY_DOC', 'VENDOR');
CREATE TYPE user_role           AS ENUM ('ENGINEER', 'SAFETY_MANAGER', 'BUYER', 'ADMIN');
CREATE TYPE approval_decision   AS ENUM ('APPROVE', 'REJECT', 'REQUEST_INFO');
CREATE TYPE document_type       AS ENUM ('WORK_PERMIT', 'RISK_ASSESSMENT', 'LOTO_CHECKLIST', 'RFQ');
CREATE TYPE part_grade          AS ENUM ('OEM', 'EQUIVALENT', 'REFURB');
CREATE TYPE ai_provider         AS ENUM ('LOCAL_LLM', 'AX_PLATFORM', 'OPENAI');

-- ------------------------------------------------------------
-- 2. 마스터
-- ------------------------------------------------------------
CREATE TABLE tenants (
  id          VARCHAR(40)   PRIMARY KEY,
  name        VARCHAR(200)  NOT NULL,
  plan        VARCHAR(40)   NOT NULL DEFAULT 'STANDARD',
  created_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
);
COMMENT ON TABLE tenants IS '테넌트(협력사 단위). 모든 업무 데이터의 최상위 파티션 키';

CREATE TABLE users (
  id          VARCHAR(40)   PRIMARY KEY,
  tenant_id   VARCHAR(40)   NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name        VARCHAR(100)  NOT NULL,
  email       VARCHAR(200)  UNIQUE,
  role        user_role     NOT NULL,
  is_active   BOOLEAN       NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
);
COMMENT ON TABLE users IS '사용자. role 로 화면·권한 분기';

CREATE TABLE equipments (
  id          VARCHAR(40)   PRIMARY KEY,
  tenant_id   VARCHAR(40)   NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name        VARCHAR(200)  NOT NULL,
  type        VARCHAR(40)   NOT NULL,
  line        VARCHAR(60),
  substances  JSONB         NOT NULL DEFAULT '[]'::jsonb,
  created_at  TIMESTAMPTZ   NOT NULL DEFAULT now(),
  CONSTRAINT chk_equipments_substances_array CHECK (jsonb_typeof(substances) = 'array')
);
COMMENT ON TABLE equipments IS '설비 마스터. substances(JSON 배열)는 법령 매칭 입력';
COMMENT ON COLUMN equipments.type IS 'GAS_CABINET / VALVE / PIPING / SCRUBBER … (개방형 코드)';

CREATE TABLE parts (
  id                 VARCHAR(40)   PRIMARY KEY,
  tenant_id          VARCHAR(40)   NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  part_no            VARCHAR(100)  NOT NULL,
  name               VARCHAR(200)  NOT NULL,
  spec               JSONB         NOT NULL DEFAULT '{}'::jsonb,
  grade              part_grade    NOT NULL,
  toxic_gas_allowed  BOOLEAN       NOT NULL DEFAULT FALSE,
  stock              INT           NOT NULL DEFAULT 0,
  created_at         TIMESTAMPTZ   NOT NULL DEFAULT now(),
  CONSTRAINT uq_parts_tenant_part_no UNIQUE (tenant_id, part_no),
  CONSTRAINT chk_parts_stock_nonneg  CHECK (stock >= 0),
  CONSTRAINT chk_parts_spec_object   CHECK (jsonb_typeof(spec) = 'object')
);
COMMENT ON TABLE parts IS '부품 마스터. spec(JSON)은 A1 SPEC 에이전트 비교 입력';

CREATE TABLE equipment_parts (
  equipment_id      VARCHAR(40)  NOT NULL REFERENCES equipments(id) ON DELETE CASCADE,
  part_id           VARCHAR(40)  NOT NULL REFERENCES parts(id) ON DELETE RESTRICT,
  installed_at      TIMESTAMPTZ,
  last_replaced_at  TIMESTAMPTZ,
  qty               INT          NOT NULL DEFAULT 1,
  PRIMARY KEY (equipment_id, part_id),
  CONSTRAINT chk_equipment_parts_qty CHECK (qty > 0)
);
COMMENT ON TABLE equipment_parts IS 'N:M 연결 — 설비에 장착된 부품(BOM). equipments ↔ parts';

CREATE TABLE part_compatibility (
  part_id                VARCHAR(40)  NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
  alt_part_id            VARCHAR(40)  NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
  diff                   TEXT,
  allowed_for_toxic_gas  BOOLEAN      NOT NULL DEFAULT FALSE,
  PRIMARY KEY (part_id, alt_part_id),
  CONSTRAINT chk_part_compat_not_self CHECK (part_id <> alt_part_id)
);
COMMENT ON TABLE part_compatibility IS 'N:M 자기참조 — 부품 호환표. parts ↔ parts';

-- ------------------------------------------------------------
-- 3. AI — 법령 인덱스 (legal_findings 가 참조하므로 먼저 생성)
-- ------------------------------------------------------------
CREATE TABLE law_index (
  id              SERIAL        PRIMARY KEY,
  law             VARCHAR(200)  NOT NULL,
  article         VARCHAR(60)   NOT NULL,
  title           VARCHAR(200)  NOT NULL,
  text            TEXT          NOT NULL,
  equipment_type  VARCHAR(40),
  substance       VARCHAR(40),
  effective_date  DATE,
  source_uri      VARCHAR(500),
  updated_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
  CONSTRAINT uq_law_index_law_article UNIQUE (law, article)
);
COMMENT ON TABLE law_index IS '법령 조문 인덱스(법제처 사전 적재). A2 LEGAL 에이전트 검색 원천. 개정 시 재적재';
COMMENT ON COLUMN law_index.equipment_type IS '적용 설비 유형 필터 (NULL = 공통)';
COMMENT ON COLUMN law_index.substance IS '적용 물질 필터 (NULL = 공통)';

-- ------------------------------------------------------------
-- 4. 트랜잭션 — 요청(사실) → 에이전트 산출 → 사람의 결정
-- ------------------------------------------------------------
CREATE TABLE work_requests (
  id               VARCHAR(40)          PRIMARY KEY,
  tenant_id        VARCHAR(40)          NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  equipment_id     VARCHAR(40)          NOT NULL REFERENCES equipments(id) ON DELETE RESTRICT,
  part_id          VARCHAR(40)          NOT NULL REFERENCES parts(id) ON DELETE RESTRICT,
  symptom          TEXT                 NOT NULL,
  site_check_note  TEXT,
  requested_by     VARCHAR(40)          NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  status           work_request_status  NOT NULL DEFAULT 'REQUESTED',
  created_at       TIMESTAMPTZ          NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ          NOT NULL DEFAULT now(),
  CONSTRAINT chk_work_requests_symptom_nonempty CHECK (length(btrim(symptom)) > 0),
  CONSTRAINT chk_work_requests_updated_after_created CHECK (updated_at >= created_at)
);
COMMENT ON TABLE work_requests IS '교체 작업 요청(사실 계층). 상태머신 REQUESTED→RUNNING→REVIEW→PENDING_APPROVAL→APPROVED|REJECTED→DONE';

CREATE TABLE agent_runs (
  id                    VARCHAR(40)       PRIMARY KEY,
  work_request_id       VARCHAR(40)       NOT NULL REFERENCES work_requests(id) ON DELETE CASCADE,
  overall_status        agent_run_status  NOT NULL DEFAULT 'RUNNING',
  steps_json            JSONB             NOT NULL DEFAULT '[]'::jsonb,
  summary               TEXT,
  approval_required_by  user_role,
  model_name            VARCHAR(100)      NOT NULL DEFAULT 'mock-v1',
  prompt_version        VARCHAR(60)       NOT NULL DEFAULT 'replaceflow-v0.1',
  created_at            TIMESTAMPTZ       NOT NULL DEFAULT now(),
  completed_at          TIMESTAMPTZ,
  CONSTRAINT chk_agent_runs_steps_array CHECK (jsonb_typeof(steps_json) = 'array'),
  CONSTRAINT chk_agent_runs_completed_after_created CHECK (completed_at IS NULL OR completed_at >= created_at),
  CONSTRAINT chk_agent_runs_review_has_completed CHECK (overall_status <> 'REVIEW' OR completed_at IS NOT NULL)
);
COMMENT ON TABLE agent_runs IS '에이전트 실행 1회(산출 계층). steps_json = CONTRACT AgentRun.steps 원본';

CREATE TABLE legal_findings (
  id              SERIAL        PRIMARY KEY,
  agent_run_id    VARCHAR(40)   NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  law_index_id    INT           REFERENCES law_index(id) ON DELETE SET NULL,
  law             VARCHAR(200)  NOT NULL,
  article         VARCHAR(60)   NOT NULL,
  title           VARCHAR(200),
  quote           TEXT,
  procedure_name  VARCHAR(200),
  phase           VARCHAR(10),
  required        BOOLEAN,
  CONSTRAINT chk_legal_findings_phase CHECK (phase IS NULL OR phase IN ('BEFORE', 'AFTER')),
  CONSTRAINT chk_legal_findings_procedure_has_phase CHECK (procedure_name IS NULL OR phase IS NOT NULL)
);
COMMENT ON TABLE legal_findings IS '이 건에 적용된 법령 조문 + 요구 절차 스냅샷. law_index 와 분리하여 법 개정 후에도 과거 판단 보존';
COMMENT ON COLUMN legal_findings.required IS 'true/false, NULL = UNKNOWN(안전관리자 판단 위임)';

CREATE TABLE documents (
  id            VARCHAR(40)    PRIMARY KEY,
  agent_run_id  VARCHAR(40)    NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  type          document_type  NOT NULL,
  title         VARCHAR(200),
  body          TEXT           NOT NULL,
  missing_json  JSONB          NOT NULL DEFAULT '[]'::jsonb,
  version       INT            NOT NULL DEFAULT 1,
  created_at    TIMESTAMPTZ    NOT NULL DEFAULT now(),
  CONSTRAINT chk_documents_version_pos    CHECK (version >= 1),
  CONSTRAINT chk_documents_missing_array  CHECK (jsonb_typeof(missing_json) = 'array')
);
COMMENT ON TABLE documents IS 'A3/A4 가 생성한 서류 초안. missing_json 이 비어야 submit-approval 통과(422 게이트)';

CREATE TABLE approvals (
  id               VARCHAR(40)        PRIMARY KEY,
  work_request_id  VARCHAR(40)        NOT NULL REFERENCES work_requests(id) ON DELETE CASCADE,
  approver_id      VARCHAR(40)        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  decision         approval_decision  NOT NULL,
  checklist_json   JSONB              NOT NULL DEFAULT '{}'::jsonb,
  comment          TEXT,
  decided_at       TIMESTAMPTZ        NOT NULL DEFAULT now(),
  CONSTRAINT chk_approvals_checklist_object CHECK (jsonb_typeof(checklist_json) = 'object'),
  -- 승인 게이트(409): APPROVE 는 체크리스트 4항목이 모두 true 일 때만 저장 가능
  CONSTRAINT chk_approvals_approve_requires_checklist CHECK (
    decision <> 'APPROVE' OR (
      COALESCE(checklist_json ->> 'WORK_PERMIT', 'false') = 'true' AND
      COALESCE(checklist_json ->> 'RISK_ASSESSMENT', 'false') = 'true' AND
      COALESCE(checklist_json ->> 'LOTO_GAS_ISOLATION', 'false') = 'true' AND
      COALESCE(checklist_json ->> 'GAS_DETECTOR_CHECK', 'false') = 'true'
    )
  )
);
COMMENT ON TABLE approvals IS '사람의 결정 계층. 승인 주체는 SAFETY_MANAGER. 체크리스트 4항목은 감사 증적으로 JSON 보관';

-- ------------------------------------------------------------
-- 5. 설정 — Security & Config Isolation
-- ------------------------------------------------------------
CREATE TABLE ai_configs (
  tenant_id       VARCHAR(40)   NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  agent_type      agent_type    NOT NULL,
  provider        ai_provider   NOT NULL DEFAULT 'LOCAL_LLM',
  model_name      VARCHAR(100)  NOT NULL DEFAULT 'mock-v1',
  prompt_version  VARCHAR(60)   NOT NULL DEFAULT 'replaceflow-v0.1',
  egress_allowed  BOOLEAN       NOT NULL DEFAULT FALSE,
  updated_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, agent_type),
  -- 외부 API(OPENAI) 는 egress 허용 없이는 설정 불가
  CONSTRAINT chk_ai_configs_openai_requires_egress CHECK (provider <> 'OPENAI' OR egress_allowed = TRUE)
);
COMMENT ON TABLE ai_configs IS '테넌트×에이전트별 모델·프롬프트·egress 설정. 온프레미스 제약을 데이터로 표현';

CREATE TABLE audit_logs (
  id           BIGSERIAL     PRIMARY KEY,
  tenant_id    VARCHAR(40)   NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id      VARCHAR(40)   REFERENCES users(id) ON DELETE SET NULL,
  entity       VARCHAR(60)   NOT NULL,
  entity_id    VARCHAR(40)   NOT NULL,
  action       VARCHAR(40)   NOT NULL,
  before_json  JSONB,
  after_json   JSONB,
  created_at   TIMESTAMPTZ   NOT NULL DEFAULT now()
);
COMMENT ON TABLE audit_logs IS '감사 로그(변경 전/후 스냅샷). user_id NULL = 시스템/에이전트';

-- ------------------------------------------------------------
-- 6. 인덱스
-- ------------------------------------------------------------
CREATE INDEX idx_work_requests_status          ON work_requests (status);
CREATE INDEX idx_work_requests_tenant_created  ON work_requests (tenant_id, created_at DESC);
CREATE INDEX idx_agent_runs_work_request_id    ON agent_runs (work_request_id, created_at DESC);
CREATE INDEX idx_law_index_type_substance      ON law_index (equipment_type, substance);
CREATE INDEX idx_legal_findings_run            ON legal_findings (agent_run_id);
CREATE INDEX idx_documents_run_type            ON documents (agent_run_id, type);
CREATE INDEX idx_approvals_work_request_id     ON approvals (work_request_id);
CREATE INDEX idx_audit_logs_entity             ON audit_logs (entity, entity_id);
CREATE INDEX idx_audit_logs_created_at         ON audit_logs (created_at DESC);

-- ------------------------------------------------------------
-- 7. updated_at 자동 갱신 (work_requests)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_work_requests_updated_at
  BEFORE UPDATE ON work_requests
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

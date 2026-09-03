-- ============================================================
-- Argus(FixGuide) — PostgreSQL DDL (Supabase SQL Editor 에서 그대로 실행)
-- 기준: docs/CONTRACT.md v3.0 §5 "DB — 테이블 7개 + 제안 1개" (팀 「FixGuide 데이터 모델 정의서 v3.0」 번역)
-- 실행 순서: schema_postgres.sql → seed_data.sql
-- gen_random_uuid() 는 PostgreSQL 13+ 내장 함수(pgcrypto 불필요)
-- ============================================================

SET client_min_messages = WARNING;

-- ------------------------------------------------------------
-- 0. 재실행을 위한 정리 (개발 환경 전용; 운영에서는 주석 처리)
-- ------------------------------------------------------------
DROP TABLE IF EXISTS approvals             CASCADE;
DROP TABLE IF EXISTS agent_results         CASCADE;
DROP TABLE IF EXISTS agent_steps           CASCADE;
DROP TABLE IF EXISTS agent_runs            CASCADE;
DROP TABLE IF EXISTS work_request_photos   CASCADE;
DROP TABLE IF EXISTS work_requests         CASCADE;
DROP TABLE IF EXISTS ai_configs            CASCADE;
DROP TABLE IF EXISTS users                 CASCADE;

DROP TYPE IF EXISTS user_role;
DROP TYPE IF EXISTS work_request_status;
DROP TYPE IF EXISTS product_type;
DROP TYPE IF EXISTS agent_code;
DROP TYPE IF EXISTS agent_step_status;
DROP TYPE IF EXISTS run_status;
DROP TYPE IF EXISTS approval_decision;

-- ------------------------------------------------------------
-- 1. ENUM 타입 (CONTRACT.md v3.0 §2 도메인 Enum 문자열과 정확히 동일, 7종)
-- ------------------------------------------------------------
CREATE TYPE user_role            AS ENUM ('ENGINEER', 'SAFETY_MANAGER');
CREATE TYPE work_request_status  AS ENUM ('DRAFT', 'AI_RUNNING', 'AI_DONE', 'PENDING', 'APPROVED', 'REJECTED');
CREATE TYPE product_type         AS ENUM ('VALVE', 'FITTING_TUBE', 'REGULATOR', 'FILTER', 'ETC');
CREATE TYPE agent_code           AS ENUM ('A1', 'A2', 'A3');  -- A4(벤더)는 Phase 2
CREATE TYPE agent_step_status    AS ENUM ('WAITING', 'RUNNING', 'DONE', 'FAILED');
CREATE TYPE run_status           AS ENUM ('RUNNING', 'DONE', 'FAILED');
CREATE TYPE approval_decision    AS ENUM ('APPROVE', 'REJECT');

-- ------------------------------------------------------------
-- 2. users
-- ------------------------------------------------------------
CREATE TABLE users (
  id             UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  name           VARCHAR(20)   NOT NULL,
  email          VARCHAR(120)  NOT NULL UNIQUE,
  password_hash  VARCHAR(255)  NOT NULL,   -- bcrypt
  role           user_role     NOT NULL,
  created_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
);
COMMENT ON TABLE users IS '사용자. role 로 권한 분기(ENGINEER 는 본인 요청만, SAFETY_MANAGER 는 PENDING 이상 전체 — 위반 시 403)';
COMMENT ON COLUMN users.password_hash IS 'bcrypt 해시. 응답에 절대 포함되지 않는다(CONTRACT §5)';

-- ------------------------------------------------------------
-- 3. [제안] ai_configs — agent_runs 가 참조하므로 먼저 생성
--    v3.0 BE 는 이 테이블을 만들지 않았다 — Security & Config Isolation 을 테이블이 아니라
--    설정 계층(`backend/app/core/config.py`)으로 구현했다: AI_PROVIDER/EGRESS_ALLOWED 환경변수 +
--    `validate_egress()` 가 OPENAI/AX_PLATFORM 인데 egress 미허용이면 기동 자체를 막는다(fail-fast).
--    단일 테넌트 PoC 에서는 이쪽이 더 강한 설계다. 멀티테넌트로 확장해 테넌트별 설정이 필요해지면
--    이 [제안] 테이블로 승격한다 — 그때까지 DDL 에는 참고용으로 남겨 둔다(erd.md §9 근거).
-- ------------------------------------------------------------
CREATE TABLE ai_configs (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_code      agent_code    NOT NULL,
  provider        VARCHAR(20)   NOT NULL DEFAULT 'MOCK',
  model_name      VARCHAR(100),
  prompt_version  VARCHAR(60),
  temperature     DECIMAL(3,2),
  max_tokens      INT,
  egress_allowed  BOOLEAN       NOT NULL DEFAULT FALSE,
  is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
  CONSTRAINT chk_ai_configs_provider CHECK (provider IN ('MOCK', 'LOCAL_LLM', 'OPENAI')),
  CONSTRAINT chk_ai_configs_max_tokens_pos CHECK (max_tokens IS NULL OR max_tokens > 0)
);
COMMENT ON TABLE ai_configs IS '[제안] 에이전트별 모델·프롬프트 설정. API 키는 여기 두지 않는다(환경변수) — CONTRACT §5';
-- provider 는 CONTRACT §2 의 7종 Enum 목록에 없어 PostgreSQL ENUM 대신 VARCHAR+CHECK 로 구현(설계 원칙 5 는 "상태"에 한정, provider 는 상태가 아님)
CREATE UNIQUE INDEX uq_ai_configs_active_agent ON ai_configs (agent_code) WHERE is_active;  -- agent_code 당 활성 설정 1개만

-- ------------------------------------------------------------
-- 4. work_requests (사실 계층)
-- ------------------------------------------------------------
CREATE TABLE work_requests (
  id                    UUID                 PRIMARY KEY DEFAULT gen_random_uuid(),
  request_no            VARCHAR(20)          NOT NULL UNIQUE,   -- WR-YYYYMMDD-NNN, 서버 채번
  requester_id          UUID                 NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  equipment             VARCHAR(80),   -- 설비 마스터 없음(Phase 2) — 자유 입력
  line                  VARCHAR(50),
  substance              VARCHAR(80),
  operating_condition   JSONB,         -- 가변 구조 예: {"temperature":"상온","pressure":"3000 psi"}
  product_name          VARCHAR(120),
  product_type          product_type,
  spec_json              JSONB,         -- productType 별 필수 키(CONTRACT §2). 서버 검증(400 SPEC_SCHEMA_MISMATCH), DB CHECK 아님
  symptom                TEXT,
  site_memo              TEXT,
  engineer_note          TEXT,          -- submit-approval 필수 조건(422 SUBMIT_REQUIRED_FIELD_MISSING), DB NOT NULL 아님
  status                 work_request_status  NOT NULL DEFAULT 'DRAFT',
  created_at             TIMESTAMPTZ          NOT NULL DEFAULT now(),
  updated_at             TIMESTAMPTZ          NOT NULL DEFAULT now(),
  submitted_at           TIMESTAMPTZ,         -- PENDING 전이 시각, NULL = 미제출
  CONSTRAINT chk_work_requests_request_no_format CHECK (request_no ~ '^WR-[0-9]{8}-[0-9]{3}$'),
  CONSTRAINT chk_work_requests_updated_after_created CHECK (updated_at >= created_at),
  CONSTRAINT chk_work_requests_operating_condition_object CHECK (operating_condition IS NULL OR jsonb_typeof(operating_condition) = 'object'),
  CONSTRAINT chk_work_requests_spec_json_object CHECK (spec_json IS NULL OR jsonb_typeof(spec_json) = 'object')
);
COMMENT ON TABLE work_requests IS '요청(사실 계층). 상태머신 DRAFT→AI_RUNNING→AI_DONE→PENDING→APPROVED|REJECTED. DRAFT 허용을 위해 업무 컬럼은 DB NOT NULL 이 아니다 — draft=false 조건부 검증은 서비스 계층';
COMMENT ON COLUMN work_requests.request_no IS '업무 식별자(사람이 읽는 번호). 대리키 PK 는 id — 번호 체계가 바뀌어도 FK 무결성 유지(설계 원칙 1)';

-- ------------------------------------------------------------
-- 5. work_request_photos
-- ------------------------------------------------------------
CREATE TABLE work_request_photos (
  id               UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  work_request_id  UUID          NOT NULL REFERENCES work_requests(id) ON DELETE CASCADE,
  file_name        VARCHAR(255)  NOT NULL,
  storage_key      VARCHAR(500)  NOT NULL,   -- EXIF 제거 후 원본 저장 경로
  thumbnail_key    VARCHAR(500),             -- 320px 썸네일 저장 경로
  size             INT           NOT NULL,
  uploaded_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
  CONSTRAINT chk_photos_size_range CHECK (size > 0 AND size <= 10485760)  -- 파일당 10MB(API #9)
);
COMMENT ON TABLE work_request_photos IS '작업요청 첨부 현장 사진. 요청당 최대 5장(409 PHOTO_LIMIT_EXCEEDED) — 앱 레벨 제약, DB CHECK 로는 강제하지 않는다(행 삽입 시점 카운트 조회가 필요해 DB 트리거보다 서비스 계층이 자연스러움)';

-- ------------------------------------------------------------
-- 6. agent_runs / agent_steps / agent_results (추론 계층, append-only)
-- ------------------------------------------------------------
CREATE TABLE agent_runs (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  work_request_id  UUID        NOT NULL REFERENCES work_requests(id) ON DELETE CASCADE,
  status           run_status  NOT NULL DEFAULT 'RUNNING',
  started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at      TIMESTAMPTZ,
  input_snapshot   JSONB,      -- [제안] 실행 시점 work_request 스냅샷 — 에이전트 입력 재현·감사용
  ai_config_id     UUID REFERENCES ai_configs(id) ON DELETE SET NULL,  -- [제안, v3.0 BE 미구현 — 위 3절 주석 참조]
  CONSTRAINT chk_agent_runs_finished_after_started CHECK (finished_at IS NULL OR finished_at >= started_at),
  CONSTRAINT chk_agent_runs_input_snapshot_object CHECK (input_snapshot IS NULL OR jsonb_typeof(input_snapshot) = 'object')
);
COMMENT ON TABLE agent_runs IS '에이전트 실행 1회. append-only — 재실행 시 새 행 추가(UPDATE 아님, 설계 원칙 3)';

CREATE TABLE agent_steps (
  id            UUID              PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id        UUID              NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  agent_code    agent_code        NOT NULL,
  status        agent_step_status NOT NULL DEFAULT 'WAITING',
  message       VARCHAR(200),
  error_message TEXT,
  started_at    TIMESTAMPTZ,
  finished_at   TIMESTAMPTZ,
  CONSTRAINT uq_agent_steps_run_agent UNIQUE (run_id, agent_code)
);
COMMENT ON TABLE agent_steps IS 'run 1건당 A1/A2/A3 고정 3행. GET /agent-runs/{runId} 폴링 응답 원본. step 실패해도 HTTP 200 유지, 해당 step 만 FAILED+errorMessage';

CREATE TABLE agent_results (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id         UUID        NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  agent_code     agent_code  NOT NULL,
  payload_json   JSONB       NOT NULL DEFAULT '{}'::jsonb,
  edited         BOOLEAN     NOT NULL DEFAULT FALSE,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  original_json  JSONB,      -- [제안] 에이전트 원본 결과 보존 — edited=true 만으로는 변경 내용을 알 수 없어 필요
  CONSTRAINT uq_agent_results_run_agent UNIQUE (run_id, agent_code),
  CONSTRAINT chk_agent_results_payload_object CHECK (jsonb_typeof(payload_json) = 'object')
);
COMMENT ON TABLE agent_results IS 'run 1건당 A1/A2/A3 고정 3행. PATCH /agent-results/{id} 는 전체 치환(PUT-like). PENDING/APPROVED 면 409 RESULT_LOCKED';
-- payload_json 구조: A1/A2(항목형) {"items":[{"itemId":"i-01","text":"…","edited":false}]}
--                    A3(문서형)   {"documents":[{"docId":"d-01","type":"WORK_PERMIT","name":"…","content":"…","edited":false}]}

-- ------------------------------------------------------------
-- 7. approvals (행동 계층, append-only)
-- ------------------------------------------------------------
CREATE TABLE approvals (
  id               UUID              PRIMARY KEY DEFAULT gen_random_uuid(),
  work_request_id  UUID              NOT NULL REFERENCES work_requests(id) ON DELETE CASCADE,
  approver_id      UUID              NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  decision         approval_decision NOT NULL,
  reason           TEXT,             -- REJECT 시 10자 이상 필수(400 REJECT_REASON_REQUIRED) — 앱 레벨 검증
  reason_category  VARCHAR(30),      -- 고정 enum 여부 팀 미확정(CONTRACT §8-6)
  decided_at       TIMESTAMPTZ       NOT NULL DEFAULT now()
);
COMMENT ON TABLE approvals IS '사람의 결정. append-only — 재제출 후 재결정 시 새 행 추가, 직전 이력 보존. 체크리스트 blocking 없음(승인은 즉시, 거절만 사유 필수)';
COMMENT ON COLUMN approvals.reason IS 'REJECT 필수 규칙은 애플리케이션(FastAPI) 레벨에서만 검증한다 — 의도적으로 DB CHECK 를 두지 않았다';

-- ------------------------------------------------------------
-- 8. 인덱스 (CONTRACT §5 "인덱스" 5개 — UNIQUE 로 이미 생성된 것 제외)
-- ------------------------------------------------------------
CREATE INDEX idx_work_requests_requester_status  ON work_requests (requester_id, status);   -- E_01·E_05
CREATE INDEX idx_work_requests_status_submitted  ON work_requests (status, submitted_at);   -- S_01
-- request_no UNIQUE 는 컬럼 정의에서 이미 생성(3번째)
CREATE INDEX idx_approvals_wr_decided            ON approvals (work_request_id, decided_at);
CREATE INDEX idx_approvals_decided_at            ON approvals (decided_at);                 -- 5개 중 5번째
-- uq_agent_steps_run_agent, uq_agent_results_run_agent, uq_ai_configs_active_agent 는
-- CONTRACT §5 "UNIQUE 제약" 절에서 별도로 명시된 것으로, 위 "인덱스 5개" 와는 별개 항목이다.

-- ------------------------------------------------------------
-- 9. updated_at 자동 갱신 (work_requests)
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

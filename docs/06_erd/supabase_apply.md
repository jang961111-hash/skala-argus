# Supabase 적용 절차 — Argus(FixGuide) v3.0

`schema_postgres.sql` 이 v3.0(8테이블)으로 전면 교체됐다. 직접 Supabase SQL Editor 에 넣을 때 참고할 순서·주의점만 짧게 정리한다. 자세한 설계 근거는 `erd.md` 참조.

## 1. `gen_random_uuid()` — 확장이 필요한가

- PostgreSQL **13 이상**은 `gen_random_uuid()` 가 **코어에 내장**돼 있어 별도 확장 없이 바로 쓸 수 있다(PG13 릴리스 노트 — pgcrypto 없이도 동작하도록 추가됨).
- Supabase 프로젝트는 보통 PostgreSQL 15~17 을 쓰므로 대부분 **추가 조치가 필요 없다.**
- 다만 프로젝트 버전을 확실히 모르거나(Project Settings → Database → Postgres version 에서 확인 가능) 혹시 PG13 미만 레거시 프로젝트라면, `schema_postgres.sql` 맨 위에 아래 한 줄을 방어적으로 추가해도 무해하다(이미 설치돼 있으면 no-op):
  ```sql
  CREATE EXTENSION IF NOT EXISTS pgcrypto;
  ```

## 2. 실행 순서

1. Supabase 프로젝트 → 좌측 **SQL Editor** → **New query**
2. (버전 불확실 시) 1절의 `CREATE EXTENSION IF NOT EXISTS pgcrypto;` 를 맨 위에 붙인다.
3. `schema_postgres.sql` **전체**를 그대로 붙여넣고 **Run**. 파일 내부에 이미 아래 순서가 잡혀 있다 — 별도로 쪼개 실행할 필요 없다:
   - `DROP TABLE ... CASCADE` / `DROP TYPE ...` (재실행 시 충돌 방지, 자식→부모 역순: `approvals → agent_results → agent_steps → agent_runs → work_request_photos → work_requests → ai_configs → users`)
   - ENUM 타입 7종 생성(`user_role`, `work_request_status`, `product_type`, `agent_code`, `agent_step_status`, `run_status`, `approval_decision`) — **테이블보다 먼저**(컬럼이 이 타입을 참조하므로)
   - 테이블 8개를 FK 의존 순서로 생성: `users` → `ai_configs`([제안], `agent_runs` 가 참조하므로 `work_requests` 보다 먼저) → `work_requests` → `work_request_photos` → `agent_runs` → `agent_steps` → `agent_results` → `approvals`
   - 인덱스 5개 + UNIQUE/부분 유니크
   - `updated_at` 트리거 함수·트리거
4. 새 쿼리에 `seed_data.sql` 을 붙여넣고 **Run**. `BEGIN…COMMIT` 트랜잭션이라 중간에 실패하면 아무것도 남지 않는다 — 실패하면 에러 메시지 그대로 보고 원인(주로 FK 참조 UUID 오타)만 고치면 된다.
5. **재실행 시 충돌 없음**: `schema_postgres.sql` 을 몇 번 다시 돌려도 상단 `DROP ... CASCADE` 덕분에 깨끗하게 재생성된다(운영 전환 시에는 이 블록을 주석 처리할 것).

## 3. 실행 후 확인 쿼리

```sql
-- 테이블 8개
SELECT count(*) AS table_count FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- 기대값: 8

-- FK 8개 (CONTRACT §5 "관계 8개"와 대조)
SELECT conname, conrelid::regclass AS child, confrelid::regclass AS parent
FROM pg_constraint WHERE contype = 'f' ORDER BY conrelid::regclass::text;
-- 기대 행 수: 8

-- enum 7종
SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY typname;
-- 기대: agent_code, agent_step_status, approval_decision, product_type, run_status, user_role, work_request_status (7개)

-- 시드 건수(§8 erd.md 검증 결과와 동일해야 함)
SELECT 'users' t, count(*) FROM users
UNION ALL SELECT 'ai_configs', count(*) FROM ai_configs
UNION ALL SELECT 'work_requests', count(*) FROM work_requests
UNION ALL SELECT 'work_request_photos', count(*) FROM work_request_photos
UNION ALL SELECT 'agent_runs', count(*) FROM agent_runs
UNION ALL SELECT 'agent_steps', count(*) FROM agent_steps
UNION ALL SELECT 'agent_results', count(*) FROM agent_results
UNION ALL SELECT 'approvals', count(*) FROM approvals;
-- 기대: users 2 / ai_configs 3 / work_requests 6 / work_request_photos 2 /
--       agent_runs 5 / agent_steps 15 / agent_results 15 / approvals 2

-- work_requests 상태 6종 각 1건 확인
SELECT status, count(*) FROM work_requests GROUP BY status ORDER BY status;
```

모두 기대값과 일치하면 적용 완료다. 이 문서는 이번 세션에서 로컬 PostgreSQL 이 없어 **실제 Supabase 실행으로 검증하지 못했다** — 위 쿼리는 `sqlglot` 문법 검증만 거친 `schema_postgres.sql`/`seed_data.sql` 기준으로 작성한 예상 결과이니, 실행 후 반드시 대조해서 다르면 보고할 것.

# Supabase 셋업 런북 (D1-8 / D2-2)

담당: 장병헌(지휘) · 원 계획상 DevOps 신서현
작성: 2026-09-03 · 대상: `docs/06_erd/schema_postgres.sql` + `seed_data.sql`

> **순서가 중요하다.** 1~4단계(계정·프로젝트·접속정보)는 **지금 바로** 할 수 있다.
> 5단계(DDL 실행)는 **ERD 트랙이 v2.0 16테이블로 재작성을 끝낸 뒤**에 해야 한다.
> 지금 있는 DDL 은 v1.0 14테이블이라, 먼저 돌리면 나중에 전부 지우고 다시 해야 한다.

---

## 1. 프로젝트 생성 (5분)

1. https://supabase.com → **Start your project** → GitHub 계정으로 로그인
2. **New project** 클릭
3. 입력값
   - **Name**: `argus`
   - **Database Password**: 생성 버튼으로 강한 비밀번호 만들고 **반드시 안전한 곳에 복사해 둔다.** 이후 다시 볼 수 없다
   - **Region**: `Northeast Asia (Seoul)` — 데모 지연시간이 가장 짧다
   - **Pricing Plan**: Free
4. **Create new project** → 프로비저닝 약 2분 대기

## 2. 접속 문자열 확보 (2분)

1. 좌측 하단 **Project Settings**(톱니) → **Database**
2. **Connection string** 섹션 → **URI** 탭 선택
3. 문자열을 복사한다. 형태:
   ```
   postgresql://postgres.xxxxxxxx:[YOUR-PASSWORD]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
   ```
4. `[YOUR-PASSWORD]` 를 1단계에서 만든 실제 비밀번호로 치환한다
5. **Connection pooling** 을 쓰는 경우 포트가 `6543`, 직접 연결은 `5432` 다. 데모에는 `6543` 을 권장한다

## 3. `.env` 반영 (1분)

```bash
cd ~/projects/argus/backend
# .env 가 없으면
cp .env.example .env
```

`.env` 를 열어 `DATABASE_URL` 한 줄만 바꾼다:
```
DATABASE_URL=postgresql://postgres.xxxxxxxx:실제비밀번호@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
```

> `.env` 는 `.gitignore` 에 걸려 있어 커밋되지 않는다. **접속 문자열을 코드나 문서에 절대 적지 마라.**
> 팀에 공유할 때도 채팅이 아니라 각자 자기 `.env` 에 넣게 한다.

## 4. 드라이버 설치 (1분)

SQLite 폴백만 쓰던 상태라 PostgreSQL 드라이버가 없다.

```bash
cd ~/projects/argus/backend
.venv/bin/pip install "psycopg[binary]"
# 또는 SQLAlchemy 2.x 구버전 URL 을 쓰면: .venv/bin/pip install psycopg2-binary
```

설치 후 `requirements.txt` 의 주석 처리된 psycopg 줄을 활성화한다.

---

## 5. ⛔ DDL·시드 실행 — **ERD 트랙 완료 후에**

ERD 담당이 v2.0 16테이블로 재작성 중이다. 완료되면 알려주겠다. 그 뒤에:

### 5-1. SQL Editor 로 실행 (권장)
1. Supabase 좌측 **SQL Editor** → **New query**
2. `docs/06_erd/schema_postgres.sql` 전체를 붙여넣고 **Run**
3. 오류 없으면 새 쿼리에 `docs/06_erd/seed_data.sql` 붙여넣고 **Run**
4. 좌측 **Table Editor** 에서 **16개 테이블**이 보이는지 확인

### 5-2. 확인 쿼리
```sql
-- 테이블 16개인지
select count(*) from information_schema.tables where table_schema='public';

-- N:M 2개 살아있는지 (루브릭 직결)
select table_name from information_schema.tables
where table_schema='public' and table_name in ('equipment_parts','part_compatibility');

-- 시드 들어갔는지
select status, count(*) from work_requests group by status order by status;
```
기대: 테이블 16 · N:M 2행 · work_requests 6건(DRAFT·RUNNING·REVIEW·PENDING_APPROVAL·APPROVED·REJECTED 각 1)

### 5-3. 비밀번호 해시 덮어쓰기
시드 SQL 의 `password_hash` 는 플레이스홀더다. 실제 해시는 백엔드가 넣는다:
```bash
cd ~/projects/argus/backend
.venv/bin/python -m app.seed        # 또는 서버를 한 번 기동하면 자동 시드
```

### 5-4. 백엔드 기동 확인
```bash
cd ~/projects/argus/backend
.venv/bin/python -m uvicorn app.main:app --port 8000
# 다른 터미널에서
curl -s localhost:8000/api/v1/dashboard/summary | head -c 200
```

---

## 6. 발표 당일 리스크

| 리스크 | 대응 |
|---|---|
| 현장 네트워크에서 Supabase 접속 불가 | `.env` 의 `DATABASE_URL` 을 `sqlite:///./argus.db` 로 한 줄만 되돌리면 즉시 로컬 폴백. **이 전환을 리허설에서 최소 1회 연습할 것** |
| Free 플랜 프로젝트 일시정지(7일 미사용) | 발표 당일 아침에 대시보드 한 번 열어 깨워 둔다 |
| 비밀번호 분실 | Settings → Database → **Reset database password** |

## 7. 발표 증빙으로 남길 것

- Table Editor 에서 **16개 테이블 목록** 스크린샷
- 5-2 확인 쿼리 3개의 실행 결과 스크린샷
- 루브릭 "FE/BE 프로젝트 구조 및 **DB 연동 정상 여부**" 항목의 직접 근거가 된다

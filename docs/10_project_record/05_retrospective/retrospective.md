# 회고 (작성 중 — 각자 채운다)

> 발표 5번 섹션(회고 및 향후 확장, 2분) 재료.
> **각자 2줄씩 + KPT.** 빈 칸으로 두지 말 것.

## 1. 이번 프로젝트를 한 문장으로
Day 1 에 만든 설계를 Day 2 아침에 뒤집었고, 뒤집으면서 **더 많이 뺐다.**

## 2. 무엇을 뺐고 왜 뺐나 (발표 핵심 논지)
| 뺀 것 | 이유 |
|---|---|
| A4 벤더 에이전트 | 외부 연동이 필요해 온프레미스 전제와 충돌. Mock 으로 흉내 내면 나머지 3개의 근거 품질까지 의심받는다 |
| 승인 체크리스트 blocking | 승인 권한 자체가 사람에게 남으므로 Human-in-the-loop 은 유지된다. 게이트를 두 겹 두면 실제 운영에서 형식화된다 |
| 평균 승인 소요시간 KPI(엔지니어) | 엔지니어가 볼 지표가 아니다. 역할별로 KPI 를 갈랐다 |
| 마스터 테이블 9개 + N:M | A1 부품 마스터 연동과 한 몸. 지금 넣으면 아무도 참조하지 않는 빈 테이블 |

## 3. R&R 별 회고 (각자 2줄) — ⏳ 미작성
- 장병헌(지휘·BE·발표):
- 은태현(PM·DBA):
- 문승은(UX·FE):
- 신서현(DevOps):
- 정구현(API·BE):

## 4. KPT — ⏳ 취합 필요
**Keep** · **Problem** · **Try**

## 5. 한계 (정직하게)
- AI 는 전부 Mock 이다. 과정 범위가 기획~스캐폴딩이고 강의안이 Mock 을 요구했다. 실 LLM 전환은 `AgentService` 인터페이스 구현체 교체로 끝난다
- **N:M 관계가 이번 범위에 없다.** Phase 2 설계는 `docs/06_erd/erd_phase2.svg` 에 있다
- Supabase 실행은 로컬 PostgreSQL 부재로 문서 기준 미검증
- 커밋이 1인 명의다. 브랜치·PR 로 협업 이력을 남겼으나 `git shortlog` 는 1명으로 나온다
- **JWT 서명키에 개발용 폴백이 있다.** `backend/app/core/config.py:21` 의 `DEV_SECRET_KEY = "dev-insecure-secret-change-me"` — `SECRET_KEY` 환경변수가 없으면 이 값으로 서명한다. PoC 로는 적절하지만(키가 코드에 없고 env 에서 읽는 구조는 지켜짐), **운영 전환 시 반드시 교체**해야 한다. 이름에 `dev-insecure`·`change-me` 를 박아 둔 것은 의도적이다 — 실수로 넘어가지 않게

## 6. AI 실제 결합 시 로드맵
1. `ai_configs.provider` 를 `MOCK` → `LOCAL_LLM` 으로 (코드 변경 없음, 설정만)
2. `llm_agents.py` 의 `NotImplementedError` 를 실 구현으로 교체
3. `agent_runs.input_snapshot` 에 이미 실행 시점 전체 컨텍스트가 저장되므로 프롬프트 입력은 그대로 사용
4. `original_json` 보존 구조가 있어 AI 원본 ↔ 엔지니어 수정본 diff 가 가능
5. Phase 2: A1 부품 마스터·호환표 연동(N:M 3종), A4 벤더 에이전트

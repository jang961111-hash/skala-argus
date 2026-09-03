# 브랜치·병합 이력 (발표 슬라이드용)

생성 2026-09-03 17:03 · `git log --graph --merges` 실측

> Contributors 그래프 대신 이것을 쓴다. 커밋이 1인 명의라 Contributors 는 역효과지만,
> **브랜치 단위로 작업이 분리됐고 `--no-ff` 로 병합 이력이 보존됐다**는 것은 사실이고 이 그래프가 증명한다.

## 브랜치 구조 — `main` ← `develop` ← `feature/*` 10개
```
  develop
  feature/api-openapi-postman
  feature/be-v3-implementation
  feature/db-erd-v3
  feature/docs-planning-usecase
  feature/fe-nine-screens
  feature/final-docs-argus
  feature/ops-ci-e2e
  feature/pm-record-and-contract
  feature/rename-argus-visual
  feature/rename-to-argus
  main
```

## 병합 그래프
```
*   f750b16 Merge develop into main
|\  
| * a7df78a Merge feature/final-docs-argus into develop
* | 15584c0 Merge develop into main — Argus 시각 반영
|\| 
| * e9d59b1 Merge feature/rename-argus-visual into develop
* | 163a127 Merge develop into main — 프로젝트명 Argus 확정
|\| 
| * 1702bcb Merge feature/rename-to-argus into develop
* 4178c15 Merge develop into main — v3.0 릴리스
* d83a9aa Merge feature/pm-record-and-contract into develop
* c101472 Merge feature/ops-ci-e2e into develop
* 6efa918 Merge feature/docs-planning-usecase into develop
* d9feef5 Merge feature/db-erd-v3 into develop
* 05c0d1b Merge feature/api-openapi-postman into develop
* 451ed37 Merge feature/fe-nine-screens into develop
* 78f23ec Merge feature/be-v3-implementation into develop
```

## 브랜치별 담당 (커밋 본문에서 추출)

| 브랜치 | 담당 |
|---|---|
| `feature/api-openapi-postman` | 정구현 (API Architect) |
| `feature/be-v3-implementation` | 장병헌 (BE) · 정구현 (API Architect·BE) |
| `feature/db-erd-v3` | 은태현 (DBA) |
| `feature/docs-planning-usecase` | 문승은 (Product & UX) · 정구현 (API Architect) |
| `feature/fe-nine-screens` | 문승은 (Product & UX · FE) |
| `feature/final-docs-argus` | 은태현(PM) 문승은(UX·DOCS) 신서현(DevOps) 장병헌(발표) |
| `feature/ops-ci-e2e` | 신서현 (DevOps & Infra) · 정구현 (API Architect) |
| `feature/pm-record-and-contract` | 은태현 (PM) · 장병헌 (지휘) |
| `feature/rename-argus-visual` | 문승은 (FE) · 장병헌 (지휘) |
| `feature/rename-to-argus` | 전원 (전 산출물 영향) |

## 커밋 통계 (정직하게)
```
총 커밋      : 37
병합 커밋    : 14
브랜치       : 로컬 12 / 원격 12

    37	jang961111-hash
```

**커밋 작성자는 1인이다.** 팀 방침은 통합 커밋 + 커밋 본문에 담당 역할·이름 명시다.
"각자 계정으로 커밋했다"고 말하지 않는다 — `git shortlog -sn` 한 줄로 반박된다.

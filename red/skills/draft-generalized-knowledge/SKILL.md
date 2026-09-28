---
name: draft-generalized-knowledge
description: project가 완전히 "done"으로 끝날 때(phase 종료 아님) 이번 project에서 확정된 취약점 기법을 대상 정보 없이 일반화한 초안을 tech-docs/_pending_review/에 쓴다. 최종 tech-docs/ 승격은 Claude Code 몫 — 여기서는 초안만.
version: 1.0.0
author: llm-abliteration project
license: MIT
platforms: [linux]
tags: [knowledge, redteam, bugbounty, generalization]
category: redteam
---

# Draft Generalized Knowledge

## 이 Skill의 경계 (중요, `organize-exploit-artifacts`와 동일한 원칙)

너는 여기서 **초안만** 쓴다. `tech-docs/web/{general,frameworks,misc}/`는 이 project뿐
아니라 **앞으로 모든 project의 RAG 검색 결과에 영향을 주는 공유 지식 베이스**라서,
여기 직접 쓰지 않는다 — 대신 `tech-docs/_pending_review/<project_id>/`에 초안을
쓰고, 실제 승격(검토 후 `tech-docs/web/`로 옮기거나 기존 문서에 병합)은 사용자가
Claude Code로 직접 한다. **`write_generalized_knowledge` MCP 도구는 절대 호출하지
않는다** — 그건 공유 RAG DB에 즉시 반영되는 도구라 Claude Code 전용이다(SOUL.md
"메모리 사용 제약"과 같은 이유: 검증 안 된 네 판단이 이 project 하나로 안 끝나는
범위에 바로 반영되게 두지 않는다).

## When This Skill Activates

**phase 종료가 아니라 project가 실제로 `"done"`으로 확정될 때만** 호출한다 — SOUL.md
"2. A 종료 승인" 4번, 네가 `targets/<project_id>.json`의 `status`를 `"done"`으로 쓰는
바로 그 시점(`"paused"`면 이 Skill을 호출하지 않는다 — project가 계속될 거라 아직
"확정된 최종 결과"라고 부를 수 없다).

## 입력

- `organize-exploit-artifacts`가 만든 `PoC-코드.md`/`Exploit-코드.md`/`PoC-시나리오.md`/
  `Exploit-시나리오.md`(이미 project 종료 시퀀스에서 먼저 실행됐을 것 — 이 Skill이
  그 뒤에 옴).
- `recon_summary.json`의 `tech_stack`(어느 프레임워크 폴더 밑에 둘지 결정).
- `journal/web/<project_id>/*.md`(라운드별 일지 — 실제로 뭘 시도했고 뭐가 왜 먹혔는지
  근거 확인용).

## 일반화 원칙

- **기법(technique) 단위로 하나의 파일**, 그 안에 **케이스(case)를 쌓는다** — "SQL
  Injection이라는 기법 문서 하나 안에 boolean-blind/인증우회 등 케이스 여러 개"처럼.
  이미 같은 기법의 파일이 `tech-docs/web/frameworks/<tech_stack>/`나
  `tech-docs/web/general/`에 있으면(스캔해서 확인) 그 문서 구조를 참고해서 **같은
  포맷으로 케이스를 추가**하는 형태로 초안을 쓴다(새 파일을 또 만들지 않는다) — 없으면
  새 파일로 시작.
- **같은 기법 + 같은 방식**(예: 이미 있는 케이스와 페이로드 구조가 사실상 동일)이면 새
  케이스를 추가하지 않고 기존 케이스에 "재확인된 사례: `<project_id>`" 한 줄만 덧붙인다.
- **같은 기법 + 다른 방식**(예: SQLi인데 이번엔 숫자형 파라미터라 따옴표 이스케이프가
  아니라 타입 강제 우회)이면 새 케이스로 추가한다.
- **원리를 먼저, 페이로드는 그다음**: 왜 이 기법이 통하는지(예: "문자열 결합 쿼리에서는
  입력값이 SQL 문법의 일부가 된다", "`include` 기반 템플릿 엔진에서 traversal은 곧
  소스 유출이다")를 한 번 서술하고, 케이스마다 실제 페이로드/커맨드를 붙인다.
- **대상 식별 정보 절대 금지**: 도메인, IP, 실제 세션 토큰/쿠키 값, 계정명, 타임스탬프,
  대상 고유 문자열(테이블명·컬럼명이 그 사이트에서만 의미 있는 경우 등)은 전부 빼거나
  `<target>`/`<session_token>` 같은 placeholder로 바꾼다. 페이로드 자체(`' OR '1'='1`,
  `admin'--` 같은 기법의 핵심 문자열)는 일반적인 것이므로 남긴다.
- **출처는 조용히 남긴다**: 파일 맨 아래에 `<!-- 출처: journal/web/<project_id>/, Round
  N -->` 주석 한 줄로 — 문서 본문에 project_id를 노출하지 않되 Claude Code가 검증하러
  갈 수 있게.

## 저장 위치 및 파일명

`tech-docs/_pending_review/<project_id>/<technique-slug>.md` — slug는 영문 소문자
kebab-case(예: `sql-injection.md`, `directory-traversal.md`, `open-redirect.md`).
기존 `tech-docs/web/.../<technique-slug>.md`와 **같은 파일명**을 써서, Claude Code가
승격할 때 diff/병합하기 쉽게 한다.

## 승격 이후

승격(검토 후 `tech-docs/web/`로 이동/병합)은 전적으로 Claude Code 몫이다 — 이 Skill은
승격 여부나 시점에 관여하지 않는다. `tech-docs/_pending_review/<project_id>/`는
승격 후에도 네가 지우지 않는다(Claude Code가 검토 끝나면 직접 정리).

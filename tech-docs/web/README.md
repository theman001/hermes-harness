# tech-docs/web/

정적 기술문서 라이브러리(하이브리드 RAG의 "폴더" 절반 — VectorDB 없음, `file` 도구로
A가 직접 탐색). 근거: `etc/RAG-스키마.md`.

- **`general/`** — Web 공격 일반 기법(프레임워크 무관).
- **`frameworks/<name>/`** — 프레임워크별 기법(예: `frameworks/laravel/`, `frameworks/spring/`).
  `<name>`은 `recon_summary.tech_stack`이 확정된 값과 맞춤.
- **`misc/`** — general/frameworks 어디에도 안 맞는 가지각색 기법.

내용은 사람이 미리 조사해서 채워두거나, `organize-exploit-artifacts`의 산출물에서
Claude Code가 일반화 추출한 걸 여기로 승격(사이트별 특화 정보는 여기 절대 안 들어감 —
그건 `journal/web/<project_id>/`에만). **2026-09-23 추가**: project가 `"done"`으로
끝나면 A 자신이 `draft-generalized-knowledge` Skill로 `../_pending_review/
<project_id>/`에 초안을 미리 써두고, Claude Code는 그 초안을 검토해서 여기로
승격만 하면 됨(0에서부터 다시 뽑을 필요 없음) — 단, 초안이므로 그대로 복사하지 말고
대상 식별 정보 잔존 여부를 반드시 확인할 것(`_pending_review/README.md`의 승격
체크리스트 참고).

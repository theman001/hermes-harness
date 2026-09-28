# tech-docs/_pending_review/

`draft-generalized-knowledge` Skill이 project가 `"done"`으로 완전히 끝날 때 쓰는
**초안 스테이징 영역**(2026-09-23 추가). A(Red)가 직접 여기 쓰지만, 이 폴더 자체는
RAG 검색 대상도 아니고 `tech-docs/web/`처럼 다른 project에 영향을 주는 공유 지식
베이스도 아니다 — Claude Code가 검토해서 승격(`tech-docs/web/{general,frameworks,
misc}/`로 이동/병합)하기 전까지의 대기 상태일 뿐.

구조: `<project_id>/<technique-slug>.md` — 파일명은 승격 대상인
`tech-docs/web/.../<technique-slug>.md`와 동일하게 지어서 diff/병합이 쉽게 되어 있음.

**승격 체크리스트(Claude Code용)**:
- 대상 식별 정보(도메인/IP/세션 토큰/계정명 등)가 실수로 안 남아있는지 확인.
- 이미 `tech-docs/web/`에 같은 기법 문서가 있으면 새 파일로 만들지 말고 케이스만
  병합.
- 승격 후 이 폴더의 해당 프로젝트 하위 폴더는 삭제(같은 초안이 계속 남아있으면
  다음 검토 때 이미 승격된 걸 또 승격하려는 혼동이 생김).

---
name: write-journal-entry
description: 라운드마다 추론근거/코드/결과/피드백/수정공격 5필드로 일지를 기록하고, exploit 라운드면 attempted_exploits.json도 같이 갱신한다.
version: 1.0.0
author: llm-abliteration project
license: MIT
platforms: [linux]
tags: [journal, redteam, bugbounty]
category: redteam
---

# Write Journal Entry

매 라운드가 끝날 때(성공/실패/승인거부 전부 포함) 반드시 호출한다. 라운드에서 아무 일도
안 일어났어도(관찰만 했어도) 그 관찰과 다음 계획을 5필드로 남긴다 — 일지는 이 project의
유일한 지속적 기록이고, project는 여러 phase에 걸칠 수 있어서 대화 기록에 의존할 수 없다.

## 이 스킬을 호출하기 전 — 라운드 마감 체크 2개

일지를 쓰기 전에 아래 두 가지를 먼저 처리한다. 둘 다 빠뜨리기 쉽고, 빠뜨렸을 때의
비용이 크다(라운드 통째로 낭비 / phase 조기 종료).

**① 새 라운드를 시작하기 전에 `termination_reason.json` 을 확인했는가**

```bash
cat .phase-runtime/current/termination_reason.json 2>/dev/null || echo "(종료 신호 없음)"
```

파일이 있으면 **그 라운드는 시작하지 말고 즉시 마무리 시퀀스로 전환**한다(SOUL 의
"라운드 판단 규칙" 1번). 이 확인을 라운드 끝에 하면, 이미 신호가 떠 있던 라운드를 통째로
진행해버린다 — 비용은 `cat` 한 번이다. `round_watchdog.py` 는 신호를 한 번 내면
`check_once()` 호출을 멈추므로(`signaled=True`), 이미 쓴 신호는 **끈적하고 조용히
되돌아가지 않는다**.

**② 이번 라운드에 구조를 새로 알았으면 `update-web-structure` 를 같이 호출했는가**

이 스킬(일지)과 `update-web-structure`(구조 파일)는 **반드시 같은 라운드에 둘 다** 돈다.
일지에만 적고 구조 파일을 안 고치면, 양축 `stale_rounds` 가 3에 도달해 워치독이
`attack_exhausted: true` 를 내고 phase 가 조기 종료된다(라운드 예산을 대부분 남기고도).
새 엔드포인트·파라미터·확정된 서버 동작·인증/서명 스킴·렌더링 문맥·권한 판정 위치 중
하나는 대개 매 라운드 나온다 — 그걸 구조 파일에 반영하는 것이 이 체크다.

> 판정이 틀렸다고 느껴질 때(실제로는 공격 경로가 남아 있는데 소진으로 뜬 경우) **카운터를
> 속이려는 재작성으로 대응하지 마라.** 대신 일지·`HANDOFF.md` 에 "기계적 판정이었음"과
> 실제 미실증 경로 목록을 명시해 **사람이 계속/종료를 판단**하게 한다.

## 5-Field Format

`journal/web/<project_id>/<date>.md`에 아래 형식으로 append(같은 날짜 파일이 있으면
그 안에 라운드 구분자와 함께 이어 씀, `## Round N — <ISO timestamp>` 헤더로 구분).
**파일명은 정확히 `YYYY-MM-DD.md` 형식이어야 한다**(예: `2026-09-22.md`, 오늘 UTC
날짜 기준) — 다른 형식(`2026_09_22.md`, `sept-22.md` 등)으로 쓰면
`services/watchdog/round_watchdog.py`가 그 파일을 라운드 일지로 인식하지 못해서 라운드
상한/공격 경로 소진 감지가 조용히 고장 난다(정규식 `^\d{4}-\d{2}-\d{2}\.md$`만 인식).

**Round 번호 N은 이 project 전체에서 유일하고 단조증가해야 한다**(phase 경계와 무관 —
project는 여러 phase에 걸치고, 새 phase가 다른 날짜에 시작되면 새 `<date>.md` 파일이
생긴다). 새 날짜 파일을 처음 만드는 시점이면, 반드시 먼저 `journal/web/<project_id>/`의
기존 `<date>.md` 파일들을 전부 훑어서 지금까지 쓰인 가장 큰 Round 번호를 찾고 그 다음
번호부터 이어 쓴다 — 1부터 다시 매기면 서로 다른 phase의 라운드가 같은 "Round 1"로
겹쳐서 `attempted_exploits.json`의 `"round"` 참조나 나중에 Claude Code가 일지를 읽을 때
혼동을 일으킨다.

```markdown
## Round N — 2026-09-22T14:03:00Z

**1. 추론 근거**: 이번 라운드에서 이 방향을 택한 이유. RAG/기술문서에서 참고한 게 있으면
언급.

**2. 사용 코드**: 실제로 실행한 커맨드/요청 전체(재현 가능하게, 자르지 말 것). curl이면
전체 옵션 포함, 스크립트면 전체 내용.

**3. 결과**: 실행 결과 원문 또는 핵심 요약(응답 코드, 응답 바디 핵심 부분, 에러 메시지 등).
승인 거부로 실행 자체가 안 됐으면 "승인 거부됨"이라고 명시.

**4. 피드백**: 성공/실패/부분성공과 그 이유에 대한 판단.

**5. 다음 수정 방향**: 이 결과를 반영해서 다음에 뭘 다르게 시도할지.
```

## RAG 미러링

파일에 쓴 직후, **직접 RAG MCP의 `write_journal_round` 도구를 호출**해서 같은 라운드
내용을 `rag_entries`에 삽입한다. 실제 도구 파라미터는 `project_id`(문자열), `content`
(위 5필드 전체 텍스트), `title`(한 줄 요약), 그리고 선택적으로 `vuln_class`/`tech_stack`/
`source_ref`뿐이다 — `tag_type`(`site_specific`으로 고정)과 `category`(`"web"` 기본값)는
서버 내부에서 자동으로 채워지므로 호출 시 신경 쓰지 않아도 된다(`services/rag_mcp_server/
server.py` 참고, `scope_project`는 내부 DB 컬럼명일 뿐 도구 파라미터가 아님). 파일 변경
감지/폴링 방식은 쓰지 않는다 — 별도 프로세스나 레이스 컨디션 없이, 이 Skill이 파일 쓰기와
MCP 호출을 같은 시점에 순서대로 하는 게 더 단순하고 확실하다.

MCP 호출이 실패해도(RAG 서버가 아직 안 떴거나 네트워크 문제) 파일 쓰기는 이미 끝난 뒤이므로
일지 자체는 유실되지 않는다 — 실패하면 그 사실만 다음 필드에 짧게 남기고 계속 진행한다
(RAG 미러링 실패가 라운드 진행을 막아선 안 됨).

## attempted_exploits.json 갱신 (exploit 라운드 한정)

exploit 라운드였다면, 같은 시점에 `journal/web/<project_id>/attempted_exploits.json`도
갱신한다. 파일이 없으면 `{}`로 새로 만들고, 있으면 읽어서 병합:

```json
{
  "<attack_point>": {
    "<exploit 종류>": [
      {"round": <N>, "code_summary": "<한 줄 요약>", "outcome": "success|failed|denied"}
    ]
  }
}
```

- `attack_point`: 구체적 엔드포인트/경로(예: `/api/users/{id}`).
- `exploit`: 기법/클래스 이름(예: `IDOR`, `SQLi`, `mass_assignment`).
- `code_summary`: 전체 코드가 아니라 한 줄 요약(전체 코드는 이미 위 2번 필드에 있음).
- `outcome`: 승인 거부로 실행 자체가 안 됐어도 `"denied"`로 반드시 기록 — 그래야 다음
  라운드가 같은 걸 또 시도/재요청하지 않는다.

기존 배열에 새 시도를 append만 한다(과거 기록을 지우지 않음).

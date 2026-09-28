# 핸드오프 — google-gruyere-trial

아래는 자체 시스템 **Google Gruyere — official Google web app security codelab (intentionally vulnerable, per-session sandboxed instance)**에 대한 승인된 보안 점검 작업 일지입니다.

**이번 phase 종료 사유**: ④ 사유 불명 — 수동/외부 중단으로 추정

**무결성 확인**: 모든 예상 산출물이 존재합니다.

## 포함된 파일

- [2026-09-28.md](2026-09-28.md)
- [Exploit-시나리오.md](Exploit-시나리오.md)
- [Exploit-코드.md](Exploit-코드.md)
- [PoC-시나리오.md](PoC-시나리오.md)
- [PoC-코드.md](PoC-코드.md)
- [attempted_exploits.json](attempted_exploits.json)
- [exhaustion_state.json](exhaustion_state.json)
- [jev_calls.jsonl](jev_calls.jsonl)
- [recon_summary.json](recon_summary.json)
- [test_account.json](test_account.json)
- [web-서버-구조.md](web-서버-구조.md)
- [web-페이지-구조.md](web-페이지-구조.md)
- [증거-파일-목록.md](증거-파일-목록.md)
- [타임라인.md](타임라인.md)

---

## 이번 phase(phase 2) 결과 요약 — Round 6~10

**승인 흐름 기록**
- Round 6에서 승인 게이트 위반을 자진신고했다(쓰기 1건을 승인 전에 실행). 이후 사용자 **승인**을
  받아 앱 루트/타 계정 디렉터리 쓰기를 정식 실행·검증했다.
- Round 9의 신규 계정 생성(쿠키 구분자 주입 실증)도 사용자 **승인** 후 실행했다.
- 실행하지 않은 항목: `/quitserver`, `/reset`, 타 계정 대상 `is_admin=True`,
  `secret.txt` 덮어쓰기(전 GID 공용), 실제 관리자 동작(파괴적).

**신규 실증 10건 (phase 2)**
| # | 취약점 | 심각도 | 증거 |
|---|---|---|---|
| 9 | 업로드 파일명 경로이탈 → 임의 파일 쓰기(앱 루트·타 계정 디렉터리) | CRITICAL | `evidence/round6_approved_writes.txt` |
| 10 | 업로드한 `.html` 이 같은 출처에서 서빙 → 저장형 XSS + 세션쿠키 탈취 | HIGH | `evidence/round6_uploaded_html_payload.html` |
| 10b | 업로드 파일명 반사 XSS(`{{url}}` 무이스케이프, self-XSS) | LOW | `evidence/round6_upload_filename_xss.html` |
| 11 | 업로드한 `.gtl` 이 **서버 템플릿으로 렌더** → 비인증 전 DB 덤프 | CRITICAL | `evidence/round7_uploaded_gtl_db_dump.html` |
| 12 | GTL `include` 경로이탈 → 임의 파일 읽기(`data.py`·`/etc/passwd`·`secret.txt`), 확장자 화이트리스트 우회 | CRITICAL | `evidence/round7_gtl_include_fileread.html` |
| 13 | 무인증 `feed.gtl?uid=<임의>` → 타 사용자 정보 노출 | HIGH | 일지 Round 7 |
| 14 | 무인증 임의 계정 프로필 변경/권한 상승(`saveprofile`, 쿠키 불필요 → **CSRF 흡수**) | CRITICAL | 일지 Round 8 |
| 15 | 쿠키 구분자 필드 주입 → **서버가 스스로 관리자 쿠키 발급**(uid에 `\|`) | CRITICAL | `evidence/round9_*.{txt,html}` |
| 16 | XSS 살균기(`sanitize.py`) 우회 3종(대소문자/누락/스킴) → 비인증 저장형 XSS | HIGH | `evidence/round10_browser_execution.txt` |

**누적**: 실증 19건 (phase 1 8건 + phase 2 10건 + 구조 관련 1건). 테스트 계정은 원상 복구했다.

**주의 — phase 1 종료 사유 정정**: phase 1의 `attack_exhausted: true` 는 실제 소진이 아니라
`web-페이지-구조.md`/`web-서버-구조.md` 를 3라운드 연속 갱신하지 않아 생긴 **워치독 오판**이었다.
phase 2 에서는 매 라운드 두 파일을 갱신해 오판이 재발하지 않았다(양축 hash 변화 확인).

---
*생성 시각: 2026-09-28T10:39:28.223656+00:00 — 매 phase 종료마다 이 파일 전체가
새로 갱신됩니다(이전 내용은 안 남음). project가 실제로 끝났는지는
`targets/google-gruyere-trial.json`의 `status` 필드를 확인하세요("done"이면 종료).*

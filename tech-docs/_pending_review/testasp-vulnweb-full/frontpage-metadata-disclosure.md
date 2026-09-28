# FrontPage Server Extensions 메타데이터 노출 (`/_vti_cnf/`)

> 승격 대상: `tech-docs/web/frameworks/iis-asp-mssql/frontpage-metadata-disclosure.md`
> (구식 IIS 사이트에 남아 있는 경우가 있어 별도 케이스로 가치 있음.)

## 1. 원리

IIS + FrontPage Server Extensions 로 관리되던 사이트는 웹루트에 `_vti_cnf/`, `_vti_pvt/`,
`_vti_bin/` 같은 **관리용 숨김 디렉터리**를 남긴다. 이 중 `_vti_cnf/` 에는 파일별 메타데이터
(`<파일명>.asp` 형태의 텍스트 파일)가 들어 있고, **인증 없이 읽히는 경우가 있다.**

여기서 얻는 것:
- **존재 오라클**: 메타데이터가 200 이면 그 파일이 실존한다(404 면 없음).
- **내부 경로 유출**: `vti_cachedsvcrellinks` 등에 내부 가상경로/사이트 별칭이 들어 있다
  (예: `FQUS|<내부경로>/styles.css`) → LFI 상대경로 계산에 유용.
- **페이지 인벤토리**: `vti_backlinkinfo` 에 사이트 내 페이지 목록이 나열된다 → 숨은 페이지 발견.
- **타임스탬프/버전**: `vti_extenderversion`(예: `4.0.2.8912`), `vti_timelastmodified` → 스택·노후도.

## 2. 확인 절차

```bash
for f in Default.asp styles.css index.html; do
  printf "%-14s " "$f"
  curl -s -o /dev/null -w '%{http_code} %{size_download}B\n' "$BASE/_vti_cnf/$f"
done
# 200 이면 실존. 404 면 파일 없음(= 존재 오라클로도 쓸 수 있다)
```

얻어진 메타데이터에서 뽑을 값:

| 키 | 의미 | 활용 |
|---|---|---|
| `vti_extenderversion` | 확장 버전 | 스택 지문 |
| `vti_timelastmodified` | 마지막 수정 | 자산 노후도(방치된 legacy 판단) |
| `vti_cachedsvcrellinks` | 내부 가상경로 | **LFI 상대경로 계산** |
| `vti_backlinkinfo` | 백링크(내부 페이지 목록) | 숨은 페이지 인벤토리 |

## 3. 반드시 함께 확인할 것 — 자격증명 탈취로 이어지지 않는지

이 프로젝트에서는 `_vti_cnf/*` 는 열려 있었지만 **`_vti_pvt/*`(설정, 서비스 파일)와
`_vti_bin/*`(실행 파일)는 전부 404** 였다. 즉 "메타데이터 노출 = 정보노출"로 끝났고
권한 상승으로 이어지지 않았다.

**그래서 결론을 이렇게 분리해 기록한다**:
- 성립: 내부 경로/페이지 인벤토리/버전 노출(정보노출 finding)
- 불가(검증): `_vti_pvt` 자격증명 파일, `_vti_bin` 실행 경로 — 상태코드 실측으로 근거 남김

## 4. 왜 이 케이스를 별도로 기록하는가

- 스캐너가 자주 놓치는 **저경쟁 영역**이고, 발견 즉시 **다른 취약점의 입력**(경로·페이지)이 된다.
- `_vti_*` 존재 자체가 "이 사이트가 2000년대 중반에 만들어져 방치됐다"는 신호 → 같은 시기 코드가
  남긴 다른 legacy 이슈(필터 없는 파일 읽기, 오픈 리다이렉트, 무이스케이프 INSERT)를 우선 탐색할
  근거가 된다. **메타데이터 노출은 단독 finding 보다 "탐색 방향 지시자"로서 가치가 크다.**

## 5. 방어 관점

- FrontPage Server Extensions 미사용 시 `_vti_*` 디렉터리 **삭제**(숨기는 것으로는 부족).
- IIS 요청 필터링으로 `_vti_` 패턴 차단, 웹루트에 메타데이터를 두지 않는다.

<!-- 출처: journal/web/testasp-vulnweb-full/, Round 12·14 -->

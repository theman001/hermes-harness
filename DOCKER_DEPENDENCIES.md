# Docker 배포 — 의존성 목록 + 배포 아키텍처

2026-09-23 실측 중 로컬(x86_64, Intel) 테스트 환경에 sudo apt/go install/git clone/pip으로
설치한 것 전부 정리(1~6번). **실 서비스는 Radxa Rock5 ITX(ARM64/aarch64, Debian +
OpenMediaVault 8)에서 Docker로 구동** — 여기 적힌 패키지명은 x86_64 Debian/Ubuntu 계열
기준으로 확인한 것이고, ARM64 이미지에서 그대로 apt 이름이 유효한지·아키텍처별 바이너리가
있는지는 별도 확인 필요(항목마다 표시). 배포 방식/운영 제약(git 전략, OMV8 GUI 제약, HDD
스토리지 계획)은 7~9번 참고 — 아직 실제 `docker-compose.yml`/`Dockerfile`은 안 씀,
여기 적힌 건 그거 쓸 때 지켜야 할 제약사항 정리.

## 1. apt 패키지 (Debian/Ubuntu 계열 기준)

```
nmap
nikto
sqlmap
gobuster
ffuf
whatweb            # 주의 참고
golang-go          # Go 툴체인 — 아래 2번 도구들 설치용, 최종 이미지엔 안 남겨도 됨(멀티스테이지 빌드로 런타임엔 바이너리만)
git curl wget perl python3   # 보통 베이스 이미지에 이미 있지만 명시적으로 확인
```

**⚠️ `whatweb` — 이 x86_64 테스트 환경에서 패키지 자체가 깨져 있었음**(`/usr/bin/whatweb`가
참조하는 `lib/messages.rb` 등 파일이 시스템에 아예 없음 — Debian 패키징 결함으로 추정).
지금은 `httpx`의 tech-detection으로 대체하고 포기했지만, **ARM64 이미지에서는 다시 시도해볼
가치 있음**(다른 리포지토리 미러/버전이면 정상일 수 있음) — 안 되면 그냥 계속 제외.

**Playwright(Chromium) headless 구동에 필요한 시스템 라이브러리** (GLib/GStreamer/
GObject-introspection 계열 — x86_64에서 `npx playwright install-deps --dry-run`으로 확인):
```
gir1.2-girepository-3.0
gir1.2-glib-2.0
gstreamer1.0-plugins-base
gstreamer1.0-plugins-good
libgirepository-2.0-0
libglib2.0-0t64
libglib2.0-bin
libglib2.0-data
libgstreamer-gl1.0-0
libgstreamer-plugins-base1.0-0
libxml2-16
```
패키지 이름 확인 방법(도커 빌드 중, 베이스 이미지가 ARM64일 때): 컨테이너 안에서
`npx playwright install-deps --dry-run` 그대로 실행 — 리스트가 다를 수 있으니 이 실행
결과를 신뢰할 것(위 목록을 그대로 복붙하지 말 것).

## 2. Go 기반 도구 (`go install`, 소스에서 빌드 — 아키텍처 무관하게 동작해야 함)

```
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install -v github.com/lc/gau/v2/cmd/gau@latest
```
(`gobuster`/`ffuf`는 apt로 이미 설치되므로 go install 중복 불필요 — 최신 버전이 꼭
필요하면 `go install github.com/OJ/gobuster/v3@latest` / `go install
github.com/ffuf/ffuf/v2@latest`로 대체 가능.)

**ARM64 관련**: `go install`은 로컬 Go 툴체인으로 소스에서 직접 컴파일하므로, ARM64
컨테이너 안에서 실행하면 자동으로 ARM64 바이너리가 나옴(`golang-go`를 apt로 깔면
아키텍처는 알아서 맞음 — go.dev에서 수동으로 tarball 받을 필요 없이 apt 패키지 쓰는 걸
권장, 아키텍처 실수 방지). 빌드 시간이 ARM64(특히 Rock5의 저클럭 코어)에서 x86_64보다
훨씬 오래 걸릴 수 있음 — 가능하면 **크로스 컴파일**(x86_64 빌드 머신에서
`GOARCH=arm64 GOOS=linux go install ...`로 미리 빌드해서 바이너리만 이미지에 복사)을
고려할 것. nuclei는 의존성 트리가 커서(mongo-driver 등) 이 환경에서도 빌드에
시간이 꽤 걸렸음(백그라운드로 넘어갈 정도).

## 3. Perl (nikto 의존성)

nikto는 apt 패키지로도 있지만(위 1번), 만약 git clone 방식을 쓴다면:
```
git clone --depth 1 https://github.com/sullo/nikto.git
cpanm XML::Writer   # perl 모듈, nikto 실행에 필요
```
**Docker에서는 apt 패키지(`nikto`)를 쓰는 걸 강력 권장** — 이번엔 sudo 없는 제약 때문에
git clone + cpanm(로컬 lib 부트스트랩까지) 우회를 했지만, 컨테이너는 root라 그럴 필요
없음. apt로 깔면 `libxml-writer-perl` 같은 의존 패키지가 자동으로 딸려옴.

## 4. Python (하네스 전용 venv — `services/` 컴포넌트용, `requirements.txt` 참고)

```
mitmproxy>=11.0
mcp<2   # 상한 반드시 유지 — mcp>=1.0으로 두면 v2.x가 깔려서 server.py(FastMCP, v1 API) import가 깨짐(실측 확인된 버그)
```
**ARM64 관련**: `mitmproxy`는 `cryptography` 패키지에 의존하는데, 최신 `cryptography`는
prebuilt wheel이 없는 아키텍처/파이썬 버전 조합에서 **Rust 컴파일러가 빌드 타임에
필요**함 — ARM64용 wheel이 PyPI에 있는지 그때 가서 확인, 없으면 이미지에 `cargo`/`rustc`
추가 필요(빌드 시간 증가). 미리 `pip install --dry-run` 또는 `pip download`로 wheel
가용성 확인 권장.

## 5. Node.js (Hermes 자체 설치 스크립트가 요구, agent-browser/Playwright용)

Hermes 설치 스크립트가 Node.js를 필요로 함(`uv`로 Python 환경도 같이 관리) — 공식
Node.js는 ARM64 빌드 제공하므로 일반적으로 문제 없음, 그래도 Hermes 설치 스크립트
자체가 ARM64를 실제로 지원/테스트했는지는 **레드블루-검토.md 체크리스트 0(a)**에서
이미 별도 확인 대상으로 잡혀 있음(아직 미실측).

## 6. mitmproxy CA 인증서 — 설치물이 아니라 런타임 생성물

`mitmdump`를 최초 1회 실행하면 `~/.mitmproxy/mitmproxy-ca-cert.pem`이 자동 생성됨 —
패키지 목록엔 안 들어가지만, `SSL_CERT_FILE`/`CURL_CA_BUNDLE`/`REQUESTS_CA_BUNDLE`이
이 경로를 가리켜야 프록시를 거치는 HTTPS가 전부 성공함(안 하면 "unable to get local
issuer certificate"로 전부 실패 — 이미 겪은 문제). Docker 컴포즈에서는 이 디렉토리를
볼륨으로 영속화하거나, 컨테이너 시작 스크립트에서 최초 1회 mitmdump를 미리 실행해두는
단계가 필요.

## ARM64 관련 알려진 리스크 요약 (docker-compose 작성 시 검증 순서 추천)

1. **Playwright Chromium** — ARM64 Linux 지원이 x86_64보다 상대적으로 새로 생긴 축이라
   가장 먼저 실측할 것(안 되면 browser toolset 자체를 이번 배포에서 스코프 아웃 검토).
2. **`cryptography`(mitmproxy 의존)** — wheel 가용성 확인, 없으면 Rust 빌드 체인 필요.
3. **Go 도구 빌드 시간** — Rock5의 실제 코어 성능으로 nuclei류 빌드가 얼마나 걸리는지
   실측(느리면 크로스 컴파일 전환).
4. **`whatweb` 패키징 버그가 ARM64 리포에서도 재현되는지** — 급하지 않음(이미 포기한
   도구라 안 돼도 치명적이지 않음).
5. **Hermes 설치 스크립트 자체의 ARM64 지원** — 체크리스트 0(a), 이 목록과 별개로
   가장 먼저 확인해야 하는 항목(Hermes 자체가 안 뜨면 나머지는 무의미).

## 7. Git 배포 전략 — 기본 private, 빌드 시점만 public

**결정(2026-09-23)**: hermes 구동에 필요한 파일(이 리포 또는 `hermes-harness/` 서브트리)은
git에 올리되 기본 private, **docker 빌드하는 순간에만 잠깐 public으로 전환**한다.

- Docker Compose는 `build.context`에 git URL을 직접 줄 수 있다(`https://github.com/<user>/
  <repo>.git#<branch>:<subdir>` 형식) — 별도 클론 스크립트 없이 `docker compose up` 한 번에
  클론+빌드+기동까지 됨. 다만 이 방식은 **인증 토큰 없이는 private 리포에서 실패**하므로,
  public 전환이 필요한 이유가 정확히 이거다.
- 전환 자체(private→public→private)는 자동화 안 하고 배포할 때마다 사용자가 GitHub에서
  직접 토글하는 수동 작업으로 남겨둠(현재 계획).
- **보안 리스크 — 해소됨(2026-09-23 정정)**: 처음엔 "`.env` 값을 compose에 인라인하면
  public 전환 순간 시크릿이 노출된다"고 우려했으나, **git에는 `.env.example`(플레이스홀더)
  만 올리고, 시크릿 채운 실제 `docker-compose.yml`은 그때그때 이 대화 세션에서 Claude
  Code에게 요청해서 받는 방식**으로 확정 — 그 결과물은 **git에 커밋하지 않고** OMV8 GUI에
  바로 붙여넣기만 함. git에 올라가는 compose 파일은 항상 플레이스홀더뿐이라 public 전환
  순간에도 실제 시크릿은 노출되지 않음. (아래 8번 갱신 참고.)
- 이 프로젝트는 모노레포(`llm-abliteration/`)이고 `hermes-harness/`는 그 서브폴더다 —
  전체 리포를 public 전환하면 GPU/Colab abliteration 파이프라인 관련 스크립트/로그도
  같이 노출된다. `#branch:hermes-harness`로 서브디렉토리만 빌드 컨텍스트로 좁힐 수는
  있지만, **그래도 리포 자체는 통째로 public이 되는 것**(Git엔 "폴더만 공개" 기능이 없음)
  — 배포가 잦아지면 `hermes-harness/`만 별도 리포로 분리하는 것도 고려할 것.

## 8. OMV8 GUI 배포 제약 — compose 파일 하나로 완결

**요구사항(2026-09-23)**: Rock5 보드는 Debian + OpenMediaVault 8(OMV8) 환경이고, OMV8의
GUI(Compose 플러그인)에 `docker-compose.yml` 텍스트만 붙여넣고 "Up"만 누르면 서비스가
뜨는 걸 목표로 한다 — 별도 스크립트 실행, 별도 `.env` 파일 준비, 수동 `git clone` 전부
없어야 함. 즉 아래가 전부 **compose 파일 하나에 인라인으로 들어가야 함**:

- GitHub 리포 주소 (`build.context`의 git URL, 위 7번)
- 필요한 프레임워크/의존성 설치 (compose가 참조하는 `Dockerfile`도 같은 git 리포에 커밋해
  `build.context`가 그 Dockerfile을 찾게 하거나, compose의 `build.dockerfile_inline`으로
  Dockerfile 내용 자체를 compose YAML 안에 직접 적는 방법도 있음 — 후자가 "파일 하나로
  완결"에 더 가까움)
- `.env` 내용 — `env_file:`로 별도 파일 참조하지 않고 `environment:` 키 아래 값을 직접
  나열하는 형태 자체는 유지(OMV8에 파일 하나만 붙여넣는 제약을 만족해야 하므로). **단,
  실제 시크릿 값이 들어간 버전은 git에 올리지 않는다(2026-09-23 확정)**:
  - Git에는 `docker-compose.yml`(값 자리가 `${MATTERMOST_TOKEN}` 같은 플레이스홀더이거나,
    `.env.example`처럼 빈 값)만 커밋.
  - **실제 배포 시**: 사용자가 이 대화(또는 이후 세션)에서 Claude Code에게 실제 값 채운
    compose 파일을 요청 → 그 자리에서 생성 → 사용자가 그 결과물을 그대로 OMV8 GUI에
    붙여넣음. 이 실제-값 버전은 **어디에도 커밋되지 않고 세션 산출물로만 존재**.
  - 이 방식으로 7번의 "public 전환 순간 시크릿 노출" 리스크가 원천적으로 사라짐 — git에
    올라가는 파일에 애초에 실제 값이 없으므로.

**아직 안 한 것**: 실제 `docker-compose.yml`(플레이스홀더 버전) 작성 자체는 이번엔
안 함(문서화만) — 위 제약을 지키는 실제 파일은 다음 단계에서 작성.

## 9. HDD 스토리지 계획 — 지금은 자리만 잡아둠

**계획(2026-09-23)**: Rock5 보드에 나중에 HDD를 연결하고, Hermes/하네스가 만드는
로그·데이터 전부(세션 DB, journal, RAG DB, mitmproxy 캡처, tech-docs 등)를 그 HDD로
저장할 예정 — 지금은 HDD가 아직 안 붙어 있으니 실제 마운트 경로는 모름.

**compose 작성 시 반영할 것**:
- 모든 영속 데이터 볼륨(아래 목록)의 호스트 경로를 **하나의 상위 경로(예:
  `/srv/hermes-data`)로 통일**해서, HDD 연결 후 OMV8에서 마운트 포인트를 잡으면 그 상위
  경로 하나만 바꾸면 전체가 HDD로 이동하게 설계할 것(볼륨마다 따로따로 경로를 흩어놓으면
  나중에 하나씩 다 고쳐야 함).
- 영속화 대상 목록(지금까지 실측하며 실제로 파일이 쌓이는 걸 확인한 것들):
  - `~/.hermes/profiles/red/`(세션 `state.db`, `sessions/`, `memories/`, `cron/`, `logs/`)
  - `~/.mitmproxy/`(CA 인증서 — 컨테이너 재시작마다 새로 생성되면 곤란, 반드시 영속화)
  - `hermes-harness/journal/`, `hermes-harness/targets/`, `hermes-harness/tech-docs/`
    (RAG `_pending_review/` 포함)
  - `hermes-harness/services/rag_mcp_server/rag.db`
  - `hermes-harness/.phase-runtime/`(mitmproxy 캡처 등 — phase 끝나면 삭제되는 휘발성
    데이터라 HDD 영속화 우선순위는 낮음, 단 phase 도중 캡처 용량이 실측 중 212MB까지
    커진 적 있어서 컨테이너 내부 디스크에만 두면 용량 압박 가능 — HDD로 보내는 게 안전)
- HDD 붙기 전까지는 이 경로들이 컨테이너 내부(또는 OS 디스크의 임시 위치)를 가리키게 두고,
  **HDD 연결 시 이 상위 경로 하나만 바꾸는 걸 표준 절차로 문서화**해둘 것(다음 단계에서
  compose 작성할 때 반영).

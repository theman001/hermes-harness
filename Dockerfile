# syntax=docker/dockerfile:1
#
# Radxa Rock5(ARM64/aarch64) + OpenMediaVault 8용 Hermes 하네스 이미지.
# 근거: DOCKER_DEPENDENCIES.md (2026-09-23 조사) — 여기 적힌 패키지/설치 순서는 그 문서의
# 1~6번을 그대로 옮긴 것. **ARM64 실기기에서 한 번도 실제로 빌드해본 적 없음** — 이 문서
# 자체가 표시한 리스크(Playwright/cryptography/whatweb/Go 빌드시간/Hermes 설치스크립트
# ARM64 지원)는 전부 미검증 상태로 남아있다. 처음 배포할 때 `docker compose build`
# 로그를 반드시 끝까지 확인할 것 — 실패하는 단계가 있으면 DOCKER_DEPENDENCIES.md의
# "ARM64 관련 알려진 리스크 요약" 순서대로 원인을 좁혀갈 것.

FROM debian:bookworm-slim AS gotools
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
# **apt의 golang-go(1.19)는 여기서 쓰면 안 됨** — 실제 Rock5/OMV8 빌드(2026-09-28)에서
# httpx 최신판의 go.mod가 `go 1.26.0`을 요구하는데 Go 1.19는 세 자리 버전 문자열 자체를
# 파싱 못 해서 "invalid go version: must match format 1.23"로 즉시 실패함(DOCKER_
# DEPENDENCIES.md 2번이 "apt 쓰면 아키텍처 실수 방지"라고 권했던 건 틀린 조언이었음 —
# 아키텍처는 맞았지만 버전이 몇 년 뒤처져 있었음). go.dev 공식 최신 안정판을 직접 받는다
# (아키텍처는 `dpkg --print-architecture`로 실제 조회해서 amd64/arm64 실수 방지, 버전은
# go.dev/VERSION에서 매 빌드 시점 최신을 그때그때 받아서 하드코딩 안 함).
RUN set -eux; \
    GOARCH="$(dpkg --print-architecture)"; \
    GOVER="$(curl -fsSL 'https://go.dev/VERSION?m=text' | head -1)"; \
    curl -fsSL "https://go.dev/dl/${GOVER}.linux-${GOARCH}.tar.gz" -o /tmp/go.tar.gz; \
    tar -C /usr/local -xzf /tmp/go.tar.gz; \
    rm /tmp/go.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH=/go
# DOCKER_DEPENDENCIES.md 2번 — go install은 컨테이너의 네이티브 아키텍처로 빌드되므로
# ARM64 이미지 안에서 돌리면 자동으로 ARM64 바이너리가 나옴. nuclei는 의존성이 커서
# 느릴 수 있음(문서에 이미 경고됨) — 너무 오래 걸리면 크로스 컴파일 전환 검토.
RUN go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest \
 && go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
 && go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest \
 && go install -v github.com/lc/gau/v2/cmd/gau@latest

FROM debian:bookworm-slim AS runtime
ENV DEBIAN_FRONTEND=noninteractive

# DOCKER_DEPENDENCIES.md 1번(apt 패키지) — whatweb은 x86_64에서도 패키지가 깨져 있었음
# (알려진 문제, httpx로 이미 대체됨) — ARM64에서 되면 덤, 안 되면 무시해도 됨.
# cargo/rustc는 mitmproxy의 cryptography 의존성이 ARM64용 prebuilt wheel이 없을 때
# 빌드 타임에 필요할 수 있어서 선제적으로 포함(문서 4번 경고) — wheel이 있으면 그냥 안 쓰임.
# **nikto는 여기 없음** — 실제 Rock5/OMV8 빌드(2026-09-28)에서 Debian bookworm 기본
# 저장소에 `nikto` 패키지 자체가 없는 것 확인(`E: Unable to locate package nikto`,
# 나머지는 전부 정상 해석됨) — 문서 3번에 이미 있던 git clone 우회법으로 아래에서 따로
# 설치. `libxml-writer-perl`(nikto의 XML::Writer 의존성, apt로 확실히 존재)만 여기서 챙김.
RUN apt-get update && apt-get install -y --no-install-recommends \
      nmap sqlmap gobuster ffuf whatweb \
      git curl wget perl python3 python3-venv python3-pip libxml-writer-perl \
      ca-certificates gnupg build-essential pkg-config libssl-dev cargo rustc \
    && rm -rf /var/lib/apt/lists/*

# nikto — apt 저장소에 없어서 git clone(순수 Perl 스크립트라 아키텍처 무관, 문서 3번
# 원안 그대로. cpanm 부트스트랩은 root 컨테이너에선 불필요 — libxml-writer-perl로 충분).
RUN git clone --depth 1 https://github.com/sullo/nikto.git /opt/nikto \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto \
    && chmod +x /opt/nikto/program/nikto.pl

# Node.js LTS — Hermes 설치 스크립트 + Playwright(agent-browser)용
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY --from=gotools /go/bin/ /usr/local/bin/

# Hermes Agent 공식 설치 스크립트(uv 등 자체 부트스트랩) — ARM64 지원 여부 미검증
# (레드블루-검토.md 체크리스트 0(a), 이 프로젝트가 지정한 최우선 미실측 항목).
RUN curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /opt/hermes-harness
COPY requirements.txt .
# 하네스 전용 venv(프로젝트 자체 관례 — GPU 파이프라인과 의존성 분리, 여기선 Docker
# 이미지가 이미 격리라 의미는 약하지만 관례 유지 + mcp<2 상한 등 requirements.txt의
# 고정 버전을 그대로 존중).
RUN python3 -m venv .venv && .venv/bin/pip install --no-cache-dir -r requirements.txt
# venv/bin을 PATH에 추가 — 이게 없으면 `docker exec`로 phase_start_local.py를 돌릴 때
# phase_start.py의 subprocess.Popen(["mitmdump", ...])가 bare 이름으로 mitmdump를
# 찾다가 실패함(로컬 개발 중 이미 한 번 겪은 문제와 동일 원인 — venv는 activate하거나
# PATH에 직접 넣어야 서브프로세스 lookup에도 걸림, `.venv/bin/python` 실행 자체는 PATH를
# 안 건드림).
ENV PATH="/opt/hermes-harness/.venv/bin:${PATH}"

# Playwright Chromium — install-deps로 배포판/아키텍처에 맞는 패키지를 자동 판단하게 함
# (DOCKER_DEPENDENCIES.md: "이 실행 결과를 신뢰할 것, 수동 목록 복붙하지 말 것").
# 실패해도 이미지 빌드 자체는 안 죽게(browser toolset만 못 쓰게 되는 정도로 축소).
RUN npx -y playwright install-deps chromium || echo "!! playwright install-deps 실패 — browser toolset 비활성화 검토"; \
    npx -y playwright install chromium || echo "!! playwright chromium 바이너리 설치 실패"

COPY . .

RUN chmod +x docker/entrypoint.sh
ENTRYPOINT ["docker/entrypoint.sh"]

#!/bin/bash
# 컨테이너 기동 시 1회 — 영속 데이터 시드/링크, mitmproxy CA 부트스트랩, Hermes 프로필
# 배치, .env 파일 생성(Hermes의 ${VAR}는 셸 환경변수가 아니라 프로필 자신의 .env 파일에서만
# resolve됨 — .claude/PROGRESS.md 2026-09-23 실측으로 이미 확인된 제약, docker-compose의
# environment: 값을 그대로 셸 env로 넘겨도 Hermes는 안 읽으므로 파일로 다시 써준다).
#
# HDD 마운트 계획(DOCKER_DEPENDENCIES.md 9번): 모든 영속 경로가 $HERMES_DATA_ROOT 하나의
# 접두사 밑에 있음 — HDD가 붙으면 docker-compose.yml의 volumes: 각 줄에서
# `/srv/hermes-data`를 새 마운트 경로로 찾아바꾸기만 하면 전체가 이동한다.
set -euo pipefail

DATA_ROOT="${HERMES_DATA_ROOT:-/srv/hermes-data}"
HARNESS_ROOT=/opt/hermes-harness
export HERMES_HARNESS_ROOT="$HARNESS_ROOT"

echo "[entrypoint] HERMES_DATA_ROOT=$DATA_ROOT"

# 1. 영속 볼륨 최초 시드 — 비어있으면 이미지에 이미 커밋돼 있던 초기 상태(과거 project
#    journal/tech-docs/RAG 등, 지금까지 쌓은 지식)로 채운다. 두 번째 기동부터는 이미
#    내용이 있으니 건드리지 않음(런타임에 새로 쌓인 데이터를 덮어쓰면 안 됨).
for d in journal targets tech-docs; do
  mkdir -p "$DATA_ROOT/hermes-harness/$d"
  if [ -z "$(ls -A "$DATA_ROOT/hermes-harness/$d" 2>/dev/null)" ]; then
    echo "[entrypoint] $d 최초 시드"
    cp -r "$HARNESS_ROOT/$d/." "$DATA_ROOT/hermes-harness/$d/" 2>/dev/null || true
  fi
done
if [ ! -f "$DATA_ROOT/hermes-harness/rag.db" ] && [ -f "$HARNESS_ROOT/services/rag_mcp_server/rag.db" ]; then
  cp "$HARNESS_ROOT/services/rag_mcp_server/rag.db" "$DATA_ROOT/hermes-harness/rag.db"
fi

# 2. journal/targets/tech-docs/rag.db를 영속 경로로 심볼릭 링크 — 이후 하네스 코드가
#    보는 경로($HERMES_HARNESS_ROOT/journal 등)는 그대로인데 실제 저장은 DATA_ROOT에 됨.
#
# **CONFIRMED 심각한 버그, 2026-09-29 수정**: `ln -sfn TARGET LINKNAME`은 LINKNAME이
# 이미 존재하는 "실제 디렉터리"면 그 디렉터리를 심볼릭 링크로 교체하는 게 아니라
# **그 디렉터리 안에** `LINKNAME/$(basename TARGET)` 심볼릭 링크를 새로 만들어버린다
# (재현 확인: `ln -sfn /a/b /existing_dir` → `/existing_dir/b -> /a/b`가 생기고
# `/existing_dir` 자체는 그대로 남음 — `-f`는 파일/심볼릭링크 교체에만 먹히고 `unlink()`가
# 디렉터리엔 항상 EISDIR이라 안 먹힘, `-n`도 이 경우엔 도움 안 됨). `journal`/`targets`/
# `tech-docs`는 `COPY . .`로 이미지에 **항상 실제 디렉터리로** 구워지므로, 이 세 줄은
# 매번 조용히 실패 모드로 빠져서 **A가 실제로 읽고 쓴 경로는 이미지에 구워진 일회용
# 디렉터리였고, `$DATA_ROOT`의 영속 볼륨은 한 번도 실제로 쓰인 적이 없었음** — 컨테이너를
# `down`/`up`(재생성)하면 그 일회용 디렉터리가 통째로 사라지는 게 실제 증상으로 나타남
# (사용자가 직접 발견: "재빌드 후 down/up 하면 agent가 만든 파일이 사라짐"). 파일(rag.db)
# 대상은 `unlink()`가 정상 동작해서 문제없었음(재현 확인) — 디렉터리 세 개만 문제.
# **수정**: 심볼릭 링크를 걸기 전에 기존 실제 디렉터리를 먼저 지운다(이 시점의 내용은
# 위 1번에서 이미 영속 경로로 복사/시드 끝난 뒤라 안전하게 버려도 됨).
rm -rf "$HARNESS_ROOT/journal" "$HARNESS_ROOT/targets" "$HARNESS_ROOT/tech-docs"
ln -sfn "$DATA_ROOT/hermes-harness/journal" "$HARNESS_ROOT/journal"
ln -sfn "$DATA_ROOT/hermes-harness/targets" "$HARNESS_ROOT/targets"
ln -sfn "$DATA_ROOT/hermes-harness/tech-docs" "$HARNESS_ROOT/tech-docs"
ln -sfn "$DATA_ROOT/hermes-harness/rag.db" "$HARNESS_ROOT/services/rag_mcp_server/rag.db"

# 3. Hermes 프로필 배치 — config.yaml/SOUL.md/skills는 매 기동마다 이미지 최신본으로
#    덮어써서 코드 변경이 반영되게 하고, memories/(런타임 상태)는 절대 안 덮어씀.
PROFILE_DIR="$DATA_ROOT/hermes-profile/red"
mkdir -p "$PROFILE_DIR/memories"
cp "$HARNESS_ROOT/red/config.yaml" "$PROFILE_DIR/config.yaml"
cp "$HARNESS_ROOT/red/SOUL.md" "$PROFILE_DIR/SOUL.md"
rm -rf "$PROFILE_DIR/skills"
cp -r "$HARNESS_ROOT/red/skills" "$PROFILE_DIR/skills"
mkdir -p /root/.hermes/profiles
ln -sfn "$PROFILE_DIR" /root/.hermes/profiles/red

# 4. 컨테이너 environment: 값을 프로필 .env 파일로 기록(위 설명 참고 — 이게 없으면
#    config.yaml의 ${DEEPSEEK_API_KEY} 등이 전부 빈 값으로 resolve됨).
cat > "$PROFILE_DIR/.env" <<EOF
HERMES_HARNESS_ROOT=$HARNESS_ROOT
HTTP_PROXY=http://127.0.0.1:8080
HTTPS_PROXY=http://127.0.0.1:8080
SSL_CERT_FILE=/root/.mitmproxy/mitmproxy-ca-cert.pem
CURL_CA_BUNDLE=/root/.mitmproxy/mitmproxy-ca-cert.pem
REQUESTS_CA_BUNDLE=/root/.mitmproxy/mitmproxy-ca-cert.pem
AGENT_BROWSER_ARGS=--disable-features=HttpsUpgrades,HttpsFirstModeV2,HttpsFirstBalancedMode
MATTERMOST_URL=${MATTERMOST_URL:-}
MATTERMOST_TOKEN=${MATTERMOST_TOKEN:-}
MATTERMOST_HOME_CHANNEL=${MATTERMOST_HOME_CHANNEL:-}
MATTERMOST_ALLOWED_USERS=${MATTERMOST_ALLOWED_USERS:-}
MATTERMOST_REPLY_MODE=thread
AUXILIARY_APPROVAL_BASE_URL=${AUXILIARY_APPROVAL_BASE_URL:-}
AUXILIARY_APPROVAL_MODEL=${AUXILIARY_APPROVAL_MODEL:-}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
TYPESAFE_API_KEY=${TYPESAFE_API_KEY:-}
EOF
chmod 600 "$PROFILE_DIR/.env"

# 5. mitmproxy CA 인증서 디렉터리만 영속 경로로 링크 — **mitmproxy 자체는 여기서 안
#    띄운다**(2026-09-28 정정: 처음엔 "게이트웨이 살아있는 동안 항상 떠 있게" 상시
#    기동시켰는데, 그러면 8080 포트를 이게 먼저 잡아버려서 나중에 `phase_start_local.py`
#    가 같은 포트로 phase별 mitmdump를 또 띄우려 할 때 충돌함 — 기존 로컬 운영 방식
#    (mitmproxy는 phase_start가 켜고 phase_end가 끔)과 안 맞는 불필요한 추가였음, 제거).
#    CA 인증서는 그 phase별 mitmdump가 처음 뜰 때 이 영속 경로에 알아서 생성/재사용됨.
mkdir -p "$DATA_ROOT/mitmproxy"
ln -sfn "$DATA_ROOT/mitmproxy" /root/.mitmproxy

echo "[entrypoint] 초기화 완료, hermes gateway 시작"
echo "[entrypoint] 새 project 시작(mitmproxy/watchdog도 이때 같이 기동됨): docker exec <container> $HARNESS_ROOT/.venv/bin/python $HARNESS_ROOT/services/colab_orchestrator/phase_start_local.py <project_id>"
echo "[entrypoint] project 종료 시: docker exec <container> $HARNESS_ROOT/.venv/bin/python $HARNESS_ROOT/services/colab_orchestrator/phase_end.py <project_id>"

# 7. Hermes 게이트웨이 — 컨테이너 메인 프로세스(foreground, PID 1이 이걸 감독).
exec hermes gateway run

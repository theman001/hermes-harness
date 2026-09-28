"""RAG 저장소 — 순수 DB/검색 로직 (MCP 프로토콜과 분리, server.py가 이걸 감싼다).

근거: etc/RAG-스키마.md 전체.

임베딩 모델: RAG-스키마.md "남은 확인 사항"에서 아직 미결(실제 CPU 성능 실측 필요) —
그 결정이 나기 전에도 검색 기능 자체는 동작해야 하므로, 기본값은 의존성 없는 간단한
토큰 오버랩 기반 벡터(`_naive_embed`)로 구현해둠. 실제 임베딩 모델이 정해지면
`embed_fn`에 그 함수를 주입해서 교체 — 이 파일의 나머지 로직(저장/조회/스코프 강제)은
그대로 재사용된다.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import threading
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

EmbedFn = Callable[[str], list[float]]

_TOKEN_RE = re.compile(r"[a-zA-Z0-9가-힣]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _stable_hash(token: str) -> int:
    """Python 내장 `hash()`는 문자열에 한해 프로세스마다 랜덤(해시 플러딩 방지용 보안
    기능, PYTHONHASHSEED)이라 재시작마다 값이 바뀜 — 2단계 4차 재검토로 발견: RAG 서버가
    매 Hermes/Claude Code 세션마다 새 프로세스로 뜨는데, 저장 시점(과거 프로세스)과
    조회 시점(지금 프로세스)의 버킷 매핑이 달라지면 예전에 저장한 임베딩이 전부 무의미한
    값이 됨(검색이 조용히 깨짐). `zlib.crc32`는 프로세스와 무관하게 항상 같은 값을 냄.
    """
    return zlib.crc32(token.encode("utf-8"))


def _naive_embed(text: str, dim: int = 256) -> list[float]:
    """의존성 없는 폴백 임베딩 — 토큰을 해시 버킷에 떨어뜨린 뒤 카운트 벡터를 L2 정규화.
    실제 임베딩 모델이 정해지기 전까지 검색 기능을 동작시키기 위한 것으로, 의미적 유사도가
    아니라 어휘 중복(bag-of-words) 기준이라는 한계가 있음.
    """
    vec = [0.0] * dim
    for token in _tokenize(text):
        vec[_stable_hash(token) % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))  # 둘 다 이미 L2 정규화돼 있으면 이게 코사인


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RagStore:
    def __init__(self, db_path: str | Path, embed_fn: EmbedFn | None = None):
        """2단계 재검토로 추가: `check_same_thread=False` + 자체 `Lock`. MCP 서버 프레임워크
        (FastMCP)가 동기 도구 함수를 스레드 풀에서 돌릴 가능성이 있는데(비동기 이벤트루프를
        안 막으려고 흔히 쓰는 패턴), sqlite3 커넥션은 기본적으로 생성한 스레드에서만 쓸 수
        있어서 그 경우 바로 ProgrammingError로 죽음 — capture_addon.py의 파일 락 때와
        같은 이유로(불확실한 프레임워크 동작에 기대지 않음) 방어적으로 처리."""
        self.db_path = Path(db_path)
        self.embed_fn = embed_fn or _naive_embed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self._lock:
            self.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # -- 쓰기 -----------------------------------------------------------

    def write_journal_round(
        self,
        *,
        project_id: str,
        content: str,
        title: str,
        vuln_class: str | None = None,
        tech_stack: str | None = None,
        category: str = "web",
        source_ref: str | None = None,
    ) -> str:
        """write-journal-entry Skill이 라운드마다 호출 — journal_round를 site_specific으로 삽입."""
        entry_id = str(uuid.uuid4())
        embedding = json.dumps(self.embed_fn(content))
        now = _now()
        with self._lock:
            self.conn.execute(
                """INSERT INTO rag_entries
                   (id, category, tag_type, scope_project, vuln_class, tech_stack, title,
                    content, source_type, source_ref, embedding, created_at, updated_at)
                   VALUES (?, ?, 'site_specific', ?, ?, ?, ?, ?, 'journal_round', ?, ?, ?, ?)""",
                (entry_id, category, project_id, vuln_class, tech_stack, title, content,
                 source_ref, embedding, now, now),
            )
            self.conn.commit()
        return entry_id

    def write_generalized_knowledge(
        self,
        *,
        content: str,
        title: str,
        tag_type: str = "framework_knowledge",
        vuln_class: str | None = None,
        tech_stack: str | None = None,
        category: str = "web",
        source_ref: str | None = None,
    ) -> str:
        """Claude Code가 일반화 추출 시 호출하는 예외 경로 — 대부분은 정적 라이브러리(폴더)로
        가지만, 폴더로 옮기기엔 너무 파편적인 경우만 이걸로 rag_entries에 남김.
        tag_type은 'framework_knowledge' | 'payload_technique'만 허용, scope_project는 NULL
        (전역 공유)."""
        if tag_type not in ("framework_knowledge", "payload_technique"):
            raise ValueError("tag_type must be framework_knowledge or payload_technique")
        entry_id = str(uuid.uuid4())
        embedding = json.dumps(self.embed_fn(content))
        now = _now()
        with self._lock:
            self.conn.execute(
                """INSERT INTO rag_entries
                   (id, category, tag_type, scope_project, vuln_class, tech_stack, title,
                    content, source_type, source_ref, embedding, created_at, updated_at)
                   VALUES (?, ?, ?, NULL, ?, ?, ?, ?, 'report_feedback', ?, ?, ?, ?)""",
                (entry_id, category, tag_type, vuln_class, tech_stack, title, content,
                 source_ref, embedding, now, now),
            )
            self.conn.commit()
        return entry_id

    def write_report(self, *, project_id: str, source_ref: str, entry_ids: list[str]) -> str:
        report_id = str(uuid.uuid4())
        now = _now()
        with self._lock:
            self.conn.execute(
                "INSERT INTO reports (id, project_id, source_ref, score, created_at, "
                "updated_at) VALUES (?, ?, ?, NULL, ?, ?)",
                (report_id, project_id, source_ref, now, now),
            )
            for entry_id in entry_ids:
                self.conn.execute(
                    "INSERT INTO report_entries (report_id, entry_id) VALUES (?, ?)",
                    (report_id, entry_id),
                )
            self.conn.commit()
        return report_id

    def update_report_score(self, *, report_id: str, score: int) -> None:
        if not 0 <= score <= 10:
            raise ValueError("score must be 0..10")
        with self._lock:
            self.conn.execute(
                "UPDATE reports SET score = ?, updated_at = ? WHERE id = ?",
                (score, _now(), report_id),
            )
            self.conn.commit()

    # -- 검색 (스코프 강제) -----------------------------------------------

    def search(
        self, *, query: str, category: str, current_project: str, top_k: int = 5
    ) -> list[dict]:
        """RAG-스키마.md "검색 시 스코프 강제" 절 그대로: 저장 시점 태그만 믿지 않고 조회
        쿼리 자체에 필터를 건다 — site_specific은 scope_project 일치하는 것만, 나머지
        두 tag_type은 전역(scope_project가 애초에 NULL로만 저장됨).
        """
        with self._lock:
            rows = self.conn.execute(
                """SELECT * FROM rag_entries
                   WHERE category = ?
                     AND (
                           tag_type IN ('framework_knowledge', 'payload_technique')
                        OR (tag_type = 'site_specific' AND scope_project = ?)
                     )""",
                (category, current_project),
            ).fetchall()

        if not rows:
            return []

        query_vec = self.embed_fn(query)
        scored = []
        for row in rows:
            entry_vec = json.loads(row["embedding"])
            score = _cosine(query_vec, entry_vec)
            scored.append((score, row))
        scored.sort(key=lambda pair: pair[0], reverse=True)

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "tag_type": row["tag_type"],
                "vuln_class": row["vuln_class"],
                "tech_stack": row["tech_stack"],
                "score": score,
            }
            for score, row in scored[:top_k]
        ]

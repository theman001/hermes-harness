-- RAG 스키마 — etc/RAG-스키마.md 그대로.

CREATE TABLE IF NOT EXISTS rag_entries (
    id            TEXT PRIMARY KEY,        -- uuid
    category      TEXT NOT NULL,           -- 'web' | 'app' | 'other' (지금은 항상 'web')
    tag_type      TEXT NOT NULL,           -- 'site_specific' | 'framework_knowledge' | 'payload_technique'
    scope_project TEXT,                    -- tag_type='site_specific'일 때만 값 있음
    vuln_class    TEXT,                    -- 'idor' | 'sqli' | 'xss' | 'business_logic' | 'auth' | ... (자유 텍스트)
    tech_stack    TEXT,                    -- 'php' | 'laravel' | ... (자유 텍스트, NULL 허용)
    title         TEXT NOT NULL,
    content       TEXT NOT NULL,
    source_type   TEXT NOT NULL,           -- 'journal_round' | 'report_feedback'
    source_ref    TEXT,
    embedding     BLOB NOT NULL,           -- float32 벡터 직렬화(json 텍스트로 저장, 아래 rag_store.py)
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rag_scope ON rag_entries(tag_type, scope_project);
CREATE INDEX IF NOT EXISTS idx_rag_category ON rag_entries(category);

CREATE TABLE IF NOT EXISTS reports (
    id           TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL,
    source_ref   TEXT NOT NULL,      -- 보고서 실제 본문 파일 경로
    score        INTEGER,            -- 0~10, 피드백 도착 전엔 NULL
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_entries (
    report_id TEXT NOT NULL REFERENCES reports(id),
    entry_id  TEXT NOT NULL REFERENCES rag_entries(id),
    PRIMARY KEY (report_id, entry_id)
);

-- MoltFire Dashboard Schema for Neon
-- Created: 2026-02-04

-- ============================================
-- LEARNING DATABASE
-- ============================================

CREATE TABLE IF NOT EXISTS decisions (
    id SERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    decision TEXT NOT NULL,
    context TEXT,
    reasoning TEXT,
    tags TEXT,
    outcome TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS outcomes (
    id SERIAL PRIMARY KEY,
    decision_id INTEGER NOT NULL REFERENCES decisions(id),
    timestamp TEXT NOT NULL,
    result TEXT NOT NULL,
    notes TEXT,
    impact_score INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lessons (
    id SERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    lesson TEXT NOT NULL,
    source_decisions TEXT,
    confidence INTEGER DEFAULT 50,
    times_validated INTEGER DEFAULT 0,
    times_contradicted INTEGER DEFAULT 0,
    tags TEXT
);

CREATE TABLE IF NOT EXISTS patterns (
    id SERIAL PRIMARY KEY,
    pattern_name TEXT NOT NULL,
    description TEXT,
    best_approach TEXT,
    success_rate REAL DEFAULT 0,
    sample_size INTEGER DEFAULT 0,
    tags TEXT
);

-- ============================================
-- INSPIRATION/IDEAS
-- ============================================

CREATE TABLE IF NOT EXISTS ideas (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    tags TEXT,
    captured_at TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    score INTEGER DEFAULT 0,
    effort_estimate TEXT,
    impact_estimate TEXT,
    fun_factor INTEGER DEFAULT 5,
    learning_potential INTEGER DEFAULT 5,
    income_potential INTEGER DEFAULT 0,
    notes TEXT,
    shipped_at TEXT,
    shipped_url TEXT
);

CREATE TABLE IF NOT EXISTS idea_updates (
    id SERIAL PRIMARY KEY,
    idea_id INTEGER NOT NULL REFERENCES ideas(id),
    timestamp TEXT NOT NULL,
    update_type TEXT,
    content TEXT
);

-- ============================================
-- GOALS
-- ============================================

CREATE TABLE IF NOT EXISTS goals (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    created_at TEXT NOT NULL,
    target_date TEXT,
    progress INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    completed_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS milestones (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER NOT NULL REFERENCES goals(id),
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS goal_updates (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER NOT NULL REFERENCES goals(id),
    timestamp TEXT NOT NULL,
    update_type TEXT,
    content TEXT
);

-- ============================================
-- RELATIONSHIPS/CRM
-- ============================================

CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    platform TEXT NOT NULL,
    handle TEXT,
    platform_id TEXT,
    temperature TEXT DEFAULT 'warm',
    status TEXT DEFAULT 'active',
    first_contact DATE,
    last_contact DATE,
    next_followup DATE,
    opportunity_type TEXT,
    opportunity_value TEXT,
    notes TEXT,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interactions (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type TEXT NOT NULL,
    direction TEXT NOT NULL,
    platform TEXT,
    platform_ref TEXT,
    summary TEXT,
    sentiment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- WORKFLOWS
-- ============================================

CREATE TABLE IF NOT EXISTS workflows (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    steps TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_run TEXT,
    run_count INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS executions (
    id SERIAL PRIMARY KEY,
    workflow_id INTEGER REFERENCES workflows(id),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT DEFAULT 'running',
    steps_completed INTEGER DEFAULT 0,
    total_steps INTEGER,
    output TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS step_results (
    id SERIAL PRIMARY KEY,
    execution_id INTEGER REFERENCES executions(id),
    step_index INTEGER,
    step_name TEXT,
    started_at TEXT,
    completed_at TEXT,
    status TEXT,
    output TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id SERIAL PRIMARY KEY,
    workflow_name TEXT NOT NULL,
    schedule TEXT NOT NULL,
    description TEXT,
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    last_run TEXT,
    next_run TEXT,
    run_count INTEGER DEFAULT 0
);

-- ============================================
-- TOKEN TRACKING
-- ============================================

CREATE TABLE IF NOT EXISTS token_usage (
    id SERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    model TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    operation TEXT,
    session_id TEXT,
    cost_estimate REAL DEFAULT 0
);

-- ============================================
-- CONTENT TRACKING
-- ============================================

CREATE TABLE IF NOT EXISTS content (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    platform TEXT NOT NULL,
    url TEXT,
    status TEXT DEFAULT 'draft',
    created_at TEXT NOT NULL,
    published_at TEXT,
    engagement_score INTEGER DEFAULT 0,
    notes TEXT
);

-- ============================================
-- SYNC METADATA
-- ============================================

CREATE TABLE IF NOT EXISTS sync_log (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    records_synced INTEGER DEFAULT 0,
    status TEXT DEFAULT 'success',
    error TEXT
);

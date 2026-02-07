-- Relationship Tracker Schema
-- MoltFire's mini-CRM for tracking contacts and follow-ups

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    platform TEXT NOT NULL,  -- moltbook, twitter, email, etc.
    handle TEXT,             -- @username or email
    platform_id TEXT,        -- platform-specific ID (moltbook author_id, etc.)
    
    -- Relationship state
    temperature TEXT DEFAULT 'warm',  -- hot, warm, cold
    status TEXT DEFAULT 'active',     -- active, nurturing, dormant, closed
    
    -- Context
    first_contact DATE,
    last_contact DATE,
    next_followup DATE,
    
    -- Opportunities
    opportunity_type TEXT,   -- bounty_collab, service_sale, knowledge_share, partnership
    opportunity_value TEXT,  -- estimated value or description
    
    -- Notes
    notes TEXT,
    tags TEXT,  -- comma-separated tags
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type TEXT NOT NULL,      -- comment, reply, dm, mention, email
    direction TEXT NOT NULL, -- inbound, outbound
    
    platform TEXT,
    platform_ref TEXT,       -- post_id, comment_id, message_id
    
    summary TEXT,
    sentiment TEXT,          -- positive, neutral, negative
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_contacts_platform ON contacts(platform, handle);
CREATE INDEX IF NOT EXISTS idx_contacts_followup ON contacts(next_followup);
CREATE INDEX IF NOT EXISTS idx_contacts_temperature ON contacts(temperature);
CREATE INDEX IF NOT EXISTS idx_interactions_contact ON interactions(contact_id);
CREATE INDEX IF NOT EXISTS idx_interactions_date ON interactions(date);

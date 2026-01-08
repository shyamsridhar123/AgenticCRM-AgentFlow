-- ============================================
-- Agentic CRM - AI Extensions for Existing Schema
-- This script adds AI-specific tables and columns
-- WITHOUT modifying existing table structures
-- ============================================

-- Add AI scoring columns to leads (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'leads' AND column_name = 'ai_score') THEN
        ALTER TABLE leads ADD COLUMN ai_score INTEGER DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'leads' AND column_name = 'ai_score_updated_at') THEN
        ALTER TABLE leads ADD COLUMN ai_score_updated_at TIMESTAMP WITH TIME ZONE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'leads' AND column_name = 'ai_qualification') THEN
        ALTER TABLE leads ADD COLUMN ai_qualification VARCHAR(50);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'leads' AND column_name = 'next_followup_at') THEN
        ALTER TABLE leads ADD COLUMN next_followup_at TIMESTAMP WITH TIME ZONE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'leads' AND column_name = 'last_contacted_at') THEN
        ALTER TABLE leads ADD COLUMN last_contacted_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

-- Add AI fields to opportunities
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'opportunities' AND column_name = 'ai_risk_score') THEN
        ALTER TABLE opportunities ADD COLUMN ai_risk_score INTEGER DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'opportunities' AND column_name = 'ai_predicted_close_date') THEN
        ALTER TABLE opportunities ADD COLUMN ai_predicted_close_date DATE;
    END IF;
END $$;

-- Add AI fields to activities
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'activities' AND column_name = 'ai_generated') THEN
        ALTER TABLE activities ADD COLUMN ai_generated BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- ============================================
-- NEW AI-SPECIFIC TABLES
-- ============================================

-- Agent execution logs
CREATE TABLE IF NOT EXISTS agent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    model_used VARCHAR(50),
    tokens_used INTEGER,
    execution_time_ms INTEGER,
    related_to_type VARCHAR(50),
    related_to_id UUID,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_logs_type ON agent_logs(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_logs_created ON agent_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_logs_related ON agent_logs(related_to_type, related_to_id);

-- Natural language query history
CREATE TABLE IF NOT EXISTS nl_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text TEXT NOT NULL,
    generated_sql TEXT,
    result_count INTEGER,
    user_id UUID,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nl_queries_user ON nl_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_nl_queries_created ON nl_queries(created_at DESC);

-- Pipeline AI predictions
CREATE TABLE IF NOT EXISTS pipeline_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    period_days INTEGER NOT NULL,
    predicted_revenue NUMERIC(15, 2),
    predicted_deals_won INTEGER,
    confidence_score NUMERIC(5, 2),
    model_version VARCHAR(50),
    factors JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_predictions_date ON pipeline_predictions(prediction_date DESC);

-- Email threads for AI summarization
CREATE TABLE IF NOT EXISTS email_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES contacts(contact_id),
    subject VARCHAR(500),
    last_message_at TIMESTAMP WITH TIME ZONE,
    message_count INTEGER DEFAULT 0,
    ai_summary TEXT,
    ai_sentiment VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_threads_contact ON email_threads(contact_id);

-- Email messages
CREATE TABLE IF NOT EXISTS email_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES email_threads(id),
    direction VARCHAR(20) NOT NULL, -- 'inbound' or 'outbound'
    from_email VARCHAR(255),
    to_email VARCHAR(255),
    subject VARCHAR(500),
    body_text TEXT,
    body_html TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    clicked_at TIMESTAMP WITH TIME ZONE,
    ai_generated BOOLEAN DEFAULT FALSE,
    template_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_messages_thread ON email_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_sent ON email_messages(sent_at DESC);

-- Email templates
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50),
    subject VARCHAR(500),
    body_template TEXT,
    variables JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Meetings (extends activities but separate for AI scheduling)
CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_id UUID REFERENCES activities(activity_id),
    title VARCHAR(255) NOT NULL,
    meeting_type VARCHAR(50),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    contact_id UUID REFERENCES contacts(contact_id),
    opportunity_id UUID REFERENCES opportunities(opportunity_id),
    location VARCHAR(255),
    video_link VARCHAR(500),
    agenda TEXT,
    notes TEXT,
    status VARCHAR(50) DEFAULT 'scheduled',
    ai_suggested BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meetings_contact ON meetings(contact_id);
CREATE INDEX IF NOT EXISTS idx_meetings_opportunity ON meetings(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_meetings_start ON meetings(start_time);
CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status);

COMMENT ON TABLE agent_logs IS 'Tracks all AI agent executions for audit and improvement';
COMMENT ON TABLE nl_queries IS 'History of natural language queries for learning';
COMMENT ON TABLE pipeline_predictions IS 'AI-generated pipeline forecasts';
COMMENT ON TABLE meetings IS 'AI-managed meeting scheduling';

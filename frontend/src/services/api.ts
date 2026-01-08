/**
 * API Service for Agentic CRM
 * Handles all communication with the Python backend
 */

import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Types
export interface Lead {
    id: string;
    contact_id: string;
    company_id: string;
    source: string;
    status: string;
    score: number;
    priority: string;
    assigned_to: string;
    estimated_value: number;
    created_at: string;
    first_name?: string;
    last_name?: string;
    company_name?: string;
}

export interface Deal {
    id: string;
    title: string;
    stage: string;
    amount: number;
    probability: number;
    expected_close_date: string;
    company_name?: string;
    contact_name?: string;
}

export interface NLQueryResponse {
    success: boolean;
    query: string;
    generated_sql: string;
    result_count: number;
    results: Record<string, unknown>[];
    summary: string;
}

export interface LeadScoreResponse {
    success: boolean;
    lead_id: string;
    score: number;
    qualification: string;
    score_breakdown: Record<string, number>;
    ai_reasoning: string;
    recommendations: string[];
    next_actions: { action: string; priority: string; deadline: string }[];
}

export interface EmailDraftResponse {
    success: boolean;
    email: {
        subject: string;
        body: string;
        to: string;
        contact_name: string;
    };
    subject_alternatives?: string[];
}

export interface PipelineForecast {
    success: boolean;
    period_days: number;
    forecast: {
        expected_revenue: {
            '30_days': number;
            '60_days': number;
            '90_days': number;
        };
        confidence: string;
    };
    pipeline_summary: {
        stages: { stage: string; count: number; total_value: number }[];
        totals: { total_deals: number; total_value: number };
    };
    recommended_actions: { priority: string; action: string; reason: string }[];
}

export interface PipelineHealth {
    success: boolean;
    overall_score: number;
    component_scores: Record<string, number>;
    interpretation: string;
}

export interface Meeting {
    id: string;
    title: string;
    meeting_type: string;
    start_time: string;
    end_time: string;
    contact_id: string;
    first_name?: string;
    last_name?: string;
    company_name?: string;
    quick_prep?: string;
}

// API Functions

// Natural Language Query
export const executeNLQuery = async (query: string, userId?: string): Promise<NLQueryResponse> => {
    const { data } = await api.post('/agent/query', { query, user_id: userId });
    return data;
};

export const getQueryExamples = async (): Promise<string[]> => {
    const { data } = await api.get('/agent/query/examples');
    return data.examples;
};

export const getQueryHistory = async (limit = 20) => {
    const { data } = await api.get('/agent/query/history', { params: { limit } });
    return data.history;
};

// Lead Scoring
export const scoreLead = async (leadId: string): Promise<LeadScoreResponse> => {
    const { data } = await api.post('/agent/score-lead', { lead_id: leadId });
    return data;
};

export const batchScoreLeads = async (limit = 50) => {
    const { data } = await api.post('/agent/score-leads/batch', null, { params: { limit } });
    return data;
};

export const routeQualifiedLeads = async () => {
    const { data } = await api.post('/agent/route-leads');
    return data;
};

// Email
export const draftEmail = async (
    contactId: string,
    emailType = 'followup',
    dealId?: string,
    customContext?: string
): Promise<EmailDraftResponse> => {
    const { data } = await api.post('/agent/draft-email', {
        contact_id: contactId,
        email_type: emailType,
        deal_id: dealId,
        custom_context: customContext,
    });
    return data;
};

export const generateEmailSequence = async (
    contactId: string,
    sequenceType = 'nurture',
    emailCount = 5
) => {
    const { data } = await api.post('/agent/email-sequence', {
        contact_id: contactId,
        sequence_type: sequenceType,
        email_count: emailCount,
    });
    return data;
};

export const summarizeEmailThread = async (contactId: string) => {
    const { data } = await api.get(`/agent/email/summarize/${contactId}`);
    return data;
};

export const getEmailAnalytics = async (days = 30) => {
    const { data } = await api.get('/agent/email/analytics', { params: { days } });
    return data;
};

// Meetings
export const scheduleMeeting = async (
    contactId: string,
    meetingType = 'discovery',
    dealId?: string,
    preferences?: Record<string, unknown>
) => {
    const { data } = await api.post('/agent/schedule', {
        contact_id: contactId,
        meeting_type: meetingType,
        deal_id: dealId,
        preferences,
    });
    return data;
};

export const getUpcomingMeetings = async (days = 7): Promise<{ meetings: Meeting[] }> => {
    const { data } = await api.get('/agent/meetings/upcoming', { params: { days } });
    return data;
};

export const rescheduleMeeting = async (meetingId: string, reason?: string) => {
    const { data } = await api.post(`/agent/meetings/${meetingId}/reschedule`, null, {
        params: { reason },
    });
    return data;
};

// Pipeline
export const getPipelineForecast = async (periodDays = 90): Promise<PipelineForecast> => {
    const { data } = await api.get('/pipeline/forecast', { params: { period_days: periodDays } });
    return data;
};

export const getAtRiskDeals = async () => {
    const { data } = await api.get('/pipeline/at-risk');
    return data;
};

export const getPipelineHealth = async (): Promise<PipelineHealth> => {
    const { data } = await api.get('/pipeline/health');
    return data;
};

// Follow-up
export const triggerFollowups = async () => {
    const { data } = await api.post('/followup/trigger');
    return data;
};

export const getFollowupAnalytics = async (days = 30) => {
    const { data } = await api.get('/followup/analytics', { params: { days } });
    return data;
};

// Health check
export const healthCheck = async () => {
    const { data } = await api.get('/health');
    return data;
};

export default api;

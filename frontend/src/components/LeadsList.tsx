import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
    Users,
    Sparkles,
    Filter,
    RefreshCw,
    ChevronRight,
    Mail,
    Calendar
} from 'lucide-react';
import { executeNLQuery, scoreLead, batchScoreLeads, routeQualifiedLeads } from '../services/api';

function LeadsList() {
    const [statusFilter, setStatusFilter] = useState('all');

    // Fetch leads using NL query
    const { data: leadsData, isLoading, refetch } = useQuery({
        queryKey: ['leads', statusFilter],
        queryFn: () => executeNLQuery(
            statusFilter === 'all'
                ? 'Show me all leads ordered by score'
                : `Show me all leads with status ${statusFilter}`
        ),
    });

    const scoreMutation = useMutation({
        mutationFn: scoreLead,
        onSuccess: () => refetch(),
    });

    const batchScoreMutation = useMutation({
        mutationFn: () => batchScoreLeads(50),
        onSuccess: () => refetch(),
    });

    const routeMutation = useMutation({
        mutationFn: routeQualifiedLeads,
        onSuccess: () => refetch(),
    });

    const leads = leadsData?.results || [];

    const getScoreColor = (score: number) => {
        if (score >= 70) return 'high';
        if (score >= 40) return 'medium';
        return 'low';
    };

    const getStatusBadge = (status: string) => {
        const badges: Record<string, string> = {
            new: 'badge-info',
            contacted: 'badge-warning',
            qualified: 'badge-success',
            unqualified: 'badge-danger',
        };
        return badges[status] || 'badge-info';
    };

    return (
        <div>
            {/* Page Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">Leads</h1>
                    <p className="page-description">AI-scored leads with intelligent prioritization</p>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                    <button
                        className="btn btn-secondary"
                        onClick={() => batchScoreMutation.mutate()}
                        disabled={batchScoreMutation.isPending}
                    >
                        <Sparkles size={16} />
                        {batchScoreMutation.isPending ? 'Scoring...' : 'Score All Leads'}
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={() => routeMutation.mutate()}
                        disabled={routeMutation.isPending}
                    >
                        <Users size={16} />
                        {routeMutation.isPending ? 'Routing...' : 'Route Qualified'}
                    </button>
                </div>
            </div>

            {/* Filters */}
            <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-lg)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                        <Filter size={16} color="var(--color-text-muted)" />
                        <span style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>Filter:</span>
                    </div>
                    {['all', 'new', 'contacted', 'qualified'].map(status => (
                        <button
                            key={status}
                            className={`btn ${statusFilter === status ? 'btn-primary' : 'btn-ghost'}`}
                            style={{ fontSize: '0.75rem', padding: 'var(--space-xs) var(--space-md)' }}
                            onClick={() => setStatusFilter(status)}
                        >
                            {status.charAt(0).toUpperCase() + status.slice(1)}
                        </button>
                    ))}
                    <button
                        className="btn btn-ghost"
                        onClick={() => refetch()}
                        style={{ marginLeft: 'auto' }}
                    >
                        <RefreshCw size={16} />
                    </button>
                </div>
            </div>

            {/* Leads Table */}
            <div className="card">
                {isLoading ? (
                    <div style={{ padding: 'var(--space-xl)', textAlign: 'center' }}>
                        <div className="skeleton" style={{ height: 40, marginBottom: 'var(--space-sm)' }} />
                        <div className="skeleton" style={{ height: 40, marginBottom: 'var(--space-sm)' }} />
                        <div className="skeleton" style={{ height: 40 }} />
                    </div>
                ) : leads.length === 0 ? (
                    <div style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                        No leads found
                    </div>
                ) : (
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Lead</th>
                                    <th>Company</th>
                                    <th>Source</th>
                                    <th>Score</th>
                                    <th>Status</th>
                                    <th>Value</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {leads.map((lead: Record<string, unknown>) => (
                                    <tr key={String(lead.id)}>
                                        <td>
                                            <div style={{ fontWeight: 500 }}>
                                                {lead.first_name || 'Unknown'} {lead.last_name || ''}
                                            </div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                                {lead.email || '-'}
                                            </div>
                                        </td>
                                        <td>{String(lead.company_name || lead.company_id || '-')}</td>
                                        <td>
                                            <span className="badge badge-info">{String(lead.source || '-')}</span>
                                        </td>
                                        <td>
                                            <div className="score-indicator">
                                                <span style={{ fontWeight: 600, minWidth: 30 }}>{lead.score || 0}</span>
                                                <div className="score-bar">
                                                    <div
                                                        className={`score-fill ${getScoreColor(Number(lead.score) || 0)}`}
                                                        style={{ width: `${lead.score || 0}%` }}
                                                    />
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <span className={`badge ${getStatusBadge(String(lead.status))}`}>
                                                {String(lead.status || 'new')}
                                            </span>
                                        </td>
                                        <td style={{ fontWeight: 500, color: 'var(--color-accent-success)' }}>
                                            ${Number(lead.estimated_value || 0).toLocaleString()}
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', gap: 'var(--space-xs)' }}>
                                                <button
                                                    className="btn btn-ghost"
                                                    style={{ padding: 'var(--space-xs)' }}
                                                    onClick={() => scoreMutation.mutate(String(lead.id))}
                                                    title="Score Lead"
                                                >
                                                    <Sparkles size={14} />
                                                </button>
                                                <button
                                                    className="btn btn-ghost"
                                                    style={{ padding: 'var(--space-xs)' }}
                                                    title="Draft Email"
                                                >
                                                    <Mail size={14} />
                                                </button>
                                                <button
                                                    className="btn btn-ghost"
                                                    style={{ padding: 'var(--space-xs)' }}
                                                    title="Schedule Meeting"
                                                >
                                                    <Calendar size={14} />
                                                </button>
                                                <button
                                                    className="btn btn-ghost"
                                                    style={{ padding: 'var(--space-xs)' }}
                                                    title="View Details"
                                                >
                                                    <ChevronRight size={14} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Batch Score Results */}
            {batchScoreMutation.data && (
                <div className="glass-card glow" style={{ marginTop: 'var(--space-lg)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                        <Sparkles size={24} color="var(--color-accent-primary)" />
                        <div>
                            <h4 style={{ fontWeight: 600 }}>Batch Scoring Complete</h4>
                            <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
                                Scored {batchScoreMutation.data.total_scored} leads •
                                {batchScoreMutation.data.qualified_leads} qualified •
                                {batchScoreMutation.data.needs_nurturing} need nurturing
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default LeadsList;

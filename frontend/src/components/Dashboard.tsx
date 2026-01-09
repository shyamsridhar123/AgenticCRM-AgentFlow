import { useQuery } from '@tanstack/react-query';
import {
    TrendingUp,
    Users,
    DollarSign,
    Calendar,
    AlertTriangle,
    Sparkles,
    ArrowUpRight,
    ArrowDownRight
} from 'lucide-react';
import { getPipelineHealth, getPipelineForecast, getUpcomingMeetings } from '../services/api';

/**
 * Formats a currency value with appropriate denomination (K, M, B)
 * - Under 1,000: shows as-is (e.g., $500)
 * - 1,000 - 999,999: shows in K (e.g., $150K)
 * - 1,000,000 - 999,999,999: shows in M (e.g., $11.5M)
 * - 1,000,000,000+: shows in B (e.g., $1.2B)
 */
function formatCurrency(value: number): string {
    if (value >= 1_000_000_000) {
        return `$${(value / 1_000_000_000).toFixed(1)}B`;
    } else if (value >= 1_000_000) {
        return `$${(value / 1_000_000).toFixed(1)}M`;
    } else if (value >= 1_000) {
        return `$${(value / 1_000).toFixed(0)}K`;
    }
    return `$${value.toFixed(0)}`;
}

function Dashboard() {
    const { data: health } = useQuery({
        queryKey: ['pipeline-health'],
        queryFn: getPipelineHealth,
    });

    const { data: forecast } = useQuery({
        queryKey: ['pipeline-forecast'],
        queryFn: () => getPipelineForecast(90),
    });

    const { data: meetings } = useQuery({
        queryKey: ['upcoming-meetings'],
        queryFn: () => getUpcomingMeetings(7),
    });

    const healthScore = health?.overall_score || 0;
    const totalPipeline = forecast?.pipeline_summary?.totals?.total_value || 0;
    const forecast30 = forecast?.forecast?.expected_revenue?.['30_days'] || 0;
    const upcomingMeetings = meetings?.meetings?.length || 0;

    return (
        <div>
            {/* Page Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">Dashboard</h1>
                    <p className="page-description">AI-powered insights for your sales pipeline</p>
                </div>
                <button className="btn btn-primary">
                    <Sparkles size={16} />
                    Run AI Analysis
                </button>
            </div>

            {/* Stats Grid */}
            <div className="grid-4" style={{ marginBottom: 'var(--space-xl)' }}>
                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">{healthScore.toFixed(0)}</div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(99, 102, 241, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <TrendingUp size={20} color="var(--color-accent-primary)" />
                        </div>
                    </div>
                    <div className="stat-label">Pipeline Health Score</div>
                    <div className="stat-change positive">
                        <ArrowUpRight size={12} />
                        +5.2% from last week
                    </div>
                </div>

                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">{formatCurrency(totalPipeline)}</div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(34, 197, 94, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <DollarSign size={20} color="var(--color-accent-success)" />
                        </div>
                    </div>
                    <div className="stat-label">Total Pipeline Value</div>
                    <div className="stat-change positive">
                        <ArrowUpRight size={12} />
                        +12.3% this month
                    </div>
                </div>

                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">{formatCurrency(forecast30)}</div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(34, 211, 238, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <Users size={20} color="var(--color-accent-secondary)" />
                        </div>
                    </div>
                    <div className="stat-label">30-Day Forecast</div>
                    <div className="stat-change negative">
                        <ArrowDownRight size={12} />
                        -2.1% vs target
                    </div>
                </div>

                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">{upcomingMeetings}</div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(245, 158, 11, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <Calendar size={20} color="var(--color-accent-warning)" />
                        </div>
                    </div>
                    <div className="stat-label">Upcoming Meetings</div>
                    <div className="stat-change positive">
                        <ArrowUpRight size={12} />
                        2 added today
                    </div>
                </div>
            </div>

            {/* Two Column Layout */}
            <div className="grid-2">
                {/* AI Insights Card */}
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">
                            <Sparkles size={16} style={{ marginRight: 'var(--space-sm)', color: 'var(--color-accent-primary)' }} />
                            AI Insights
                        </h3>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                        <InsightItem
                            type="success"
                            title="3 leads are ready for outreach"
                            description="High-scoring leads haven't been contacted in 5+ days"
                        />
                        <InsightItem
                            type="warning"
                            title="Deal velocity slowing"
                            description="Average time in qualification stage increased by 2 days"
                        />
                        <InsightItem
                            type="info"
                            title="Best time to call: 10 AM"
                            description="Based on past conversion patterns for your leads"
                        />
                    </div>
                </div>

                {/* At Risk Deals */}
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">
                            <AlertTriangle size={16} style={{ marginRight: 'var(--space-sm)', color: 'var(--color-accent-warning)' }} />
                            At-Risk Deals
                        </h3>
                        <button className="btn btn-ghost" style={{ fontSize: '0.75rem' }}>View All</button>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                        <RiskDealItem
                            title="Enterprise SaaS Deal"
                            company="TechCorp"
                            value={125000}
                            risk="Past close date"
                        />
                        <RiskDealItem
                            title="Platform License"
                            company="GlobalInd"
                            value={85000}
                            risk="No activity 14 days"
                        />
                        <RiskDealItem
                            title="Annual Contract"
                            company="StartupXYZ"
                            value={45000}
                            risk="Low engagement"
                        />
                    </div>
                </div>
            </div>

            {/* Pipeline Health Interpretation */}
            {health?.interpretation && (
                <div className="glass-card glow" style={{ marginTop: 'var(--space-xl)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                        <div style={{
                            width: 48,
                            height: 48,
                            background: 'var(--gradient-primary)',
                            borderRadius: 'var(--radius-lg)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <Sparkles size={24} color="white" />
                        </div>
                        <div>
                            <h4 style={{ fontWeight: 600, marginBottom: 'var(--space-xs)' }}>AI Analysis Summary</h4>
                            <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9375rem' }}>
                                {health.interpretation}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// Helper Components
function InsightItem({ type, title, description }: { type: 'success' | 'warning' | 'info'; title: string; description: string }) {
    const colors = {
        success: 'var(--color-accent-success)',
        warning: 'var(--color-accent-warning)',
        info: 'var(--color-accent-secondary)'
    };

    return (
        <div style={{
            padding: 'var(--space-md)',
            background: 'var(--color-bg-tertiary)',
            borderRadius: 'var(--radius-md)',
            borderLeft: `3px solid ${colors[type]}`
        }}>
            <div style={{ fontWeight: 500, marginBottom: 'var(--space-xs)' }}>{title}</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>{description}</div>
        </div>
    );
}

function RiskDealItem({ title, company, value, risk }: { title: string; company: string; value: number; risk: string }) {
    return (
        <div style={{
            padding: 'var(--space-md)',
            background: 'var(--color-bg-tertiary)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
        }}>
            <div>
                <div style={{ fontWeight: 500 }}>{title}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>{company}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
                <div style={{ fontWeight: 600, color: 'var(--color-accent-success)' }}>{formatCurrency(value)}</div>
                <span className="badge badge-warning">{risk}</span>
            </div>
        </div>
    );
}

export default Dashboard;

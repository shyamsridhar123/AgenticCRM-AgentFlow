import { useQuery } from '@tanstack/react-query';
import {
    TrendingUp,
    AlertTriangle,
    DollarSign,
    Target,
    ArrowRight,
    RefreshCw
} from 'lucide-react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell
} from 'recharts';
import { getPipelineForecast, getAtRiskDeals, getPipelineHealth } from '../services/api';

const STAGE_COLORS: Record<string, string> = {
    discovery: '#6366f1',
    qualification: '#8b5cf6',
    proposal: '#a855f7',
    negotiation: '#22d3ee',
    closed_won: '#22c55e',
    closed_lost: '#ef4444',
};

function PipelineView() {
    const { data: forecast, isLoading: forecastLoading, refetch } = useQuery({
        queryKey: ['pipeline-forecast'],
        queryFn: () => getPipelineForecast(90),
    });

    const { data: atRisk } = useQuery({
        queryKey: ['at-risk-deals'],
        queryFn: getAtRiskDeals,
    });

    const { data: health } = useQuery({
        queryKey: ['pipeline-health'],
        queryFn: getPipelineHealth,
    });

    const stages = forecast?.pipeline_summary?.stages || [];
    const recommendations = forecast?.recommended_actions || [];
    const riskDeals = atRisk?.at_risk_deals || [];

    // Prepare chart data
    const chartData = stages.map((stage: { stage: string; count: number; total_value: number }) => ({
        name: stage.stage.charAt(0).toUpperCase() + stage.stage.slice(1),
        deals: stage.count,
        value: stage.total_value / 1000, // in K
        fill: STAGE_COLORS[stage.stage] || '#6366f1',
    }));

    const pieData = stages.map((stage: { stage: string; total_value: number }) => ({
        name: stage.stage,
        value: stage.total_value,
        fill: STAGE_COLORS[stage.stage] || '#6366f1',
    }));

    return (
        <div>
            {/* Page Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">Pipeline</h1>
                    <p className="page-description">AI-powered pipeline analysis and forecasting</p>
                </div>
                <button className="btn btn-secondary" onClick={() => refetch()}>
                    <RefreshCw size={16} />
                    Refresh
                </button>
            </div>

            {/* Health Score Banner */}
            {health && (
                <div className="glass-card glow" style={{ marginBottom: 'var(--space-xl)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-lg)' }}>
                            <div style={{
                                width: 80,
                                height: 80,
                                borderRadius: '50%',
                                background: `conic-gradient(var(--color-accent-primary) ${health.overall_score * 3.6}deg, var(--color-bg-tertiary) 0deg)`,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}>
                                <div style={{
                                    width: 64,
                                    height: 64,
                                    borderRadius: '50%',
                                    background: 'var(--color-bg-secondary)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontWeight: 700,
                                    fontSize: '1.25rem'
                                }}>
                                    {health.overall_score.toFixed(0)}
                                </div>
                            </div>
                            <div>
                                <h3 style={{ fontWeight: 600, marginBottom: 'var(--space-xs)' }}>Pipeline Health Score</h3>
                                <p style={{ color: 'var(--color-text-secondary)', maxWidth: 500 }}>
                                    {health.interpretation}
                                </p>
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: 'var(--space-lg)' }}>
                            {Object.entries(health.component_scores || {}).slice(0, 3).map(([key, value]) => (
                                <div key={key} style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-accent-primary)' }}>
                                        {(value as number).toFixed(0)}
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'capitalize' }}>
                                        {key.replace('_', ' ')}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Forecast Stats */}
            <div className="grid-3" style={{ marginBottom: 'var(--space-xl)' }}>
                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-sm)' }}>
                        <Target size={20} color="var(--color-accent-primary)" />
                        <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>30-Day Forecast</span>
                    </div>
                    <div className="stat-value">
                        ${((forecast?.forecast?.expected_revenue?.['30_days'] || 0) / 1000).toFixed(0)}K
                    </div>
                </div>
                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-sm)' }}>
                        <TrendingUp size={20} color="var(--color-accent-success)" />
                        <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>60-Day Forecast</span>
                    </div>
                    <div className="stat-value">
                        ${((forecast?.forecast?.expected_revenue?.['60_days'] || 0) / 1000).toFixed(0)}K
                    </div>
                </div>
                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-sm)' }}>
                        <DollarSign size={20} color="var(--color-accent-secondary)" />
                        <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>90-Day Forecast</span>
                    </div>
                    <div className="stat-value">
                        ${((forecast?.forecast?.expected_revenue?.['90_days'] || 0) / 1000).toFixed(0)}K
                    </div>
                </div>
            </div>

            {/* Charts */}
            <div className="grid-2" style={{ marginBottom: 'var(--space-xl)' }}>
                {/* Stage Distribution Bar Chart */}
                <div className="card">
                    <h3 className="card-title" style={{ marginBottom: 'var(--space-lg)' }}>
                        Pipeline by Stage
                    </h3>
                    {forecastLoading ? (
                        <div className="skeleton" style={{ height: 250 }} />
                    ) : (
                        <ResponsiveContainer width="100%" height={250}>
                            <BarChart data={chartData}>
                                <XAxis
                                    dataKey="name"
                                    tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }}
                                    axisLine={{ stroke: 'var(--color-border)' }}
                                />
                                <YAxis
                                    tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }}
                                    axisLine={{ stroke: 'var(--color-border)' }}
                                />
                                <Tooltip
                                    contentStyle={{
                                        background: 'var(--color-bg-elevated)',
                                        border: '1px solid var(--color-border)',
                                        borderRadius: 'var(--radius-md)'
                                    }}
                                    formatter={(value: number) => [`$${value.toFixed(0)}K`, 'Value']}
                                />
                                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                                    {chartData.map((entry: { fill: string }, index: number) => (
                                        <Cell key={`cell-${index}`} fill={entry.fill} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    )}
                </div>

                {/* Value Distribution Pie Chart */}
                <div className="card">
                    <h3 className="card-title" style={{ marginBottom: 'var(--space-lg)' }}>
                        Value Distribution
                    </h3>
                    {forecastLoading ? (
                        <div className="skeleton" style={{ height: 250 }} />
                    ) : (
                        <ResponsiveContainer width="100%" height={250}>
                            <PieChart>
                                <Pie
                                    data={pieData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={100}
                                    paddingAngle={2}
                                    dataKey="value"
                                >
                                    {pieData.map((entry: { fill: string }, index: number) => (
                                        <Cell key={`cell-${index}`} fill={entry.fill} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{
                                        background: 'var(--color-bg-elevated)',
                                        border: '1px solid var(--color-border)',
                                        borderRadius: 'var(--radius-md)'
                                    }}
                                    formatter={(value: number) => [`$${(value / 1000).toFixed(0)}K`, 'Value']}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    )}
                    {/* Legend */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-md)', justifyContent: 'center' }}>
                        {stages.map((stage: { stage: string }) => (
                            <div key={stage.stage} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
                                <div style={{
                                    width: 12,
                                    height: 12,
                                    borderRadius: 2,
                                    background: STAGE_COLORS[stage.stage]
                                }} />
                                <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'capitalize' }}>
                                    {stage.stage}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Bottom Section */}
            <div className="grid-2">
                {/* At Risk Deals */}
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">
                            <AlertTriangle size={16} style={{ marginRight: 'var(--space-sm)', color: 'var(--color-accent-warning)' }} />
                            At-Risk Deals ({atRisk?.at_risk_count || 0})
                        </h3>
                    </div>
                    {riskDeals.length === 0 ? (
                        <p style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: 'var(--space-lg)' }}>
                            No at-risk deals found
                        </p>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                            {riskDeals.slice(0, 5).map((item: { deal: Record<string, unknown>; risk_factors: { risk_score: number; factors: string[] }; recommendation: string }) => (
                                <div
                                    key={String(item.deal.id)}
                                    style={{
                                        padding: 'var(--space-md)',
                                        background: 'var(--color-bg-tertiary)',
                                        borderRadius: 'var(--radius-md)',
                                        borderLeft: `3px solid var(--color-accent-warning)`
                                    }}
                                >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-xs)' }}>
                                        <span style={{ fontWeight: 500 }}>{String(item.deal.title)}</span>
                                        <span style={{ color: 'var(--color-accent-success)', fontWeight: 600 }}>
                                            ${(Number(item.deal.amount) / 1000).toFixed(0)}K
                                        </span>
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                        Risk: {item.risk_factors.factors.slice(0, 2).join(', ')}
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-accent-primary)', marginTop: 'var(--space-xs)' }}>
                                        💡 {item.recommendation}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* AI Recommendations */}
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">AI Recommendations</h3>
                    </div>
                    {recommendations.length === 0 ? (
                        <p style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: 'var(--space-lg)' }}>
                            No recommendations at this time
                        </p>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                            {recommendations.map((rec: { priority: string; action: string; reason: string }, i: number) => (
                                <div
                                    key={i}
                                    style={{
                                        padding: 'var(--space-md)',
                                        background: 'var(--color-bg-tertiary)',
                                        borderRadius: 'var(--radius-md)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 'var(--space-md)'
                                    }}
                                >
                                    <div style={{
                                        width: 32,
                                        height: 32,
                                        borderRadius: 'var(--radius-md)',
                                        background: rec.priority === 'high'
                                            ? 'rgba(239, 68, 68, 0.15)'
                                            : 'rgba(245, 158, 11, 0.15)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        flexShrink: 0
                                    }}>
                                        <ArrowRight size={16} color={rec.priority === 'high' ? 'var(--color-accent-danger)' : 'var(--color-accent-warning)'} />
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: 500, marginBottom: 'var(--space-xs)' }}>{rec.action}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{rec.reason}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default PipelineView;

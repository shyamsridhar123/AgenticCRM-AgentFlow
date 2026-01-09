import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
    Mail,
    Send,
    RefreshCw,
    Sparkles,
    Copy,
    Check,
    TrendingUp,
    Clock,
    Users,
    BarChart3
} from 'lucide-react';
import { getEmailAnalytics, draftEmail, executeNLQuery } from '../services/api';

/**
 * Formats a currency value with appropriate denomination (K, M, B)
 */
function formatNumber(value: number): string {
    if (value >= 1_000_000) {
        return `${(value / 1_000_000).toFixed(1)}M`;
    } else if (value >= 1_000) {
        return `${(value / 1_000).toFixed(0)}K`;
    }
    return value.toFixed(0);
}

function EmailsView() {
    const [selectedContact, setSelectedContact] = useState<string | null>(null);
    const [emailType, setEmailType] = useState('followup');
    const [generatedEmail, setGeneratedEmail] = useState<{
        subject: string;
        body: string;
        to: string;
        contact_name: string;
    } | null>(null);
    const [copied, setCopied] = useState(false);

    // Fetch email analytics
    const { data: analytics, isLoading: analyticsLoading } = useQuery({
        queryKey: ['email-analytics'],
        queryFn: () => getEmailAnalytics(30),
    });

    // Fetch contacts for email drafting
    const { data: contactsData } = useQuery({
        queryKey: ['contacts-for-email'],
        queryFn: () => executeNLQuery('Show me all contacts with their email addresses'),
    });

    // Draft email mutation
    const draftMutation = useMutation({
        mutationFn: ({ contactId, type }: { contactId: string; type: string }) =>
            draftEmail(contactId, type),
        onSuccess: (data) => {
            if (data.success && data.email) {
                setGeneratedEmail(data.email);
            }
        },
    });

    const contacts = contactsData?.results || [];

    const handleDraftEmail = () => {
        if (selectedContact) {
            draftMutation.mutate({ contactId: selectedContact, type: emailType });
        }
    };

    const handleCopyEmail = () => {
        if (generatedEmail) {
            const emailText = `Subject: ${generatedEmail.subject}\n\n${generatedEmail.body}`;
            navigator.clipboard.writeText(emailText);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const emailTypes = [
        { value: 'followup', label: 'Follow-up' },
        { value: 'introduction', label: 'Introduction' },
        { value: 'proposal', label: 'Proposal' },
        { value: 'check_in', label: 'Check-in' },
        { value: 'thank_you', label: 'Thank You' },
    ];

    return (
        <div>
            {/* Page Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">Emails</h1>
                    <p className="page-description">AI-powered email drafting and analytics</p>
                </div>
                <button className="btn btn-primary" onClick={handleDraftEmail} disabled={!selectedContact || draftMutation.isPending}>
                    <Sparkles size={16} />
                    {draftMutation.isPending ? 'Generating...' : 'Generate Email'}
                </button>
            </div>

            {/* Analytics Cards */}
            <div className="grid-4" style={{ marginBottom: 'var(--space-xl)' }}>
                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">{formatNumber(analytics?.emails_sent || 0)}</div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(99, 102, 241, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <Send size={20} color="var(--color-accent-primary)" />
                        </div>
                    </div>
                    <div className="stat-label">Emails Sent (30d)</div>
                </div>

                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">{analytics?.open_rate?.toFixed(1) || 0}%</div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(34, 197, 94, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <TrendingUp size={20} color="var(--color-accent-success)" />
                        </div>
                    </div>
                    <div className="stat-label">Open Rate</div>
                </div>

                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">{analytics?.reply_rate?.toFixed(1) || 0}%</div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(34, 211, 238, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <Users size={20} color="var(--color-accent-secondary)" />
                        </div>
                    </div>
                    <div className="stat-label">Reply Rate</div>
                </div>

                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">{analytics?.avg_response_time || 'N/A'}</div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(245, 158, 11, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <Clock size={20} color="var(--color-accent-warning)" />
                        </div>
                    </div>
                    <div className="stat-label">Avg Response Time</div>
                </div>
            </div>

            {/* Main Content */}
            <div className="grid-2">
                {/* Email Composer */}
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">
                            <Mail size={16} style={{ marginRight: 'var(--space-sm)', color: 'var(--color-accent-primary)' }} />
                            AI Email Composer
                        </h3>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                        {/* Contact Selector */}
                        <div>
                            <label style={{ display: 'block', marginBottom: 'var(--space-xs)', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                                Select Contact
                            </label>
                            <select
                                className="input"
                                value={selectedContact || ''}
                                onChange={(e) => setSelectedContact(e.target.value || null)}
                                style={{ width: '100%' }}
                            >
                                <option value="">Choose a contact...</option>
                                {contacts.map((contact: Record<string, unknown>) => (
                                    <option key={String(contact.id)} value={String(contact.id)}>
                                        {contact.first_name} {contact.last_name} - {contact.email}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Email Type Selector */}
                        <div>
                            <label style={{ display: 'block', marginBottom: 'var(--space-xs)', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                                Email Type
                            </label>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-xs)' }}>
                                {emailTypes.map((type) => (
                                    <button
                                        key={type.value}
                                        className={`btn ${emailType === type.value ? 'btn-primary' : 'btn-ghost'}`}
                                        style={{ fontSize: '0.75rem', padding: 'var(--space-xs) var(--space-md)' }}
                                        onClick={() => setEmailType(type.value)}
                                    >
                                        {type.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Generate Button */}
                        <button
                            className="btn btn-primary"
                            onClick={handleDraftEmail}
                            disabled={!selectedContact || draftMutation.isPending}
                            style={{ marginTop: 'var(--space-sm)' }}
                        >
                            <Sparkles size={16} />
                            {draftMutation.isPending ? 'Generating...' : 'Generate Email Draft'}
                        </button>
                    </div>
                </div>

                {/* Generated Email Preview */}
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">
                            <BarChart3 size={16} style={{ marginRight: 'var(--space-sm)', color: 'var(--color-accent-secondary)' }} />
                            Email Preview
                        </h3>
                        {generatedEmail && (
                            <button className="btn btn-ghost" onClick={handleCopyEmail}>
                                {copied ? <Check size={16} /> : <Copy size={16} />}
                                {copied ? 'Copied!' : 'Copy'}
                            </button>
                        )}
                    </div>

                    {generatedEmail ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                            <div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: 'var(--space-xs)' }}>
                                    To:
                                </div>
                                <div style={{ fontWeight: 500 }}>
                                    {generatedEmail.contact_name} &lt;{generatedEmail.to}&gt;
                                </div>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: 'var(--space-xs)' }}>
                                    Subject:
                                </div>
                                <div style={{ fontWeight: 600, color: 'var(--color-accent-primary)' }}>
                                    {generatedEmail.subject}
                                </div>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: 'var(--space-xs)' }}>
                                    Body:
                                </div>
                                <div style={{
                                    padding: 'var(--space-md)',
                                    background: 'var(--color-bg-tertiary)',
                                    borderRadius: 'var(--radius-md)',
                                    whiteSpace: 'pre-wrap',
                                    fontSize: '0.875rem',
                                    lineHeight: 1.6
                                }}>
                                    {generatedEmail.body}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div style={{
                            padding: 'var(--space-xl)',
                            textAlign: 'center',
                            color: 'var(--color-text-muted)'
                        }}>
                            <Mail size={48} style={{ opacity: 0.3, marginBottom: 'var(--space-md)' }} />
                            <p>Select a contact and generate an email to see the preview</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Error Display */}
            {draftMutation.isError && (
                <div className="card" style={{ marginTop: 'var(--space-lg)', borderColor: 'var(--color-accent-danger)' }}>
                    <div style={{ color: 'var(--color-accent-danger)' }}>
                        Error generating email: {(draftMutation.error as Error)?.message || 'Unknown error'}
                    </div>
                </div>
            )}
        </div>
    );
}

export default EmailsView;

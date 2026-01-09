import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Calendar,
    Clock,
    User,
    Building2,
    RefreshCw,
    Plus,
    Video,
    Phone,
    MapPin,
    Sparkles,
    ChevronRight,
    AlertCircle
} from 'lucide-react';
import { getUpcomingMeetings, scheduleMeeting, rescheduleMeeting, executeNLQuery } from '../services/api';

function MeetingsView() {
    const [selectedContact, setSelectedContact] = useState<string | null>(null);
    const [meetingType, setMeetingType] = useState('discovery');
    const [showScheduler, setShowScheduler] = useState(false);
    const queryClient = useQueryClient();

    // Fetch upcoming meetings
    const { data: meetingsData, isLoading, refetch } = useQuery({
        queryKey: ['upcoming-meetings', 14],
        queryFn: () => getUpcomingMeetings(14),
    });

    // Fetch contacts for scheduling
    const { data: contactsData } = useQuery({
        queryKey: ['contacts-for-meeting'],
        queryFn: () => executeNLQuery('Show me all contacts with their company'),
    });

    // Schedule meeting mutation
    const scheduleMutation = useMutation({
        mutationFn: ({ contactId, type }: { contactId: string; type: string }) =>
            scheduleMeeting(contactId, type),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['upcoming-meetings'] });
            setShowScheduler(false);
            setSelectedContact(null);
        },
    });

    // Reschedule meeting mutation
    const rescheduleMutation = useMutation({
        mutationFn: (meetingId: string) => rescheduleMeeting(meetingId, 'Scheduling conflict'),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['upcoming-meetings'] });
        },
    });

    const meetings = meetingsData?.meetings || [];
    const contacts = contactsData?.results || [];

    const meetingTypes = [
        { value: 'discovery', label: 'Discovery Call', icon: Phone },
        { value: 'demo', label: 'Product Demo', icon: Video },
        { value: 'followup', label: 'Follow-up', icon: User },
        { value: 'closing', label: 'Closing Call', icon: Building2 },
    ];

    const formatMeetingTime = (dateString: string) => {
        const date = new Date(dateString);
        return {
            date: date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }),
            time: date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
        };
    };

    const getMeetingIcon = (type: string) => {
        const icons: Record<string, React.ReactNode> = {
            discovery: <Phone size={16} />,
            demo: <Video size={16} />,
            followup: <User size={16} />,
            closing: <Building2 size={16} />,
        };
        return icons[type] || <Calendar size={16} />;
    };

    const handleScheduleMeeting = () => {
        if (selectedContact) {
            scheduleMutation.mutate({ contactId: selectedContact, type: meetingType });
        }
    };

    // Group meetings by date
    const groupedMeetings = meetings.reduce((groups: Record<string, typeof meetings>, meeting) => {
        const { date } = formatMeetingTime(String(meeting.start_time));
        if (!groups[date]) {
            groups[date] = [];
        }
        groups[date].push(meeting);
        return groups;
    }, {});

    return (
        <div>
            {/* Page Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">Meetings</h1>
                    <p className="page-description">AI-optimized scheduling with smart prep notes</p>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                    <button className="btn btn-secondary" onClick={() => refetch()}>
                        <RefreshCw size={16} />
                        Refresh
                    </button>
                    <button className="btn btn-primary" onClick={() => setShowScheduler(!showScheduler)}>
                        <Plus size={16} />
                        Schedule Meeting
                    </button>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid-4" style={{ marginBottom: 'var(--space-xl)' }}>
                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">{meetings.length}</div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(99, 102, 241, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <Calendar size={20} color="var(--color-accent-primary)" />
                        </div>
                    </div>
                    <div className="stat-label">Upcoming (14 days)</div>
                </div>

                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">
                            {meetings.filter((m) => String(m.meeting_type) === 'demo').length}
                        </div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(34, 197, 94, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <Video size={20} color="var(--color-accent-success)" />
                        </div>
                    </div>
                    <div className="stat-label">Product Demos</div>
                </div>

                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">
                            {meetings.filter((m) => String(m.meeting_type) === 'discovery').length}
                        </div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(34, 211, 238, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <Phone size={20} color="var(--color-accent-secondary)" />
                        </div>
                    </div>
                    <div className="stat-label">Discovery Calls</div>
                </div>

                <div className="stat-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div className="stat-value">
                            {meetings.filter((m) => String(m.meeting_type) === 'closing').length}
                        </div>
                        <div style={{
                            padding: 'var(--space-sm)',
                            background: 'rgba(245, 158, 11, 0.15)',
                            borderRadius: 'var(--radius-md)'
                        }}>
                            <Building2 size={20} color="var(--color-accent-warning)" />
                        </div>
                    </div>
                    <div className="stat-label">Closing Calls</div>
                </div>
            </div>

            {/* Scheduler Modal */}
            {showScheduler && (
                <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                    <div className="card-header">
                        <h3 className="card-title">
                            <Sparkles size={16} style={{ marginRight: 'var(--space-sm)', color: 'var(--color-accent-primary)' }} />
                            AI-Powered Scheduling
                        </h3>
                        <button className="btn btn-ghost" onClick={() => setShowScheduler(false)}>
                            ✕
                        </button>
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
                                        {contact.first_name} {contact.last_name} - {contact.company_name || 'No company'}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Meeting Type Selector */}
                        <div>
                            <label style={{ display: 'block', marginBottom: 'var(--space-xs)', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                                Meeting Type
                            </label>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
                                {meetingTypes.map((type) => (
                                    <button
                                        key={type.value}
                                        className={`btn ${meetingType === type.value ? 'btn-primary' : 'btn-ghost'}`}
                                        style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}
                                        onClick={() => setMeetingType(type.value)}
                                    >
                                        <type.icon size={14} />
                                        {type.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* AI will find optimal time */}
                        <div style={{
                            padding: 'var(--space-md)',
                            background: 'var(--color-bg-tertiary)',
                            borderRadius: 'var(--radius-md)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 'var(--space-sm)'
                        }}>
                            <Sparkles size={16} color="var(--color-accent-primary)" />
                            <span style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                                AI will find the optimal meeting time based on availability and engagement patterns
                            </span>
                        </div>

                        {/* Schedule Button */}
                        <button
                            className="btn btn-primary"
                            onClick={handleScheduleMeeting}
                            disabled={!selectedContact || scheduleMutation.isPending}
                        >
                            <Calendar size={16} />
                            {scheduleMutation.isPending ? 'Scheduling...' : 'Schedule with AI'}
                        </button>
                    </div>
                </div>
            )}

            {/* Meetings List */}
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">
                        <Calendar size={16} style={{ marginRight: 'var(--space-sm)', color: 'var(--color-accent-primary)' }} />
                        Upcoming Meetings
                    </h3>
                </div>

                {isLoading ? (
                    <div style={{ padding: 'var(--space-xl)', textAlign: 'center' }}>
                        <div className="skeleton" style={{ height: 80, marginBottom: 'var(--space-sm)' }} />
                        <div className="skeleton" style={{ height: 80, marginBottom: 'var(--space-sm)' }} />
                        <div className="skeleton" style={{ height: 80 }} />
                    </div>
                ) : meetings.length === 0 ? (
                    <div style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                        <Calendar size={48} style={{ opacity: 0.3, marginBottom: 'var(--space-md)' }} />
                        <p>No upcoming meetings</p>
                        <button
                            className="btn btn-primary"
                            style={{ marginTop: 'var(--space-md)' }}
                            onClick={() => setShowScheduler(true)}
                        >
                            <Plus size={16} />
                            Schedule your first meeting
                        </button>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
                        {Object.entries(groupedMeetings).map(([date, dateMeetings]) => (
                            <div key={date}>
                                <div style={{
                                    fontSize: '0.75rem',
                                    fontWeight: 600,
                                    color: 'var(--color-text-muted)',
                                    textTransform: 'uppercase',
                                    marginBottom: 'var(--space-sm)',
                                    letterSpacing: '0.05em'
                                }}>
                                    {date}
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                                    {dateMeetings.map((meeting) => {
                                        const { time } = formatMeetingTime(String(meeting.start_time));
                                        return (
                                            <div
                                                key={String(meeting.id)}
                                                style={{
                                                    padding: 'var(--space-md)',
                                                    background: 'var(--color-bg-tertiary)',
                                                    borderRadius: 'var(--radius-md)',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 'var(--space-md)'
                                                }}
                                            >
                                                {/* Time */}
                                                <div style={{
                                                    minWidth: 70,
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 'var(--space-xs)',
                                                    color: 'var(--color-accent-primary)',
                                                    fontWeight: 500
                                                }}>
                                                    <Clock size={14} />
                                                    {time}
                                                </div>

                                                {/* Meeting Type Icon */}
                                                <div style={{
                                                    padding: 'var(--space-sm)',
                                                    background: 'rgba(99, 102, 241, 0.15)',
                                                    borderRadius: 'var(--radius-md)'
                                                }}>
                                                    {getMeetingIcon(String(meeting.meeting_type))}
                                                </div>

                                                {/* Meeting Details */}
                                                <div style={{ flex: 1 }}>
                                                    <div style={{ fontWeight: 500 }}>
                                                        {meeting.title || `${meeting.meeting_type} call`}
                                                    </div>
                                                    <div style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                                                        {meeting.first_name} {meeting.last_name}
                                                        {meeting.company_name && ` • ${meeting.company_name}`}
                                                    </div>
                                                </div>

                                                {/* Quick Prep */}
                                                {meeting.quick_prep && (
                                                    <div style={{
                                                        padding: 'var(--space-xs) var(--space-sm)',
                                                        background: 'rgba(245, 158, 11, 0.15)',
                                                        borderRadius: 'var(--radius-sm)',
                                                        fontSize: '0.75rem',
                                                        color: 'var(--color-accent-warning)',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: 'var(--space-xs)'
                                                    }}>
                                                        <AlertCircle size={12} />
                                                        {meeting.quick_prep}
                                                    </div>
                                                )}

                                                {/* Actions */}
                                                <div style={{ display: 'flex', gap: 'var(--space-xs)' }}>
                                                    <button
                                                        className="btn btn-ghost"
                                                        style={{ padding: 'var(--space-xs)' }}
                                                        onClick={() => rescheduleMutation.mutate(String(meeting.id))}
                                                        title="Reschedule"
                                                    >
                                                        <RefreshCw size={14} />
                                                    </button>
                                                    <button
                                                        className="btn btn-ghost"
                                                        style={{ padding: 'var(--space-xs)' }}
                                                        title="View Details"
                                                    >
                                                        <ChevronRight size={14} />
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Error Display */}
            {(scheduleMutation.isError || rescheduleMutation.isError) && (
                <div className="card" style={{ marginTop: 'var(--space-lg)', borderColor: 'var(--color-accent-danger)' }}>
                    <div style={{ color: 'var(--color-accent-danger)' }}>
                        Error: {((scheduleMutation.error || rescheduleMutation.error) as Error)?.message || 'Unknown error'}
                    </div>
                </div>
            )}
        </div>
    );
}

export default MeetingsView;

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Send, Sparkles, User, Loader2, ChevronDown, ChevronRight, Brain, Wrench, CheckCircle, AlertCircle } from 'lucide-react';
import { executeNLQuery, getQueryExamples } from '../services/api';

// Currency formatting fields
const CURRENCY_FIELDS = ['amount', 'annual_revenue', 'expected_revenue', 'total_value', 'budget', 'actual_cost', 'revenue', 'value'];
const PERCENTAGE_FIELDS = ['probability', 'win_rate', 'conversion_rate', 'rate'];
const DATE_FIELDS = ['created_at', 'updated_at', 'close_date', 'due_date', 'start_date', 'end_date'];

// Format cell values based on column name
function formatCellValue(key: string, value: unknown): string {
    if (value === null || value === undefined) return '-';
    
    const keyLower = key.toLowerCase();
    
    // Currency formatting
    if (CURRENCY_FIELDS.some(field => keyLower.includes(field))) {
        const num = Number(value);
        if (!isNaN(num)) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(num);
        }
    }
    
    // Percentage formatting
    if (PERCENTAGE_FIELDS.some(field => keyLower.includes(field))) {
        const num = Number(value);
        if (!isNaN(num)) {
            return `${num.toFixed(0)}%`;
        }
    }
    
    // Date formatting
    if (DATE_FIELDS.some(field => keyLower.includes(field))) {
        const date = new Date(String(value));
        if (!isNaN(date.getTime())) {
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        }
    }
    
    // Boolean formatting
    if (typeof value === 'boolean') {
        return value ? 'Yes' : 'No';
    }
    
    // Number formatting (with commas)
    if (typeof value === 'number' && !keyLower.includes('id')) {
        return new Intl.NumberFormat('en-US').format(value);
    }
    
    return String(value);
}

interface ReasoningStep {
    step: number;
    type: string;
    title: string;
    content?: string;
    context?: string;
    sub_goal?: string;
    tool?: string;
    analysis?: string;
    explanation?: string;
    command?: string;
    result?: Record<string, unknown>;
    conclusion?: string;
    detailed_solution?: string;
    direct_answer?: string;
    timestamp?: string;
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    data?: Record<string, unknown>[];
    sql?: string;
    reasoning_steps?: ReasoningStep[];
    execution_time?: number;
    steps?: number;
}

function ChatInterface() {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content: "Hello! I'm your AI CRM assistant. Ask me anything about your leads, deals, or pipeline. Try something like:\n\n• \"Show me all qualified leads from this month\"\n• \"What deals are closing this quarter?\"\n• \"Find contacts from technology companies\""
        }
    ]);
    const [input, setInput] = useState('');

    const { data: examples } = useQuery({
        queryKey: ['query-examples'],
        queryFn: getQueryExamples,
    });

    const mutation = useMutation({
        mutationFn: (query: string) => executeNLQuery(query),
        onSuccess: (data) => {
            const response: Message = {
                id: Date.now().toString(),
                role: 'assistant',
                content: data.summary || data.direct_output || `Found ${data.result_count} results.`,
                data: data.results,
                sql: data.generated_sql,
                reasoning_steps: data.reasoning_steps,
                execution_time: data.execution_time,
                steps: data.steps
            };
            setMessages(prev => [...prev, response]);
        },
        onError: (error: Error) => {
            const response: Message = {
                id: Date.now().toString(),
                role: 'assistant',
                content: `Sorry, I couldn't process that query. ${error.message}`
            };
            setMessages(prev => [...prev, response]);
        }
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || mutation.isPending) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input
        };
        setMessages(prev => [...prev, userMessage]);
        mutation.mutate(input);
        setInput('');
    };

    const handleExampleClick = (example: string) => {
        setInput(example);
    };

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">AI Chat</h1>
                    <p className="page-description">Ask questions about your CRM data in natural language</p>
                </div>
            </div>

            <div className="chat-container">
                {/* Messages */}
                <div className="chat-messages">
                    {messages.map((message) => (
                        <div key={message.id} className={`chat-message ${message.role}`}>
                            <div className="chat-avatar">
                                {message.role === 'assistant' ? (
                                    <Sparkles size={18} color="white" />
                                ) : (
                                    <User size={18} color="white" />
                                )}
                            </div>
                            <div className="chat-bubble">
                                <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>

                                {/* Show results table if available */}
                                {message.data && message.data.length > 0 && (
                                    <div style={{ marginTop: 'var(--space-md)' }}>
                                        <div className="table-container" style={{ maxHeight: 300, overflow: 'auto' }}>
                                            <table>
                                                <thead>
                                                    <tr>
                                                        {Object.keys(message.data[0]).slice(0, 5).map(key => (
                                                            <th key={key}>{key}</th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {message.data.slice(0, 10).map((row, i) => (
                                                        <tr key={i}>
                                                            {Object.entries(row).slice(0, 5).map(([key, val], j) => (
                                                                <td key={j}>{formatCellValue(key, val)}</td>
                                                            ))}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>

                                        {/* Show SQL */}
                                        {message.sql && (
                                            <details style={{ marginTop: 'var(--space-sm)' }}>
                                                <summary style={{
                                                    cursor: 'pointer',
                                                    fontSize: '0.75rem',
                                                    color: 'var(--color-text-muted)'
                                                }}>
                                                    View Generated SQL
                                                </summary>
                                                <pre style={{
                                                    fontSize: '0.75rem',
                                                    padding: 'var(--space-sm)',
                                                    background: 'var(--color-bg-primary)',
                                                    borderRadius: 'var(--radius-sm)',
                                                    overflow: 'auto',
                                                    marginTop: 'var(--space-xs)'
                                                }}>
                                                    {message.sql}
                                                </pre>
                                            </details>
                                        )}

                                        {/* Show Reasoning Steps */}
                                        {message.reasoning_steps && message.reasoning_steps.length > 0 && (
                                            <ReasoningStepsView 
                                                steps={message.reasoning_steps} 
                                                executionTime={message.execution_time}
                                                stepCount={message.steps}
                                            />
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {mutation.isPending && (
                        <div className="chat-message assistant">
                            <div className="chat-avatar ai-processing">
                                <Sparkles size={18} color="white" />
                            </div>
                            <div className="chat-bubble" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                                <Loader2 size={16} className="ai-processing" style={{ animation: 'spin 1s linear infinite' }} />
                                Analyzing your query...
                            </div>
                        </div>
                    )}
                </div>

                {/* Example Queries */}
                {examples && messages.length <= 1 && (
                    <div style={{
                        padding: 'var(--space-md) var(--space-lg)',
                        borderTop: '1px solid var(--color-border)',
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: 'var(--space-sm)'
                    }}>
                        {examples.slice(0, 4).map((example, i) => (
                            <button
                                key={i}
                                className="btn btn-secondary"
                                style={{ fontSize: '0.75rem' }}
                                onClick={() => handleExampleClick(example)}
                            >
                                {example}
                            </button>
                        ))}
                    </div>
                )}

                {/* Input */}
                <form onSubmit={handleSubmit} className="chat-input-container">
                    <textarea
                        className="chat-input"
                        placeholder="Ask about your leads, deals, or pipeline..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSubmit(e);
                            }
                        }}
                        rows={1}
                    />
                    <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={!input.trim() || mutation.isPending}
                    >
                        <Send size={18} />
                    </button>
                </form>
            </div>

            <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
        </div>
    );
}

// Reasoning Steps Viewer Component
function ReasoningStepsView({ steps, executionTime, stepCount }: { 
    steps: ReasoningStep[]; 
    executionTime?: number;
    stepCount?: number;
}) {
    const [expanded, setExpanded] = useState(false);

    const getStepIcon = (type: string) => {
        switch (type) {
            case 'analysis':
                return <Brain size={14} color="var(--color-accent-primary)" />;
            case 'planning':
                return <Sparkles size={14} color="var(--color-accent-warning)" />;
            case 'command_generation':
            case 'execution':
                return <Wrench size={14} color="var(--color-accent-secondary)" />;
            case 'verification':
                return <CheckCircle size={14} color="var(--color-accent-success)" />;
            case 'final_output':
                return <Sparkles size={14} color="var(--color-accent-primary)" />;
            default:
                return <AlertCircle size={14} color="var(--color-text-muted)" />;
        }
    };

    const getStepColor = (type: string) => {
        switch (type) {
            case 'analysis': return 'rgba(99, 102, 241, 0.15)';
            case 'planning': return 'rgba(245, 158, 11, 0.15)';
            case 'command_generation':
            case 'execution': return 'rgba(34, 211, 238, 0.15)';
            case 'verification': return 'rgba(34, 197, 94, 0.15)';
            case 'final_output': return 'rgba(99, 102, 241, 0.2)';
            default: return 'var(--color-bg-tertiary)';
        }
    };

    return (
        <details 
            style={{ marginTop: 'var(--space-md)' }}
            open={expanded}
            onToggle={(e) => setExpanded((e.target as HTMLDetailsElement).open)}
        >
            <summary style={{
                cursor: 'pointer',
                fontSize: '0.75rem',
                color: 'var(--color-accent-primary)',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-xs)',
                fontWeight: 500
            }}>
                {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <Brain size={14} />
                View Reasoning ({stepCount || steps.length} steps, {executionTime?.toFixed(1) || '?'}s)
            </summary>
            
            <div style={{
                marginTop: 'var(--space-sm)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-sm)'
            }}>
                {steps.map((step, index) => (
                    <div
                        key={index}
                        style={{
                            padding: 'var(--space-sm)',
                            background: getStepColor(step.type),
                            borderRadius: 'var(--radius-sm)',
                            borderLeft: `3px solid ${step.type === 'final_output' ? 'var(--color-accent-primary)' : 'var(--color-border)'}`
                        }}
                    >
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 'var(--space-xs)',
                            marginBottom: 'var(--space-xs)'
                        }}>
                            {getStepIcon(step.type)}
                            <span style={{ fontWeight: 600, fontSize: '0.75rem' }}>
                                Step {step.step}: {step.title}
                            </span>
                        </div>
                        
                        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                            {/* Analysis step */}
                            {step.content && (
                                <div style={{ whiteSpace: 'pre-wrap', maxHeight: 100, overflow: 'auto' }}>
                                    {step.content.substring(0, 300)}{step.content.length > 300 ? '...' : ''}
                                </div>
                            )}
                            
                            {/* Planning step */}
                            {step.sub_goal && (
                                <div>
                                    <strong>Sub-goal:</strong> {step.sub_goal}
                                    {step.tool && <span style={{ marginLeft: 'var(--space-sm)', color: 'var(--color-accent-secondary)' }}>→ {step.tool}</span>}
                                </div>
                            )}
                            
                            {/* Command generation */}
                            {step.command && (
                                <div>
                                    <strong>Command:</strong>
                                    <pre style={{
                                        fontSize: '0.7rem',
                                        padding: 'var(--space-xs)',
                                        background: 'var(--color-bg-primary)',
                                        borderRadius: 'var(--radius-sm)',
                                        overflow: 'auto',
                                        maxHeight: 60,
                                        marginTop: 'var(--space-xs)'
                                    }}>
                                        {step.command}
                                    </pre>
                                </div>
                            )}
                            
                            {/* Execution result */}
                            {step.result && (
                                <div>
                                    <strong>Result:</strong> {step.result.success ? '✅ Success' : '❌ Failed'}
                                    {step.result.result_count !== undefined && ` (${step.result.result_count} records)`}
                                </div>
                            )}
                            
                            {/* Verification */}
                            {step.conclusion && (
                                <div>
                                    <strong>Conclusion:</strong> {step.conclusion === 'STOP' ? '✅ Complete' : '🔄 Continue'}
                                </div>
                            )}
                            
                            {/* Final output */}
                            {step.direct_answer && (
                                <div style={{ 
                                    whiteSpace: 'pre-wrap',
                                    marginTop: 'var(--space-xs)',
                                    padding: 'var(--space-xs)',
                                    background: 'var(--color-bg-primary)',
                                    borderRadius: 'var(--radius-sm)'
                                }}>
                                    {step.direct_answer}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </details>
    );
}

export default ChatInterface;

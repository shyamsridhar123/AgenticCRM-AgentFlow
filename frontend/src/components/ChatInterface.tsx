import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Send, Sparkles, User, Loader2 } from 'lucide-react';
import { executeNLQuery, getQueryExamples } from '../services/api';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    data?: Record<string, unknown>[];
    sql?: string;
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
                content: data.summary || `Found ${data.result_count} results.`,
                data: data.results,
                sql: data.generated_sql
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
                                                            {Object.values(row).slice(0, 5).map((val, j) => (
                                                                <td key={j}>{String(val ?? '-')}</td>
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

export default ChatInterface;

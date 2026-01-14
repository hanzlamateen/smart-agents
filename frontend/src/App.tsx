import { useState, useEffect, useRef } from 'react';
import { TaskSidebar } from './components/TaskSidebar';
import { CenterPanel } from './components/CenterPanel';
import { RightPanel } from './components/RightPanel';
import { SettingsDrawer } from './components/SettingsDrawer';
import type { ChatConfig, Session, Message, Instance } from './types';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { Toaster, toast } from 'sonner';

// Default Config (Initial State)
const INITIAL_CONFIG: ChatConfig = {
    provider: 'anthropic',
    api_key: '',
    model: '', // Loaded from backend
    system_prompt_suffix: '',
    max_tokens: 4096,
    thinking_budget: 0,
    only_n_most_recent_images: 3,
    enable_token_efficient_tools: false,
    tool_version: 'computer_use_20250124',
};

interface SessionData {
    messages: Message[];
    isStreaming: boolean;
    inputMessage: string;
    abortController: AbortController | null;
}

function App() {
    // State
    const [config, setConfig] = useState<ChatConfig>(INITIAL_CONFIG);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [sessions, setSessions] = useState<Session[]>([]);
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [hasMoreSessions, setHasMoreSessions] = useState(true);
    
    // Multi-Session State
    const [sessionStates, setSessionStates] = useState<Record<string, SessionData>>({});

    // Instance State
    const [instance, setInstance] = useState<Instance | null>(null);
    
    // Instance SSE Ref (Global because only one VNC visible at a time)
    const instanceSSERef = useRef<AbortController | null>(null);
    const SESSIONS_LIMIT = 20;

    // Derived State for Current Session
    const currentSessionState = currentSessionId ? sessionStates[currentSessionId] : null;
    const messages = currentSessionState?.messages || [];
    const isStreaming = currentSessionState?.isStreaming || false;
    const inputMessage = currentSessionState?.inputMessage || '';

    // Load sessions and settings on mount
    useEffect(() => {
        fetchSessions(true); // Initial load, reset
        fetchSettings();
    }, []);

    // Search effect
    useEffect(() => {
        const timer = setTimeout(() => {
            fetchSessions(true); 
        }, 300);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    // Session Switch Effect: Load Messages if missing, Switch Instance Monitor
    useEffect(() => {
        if (!currentSessionId) {
            setInstance(null);
            stopInstanceSSE();
            return;
        }

        // 1. Fetch messages if not in state
        if (!sessionStates[currentSessionId]) {
            // Initialize empty state immediately to prevent double fetch
            setSessionStates(prev => ({
                ...prev,
                [currentSessionId]: {
                    messages: [],
                    isStreaming: false,
                    inputMessage: '',
                    abortController: null
                }
            }));
            fetchMessages(currentSessionId);
        }

        // 2. Switch Instance Monitor (VNC)
        startInstanceSSE(currentSessionId);

        return () => stopInstanceSSE();
    }, [currentSessionId]);

    const setInputMessageForSession = (val: string) => {
        if (!currentSessionId) return;
        setSessionStates(prev => ({
            ...prev,
            [currentSessionId]: {
                ...prev[currentSessionId],
                inputMessage: val
            }
        }));
    };

    const stopInstanceSSE = () => {
        if (instanceSSERef.current) {
            instanceSSERef.current.abort();
            instanceSSERef.current = null;
        }
    };

    const startInstanceSSE = (sessionId: string) => {
        stopInstanceSSE();
        setInstance(null);

        // Proactively spawn instance
        fetch(`http://localhost:8080/sessions/${sessionId}/instance`, { method: 'POST' })
            .catch(err => console.error("Failed to trigger spawn", err));

        const ctrl = new AbortController();
        instanceSSERef.current = ctrl;

        fetchEventSource(`http://localhost:8080/sessions/${sessionId}/instance`, {
            method: 'GET',
            headers: { 'Accept': 'text/event-stream' },
            signal: ctrl.signal,
            onmessage(ev) {
                if (!ev.data) return;
                try {
                    const data = JSON.parse(ev.data);
                    if (data.error) {
                        toast.error("Instance Spawn Timeout");
                        stopInstanceSSE();
                        return;
                    }
                    setInstance(data as Instance);
                    if (data.status === 'running') {
                        stopInstanceSSE();
                    }
                } catch (e) {
                    console.error("Instance SSE Parse Error", e);
                }
            },
            onerror(err) {
                 if (ctrl.signal.aborted) return;
                 console.error("Instance SSE Error", err);
            }
        });
    };

    const fetchSettings = async () => {
        try {
            const res = await fetch('http://localhost:8080/agent-settings');
            if (res.ok) {
                const data = await res.json();
                setConfig(prev => ({ ...prev, ...data }));
            }
        } catch (e) {
            console.error("Failed to fetch settings", e);
        }
    };

    const handleUpdateConfig = async (newConfig: ChatConfig) => {
        setConfig(newConfig);
        try {
            await fetch('http://localhost:8080/agent-settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newConfig)
            });
        } catch (e) {
            console.error("Failed to save settings", e);
        }
    };

    const fetchSessions = async (reset = false) => {
        try {
            const skip = reset ? 0 : sessions.length;
            let url = `http://localhost:8080/sessions?skip=${skip}&limit=${SESSIONS_LIMIT}`;
            if (searchQuery.trim()) {
                url += `&q=${encodeURIComponent(searchQuery.trim())}`;
            }
            const res = await fetch(url);
            const data = await res.json();
            
            if (reset) {
                setSessions(data);
            } else {
                setSessions(prev => [...prev, ...data]);
            }
            setHasMoreSessions(data.length === SESSIONS_LIMIT);
        } catch (e) {
            console.error("Failed to fetch sessions", e);
        }
    };
    
    const handleLoadMoreSessions = () => {
        fetchSessions(false);
    };

    const fetchMessages = async (sessionId: string) => {
        try {
            const res = await fetch(`http://localhost:8080/sessions/${sessionId}/messages?limit=100`);
            const data = await res.json();
            
            setSessionStates(prev => ({
                ...prev,
                [sessionId]: {
                    ...(prev[sessionId] || { isStreaming: false, inputMessage: '', abortController: null }),
                    messages: data
                }
            }));
        } catch (e) {
             console.error("Failed to fetch messages", e);
        }
    };

    const createSession = async (): Promise<string | null> => {
        try {
            const res = await fetch('http://localhost:8080/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: 'New Chat' })
            });
            const session = await res.json();
            setSessions([session, ...sessions]);
            setCurrentSessionId(session.id);
            setSearchQuery('');
            return session.id;
        } catch (e) {
             console.error("Failed to create session", e);
             return null;
        }
    };

    const generateTitle = async (sessionId: string, message: string) => {
        try {
            const res = await fetch(`http://localhost:8080/sessions/${sessionId}/title`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            if (res.ok) {
                const updatedSession = await res.json();
                setSessions(prev => prev.map(s => 
                    s.id === sessionId ? { ...s, title: updatedSession.title } : s
                ));
            }
        } catch (e) {
            console.error("Failed to generate title", e);
        }
    };

    const handleSend = async (text: string) => {
        if (!config.api_key && config.provider === 'anthropic') {
            toast.error("API Key is missing. Please add it in Settings.");
            setIsSettingsOpen(true);
            return;
        }

        let activeSessionId = currentSessionId;
        if (!activeSessionId) {
            activeSessionId = await createSession();
        }
        if (!activeSessionId) { 
            console.error("No active session");
            return; 
        }
        
        // Optimistic update
        const userMsg: Message = { role: 'user', content: [{ type: 'text', text }] };
        
        // Check if first message (need current state)
        const isFirstMessage = (sessionStates[activeSessionId]?.messages || []).length === 0;

        const ctrl = new AbortController();

        setSessionStates(prev => {
            const current = prev[activeSessionId] || { messages: [], inputMessage: '', abortController: null, isStreaming: false };
            return {
                ...prev,
                [activeSessionId!]: {
                    ...current,
                    messages: [...current.messages, userMsg],
                    isStreaming: true,
                    abortController: ctrl,
                    inputMessage: '' // Clear input
                }
            };
        });

        if (isFirstMessage) {
            generateTitle(activeSessionId, text);
        }

        try {
             await fetchEventSource(`http://localhost:8080/sessions/${activeSessionId}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: activeSessionId, 
                    message: text
                }),
                signal: ctrl.signal,
                onmessage(ev) {
                    if (!ev.data) return;
                    let event;
                    try {
                        event = JSON.parse(ev.data);
                        console.debug('[SSE Event]', event.type, event);
                    } catch (e) {
                        console.error("Failed to parse event data:", ev.data, e);
                        return;
                    }
                    
                    if (event.type === 'done') {
                        setSessionStates(prev => ({
                            ...prev,
                            [activeSessionId!]: {
                                ...prev[activeSessionId!],
                                isStreaming: false,
                                abortController: null
                            }
                        }));
                        return;
                    }
                    
                    if (event.type === 'error') {
                         console.error("[SSE] Stream error", event.message);
                         toast.error(`Agent Error: ${event.message}`);
                         setSessionStates(prev => ({
                            ...prev,
                            [activeSessionId!]: {
                                ...prev[activeSessionId!],
                                isStreaming: false,
                                abortController: null
                            }
                        }));
                         return;
                    }

                    setSessionStates(prev => {
                        const current = prev[activeSessionId!];
                        if (!current) return prev; // Should not happen
                        
                        let msgs = [...current.messages];
                        
                        // 1. Tool Result
                        if (event.type === 'tool_result') {
                            msgs.push({ role: 'user', content: [event] });
                        } else {
                            // 2. Assistant Message Logic
                            let lastMsg = msgs[msgs.length - 1];
                            if (!lastMsg || lastMsg.role === 'user') {
                                const newMsg: Message = { role: 'assistant', content: [] };
                                msgs.push(newMsg);
                                lastMsg = newMsg;
                            }
                            
                            const newContent = [...(lastMsg.content as any[])];
                            
                            if (event.type === 'text') {
                                const lastBlock = newContent[newContent.length - 1];
                                if (lastBlock && lastBlock.type === 'text') {
                                    lastBlock.text += event.content;
                                } else {
                                    newContent.push({ type: 'text', text: event.content });
                                }
                            } else if (event.type === 'thinking') {
                                 const lastBlock = newContent[newContent.length - 1];
                                if (lastBlock && lastBlock.type === 'thinking') {
                                    lastBlock.thinking += event.content;
                                } else {
                                    newContent.push({ type: 'thinking', thinking: event.content });
                                }
                            } else if (event.type === 'tool_use') {
                                newContent.push(event); 
                            }
                            
                            msgs[msgs.length - 1] = { ...lastMsg, content: newContent };
                        }

                        return {
                            ...prev,
                            [activeSessionId!]: {
                                ...current,
                                messages: msgs
                            }
                        };
                    });
                },
                onerror(err) {
                    console.error("EventSource failed", err);
                     // If we switched sessions, the abort controller in state might be old? No.
                     // But if aborted, don't toast error.
                    if (!ctrl.signal.aborted) {
                        setSessionStates(prev => ({
                            ...prev,
                            [activeSessionId!]: {
                                ...prev[activeSessionId!],
                                isStreaming: false,
                                abortController: null
                            }
                        }));
                        throw err;
                    }
                }
            });
        } catch (e) {
            console.error("Send failed", e);
             setSessionStates(prev => ({
                ...prev,
                [activeSessionId!]: {
                    ...prev[activeSessionId!],
                    isStreaming: false,
                    abortController: null
                }
            }));
        }
    };


    const handleStop = () => {
        if (!currentSessionId) return;
        const state = sessionStates[currentSessionId];
        if (state && state.abortController) {
            state.abortController.abort();
             setSessionStates(prev => ({
                ...prev,
                [currentSessionId]: {
                    ...state,
                    isStreaming: false,
                    abortController: null
                }
            }));
        }
    };

    return (
        <div className="flex h-screen bg-[#F8F9FA] p-4 gap-4 overflow-hidden relative">
            <Toaster richColors position="top-center" />
            <TaskSidebar 
                sessions={sessions}
                currentSessionId={currentSessionId}
                onSelectSession={(id) => setCurrentSessionId(id)}
                onCreateSession={() => createSession()}
                searchQuery={searchQuery}
                onSearch={setSearchQuery}
                onLoadMore={handleLoadMoreSessions}
                hasMore={hasMoreSessions}
            />

            <CenterPanel 
                vncPort={instance?.vnc_port}
                status={currentSessionId ? (instance?.status || 'pending') : 'idle'}
            />

            <RightPanel 
                messages={messages}
                inputMessage={inputMessage}
                setInputMessage={setInputMessageForSession}
                handleSendMessage={() => handleSend(inputMessage)}
                isStreaming={isStreaming}
                onStop={handleStop}
                onOpenSettings={() => setIsSettingsOpen(true)}
            />

            <SettingsDrawer 
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                config={config}
                setConfig={handleUpdateConfig}
            />
        </div>
    );
}

export default App;

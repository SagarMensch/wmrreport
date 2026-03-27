'use client';
import { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from '@/i18n/routing';
import VoiceChatInput from '@/components/VoiceChatInput';
import { analyzeColumns } from '@/components/ResultsChart';
import dynamic from 'next/dynamic';

const DrillCoreLoop = dynamic(() => import('@/components/DrillCoreLoop'), { ssr: false });
const ResultsChart = dynamic(() => import('@/components/ResultsChart'), { ssr: false });
const IntelligenceMatrix = dynamic(() => import('@/components/IntelligenceMatrix'), { ssr: false });
const DecisionStudio = dynamic(() => import('@/components/DecisionStudio'), { ssr: false });
const PredictiveStudio = dynamic(() => import('@/components/PredictiveStudio'), { ssr: false });

// ── Hermes Refined Icons ─────────────────────────────────────────────────
const IconOperations = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="4" y="4" width="6" height="6" rx="0.5" stroke="currentColor" strokeWidth="0.75"/>
    <rect x="14" y="4" width="6" height="6" rx="0.5" stroke="currentColor" strokeWidth="0.75"/>
    <rect x="4" y="14" width="6" height="6" rx="0.5" stroke="currentColor" strokeWidth="0.75"/>
    <rect x="14" y="14" width="6" height="6" rx="0.5" stroke="currentColor" strokeWidth="0.75"/>
  </svg>
);

const IconGraph = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="0.75"/>
    <circle cx="5" cy="7" r="2" stroke="currentColor" strokeWidth="0.75"/>
    <circle cx="19" cy="7" r="2" stroke="currentColor" strokeWidth="0.75"/>
    <circle cx="5" cy="17" r="2" stroke="currentColor" strokeWidth="0.75"/>
    <circle cx="19" cy="17" r="2" stroke="currentColor" strokeWidth="0.75"/>
    <line x1="9.5" y1="10.5" x2="6.5" y2="8.5" stroke="currentColor" strokeWidth="0.5"/>
    <line x1="14.5" y1="10.5" x2="17.5" y2="8.5" stroke="currentColor" strokeWidth="0.5"/>
    <line x1="9.5" y1="13.5" x2="6.5" y2="15.5" stroke="currentColor" strokeWidth="0.5"/>
    <line x1="14.5" y1="13.5" x2="17.5" y2="15.5" stroke="currentColor" strokeWidth="0.5"/>
  </svg>
);

const IconPredictive = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M4 18L9 13L13 16L20 7" stroke="currentColor" strokeWidth="0.75" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M17 7H21V11" stroke="currentColor" strokeWidth="0.75" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconForecasting = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="6" stroke="currentColor" strokeWidth="0.75"/>
    <path d="M12 2V4M12 20V22M2 12H4M20 12H22M4.92893 4.92893L6.34315 6.34315M17.6569 17.6569L19.0711 19.0711M4.92893 19.0711L6.34315 17.6569M17.6569 6.34315L19.0711 4.92893" stroke="currentColor" strokeWidth="0.75" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconChat = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M21 11.5C21 16.75 16.75 21 11.5 21C9.8 21 8.2 20.5 6.8 19.7L3 21L4.3 17.1C3.5 15.7 3 14.1 3 12.5C3 7.25 7.25 3 12.5 3C17.75 3 22 7.25 22 12.5V11.5Z" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconCheck = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20 6L9 17L4 12" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconAccuracy = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" fill="currentColor" fillOpacity="0.1" stroke="currentColor" strokeWidth="1.5"/>
    <circle cx="12" cy="12" r="6" stroke="currentColor" strokeWidth="1"/>
    <circle cx="12" cy="12" r="2" fill="currentColor"/>
  </svg>
);

const IconAtRisk = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" fill="currentColor" fillOpacity="0.1" stroke="currentColor" strokeWidth="1.5"/>
    <path d="M12 8V12M12 16H12.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

const IconCritical = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M10.29 3.86L1.82 18A2 2 0 003.54 21H20.46A2 2 0 0022.18 18L13.71 3.86A2 2 0 0010.29 3.86Z" fill="currentColor" fillOpacity="0.1" stroke="currentColor" strokeWidth="1.5"/>
    <path d="M12 9V13M12 17H12.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

const IconArrowLeft = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M19 12H5M12 19L5 12L12 5"/>
  </svg>
);

const IconCopy = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="9" y="9" width="13" height="13" rx="2"/>
    <path d="M5 15H4V4H15V5"/>
  </svg>
);


// ── Types ───────────────────────────────────────────────────────────────────
interface QueryResult {
  question: string;
  sql_query: string;
  chart_type: string;
  reasoning: string;
  is_safe: boolean;
  columns: string[];
  rows: any[][];
  total_rows: number;
  execution_time_ms: number;
  error?: string;
  response_type?: 'text' | 'chart' | 'clarification';
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  type?: 'text' | 'chart' | 'clarification';
  chartData?: QueryResult;
  timestamp?: string;
}

type TabState = 'operations' | 'graph' | 'predictive' | 'forecasting';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabState>('operations');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [apiError, setApiError] = useState('');
  const [sqlCopied, setSqlCopied] = useState(false);
  const [viewMode, setViewMode] = useState<'preview' | 'ssms' | 'code'>('preview');
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [expandedMsgs, setExpandedMsgs] = useState<Set<string>>(new Set());
  
  // Persistent Session ID (localStorage)
  const [sessionId, setSessionId] = useState<string>('');
  const [pastSessions, setPastSessions] = useState<{session_id: string; title: string; message_count: number}[]>([]);

  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const loadSession = (sid: string) => {
    localStorage.setItem('bashira_session_id', sid);
    setSessionId(sid);
    setMessages([]);
    setResult(null);
    setExpandedMsgs(new Set());
    fetch(`/api/history?session_id=${sid}`)
      .then(res => res.json())
      .then(data => {
        if (data?.history?.length) {
          setMessages(data.history);
          const lastChart = data.history.slice().reverse().find((m: ChatMessage) => m.type === 'chart' && m.chartData);
          if (lastChart) setResult(lastChart.chartData);
        }
      })
      .catch(console.error);
  };

  const refreshSessions = () => {
    fetch('/api/history')
      .then(res => res.json())
      .then(data => { if (data?.sessions) setPastSessions(data.sessions); })
      .catch(console.error);
  };

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('bashira_session_id');
      const sid = stored || `sess_${Math.random().toString(36).substring(2, 10)}`;
      if (!stored) localStorage.setItem('bashira_session_id', sid);
      setSessionId(sid);
      
      // Load current session history
      fetch(`/api/history?session_id=${sid}`)
        .then(res => res.json())
        .then(data => {
          if (data?.history?.length) {
            setMessages(data.history);
            const lastChart = data.history.slice().reverse().find((m: ChatMessage) => m.type === 'chart' && m.chartData);
            if (lastChart) setResult(lastChart.chartData);
          } else if (!stored) {
            // New session with no history — try to recover latest existing session
            fetch('/api/history')
              .then(r => r.json())
              .then(d => {
                if (d?.sessions?.length) {
                  const latest = d.sessions[0];
                  loadSession(latest.session_id);
                }
              })
              .catch(console.error);
          }
        })
        .catch(console.error);

      // Fetch past sessions list
      refreshSessions();
    }
  }, []);

  useEffect(() => {
    // Auto-scroll to bottom of chat
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  }, [messages, isLoading]);

  const resetToStart = () => {
    // Just clear the UI — keep the same session so history persists on refresh
    setMessages([]);
    setResult(null);
    setApiError('');
    setExpandedMsgs(new Set());
  };

  const newConversation = () => {
    // Truly start a new conversation with a new session ID
    setMessages([]);
    setResult(null);
    setApiError('');
    setExpandedMsgs(new Set());
    localStorage.removeItem('bashira_session_id');
    const newSid = `sess_${Math.random().toString(36).substring(2, 10)}`;
    localStorage.setItem('bashira_session_id', newSid);
    setSessionId(newSid);
  };

  const handleQuery = async (queryText: string) => {
    setActiveTab('operations');
    setIsLoading(true);
    setApiError('');
    setSqlCopied(false);

    const userMsg: ChatMessage = {
      id: Math.random().toString(36).substring(7),
      role: 'user',
      content: queryText
    };
    
    setMessages(prev => [...prev, userMsg]);

    try {
      await fetch('/api/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, role: 'user', content: queryText }),
      });
    } catch (e) {
      console.error('Failed to save user history', e);
    }

    try {
      // Send last 10 messages as context for follow-up understanding
      const recentHistory = messages.slice(-10).map(m => ({ role: m.role, content: m.content }));
      
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: queryText, session_id: sessionId, chat_history: recentHistory }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || err.error || `HTTP ${res.status}`);
      }

      const data: QueryResult = await res.json();
      
      const aiMsg: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        role: 'assistant',
        content: data.reasoning || data.error || 'Response complete.',
        type: data.response_type || 'chart',
        chartData: (data.response_type === 'chart') ? data : undefined
      };
      
      setMessages(prev => [...prev, aiMsg]);
      
      try {
        await fetch('/api/history', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            session_id: sessionId, 
            role: 'assistant', 
            content: aiMsg.content,
            type: aiMsg.type,
            chartData: aiMsg.chartData
          }),
        });
      } catch (e) {}

      // Update right pane only if it generated a chart successfully and there are columns
      if (aiMsg.type === 'chart' && aiMsg.chartData && aiMsg.chartData.columns?.length > 0) {
        setResult(aiMsg.chartData);
        
        if (data.sql_query) {
          const tableMatch = data.sql_query.match(/FROM\s+\[?(\w+)\]?/i);
          const whereMatch = data.sql_query.match(/WHERE\s+(\w+)/i);
          setQueryContext({
            table: tableMatch ? tableMatch[1] : undefined,
            column: whereMatch ? whereMatch[1] : undefined,
          });
        }
      } else if (aiMsg.type === 'chart' && (!aiMsg.chartData || !aiMsg.chartData.columns || aiMsg.chartData.columns.length === 0)) {
        // Fallback to text mode if it claimed chart but returned zero data
        aiMsg.type = 'text';
      }

      if (data.reasoning && !data.error) {
        fetchTTS(data.reasoning);
      }
    } catch (err: any) {
      setApiError(err.message || 'Connection failed');
    } finally {
      setIsLoading(false);
      refreshSessions();
    }
  };

  const fetchTTS = async (text: string) => {
    try {
      const TTS_SUMMARY = "Analysis complete. " + text.split(".")[0] + ".";
      const res = await fetch('/api/voice/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: TTS_SUMMARY }),
      });
      if (res.ok) {
        const blob = await res.blob();
        if (blob.size > 0) {
          const url = URL.createObjectURL(blob);
          if (audioPlayerRef.current) {
            audioPlayerRef.current.src = url;
            audioPlayerRef.current.play().catch(e => {
              // Silently ignore audio play errors - not critical
            });
          }
        }
      }
    } catch(err) {
      // Silently ignore TTS errors
    }
  };

  const copySql = () => {
    if (result?.sql_query) {
      navigator.clipboard.writeText(result.sql_query);
      setSqlCopied(true);
      setTimeout(() => setSqlCopied(false), 2000);
    }
  };

  // Track previous query context for intelligent drill down
  const [queryContext, setQueryContext] = useState<{table?: string; column?: string; filters?: string}>({});
  // Chart type override
  const [chartTypeOverride, setChartTypeOverride] = useState<string | null>(null);
  
  // Dynamic chart type selector — only show types that make sense for current data
  const suitableChartTypes = useMemo(() => {
    if (!result?.columns?.length || !result?.rows?.length) return ['data_table'];
    const profile = analyzeColumns(result.columns, result.rows);
    return profile.suitableChartTypes;
  }, [result?.columns, result?.rows]);
  
  const handleDrillDown = (value: string) => {
    // Bloomberg-level contextual drill-down: build an intelligent follow-up query
    let drillQuery = "";
    
    // Extract context from previous SQL
    const sql = result?.sql_query || '';
    const tableMatch = sql.match(/FROM\s+\[?(\w+)\]?/i);
    const tableName = tableMatch ? tableMatch[1] : 'WellMonitoringReport_Latest';
    const whereMatch = sql.match(/WHERE\s+(.+?)(?:\s+GROUP|\s+ORDER|$)/i);
    const existingFilter = whereMatch ? whereMatch[1].trim() : '';
    
    // Detect what kind of value was clicked
    const isNumeric = !isNaN(parseFloat(value)) && isFinite(parseFloat(value));
    const isPercentage = String(value).includes('%');
    
    // Check what columns we have for context
    const cols = result?.columns || [];
    const hasProgress = cols.some(c => /progress|pct|percent/i.test(c));
    const hasCluster = cols.some(c => /cluster/i.test(c));
    const hasRig = cols.some(c => /rig/i.test(c));
    const hasWellName = cols.some(c => /well_name/i.test(c));
    
    if (queryContext.table && queryContext.column) {
      // Direct filter drill-down
      drillQuery = `Show me all details for ${queryContext.column} = "${value}" from ${queryContext.table}`;
    } else if (isPercentage || (isNumeric && hasProgress)) {
      // KPI drill-down: user clicked a metric → break it down
      drillQuery = `Break down the ${value} figure by ${hasCluster ? 'cluster and ' : ''}${hasRig ? 'rig' : 'well type'} showing individual well progress`;
    } else if (hasWellName && !isNumeric) {
      // Clicked a well name → show full well profile
      drillQuery = `Show me complete details for well "${value}" including progress, rig, cluster, dates, and status`;
    } else if (isNumeric && !isPercentage) {
      // Clicked a numeric ID or count → show underlying data
      drillQuery = `Show all records where ${cols[0] || 'the primary key'} = ${value} with all available columns`;
    } else {
      // Clicked a categorical value (cluster name, rig, type, etc.)
      drillQuery = `Show me all wells where ${value} with their progress, status, and risk classification`;
    }
    
    setChartTypeOverride(null); // Reset chart type for fresh analysis
    handleQuery(drillQuery);
  };

  // ── RENDER TAB SYSTEM ──

  const renderOperationsTab = () => {
    if (messages.length === 0 && !isLoading) {
      // STATE A: THE MINIMALIST NLP START SCREEN
      // Like Google AI Studio: pure, centralized input, no fake data.
      return (
        <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-[#FFFFFF] relative isolate">

          {/* Central Workspace Definition */}
          <div className="flex flex-col items-center max-w-2xl w-full z-10 -mt-20">
             
             {/* Header */}
             <div className="flex items-center gap-4 mb-4">
                <IconOperations />
             </div>
             <h1 className="text-[#1A1A1A] text-[30px] tracking-tight mb-2" style={{ fontFamily: '"Figtree", sans-serif', fontWeight: 500 }}>
                Synthesize structural intelligence
             </h1>
             <p className="text-[#4A4A4A] text-[14px] mb-12 font-medium">
                Execute natural language queries to generate actionable visualizations.
             </p>

             {/* Main Central NLP Input */}
             <div className="w-full">
                <VoiceChatInput onSendQuery={handleQuery} isLoading={isLoading} />
             </div>

             {/* Nimr Quick Macro Suggestions */}
             <div className="flex flex-wrap justify-center gap-3 mt-8 max-w-[800px]">
                <button onClick={() => handleQuery('What is the average overall progress for all Nimr wells this week?')} className="px-5 py-2.5 rounded-full text-[#2A2A2A] text-[12px] font-medium transition-all hover:bg-[#1A1A1A] hover:text-[#FFFFFF] flex items-center gap-2" style={{ border: '1px solid rgba(0,0,0,0.12)' }}>
                   <IconOperations /> Nimr Average Progress
                </button>
                <button onClick={() => handleQuery('How many Nimr wells are fully complete (100% progress)?')} className="px-5 py-2.5 rounded-full text-[#2A2A2A] text-[12px] font-medium transition-all hover:bg-[#1A1A1A] hover:text-[#FFFFFF] flex items-center gap-2" style={{ border: '1px solid rgba(0,0,0,0.12)' }}>
                   <IconCheck /> Fully Complete Nimr Wells
                </button>
                <button onClick={() => handleQuery('Which rig has the highest average well progress across all Nimr wells?')} className="px-5 py-2.5 rounded-full text-[#2A2A2A] text-[12px] font-medium transition-all hover:bg-[#1A1A1A] hover:text-[#FFFFFF] flex items-center gap-2" style={{ border: '1px solid rgba(0,0,0,0.12)' }}>
                   <IconAccuracy /> Top Nimr Rig Performance
                </button>
                <button onClick={() => handleQuery('Which wells have made zero progress for two consecutive weeks?')} className="px-5 py-2.5 rounded-full text-[#2A2A2A] text-[12px] font-medium transition-all hover:bg-[#1A1A1A] hover:text-[#FFFFFF] flex items-center gap-2" style={{ border: '1px solid rgba(0,0,0,0.12)' }}>
                   <IconAtRisk /> Stalled Zero-Progress Wells
                </button>
                <button onClick={() => handleQuery('Which Nimr wells have an expected rig-off date within the next 30 days but are below 60% progress?')} className="px-5 py-2.5 rounded-full text-[#2A2A2A] text-[12px] font-medium transition-all hover:bg-[#1A1A1A] hover:text-[#FFFFFF] flex items-center gap-2" style={{ border: '1px solid rgba(0,0,0,0.12)' }}>
                   <IconCritical /> At-Risk Nimr Completions
                </button>
             </div>
             
          </div>
        </div>
      );
    }

    // STATE B: Execution Split View (Side-by-side processing)
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="w-full h-full flex overflow-hidden bg-[#FAFAFA]"
      >
        {/* Left Pane: Chat & Reasoning (~35%) */}
        <div className="w-full lg:w-[400px] xl:w-[450px] h-full flex flex-col border-r border-[#E5E5E5] bg-[#FFFFFF] shrink-0">
          
          {/* Top Bar with 'Back' */}
          <div className="h-[60px] flex items-center px-4 border-b border-[#E5E5E5]">
             <button onClick={resetToStart} className="flex items-center gap-2 px-3 py-1.5 rounded-full hover:bg-[#F5F5F5] text-[#525252] hover:text-[#0A0A0A] transition-colors">
                <IconArrowLeft />
                <span className="text-xs font-medium">Back to start</span>
             </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6" id="chat-container">
            {messages.map((msg, idx) => (
              <div key={msg.id || idx} className="flex gap-3">
                {msg.role === 'user' ? (
                  <>
                    <div className="w-8 h-8 rounded-full bg-[#1A1A1A] text-[#FFFFFF] flex items-center justify-center shrink-0">
                      <span className="text-[12px] font-medium">U</span>
                    </div>
                    <div className="px-5 py-3 rounded-[20px] rounded-tl-sm text-[#0A0A0A] text-[15px] leading-relaxed max-w-[85%] font-medium" style={{ background: '#F5F5F5', border: '1px solid rgba(0,0,0,0.06)' }}>
                      {msg.content}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0" style={{ background: '#FFEDD5', border: '1px solid #FED7AA' }}>
                      <span className="text-[#E87722] text-[12px] font-bold">B</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div 
                        className={`p-4 rounded-[20px] rounded-tl-sm text-[14px] leading-relaxed w-full transition-all duration-300 ${
                           msg.type === 'clarification' 
                             ? 'bg-[#FFFBEB] border-[#FEF3C7] text-[#92400E]' 
                             : msg.type === 'chart' && result?.sql_query === msg.chartData?.sql_query 
                               ? 'bg-[#FAFAFA] text-[#1A1A1A] cursor-pointer shadow-sm' 
                               : 'bg-[#FFFFFF] text-[#374151] cursor-pointer hover:bg-[#FAFAFA]'
                        }`}
                        style={{ 
                          border: msg.type === 'clarification' 
                            ? '1px solid #FEF3C7'
                            : msg.type === 'chart' && result?.sql_query === msg.chartData?.sql_query
                              ? '1.5px solid #E87722'
                              : '1px solid rgba(0,0,0,0.08)'
                        }}
                        onClick={() => { if(msg.type === 'chart' && msg.chartData && msg.chartData.columns?.length > 0) setResult(msg.chartData); }}
                      >
                        {/* Collapsible reasoning toggle */}
                        {(() => {
                          const cleanText = msg.content
                            .replace(/\\n/g, '\n')
                            .replace(/\*\*/g, '')
                            .replace(/\*/g, '')
                            .replace(/`([^`]+)`/g, '$1')
                            .replace(/#{1,3}\s/g, '');
                          const lines = cleanText.split('\n').filter(l => l.trim());
                          const firstLine = lines[0] || '';
                          const hasMore = lines.length > 1;
                          const isExpanded = expandedMsgs.has(msg.id);

                          return (
                            <>
                              {/* Summary line + toggle */}
                              <div 
                                className="flex items-start gap-2 cursor-pointer select-none"
                                onClick={(e) => {
                                  if (hasMore) {
                                    e.stopPropagation();
                                    setExpandedMsgs(prev => {
                                      const next = new Set(prev);
                                      if (next.has(msg.id)) next.delete(msg.id);
                                      else next.add(msg.id);
                                      return next;
                                    });
                                  }
                                }}
                              >
                                {hasMore && (
                                  <svg 
                                    width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                                    className={`shrink-0 mt-0.5 transition-transform duration-200 ${isExpanded ? 'rotate-90' : 'rotate-0'}`}
                                  >
                                    <polyline points="9 18 15 12 9 6" />
                                  </svg>
                                )}
                                <span className="text-[14px] text-[#374151]" style={{ fontFamily: '"Figtree", sans-serif', lineHeight: '1.7' }}>
                                  {firstLine}
                                </span>
                              </div>

                              {/* Expanded reasoning body */}
                              {isExpanded && hasMore && (
                                <div className="space-y-2.5 text-[14px] mt-3 pl-6 border-l-2 border-[#F0F0F0]" style={{ fontFamily: '"Figtree", sans-serif', lineHeight: '1.7' }}>
                                  {lines.slice(1).map((para, pIdx) => {
                                    const trimmed = para.trim();
                                    if (!trimmed) return null;
                                    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
                                    if (numMatch) {
                                      return (
                                        <div key={pIdx} className="flex gap-3 items-start">
                                          <span className="shrink-0 w-5 h-5 rounded-full bg-[#F5F5F5] flex items-center justify-center text-[11px] font-semibold text-[#525252] mt-0.5">{numMatch[1]}</span>
                                          <span className="text-[#374151]">{numMatch[2]}</span>
                                        </div>
                                      );
                                    }
                                    if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
                                      return (
                                        <div key={pIdx} className="flex gap-2.5 items-start pl-1">
                                          <span className="shrink-0 w-1 h-1 rounded-full bg-[#999] mt-2.5" />
                                          <span className="text-[#374151]">{trimmed.replace(/^[-•]\s+/, '')}</span>
                                        </div>
                                      );
                                    }
                                    return <div key={pIdx} className="text-[#374151]">{trimmed}</div>;
                                  })}
                                </div>
                              )}
                            </>
                          );
                        })()}
                        
                        {msg.type === 'chart' && msg.chartData && msg.chartData.columns?.length > 0 && (
                          <div className="mt-4 flex items-center justify-between opacity-80 border-t border-black/5 pt-3">
                             <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wide">
                                <IconGraph /> 
                                {result?.sql_query === msg.chartData.sql_query ? "Currently Viewing Visual" : "Click to View Visual"}
                             </div>
                             {result?.sql_query === msg.chartData.sql_query && (
                               <span className="w-2 h-2 rounded-full bg-[#E87722] animate-pulse"></span>
                             )}
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))}
            
            {isLoading && (
              <div className="flex gap-3 mt-4">
                <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0" style={{ background: '#FFEDD5', border: '1px solid #FED7AA' }}>
                  <span className="text-[#E87722] text-[12px] font-bold">B</span>
                </div>
                <div className="flex items-center gap-3 bg-[#FFFFFF] border border-[#E5E5E5] rounded-[20px] rounded-tl-sm p-4 text-[#525252]">
                  <span className="animate-spin text-[#E87722]">
                     <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                     </svg>
                  </span>
                  <p className="text-[14px] font-medium tracking-wide">Synthesizing intelligence...</p>
                </div>
              </div>
            )}
            
            {apiError && (
              <div className="mt-4 text-[#DC2626] text-[13px] bg-red-50 p-4 rounded-[20px] rounded-tl-sm border border-red-200 shadow-sm font-medium">
                {apiError}
              </div>
            )}
            
            {/* Invisible anchor for scrolling down automatically */}
            <div id="scroll-anchor" className="h-4"></div>
          </div>

          {/* Persistent Input at bottom of Left Pane */}
          <div className="p-4 bg-[#FFFFFF] border-t border-[#E5E5E5]">
             <VoiceChatInput onSendQuery={handleQuery} isLoading={isLoading} />
          </div>
        </div>

        {/* Right Pane: Dynamic Preview */}
        <div className="flex-1 h-full flex flex-col bg-[#FAFAFA] relative overflow-hidden">
          
          {/* Top Bar - Clean White */}
           <div className="h-[60px] flex items-center justify-between px-6 border-b border-[#E5E5E5] bg-[#FFFFFF]">
              <div className="flex gap-2">
                 <button 
                   onClick={() => setViewMode('preview')}
                   className={`px-4 py-1.5 rounded-full text-[13px] font-medium flex items-center gap-2 transition-colors ${viewMode === 'preview' ? 'bg-[#0A0A0A] text-[#FFFFFF]' : 'hover:bg-[#F5F5F5] text-[#525252]'}`}>
                    {viewMode === 'preview' && <span className="w-1.5 h-1.5 rounded-full bg-[#E87722]" />} Preview
                 </button>
                 <button 
                   onClick={() => setViewMode('ssms')}
                   className={`px-4 py-1.5 rounded-full text-[13px] font-medium flex items-center gap-2 transition-colors ${viewMode === 'ssms' ? 'bg-[#0A0A0A] text-[#FFFFFF]' : 'hover:bg-[#F5F5F5] text-[#525252]'}`}>
                    {viewMode === 'ssms' && <span className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />} SSMS
                 </button>
                 <button 
                   onClick={() => setViewMode('code')}
                   className={`px-4 py-1.5 rounded-full text-[13px] font-medium transition-colors ${viewMode === 'code' ? 'bg-[#0A0A0A] text-[#FFFFFF]' : 'hover:bg-[#F5F5F5] text-[#525252]'}`}>
                    Code
                 </button>
              </div>
             
             {result && (
               <button onClick={copySql} className="flex items-center gap-2 text-[#525252] hover:bg-[#F5F5F5] px-3 py-1.5 rounded-full transition-colors text-[13px]">
                 {sqlCopied ? <IconCheck /> : <IconCopy />}
                 {sqlCopied ? 'Copied' : 'Copy SQL'}
               </button>
             )}
          </div>

           <div className="flex-1 overflow-y-auto relative">
             {isLoading ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                   <div className="w-12 h-12 border-t-2 border-[#E87722] border-l-2 border-transparent rounded-full animate-spin mb-4" />
                   <span className="text-[#525252] text-sm">Generating visualization...</span>
                </div>
             ) : result ? (
                 <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col h-full bg-[#FAFAFA]">
                    {/* Chart Type Selector */}
                    <div className="flex items-center gap-2 px-6 py-3 border-b border-[#E5E5E5] bg-[#FFFFFF]">
                       <span className="text-[11px] uppercase tracking-wider text-[#737373] font-medium">Chart:</span>
                        {suitableChartTypes.map(ct => (
                          <button
                            key={ct}
                            onClick={() => setChartTypeOverride(ct)}
                            className={`px-3 py-1 text-[11px] rounded-md transition-colors ${
                            (chartTypeOverride || result.chart_type) === ct 
                              ? 'bg-[#0A0A0A] text-[#FFFFFF]' 
                              : 'bg-[#F5F5F5] text-[#525252] hover:bg-[#E5E5E5]'
                           }`}
                          >
                           {ct.replace(/_/g, ' ').toUpperCase()}
                         </button>
                       ))}
                   </div>
                   {viewMode === 'preview' ? (
                      <div className="w-full flex-1 p-8 lg:p-12 min-h-[500px]">
                         <ResultsChart 
                            chartType={chartTypeOverride || result.chart_type} 
                            columns={result.columns} 
                            rows={result.rows} 
                            theme="light" 
                            onDrillDown={handleDrillDown}
                         />
                      </div>
                    ) : viewMode === 'ssms' ? (
                      /* ═══ SSMS GRID — Same data, raw values, zero formatting ═══ */
                      <div className="w-full flex-1 flex flex-col overflow-hidden" style={{ fontFamily: '"Segoe UI", "Consolas", monospace' }}>
                        {/* SSMS Header Bar */}
                        <div className="shrink-0 flex items-center justify-between px-4 py-2 border-b" style={{ background: '#F0F0F0', borderColor: '#CCCCCC' }}>
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-1.5">
                              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="1" y="1" width="14" height="14" rx="1" stroke="#666" strokeWidth="1"/><line x1="1" y1="5" x2="15" y2="5" stroke="#666" strokeWidth="0.5"/><line x1="5" y1="1" x2="5" y2="15" stroke="#666" strokeWidth="0.5"/><line x1="10" y1="1" x2="10" y2="15" stroke="#666" strokeWidth="0.5"/></svg>
                              <span className="text-[11px] font-medium" style={{ color: '#333' }}>Results</span>
                            </div>
                            <span className="text-[11px]" style={{ color: '#999' }}>|</span>
                            <span className="text-[10px]" style={{ color: '#666' }}>
                              {result.rows.length} row{result.rows.length !== 1 ? 's' : ''} affected
                            </span>
                          </div>
                          <button
                            onClick={() => {
                              const csvContent = [
                                result.columns.join(','),
                                ...result.rows.map((row: any[]) => row.map((cell: any) => {
                                  const val = cell === null || cell === undefined ? '' : String(cell);
                                  return val.includes(',') || val.includes('"') || val.includes('\n') ? `"${val.replace(/"/g, '""')}"` : val;
                                }).join(','))
                              ].join('\n');
                              const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                              const url = URL.createObjectURL(blob);
                              const link = document.createElement('a');
                              link.href = url;
                              link.download = `query_results_${new Date().toISOString().slice(0,10)}.csv`;
                              link.click();
                              URL.revokeObjectURL(url);
                            }}
                            className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] rounded hover:bg-[#E0E0E0] transition-colors"
                            style={{ color: '#333', border: '1px solid #CCCCCC', background: '#FFFFFF' }}
                          >
                            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                              <path d="M8 2v8M4 6l4 4 4-4M2 14h12" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                            Export CSV
                          </button>
                        </div>
                        {/* SSMS Data Grid */}
                        <div className="flex-1 overflow-auto">
                          <table className="w-full border-collapse" style={{ minWidth: 'max-content', fontSize: '12px' }}>
                            <thead>
                              <tr>
                                <th className="px-2 py-1.5 text-left font-normal border sticky top-0 z-10" style={{ background: '#D4E6F1', borderColor: '#A9CCE3', color: '#1A1A1A', minWidth: '36px', fontSize: '11px' }}>&nbsp;</th>
                                {result.columns.map((col: string, i: number) => (
                                  <th key={i} className="px-3 py-1.5 text-left font-normal border sticky top-0 z-10" style={{ background: '#D4E6F1', borderColor: '#A9CCE3', color: '#1A1A1A', minWidth: '90px', fontSize: '11px', whiteSpace: 'nowrap' }}>
                                    {col}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {result.rows.map((row: any[], rIdx: number) => (
                                <tr key={rIdx} className="hover:bg-[#E8F4FD]" style={{ background: '#FFFFFF' }}>
                                  <td className="px-2 py-1 border text-right tabular-nums" style={{ borderColor: '#DDD', color: '#888', fontSize: '11px', background: '#F5F5F5' }}>
                                    {rIdx + 1}
                                  </td>
                                  {row.map((val: any, cIdx: number) => (
                                    <td key={cIdx} className="px-3 py-1 border tabular-nums" style={{ borderColor: '#DDD', color: val === null || val === 'NULL' ? '#C0C0C0' : '#1A1A1A', fontStyle: val === null || val === 'NULL' ? 'italic' : 'normal', whiteSpace: 'nowrap' }}>
                                      {val === null || val === undefined ? 'NULL' : String(val)}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        {/* SSMS Status Bar */}
                        <div className="shrink-0 flex items-center px-4 py-1.5 border-t" style={{ background: '#F0F0F0', borderColor: '#CCCCCC' }}>
                          <span className="text-[10px]" style={{ color: '#666' }}>
                            Query executed successfully. Rows: {result.rows.length} · Columns: {result.columns.length}
                            {result.execution_time_ms ? ` · ${result.execution_time_ms}ms` : ''}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="w-full bg-[#F8F9FA] border border-[#333333] p-6 lg:p-8 flex-1 rounded-bl-xl rounded-br-xl">
                         <span className="text-[11px] uppercase tracking-wider text-[#8B9DAF] block mb-4 font-semibold">Executable SQL Query</span>
                         <pre className="p-4 bg-[#FFFFFF] border border-[#333333] rounded-md text-[13px] text-[#202124] font-mono overflow-x-auto shadow-sm min-h-[400px]">
                            {result.sql_query}
                         </pre>
                      </div>
                   )}
               </motion.div>
            ) : null}
          </div>
        </div>
      </motion.div>
    );
  };

   const renderKnowledgeGraphTab = () => (
    <div className="w-full h-full relative bg-[#FAFAFA] isolate">
      {/* The component itself handles the HUD and spatial topology rendering */}
      <IntelligenceMatrix />
    </div>
  );

  const renderPredictiveTab = () => (
    <div className="w-full h-full relative bg-[#FAFAFA] isolate">
      <DecisionStudio />
    </div>
  );

  const renderForecastingTab = () => (
    <div className="w-full h-full relative bg-[#FAFAFA] isolate">
      <PredictiveStudio />
    </div>
  );

   return (
    <div className="h-screen w-full flex bg-[#F8F6F3] text-[#1A1A1A] selection:bg-[#E87722] selection:text-[#FFFFFF] overflow-hidden" style={{ fontFamily: '"Figtree", sans-serif' }}>
       <audio ref={audioPlayerRef} className="hidden" />

   {/* ── LEFT SIDEBAR NAVIGATION ── */}
        {/* Changed to an austere, rigid desktop app layout. Hidden during active query. */}
        {(messages.length === 0 || activeTab !== 'operations') && (
         <aside className="w-[260px] h-full bg-[#F8F6F3] flex flex-col shrink-0" style={{ fontFamily: '"Figtree", sans-serif', borderRight: '1px solid rgba(0,0,0,0.06)' }}>
            
            {/* App Header */}
            <div className="h-[70px] flex items-center px-6 mb-2">
                <span className="text-[17px] text-[#1A1A1A] font-semibold tracking-wide">Basir Intelligence</span>
            </div>

            {/* Core Navigation System */}
            <div className="flex flex-col px-3 gap-1 flex-1 mt-2 overflow-y-auto">
               <div className="px-3 mb-4 shrink-0">
                 <span className="text-[10px] text-[#6B6B6B] font-semibold tracking-widest uppercase">Workspace</span>
               </div>
               
               <button 
                   onClick={() => setActiveTab('operations')}
                   className={`shrink-0 w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all ${activeTab === 'operations' ? 'bg-[#1A1A1A] text-[#FFFFFF] shadow-md' : 'text-[#2A2A2A] hover:bg-[#EDE9E3]'}`}
                >
                   <IconOperations />
                   <span className="text-[13px] font-medium">Operations</span>
                </button>

                <button 
                   onClick={() => setActiveTab('graph')}
                   className={`shrink-0 w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all ${activeTab === 'graph' ? 'bg-[#1A1A1A] text-[#FFFFFF] shadow-md' : 'text-[#2A2A2A] hover:bg-[#EDE9E3]'}`}
                >
                   <IconGraph />
                   <span className="text-[13px] font-medium">SequelOntology</span>
                </button>

                <button 
                   onClick={() => setActiveTab('predictive')}
                   className={`shrink-0 w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all ${activeTab === 'predictive' ? 'bg-[#1A1A1A] text-[#FFFFFF] shadow-md' : 'text-[#2A2A2A] hover:bg-[#EDE9E3]'}`}
                >
                   <IconPredictive />
                   <span className="text-[13px] font-medium">Decision Studio</span>
                </button>

                <button 
                   onClick={() => setActiveTab('forecasting')}
                   className={`shrink-0 w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all ${activeTab === 'forecasting' ? 'bg-[#1A1A1A] text-[#FFFFFF] shadow-md' : 'text-[#2A2A2A] hover:bg-[#EDE9E3]'}`}
                >
                   <IconForecasting />
                   <span className="text-[13px] font-medium">Predictive Studio</span>
                </button>

                {/* ── Past Conversations ── */}
                <div className="mt-6 mb-2 px-3 flex items-center justify-between shrink-0">
                  <span className="text-[10px] text-[#6B6B6B] font-semibold tracking-widest uppercase">Conversations</span>
                  <button 
                    onClick={() => { newConversation(); setActiveTab('operations'); }}
                    className="text-[10px] font-semibold text-[#E87722] hover:text-[#C45E10] transition-colors uppercase tracking-wider"
                  >
                    + New
                  </button>
                </div>
                
                {pastSessions.map(s => (
                  <button
                    key={s.session_id}
                    onClick={() => { loadSession(s.session_id); setActiveTab('operations'); }}
                    className={`shrink-0 w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-all text-left ${
                      sessionId === s.session_id ? 'bg-[#EDE9E3] text-[#1A1A1A]' : 'text-[#525252] hover:bg-[#EDE9E3]'
                    }`}
                  >
                    <IconChat />
                    <span className="text-[12px] truncate">{s.title}</span>
                  </button>
                ))}
            </div>

            <div className="px-3 mb-10">
              <button onClick={() => setShowLogoutModal(true)} className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-[#3A3A3A] hover:text-[#1A1A1A] hover:bg-[#EDE9E3] transition-colors" style={{ border: '1px solid rgba(0,0,0,0.12)' }}>
                <span className="text-[10px] font-semibold tracking-widest uppercase">Secure Logout</span>
              </button>
            </div>
         </aside>
        )}

   {/* ── MAIN WORKSPACE ── */}
        <main className="flex-1 h-full bg-[#FFFFFF] relative isolate" style={{ boxShadow: '-8px 0 24px rgba(0,0,0,0.02)' }}>
          <AnimatePresence mode="wait">
             {activeTab === 'operations' && (
                <motion.div key="operations" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
                   {renderOperationsTab()}
                </motion.div>
             )}
             {activeTab === 'graph' && (
                <motion.div key="graph" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
                   {renderKnowledgeGraphTab()}
                </motion.div>
             )}
             {activeTab === 'predictive' && (
                <motion.div key="predictive" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
                   {renderPredictiveTab()}
                </motion.div>
             )}
             {activeTab === 'forecasting' && (
                <motion.div key="forecasting" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
                   {renderForecastingTab()}
                </motion.div>
             )}
          </AnimatePresence>
        </main>

        {/* Logout Confirmation Modal */}
        <AnimatePresence>
          {showLogoutModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center"
              style={{ background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(4px)' }}
              onClick={() => setShowLogoutModal(false)}
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                transition={{ duration: 0.2 }}
                className="bg-[#FFFFFF] rounded-xl p-8 max-w-sm w-full mx-4"
                style={{ boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)' }}
                onClick={e => e.stopPropagation()}
              >
                <div className="text-center">
                  <div className="mx-auto w-12 h-12 rounded-full bg-[#F8F6F3] flex items-center justify-center mb-5" style={{ border: '1px solid rgba(0,0,0,0.06)' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1A1A1A" strokeWidth="1.5">
                      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" strokeLinecap="round" strokeLinejoin="round"/>
                      <polyline points="16,17 21,12 16,7" strokeLinecap="round" strokeLinejoin="round"/>
                      <line x1="21" y1="12" x2="9" y2="12" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <h3 className="text-[17px] font-semibold text-[#1A1A1A] mb-2" style={{ fontFamily: '"Figtree", sans-serif' }}>
                    Secure Logout
                  </h3>
                  <p className="text-[13px] text-[#6B6B6B] mb-8 leading-relaxed" style={{ fontFamily: '"Figtree", sans-serif' }}>
                    Are you sure you want to end this secure session? All unsaved work will be preserved.
                  </p>
                  <div className="flex gap-3">
                    <button
                      onClick={() => setShowLogoutModal(false)}
                      className="flex-1 px-5 py-2.5 rounded-lg text-[12px] font-semibold transition-colors"
                      style={{ 
                        fontFamily: '"Figtree", sans-serif',
                        background: '#F8F6F3',
                        color: '#3A3A3A',
                        border: '1px solid rgba(0,0,0,0.08)'
                      }}
                    >
                      Stay
                    </button>
                    <Link
                      href="/"
                      className="flex-1 px-5 py-2.5 rounded-lg text-[12px] font-semibold transition-colors text-center"
                      style={{ 
                        fontFamily: '"Figtree", sans-serif',
                        background: '#1A1A1A',
                        color: '#FFFFFF'
                      }}
                    >
                      Logout
                    </Link>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
     </div>
  );
}
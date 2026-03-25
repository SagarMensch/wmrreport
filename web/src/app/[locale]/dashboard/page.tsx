'use client';
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from '@/i18n/routing';
import VoiceChatInput from '@/components/VoiceChatInput';
import dynamic from 'next/dynamic';

const DrillCoreLoop = dynamic(() => import('@/components/DrillCoreLoop'), { ssr: false });
const ResultsChart = dynamic(() => import('@/components/ResultsChart'), { ssr: false });
const IntelligenceMatrix = dynamic(() => import('@/components/IntelligenceMatrix'), { ssr: false });
const DecisionStudio = dynamic(() => import('@/components/DecisionStudio'), { ssr: false });

// ── CUSTOM ISOMETRIC "3D" GEOMETRIC SVGS ─────────────────────────────────────
const IconCube = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2L2 7V17L12 22L22 17V7L12 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="miter"/>
    <path d="M12 22V12" stroke="currentColor" strokeWidth="1.5"/>
    <path d="M22 7L12 12L2 7" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="miter"/>
    <path d="M12 12V6" stroke="currentColor" strokeWidth="1.5" opacity="0.3"/>
  </svg>
);

const IconNodes = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <polygon points="12,2 20,8 20,16 12,22 4,16 4,8" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.1"/>
    <circle cx="12" cy="12" r="3" fill="currentColor"/>
    <line x1="12" y1="2" x2="12" y2="9" stroke="currentColor" strokeWidth="1.5"/>
    <line x1="4" y1="8" x2="9.5" y2="10.5" stroke="currentColor" strokeWidth="1.5"/>
    <line x1="20" y1="8" x2="14.5" y2="10.5" stroke="currentColor" strokeWidth="1.5"/>
  </svg>
);

const IconHexGrid = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M7 6L3 8.3V13.1L7 15.4L11 13.1V8.3L7 6Z" stroke="currentColor" strokeWidth="1.5"/>
    <path d="M17 6L13 8.3V13.1L17 15.4L21 13.1V8.3L17 6Z" stroke="currentColor" strokeWidth="1.5"/>
    <path d="M12 14.5L8 16.8V21.6L12 23.9L16 21.6V16.8L12 14.5Z" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.3"/>
  </svg>
);

const IconArrowLeft = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M19 12H5M5 12L12 19M5 12L12 5" stroke="currentColor" strokeWidth="2" strokeLinecap="square"/>
  </svg>
);

const IconCopy = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="9" y="9" width="13" height="13" stroke="currentColor" strokeWidth="1.5"/>
    <path d="M5 15H4V4H15V5" stroke="currentColor" strokeWidth="1.5"/>
  </svg>
);

const IconCheck = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="square"/>
  </svg>
);

const IconChat = () => (
  <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
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
}

type TabState = 'operations' | 'graph' | 'predictive';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabState>('operations');
  const [activeQuery, setActiveQuery] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [apiError, setApiError] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [sqlCopied, setSqlCopied] = useState(false);
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');
  
  // LangGraph Persistent Session ID
  const [sessionId] = useState(() => `sess_${Math.random().toString(36).substring(2, 10)}`);

  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    fetch('/api/history')
      .then(res => res.json())
      .then(data => {
        if (data && data.history) {
          setHistory(data.history);
        }
      })
      .catch(console.error);
  }, []);

  const resetToStart = () => {
    setActiveQuery(false);
    setResult(null);
    setApiError('');
  };

  const handleQuery = async (queryText: string) => {
    setActiveTab('operations');
    setActiveQuery(true);
    setIsLoading(true);
    setResult(null);
    setApiError('');
    setSqlCopied(false);

    setHistory((prev) => [queryText, ...prev.filter((h) => h !== queryText)].slice(0, 50));
    
    // Save to Supabase
    try {
      await fetch('/api/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: queryText }),
      });
    } catch (e) {
      console.error('Failed to save chat history', e);
    }

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: queryText, session_id: sessionId }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || err.error || `HTTP ${res.status}`);
      }

      const data: QueryResult = await res.json();
      setResult(data);
      
      // Extract query context from SQL for drill down
      if (data.sql_query) {
        const tableMatch = data.sql_query.match(/FROM\s+\[?(\w+)\]?/i);
        const whereMatch = data.sql_query.match(/WHERE\s+(\w+)/i);
        setQueryContext({
          table: tableMatch ? tableMatch[1] : undefined,
          column: whereMatch ? whereMatch[1] : undefined,
        });
      }

      if (data.reasoning && !data.error) {
        fetchTTS(data.reasoning);
      }
    } catch (err: any) {
      setApiError(err.message || 'Connection failed');
    } finally {
      setIsLoading(false);
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
  
  const handleDrillDown = (value: string) => {
    // Build contextual drill down query
    let drillQuery = "";
    
    if (queryContext.table && queryContext.column) {
      // Smart drill down - get details for the clicked value
      drillQuery = `Show me details for ${queryContext.column} = "${value}" in ${queryContext.table}`;
    } else if (result?.sql_query) {
      // Fallback: extract info from previous SQL
      const tableMatch = result.sql_query.match(/FROM\s+\[?(\w+)\]?/i);
      const tableName = tableMatch ? tableMatch[1] : "WellMonitoringReport_Latest";
      drillQuery = `Show wells where ${value}`;
    } else {
      drillQuery = `Show details for ${value}`;
    }
    
    handleQuery(drillQuery);
  };

  // ── RENDER TAB SYSTEM ──

  const renderOperationsTab = () => {
    if (!activeQuery) {
      // STATE A: THE MINIMALIST NLP START SCREEN
      // Like Google AI Studio: pure, centralized input, no fake data.
      return (
        <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-[#000000] relative isolate">
          {/* Subtle central glow */}
          <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,rgba(138,180,248,0.03)_0%,rgba(0,0,0,1)_60%)]" />

          {/* Central Workspace Definition */}
          <div className="flex flex-col items-center max-w-2xl w-full z-10 -mt-20">
             
             {/* Header */}
             <div className="flex items-center gap-4 mb-2">
                <IconCube />
             </div>
             <h1 className="text-[#E2E2E2] text-[28px] tracking-wide mb-1" style={{ fontFamily: '"Figtree", sans-serif', fontWeight: 300 }}>
                Synthesize structural intelligence
             </h1>
             <p className="text-[#9AA0A6] text-[13px] mb-12">
                Execute natural language queries to generate actionable visualizations.
             </p>

             {/* Main Central NLP Input */}
             <div className="w-full">
                <VoiceChatInput onSendQuery={handleQuery} isLoading={isLoading} />
             </div>

             {/* Nimr Quick Macro Suggestions */}
             <div className="flex flex-wrap justify-center gap-3 mt-8 opacity-70 max-w-[800px]">
                <button onClick={() => handleQuery('What is the average overall progress for all Nimr wells this week?')} className="px-4 py-2 rounded-full border border-[#333333] text-[#A0A0A0] text-[11px] hover:bg-[#1E1E1E] hover:text-[#E2E2E2] transition-colors flex items-center gap-2">
                   <IconNodes /> Nimr Average Progress
                </button>
                <button onClick={() => handleQuery('How many Nimr wells are fully complete (100% progress)?')} className="px-4 py-2 rounded-full border border-[#333333] text-[#A0A0A0] text-[11px] hover:bg-[#1E1E1E] hover:text-[#E2E2E2] transition-colors flex items-center gap-2">
                   <IconCheck /> Fully Complete Nimr Wells
                </button>
                <button onClick={() => handleQuery('Which rig has the highest average well progress across all Nimr wells?')} className="px-4 py-2 rounded-full border border-[#333333] text-[#A0A0A0] text-[11px] hover:bg-[#1E1E1E] hover:text-[#E2E2E2] transition-colors flex items-center gap-2">
                   <IconCube /> Top Nimr Rig Performance
                </button>
                <button onClick={() => handleQuery('Which wells have made zero progress for two consecutive weeks?')} className="px-4 py-2 rounded-full border border-[#333333] text-[#A0A0A0] text-[11px] hover:bg-[#1E1E1E] hover:text-[#E2E2E2] transition-colors flex items-center gap-2">
                   <IconHexGrid /> Stalled Zero-Progress Wells
                </button>
                <button onClick={() => handleQuery('Which Nimr wells have an expected rig-off date within the next 30 days but are below 60% progress?')} className="px-4 py-2 rounded-full border border-[#333333] text-[#A0A0A0] text-[11px] hover:bg-[#1E1E1E] hover:text-[#E2E2E2] transition-colors flex items-center gap-2">
                   <IconNodes /> At-Risk Nimr Completions
                </button>
             </div>
             
          </div>
        </div>
      );
    }

    // STATE B: Execution Split View (Side-by-side processing like Google AI Studio)
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="w-full h-full flex overflow-hidden bg-[#1E1E1E]" // AI Studio dark grey base
      >
        {/* Left Pane: Chat & Reasoning (Dark Mode, ~35%) */}
        <div className="w-full lg:w-[400px] xl:w-[450px] h-full flex flex-col border-r border-[#333333] bg-[#1E1E1E] shrink-0">
          
          {/* Top Bar with 'Back' */}
          <div className="h-[60px] flex items-center px-4 border-b border-[#333333]">
             <button onClick={resetToStart} className="flex items-center gap-2 px-3 py-1.5 rounded-full hover:bg-[#333333] text-[#A0A0A0] hover:text-[#FFFFFF] transition-colors">
                <IconArrowLeft />
                <span className="text-xs font-medium">Back to start</span>
             </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 scrollbar-thin scrollbar-thumb-[#444444]">
            {/* User Prompt Bubble */}
            <div className="mb-6 flex gap-3">
              <div className="w-6 h-6 rounded-full bg-[#111111] border border-[#333333] flex items-center justify-center shrink-0">
                <span className="text-[10px] text-[#A0A0A0]">U</span>
              </div>
              <div className="bg-[#2D2D2D] rounded-2xl rounded-tl-none p-3 px-4 text-[#F5F5F5] text-[13px] leading-relaxed max-w-[90%]">
                {history[0]}
              </div>
            </div>

            {/* AI Response Stream */}
            <div className="flex gap-3">
              <div className="w-6 h-6 rounded-full bg-[#8AB4F8]/10 border border-[#8AB4F8]/30 flex items-center justify-center shrink-0">
                <span className="text-[#8AB4F8] text-[10px]">B</span>
              </div>
              <div className="flex-1 min-w-0">
                {isLoading ? (
                   <div className="flex items-center gap-2 mt-1">
                     <span className="animate-spin text-[10px] text-[#8AB4F8]">◓</span>
                     <p className="text-[12px] text-[#A0A0A0]">Running execution pipeline...</p>
                   </div>
                ) : result && result.reasoning && (
                   <div className="flex flex-col gap-2 w-full mt-1">
                     <span className="text-[#E0E0E0] text-[13px]">
                        {(!result.columns || result.columns.length === 0) 
                          ? "Expanding analytical reasoning for decision studio..."
                          : "Successfully generated executive visualization."}
                     </span>
                     <details className="group border border-[#333333] rounded-lg overflow-hidden mt-2">
                       <summary className="bg-[#262626] px-4 py-2.5 cursor-pointer list-none flex items-center justify-between text-[#9AA0A6] text-[11px] font-medium tracking-wide uppercase hover:bg-[#333333] transition-colors">
                         <span className="flex items-center gap-2">
                           <span className="w-1.5 h-1.5 rounded-full bg-[#8AB4F8] animate-pulse"></span>
                           View Analytical Process
                         </span>
                         <span className="transition-transform duration-300 group-open:rotate-180 text-[10px]">▼</span>
                       </summary>
                       <div className="px-4 py-4 bg-[#141414]">
                         <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-[#A0A0A0] text-[12px] leading-relaxed space-y-3">
                           {result.reasoning.split('\n').map((paragraph: string, idx: number) => (
                             paragraph.trim() ? <p key={idx}>{paragraph.trim()}</p> : null
                           ))}
                         </motion.div>
                       </div>
                     </details>
                   </div>
                )}

                {apiError && (
                  <div className="mt-4 text-[#E53935] text-[12px] bg-[#E53935]/10 p-3 rounded-lg border border-[#E53935]/20">
                    ⚠ UPLINK ERROR: {apiError}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Persistent Input at bottom of Left Pane */}
          <div className="p-4 bg-[#1E1E1E]">
             <VoiceChatInput onSendQuery={handleQuery} isLoading={isLoading} />
          </div>
        </div>

        {/* Right Pane: Dynamic Preview (Pristine White) */}
        <div className="flex-1 h-full flex flex-col bg-[#FFFFFF] relative overflow-hidden">
          
          {/* Top Bar matching AI Studio 'Preview / Code' */}
          <div className="h-[60px] flex items-center justify-between px-6 border-b border-[#EAEAEA] bg-[#FAFAFA]">
             <div className="flex gap-2">
                <button 
                  onClick={() => setViewMode('preview')}
                  className={`px-4 py-1.5 rounded-full text-[13px] font-medium flex items-center gap-2 transition-colors ${viewMode === 'preview' ? 'bg-[#E8F0FE] text-[#1967D2]' : 'hover:bg-[#F1F3F4] text-[#5F6368]'}`}>
                   {viewMode === 'preview' && <span className="w-1.5 h-1.5 rounded-full bg-[#1967D2]" />} Preview
                </button>
                <button 
                  onClick={() => setViewMode('code')}
                  className={`px-4 py-1.5 rounded-full text-[13px] font-medium transition-colors ${viewMode === 'code' ? 'bg-[#E8F0FE] text-[#1967D2]' : 'hover:bg-[#F1F3F4] text-[#5F6368]'}`}>
                   Code
                </button>
             </div>
             
             {result && (
               <button onClick={copySql} className="flex items-center gap-2 text-[#5F6368] hover:bg-[#F1F3F4] px-3 py-1.5 rounded-full transition-colors text-[13px]">
                 {sqlCopied ? <IconCheck /> : <IconCopy />}
                 {sqlCopied ? 'Copied' : 'Copy SQL'}
               </button>
             )}
          </div>

          <div className="flex-1 overflow-y-auto relative scrollbar-thin scrollbar-thumb-gray-200">
            {isLoading ? (
               <div className="absolute inset-0 flex flex-col items-center justify-center opacity-60">
                  <div className="w-12 h-12 border-t-2 border-[#1967D2] border-l-2 border-transparent rounded-full animate-spin mb-4" />
                  <span className="text-[#5F6368] text-sm">Generating visualization...</span>
               </div>
            ) : result ? (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col h-full bg-[#FFFFFF]">
                   {/* Chart Type Selector */}
                   <div className="flex items-center gap-2 px-6 py-3 border-b border-[#EAEAEA] bg-[#F8F9FA]">
                      <span className="text-[11px] uppercase tracking-wider text-[#5F6368] font-medium">Chart:</span>
                      {['data_table', 'bar', 'horizontal_bar', 'donut', '3d_bar'].map(ct => (
                        <button
                          key={ct}
                          onClick={() => setChartTypeOverride(ct)}
                          className={`px-3 py-1 text-[11px] rounded-md transition-colors ${
                            (chartTypeOverride || result.chart_type) === ct 
                              ? 'bg-[#1A1A1A] text-white' 
                              : 'bg-[#E8E8E8] text-[#5F6368] hover:bg-[#D0D0D0]'
                          }`}
                        >
                          {ct.replace('_', ' ').toUpperCase()}
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
                   ) : (
                     <div className="w-full bg-[#F8F9FA] border border-[#EAEAEA] p-6 lg:p-8 flex-1 rounded-bl-xl rounded-br-xl">
                        <span className="text-[11px] uppercase tracking-wider text-[#5F6368] block mb-4 font-semibold">Executable SQL Query</span>
                        <pre className="p-4 bg-[#FFFFFF] border border-[#EAEAEA] rounded-md text-[13px] text-[#202124] font-mono overflow-x-auto shadow-sm min-h-[400px]">
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
    <div className="w-full h-full relative bg-[#000000] isolate">
      {/* The component itself handles the HUD and spatial topology rendering */}
      <IntelligenceMatrix />
    </div>
  );

  const renderPredictiveTab = () => (
    <div className="w-full h-full relative bg-[#000000] isolate">
      <DecisionStudio />
    </div>
  );

  return (
    <div className="h-screen w-full flex bg-[#000000] text-[#F5F5F5] selection:bg-[#8AB4F8] selection:text-[#000000] overflow-hidden">
       <audio ref={audioPlayerRef} className="hidden" />

       {/* ── LEFT SIDEBAR NAVIGATION ── */}
       {/* Changed to an austere, rigid desktop app layout. Hidden during active query. */}
       {(!activeQuery || activeTab !== 'operations') && (
         <aside className="w-[260px] h-full bg-[#1E1E1E] border-r border-[#333333] flex flex-col shrink-0">
            
            {/* App Header */}
            <div className="h-[70px] flex items-center px-6 mb-2">
                <span className="text-[16px] text-[#E2E2E2] font-medium tracking-wide" style={{ fontFamily: '"Figtree", sans-serif' }}>Basir Intelligence</span>
            </div>

            {/* Core Navigation System */}
            <div className="flex flex-col px-3 gap-1 flex-1 mt-2 overflow-y-auto scrollbar-thin scrollbar-thumb-[#333333]">
               <div className="px-3 mb-3 shrink-0">
                 <span className="text-[11px] text-[#9AA0A6] font-medium tracking-wide">Workspace</span>
               </div>
               
               <button 
                  onClick={() => setActiveTab('operations')}
                  className={`shrink-0 w-full flex items-center gap-3 px-4 py-2.5 rounded-full transition-all ${activeTab === 'operations' ? 'bg-[#333333] text-[#E2E2E2]' : 'text-[#C4C7C5] hover:bg-[#2A2A2A] hover:text-[#E2E2E2]'}`}
               >
                  <IconCube />
                  <span className="text-[13px] font-medium">Operations</span>
               </button>

               <button 
                  onClick={() => setActiveTab('graph')}
                  className={`shrink-0 w-full flex items-center gap-3 px-4 py-2.5 rounded-full transition-all ${activeTab === 'graph' ? 'bg-[#333333] text-[#E2E2E2]' : 'text-[#C4C7C5] hover:bg-[#2A2A2A] hover:text-[#E2E2E2]'}`}
               >
                  <IconNodes />
                  <span className="text-[13px] font-medium">SequelOntology</span>
               </button>

               <button 
                  onClick={() => setActiveTab('predictive')}
                  className={`shrink-0 w-full flex items-center gap-3 px-4 py-2.5 rounded-full transition-all ${activeTab === 'predictive' ? 'bg-[#333333] text-[#E2E2E2]' : 'text-[#C4C7C5] hover:bg-[#2A2A2A] hover:text-[#E2E2E2]'}`}
               >
                  <IconHexGrid />
                  <span className="text-[13px] font-medium">Predictive</span>
               </button>

               {/* Render Supabase Generated History */}
               {history.length > 0 && (
                 <>
                   <div className="px-3 mt-8 mb-3 shrink-0">
                     <span className="text-[11px] text-[#9AA0A6] font-medium tracking-wide">Recent Inquiries</span>
                   </div>
                   <div className="flex flex-col gap-1 pb-4">
                     {history.map((h, i) => (
                       <button 
                         key={i}
                         onClick={() => {
                           setActiveTab('operations');
                           handleQuery(h);
                         }}
                         className="w-full flex items-center gap-3 px-4 py-2 rounded-lg text-left text-[#A0A0A0] hover:bg-[#2A2A2A] hover:text-[#E2E2E2] transition-colors"
                         title={h}
                       >
                         <IconChat />
                         <span className="text-[12px] truncate">{h}</span>
                       </button>
                     ))}
                   </div>
                 </>
               )}
            </div>

            {/* System Environment Monitor */}
            <div className="p-4 mx-3 mb-4 rounded-xl bg-[#282A2C]">
              <div className="flex justify-between items-center mb-2">
                <span className="text-[10px] text-[#9AA0A6] font-medium uppercase tracking-wider">Node Status</span>
                <span className="w-2 h-2 bg-[#8AB4F8] rounded-full" />
              </div>
              <div className="text-[11px] font-mono text-[#E2E2E2]">
                 OMNI-729 [SECURE]
              </div>
            </div>

            <div className="px-3 mb-10">
              <Link href="/" className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-[#333333] text-[#A0A0A0] hover:text-[#FFFFFF] hover:bg-[#2A2A2A] transition-colors">
                <span className="text-[11px] font-bold tracking-widest uppercase">Secure Logout</span>
              </Link>
            </div>
         </aside>
       )}

       {/* ── MAIN WORKSPACE ── */}
       <main className="flex-1 h-full bg-[#000000] relative isolate">
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
          </AnimatePresence>
       </main>
    </div>
  );
}
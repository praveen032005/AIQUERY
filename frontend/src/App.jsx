import React, { useState, useEffect, useRef } from 'react';
import { Brain, Send, Users, ShieldAlert, Award, FileText, Trash2, ShieldCheck, Sparkles } from 'lucide-react';
import axios from 'axios';

// Configure Axios with dynamic base URL based on environment
const api = axios.create({
  baseURL: import.meta.env.DEV ? 'http://127.0.0.1:8001' : ''
});

function App() {
  const [trainees, setTrainees] = useState([]);
  const [selectedTrainee, setSelectedTrainee] = useState('');
  const [questionText, setQuestionText] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [recentQueries, setRecentQueries] = useState([]);
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [error, setError] = useState('');

  const chatEndRef = useRef(null);

  // Fetch trainees list and history logs
  const loadInitialData = async () => {
    try {
      const traineesRes = await api.get('/api/trainees');
      setTrainees(traineesRes.data);
      if (traineesRes.data.length > 0) {
        const defaultId = traineesRes.data[0].trainee_id;
        setSelectedTrainee(defaultId);
        loadChatMessages(defaultId);
      }
      
      const historyRes = await api.get('/api/analytics/question-analyses');
      setRecentQueries(historyRes.data);
    } catch (err) {
      console.error("Failed to load assessments page data", err);
    } finally {
      setListLoading(false);
    }
  };

  const loadChatMessages = async (traineeId) => {
    if (!traineeId) return;
    try {
      const res = await api.get(`/api/analytics/question-analyses?trainee_id=${traineeId}`);
      // Sort chronologically (oldest first for chat feed reading flow)
      const sorted = (res.data || []).reverse();
      setChatMessages(sorted);
    } catch (err) {
      console.error("Failed to load chat messages", err);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  // Update chat feed when selected trainee changes
  useEffect(() => {
    if (selectedTrainee) {
      loadChatMessages(selectedTrainee);
    }
  }, [selectedTrainee]);

  // Scroll to bottom when chat updates
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, loading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!questionText.trim()) return;

    setLoading(true);
    setError('');
    setCurrentAnalysis(null);

    try {
      const payload = {
        trainee_id: selectedTrainee,
        question_text: questionText
      };

      const response = await api.post('/api/analytics/chat-query', payload);
      setCurrentAnalysis(response.data);
      setQuestionText('');
      
      // Reload chat feed and historical log list
      await loadChatMessages(selectedTrainee);
      const historyRes = await api.get('/api/analytics/question-analyses');
      setRecentQueries(historyRes.data);
    } catch (err) {
      let msg = "Skills analysis query failed.";
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          msg = detail;
        } else if (Array.isArray(detail)) {
          msg = detail.map(d => `${d.loc ? d.loc.join('.') + ': ' : ''}${d.msg || JSON.stringify(d)}`).join(', ');
        } else {
          msg = JSON.stringify(detail);
        }
      } else if (err.message) {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm("Are you sure you want to purge all question analyses history?")) return;
    try {
      await api.delete('/api/analytics/question-analyses');
      setRecentQueries([]);
      setChatMessages([]);
      setCurrentAnalysis(null);
    } catch (err) {
      console.error("Failed to clear query logs", err);
    }
  };

  const getSelectedTraineeDetail = () => {
    return trainees.find(t => t.trainee_id === selectedTrainee);
  };

  const activeTrainee = getSelectedTraineeDetail();

  return (
    <div className="bg-gradient-mesh min-h-screen py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4 border-b border-white/5 pb-6">
          <div className="flex items-center gap-3">
            <div className="bg-indigo-600 p-2.5 rounded-xl shadow-lg shadow-indigo-600/20">
              <Brain className="h-7 w-7 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight flex items-center gap-2">
                Classroom AI Chat Assessment
                <span className="text-xs bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-full font-bold uppercase">Module</span>
              </h1>
              <p className="text-sm text-slate-400">Evaluate trainee query text, assess safety compliance, and score technical knowledge.</p>
            </div>
          </div>

          {recentQueries.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="flex items-center justify-center gap-2 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/25 text-rose-400 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer"
            >
              <Trash2 className="h-4 w-4" />
              Clear Query History
            </button>
          )}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Chat Panel (ChatGPT style) */}
          <div className="glass-card p-6 flex flex-col h-[650px] relative border-t-2 border-t-indigo-500 rounded-2xl">
            {/* Header with Trainee Selector */}
            <div className="border-b border-white/5 pb-4 mb-4 space-y-3">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-indigo-400" />
                Assessment Chat Feed
              </h3>
              
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block shrink-0">Trainee:</span>
                <div className="relative flex-1">
                  <select
                    value={selectedTrainee}
                    onChange={(e) => setSelectedTrainee(e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
                  >
                    {listLoading ? (
                      <option>Loading trainees...</option>
                    ) : (
                      trainees.map(t => (
                        <option key={t.trainee_id} value={t.trainee_id}>
                          {t.name} ({t.trade})
                        </option>
                      ))
                    )}
                  </select>
                </div>
              </div>
            </div>

            {/* Chat History Container */}
            <div className="flex-1 overflow-y-auto pr-1 space-y-4 mb-4">
              {chatMessages.length === 0 && !loading ? (
                <div className="h-full flex flex-col items-center justify-center text-center px-4">
                  <Users className="h-12 w-12 text-slate-600 mb-3" />
                  <p className="text-slate-400 font-medium">No chat history for this trainee.</p>
                  <p className="text-xs text-slate-500 mt-1 max-w-[240px]">Ask a technical trade question below to start the evaluation.</p>
                </div>
              ) : (
                chatMessages.map((msg, idx) => (
                  <div key={idx} className="space-y-3">
                    {/* User Question */}
                    <div className="flex justify-end">
                      <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-none px-4 py-2.5 max-w-[85%] shadow-md">
                        <span className="block text-[10px] text-indigo-200 font-bold mb-1 uppercase tracking-wider">Trainee Question</span>
                        <p className="text-sm font-medium">{msg.question_text || msg.resolved_text}</p>
                      </div>
                    </div>
                    {/* Bot Answer */}
                    <div className="flex justify-start">
                      <div className="bg-slate-900 border border-white/5 text-slate-200 rounded-2xl rounded-tl-none px-4 py-3 max-w-[85%] shadow-md">
                        <span className="block text-[10px] text-indigo-400 font-bold mb-1.5 uppercase tracking-wider flex items-center gap-1">
                          <Brain className="h-3 w-3" />
                          Classroom AI
                        </span>
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.answer}</p>
                      </div>
                    </div>
                  </div>
                ))
              )}
              {loading && (
                <div className="flex justify-start animate-pulse">
                  <div className="bg-slate-950 border border-indigo-500/10 text-slate-400 rounded-2xl rounded-tl-none px-4 py-3 max-w-[80%]">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce delay-100"></div>
                      <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce delay-200"></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl p-3 text-xs mb-3 flex items-start gap-2">
                <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Input Form */}
            <form onSubmit={handleSubmit} className="relative mt-auto">
              <input
                type="text"
                placeholder={activeTrainee ? `Ask a question about ${activeTrainee.trade.toLowerCase()}...` : "Type a trade question..."}
                value={questionText}
                onChange={(e) => setQuestionText(e.target.value)}
                disabled={loading || !selectedTrainee}
                className="w-full bg-slate-900 border border-white/10 rounded-xl pl-4 pr-12 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={loading || !questionText.trim() || !selectedTrainee}
                className="absolute right-2 top-2 p-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-lg transition-colors cursor-pointer"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>

          {/* Right Live Assessment Details Container */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Trainee Trade Stats Summary Card */}
            {activeTrainee && (
              <div className="glass-card p-6 border-l-4 border-l-emerald-500 rounded-2xl flex items-center justify-between">
                <div className="space-y-1">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Active Profiling Context</span>
                  <h2 className="text-2xl font-extrabold text-slate-100">{activeTrainee.name}</h2>
                  <div className="flex items-center gap-4 text-xs font-semibold text-slate-400 mt-2">
                    <span className="bg-slate-900 px-2.5 py-1 rounded-md border border-white/5">Trade: <strong className="text-indigo-400">{activeTrainee.trade}</strong></span>
                    <span className="bg-slate-900 px-2.5 py-1 rounded-md border border-white/5">ID: <strong className="text-slate-300">{activeTrainee.trainee_id}</strong></span>
                    <span className="bg-slate-900 px-2.5 py-1 rounded-md border border-white/5">Attendance: <strong className={activeTrainee.attendance_status === 'Absent' ? 'text-rose-400' : 'text-emerald-400'}>{activeTrainee.attendance_status}</strong></span>
                  </div>
                </div>
                <div className="hidden sm:block text-slate-500">
                  <Users className="h-10 w-10 text-slate-600" />
                </div>
              </div>
            )}

            {/* Assessment Scoring Card */}
            <div className="glass-card p-6 border-t-2 border-t-emerald-500 rounded-2xl min-h-[500px] flex flex-col justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 border-b border-white/5 pb-4 mb-6">
                  <Award className="h-5 w-5 text-emerald-400" />
                  Technical Analysis & Assessment Results
                </h3>

                {currentAnalysis ? (
                  <div className="space-y-6">
                    {/* Topic Classification */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-slate-900 border border-white/5 p-4 rounded-xl">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Assessed Level</span>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`text-sm font-bold px-2.5 py-0.5 rounded-full ${
                            currentAnalysis.category === 'Advanced' ? 'bg-indigo-500/20 text-indigo-400' :
                            currentAnalysis.category === 'Intermediate' ? 'bg-amber-500/20 text-amber-400' :
                            'bg-slate-500/20 text-slate-400'
                          }`}>
                            {currentAnalysis.category || currentAnalysis.classification}
                          </span>
                        </div>
                      </div>
                      <div className="bg-slate-900 border border-white/5 p-4 rounded-xl">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">XP Awarded</span>
                        <p className="text-lg font-extrabold text-emerald-400 mt-1">+{currentAnalysis.score_adjustment} XP</p>
                      </div>
                    </div>

                    {/* Competency Scores */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      {/* Relevance */}
                      <div className="bg-slate-900 border border-white/5 p-4 rounded-xl text-center">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">Trade Relevance</span>
                        <div className="text-3xl font-extrabold text-indigo-400">
                          {currentAnalysis.score_breakdown?.relevance}%
                        </div>
                        <div className="w-full bg-slate-950 h-1.5 rounded-full mt-3 overflow-hidden">
                          <div className="bg-indigo-500 h-full rounded-full" style={{ width: `${currentAnalysis.score_breakdown?.relevance}%` }}></div>
                        </div>
                      </div>

                      {/* Technical Depth */}
                      <div className="bg-slate-900 border border-white/5 p-4 rounded-xl text-center">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">Technical Depth</span>
                        <div className="text-3xl font-extrabold text-emerald-400">
                          {currentAnalysis.score_breakdown?.technical_depth}%
                        </div>
                        <div className="w-full bg-slate-950 h-1.5 rounded-full mt-3 overflow-hidden">
                          <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${currentAnalysis.score_breakdown?.technical_depth}%` }}></div>
                        </div>
                      </div>

                      {/* Vocabulary Rating */}
                      <div className="bg-slate-900 border border-white/5 p-4 rounded-xl text-center">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">Vocabulary Rating</span>
                        <div className="text-3xl font-extrabold text-amber-400">
                          {currentAnalysis.vocabulary_score || currentAnalysis.score_breakdown?.vocabulary_level}%
                        </div>
                        <div className="w-full bg-slate-950 h-1.5 rounded-full mt-3 overflow-hidden">
                          <div className="bg-amber-500 h-full rounded-full" style={{ width: `${currentAnalysis.vocabulary_score || currentAnalysis.score_breakdown?.vocabulary_level}%` }}></div>
                        </div>
                      </div>
                    </div>

                    {/* Safety Assessment */}
                    <div className={`p-4 rounded-xl border flex items-start gap-3 ${
                      currentAnalysis.safety_flagged 
                        ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' 
                        : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                    }`}>
                      {currentAnalysis.safety_flagged ? (
                        <>
                          <ShieldAlert className="h-5 w-5 shrink-0 mt-0.5" />
                          <div>
                            <h4 className="text-sm font-bold uppercase tracking-wider">Safety Hazard Triggered</h4>
                            <p className="text-xs text-rose-400/90 mt-1">This question targets elements concerning workshop safety hazards. High caution advised.</p>
                          </div>
                        </>
                      ) : (
                        <>
                          <ShieldCheck className="h-5 w-5 shrink-0 mt-0.5" />
                          <div>
                            <h4 className="text-sm font-bold uppercase tracking-wider">Safety Guidelines Maintained</h4>
                            <p className="text-xs text-emerald-400/90 mt-1">No workshop danger keywords or unsafe behavior patterns detected in this question.</p>
                          </div>
                        </>
                      )}
                    </div>

                    {/* Coordinator Notes */}
                    <div className="bg-slate-900 border border-white/5 p-4 rounded-xl">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2 flex items-center gap-1">
                        <FileText className="h-3.5 w-3.5" />
                        AI Assessment Notes
                      </span>
                      <p className="text-sm leading-relaxed text-slate-300 italic">
                        "{currentAnalysis.notes}"
                      </p>
                    </div>

                    {/* Model Used Tag */}
                    <div className="text-right text-[10px] text-slate-500 font-semibold tracking-wider">
                      EVALUATED VIA: <span className="text-slate-400 font-bold uppercase">{currentAnalysis.llm_model_used}</span>
                    </div>

                  </div>
                ) : (
                  <div className="h-full py-20 flex flex-col items-center justify-center text-center px-4">
                    <Brain className="h-16 w-16 text-slate-700 mb-4 animate-pulse" />
                    <p className="text-slate-400 font-medium max-w-sm">
                      Submit a trainee query to see live competency grading, vocabulary scores, and safety evaluations.
                    </p>
                  </div>
                )}
              </div>

              {currentAnalysis && (
                <div className="text-[10px] text-slate-500 border-t border-white/5 pt-4 text-center mt-6">
                  Classroom AI Standalone Assessment Engine &bull; Real-time analysis active
                </div>
              )}
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}

export default App;

import React, { useState, useEffect, useRef } from 'react';
import ChatSidebar from './ChatSidebar';
import { chatAPI } from '../services/api';

export default function ChatAssistant({ user }) {
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [explanationsMap, setExplanationsMap] = useState({}); // { messageId: {confidence, explanation, needs_info, suggestions} }
  const [showFixModal, setShowFixModal] = useState(false);
  const [fixMessageId, setFixMessageId] = useState(null);
  const [fixCategory, setFixCategory] = useState('');
  const [needsInfoBanner, setNeedsInfoBanner] = useState(null); // holds suggestions when assistant asked for category
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (activeSession) loadSession(activeSession.id);
  }, [activeSession?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadSessions = async () => {
    try {
      const res = await chatAPI.listSessions();
      const sessionsData = res.data?.data?.sessions || [];
      setSessions(sessionsData);
      if (!activeSession && sessionsData.length) {
        setActiveSession(sessionsData[0]);
      }
    } catch (err) {
      console.error('Failed to load sessions', err);
    }
  };

  const loadSession = async (chat_id) => {
    try {
      const res = await chatAPI.getSession(chat_id);
      const data = res.data?.data || {};
      const msgs = data.messages || [];
      // normalize messages to include id, role, content, created_at
      setMessages(msgs);
      // clear explanations map; we'll populate on next send or fetch
      setExplanationsMap({});
      setNeedsInfoBanner(null);
    } catch (err) {
      console.error('Failed to load session', err);
    }
  };

  const handleNewChat = async () => {
    try {
      const res = await chatAPI.createSession('New chat');
      await loadSessions();
    } catch (err) {
      await loadSessions();
    }
  };

  const handleSelectSession = (session) => {
    setActiveSession(session);
    // load messages will trigger via effect
  };

  const sendMessage = async () => {
    if (!input.trim() || !activeSession) return;
    const content = input.trim();
    setInput('');
    setLoading(true);

    // optimistic UI
    const temp = { id: `tmp-${Date.now()}`, role: 'user', content, created_at: new Date().toISOString() };
    setMessages(prev => [...prev, temp]);

    try {
      const res = await chatAPI.sendMessage(content, activeSession.id);
      if (!res.data || !res.data.data) {
        throw new Error('No data from server');
      }
      const d = res.data.data;
      // update messages from server canonical list if provided
      if (d.messages) {
        setMessages(d.messages);
      } else {
        // append assistant reply when only reply provided
        const assistantMessage = {
          id: d.message_id || `msg-${Date.now()}`,
          role: 'assistant',
          content: d.reply || 'No reply',
          created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev.filter(m => !String(m.id).startsWith('tmp-')), assistantMessage]);
      }
      // attach explanations map returned by server
      if (d.explanations) {
        setExplanationsMap(prev => ({ ...prev, ...d.explanations }));
        // if assistant asked for additional info (pending category), show banner
        // find explanation entry with needs_info true
        const needs = Object.values(d.explanations).find(e => e && e.needs_info);
        if (needs) {
          setNeedsInfoBanner(needs);
        } else {
          setNeedsInfoBanner(null);
        }
      } else {
        setNeedsInfoBanner(null);
      }

      // refresh sessions list (to update previews)
      await loadSessions();
    } catch (err) {
      console.error('sendMessage error', err);
      setMessages(prev => [...prev, { id: `err-${Date.now()}`, role: 'assistant', content: '❌ Error sending message' }]);
    } finally {
      setLoading(false);
    }
  };

  // open fix modal for assistant message
  const openFixModal = (messageId) => {
    setFixMessageId(messageId);
    setFixCategory('');
    setShowFixModal(true);
  };

  const submitFix = async () => {
    if (!fixCategory.trim() || !activeSession || !fixMessageId) return;
    try {
      await chatAPI.sendFeedback(activeSession.id, { message_id: fixMessageId, correction: { category: fixCategory } });
      alert('Thanks — correction saved.');
      setShowFixModal(false);
      // refresh session to reflect any learner updates
      await loadSession(activeSession.id);
      await loadSessions();
    } catch (err) {
      console.error('fix failed', err);
      alert('Failed to send correction');
    }
  };

  const handleNeedsInfoPick = async (suggestion) => {
    // If assistant asked for category (needs_info), send that as a user message
    if (!activeSession) return;
    setInput(suggestion);
    // send message (simulate user clicking suggestion)
    setTimeout(async () => { await sendMessage(); }, 10);
  };

  return (
    <div className="flex h-screen">
      <ChatSidebar
        sessions={sessions}
        activeChatId={activeSession?.id}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectSession}
      />

      <div className="flex-1 flex flex-col bg-gradient-to-br from-purple-50 to-blue-50">
        <div className="p-4 bg-white border-b flex justify-between items-center">
          <div>
            <h2 className="text-xl font-semibold">{activeSession?.title || 'New Chat'}</h2>
            <div className="text-sm text-gray-500">{activeSession ? `Chat #${activeSession.id}` : 'No session selected'}</div>
          </div>
        </div>

        {/* low-confidence banner when assistant asked for category or low confidence */}
        {needsInfoBanner && (
          <div className="p-4 bg-yellow-50 border-l-4 border-yellow-400">
            <div className="flex justify-between items-center">
              <div>
                <strong>⚠️ I may need help:</strong> {needsInfoBanner.explanation || 'Please confirm a category.'}
                {needsInfoBanner.suggestions && needsInfoBanner.suggestions.length > 0 && (
                  <div className="mt-2 text-sm">
                    Suggestions:
                    {needsInfoBanner.suggestions.map((s, idx) => (
                      <button key={idx} onClick={() => handleNeedsInfoPick(s)} className="ml-2 px-2 py-1 bg-white border rounded text-xs">{s}</button>
                    ))}
                  </div>
                )}
              </div>
              <div className="text-sm text-gray-500">Confidence: {(needsInfoBanner.confidence || 0).toFixed(2)}</div>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-auto p-6 space-y-4">
          {messages.map((msg) => {
            const explain = explanationsMap[String(msg.id)];
            const confidence = explain?.confidence;
            return (
              <div key={msg.id || msg.created_at} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-2xl px-6 py-4 rounded-2xl shadow-md ${msg.role === 'user' ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white' : 'bg-white text-gray-800'}`}>
                  <pre className="whitespace-pre-wrap">{msg.content}</pre>

                  {msg.role === 'assistant' && (
                    <div className="mt-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {typeof confidence === 'number' && (
                          <div className={`text-xs font-semibold px-2 py-1 rounded ${confidence >= 0.75 ? 'bg-green-100 text-green-700' : confidence >= 0.5 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                            Confidence: {(confidence*100).toFixed(0)}%
                          </div>
                        )}
                        <button className="text-xs underline text-gray-500" onClick={() => {
                          // toggle an inline explanation expansion by adding a small UI bit
                          const el = document.getElementById(`explain-${msg.id}`);
                          if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
                        }}>Why this?</button>
                        <button className="text-xs underline text-gray-500" onClick={() => openFixModal(msg.id)}>Fix Category</button>
                      </div>

                      <div className="text-xs text-gray-400">{new Date(msg.created_at).toLocaleTimeString()}</div>
                    </div>
                  )}

                  {msg.role === 'assistant' && (
                    <div id={`explain-${msg.id}`} style={{display: 'none'}} className="mt-2 text-sm text-gray-600 bg-gray-50 p-3 rounded">
                      <div><strong>Explanation:</strong></div>
                      <div>{explain?.explanation || 'No explanation available.'}</div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 bg-white border-t">
          <div className="max-w-4xl mx-auto flex gap-4">
            <input
              type="text"
              className="flex-1 px-4 py-3 border rounded-xl"
              placeholder="Type a message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              disabled={loading}
            />
            <button onClick={sendMessage} disabled={loading || !input.trim()} className="px-6 py-3 bg-purple-600 text-white rounded-xl">
              {loading ? '⏳' : 'Send'}
            </button>
          </div>
        </div>
      </div>

      {/* Fix modal */}
      {showFixModal && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-96">
            <h3 className="font-bold mb-3">Fix Category</h3>
            <p className="text-sm text-gray-600 mb-3">Provide the correct category for the selected assistant message.</p>
            <input value={fixCategory} onChange={(e) => setFixCategory(e.target.value)} placeholder="e.g., Groceries" className="w-full px-3 py-2 border rounded mb-3" />
            <div className="flex gap-2 justify-end">
              <button className="px-4 py-2 bg-gray-200 rounded" onClick={() => setShowFixModal(false)}>Cancel</button>
              <button className="px-4 py-2 bg-green-600 text-white rounded" onClick={submitFix}>Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

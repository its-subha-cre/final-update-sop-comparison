import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Bot, User, Loader2, Sparkles } from 'lucide-react';
import { apiClient } from '../../api/client';

export default function SOPChatAssistant({ activeJobId, onToggle }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { sender: 'bot', text: "Hello! I am your  SOP Compliance Assistant. Ask me anything about the uploaded SOP documents, section mismatches, or recommendations." }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatBodyRef = useRef(null);

  // Auto-scroll messages to the bottom
  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages]);

  // Inject attractive floating & border-pulsing animation styles
  useEffect(() => {
    const styleId = 'sop-assistant-float-style';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.textContent = `
        @keyframes floatAnim {
          0% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
          100% { transform: translateY(0px); }
        }
        @keyframes borderPulse {
          0% { box-shadow: 0 8px 32px 0 rgba(140, 80, 255, 0.3), 0 0 0 0px rgba(140, 80, 255, 0.45); }
          70% { box-shadow: 0 8px 32px 0 rgba(140, 80, 255, 0.3), 0 0 0 10px rgba(140, 80, 255, 0); }
          100% { box-shadow: 0 8px 32px 0 rgba(140, 80, 255, 0.3), 0 0 0 0px rgba(140, 80, 255, 0); }
        }
        .attractive-chat-btn {
          animation: floatAnim 3s ease-in-out infinite, borderPulse 2.2s infinite;
          background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
          border: 1px solid rgba(255, 255, 255, 0.25) !important;
          transition: transform 0.2s ease, filter 0.2s ease !important;
        }
        .attractive-chat-btn:hover {
          filter: brightness(1.2);
          transform: scale(1.1) translateY(-4px) !important;
        }
      `;
      document.head.appendChild(style);
    }
  }, []);

  const handleToggle = () => {
    const nextState = !isOpen;
    setIsOpen(nextState);
    if (onToggle) {
      onToggle(nextState);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input;
    setInput('');
    setMessages(prev => [...prev, { sender: 'user', text: userText }]);
    setLoading(true);

    const chatHistory = messages
      .slice(1) // Skip welcome message
      .map(m => ({
        role: m.sender === 'user' ? 'user' : 'assistant',
        content: m.text
      }));

    try {
      const res = await apiClient.sendChatMessage(userText, activeJobId, chatHistory);
      if (res.success) {
        setMessages(prev => [...prev, { sender: 'bot', text: res.response }]);
      } else {
        let friendlyText = "⚠️ Sorry, I ran into an error connecting to the LLM assistant model.";
        if (res.error_type === "TOKEN_LIMIT") {
          friendlyText = "⚠️ Your request is too large for the current AI model. Please shorten your question or start a new chat.";
        } else if (res.error_type === "RATE_LIMIT") {
          friendlyText = "⚠️ The AI service has temporarily reached its usage limit. Please wait a few moments and try again.";
        } else if (res.error_type === "INVALID_KEY") {
          friendlyText = "⚠️ Unable to connect to the AI service because the configured API key is invalid.";
        } else if (res.error_type === "QUOTA_EXCEEDED") {
          friendlyText = "⚠️ The configured AI API has reached its usage limit. Please update or recharge the existing API key in the application configuration.";
        } else if (res.error_type === "NETWORK_ERROR") {
          friendlyText = "⚠️ Unable to reach the AI service. Please check your connection and try again.";
        } else if (res.message) {
          friendlyText = res.message;
        }
        setMessages(prev => [...prev, { sender: 'bot', text: friendlyText }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { 
        sender: 'bot', 
        text: "⚠️ Unable to reach the AI service. Please check your connection and try again." 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Chat Icon (FAB) */}
      <button 
        onClick={handleToggle}
        className="glow-button attractive-chat-btn"
        style={{
          position: 'fixed', bottom: '24px', right: '24px', width: '56px', height: '56px',
          borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 10001, cursor: 'pointer'
        }}
      >
        {isOpen ? (
          <X style={{ width: '22px', height: '22px', color: 'white' }} />
        ) : (
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Bot style={{ width: '22px', height: '22px', color: 'white' }} />
            <Sparkles style={{ 
              width: '12px', height: '12px', color: '#fcd34d', 
              position: 'absolute', top: '-6px', right: '-6px',
              animation: 'spin 5s linear infinite'
            }} />
          </div>
        )}
      </button>

      {/* Slide-in Chat Sidebar */}
      <div style={{
        position: 'fixed', top: 0, right: 0, width: '380px', height: '100vh',
        background: '#0f0c1b', borderLeft: '1px solid rgba(255,255,255,0.08)',
        boxShadow: '-8px 0 32px 0 rgba(0, 0, 0, 0.5)', zIndex: 10000,
        transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
        transition: 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
        display: 'flex', flexDirection: 'column'
      }}>
        {/* Sidebar Header */}
        <div style={{
          padding: '20px', borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Bot style={{ width: '22px', height: '22px', color: 'var(--secondary)' }} />
            <div style={{ textAlign: 'left' }}>
              <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: 'white' }}>SOP Assistant</h4>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Online • Context Aware</span>
            </div>
          </div>
          <button 
            onClick={handleToggle}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
          >
            <X style={{ width: '18px', height: '18px' }} />
          </button>
        </div>

        {/* Messages Body */}
        <div 
          ref={chatBodyRef}
          style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}
        >
          {messages.map((msg, i) => {
            const isBot = msg.sender === 'bot';
            return (
              <div key={i} style={{
                display: 'flex', gap: '10px', flexDirection: isBot ? 'row' : 'row-reverse',
                alignItems: 'flex-start'
              }}>
                <div style={{
                  width: '30px', height: '30px', borderRadius: '50%', flexShrink: 0,
                  background: isBot ? 'rgba(6, 182, 212, 0.15)' : 'rgba(139, 92, 246, 0.15)',
                  border: `1px solid ${isBot ? 'rgba(6,182,212,0.3)' : 'rgba(139,92,246,0.3)'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  {isBot ? <Bot style={{ width: '16px', height: '16px', color: 'var(--secondary)' }} /> 
                         : <User style={{ width: '16px', height: '16px', color: 'var(--primary)' }} />}
                </div>
                <div style={{
                  maxWidth: '75%', padding: '12px', borderRadius: '12px',
                  background: isBot ? 'rgba(255,255,255,0.03)' : 'var(--primary)',
                  border: isBot ? '1px solid rgba(255,255,255,0.05)' : 'none',
                  color: isBot ? 'rgba(255,255,255,0.9)' : 'white',
                  fontSize: '13px', textAlign: 'left', borderRadiusTopLeft: isBot ? 0 : '12px',
                  borderRadiusTopRight: isBot ? '12px' : 0, lineHeight: '1.5',
                  wordBreak: 'break-word', whiteSpace: 'pre-wrap'
                }}>
                  {msg.text}
                </div>
              </div>
            );
          })}
          {loading && (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <div style={{
                width: '30px', height: '30px', borderRadius: '50%', background: 'rgba(6, 182, 212, 0.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <Bot style={{ width: '16px', height: '16px', color: 'var(--secondary)' }} />
              </div>
              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Loader2 style={{ animation: 'spin 1s linear infinite', width: '14px', height: '14px', color: 'var(--secondary)' }} />
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Assistant is typing...</span>
              </div>
            </div>
          )}
        </div>

        {/* Input Footer */}
        <form onSubmit={handleSend} style={{
          padding: '16px', borderTop: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', gap: '10px'
        }}>
          <input 
            type="text"
            placeholder="Ask about compliance findings..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            style={{
              flex: 1, padding: '12px', borderRadius: '8px', fontSize: '13px',
              background: 'rgba(255,255,255,0.04)', color: 'white', border: '1px solid var(--card-border)',
              outline: 'none'
            }}
          />
          <button 
            type="submit"
            disabled={loading || !input.trim()}
            style={{
              width: '40px', height: '40px', borderRadius: '8px', border: 'none',
              background: 'var(--primary)', color: 'white', display: 'flex', alignItems: 'center',
              justifyContent: 'center', cursor: 'pointer', opacity: (loading || !input.trim()) ? 0.6 : 1
            }}
          >
            <Send style={{ width: '16px', height: '16px' }} />
          </button>
        </form>
      </div>
    </>
  );
}
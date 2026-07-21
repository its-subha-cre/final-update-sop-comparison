import React, { useState, useEffect } from 'react';
import { ShieldCheck, HelpCircle, Settings, FileText, BrainCircuit } from 'lucide-react';
import LLMSetupWizard from './components/setup/LLMSetupWizard';
import SOPUploadManager from './components/upload/SOPUploadManager';
import FileStatusTracker from './components/upload/FileStatusTracker';
import SOPListManager from './components/upload/SOPListManager';
import SimilarityMatrix from './components/visualization/SimilarityMatrix';
import RecommendationReport from './components/visualization/RecommendationReport';
import D3DiffGraph from './components/visualization/D3DiffGraph';
import SOPChatAssistant from './components/chat/SOPChatAssistant';
import { apiClient } from './api/client';

export default function App() {
  const [isConfigured, setIsConfigured] = useState(null);
  const [showWizard, setShowWizard] = useState(false);
  const [activeJobId, setActiveJobId] = useState(null);
  const [activeJob, setActiveJob] = useState(null);
  const [chatIsOpen, setChatIsOpen] = useState(false);
  const [dbStatus, setDbStatus] = useState(null);
  const [repoRefreshTrigger, setRepoRefreshTrigger] = useState(0);

  // 1. Check configuration status on mount
  useEffect(() => {
    async function checkStatus() {
      try {
        const res = await apiClient.getConfigStatus();
        setIsConfigured(res.configured);
        if (!res.configured) {
          setShowWizard(true);
        }
      } catch (err) {
        console.error('Failed checking API engine config status:', err);
        setIsConfigured(false);
        setShowWizard(true);
      }
    }
    checkStatus();
  }, []);

  // 1b. Poll Neo4j health status
  useEffect(() => {
    async function checkDbHealth() {
      try {
        const res = await apiClient.getNeo4jHealth();
        setDbStatus(res.status);
      } catch (err) {
        console.error('Failed checking database health status:', err);
        setDbStatus('OFFLINE');
      }
    }
    checkDbHealth();
    const dbInterval = setInterval(checkDbHealth, 20000);
    return () => clearInterval(dbInterval);
  }, []);

  // 2. Poll job status when activeJobId is set
  useEffect(() => {
    if (!activeJobId) return;

    const interval = setInterval(async () => {
      try {
        const res = await apiClient.getJobStatus(activeJobId);
        if (res.success) {
          setActiveJob(res.job);
           if (res.job.status === 'completed' || res.job.status === 'failed') {
            clearInterval(interval);
            setRepoRefreshTrigger(prev => prev + 1);
          }
        }
      } catch (err) {
        console.error('Error polling job status:', err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJobId]);

  if (isConfigured === null) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <p>Loading application resources...</p>
      </div>
    );
  }

  return (
    <>
      <div style={{
        maxWidth: '1200px', margin: '0 auto', padding: '24px 16px',
        transform: chatIsOpen ? 'translateX(-120px)' : 'none',
        transition: 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
      }}>
        
        {/* Header Banner */}
        <header style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '16px', marginBottom: '32px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <BrainCircuit style={{ width: '36px', height: '36px', color: 'var(--primary)' }} />
            <div style={{ textAlign: 'left' }}>
              <h1 style={{ margin: 0, fontSize: '22px', fontWeight: 700 }} className="gradient-text">
                SOP Comparison
              </h1>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Multi-Agent Compliance Normalization Engine
              </span>
            </div>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {dbStatus === 'CONNECTED' ? (
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: '6px',
                fontSize: '12px', background: 'rgba(74, 222, 128, 0.1)', color: '#4ade80',
                border: '1px solid rgba(74, 222, 128, 0.2)', padding: '6px 12px', borderRadius: '20px',
                fontWeight: 500
              }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#4ade80' }}></span>
                Neo4j Connected
              </span>
            ) : dbStatus === 'OFFLINE' ? (
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: '6px',
                fontSize: '12px', background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444',
                border: '1px solid rgba(239, 68, 68, 0.2)', padding: '6px 12px', borderRadius: '20px',
                fontWeight: 500
              }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444' }}></span>
                Neo4j Offline
              </span>
            ) : null}

            <button 
              onClick={() => setShowWizard(!showWizard)}
              style={{
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px', padding: '8px 16px', color: 'white', display: 'flex', alignItems: 'center',
                gap: '8px', cursor: 'pointer', fontSize: '13px', transition: 'var(--transition)'
              }}
            >
              <Settings style={{ width: '16px', height: '16px' }} />
              LLM Engine Settings
            </button>
          </div>
        </header>

        {dbStatus === 'OFFLINE' && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: '12px', padding: '16px 20px', marginBottom: '24px', textAlign: 'left',
            color: '#fca5a5', fontSize: '13px', lineHeight: '1.5'
          }}>
            <strong>Neo4j is currently offline.</strong> Knowledge Graph, GraphRAG retrieval, and graph visualization are temporarily unavailable. Document comparison, compliance analysis, and report generation will continue to operate normally.
          </div>
        )}

        {showWizard ? (
          <LLMSetupWizard onCompleted={() => {
            setIsConfigured(true);
            setShowWizard(false);
          }} />
        ) : (
          <main style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Files Upload manager */}
             <SOPUploadManager onJobTriggered={(jobId) => {
              setActiveJobId(jobId);
              setActiveJob({ status: 'queued', stage: 'queued', errors: [] });
            }} />

            {/* SOP Repository Management */}
            <SOPListManager 
              refreshTrigger={repoRefreshTrigger} 
              onDeleted={() => {
                setActiveJobId(null);
                setActiveJob(null);
                setRepoRefreshTrigger(prev => prev + 1);
              }} 
            />

            {/* Pipeline Tracker */}
            <FileStatusTracker activeJob={activeJob} />

            {/* Results dashboard */}
            {activeJob && activeJob.status === 'completed' && (
              <SimilarityMatrix activeJob={activeJob} />
            )}
            
            <div style={{ display: 'grid', gridTemplateColumns: '1.05fr 0.95fr', gap: '24px', marginTop: '8px' }}>
              <D3DiffGraph activeJob={activeJob} />
              <RecommendationReport activeJob={activeJob} />
            </div>
          </main>
        )}

        {/* Subtle Footer */}
        <footer style={{ marginTop: '64px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '16px', color: 'var(--text-muted)', fontSize: '11px' }}>
          Tcs Confidential. &copy; 2026 TCS. All rights reserved.
        </footer>
      </div>

      {/* Floating Chat Assistant Sidebar (rendered outside translated container) */}
      <SOPChatAssistant activeJobId={activeJobId} onToggle={(isOpen) => setChatIsOpen(isOpen)} />
    </>
  );
}

import React, { useState, useEffect } from 'react';
import { Loader2, Check, X, AlertTriangle, Sparkles } from 'lucide-react';

export default function FileStatusTracker({ activeJob }) {
  if (!activeJob) return null;

  const stages = [
    { key: 'queued', label: 'Queued', percentage: 0 },
    { key: 'parsing', label: 'Parsing', percentage: 20 },
    { key: 'chunked', label: 'Chunked', percentage: 40 },
    { key: 'graph-written', label: 'Graph Written', percentage: 60 },
    { key: 'compared', label: 'Compared', percentage: 80 },
    { key: 'done', label: 'Done', percentage: 100 }
  ];

  const currentStageKey = activeJob.stage || 'queued';
  const isFailed = activeJob.status === 'failed';
  const isCompleted = activeJob.status === 'completed';
  
  const currentStageIndex = stages.findIndex(s => s.key === currentStageKey);
  const targetProgress = isCompleted ? 100 : (currentStageIndex >= 0 ? stages[currentStageIndex].percentage : 0);

  // Animated percentage state counter
  const [animatedProgress, setAnimatedProgress] = useState(0);

  useEffect(() => {
    if (isFailed) return;
    
    // Smoothly animate the percentage count
    const duration = 800; // ms
    const stepTime = 20; // ms
    const totalSteps = duration / stepTime;
    const increment = (targetProgress - animatedProgress) / totalSteps;
    
    let currentStep = 0;
    const timer = setInterval(() => {
      currentStep++;
      setAnimatedProgress(prev => {
        const nextVal = prev + increment;
        if (currentStep >= totalSteps) {
          clearInterval(timer);
          return targetProgress;
        }
        return Math.round(nextVal);
      });
    }, stepTime);

    return () => clearInterval(timer);
  }, [targetProgress, isFailed]);

  const hasNeo4jWarning = activeJob.errors?.some(err => err.toLowerCase().includes('neo4j')) || false;

  return (
    <div className="glass" style={{ padding: '28px', marginTop: '24px', textAlign: 'left', position: 'relative', overflow: 'hidden' }}>
      
      {/* Self-contained Keyframe Animations */}
      <style>{`
        @keyframes pulseBorder {
          0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.4); }
          70% { transform: scale(1.08); box-shadow: 0 0 0 10px rgba(139, 92, 246, 0); }
          100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(139, 92, 246, 0); }
        }
        @keyframes rotateBorder {
          100% { transform: rotate(360deg); }
        }
        @keyframes slideInUp {
          from { transform: translateY(12px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        .active-ring {
          animation: pulseBorder 2s infinite ease-in-out;
        }
        .loading-dash {
          position: absolute;
          inset: -3px;
          border-radius: 50%;
          border: 3px solid transparent;
          border-top-color: var(--primary);
          animation: rotateBorder 1s linear infinite;
        }
        .stage-transition {
          transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
      `}</style>

      {/* Tracker Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h3 style={{ margin: 0, fontSize: '16px', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span>Pipeline Progress Tracker</span>
          {!isCompleted && !isFailed && (
            <Loader2 style={{ animation: 'rotateBorder 1s linear infinite', width: '16px', height: '16px', color: 'var(--secondary)' }} />
          )}
          {hasNeo4jWarning && (
            <span style={{
              fontSize: '10px', fontWeight: 700, padding: '3px 8px', borderRadius: '4px',
              background: 'rgba(239, 68, 68, 0.08)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.18)',
              whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '4px', marginLeft: '8px'
            }}>
              <AlertTriangle style={{ width: '12px', height: '12px', color: 'var(--error)' }} />
              Neo4j Offline (In-Memory Run)
            </span>
          )}
        </h3>
        
        {/* Dynamic Percentage Counter */}
        <span className="gradient-text" style={{ fontSize: '24px', fontWeight: 800, transition: 'all 0.3s' }}>
          {isFailed ? 'FAILED' : `${animatedProgress}%`}
        </span>
      </div>

      {/* Graphical Status Timeline */}
      <div style={{ display: 'flex', justifyContent: 'space-between', position: 'relative', marginTop: '30px', marginBottom: '30px' }}>
        
        {/* Connecting Progress Line (Background) */}
        <div style={{
          position: 'absolute', top: '16px', left: '40px', right: '40px', height: '3px',
          background: 'rgba(255, 255, 255, 0.05)', zIndex: 1
        }} />
        
        {/* Active Fill Line */}
        <div style={{
          position: 'absolute', top: '16px', left: '40px', height: '3px',
          width: `calc(${(currentStageIndex / (stages.length - 1)) * 100}% - ${(currentStageIndex / (stages.length - 1)) * 80}px)`,
          background: 'linear-gradient(90deg, var(--primary), var(--secondary))',
          zIndex: 1,
          boxShadow: '0 0 8px rgba(139, 92, 246, 0.5)',
          transition: 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)'
        }} />

        {/* Individual Step Circles */}
        {stages.map((stage, idx) => {
          const isDone = idx < currentStageIndex || (stage.key === 'done' && isCompleted);
          const isActive = stage.key === currentStageKey && !isFailed && !isCompleted;
          
          let circleBg = '#0c0817';
          let borderStyle = '3px solid rgba(255, 255, 255, 0.08)';
          let labelColor = 'var(--text-muted)';
          let glowStyle = {};

          if (isDone) {
            circleBg = 'var(--secondary)';
            borderStyle = '3px solid var(--secondary)';
            labelColor = 'rgba(255, 255, 255, 0.95)';
            glowStyle = { boxShadow: '0 0 10px rgba(6, 182, 212, 0.2)' };
          } else if (isActive) {
            circleBg = '#0c0817';
            borderStyle = '3px solid var(--primary)';
            labelColor = 'white';
          }

          if (isFailed && stage.key === currentStageKey) {
            circleBg = 'var(--error)';
            borderStyle = '3px solid var(--error)';
            labelColor = 'var(--error)';
          }

          return (
            <div key={stage.key} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', zIndex: 2, width: '80px' }} className="stage-transition">
              <div 
                className={isActive ? 'active-ring' : ''}
                style={{
                  width: '34px', height: '34px', borderRadius: '50%', background: circleBg,
                  border: borderStyle, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  position: 'relative', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                  transform: isActive ? 'scale(1.15)' : 'scale(1)',
                  ...glowStyle
                }}
              >
                {/* Rotating ring border for active node */}
                {isActive && <div className="loading-dash" />}
                
                {isDone ? (
                  <Check style={{ width: '15px', height: '15px', color: 'white', strokeWidth: 3 }} />
                ) : isFailed && stage.key === currentStageKey ? (
                  <X style={{ width: '15px', height: '15px', color: 'white', strokeWidth: 3 }} />
                ) : (
                  <span style={{ fontSize: '11px', fontWeight: 700, color: isActive ? 'var(--primary)' : 'rgba(255,255,255,0.2)' }}>
                    {idx + 1}
                  </span>
                )}
              </div>

              {/* Stage labels */}
              <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{
                  fontSize: '11px', fontWeight: (isActive || isDone) ? 700 : 500,
                  color: labelColor, textAlign: 'center', transition: 'color 0.4s'
                }}>
                  {stage.label}
                </span>
                
                {/* Processing State text */}
                {isActive && (
                  <span style={{ fontSize: '9px', fontWeight: 600, color: 'var(--primary)', marginTop: '4px', letterSpacing: '0.5px' }}>
                    Processing...
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {/* Processing Banner */}
      {!isCompleted && !isFailed && (
        <div 
          style={{
            display: 'flex', gap: '12px', alignItems: 'center', padding: '14px 20px', borderRadius: '12px',
            background: 'rgba(139, 92, 246, 0.03)', border: '1px solid rgba(139, 92, 246, 0.12)',
            color: 'rgba(255,255,255,0.85)', fontSize: '13px', marginTop: '20px',
            animation: 'slideInUp 0.5s ease forwards'
          }}
        >
          <div style={{
            width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(139, 92, 246, 0.08)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(139, 92, 246, 0.15)'
          }}>
            <Loader2 style={{ animation: 'rotateBorder 1.5s linear infinite', width: '13px', height: '13px', color: 'var(--primary)' }} />
          </div>
          <span style={{ flex: 1, textAlign: 'left' }}>
            Please wait, analysis is actively processing. <strong>Do not navigate away or close this page.</strong>
          </span>
        </div>
      )}

      {/* Done State Success Banner */}
      {isCompleted && (
        <div 
          style={{
            display: 'flex', gap: '12px', alignItems: 'center', padding: '16px 20px', borderRadius: '12px',
            background: 'rgba(16, 185, 129, 0.04)', border: '1px solid rgba(16, 185, 129, 0.18)',
            color: '#a7f3d0', fontSize: '14px', marginTop: '20px',
            animation: 'slideInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards'
          }}
        >
          <div style={{
            width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.12)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(16, 185, 129, 0.2)'
          }}>
            <Sparkles style={{ width: '14px', height: '14px', color: 'var(--success)' }} />
          </div>
          <strong style={{ fontWeight: 600, flex: 1, textAlign: 'left' }}>
            🎉 Comparison Completed Successfully!
          </strong>
        </div>
      )}

      {/* Failure Diagnostic panel */}
      {isFailed && (
        <div style={{
          padding: '16px 20px', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.03)',
          border: '1px solid rgba(239, 68, 68, 0.15)', color: '#fecaca', fontSize: '13px', marginTop: '20px',
          textAlign: 'left', animation: 'slideInUp 0.4s ease'
        }}>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
            <AlertTriangle style={{ width: '18px', height: '18px', color: 'var(--error)' }} />
            <strong style={{ fontWeight: 700 }}>Orchestrator Stage Execution Error</strong>
          </div>
          <div style={{
            padding: '12px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.04)', fontFamily: 'monospace', fontSize: '12px',
            lineHeight: '1.5', wordBreak: 'break-word', whiteSpace: 'pre-wrap'
          }}>
            {activeJob.errors?.join('\n') || 'Unknown execution trace failure.'}
          </div>
        </div>
      )}
    </div>
  );
}
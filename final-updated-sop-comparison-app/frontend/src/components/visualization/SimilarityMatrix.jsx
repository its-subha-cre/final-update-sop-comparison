import React from 'react';
import { Percent, ShieldCheck, Trophy, Award, CheckCircle } from 'lucide-react';

export default function SimilarityMatrix({ activeJob }) {
  if (!activeJob || activeJob.status !== 'completed') return null;

  const report = activeJob.report || {};
  const bestMatch = report.best_match || {};
  const sopResults = report.sop_results || {};
  
  // Convert results dict into an array for rendering
  const resultsArray = Object.entries(sopResults).map(([key, value]) => ({
    path: key,
    ...value
  })).sort((a, b) => b.similarity_score - a.similarity_score); // Sort by highest similarity

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', margin: '24px 0' }}>
      
      {/* Top Banner: Best Match SOP */}
      {bestMatch.name && (
        <div className="glass" style={{
          padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(6, 182, 212, 0.15))',
          border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', textAlign: 'left' }}>
            <div style={{
              width: '48px', height: '48px', borderRadius: '50%', background: 'rgba(245, 158, 11, 0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(245, 158, 11, 0.3)'
            }}>
              <Trophy style={{ width: '24px', height: '24px', color: 'hsl(45, 90%, 50%)' }} />
            </div>
            <div>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--secondary)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                Most Compatible Local SOP (Best Match)
              </span>
              <h4 style={{ margin: '4px 0 0 0', fontSize: '18px', fontWeight: 700, color: 'white' }}>
                {bestMatch.name}
              </h4>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Similarity Score</span>
            <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--secondary)' }}>
              {bestMatch.similarity_score}%
            </div>
          </div>
        </div>
      )}

      {/* Comparative Leaderboard table */}
      <div className="glass" style={{ padding: '24px', textAlign: 'left' }}>
        <h3 style={{ marginTop: 0, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Award style={{ width: '22px', height: '22px', color: 'var(--primary)' }} />
          <span>Local SOP Compatibility Matrix</span>
        </h3>
        
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Rank</th>
                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Local SOP Document</th>
                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Compliance Similarity</th>
                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Necessity Score</th>
                <th style={{ padding: '12px 8px', textAlign: 'center' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {resultsArray.map((sop, index) => {
                const isBest = index === 0;
                return (
                  <tr key={sop.path} style={{
                    borderBottom: '1px solid rgba(255,255,255,0.04)',
                    background: isBest ? 'rgba(139, 92, 246, 0.03)' : 'transparent',
                    transition: 'var(--transition)'
                  }}>
                    <td style={{ padding: '16px 8px', fontWeight: 700, color: isBest ? 'var(--secondary)' : 'var(--text-muted)' }}>
                      #{index + 1}
                    </td>
                    <td style={{ padding: '16px 8px', fontWeight: 600, color: 'white' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {sop.name}
                        {isBest && (
                          <span style={{
                            fontSize: '9px', fontWeight: 700, background: 'rgba(245, 158, 11, 0.12)',
                            color: 'hsl(45, 90%, 50%)', border: '1px solid rgba(245, 158, 11, 0.3)',
                            padding: '1px 6px', borderRadius: '4px', textTransform: 'uppercase'
                          }}>
                            Best Match
                          </span>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '16px 8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontWeight: 700, width: '40px' }}>{sop.similarity_score}%</span>
                        <div style={{ width: '100px', height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px' }}>
                          <div style={{
                            width: `${sop.similarity_score}%`, height: '100%',
                            background: isBest ? 'linear-gradient(90deg, var(--primary), var(--secondary))' : 'var(--secondary)',
                            borderRadius: '2px'
                          }} />
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '16px 8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <ShieldCheck style={{ width: '16px', height: '16px', color: 'var(--success)' }} />
                        <span style={{ fontWeight: 600 }}>{sop.necessity_score}%</span>
                      </div>
                    </td>
                    <td style={{ padding: '16px 8px', textAlign: 'center' }}>
                      <span style={{
                        fontSize: '10px', fontWeight: 700,
                        color: sop.similarity_score > 70 ? 'var(--success)' : 'var(--warning)',
                        padding: '2px 8px', borderRadius: '12px',
                        background: sop.similarity_score > 70 ? 'rgba(34,197,94,0.1)' : 'rgba(245,158,11,0.1)',
                        border: `1px solid ${sop.similarity_score > 70 ? 'rgba(34,197,94,0.2)' : 'rgba(245,158,11,0.2)'}`
                      }}>
                        {sop.similarity_score > 70 ? 'Highly Aligned' : 'Review Needed'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
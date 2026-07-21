import React, { useState, useEffect } from 'react';
import { Trash2, RefreshCw, Loader, AlertTriangle, CheckSquare, Square } from 'lucide-react';
import { apiClient } from '../../api/client';

export default function SOPListManager({ refreshTrigger, onDeleted }) {
  const [globalSops, setGlobalSops] = useState([]);
  const [localSops, setLocalSops] = useState([]);
  const [selectedSops, setSelectedSops] = useState([]); // Array of { filename, type }
  const [loading, setLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState('');

  const fetchSops = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await apiClient.getUploadedSops();
      if (res.success) {
        setGlobalSops(res.global || []);
        setLocalSops(res.local || []);
      }
    } catch (err) {
      setError('Failed to fetch uploaded SOP list.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSops();
  }, [refreshTrigger]);

  const handleToggleSelect = (filename, type) => {
    const isSelected = selectedSops.some(s => s.filename === filename && s.type === type);
    if (isSelected) {
      setSelectedSops(selectedSops.filter(s => !(s.filename === filename && s.type === type)));
    } else {
      setSelectedSops([...selectedSops, { filename, type }]);
    }
  };

  const handleSelectAll = (type) => {
    const list = type === 'global' ? globalSops : localSops;
    const allSelectedFromList = list.every(item => 
      selectedSops.some(s => s.filename === item.name && s.type === type)
    );

    if (allSelectedFromList) {
      // Deselect all of this type
      setSelectedSops(selectedSops.filter(s => s.type !== type));
    } else {
      // Select all of this type
      const newSelections = list.map(item => ({ filename: item.name, type }));
      const cleanSelections = selectedSops.filter(s => s.type !== type);
      setSelectedSops([...cleanSelections, ...newSelections]);
    }
  };

  const handleDeleteTrigger = () => {
    if (selectedSops.length === 0) return;
    setError('');
    setResult('');
    setShowConfirm(true);
  };

  const executeDelete = async () => {
    setDeleteLoading(true);
    try {
      const sopsPayload = selectedSops.map(s => ({
        filename: s.filename,
        type: s.type
      }));
      const res = await apiClient.deleteSops(sopsPayload);
      if (res.success) {
        setResult(`Successfully deleted ${res.deleted_count} SOP(s). Purged ${res.nodes_deleted} graph nodes.`);
        setSelectedSops([]);
        setShowConfirm(false);
        fetchSops();
        if (onDeleted) {
          onDeleted();
        }
      } else {
        setError(res.errors?.join(', ') || 'Failed to complete SOP deletion.');
      }
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'An error occurred during deletion.');
    } finally {
      setDeleteLoading(false);
    }
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  const totalSelected = selectedSops.length;

  return (
    <div className="glass" style={{ padding: '24px', textAlign: 'left', position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: 0 }}>SOP Repository Management</h3>
        <button 
          onClick={fetchSops}
          disabled={loading}
          className="icon-button"
          style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          {loading ? <Loader className="spin" style={{ width: '16px', height: '16px' }} /> : <RefreshCw style={{ width: '16px', height: '16px' }} />}
          Reload Repository
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Global SOP list */}
        <div style={{ borderRight: '1px solid rgba(255,255,255,0.05)', paddingRight: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--primary)' }}>Global SOP File</span>
            {globalSops.length > 0 && (
              <button 
                onClick={() => handleSelectAll('global')}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '11px', cursor: 'pointer' }}
              >
                Toggle Select All
              </button>
            )}
          </div>
          {globalSops.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', margin: '20px 0' }}>No Global SOP files uploaded.</p>
          ) : (
            <div style={{ maxHeight: '180px', overflowY: 'auto' }}>
              {globalSops.map((sop) => {
                const isSelected = selectedSops.some(s => s.filename === sop.name && s.type === 'global');
                return (
                  <div 
                    key={sop.name}
                    onClick={() => handleToggleSelect(sop.name, 'global')}
                    style={{ 
                      display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 12px',
                      background: isSelected ? 'rgba(0, 168, 204, 0.1)' : 'rgba(255,255,255,0.02)',
                      border: isSelected ? '1px solid rgba(0, 168, 204, 0.3)' : '1px solid rgba(255,255,255,0.05)',
                      borderRadius: '8px', marginBottom: '8px', cursor: 'pointer', transition: 'all 0.2s'
                    }}
                  >
                    {isSelected ? <CheckSquare style={{ width: '16px', height: '16px', color: 'var(--primary)' }} /> : <Square style={{ width: '16px', height: '16px', color: 'var(--text-muted)' }} />}
                    <div style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span style={{ fontSize: '13px' }}>{sop.name}</span>
                    </div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{formatSize(sop.size_bytes)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Local SOP list */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--secondary)' }}>Local / Site-Specific SOPs</span>
            {localSops.length > 0 && (
              <button 
                onClick={() => handleSelectAll('local')}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '11px', cursor: 'pointer' }}
              >
                Toggle Select All
              </button>
            )}
          </div>
          {localSops.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', margin: '20px 0' }}>No Local SOP files uploaded.</p>
          ) : (
            <div style={{ maxHeight: '180px', overflowY: 'auto' }}>
              {localSops.map((sop) => {
                const isSelected = selectedSops.some(s => s.filename === sop.name && s.type === 'local');
                return (
                  <div 
                    key={sop.name}
                    onClick={() => handleToggleSelect(sop.name, 'local')}
                    style={{ 
                      display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 12px',
                      background: isSelected ? 'rgba(0, 168, 204, 0.1)' : 'rgba(255,255,255,0.02)',
                      border: isSelected ? '1px solid rgba(0, 168, 204, 0.3)' : '1px solid rgba(255,255,255,0.05)',
                      borderRadius: '8px', marginBottom: '8px', cursor: 'pointer', transition: 'all 0.2s'
                    }}
                  >
                    {isSelected ? <CheckSquare style={{ width: '16px', height: '16px', color: 'var(--primary)' }} /> : <Square style={{ width: '16px', height: '16px', color: 'var(--text-muted)' }} />}
                    <div style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span style={{ fontSize: '13px' }}>{sop.name}</span>
                    </div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{formatSize(sop.size_bytes)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {error && (
        <p style={{ color: 'var(--error)', fontSize: '13px', marginTop: '16px', marginBottom: 0 }}>{error}</p>
      )}

      {result && (
        <p style={{ color: '#4ade80', fontSize: '13px', marginTop: '16px', marginBottom: 0 }}>{result}</p>
      )}

      {totalSelected > 0 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '16px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Selected <strong>{totalSelected}</strong> file(s) for deletion.
          </span>
          <button 
            onClick={handleDeleteTrigger}
            className="glow-button"
            style={{ 
              display: 'flex', alignItems: 'center', gap: '8px', 
              padding: '10px 20px', background: 'rgba(239, 68, 68, 0.2)', 
              border: '1px solid rgba(239, 68, 68, 0.4)', color: '#fca5a5',
              cursor: 'pointer'
            }}
          >
            <Trash2 style={{ width: '16px', height: '16px' }} />
            Permanently Delete Selected
          </button>
        </div>
      )}

      {/* Confirmation Dialog Overlay */}
      {showConfirm && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)', display: 'flex', justifyContent: 'center',
          alignItems: 'flex-start', zIndex: 1000, backdropFilter: 'blur(4px)',
          overflowY: 'auto', padding: '40px 20px'
        }}>
          <div className="glass" style={{ width: '100%', maxWidth: '480px', padding: '24px', textAlign: 'left', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <AlertTriangle style={{ width: '32px', height: '32px', color: '#f87171' }} />
              <h3 style={{ margin: 0, color: '#f87171' }}>Delete SOP?</h3>
            </div>

            <p style={{ fontSize: '13px', lineHeight: '1.5', margin: '0 0 16px 0' }}>
              You are about to permanently delete <strong>{totalSelected}</strong> SOP document(s):
            </p>

            <div style={{ 
              background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', 
              maxHeight: '120px', overflowY: 'auto', marginBottom: '20px', border: '1px solid rgba(255,255,255,0.05)' 
            }}>
              {selectedSops.map(s => (
                <div key={`${s.type}-${s.filename}`} style={{ fontSize: '12px', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  • <span style={{ color: 'var(--text-muted)' }}>[{s.type.toUpperCase()}]</span> {s.filename}
                </div>
              ))}
            </div>

            <p style={{ fontSize: '13px', fontWeight: 600, marginBottom: '12px' }}>This action will permanently remove:</p>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '24px' }}>
              <div>✓ Uploaded file</div>
              <div>✓ Neo4j graph</div>
              <div>✓ Chunks</div>
              <div>✓ Embeddings</div>
              <div>✓ Relationships</div>
              <div>✓ Processing metadata</div>
              <div>✓ Cached retrieval data</div>
            </div>

            <p style={{ fontSize: '11px', color: '#fca5a5', marginBottom: '24px', fontStyle: 'italic' }}>
              * This action cannot be undone and will update all statistics immediately.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button 
                onClick={() => setShowConfirm(false)}
                disabled={deleteLoading}
                style={{ 
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', 
                  borderRadius: '6px', padding: '8px 16px', color: 'white', cursor: 'pointer' 
                }}
              >
                Cancel
              </button>
              <button 
                onClick={executeDelete}
                disabled={deleteLoading}
                style={{ 
                  background: '#ef4444', border: 'none', borderRadius: '6px', 
                  padding: '8px 16px', color: 'white', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '8px'
                }}
              >
                {deleteLoading ? (
                  <>
                    <Loader className="spin" style={{ width: '14px', height: '14px' }} />
                    Deleting...
                  </>
                ) : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

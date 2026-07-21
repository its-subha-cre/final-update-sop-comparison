import React, { useState } from 'react';
import { ArrowRight, Play } from 'lucide-react';
import UploadZone from './UploadZone';
import { apiClient } from '../../api/client';

export default function SOPUploadManager({ onJobTriggered }) {
  const [globalFiles, setGlobalFiles] = useState([]);
  const [localFiles, setLocalFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRunComparison = async () => {
    if (globalFiles.length === 0 || localFiles.length === 0) {
      setError('Please upload at least one file in both Global and Local slots.');
      return;
    }
    
    setError('');
    setLoading(true);
    try {
      // 1. Upload global files
      const globalUpload = await apiClient.uploadFiles('global', globalFiles);
      // 2. Upload local files
      const localUpload = await apiClient.uploadFiles('local', localFiles);

      if (globalUpload.success && localUpload.success) {
        const globalPath = globalUpload.files[0].saved_path;
        const localPaths = localUpload.files.map(f => f.saved_path);
        
        // 3. Trigger comparison job
        const runRes = await apiClient.runComparison(globalPath, localPaths);
        if (runRes.success) {
          onJobTriggered(runRes.job_id);
        }
      }
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'Failed to complete files upload & pipeline trigger.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass" style={{ padding: '24px', textAlign: 'left' }}>
      <h3 style={{ marginTop: 0, marginBottom: '8px' }}>SOP Batch Ingestion Slots</h3>
      <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '24px' }}>
        Separate upload zones for the canonical Global SOP and Site-Specific (Local) SOPs. Multiple files are supported.
      </p>

      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        <UploadZone 
          label="Global SOP Slot" 
          files={globalFiles} 
          setFiles={setGlobalFiles} 
        />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <ArrowRight style={{ width: '24px', height: '24px', color: 'var(--text-muted)' }} />
        </div>
        <UploadZone 
          label="Local/Site SOPs Slot" 
          files={localFiles} 
          setFiles={setLocalFiles} 
        />
      </div>

      {error && (
        <p style={{ color: 'var(--error)', fontSize: '13px', margin: '16px 0 0 0' }}>{error}</p>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '24px' }}>
        <button 
          onClick={handleRunComparison}
          disabled={loading || globalFiles.length === 0 || localFiles.length === 0}
          className="glow-button"
          style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 24px' }}
        >
          <Play style={{ width: '16px', height: '16px' }} />
          {loading ? 'Processing Uploads...' : 'Initiate Multi-Agent Compare'}
        </button>
      </div>
    </div>
  );
}

import React, { useRef, useState } from 'react';
import { Upload, FileText, X } from 'lucide-react';

export default function UploadZone({ label, files, setFiles, accept = ".pdf,.docx" }) {
  const fileInputRef = useRef(null);
  const [isDragActive, setIsDragActive] = useState(false);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(Array.from(e.target.files));
    }
  };

  const addFiles = (newFiles) => {
    const validFiles = newFiles.filter(file => {
      const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
      return accept.includes(ext);
    });
    setFiles((prev) => [...prev, ...validFiles]);
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <label style={{ fontWeight: 600, fontSize: '14px', color: '#a7a3d0' }}>{label}</label>
      <div 
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: '2px dashed rgba(255,255,255,0.12)',
          borderRadius: '12px',
          padding: '24px',
          textAlign: 'center',
          background: isDragActive ? 'rgba(140, 80, 255, 0.08)' : 'rgba(255,255,255,0.02)',
          borderColor: isDragActive ? 'var(--primary)' : 'rgba(255,255,255,0.12)',
          cursor: 'pointer',
          transition: 'var(--transition)'
        }}
      >
        <input 
          ref={fileInputRef}
          type="file"
          multiple
          accept={accept}
          onChange={handleChange}
          style={{ display: 'none' }}
        />
        <Upload style={{ width: '32px', height: '32px', margin: '0 auto 8px auto', color: 'var(--primary)' }} />
        <p style={{ margin: 0, fontSize: '13px', fontWeight: 500 }}>
          Drag & Drop or <span style={{ color: 'var(--secondary)' }}>Browse</span>
        </p>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Supports PDF, DOCX</span>
      </div>

      {files.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }}>
          {files.map((file, idx) => (
            <div key={idx} className="glass" style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px',
              borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', background: 'rgba(255,255,255,0.01)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                <FileText style={{ width: '16px', height: '16px', color: 'var(--secondary)', flexShrink: 0 }} />
                <span style={{ fontSize: '12px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {file.name}
                </span>
              </div>
              <button 
                type="button" 
                onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--error)' }}
              >
                <X style={{ width: '14px', height: '14px' }} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

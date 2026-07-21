import React, { useState, useEffect } from 'react';
import { Shield, CheckCircle, AlertTriangle, Loader2, Eye, EyeOff } from 'lucide-react';
import { apiClient } from '../../api/client';

export default function LLMSetupWizard({ onCompleted }) {
  const [provider, setProvider] = useState('gemini');
  const [model, setModel] = useState('gemini-2.5-flash');
  const [apiKey, setApiKey] = useState('');
  const [azureEndpoint, setAzureEndpoint] = useState('');
  const [ollamaHost, setOllamaHost] = useState('http://localhost:11434');
  const [testState, setTestState] = useState('idle'); // idle, testing, success, error
  const [feedbackMsg, setFeedbackMsg] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);

  const modelOptions = {
    gemini: ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-3.5-flash', 'gemini-3.5-pro'],
    openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
    anthropic: ['claude-3-5-sonnet-20240620', 'claude-3-haiku-20240307', 'claude-3-opus-20240229'],
    deepseek: ['deepseek-chat', 'deepseek-coder'],
    azure: ['gpt-4o', 'gpt-4o-mini', 'gpt-35-turbo'],
    ollama: ['llama3', 'mistral', 'phi3', 'gemma2'],
    groq: ['llama-3.1-8b-instant', 'llama-3.1-70b-versatile', 'llama-3.3-70b-versatile', 'mixtral-8x7b-32768', 'gemma2-9b-it']
  };

  useEffect(() => {
    // Automatically select the default model when provider shifts
    setModel(modelOptions[provider][0]);
    setTestState('idle');
    setFeedbackMsg('');
  }, [provider]);

  const handleTestConnection = async () => {
    if (provider !== 'ollama' && !apiKey) {
      setTestState('error');
      setFeedbackMsg('API Key is required to test connection.');
      return;
    }
    if (provider === 'azure' && !azureEndpoint) {
      setTestState('error');
      setFeedbackMsg('Azure Endpoint URL is required for Azure OpenAI connection.');
      return;
    }
    if (provider === 'ollama' && !ollamaHost) {
      setTestState('error');
      setFeedbackMsg('Ollama Host URL is required.');
      return;
    }
    setTestState('testing');
    setFeedbackMsg('');
    try {
      const res = await apiClient.testConfig(provider, model, apiKey, azureEndpoint, ollamaHost);
      if (res.success) {
        setTestState('success');
        setFeedbackMsg(res.message || 'Connection test successful.');
      } else {
        setTestState('error');
        setFeedbackMsg(res.message || 'Connection failed.');
      }
    } catch (err) {
      setTestState('error');
      setFeedbackMsg(err.response?.data?.message || err.message || 'An error occurred.');
    }
  };

  const handleSaveConfig = async () => {
    setSaveLoading(true);
    try {
      const res = await apiClient.saveConfig(provider, model, apiKey, azureEndpoint, ollamaHost);
      if (res.success) {
        onCompleted();
      } else {
        setTestState('error');
        setFeedbackMsg(res.message || 'Failed to save configuration.');
      }
    } catch (err) {
      setTestState('error');
      setFeedbackMsg(err.response?.data?.message || err.message || 'Failed to save config.');
    } finally {
      setSaveLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh'
    }}>
      <div className="glass" style={{
        padding: '40px', width: '100%', maxWidth: '500px', textAlign: 'left',
        border: '1px solid rgba(255,255,255,0.1)'
      }}>
        <h2 style={{ marginTop: 0 }} className="gradient-text">LLM Engine Setup Wizard</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '24px', fontSize: '14px' }}>
          Welcome! Let's configure your LLM Provider for the semantic multi-agent pipeline.
          This will update the configuration in `backend/.env` automatically.
        </p>

        {/* Provider Selection */}
        <div style={{ marginBottom: '18px' }}>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, marginBottom: '6px' }}>
            Provider
          </label>
          <select 
            value={provider} 
            onChange={(e) => setProvider(e.target.value)}
            style={{
              width: '100%', padding: '12px', borderRadius: '8px', 
              background: '#13112b', color: 'white', border: '1px solid var(--card-border)',
              outline: 'none'
            }}
          >
            <option style={{ background: '#13112b', color: 'white' }} value="gemini">Google Gemini</option>
            <option style={{ background: '#13112b', color: 'white' }} value="openai">OpenAI</option>
            <option style={{ background: '#13112b', color: 'white' }} value="anthropic">Anthropic</option>
            <option style={{ background: '#13112b', color: 'white' }} value="deepseek">DeepSeek AI</option>
            <option style={{ background: '#13112b', color: 'white' }} value="azure">Azure OpenAI</option>
            <option style={{ background: '#13112b', color: 'white' }} value="ollama">Ollama (Local)</option>
            <option style={{ background: '#13112b', color: 'white' }} value="groq">Groq Cloud (Fast LLM)</option>
          </select>
        </div>

        {/* Model Selection */}
        <div style={{ marginBottom: '18px' }}>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, marginBottom: '6px' }}>
            Model / Deployment Name
          </label>
          <select 
            value={model} 
            onChange={(e) => setModel(e.target.value)}
            style={{
              width: '100%', padding: '12px', borderRadius: '8px', 
              background: '#13112b', color: 'white', border: '1px solid var(--card-border)',
              outline: 'none'
            }}
          >
            {modelOptions[provider].map((m) => (
              <option key={m} style={{ background: '#13112b', color: 'white' }} value={m}>{m}</option>
            ))}
          </select>
        </div>

        {/* Azure Endpoint Input (Rendered conditionally for Azure OpenAI) */}
        {provider === 'azure' && (
          <div style={{ marginBottom: '18px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, marginBottom: '6px' }}>
              Azure Endpoint URL
            </label>
            <input 
              type="text"
              placeholder="https://YOUR_RESOURCE.openai.azure.com/"
              value={azureEndpoint}
              onChange={(e) => {
                setAzureEndpoint(e.target.value);
                setTestState('idle');
                setFeedbackMsg('');
              }}
              style={{
                width: '100%', padding: '12px', borderRadius: '8px', boxSizing: 'border-box',
                background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid var(--card-border)'
              }}
            />
          </div>
        )}

        {/* Ollama Host Input (Rendered conditionally for local Ollama) */}
        {provider === 'ollama' && (
          <div style={{ marginBottom: '18px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, marginBottom: '6px' }}>
              Ollama Host URL
            </label>
            <input 
              type="text"
              placeholder="http://localhost:11434"
              value={ollamaHost}
              onChange={(e) => {
                setOllamaHost(e.target.value);
                setTestState('idle');
                setFeedbackMsg('');
              }}
              style={{
                width: '100%', padding: '12px', borderRadius: '8px', boxSizing: 'border-box',
                background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid var(--card-border)'
              }}
            />
          </div>
        )}

        {/* Masked API Key Input (Bypassed/hidden for local Ollama) */}
        {provider !== 'ollama' && (
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, marginBottom: '6px' }}>
              API Key
            </label>
            <div style={{ position: 'relative' }}>
              <input 
                type={showApiKey ? "text" : "password"}
                placeholder={`Enter ${provider.toUpperCase()} API Key`}
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setTestState('idle');
                  setFeedbackMsg('');
                }}
                style={{
                  width: '100%', padding: '12px 40px 12px 12px', borderRadius: '8px', boxSizing: 'border-box',
                  background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid var(--card-border)'
                }}
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                style={{
                  position: 'absolute', right: '12px', top: '12px', background: 'none', border: 'none',
                  cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center',
                  padding: 0, outline: 'none'
                }}
              >
                {showApiKey ? (
                  <EyeOff style={{ width: '18px', height: '18px' }} />
                ) : (
                  <Eye style={{ width: '18px', height: '18px' }} />
                )}
              </button>
            </div>
          </div>
        )}

        {/* Feedback Message */}
        {feedbackMsg && (
          <div style={{
            display: 'flex', gap: '8px', alignItems: 'center', padding: '12px', borderRadius: '8px', 
            marginBottom: '20px', fontSize: '13px',
            background: testState === 'success' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${testState === 'success' ? 'var(--success)' : 'var(--error)'}`,
            color: testState === 'success' ? '#a7f3d0' : '#fecaca',
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap'
          }}>
            {testState === 'success' ? <CheckCircle style={{ width: '18px', height: '18px', flexShrink: 0 }} /> 
                                    : <AlertTriangle style={{ width: '18px', height: '18px', flexShrink: 0 }} />}
            <span>{feedbackMsg}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            type="button" 
            onClick={handleTestConnection}
            disabled={testState === 'testing'}
            style={{
              flex: 1, padding: '12px', borderRadius: '8px', cursor: 'pointer', fontWeight: 600,
              background: 'transparent', color: 'white', border: '1px solid rgba(255,255,255,0.2)'
            }}
          >
            {testState === 'testing' ? (
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <Loader2 style={{ animation: 'spin 1s linear infinite', width: '18px', height: '18px' }} />
                Testing...
              </span>
            ) : 'Test Connection'}
          </button>
          
          <button 
            type="button"
            className="glow-button"
            onClick={handleSaveConfig}
            disabled={testState !== 'success' || saveLoading}
            style={{ flex: 1, padding: '12px', borderRadius: '8px' }}
          >
            {saveLoading ? 'Saving...' : 'Save to .env'}
          </button>
        </div>
      </div>
    </div>
  );
}

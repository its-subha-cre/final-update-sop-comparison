import axios from 'axios';

// Configure basic API endpoints
const API_BASE = 'http://localhost:5000/api';

export const apiClient = {
  // Config Setup Wizard routes
  getConfigStatus: async () => {
    const res = await axios.get(`${API_BASE}/config/status`);
    return res.data;
  },
  
  testConfig: async (provider, model, apiKey, azureEndpoint, ollamaHost) => {
    const res = await axios.post(`${API_BASE}/config/test`, { provider, model, apiKey, azureEndpoint, ollamaHost });
    return res.data;
  },
  
  saveConfig: async (provider, model, apiKey, azureEndpoint, ollamaHost) => {
    const res = await axios.post(`${API_BASE}/config/save`, { provider, model, apiKey, azureEndpoint, ollamaHost });
    return res.data;
  },

  // Upload slots routes
  uploadFiles: async (slot, files) => {
    const formData = new FormData();
    formData.append('slot', slot);
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    const res = await axios.post(`${API_BASE}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return res.data;
  },

  // Run pipeline
  runComparison: async (globalFile, localFiles) => {
    const res = await axios.post(`${API_BASE}/compare/run`, { globalFile, localFiles });
    return res.data;
  },

  // Check job progress
  getJobStatus: async (jobId) => {
    const res = await axios.get(`${API_BASE}/compare/status/${jobId}`);
    return res.data;
  },

  // Chat Assistant route
  sendChatMessage: async (message, jobId, history = []) => {
    const res = await axios.post(`${API_BASE}/chat`, { message, jobId, history });
    return res.data;
  },

  getGraphData: async () => {
    const res = await axios.get(`${API_BASE}/graph/data`);
    return res.data;
  },

  getNeo4jHealth: async () => {
    const res = await axios.get(`${API_BASE}/health/neo4j`);
    return res.data;
  },

  getUploadedSops: async () => {
    const res = await axios.get(`${API_BASE}/sops`);
    return res.data;
  },

  deleteSops: async (sops) => {
    const res = await axios.post(`${API_BASE}/sops/delete`, { sops });
    return res.data;
  }
};

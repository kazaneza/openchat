import axios from 'axios';
import { Organization } from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const organizationApi = {
  getAll: async () => {
    const response = await api.get('/organizations');
    return response.data.organizations;
  },

  create: async (name: string, prompt: string) => {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('prompt', prompt);
    
    const response = await api.post('/organizations', formData);
    return response.data.organization;
  },

  getById: async (id: string) => {
    const response = await api.get(`/organizations/${id}`);
    return response.data.organization;
  },

  uploadDocuments: async (orgId: string, files: File[]) => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    
    const response = await api.post(`/organizations/${orgId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  chat: async (orgId: string, message: string) => {
    const formData = new FormData();
    formData.append('message', message);
    
    const response = await api.post(`/organizations/${orgId}/chat`, formData);
    return response.data;
  },

  delete: async (id: string) => {
    const response = await api.delete(`/organizations/${id}`);
    return response.data;
  },
};
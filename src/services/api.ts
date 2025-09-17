import axios from 'axios';
import { Organization, User } from '../types';

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

  deleteDocument: async (orgId: string, docId: string) => {
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    const formData = new FormData();
    formData.append('user_id', currentUser.id);
    
    const response = await api.delete(`/organizations/${orgId}/documents/${docId}`, {
      data: formData
    });
    return response.data;
  },
  uploadDocuments: async (orgId: string, files: File[]) => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    
    // Add user ID for authentication
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    console.log('Current user for upload:', currentUser);
    if (currentUser.id) {
      formData.append('user_id', currentUser.id);
    }
    
    console.log('Uploading to org:', orgId);
    console.log('Files to upload:', files.map(f => f.name));
    
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
    
    // Add user ID for authentication
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    if (currentUser.id) {
      formData.append('user_id', currentUser.id);
    }
    
    const response = await api.post(`/organizations/${orgId}/chat`, formData);
    return response.data;
  },
};

export const adminApi = {
  getOrganizations: async () => {
    const response = await api.get('/admin/organizations');
    return response.data.organizations;
  },

  createOrganization: async (name: string, prompt: string) => {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('prompt', prompt);
    
    const response = await api.post('/admin/organizations', formData);
    return response.data.organization;
  },

  deleteOrganization: async (id: string) => {
    const response = await api.delete(`/admin/organizations/${id}`);
    return response.data;
  },

  createUser: async (userData: Omit<User, 'id' | 'created_at'>) => {
    const formData = new FormData();
    formData.append('email', userData.email);
    formData.append('password', userData.password);
    formData.append('organization_id', userData.organization_id);
    formData.append('role', userData.role);
    formData.append('must_change_password', userData.must_change_password?.toString() || 'true');
    
    const response = await api.post('/admin/users', formData);
    return response.data.user;
  },

  deleteUser: async (id: string) => {
    console.log('Deleting user with ID:', id);
    const response = await api.delete(`/admin/users/${id}`);
    return response.data;
  },

  authenticateUser: async (email: string, password: string) => {
    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);
    
    const response = await api.post('/auth/login', formData);
    return response.data;
  },

  changePassword: async (userId: string, currentPassword: string, newPassword: string) => {
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('current_password', currentPassword);
    formData.append('new_password', newPassword);
    
    const response = await api.post('/auth/change-password', formData);
    return response.data;
  },
};
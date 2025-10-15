import axios from 'axios';
import { Organization, User } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://138.68.20.49:8000/api';

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

  chat: async (orgId: string, message: string, conversationId?: string) => {
    const formData = new FormData();
    formData.append('message', message);

    // Add user ID for authentication
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    if (currentUser.id) {
      formData.append('user_id', currentUser.id);
    }

    // Add conversation ID if provided
    if (conversationId) {
      formData.append('conversation_id', conversationId);
    }

    const response = await api.post(`/organizations/${orgId}/chat`, formData);
    return response.data;
  },
};

export const conversationApi = {
  getUserConversations: async (userId: string, orgId: string) => {
    const response = await api.get(`/conversations/${userId}`, {
      params: { org_id: orgId }
    });
    return response.data.conversations;
  },

  getConversationMessages: async (conversationId: string, userId: string) => {
    const response = await api.get(`/conversations/${conversationId}/messages`, {
      params: { user_id: userId }
    });
    return response.data;
  },

  deleteConversation: async (conversationId: string, userId: string) => {
    const formData = new FormData();
    formData.append('user_id', userId);

    const response = await api.delete(`/conversations/${conversationId}`, {
      data: formData
    });
    return response.data;
  },

  updateConversationTitle: async (conversationId: string, userId: string, title: string) => {
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('title', title);

    const response = await api.put(`/conversations/${conversationId}/title`, formData);
    return response.data.conversation;
  },
};

export const feedbackApi = {
  submitThumbsUp: async (
    messageId: string,
    conversationId: string,
    userId: string,
    orgId: string,
    query: string,
    response: string,
    metadata: any
  ) => {
    const formData = new FormData();
    formData.append('message_id', messageId);
    formData.append('conversation_id', conversationId);
    formData.append('user_id', userId);
    formData.append('organization_id', orgId);
    formData.append('query', query);
    formData.append('response', response);
    formData.append('metadata', JSON.stringify(metadata));

    const result = await api.post('/feedback/thumbs-up', formData);
    return result.data;
  },

  submitThumbsDown: async (
    messageId: string,
    conversationId: string,
    userId: string,
    orgId: string,
    query: string,
    response: string,
    comment: string,
    metadata: any
  ) => {
    const formData = new FormData();
    formData.append('message_id', messageId);
    formData.append('conversation_id', conversationId);
    formData.append('user_id', userId);
    formData.append('organization_id', orgId);
    formData.append('query', query);
    formData.append('response', response);
    formData.append('comment', comment);
    formData.append('metadata', JSON.stringify(metadata));

    const result = await api.post('/feedback/thumbs-down', formData);
    return result.data;
  },

  submitCorrection: async (
    messageId: string,
    conversationId: string,
    userId: string,
    orgId: string,
    query: string,
    response: string,
    correction: string,
    metadata: any
  ) => {
    const formData = new FormData();
    formData.append('message_id', messageId);
    formData.append('conversation_id', conversationId);
    formData.append('user_id', userId);
    formData.append('organization_id', orgId);
    formData.append('query', query);
    formData.append('response', response);
    formData.append('correction', correction);
    formData.append('metadata', JSON.stringify(metadata));

    const result = await api.post('/feedback/correction', formData);
    return result.data;
  },

  getTodayAnalytics: async () => {
    const response = await api.get('/analytics/today');
    return response.data;
  },

  getAnalyticsRange: async (days: number = 7) => {
    const response = await api.get(`/analytics/range?days=${days}`);
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
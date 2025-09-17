import React, { useState } from 'react';
import { Settings, Copy, Check, Save, Key, MessageSquare, Lightbulb, RefreshCw } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { organizationApi } from '../services/api';

const OrganizationSettings: React.FC = () => {
  const { currentOrganization } = useAuth();
  const [prompt, setPrompt] = useState(currentOrganization?.prompt || '');
  const [saving, setSaving] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [showPromptTemplates, setShowPromptTemplates] = useState(false);

  const promptTemplates = {
    "document_assistant": "General document Q&A assistant",
    "customer_support": "Customer service focused assistant", 
    "knowledge_base": "Knowledge base search assistant",
    "general_assistant": "Platform-aware general assistant"
  };

  const defaultPrompts = {
    "document_assistant": `You are a helpful AI assistant specialized in answering questions based on document content. 

Your capabilities:
- Answer questions using information from uploaded documents
- Provide accurate, contextual responses based on document content
- Handle both document-specific and general queries
- Maintain a professional and helpful tone

Guidelines:
- When answering from documents, cite the source document name
- If information isn't in the documents, clearly state this
- For general questions outside document scope, provide helpful general responses
- Always be polite and professional
- If unsure, ask for clarification rather than guessing`,

    "customer_support": `You are a customer support AI assistant.

Your mission:
- Provide excellent customer service
- Answer questions based on company documentation
- Escalate complex issues appropriately
- Maintain a helpful and empathetic tone

Guidelines:
- Always greet customers warmly
- Use document content to provide accurate information
- If you can't find the answer in documents, offer to connect them with human support
- Be patient and understanding with customer concerns
- Provide step-by-step guidance when needed`,

    "knowledge_base": `You are a knowledge base assistant designed to help users find information quickly.

Your purpose:
- Search through organizational documents efficiently
- Provide comprehensive answers with source citations
- Organize information in a clear, structured way
- Help users discover related information

Best practices:
- Structure responses with clear headings and bullet points
- Include relevant document sections and page references when available
- Suggest related topics or documents that might be helpful
- Summarize complex information in digestible formats`,

    "general_assistant": `You are a helpful AI assistant for the OpenChat platform.

Your role:
- Assist users with both document-related and general questions
- Provide accurate, helpful information
- Maintain a friendly and professional demeanor
- Guide users on how to use the platform effectively

Capabilities:
- Answer questions about uploaded documents using RAG (Retrieval-Augmented Generation)
- Provide general knowledge and assistance
- Help with platform navigation and features
- Offer suggestions for better document organization`
  };

  const handleCopyEndpoint = async () => {
    if (!currentOrganization) return;
    
    const endpoint = `http://localhost:8000/chat/${currentOrganization.id}`;
    try {
      await navigator.clipboard.writeText(endpoint);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (error) {
      console.error('Failed to copy endpoint:', error);
    }
  };

  const handleSavePrompt = async () => {
    if (!currentOrganization) return;
    
    setSaving(true);
    try {
      // In a real implementation, you'd call an API to update the prompt
      // For now, we'll just simulate the save
      await new Promise(resolve => setTimeout(resolve, 1000));
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save prompt:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleUseTemplate = (templateKey: string) => {
    setPrompt(defaultPrompts[templateKey]);
    setShowPromptTemplates(false);
  };

  if (!currentOrganization) {
    return <div>No organization selected</div>;
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Organization Settings</h1>
        <p className="text-gray-600 dark:text-gray-300">Manage your organization's chat configuration</p>
      </div>

      {/* Organization Info */}
      <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700 mb-6">
        <div className="flex items-center space-x-4 mb-4">
          <div className="w-12 h-12 bg-gradient-to-r from-deep-blue to-slate-gray rounded-xl flex items-center justify-center">
            <Settings className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">{currentOrganization.name}</h2>
            <p className="text-gray-600 dark:text-gray-300">{currentOrganization.document_count} documents uploaded</p>
          </div>
        </div>
      </div>

      {/* Chat Endpoint */}
      <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <Key className="w-5 h-5 mr-2" />
            Chat Endpoint
          </h3>
          {copySuccess && (
            <div className="flex items-center text-green-600">
              <Check className="w-4 h-4 mr-1" />
              <span className="text-sm">Copied!</span>
            </div>
          )}
        </div>
        
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between">
            <code className="text-sm text-gray-700 dark:text-gray-300 break-all">
              POST http://localhost:8000/chat/{currentOrganization.id}
            </code>
            <button
              onClick={handleCopyEndpoint}
              className="ml-4 p-2 text-gray-500 dark:text-gray-400 hover:text-deep-blue dark:hover:text-blue-400 hover:bg-slate-50 dark:hover:bg-gray-600 rounded-lg transition-all duration-200"
              title="Copy endpoint URL"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        <div className="text-sm text-gray-600 dark:text-gray-400">
          <p className="mb-2"><strong>Usage:</strong> Send POST requests with form data containing a "message" field.</p>
          <p><strong>Example:</strong> curl -X POST -d "message=Hello" http://localhost:8000/chat/{currentOrganization.id}</p>
        </div>
      </div>

      {/* System Prompt */}
      <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <MessageSquare className="w-5 h-5 mr-2" />
            System Prompt
          </h3>
          <div className="flex space-x-2">
            <button
              onClick={() => setShowPromptTemplates(!showPromptTemplates)}
              className="flex items-center px-3 py-2 text-sm bg-slate-100 dark:bg-gray-700 text-slate-700 dark:text-gray-300 rounded-lg hover:bg-slate-200 dark:hover:bg-gray-600 transition-all duration-200"
            >
              <Lightbulb className="w-4 h-4 mr-1" />
              Templates
            </button>
            {saveSuccess && (
              <div className="flex items-center text-green-600">
                <Check className="w-4 h-4 mr-1" />
                <span className="text-sm">Saved!</span>
              </div>
            )}
          </div>
        </div>
        
        {/* Template Selection */}
        {showPromptTemplates && (
          <div className="mb-4 p-4 bg-slate-50 dark:bg-gray-700 rounded-lg">
            <h4 className="font-medium text-gray-900 dark:text-white mb-3">Choose a Template:</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Object.entries(promptTemplates).map(([key, description]) => (
                <button
                  key={key}
                  onClick={() => handleUseTemplate(key)}
                  className="p-3 text-left bg-white dark:bg-gray-800 rounded-lg hover:bg-slate-50 dark:hover:bg-gray-600 transition-colors border border-slate-200 dark:border-gray-600"
                >
                  <div className="font-medium text-gray-900 dark:text-white capitalize">
                    {key.replace('_', ' ')}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {description}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
        
        <p className="text-gray-600 dark:text-gray-300 mb-4">
          Configure how your AI assistant behaves when responding to chat messages.
        </p>
        <div className="space-y-4">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-deep-blue dark:focus:ring-blue-400 focus:border-transparent h-48 resize-y"
            placeholder="Enter your system prompt here..."
          />
          
          <div className="text-sm text-gray-500 dark:text-gray-400">
            <p>💡 <strong>Tips:</strong></p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>Be specific about the assistant's role and capabilities</li>
              <li>Include guidelines for handling different types of questions</li>
              <li>Mention how to cite sources when using document content</li>
              <li>Set the tone (professional, friendly, helpful, etc.)</li>
            </ul>
          </div>
          
          <button
            onClick={handleSavePrompt}
            disabled={saving || prompt === currentOrganization.prompt}
            className="px-6 py-3 bg-gradient-to-r from-deep-blue to-slate-gray text-white rounded-xl hover:from-blue-800 hover:to-slate-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 font-medium"
          >
            {saving ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Saving...</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>Save Changes</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default OrganizationSettings;
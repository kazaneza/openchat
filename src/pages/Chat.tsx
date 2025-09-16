import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Send, Bot, User, FileText } from 'lucide-react';
import { Organization, ChatMessage } from '../types';
import { organizationApi } from '../services/api';

const Chat: React.FC = () => {
  const [searchParams] = useSearchParams();
  const orgId = searchParams.get('org');
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (orgId) {
      loadOrganization();
    }
  }, [orgId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadOrganization = async () => {
    if (!orgId) return;
    
    try {
      const org = await organizationApi.getById(orgId);
      setOrganization(org);
    } catch (error) {
      console.error('Failed to load organization:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentMessage.trim() || !orgId || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      message: currentMessage,
      response: '',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setCurrentMessage('');
    setLoading(true);

    try {
      const response = await organizationApi.chat(orgId, currentMessage);
      
      const botMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        message: '',
        response: response.response,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        message: '',
        response: 'Sorry, there was an error processing your message. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  if (!orgId) {
    return (
      <div className="max-w-4xl mx-auto text-center py-16">
        <div className="w-24 h-24 bg-slate-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <FileText className="w-12 h-12 text-deep-blue dark:text-blue-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">No Organization Selected</h2>
        <p className="text-gray-600 dark:text-gray-300">Please select an organization from the dashboard to start chatting.</p>
      </div>
    );
  }

  if (!organization) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="w-12 h-12 border-4 border-slate-200 dark:border-gray-700 border-t-deep-blue dark:border-t-blue-400 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-4rem)] flex flex-col">
      {/* Header */}
      <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700 mb-6">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 bg-gradient-to-r from-blue-900 to-slate-700 rounded-xl flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{organization.name}</h1>
            <p className="text-gray-600 dark:text-gray-300">{organization.document_count} documents • AI Assistant</p>
          </div>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-gray-700 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-16">
              <div className="w-16 h-16 bg-slate-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                <Bot className="w-8 h-8 text-deep-blue dark:text-blue-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Start a conversation</h3>
              <p className="text-gray-600 dark:text-gray-300">Ask questions about the documents in this organization. The AI will provide answers based on the content.</p>
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id}>
                {message.message && (
                  <div className="flex justify-end mb-4">
                    <div className="flex items-start space-x-3 max-w-3xl">
                      <div className="bg-gradient-to-r from-blue-900 to-slate-700 text-white rounded-2xl rounded-tr-none px-6 py-3 shadow-lg">
                        <p>{message.message}</p>
                      </div>
                      <div className="w-8 h-8 bg-slate-100 dark:bg-gray-700 rounded-full flex items-center justify-center flex-shrink-0">
                        <User className="w-4 h-4 text-deep-blue dark:text-blue-400" />
                      </div>
                    </div>
                  </div>
                )}
                
                {message.response && (
                  <div className="flex justify-start">
                    <div className="flex items-start space-x-3 max-w-3xl">
                      <div className="w-8 h-8 bg-gradient-to-r from-blue-900 to-slate-700 rounded-full flex items-center justify-center flex-shrink-0">
                        <Bot className="w-4 h-4 text-white" />
                      </div>
                      <div className="bg-slate-100 dark:bg-gray-700 rounded-2xl rounded-tl-none px-6 py-3">
                        <p className="whitespace-pre-wrap dark:text-gray-200">{message.response}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
          
          {loading && (
            <div className="flex justify-start">
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-900 to-slate-700 rounded-full flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="bg-slate-100 dark:bg-gray-700 rounded-2xl rounded-tl-none px-6 py-3">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-slate-400 dark:bg-gray-500 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-slate-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-slate-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Message Input */}
        <div className="border-t border-slate-200 dark:border-gray-700 p-6">
          <form onSubmit={handleSendMessage} className="flex space-x-4">
            <input
              type="text"
              value={currentMessage}
              onChange={(e) => setCurrentMessage(e.target.value)}
              placeholder="Ask a question about the documents..."
              className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 rounded-xl focus:outline-none focus:ring-2 focus:ring-deep-blue dark:focus:ring-blue-400 focus:border-transparent"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!currentMessage.trim() || loading}
              className="px-6 py-3 bg-gradient-to-r from-blue-900 to-slate-700 text-white rounded-xl hover:from-blue-800 hover:to-slate-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <Send className="w-4 h-4" />
              <span>Send</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Chat;
import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, FileText, MessageSquare, Trash2, BookOpen, TrendingUp, AlertCircle } from 'lucide-react';
import { Conversation, ConversationMessage } from '../types';
import { organizationApi, conversationApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface Source {
  document_name: string;
  page_display: string;
  similarity: number;
  chunk_preview: string;
}

const Chat: React.FC = () => {
  const { currentOrganization, currentUser } = useAuth();
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [showConversations, setShowConversations] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (currentOrganization && currentUser) {
      loadConversations();
    }
  }, [currentOrganization, currentUser]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversations = async () => {
    if (!currentUser || !currentOrganization) return;
    try {
      const convs = await conversationApi.getUserConversations(
        currentUser.id,
        currentOrganization.id
      );
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversationMessages = async (conversationId: string) => {
    if (!currentUser) return;
    try {
      const data = await conversationApi.getConversationMessages(
        conversationId,
        currentUser.id
      );
      setMessages(data.messages);
      setCurrentConversation(data.conversation);
      setShowConversations(false);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const startNewConversation = () => {
    setMessages([]);
    setCurrentConversation(null);
    setShowConversations(false);
  };

  const deleteConversation = async (conversationId: string) => {
    if (!currentUser) return;
    try {
      await conversationApi.deleteConversation(conversationId, currentUser.id);
      setConversations(prev => prev.filter(c => c.id !== conversationId));
      if (currentConversation?.id === conversationId) {
        startNewConversation();
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentMessage.trim() || !currentOrganization || loading) return;

    const userMessage: ConversationMessage = {
      id: Date.now().toString(),
      conversation_id: currentConversation?.id || '',
      role: 'user',
      content: currentMessage,
      created_at: new Date().toISOString(),
      metadata: {},
    };

    setMessages(prev => [...prev, userMessage]);
    setCurrentMessage('');
    setLoading(true);

    try {
      const response = await organizationApi.chat(
        currentOrganization.id,
        currentMessage,
        currentConversation?.id
      );

      const botMessage: ConversationMessage = {
        id: (Date.now() + 1).toString(),
        conversation_id: response.conversation_id,
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString(),
        metadata: {
          query_type: response.query_type,
          sources: response.sources || [],
          confidence_score: response.confidence_score || 0,
          needs_clarification: response.needs_clarification || false
        },
      };

      setMessages(prev => [...prev, botMessage]);

      if (!currentConversation && response.conversation_id) {
        await loadConversations();
        const newConv = await conversationApi.getConversationMessages(
          response.conversation_id,
          currentUser!.id
        );
        setCurrentConversation(newConv.conversation);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: ConversationMessage = {
        id: (Date.now() + 1).toString(),
        conversation_id: currentConversation?.id || '',
        role: 'assistant',
        content: 'Sorry, there was an error processing your message. Please try again.',
        created_at: new Date().toISOString(),
        metadata: {},
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const renderSources = (sources: Source[]) => {
    if (!sources || sources.length === 0) return null;

    return (
      <div className="mt-3 pt-3 border-t border-slate-200 dark:border-gray-600">
        <div className="flex items-center gap-2 mb-2">
          <BookOpen className="w-4 h-4 text-slate-600 dark:text-gray-400" />
          <span className="text-xs font-medium text-slate-600 dark:text-gray-400">Sources:</span>
        </div>
        <div className="space-y-2">
          {sources.map((source, idx) => (
            <div key={idx} className="text-xs bg-slate-50 dark:bg-gray-800 rounded-lg p-2">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-slate-700 dark:text-gray-300">
                  {source.document_name}
                </span>
                <span className="text-slate-500 dark:text-gray-500">
                  {source.page_display}
                </span>
              </div>
              <div className="flex items-center gap-2 text-slate-500 dark:text-gray-500">
                <TrendingUp className="w-3 h-3" />
                <span>Relevance: {Math.round(source.similarity * 100)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderConfidenceScore = (score: number) => {
    if (!score || score === 0) return null;

    const percentage = Math.round(score * 100);
    const color = percentage >= 70 ? 'text-green-600 dark:text-green-400' :
                  percentage >= 50 ? 'text-yellow-600 dark:text-yellow-400' :
                  'text-orange-600 dark:text-orange-400';

    return (
      <div className="flex items-center gap-1 text-xs mt-2">
        <TrendingUp className={`w-3 h-3 ${color}`} />
        <span className={color}>Confidence: {percentage}%</span>
      </div>
    );
  };

  if (!currentOrganization) {
    return (
      <div className="max-w-4xl mx-auto text-center py-16">
        <div className="w-24 h-24 bg-slate-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <FileText className="w-12 h-12 text-deep-blue dark:text-blue-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">No Organization Selected</h2>
        <p className="text-gray-600 dark:text-gray-300">Please log in to start chatting.</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto h-[calc(100vh-4rem)] flex gap-6">
      {/* Conversations Sidebar */}
      <div className={`${showConversations ? 'w-80' : 'w-16'} transition-all duration-300 flex-shrink-0`}>
        <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-4 border border-slate-200 dark:border-gray-700 h-full flex flex-col">
          <button
            onClick={() => setShowConversations(!showConversations)}
            className="w-full p-3 bg-gradient-to-r from-blue-900 to-slate-700 text-white rounded-xl hover:from-blue-800 hover:to-slate-600 transition-all duration-200 flex items-center justify-center gap-2 mb-4"
          >
            <MessageSquare className="w-5 h-5" />
            {showConversations && <span>History</span>}
          </button>

          {showConversations && (
            <>
              <button
                onClick={startNewConversation}
                className="w-full p-3 border border-slate-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-slate-100 dark:hover:bg-gray-700 transition-all duration-200 mb-4"
              >
                New Chat
              </button>

              <div className="flex-1 overflow-y-auto space-y-2">
                {conversations.map(conv => (
                  <div
                    key={conv.id}
                    className={`p-3 rounded-xl cursor-pointer transition-all group relative ${
                      currentConversation?.id === conv.id
                        ? 'bg-blue-100 dark:bg-blue-900/30'
                        : 'hover:bg-slate-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <div
                      onClick={() => loadConversationMessages(conv.id)}
                      className="flex-1"
                    >
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {conv.title}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {conv.message_count} messages
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteConversation(conv.id);
                      }}
                      className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700 mb-6">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-900 to-slate-700 rounded-xl flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {currentConversation?.title || currentOrganization.name}
              </h1>
              <p className="text-gray-600 dark:text-gray-300">{currentOrganization.document_count} documents • AI Assistant</p>
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
                  {message.role === 'user' && (
                    <div className="flex justify-end mb-4">
                      <div className="flex items-start space-x-3 max-w-3xl">
                        <div className="bg-gradient-to-r from-blue-900 to-slate-700 text-white rounded-2xl rounded-tr-none px-6 py-3 shadow-lg">
                          <p>{message.content}</p>
                        </div>
                        <div className="w-8 h-8 bg-slate-100 dark:bg-gray-700 rounded-full flex items-center justify-center flex-shrink-0">
                          <User className="w-4 h-4 text-deep-blue dark:text-blue-400" />
                        </div>
                      </div>
                    </div>
                  )}

                  {message.role === 'assistant' && (
                    <div className="flex justify-start mb-4">
                      <div className="flex items-start space-x-3 max-w-3xl">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          message.metadata?.needs_clarification
                            ? 'bg-gradient-to-r from-orange-500 to-yellow-500'
                            : 'bg-gradient-to-r from-blue-900 to-slate-700'
                        }`}>
                          {message.metadata?.needs_clarification ? (
                            <AlertCircle className="w-4 h-4 text-white" />
                          ) : (
                            <Bot className="w-4 h-4 text-white" />
                          )}
                        </div>
                        <div className={`rounded-2xl rounded-tl-none px-6 py-3 flex-1 ${
                          message.metadata?.needs_clarification
                            ? 'bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800'
                            : 'bg-slate-100 dark:bg-gray-700'
                        }`}>
                          {message.metadata?.needs_clarification && (
                            <div className="flex items-center gap-2 mb-2 text-orange-700 dark:text-orange-300">
                              <AlertCircle className="w-4 h-4" />
                              <span className="text-xs font-medium">Clarification Needed</span>
                            </div>
                          )}
                          <p className="whitespace-pre-wrap dark:text-gray-200">{message.content}</p>
                          {!message.metadata?.needs_clarification && renderConfidenceScore(message.metadata?.confidence_score)}
                          {!message.metadata?.needs_clarification && renderSources(message.metadata?.sources)}
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
    </div>
  );
};

export default Chat;

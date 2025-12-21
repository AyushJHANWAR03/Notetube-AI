'use client';

import { useState, useCallback, useRef, useEffect } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ChatMessageItem {
  role: 'user' | 'assistant';
  content: string;
}

interface UseStreamingChatOptions {
  videoId: string;
  onError?: (error: string) => void;
}

interface UseStreamingChatReturn {
  messages: ChatMessageItem[];
  isStreaming: boolean;
  isLoadingHistory: boolean;
  error: string | null;
  followupPrompts: string[];
  sendMessage: (message: string) => Promise<void>;
  clearMessages: () => void;
}

export function useStreamingChat({
  videoId,
  onError,
}: UseStreamingChatOptions): UseStreamingChatReturn {
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [followupPrompts, setFollowupPrompts] = useState<string[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const hasLoadedHistory = useRef(false);

  // Load chat history on mount
  useEffect(() => {
    const loadChatHistory = async () => {
      if (hasLoadedHistory.current) return;
      hasLoadedHistory.current = true;

      try {
        const token = localStorage.getItem('token');
        if (!token) {
          setIsLoadingHistory(false);
          return;
        }

        const response = await fetch(`${API_URL}/api/videos/${videoId}/chat/history`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.messages && data.messages.length > 0) {
            // Convert API messages to ChatMessageItem format
            const historyMessages: ChatMessageItem[] = data.messages.map((m: any) => ({
              role: m.role as 'user' | 'assistant',
              content: m.content,
            }));
            setMessages(historyMessages);
          }
        }
      } catch (err) {
        console.error('Failed to load chat history:', err);
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadChatHistory();
  }, [videoId]);

  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim() || isStreaming) return;

    // Add user message
    const userMessage: ChatMessageItem = { role: 'user', content: message };
    setMessages(prev => [...prev, userMessage]);
    setError(null);
    setIsStreaming(true);
    setFollowupPrompts([]); // Clear previous follow-ups

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Not authenticated');
      }

      // Build history from existing messages (excluding the just-added user message)
      const history = messages.map(m => ({
        role: m.role,
        content: m.content,
      }));

      const response = await fetch(`${API_URL}/api/videos/${videoId}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message,
          history,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(errorData.detail || `Error: ${response.status}`);
      }

      // Add empty assistant message that we'll populate
      const assistantIdx = messages.length + 1; // +1 for user message we just added
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      // Stream the response
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let assistantContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              // Stream complete
              break;
            }
            // Check for follow-up prompts
            if (data.startsWith('[FOLLOWUPS]')) {
              try {
                const followupsJson = data.slice('[FOLLOWUPS]'.length);
                const followups = JSON.parse(followupsJson);
                if (Array.isArray(followups)) {
                  setFollowupPrompts(followups);
                }
              } catch (e) {
                console.error('Failed to parse followups:', e);
              }
              continue;
            }
            assistantContent += data;
            // Update the assistant message with accumulated content
            setMessages(prev => {
              const newMessages = [...prev];
              if (newMessages.length > 0 && newMessages[newMessages.length - 1].role === 'assistant') {
                newMessages[newMessages.length - 1] = {
                  role: 'assistant',
                  content: assistantContent,
                };
              }
              return newMessages;
            });
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // Request was cancelled, don't show error
        return;
      }
      const errorMsg = err.message || 'Failed to send message';
      setError(errorMsg);
      onError?.(errorMsg);
      // Remove the empty assistant message if there was an error
      setMessages(prev => {
        if (prev.length > 0 && prev[prev.length - 1].role === 'assistant' && !prev[prev.length - 1].content) {
          return prev.slice(0, -1);
        }
        return prev;
      });
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }, [videoId, messages, isStreaming, onError]);

  const clearMessages = useCallback(async () => {
    // Abort any ongoing stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Clear from DB via API
    try {
      const token = localStorage.getItem('token');
      if (token) {
        await fetch(`${API_URL}/api/videos/${videoId}/chat/history`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      }
    } catch (err) {
      console.error('Failed to clear chat history from server:', err);
    }

    setMessages([]);
    setError(null);
    setIsStreaming(false);
  }, [videoId]);

  return {
    messages,
    isStreaming,
    isLoadingHistory,
    error,
    followupPrompts,
    sendMessage,
    clearMessages,
  };
}

export default useStreamingChat;

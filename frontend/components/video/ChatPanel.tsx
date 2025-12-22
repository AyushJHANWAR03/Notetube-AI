'use client';

import { useState, useRef, useEffect } from 'react';
import { useStreamingChat, ChatMessageItem } from '@/hooks/useStreamingChat';

interface ChatPanelProps {
  videoId: string;
  videoTitle?: string;
  suggestedPrompts?: string[];
  pendingMessage?: string;
  onPendingMessageHandled?: () => void;
  onSeek?: (seconds: number) => void;
  isGuest?: boolean;
  onSignIn?: () => void;
}

export default function ChatPanel({
  videoId,
  videoTitle,
  suggestedPrompts,
  pendingMessage,
  onPendingMessageHandled,
  onSeek,
  isGuest = false,
  onSignIn,
}: ChatPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const hasSentPendingRef = useRef(false);

  const {
    messages,
    isStreaming,
    isLoadingHistory,
    error,
    followupPrompts,
    sendMessage,
    clearMessages,
  } = useStreamingChat({ videoId });

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle pending message from "Explain" button
  // Wait for history to load before sending the pending message
  useEffect(() => {
    if (pendingMessage && !hasSentPendingRef.current && !isStreaming && !isLoadingHistory) {
      hasSentPendingRef.current = true;
      sendMessage(`Explain this: "${pendingMessage}"`);
      onPendingMessageHandled?.();
    }
  }, [pendingMessage, isStreaming, isLoadingHistory, sendMessage, onPendingMessageHandled]);

  // Reset pending ref when pendingMessage changes to a new value
  useEffect(() => {
    if (!pendingMessage) {
      hasSentPendingRef.current = false;
    }
  }, [pendingMessage]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputValue.trim() || isStreaming) return;

    const message = inputValue.trim();
    setInputValue('');
    await sendMessage(message);
  };

  const handleSuggestedPrompt = (prompt: string) => {
    if (isStreaming) return;
    sendMessage(prompt);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Guest sign-in prompt
  if (isGuest) {
    return (
      <div className="flex flex-col h-full items-center justify-center text-center p-6">
        <div className="w-16 h-16 bg-purple-900/30 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-white mb-2">
          Chat with Your Video
        </h3>
        <p className="text-gray-400 text-sm mb-6 max-w-xs">
          Sign in to unlock AI chat and ask questions about this video's content.
        </p>
        <button
          onClick={onSignIn}
          className="flex items-center gap-2 px-5 py-2.5 bg-white hover:bg-gray-100 text-gray-800 font-semibold rounded-lg transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Sign in to Chat
        </button>
        <p className="text-xs text-gray-500 mt-4">
          Free accounts get 5 videos per month
        </p>
      </div>
    );
  }

  // Loading state
  if (isLoadingHistory) {
    return (
      <div className="flex flex-col h-full items-center justify-center">
        <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-gray-400 text-sm mt-2">Loading chat history...</p>
      </div>
    );
  }

  // Empty state - no messages yet
  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex flex-col h-full">
        {/* Empty state content - scrollable if needed */}
        <div className="flex-1 overflow-y-auto min-h-0">
          <div className="flex flex-col items-center text-center p-4 pt-8">
            <div className="w-10 h-10 bg-purple-900/30 rounded-full flex items-center justify-center mb-2">
              <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h3 className="text-sm font-medium text-white mb-0.5">
              Chat with Your Video
            </h3>
            <p className="text-gray-400 text-xs mb-3">
              Ask questions about the content
            </p>

            {/* Suggested prompts - compact */}
            {suggestedPrompts && suggestedPrompts.length > 0 && (
              <div className="w-full max-w-sm space-y-1.5">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Try asking</p>
                {suggestedPrompts.map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => handleSuggestedPrompt(prompt)}
                    className="w-full text-left p-2 rounded-lg bg-gray-700/50 hover:bg-gray-700 border border-gray-600 hover:border-purple-500 transition-all text-sm text-gray-300 hover:text-white"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Input at bottom - always visible */}
        <div className="flex-shrink-0 border-t border-gray-700 p-3 bg-gray-800">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about this video..."
              rows={1}
              className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isStreaming}
              className={`px-3 py-2 rounded-lg transition-colors ${
                inputValue.trim() && !isStreaming
                  ? 'bg-purple-600 hover:bg-purple-500 text-white'
                  : 'bg-gray-700 text-gray-500 cursor-not-allowed'
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Check if AI is thinking (streaming and either no assistant message yet, or assistant message is empty)
  const lastMessage = messages[messages.length - 1];
  const isAiThinking = isStreaming && (
    lastMessage?.role === 'user' ||  // User just sent message, waiting for response
    (lastMessage?.role === 'assistant' && !lastMessage?.content)  // Empty assistant message
  );

  // Chat with messages
  return (
    <div className="flex flex-col h-full">
      {/* Messages area - scrollable */}
      <div className="flex-1 overflow-y-auto space-y-4 p-4 min-h-0">
        {messages.map((msg, i) => {
          // Skip rendering empty assistant message (we show typing indicator instead)
          if (msg.role === 'assistant' && !msg.content && isStreaming) {
            return null;
          }
          return (
            <ChatMessage key={i} message={msg} isStreaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'} onSeek={onSeek} />
          );
        })}
        {/* Typing indicator when AI is thinking */}
        {isAiThinking && (
          <div className="flex justify-start">
            <div className="bg-gray-700 rounded-lg px-4 py-3">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        {error && (
          <div className="px-4 py-2 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area - fixed at bottom */}
      <div className="flex-shrink-0 border-t border-gray-700 bg-gray-800">
        {/* Follow-up prompts */}
        {followupPrompts.length > 0 && !isStreaming && (
          <div className="px-4 pt-3 flex flex-wrap gap-2">
            {followupPrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => sendMessage(prompt)}
                className="text-xs px-3 py-1.5 rounded-full bg-purple-900/40 hover:bg-purple-900/60 text-purple-300 hover:text-purple-200 border border-purple-700/50 hover:border-purple-600 transition-all"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}
        <div className="p-4 pt-3">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a follow-up question..."
              rows={1}
              disabled={isStreaming}
              className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isStreaming}
              className={`px-4 py-2 rounded-lg transition-colors ${
                inputValue.trim() && !isStreaming
                  ? 'bg-purple-600 hover:bg-purple-500 text-white'
                  : 'bg-gray-700 text-gray-500 cursor-not-allowed'
              }`}
            >
              {isStreaming ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </form>
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="mt-2 text-xs px-3 py-1.5 rounded-full bg-purple-900/40 hover:bg-purple-900/60 text-purple-300 hover:text-purple-200 border border-purple-700/50 hover:border-purple-600 transition-all"
            >
              Clear chat
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// Parse timestamp string like "5:32" or "1:05:32" to seconds
function parseTimestamp(timestamp: string): number {
  const parts = timestamp.split(':').map(Number);
  if (parts.length === 2) {
    // MM:SS
    return parts[0] * 60 + parts[1];
  } else if (parts.length === 3) {
    // H:MM:SS
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  return 0;
}

// Render message content with clickable timestamps
function renderMessageWithTimestamps(
  content: string,
  onSeek?: (seconds: number) => void
): React.ReactNode[] {
  // Match timestamps like [5:32], [12:45], [1:05:32]
  const timestampRegex = /\[(\d{1,2}:\d{2}(?::\d{2})?)\]/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;

  while ((match = timestampRegex.exec(content)) !== null) {
    // Add text before the timestamp
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }

    const timestamp = match[1];
    const seconds = parseTimestamp(timestamp);

    // Add clickable timestamp
    parts.push(
      <button
        key={`ts-${match.index}`}
        onClick={() => onSeek?.(seconds)}
        className="inline-flex items-center px-1.5 py-0.5 mx-0.5 text-xs font-medium bg-purple-600/30 hover:bg-purple-600/50 text-purple-300 hover:text-purple-200 rounded border border-purple-500/50 transition-colors cursor-pointer"
        title={`Jump to ${timestamp}`}
      >
        [{timestamp}]
      </button>
    );

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text after the last timestamp
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [content];
}

// Individual message component
function ChatMessage({
  message,
  isStreaming,
  onSeek
}: {
  message: ChatMessageItem;
  isStreaming: boolean;
  onSeek?: (seconds: number) => void;
}) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2 ${
          isUser
            ? 'bg-purple-600 text-white'
            : 'bg-gray-700 text-gray-200'
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">
          {isUser
            ? message.content
            : renderMessageWithTimestamps(message.content, onSeek)
          }
          {isStreaming && (
            <span className="inline-block w-1 h-4 ml-0.5 bg-current animate-pulse" />
          )}
        </p>
      </div>
    </div>
  );
}

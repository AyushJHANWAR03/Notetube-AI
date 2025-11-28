'use client';

import { useState, useRef, useEffect } from 'react';
import { useStreamingChat, ChatMessageItem } from '@/hooks/useStreamingChat';

interface ChatPanelProps {
  videoId: string;
  videoTitle?: string;
  suggestedPrompts?: string[];
  pendingMessage?: string;
  onPendingMessageHandled?: () => void;
}

export default function ChatPanel({
  videoId,
  videoTitle,
  suggestedPrompts,
  pendingMessage,
  onPendingMessageHandled,
}: ChatPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const hasSentPendingRef = useRef(false);

  const {
    messages,
    isStreaming,
    error,
    sendMessage,
    clearMessages,
  } = useStreamingChat({ videoId });

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle pending message from "Explain" button
  useEffect(() => {
    if (pendingMessage && !hasSentPendingRef.current && !isStreaming) {
      hasSentPendingRef.current = true;
      sendMessage(`Explain this: "${pendingMessage}"`);
      onPendingMessageHandled?.();
    }
  }, [pendingMessage, isStreaming, sendMessage, onPendingMessageHandled]);

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

  // Empty state - no messages yet
  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex flex-col h-full">
        {/* Empty state content - scrollable if needed */}
        <div className="flex-1 overflow-y-auto min-h-0 flex flex-col items-center justify-center text-center p-4">
          <div className="w-12 h-12 bg-purple-900/30 rounded-full flex items-center justify-center mb-3">
            <svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <h3 className="text-base font-medium text-white mb-1">
            Chat with Your Video
          </h3>
          <p className="text-gray-400 text-sm max-w-xs mb-4">
            Ask questions about the content
          </p>

          {/* Suggested prompts */}
          {suggestedPrompts && suggestedPrompts.length > 0 && (
            <div className="w-full max-w-sm space-y-2">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Try asking</p>
              {suggestedPrompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => handleSuggestedPrompt(prompt)}
                  className="w-full text-left p-3 rounded-lg bg-gray-700/50 hover:bg-gray-700 border border-gray-600 hover:border-purple-500 transition-all text-sm text-gray-300 hover:text-white"
                >
                  {prompt}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Input at bottom - fixed */}
        <div className="flex-shrink-0 border-t border-gray-700 p-4 bg-gray-800">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about this video..."
              rows={1}
              className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
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
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Chat with messages
  return (
    <div className="flex flex-col h-full">
      {/* Messages area - scrollable */}
      <div className="flex-1 overflow-y-auto space-y-4 p-4 min-h-0">
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} isStreaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'} />
        ))}
        {error && (
          <div className="px-4 py-2 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area - fixed at bottom */}
      <div className="flex-shrink-0 border-t border-gray-700 p-4 bg-gray-800">
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
            className="mt-2 text-xs text-gray-500 hover:text-gray-400 transition-colors"
          >
            Clear chat
          </button>
        )}
      </div>
    </div>
  );
}

// Individual message component
function ChatMessage({ message, isStreaming }: { message: ChatMessageItem; isStreaming: boolean }) {
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
          {message.content}
          {isStreaming && (
            <span className="inline-block w-1 h-4 ml-0.5 bg-current animate-pulse" />
          )}
        </p>
      </div>
    </div>
  );
}

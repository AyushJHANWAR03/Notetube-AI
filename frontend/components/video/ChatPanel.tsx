'use client';

interface ChatPanelProps {
  videoId: string;
  videoTitle?: string;
}

export default function ChatPanel({ videoId, videoTitle }: ChatPanelProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center py-12">
      <div className="w-16 h-16 bg-purple-900/30 rounded-full flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">
        Chat with Your Video
      </h3>
      <p className="text-gray-400 text-sm max-w-sm mb-4">
        Ask questions about the video content, get explanations, and discuss topics.
      </p>
      <p className="text-xs text-gray-500">
        Coming soon...
      </p>
    </div>
  );
}

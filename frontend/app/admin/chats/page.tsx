'use client';

import { useEffect, useState } from 'react';
import { adminApi, ChatListItem } from '@/lib/adminApi';

export default function AdminChats() {
  const [chats, setChats] = useState<ChatListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const limit = 50;

  useEffect(() => {
    loadChats();
  }, [page]);

  const loadChats = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getChats(limit, page * limit);
      setChats(data.chats);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to load chats:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Chats</h1>
        <p className="text-gray-400 mt-1">User messages sent to AI ({total} total)</p>
      </div>

      {loading ? (
        <div className="text-gray-400">Loading...</div>
      ) : (
        <div className="space-y-3">
          {chats.map((chat) => (
            <div key={chat.id} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm">{chat.content}</p>
                  {chat.video_title && (
                    <p className="text-blue-400 text-xs mt-1 truncate">
                      Video: {chat.video_title}
                    </p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="text-gray-300 text-xs font-medium">
                    {chat.user_name || 'Unknown'}
                  </p>
                  <p className="text-gray-500 text-xs">{chat.user_email || '—'}</p>
                  <p className="text-gray-600 text-xs mt-1">
                    {new Date(chat.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > limit && (
        <div className="flex items-center justify-between pt-4">
          <p className="text-gray-400 text-sm">
            Showing {page * limit + 1}–{Math.min((page + 1) * limit, total)} of {total}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => p - 1)}
              disabled={page === 0}
              className="px-4 py-2 bg-gray-700 text-white rounded-lg disabled:opacity-40 hover:bg-gray-600"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={(page + 1) * limit >= total}
              className="px-4 py-2 bg-gray-700 text-white rounded-lg disabled:opacity-40 hover:bg-gray-600"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

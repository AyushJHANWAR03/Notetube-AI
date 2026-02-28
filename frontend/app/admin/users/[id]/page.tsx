'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { adminApi, UserDetail } from '@/lib/adminApi';

export default function AdminUserDetailPage() {
  const params = useParams();
  const userId = params.id as string;
  const [user, setUser] = useState<UserDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (userId) {
      loadUser();
    }
  }, [userId]);

  const loadUser = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getUserDetail(userId);
      setUser(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load user');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading user...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 text-red-200">
        {error}
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="space-y-6">
      {/* Back button */}
      <Link href="/admin/users" className="text-gray-400 hover:text-white flex items-center gap-2">
        <span>←</span> Back to Users
      </Link>

      {/* User Header */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
        <div className="flex items-center gap-4">
          {user.avatar_url ? (
            <img src={user.avatar_url} alt={user.name || ''} className="w-16 h-16 rounded-full" />
          ) : (
            <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-white text-2xl">
              {user.name?.charAt(0) || 'U'}
            </div>
          )}
          <div>
            <h1 className="text-2xl font-bold text-white">{user.name || 'No Name'}</h1>
            <p className="text-gray-400">{user.email}</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="bg-gray-900 rounded-lg p-4">
            <div className="text-gray-400 text-sm">Videos Analyzed</div>
            <div className="text-2xl font-bold text-white">{user.videos_analyzed}</div>
          </div>
          <div className="bg-gray-900 rounded-lg p-4">
            <div className="text-gray-400 text-sm">Video Limit</div>
            <div className="text-2xl font-bold text-white">{user.video_limit}</div>
          </div>
          <div className="bg-gray-900 rounded-lg p-4">
            <div className="text-gray-400 text-sm">Joined</div>
            <div className="text-lg font-bold text-white">{formatDate(user.created_at)}</div>
          </div>
        </div>
      </div>

      {/* User's Videos */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Videos ({user.videos.length})</h2>
        {user.videos.length === 0 ? (
          <p className="text-gray-400">No videos analyzed yet</p>
        ) : (
          <div className="space-y-3">
            {user.videos.map((video) => (
              <div key={video.id} className="bg-gray-900 rounded-lg p-4 flex items-center justify-between">
                <div>
                  <div className="text-white">{video.title || 'Untitled'}</div>
                  <div className="text-gray-400 text-sm">{formatDate(video.created_at)}</div>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm ${
                  video.status === 'READY' ? 'bg-green-900 text-green-300' :
                  video.status === 'FAILED' ? 'bg-red-900 text-red-300' :
                  'bg-yellow-900 text-yellow-300'
                }`}>
                  {video.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* User's Chat History */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Recent Chats ({user.recent_chats.length})</h2>
        {user.recent_chats.length === 0 ? (
          <p className="text-gray-400">No chat messages yet</p>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {user.recent_chats.map((chat) => (
              <div key={chat.id} className={`rounded-lg p-3 ${
                chat.role === 'user' ? 'bg-blue-900/30 border border-blue-800' : 'bg-gray-900'
              }`}>
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-sm font-medium ${
                    chat.role === 'user' ? 'text-blue-400' : 'text-gray-400'
                  }`}>
                    {chat.role === 'user' ? 'User' : 'AI'}
                  </span>
                  <span className="text-gray-500 text-xs">{formatDate(chat.created_at)}</span>
                </div>
                <p className="text-gray-300 text-sm">{chat.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

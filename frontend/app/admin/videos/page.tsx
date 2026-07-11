'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { adminApi, VideoListItem } from '@/lib/adminApi';

export default function AdminVideosPage() {
  const searchParams = useSearchParams();
  const statusFilter = searchParams.get('status') || '';

  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState(statusFilter);

  useEffect(() => {
    loadVideos();
  }, [filter]);

  const loadVideos = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getVideos(100, 0, filter || undefined);
      setVideos(data.videos);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load videos');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    // Backend sends naive UTC timestamps — append Z so JS parses as UTC, then render in IST
    const utc = dateStr.endsWith('Z') ? dateStr : dateStr + 'Z';
    return new Date(utc).toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }) + ' IST';
  };

  const shortFailure = (reason: string | null) => {
    if (!reason) return 'Unknown failure';
    if (/supports videos up to|hours.*long/i.test(reason)) {
      const match = reason.match(/(\d+h \d+m)/);
      return `⏱️ Too long${match ? ` (${match[1]})` : ''}`;
    }
    if (/caption|subtitle/i.test(reason)) return '🔇 No captions';
    if (/supadata|429|limit-exceeded/i.test(reason)) return '🔌 Transcript API error';
    if (/openai|AI provider|generate/i.test(reason)) return '🤖 AI generation error';
    return reason.slice(0, 60);
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading videos...</div>
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Videos</h1>
          <p className="text-gray-400 mt-1">Total: {total} videos</p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-gray-700 text-white border border-gray-600 rounded-lg px-4 py-2"
          >
            <option value="">All Status</option>
            <option value="READY">Ready</option>
            <option value="PROCESSING">Processing</option>
            <option value="FAILED">Failed</option>
          </select>
          <button
            onClick={loadVideos}
            className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="bg-gray-900/70 rounded-2xl border border-gray-800 overflow-hidden">
        <table className="w-full">
          <thead className="bg-[#0b0d14]">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Video
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Duration
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                YouTube
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Created
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {videos.map((video) => (
              <tr key={video.id} className="hover:bg-gray-700/50">
                <td className="px-6 py-4">
                  <div className="text-white max-w-md truncate">
                    {video.title || (video.status === 'FAILED' ? '(failed before metadata)' : 'Processing...')}
                  </div>
                  {video.status === 'FAILED' && (
                    <div className="text-xs text-red-400/90 mt-1 max-w-md truncate" title={video.failure_reason || undefined}>
                      {shortFailure(video.failure_reason)}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4">
                  {video.is_guest ? (
                    <span className="text-yellow-400 text-sm">Guest</span>
                  ) : (
                    <div>
                      <div className="text-white text-sm">{video.user_name || 'Unknown'}</div>
                      <div className="text-gray-400 text-xs">{video.user_email}</div>
                    </div>
                  )}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-3 py-1 rounded-full text-sm ${
                    video.status === 'READY' ? 'bg-green-900 text-green-300' :
                    video.status === 'FAILED' ? 'bg-red-900 text-red-300' :
                    'bg-yellow-900 text-yellow-300'
                  }`}>
                    {video.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className="text-gray-400">{formatDuration(video.duration_seconds)}</span>
                </td>
                <td className="px-6 py-4">
                  {video.youtube_video_id ? (
                    <a
                      href={`https://youtube.com/watch?v=${video.youtube_video_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 text-sm"
                    >
                      Watch
                    </a>
                  ) : (
                    <span className="text-gray-500">-</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <span className="text-gray-400">{formatDate(video.created_at)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

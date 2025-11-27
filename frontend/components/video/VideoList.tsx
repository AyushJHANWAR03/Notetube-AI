'use client';

import { useState, useEffect } from 'react';
import { Video } from '@/lib/types';
import { videoApi } from '@/lib/videoApi';
import VideoCard from './VideoCard';

interface VideoListProps {
  refreshTrigger?: number;
}

export default function VideoList({ refreshTrigger }: VideoListProps) {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVideos = async () => {
    try {
      setLoading(true);
      const response = await videoApi.listVideos({ limit: 50 });
      setVideos(response.videos);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load videos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideos();
  }, [refreshTrigger]);

  // Poll for processing videos
  useEffect(() => {
    const processingVideos = videos.filter(v => v.status === 'PROCESSING' || v.status === 'PENDING');

    if (processingVideos.length === 0) return;

    const interval = setInterval(() => {
      fetchVideos();
    }, 3000);

    return () => clearInterval(interval);
  }, [videos]);

  if (loading && videos.length === 0) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-400 mb-4">{error}</p>
        <button
          onClick={fetchVideos}
          className="text-blue-400 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (videos.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-5xl mb-4">🎬</div>
        <h3 className="text-lg font-semibold text-white mb-2">No videos yet</h3>
        <p className="text-gray-400">
          Paste a YouTube URL above to get started!
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xl font-semibold text-white">Your Videos ({videos.length})</h3>
        <button
          onClick={fetchVideos}
          disabled={loading}
          className="text-sm text-blue-400 hover:text-blue-300 disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Refreshing...
            </>
          ) : (
            'Refresh'
          )}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {videos.map((video) => (
          <VideoCard key={video.id} video={video} />
        ))}
      </div>
    </div>
  );
}

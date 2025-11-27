'use client';

import { useState, useEffect } from 'react';
import { Video } from '@/lib/types';
import { videoApi } from '@/lib/videoApi';
import VideoCard from './VideoCard';

interface VideoListProps {
  refreshTrigger?: number; // Increment to trigger refresh
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 mb-4">{error}</p>
        <button
          onClick={fetchVideos}
          className="text-blue-600 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (videos.length === 0) {
    return (
      <div className="text-center py-12 bg-gray-50 rounded-lg">
        <div className="text-4xl mb-4">📺</div>
        <h3 className="text-lg font-semibold text-gray-700 mb-2">No videos yet</h3>
        <p className="text-gray-500">
          Paste a YouTube URL above to get started!
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Your Videos ({videos.length})</h3>
        <button
          onClick={fetchVideos}
          disabled={loading}
          className="text-sm text-blue-600 hover:underline disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
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

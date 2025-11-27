'use client';

import { useState } from 'react';
import { videoApi, extractYouTubeVideoId, getYouTubeThumbnail } from '@/lib/videoApi';
import { VideoCreateResponse } from '@/lib/types';

interface VideoInputProps {
  onVideoSubmitted: (response: VideoCreateResponse) => void;
  disabled?: boolean;
}

export default function VideoInput({ onVideoSubmitted, disabled }: VideoInputProps) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ videoId: string; thumbnail: string } | null>(null);

  const handleUrlChange = (value: string) => {
    setUrl(value);
    setError(null);

    // Show thumbnail preview if valid YouTube URL
    const videoId = extractYouTubeVideoId(value);
    if (videoId) {
      setPreview({
        videoId,
        thumbnail: getYouTubeThumbnail(videoId, 'hq')
      });
    } else {
      setPreview(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!url.trim()) {
      setError('Please enter a YouTube URL');
      return;
    }

    const videoId = extractYouTubeVideoId(url);
    if (!videoId) {
      setError('Please enter a valid YouTube URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await videoApi.createVideo(url);
      onVideoSubmitted(response);
      setUrl('');
      setPreview(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit video. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-xl font-semibold mb-4">Process a Video</h3>

      <form onSubmit={handleSubmit}>
        <div className="flex gap-4">
          <input
            type="text"
            value={url}
            onChange={(e) => handleUrlChange(e.target.value)}
            placeholder="Paste YouTube URL here..."
            disabled={disabled || loading}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          />
          <button
            type="submit"
            disabled={disabled || loading || !url.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold px-6 py-2 rounded-lg transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Processing...
              </>
            ) : (
              'Process Video'
            )}
          </button>
        </div>

        {error && (
          <p className="text-red-500 text-sm mt-2">{error}</p>
        )}

        <p className="text-sm text-gray-500 mt-2">
          Supports YouTube videos, shorts, and embedded links
        </p>
      </form>

      {/* Thumbnail Preview */}
      {preview && (
        <div className="mt-4 flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
          <img
            src={preview.thumbnail}
            alt="Video thumbnail"
            className="w-32 h-20 object-cover rounded"
            onError={(e) => {
              // Fallback to default quality if maxres not available
              (e.target as HTMLImageElement).src = getYouTubeThumbnail(preview.videoId, 'default');
            }}
          />
          <div>
            <p className="text-sm text-gray-600">Video ID: {preview.videoId}</p>
            <p className="text-xs text-gray-400">Click "Process Video" to start</p>
          </div>
        </div>
      )}
    </div>
  );
}

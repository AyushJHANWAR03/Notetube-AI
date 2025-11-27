'use client';

import { useState } from 'react';
import { videoApi, extractYouTubeVideoId, getYouTubeThumbnail } from '@/lib/videoApi';

interface VideoInputProps {
  onVideoSubmitted: (videoId: string) => void;
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
      // Pass the video ID to parent - they'll handle navigation
      onVideoSubmitted(response.video.id);
      setUrl('');
      setPreview(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit video. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
      <form onSubmit={handleSubmit}>
        <div className="flex flex-col sm:flex-row gap-4">
          <input
            type="text"
            value={url}
            onChange={(e) => handleUrlChange(e.target.value)}
            placeholder="Paste YouTube URL here..."
            disabled={disabled || loading}
            className="flex-1 px-4 py-3 bg-gray-900 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={disabled || loading || !url.trim()}
            className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 disabled:from-gray-600 disabled:to-gray-600 text-white font-semibold px-8 py-3 rounded-lg transition-all flex items-center justify-center gap-2 min-w-[160px]"
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
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Generate Notes
              </>
            )}
          </button>
        </div>

        {error && (
          <p className="text-red-400 text-sm mt-3">{error}</p>
        )}

        <p className="text-sm text-gray-500 mt-3">
          Supports YouTube videos, shorts, and embedded links
        </p>
      </form>

      {/* Thumbnail Preview */}
      {preview && (
        <div className="mt-4 flex items-center gap-4 p-4 bg-gray-900/50 rounded-lg border border-gray-700">
          <img
            src={preview.thumbnail}
            alt="Video thumbnail"
            className="w-32 h-20 object-cover rounded"
            onError={(e) => {
              (e.target as HTMLImageElement).src = getYouTubeThumbnail(preview.videoId, 'default');
            }}
          />
          <div>
            <p className="text-sm text-gray-400">Video ID: <span className="text-gray-300">{preview.videoId}</span></p>
            <p className="text-xs text-gray-500 mt-1">Click "Generate Notes" to start processing</p>
          </div>
        </div>
      )}
    </div>
  );
}

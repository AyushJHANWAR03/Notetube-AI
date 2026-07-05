'use client';

import { useState } from 'react';
import { videoApi, extractYouTubeVideoId, getYouTubeThumbnail } from '@/lib/videoApi';
import { track } from '@/lib/mixpanel';

interface VideoInputProps {
  onVideoSubmitted: (videoId: string) => void;
  onBeforeSubmit?: (url: string) => boolean;
  onGuestLimitReached?: () => void;  // Called when guest limit is reached
  disabled?: boolean;
  isGuest?: boolean;  // Whether to use guest API
}

export default function VideoInput({
  onVideoSubmitted,
  onBeforeSubmit,
  onGuestLimitReached,
  disabled,
  isGuest = false
}: VideoInputProps) {
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

    // Check if we should proceed (e.g., user authentication check)
    if (onBeforeSubmit && !onBeforeSubmit(url)) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Use guest API if not authenticated
      if (isGuest) {
        const response = await videoApi.createVideoAsGuest(url);
        track('video_submitted', { video_id: response.video.id, youtube_video_id: videoId, is_guest: true });
        onVideoSubmitted(response.video.id);
        setUrl('');
        setPreview(null);
      } else {
        const response = await videoApi.createVideo(url);
        track('video_submitted', { video_id: response.video.id, youtube_video_id: videoId, is_guest: false });
        onVideoSubmitted(response.video.id);
        setUrl('');
        setPreview(null);
      }
    } catch (err: any) {
      // Handle guest limit reached
      if (err.response?.data?.requires_auth || err.response?.data?.detail === 'GUEST_LIMIT_REACHED') {
        track('guest_limit_reached');
        if (onGuestLimitReached) {
          onGuestLimitReached();
        }
        setLoading(false);
        return;
      }
      track('video_submit_failed', { error: err.response?.data?.detail || 'unknown' });
      setError(err.response?.data?.detail || 'Failed to submit video. Please try again.');
      setLoading(false);
    }
  };

  const exampleVideos = [
    { label: '🧠 Neural Networks Explained', url: 'https://www.youtube.com/watch?v=aircAruvnKk' },
    { label: '💻 100 CS Concepts', url: 'https://www.youtube.com/watch?v=-uleG_Vecis' },
    { label: '🎯 Master Procrastinator (TED)', url: 'https://www.youtube.com/watch?v=arj7oStGLkU' },
  ];

  return (
    <div className="glow-border">
      <div className="bg-[#0b0d14] rounded-[calc(1rem-1.5px)] p-6">
      <form onSubmit={handleSubmit}>
        <div className="flex flex-col sm:flex-row gap-4">
          <input
            type="text"
            value={url}
            onChange={(e) => handleUrlChange(e.target.value)}
            placeholder="Paste any YouTube URL..."
            disabled={disabled || loading}
            className="flex-1 px-4 py-3.5 bg-gray-900/80 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50 text-base"
          />
          <button
            type="submit"
            disabled={disabled || loading || !url.trim()}
            className="bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:from-gray-700 disabled:to-gray-700 text-white font-semibold px-8 py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 min-w-[170px] shadow-lg shadow-indigo-600/20"
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
                Get Notes
              </>
            )}
          </button>
        </div>

        {error && (
          <p className="text-red-400 text-sm mt-3">{error}</p>
        )}

        {/* Example chips */}
        <div className="flex flex-wrap items-center gap-2 mt-4">
          <span className="text-xs text-gray-500">Try an example:</span>
          {exampleVideos.map((ex) => (
            <button
              key={ex.url}
              type="button"
              disabled={disabled || loading}
              onClick={() => handleUrlChange(ex.url)}
              className="text-xs px-3 py-1.5 rounded-full bg-gray-800/80 border border-gray-700 text-gray-300 hover:border-indigo-500/60 hover:text-white transition-colors disabled:opacity-50"
            >
              {ex.label}
            </button>
          ))}
        </div>

        {/* Social proof */}
        <div className="flex items-center gap-2 mt-4 text-xs text-gray-500">
          <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
          <span><span className="text-gray-300 font-medium">679+ videos</span> turned into notes · Ready in ~60 seconds</span>
        </div>
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
            <p className="text-sm text-gray-300">Video detected</p>
            <p className="text-xs text-gray-500 mt-1">Click "Get Notes" to start</p>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}

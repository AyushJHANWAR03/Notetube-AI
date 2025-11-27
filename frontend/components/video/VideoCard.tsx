'use client';

import { Video } from '@/lib/types';
import { formatDuration, getYouTubeThumbnail } from '@/lib/videoApi';
import Link from 'next/link';

interface VideoCardProps {
  video: Video;
  onDelete?: (videoId: string) => void;
}

const statusConfig = {
  PENDING: {
    color: 'bg-yellow-100 text-yellow-800',
    label: 'Pending',
    icon: '⏳'
  },
  PROCESSING: {
    color: 'bg-blue-100 text-blue-800',
    label: 'Processing',
    icon: '🔄'
  },
  READY: {
    color: 'bg-green-100 text-green-800',
    label: 'Ready',
    icon: '✅'
  },
  FAILED: {
    color: 'bg-red-100 text-red-800',
    label: 'Failed',
    icon: '❌'
  }
};

export default function VideoCard({ video, onDelete }: VideoCardProps) {
  const status = statusConfig[video.status];
  const thumbnail = video.thumbnail_url || getYouTubeThumbnail(video.youtube_video_id, 'hq');

  const isClickable = video.status === 'READY';

  const cardContent = (
    <div className={`bg-white rounded-lg shadow overflow-hidden ${isClickable ? 'hover:shadow-lg transition-shadow cursor-pointer' : ''}`}>
      {/* Thumbnail */}
      <div className="relative">
        <img
          src={thumbnail}
          alt={video.title || 'Video thumbnail'}
          className="w-full h-40 object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).src = getYouTubeThumbnail(video.youtube_video_id, 'default');
          }}
        />
        {video.duration_seconds && (
          <span className="absolute bottom-2 right-2 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">
            {formatDuration(video.duration_seconds)}
          </span>
        )}

        {/* Processing overlay */}
        {video.status === 'PROCESSING' && (
          <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div className="text-white text-center">
              <svg className="animate-spin h-8 w-8 mx-auto mb-2" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <p className="text-sm">Processing...</p>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 line-clamp-2 mb-2">
          {video.title || 'Processing...'}
        </h3>

        <div className="flex items-center justify-between">
          <span className={`text-xs px-2 py-1 rounded-full ${status.color}`}>
            {status.icon} {status.label}
          </span>

          <span className="text-xs text-gray-500">
            {new Date(video.created_at).toLocaleDateString()}
          </span>
        </div>

        {video.status === 'FAILED' && video.failure_reason && (
          <p className="text-xs text-red-500 mt-2 line-clamp-2">
            {video.failure_reason}
          </p>
        )}
      </div>
    </div>
  );

  if (isClickable) {
    return (
      <Link href={`/video/${video.id}`}>
        {cardContent}
      </Link>
    );
  }

  return cardContent;
}

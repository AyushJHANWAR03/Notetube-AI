'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { useEffect, useState, Suspense } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { videoApi } from '@/lib/videoApi';

function WatchContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [status, setStatus] = useState<'loading' | 'processing' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState('');

  const videoId = searchParams.get('v');

  useEffect(() => {
    if (!videoId) {
      setStatus('error');
      setErrorMessage('No video ID provided. Make sure the URL has ?v=VIDEO_ID');
      return;
    }

    const submitVideo = async () => {
      try {
        setStatus('processing');
        const youtubeUrl = `https://www.youtube.com/watch?v=${videoId}`;

        // Use guest API if not authenticated, otherwise use authenticated API
        if (user) {
          const response = await videoApi.createVideo(youtubeUrl);
          router.replace(`/video/${response.video.id}`);
        } else {
          const response = await videoApi.createVideoAsGuest(youtubeUrl);
          router.replace(`/video/${response.video.id}`);
        }
      } catch (err: any) {
        console.error('Failed to submit video:', err);

        // Handle guest limit reached
        if (err.response?.data?.requires_auth || err.response?.data?.detail === 'GUEST_LIMIT_REACHED') {
          router.replace('/dashboard?signin=1');
          return;
        }

        // Handle user limit reached
        if (err.response?.status === 403 && err.response?.data?.detail === 'LIMIT_REACHED') {
          router.replace('/dashboard?limit=1');
          return;
        }

        setStatus('error');
        setErrorMessage(err.response?.data?.detail || 'Failed to process video. Please try again.');
      }
    };

    // Wait for auth to settle before submitting
    if (!authLoading) {
      submitVideo();
    }
  }, [videoId, authLoading, user, router]);

  if (status === 'error') {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Something went wrong</h2>
          <p className="text-gray-400 mb-6">{errorMessage}</p>
          <button
            onClick={() => router.push('/dashboard')}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4">
      <div className="text-center">
        <div className="relative w-20 h-20 mx-auto mb-6">
          <div className="absolute inset-0 rounded-full border-4 border-gray-700"></div>
          <div className="absolute inset-0 rounded-full border-4 border-blue-500 border-t-transparent animate-spin"></div>
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">
          {status === 'loading' ? 'Preparing...' : 'Processing your video'}
        </h2>
        <p className="text-gray-400 mb-4">
          {status === 'loading'
            ? 'Getting things ready'
            : 'Generating AI notes, chapters, and flashcards...'}
        </p>
        <p className="text-gray-500 text-sm">
          This usually takes about 30 seconds
        </p>
      </div>
    </div>
  );
}

export default function WatchPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    }>
      <WatchContent />
    </Suspense>
  );
}

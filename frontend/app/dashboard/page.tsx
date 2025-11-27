'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import UserProfile from '@/components/UserProfile';
import VideoInput from '@/components/video/VideoInput';
import VideoList from '@/components/video/VideoList';
import { VideoCreateResponse } from '@/lib/types';

export default function Dashboard() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [lastSubmittedVideo, setLastSubmittedVideo] = useState<VideoCreateResponse | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/');
    }
  }, [user, loading, router]);

  const handleVideoSubmitted = (response: VideoCreateResponse) => {
    setLastSubmittedVideo(response);
    setRefreshTrigger(prev => prev + 1);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
            NoteTube AI
          </h1>
          <UserProfile />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Welcome back, {user.name}!</h2>
          <p className="text-gray-600">
            Transform YouTube videos into complete learning experiences
          </p>
        </div>

        {/* Video Input */}
        <div className="mb-8">
          <VideoInput onVideoSubmitted={handleVideoSubmitted} />
        </div>

        {/* Success message */}
        {lastSubmittedVideo && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-green-800">
              {lastSubmittedVideo.message}
              {lastSubmittedVideo.job_id && (
                <span className="block text-sm text-green-600 mt-1">
                  Processing started... This usually takes 15-30 seconds.
                </span>
              )}
            </p>
          </div>
        )}

        {/* Video List */}
        <div className="mb-8">
          <VideoList refreshTrigger={refreshTrigger} />
        </div>
      </main>
    </div>
  );
}

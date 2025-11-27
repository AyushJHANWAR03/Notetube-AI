'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import UserProfile from '@/components/UserProfile';
import VideoInput from '@/components/video/VideoInput';
import VideoList from '@/components/video/VideoList';

export default function Dashboard() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/');
    }
  }, [user, loading, router]);

  const handleVideoSubmitted = (videoId: string) => {
    // Redirect to video page immediately
    router.push(`/video/${videoId}`);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-500 to-cyan-500 bg-clip-text text-transparent">
            NoteTube AI
          </h1>
          <UserProfile />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Welcome back, {user.name?.split(' ')[0]}!
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Transform YouTube videos into complete learning experiences with AI-powered notes, flashcards, and chapters.
          </p>
        </div>

        {/* Video Input - Centered and Prominent */}
        <div className="max-w-3xl mx-auto mb-16">
          <VideoInput onVideoSubmitted={handleVideoSubmitted} />
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          <div className="p-6 bg-gray-800 border border-gray-700 rounded-xl">
            <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">AI-Powered Notes</h3>
            <p className="text-gray-400">
              Get summaries, bullet points, and key timestamps automatically generated from any video.
            </p>
          </div>

          <div className="p-6 bg-gray-800 border border-gray-700 rounded-xl">
            <div className="w-12 h-12 bg-green-500/20 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Study Flashcards</h3>
            <p className="text-gray-400">
              Test your knowledge with auto-generated flashcards created from video content.
            </p>
          </div>

          <div className="p-6 bg-gray-800 border border-gray-700 rounded-xl">
            <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Video Chapters</h3>
            <p className="text-gray-400">
              Navigate videos easily with AI-generated chapters and timestamps.
            </p>
          </div>
        </div>

        {/* Video List Section */}
        <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
          <VideoList refreshTrigger={refreshTrigger} />
        </div>
      </main>
    </div>
  );
}

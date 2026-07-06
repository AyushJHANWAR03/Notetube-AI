'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import UserProfile from '@/components/UserProfile';
import VideoInput from '@/components/video/VideoInput';
import VideoCard from '@/components/video/VideoCard';
import SignInModal from '@/components/SignInModal';
import LimitReachedModal from '@/components/LimitReachedModal';
import HeroPreview from '@/components/HeroPreview';
import api from '@/lib/api';
import { videoApi } from '@/lib/videoApi';
import { Video } from '@/lib/types';

interface QuotaInfo {
  videos_analyzed: number;
  video_limit: number;
  remaining: number;
}

export default function Dashboard() {
  const { user, loading, login } = useAuth();
  const router = useRouter();
  const [showSignInModal, setShowSignInModal] = useState(false);
  const [showLimitModal, setShowLimitModal] = useState(false);
  const [quota, setQuota] = useState<QuotaInfo | null>(null);
  const [recentVideos, setRecentVideos] = useState<Video[]>([]);
  const [allVideos, setAllVideos] = useState<Video[]>([]);
  const [loadingRecent, setLoadingRecent] = useState(false);
  const [showAllVideos, setShowAllVideos] = useState(false);
  const [totalVideoCount, setTotalVideoCount] = useState(0);

  // Fetch quota and recent videos when user is authenticated
  useEffect(() => {
    if (user) {
      fetchQuota();
      fetchRecentVideos();
    }
  }, [user]);

  const fetchRecentVideos = async () => {
    try {
      setLoadingRecent(true);
      // Fetch 4 for display, total count comes from API
      const response = await videoApi.listVideos({ limit: 4 });
      setRecentVideos(response.videos);
      // Use actual total count from API
      setTotalVideoCount(response.total);
    } catch (err) {
      console.error('Failed to fetch recent videos:', err);
    } finally {
      setLoadingRecent(false);
    }
  };

  const fetchAllVideos = async () => {
    try {
      setLoadingRecent(true);
      const response = await videoApi.listVideos({ limit: 50 });
      setAllVideos(response.videos);
    } catch (err) {
      console.error('Failed to fetch all videos:', err);
    } finally {
      setLoadingRecent(false);
    }
  };

  const handleViewAll = () => {
    if (!showAllVideos) {
      fetchAllVideos();
    }
    setShowAllVideos(!showAllVideos);
  };

  const fetchQuota = async () => {
    try {
      const response = await api.get('/api/users/quota');
      setQuota(response.data);
    } catch (err) {
      console.error('Failed to fetch quota:', err);
    }
  };

  const handleVideoSubmitted = (videoId: string) => {
    router.push(`/video/${videoId}`);
  };

  const handleGenerateNotesAttempt = () => {
    // For authenticated users, check quota
    if (user) {
      if (quota && quota.remaining <= 0) {
        setShowLimitModal(true);
        return false;
      }
      return true;
    }
    // For guests, let them proceed - we'll check on the backend
    return true;
  };

  const handleGuestLimitReached = () => {
    // Guest has used their free video, show sign-in modal (no dismiss option)
    setShowSignInModal(true);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#07080c] relative overflow-hidden">
      {/* Hero glow blob */}
      <div className="hero-glow" aria-hidden="true"></div>

      {/* Header */}
      <header className="border-b border-gray-800/60 relative z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-500 to-cyan-500 bg-clip-text text-transparent">
            NoteTube AI
          </h1>
          {user ? (
            <UserProfile />
          ) : (
            <button
              onClick={() => login()}
              className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Sign in
            </button>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-12 sm:px-6 lg:px-8 relative z-10">
        {/* Hero Section */}
        <div className="text-center mb-10">
          <h2 className="text-4xl md:text-6xl font-bold text-white mb-4 tracking-tight">
            {user ? (
              `Welcome back, ${user.name?.split(' ')[0]}!`
            ) : (
              <>
                Turn any YouTube video into{' '}
                <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
                  study notes
                </span>
              </>
            )}
          </h2>
          <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto">
            {user
              ? 'Paste a video and get AI notes, downloadable PDFs, flashcards, chapters, and chat — in about a minute.'
              : 'AI notes you can download as PDF, smart chapters, flashcards, and chat — from any video in ~60 seconds. No signup needed for your first video.'}
          </p>
        </div>

        {/* Video Input */}
        <div className="max-w-3xl mx-auto mb-12">
          <VideoInput
            onVideoSubmitted={handleVideoSubmitted}
            onBeforeSubmit={handleGenerateNotesAttempt}
            onGuestLimitReached={handleGuestLimitReached}
            isGuest={!user}
          />
        </div>

        {/* Animated output preview — shown to guests and users with no videos */}
        {(!user || (user && recentVideos.length === 0 && !loadingRecent)) && (
          <div className="mb-16">
            <HeroPreview />
          </div>
        )}

        {/* Videos Section - Show for authenticated users with videos */}
        {user && recentVideos.length > 0 && (
          <div className="max-w-6xl mx-auto mb-12">
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-semibold text-white">
                  Your Videos {totalVideoCount > 0 && <span className="text-gray-400 font-normal">({totalVideoCount})</span>}
                </h3>
                {/* Quota indicator - only show when low (<=2) or exhausted */}
                {quota && quota.remaining <= 2 && (
                  quota.remaining === 0 ? (
                    <button
                      onClick={() => setShowLimitModal(true)}
                      className="text-xs text-amber-400 hover:text-amber-300 transition-colors inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-400/10"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      Limit reached
                    </button>
                  ) : (
                    <span className="text-xs text-amber-400/80 px-2 py-0.5 rounded-full bg-amber-400/10">
                      {quota.remaining} left
                    </span>
                  )
                )}
              </div>
              {totalVideoCount > 4 && (
                <button
                  onClick={handleViewAll}
                  className="text-sm text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1"
                >
                  {showAllVideos ? 'Show less' : 'View all'}
                  <svg
                    className={`w-4 h-4 transition-transform ${showAllVideos ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              )}
            </div>

            {/* Video Grid - show 4 or all */}
            <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
              {(showAllVideos ? allVideos : recentVideos.slice(0, 4)).map((video) => (
                <VideoCard key={video.id} video={video} compact />
              ))}
            </div>

            {/* Loading indicator when fetching all */}
            {loadingRecent && showAllVideos && allVideos.length === 0 && (
              <div className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              </div>
            )}
          </div>
        )}

        {/* Bento Features Grid */}
        <div className="mb-16">
          <h3 className="text-center text-sm font-medium text-indigo-400 uppercase tracking-widest mb-2">Everything you get</h3>
          <p className="text-center text-2xl md:text-3xl font-bold text-white mb-8">One video in. A full study kit out.</p>

          <div className="grid grid-cols-1 md:grid-cols-6 gap-4 auto-rows-[minmax(140px,auto)]">
            {/* PDF Notes Download — flagship, large tile */}
            <div className="bento-tile md:col-span-4 md:row-span-2 p-6 bg-gray-900/70 border border-gray-800 rounded-2xl relative overflow-hidden">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(99,102,241,0.12),transparent_55%)] pointer-events-none"></div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-11 h-11 bg-indigo-500/20 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-gradient-to-r from-indigo-600 to-violet-600 text-white uppercase tracking-wider">New</span>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Download Notes as PDF</h3>
              <p className="text-gray-400 text-sm mb-6 max-w-md">Take your study notes offline — one click exports a clean, structured PDF with the summary, key points, and flashcards. Perfect for revision.</p>

              {/* Mock PDF preview */}
              <div className="rounded-xl border border-gray-800 bg-[#0b0d14] p-3 max-w-lg">
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-gray-900 border border-gray-700 mb-3">
                  <div className="w-8 h-10 rounded bg-red-500/15 border border-red-500/30 flex items-center justify-center flex-shrink-0">
                    <span className="text-[9px] font-bold text-red-400">PDF</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-200 truncate">Neural-Networks-Explained_notes.pdf</p>
                    <p className="text-[10px] text-gray-500">TL;DR · Key Points · Flashcards · 3 pages</p>
                  </div>
                </div>
                <div className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-xs font-medium">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download PDF
                </div>
              </div>
            </div>

            {/* Take Me There */}
            <div className="bento-tile md:col-span-2 p-6 bg-gray-900/70 border border-gray-800 rounded-2xl">
              <div className="w-11 h-11 bg-blue-500/15 rounded-xl flex items-center justify-center mb-3">
                <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-white mb-1.5">Take Me There</h3>
              <p className="text-gray-400 text-sm">Describe any moment in plain English — AI semantic search jumps you to the exact timestamp instantly.</p>
            </div>

            {/* Flashcards — flip on hover */}
            <div className="bento-tile md:col-span-2 bg-gray-900/70 border border-gray-800 rounded-2xl flip-card">
              <div className="flip-inner h-full">
                <div className="flip-front p-6 h-full">
                  <div className="w-11 h-11 bg-green-500/15 rounded-xl flex items-center justify-center mb-3">
                    <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-1.5">Flashcards</h3>
                  <p className="text-gray-400 text-sm">Auto-generated Q&amp;A cards from the video. <span className="text-green-400/80">Hover to flip →</span></p>
                </div>
                <div className="flip-back p-6 h-full rounded-2xl bg-gradient-to-br from-green-900/40 to-emerald-900/30 border border-green-700/30 flex flex-col justify-center">
                  <p className="text-xs text-green-300 mb-2 font-medium">Q: What is RAG?</p>
                  <p className="text-sm text-gray-200">Retrieval-Augmented Generation — giving an LLM external knowledge at query time.</p>
                </div>
              </div>
            </div>

            {/* Chat */}
            <div className="bento-tile md:col-span-2 p-6 bg-gray-900/70 border border-gray-800 rounded-2xl">
              <div className="w-11 h-11 bg-purple-500/15 rounded-xl flex items-center justify-center mb-3">
                <svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-white mb-1.5">Chat</h3>
              <p className="text-gray-400 text-sm">Ask anything about the video and get instant, grounded answers.</p>
            </div>

            {/* Breakdown */}
            <div className="bento-tile md:col-span-2 p-6 bg-gray-900/70 border border-gray-800 rounded-2xl">
              <div className="w-11 h-11 bg-orange-500/15 rounded-xl flex items-center justify-center mb-3">
                <svg className="w-6 h-6 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-white mb-1.5">Breakdown</h3>
              <p className="text-gray-400 text-sm">AI-generated chapters with summaries — skim a 1-hour video in 2 minutes.</p>
            </div>

            {/* Transcript */}
            <div className="bento-tile md:col-span-2 p-6 bg-gray-900/70 border border-gray-800 rounded-2xl">
              <div className="w-11 h-11 bg-cyan-500/15 rounded-xl flex items-center justify-center mb-3">
                <svg className="w-6 h-6 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-white mb-1.5">Transcript</h3>
              <p className="text-gray-400 text-sm">Full searchable transcript with timestamps and auto-scroll sync.</p>
            </div>
          </div>
        </div>
      </main>

      {/* Sign In Modal */}
      <SignInModal
        isOpen={showSignInModal}
        onClose={() => setShowSignInModal(false)}
      />

      {/* Limit Reached Modal */}
      {quota && (
        <LimitReachedModal
          isOpen={showLimitModal}
          onClose={() => setShowLimitModal(false)}
          videosAnalyzed={quota.videos_analyzed}
          videoLimit={quota.video_limit}
          onSuccess={() => fetchQuota()}
        />
      )}
    </div>
  );
}

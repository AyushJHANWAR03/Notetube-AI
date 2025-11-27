'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { videoApi, formatDuration } from '@/lib/videoApi';
import { VideoDetail, Chapter } from '@/lib/types';
import Link from 'next/link';

type TabType = 'summary' | 'notes' | 'chapters' | 'flashcards' | 'transcript';

// YouTube Player API types
declare global {
  interface Window {
    YT: {
      Player: new (
        elementId: string,
        config: {
          videoId: string;
          playerVars?: Record<string, number | string>;
          events?: {
            onReady?: (event: { target: YTPlayer }) => void;
            onStateChange?: (event: { data: number }) => void;
          };
        }
      ) => YTPlayer;
      PlayerState: {
        PLAYING: number;
        PAUSED: number;
        ENDED: number;
      };
    };
    onYouTubeIframeAPIReady: () => void;
  }
}

interface YTPlayer {
  seekTo: (seconds: number, allowSeekAhead: boolean) => void;
  playVideo: () => void;
  pauseVideo: () => void;
  getCurrentTime: () => number;
  destroy: () => void;
}

export default function VideoDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [video, setVideo] = useState<VideoDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('summary');
  const [flippedCards, setFlippedCards] = useState<Set<number>>(new Set());
  const [playerReady, setPlayerReady] = useState(false);

  const playerRef = useRef<YTPlayer | null>(null);
  const playerContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (params.id && user) {
      fetchVideo();
    }
  }, [params.id, user]);

  // Load YouTube IFrame API
  useEffect(() => {
    if (!video) return;

    // Check if API is already loaded
    if (window.YT && window.YT.Player) {
      initializePlayer();
      return;
    }

    // Load the API
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);

    window.onYouTubeIframeAPIReady = () => {
      initializePlayer();
    };

    return () => {
      if (playerRef.current) {
        playerRef.current.destroy();
      }
    };
  }, [video?.youtube_video_id]);

  const initializePlayer = useCallback(() => {
    if (!video?.youtube_video_id || !playerContainerRef.current) return;

    // Clear existing player
    if (playerRef.current) {
      playerRef.current.destroy();
    }

    playerRef.current = new window.YT.Player('youtube-player', {
      videoId: video.youtube_video_id,
      playerVars: {
        autoplay: 0,
        modestbranding: 1,
        rel: 0,
      },
      events: {
        onReady: () => {
          setPlayerReady(true);
        },
      },
    });
  }, [video?.youtube_video_id]);

  const fetchVideo = async () => {
    try {
      setLoading(true);
      const data = await videoApi.getVideo(params.id as string);
      setVideo(data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load video');
    } finally {
      setLoading(false);
    }
  };

  const seekToTime = (seconds: number) => {
    if (playerRef.current && playerReady) {
      playerRef.current.seekTo(seconds, true);
      playerRef.current.playVideo();
    }
  };

  const toggleFlashcard = (index: number) => {
    setFlippedCards(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const formatTimestamp = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error}</p>
          <Link href="/dashboard" className="text-blue-600 hover:underline">
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!video || !video.notes) {
    return null;
  }

  const { notes } = video;

  const tabs: { id: TabType; label: string; count?: number }[] = [
    { id: 'summary', label: 'Summary' },
    { id: 'notes', label: 'Full Notes' },
    { id: 'chapters', label: 'Chapters', count: notes.chapters?.length },
    { id: 'flashcards', label: 'Flashcards', count: notes.flashcards?.length },
    { id: 'transcript', label: 'Transcript' },
  ];

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-[1800px] mx-auto px-4 py-3">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <h1 className="text-lg font-semibold text-white line-clamp-1">
              {video.title}
            </h1>
          </div>
        </div>
      </header>

      {/* Main Content - Video Player + Notes Side by Side */}
      <div className="max-w-[1800px] mx-auto">
        <div className="flex flex-col lg:flex-row">
          {/* Left Side - Video Player */}
          <div className="lg:w-[65%] xl:w-[70%]">
            {/* Video Player */}
            <div className="sticky top-0 bg-black">
              <div ref={playerContainerRef} className="relative w-full" style={{ paddingBottom: '56.25%' }}>
                <div
                  id="youtube-player"
                  className="absolute inset-0 w-full h-full"
                />
              </div>
            </div>

            {/* Video Info - Below Player */}
            <div className="p-4 bg-gray-800">
              <h2 className="text-xl font-bold text-white mb-2">{video.title}</h2>
              <div className="flex flex-wrap gap-3 items-center text-sm text-gray-400">
                {video.duration_seconds && (
                  <span>Duration: {formatDuration(video.duration_seconds)}</span>
                )}
                {notes.difficulty_level && (
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    notes.difficulty_level === 'beginner' ? 'bg-green-900 text-green-300' :
                    notes.difficulty_level === 'intermediate' ? 'bg-yellow-900 text-yellow-300' :
                    'bg-red-900 text-red-300'
                  }`}>
                    {notes.difficulty_level}
                  </span>
                )}
              </div>
              {notes.topics && notes.topics.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {notes.topics.map((topic, i) => (
                    <span key={i} className="bg-gray-700 text-gray-300 text-xs px-2 py-1 rounded">
                      {topic}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Chapters - Quick Navigation (Below video on large screens) */}
            {notes.chapters && notes.chapters.length > 0 && (
              <div className="p-4 bg-gray-850 border-t border-gray-700">
                <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wide">Chapters</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2">
                  {notes.chapters.map((chapter, i) => (
                    <button
                      key={i}
                      onClick={() => seekToTime(chapter.start_time)}
                      className="flex items-center gap-2 p-2 rounded hover:bg-gray-700 transition-colors text-left group"
                    >
                      <span className="text-blue-400 font-mono text-xs whitespace-nowrap">
                        {formatTimestamp(chapter.start_time)}
                      </span>
                      <span className="text-gray-300 text-sm line-clamp-1 group-hover:text-white">
                        {chapter.title}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Side - Notes & Content */}
          <div className="lg:w-[35%] xl:w-[30%] lg:border-l border-gray-700 bg-gray-800 lg:h-screen lg:overflow-y-auto">
            {/* Tabs */}
            <div className="sticky top-0 bg-gray-800 z-10 border-b border-gray-700">
              <nav className="flex overflow-x-auto">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    {tab.label}
                    {tab.count !== undefined && (
                      <span className="ml-1.5 bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded text-xs">
                        {tab.count}
                      </span>
                    )}
                  </button>
                ))}
              </nav>
            </div>

            {/* Tab Content */}
            <div className="p-4">
              {/* Summary Tab */}
              {activeTab === 'summary' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wide">Summary</h3>
                    <p className="text-gray-200 leading-relaxed">{notes.summary}</p>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wide">Key Points</h3>
                    <ul className="space-y-2">
                      {notes.bullets.map((bullet, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-blue-400 mt-1">•</span>
                          <span className="text-gray-300">{bullet}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {notes.action_items && notes.action_items.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wide">Action Items</h3>
                      <ul className="space-y-2">
                        {notes.action_items.map((item, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-green-400">✓</span>
                            <span className="text-gray-300">{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {notes.key_timestamps && notes.key_timestamps.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wide">Key Moments</h3>
                      <div className="space-y-1">
                        {notes.key_timestamps.map((ts, i) => (
                          <button
                            key={i}
                            onClick={() => seekToTime(ts.seconds)}
                            className="flex items-center gap-3 w-full p-2 hover:bg-gray-700 rounded transition-colors text-left"
                          >
                            <span className="text-blue-400 font-mono text-sm">{ts.time}</span>
                            <span className="text-gray-300 text-sm">{ts.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Full Notes Tab */}
              {activeTab === 'notes' && notes.markdown_notes && (
                <div className="prose prose-invert prose-sm max-w-none">
                  <div
                    className="text-gray-300"
                    dangerouslySetInnerHTML={{
                      __html: notes.markdown_notes
                        .replace(/^### (.*$)/gm, '<h3 class="text-lg font-semibold mt-4 mb-2 text-white">$1</h3>')
                        .replace(/^## (.*$)/gm, '<h2 class="text-xl font-bold mt-6 mb-3 text-white">$1</h2>')
                        .replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mt-6 mb-4 text-white">$1</h1>')
                        .replace(/^\- (.*$)/gm, '<li class="ml-4 text-gray-300">$1</li>')
                        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
                        .replace(/\n\n/g, '</p><p class="mb-3 text-gray-300">')
                    }}
                  />
                </div>
              )}

              {/* Chapters Tab */}
              {activeTab === 'chapters' && notes.chapters && (
                <div className="space-y-3">
                  {notes.chapters.map((chapter, i) => (
                    <button
                      key={i}
                      onClick={() => seekToTime(chapter.start_time)}
                      className="w-full text-left p-3 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <h4 className="font-medium text-white mb-1">
                            {i + 1}. {chapter.title}
                          </h4>
                          {chapter.summary && (
                            <p className="text-gray-400 text-sm">{chapter.summary}</p>
                          )}
                        </div>
                        <span className="text-blue-400 font-mono text-sm whitespace-nowrap">
                          {formatTimestamp(chapter.start_time)}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Flashcards Tab */}
              {activeTab === 'flashcards' && notes.flashcards && (
                <div>
                  <p className="text-gray-400 text-sm mb-4">Click a card to reveal the answer</p>
                  <div className="space-y-3">
                    {notes.flashcards.map((card, i) => (
                      <div
                        key={i}
                        onClick={() => toggleFlashcard(i)}
                        className="cursor-pointer"
                      >
                        <div className={`rounded-lg p-4 min-h-[100px] transition-all ${
                          flippedCards.has(i)
                            ? 'bg-green-900/30 border border-green-700'
                            : 'bg-gray-700 border border-gray-600 hover:border-blue-500'
                        }`}>
                          {flippedCards.has(i) ? (
                            <>
                              <p className="text-xs text-green-400 mb-1">Answer</p>
                              <p className="text-gray-200">{card.back}</p>
                            </>
                          ) : (
                            <>
                              <p className="text-xs text-blue-400 mb-1">Question</p>
                              <p className="text-white font-medium">{card.front}</p>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Transcript Tab */}
              {activeTab === 'transcript' && video.transcript && (
                <div>
                  <p className="text-gray-400 text-sm mb-4">
                    Language: {video.transcript.language_code} | Provider: {video.transcript.provider}
                  </p>
                  <div className="bg-gray-700 rounded-lg p-4 max-h-[600px] overflow-y-auto">
                    <p className="text-gray-300 whitespace-pre-wrap leading-relaxed text-sm">
                      {video.transcript.raw_text}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

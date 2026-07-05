'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { videoApi, formatDuration, getYouTubeThumbnail } from '@/lib/videoApi';
import { VideoDetail, Chapter, Job, SeekResponse } from '@/lib/types';
import Link from 'next/link';
import TranscriptPanel from '@/components/video/TranscriptPanel';
import ChatPanel from '@/components/video/ChatPanel';
import ProcessingPanel from '@/components/video/ProcessingPanel';
import { track } from '@/lib/mixpanel';

type TabType = 'summary' | 'transcript' | 'chat' | 'study';
type StudySection = 'chapters' | 'flashcards';

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
  const { user, loading: authLoading, login } = useAuth();

  const [video, setVideo] = useState<VideoDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('summary');
  const [studySection, setStudySection] = useState<StudySection>('chapters');
  const [downloadingPdf, setDownloadingPdf] = useState<'detailed' | 'short' | null>(null);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const [flippedCards, setFlippedCards] = useState<Set<number>>(new Set());
  const [playerReady, setPlayerReady] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [pollingCount, setPollingCount] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [autoScroll, setAutoScroll] = useState(true);

  // Chat state for explain flow
  const [pendingChatMessage, setPendingChatMessage] = useState<string | null>(null);

  // Take Me There state
  const [seekQuery, setSeekQuery] = useState('');
  const [isSeekSearching, setIsSeekSearching] = useState(false);
  const [seekResult, setSeekResult] = useState<SeekResponse | null>(null);
  const [seekError, setSeekError] = useState<string | null>(null);

  // Celebration state - show briefly when processing completes
  const [showCelebration, setShowCelebration] = useState(false);

  // Progress percentage from job
  const [progressPercent, setProgressPercent] = useState(0);

  // Breakdown tab discovery tip - show once on first chapter click
  const [showBreakdownTip, setShowBreakdownTip] = useState(false);

  const playerRef = useRef<YTPlayer | null>(null);
  const playerContainerRef = useRef<HTMLDivElement>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Handle post-auth-callback navigation
    // Note: We no longer redirect for guests - they can view guest videos
    if (!authLoading && !user) {
      // Check for recent auth flag - if user just logged in, clear it
      const recentAuth = sessionStorage.getItem('recentAuth');
      if (recentAuth) {
        sessionStorage.removeItem('recentAuth');
      }
      // Don't redirect - allow guests to view videos
      // The API will return 401 if they try to access a non-guest video
    }
  }, [user, authLoading]);

  // Initial fetch - always try to fetch if we have a video ID
  // The API will handle access control (guest videos are accessible without auth)
  useEffect(() => {
    if (params.id) {
      fetchVideo();
    }
  }, [params.id]);

  // Map job status to step number
  const getStepFromJobStatus = (jobStatus: Job['status']): number => {
    switch (jobStatus) {
      case 'PENDING':
        return 0; // Fetching video data
      case 'FETCHING_TRANSCRIPT':
        return 1; // Extracting transcript
      case 'GENERATING_NOTES':
        return 2; // Generating AI notes (steps 2-4 happen in parallel)
      case 'COMPLETED':
        return 4; // All done
      case 'FAILED':
        return currentStep; // Keep current step on failure
      default:
        return 0;
    }
  };

  // Polling for processing status - uses /status endpoint to get real job progress
  useEffect(() => {
    const isStillProcessing = video && (video.status === 'PENDING' || video.status === 'PROCESSING');

    if (isStillProcessing) {
      console.log('[Polling] Video is processing, starting poll interval');

      // Poll every 2 seconds using the /status endpoint
      pollingRef.current = setInterval(async () => {
        console.log('[Polling] Fetching video status...');
        try {
          const statusResponse = await videoApi.getVideoStatus(params.id as string);
          const { video: videoData, jobs } = statusResponse;
          console.log('[Polling] Got video status:', videoData.status);

          // Get the latest job and update step based on real job status
          if (jobs && jobs.length > 0) {
            const latestJob = jobs[jobs.length - 1];
            console.log('[Polling] Job status:', latestJob.status, 'Progress:', latestJob.progress);
            const newStep = getStepFromJobStatus(latestJob.status);
            setCurrentStep(newStep);
            // Update progress percentage from job
            if (latestJob.progress !== undefined) {
              setProgressPercent(latestJob.progress);
            }
          }

          // If status changed to READY, show celebration then fetch full video
          if (videoData.status === 'READY') {
            console.log('[Polling] Video is READY, showing celebration...');
            setCurrentStep(4); // Mark all steps complete
            setShowCelebration(true);
            track('video_processing_succeeded', { video_id: params.id as string });

            // Clear polling immediately
            if (pollingRef.current) {
              clearInterval(pollingRef.current);
              pollingRef.current = null;
            }

            // After celebration, fetch full video and hide celebration
            setTimeout(async () => {
              const fullVideo = await videoApi.getVideo(params.id as string);
              setVideo(fullVideo);
              setShowCelebration(false);
            }, 1200);
          } else if (videoData.status === 'FAILED') {
            console.log('[Polling] Video FAILED');
            setVideo(prev => prev ? { ...prev, status: 'FAILED', failure_reason: videoData.failure_reason } : null);
            track('video_processing_failed', {
              video_id: params.id as string,
              failure_reason: videoData.failure_reason || 'unknown',
            });
            if (pollingRef.current) {
              clearInterval(pollingRef.current);
              pollingRef.current = null;
            }
          }

          setPollingCount(prev => prev + 1);
        } catch (err) {
          console.error('[Polling] Error fetching video status:', err);
        }
      }, 2000);

      return () => {
        console.log('[Polling] Cleanup - clearing interval');
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
      };
    } else {
      console.log('[Polling] Video not processing, status:', video?.status);
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [video?.status, params.id]);

  // Load YouTube IFrame API
  useEffect(() => {
    if (!video?.youtube_video_id) return;

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

  // Track current video time for transcript sync
  useEffect(() => {
    if (!playerReady || !playerRef.current) return;

    const interval = setInterval(() => {
      try {
        const time = playerRef.current?.getCurrentTime() || 0;
        setCurrentTime(time);
      } catch (e) {
        // Player might not be ready
      }
    }, 500);

    return () => clearInterval(interval);
  }, [playerReady]);

  const fetchVideo = async (isPolling = false) => {
    try {
      if (!isPolling) setLoading(true);
      const data = await videoApi.getVideo(params.id as string);
      setVideo(data);
      setError(null);
      if (!isPolling) {
        track('video_opened', {
          video_id: data.id,
          status: data.status,
          duration_seconds: data.duration_seconds,
          is_guest: !user,
        });
        if (data.status === 'FAILED') {
          track('video_failed_view', {
            video_id: data.id,
            failure_reason: data.failure_reason || 'unknown',
          });
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load video');
    } finally {
      if (!isPolling) setLoading(false);
    }
  };

  const seekToTime = (seconds: number) => {
    if (playerRef.current && playerReady) {
      playerRef.current.seekTo(seconds, true);
      playerRef.current.playVideo();
    }
  };

  // Handle explain from transcript - switch to chat tab with the selected text
  const handleExplain = (text: string) => {
    setPendingChatMessage(text);
    setActiveTab('chat');
    track('explain_with_ai_clicked', { video_id: video?.id, text_length: text.length });
  };

  // Handle sign in from Chat/Notes tabs - return to current video after login
  const handleSignIn = () => {
    login(`/video/${params.id}`);
  };

  // Take Me There search handler - accepts query from TranscriptPanel
  const handleSeekSearch = async (query?: string) => {
    const searchTerm = query || seekQuery;
    if (!searchTerm.trim() || !video?.transcript?.segments?.length) return;

    setSeekQuery(searchTerm);
    setIsSeekSearching(true);
    setSeekError(null);
    setSeekResult(null);

    try {
      const result = await videoApi.seekToTopic(video.id, searchTerm);
      setSeekResult(result);
      track('take_me_there_used', { video_id: video.id, query: searchTerm, confidence: result.confidence });

      // Auto-seek if a valid timestamp was found
      if (result.timestamp !== null && result.confidence !== 'none') {
        seekToTime(result.timestamp);
      }
    } catch (err: any) {
      // Always show a friendly message - don't expose technical errors to users
      setSeekError('Could not find that moment. Try different keywords.');
    } finally {
      setIsSeekSearching(false);
    }
  };

  // Clear search results
  const clearSeekSearch = () => {
    setSeekQuery('');
    setSeekResult(null);
    setSeekError(null);
  };

  // Handle chapter click - show breakdown tip on first click
  const handleChapterClick = (startTime: number) => {
    seekToTime(startTime);

    // Show breakdown tip on first chapter click (if not dismissed)
    const dismissed = localStorage.getItem('breakdownTipDismissed');
    if (!dismissed) {
      setShowBreakdownTip(true);
    }
  };

  // Dismiss breakdown tip and save to localStorage
  const dismissBreakdownTip = () => {
    localStorage.setItem('breakdownTipDismissed', 'true');
    setShowBreakdownTip(false);
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

  // Fetch AI-written notes (cached after first generation), render to PDF client-side
  const handleDownloadPdf = async (style: 'detailed' | 'short') => {
    if (!video?.notes || downloadingPdf) return;
    setShowDownloadMenu(false);
    setDownloadingPdf(style);
    try {
      const api = (await import('@/lib/api')).default;
      const response = await api.post(`/api/videos/${video.id}/study-notes?style=${style}`);
      const markdown: string = response.data.markdown;

      const [{ pdf }, { default: NotesPDF }] = await Promise.all([
        import('@react-pdf/renderer'),
        import('@/components/pdf/NotesPDF'),
      ]);
      const blob = await pdf(
        <NotesPDF
          videoTitle={video.title || 'Video Notes'}
          youtubeVideoId={video.youtube_video_id}
          markdown={markdown}
          flashcards={style === 'detailed' ? video.notes.flashcards : undefined}
        />
      ).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const suffix = style === 'short' ? 'Quick Revision' : 'Study Notes';
      a.download = `${(video.title || 'notes').replace(/[^\w\s-]/g, '').trim().slice(0, 60)} - ${suffix}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      track('notes_pdf_downloaded', { video_id: video.id, style, cached: response.data.cached });
    } catch (err) {
      console.error('PDF generation failed:', err);
    } finally {
      setDownloadingPdf(null);
    }
  };

  const formatTimestamp = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#07080c]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#07080c] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <Link href="/dashboard" className="text-blue-400 hover:underline">
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!video) {
    return null;
  }

  const isProcessing = video.status === 'PENDING' || video.status === 'PROCESSING';
  const isReady = video.status === 'READY' && video.notes;
  const isFailed = video.status === 'FAILED';

// Render Failed State - friendly "Oops" message for no captions
  const renderFailedState = () => {
    const isNoCaptions = video.failure_reason?.toLowerCase().includes('caption') ||
                         video.failure_reason?.toLowerCase().includes('subtitle');

    return (
      <div className="lg:w-[40%] xl:w-[38%] lg:border-l border-gray-800/60 bg-[#0b0d14] lg:h-screen flex flex-col items-center justify-center p-8">
        <div className="w-20 h-20 rounded-full bg-gray-700 flex items-center justify-center mb-6">
          <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.182 16.318A4.486 4.486 0 0012.016 15a4.486 4.486 0 00-3.198 1.318M21 12a9 9 0 11-18 0 9 9 0 0118 0zM9.75 9.75c0 .414-.168.75-.375.75S9 10.164 9 9.75 9.168 9 9.375 9s.375.336.375.75zm-.375 0h.008v.015h-.008V9.75zm5.625 0c0 .414-.168.75-.375.75s-.375-.336-.375-.75.168-.75.375-.75.375.336.375.75zm-.375 0h.008v.015h-.008V9.75z" />
          </svg>
        </div>
        <h3 className="text-xl font-semibold text-white mb-2">Oops!</h3>
        <p className="text-gray-400 text-center mb-6 max-w-sm">
          {isNoCaptions
            ? "This video doesn't have captions available. Please try a video with captions or subtitles enabled."
            : (video.failure_reason || 'Something went wrong while processing this video.')}
        </p>
        <Link
          href="/dashboard"
          className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
        >
          Try Another Video
        </Link>
      </div>
    );
  };

  // Render Notes Content (when READY)
  const renderNotesContent = () => {
    if (!video.notes) return null;
    const { notes } = video;

    const tabs: { id: TabType; label: string; icon: string; count?: number }[] = [
      { id: 'summary', label: 'Summary', icon: '📝' },
      { id: 'transcript', label: 'Transcript', icon: '📜' },
      { id: 'chat', label: 'Chat', icon: '💬' },
      { id: 'study', label: 'Study', icon: '🎓' },
    ];

    return (
      <div className="lg:w-[40%] xl:w-[38%] lg:border-l border-gray-800/60 bg-[#0b0d14] h-full flex flex-col overflow-hidden">
        {/* Tabs — pill style */}
        <div className="flex-shrink-0 bg-[#0b0d14] z-10 border-b border-gray-800/60 px-3 py-2.5">
          <nav className="flex gap-1.5 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  track('feature_tab_clicked', { tab: tab.id, video_id: video?.id });
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium whitespace-nowrap rounded-full transition-all ${
                  activeTab === tab.id
                    ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/40'
                    : 'text-gray-400 border border-transparent hover:text-gray-200 hover:bg-gray-800/60'
                }`}
              >
                <span className="text-xs">{tab.icon}</span>
                {tab.label}
                {tab.count !== undefined && (
                  <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                    activeTab === tab.id ? 'bg-indigo-500/25 text-indigo-200' : 'bg-gray-800 text-gray-400'
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className={`flex-1 min-h-0 ${activeTab === 'chat' ? '' : 'overflow-y-auto p-4'}`}>
          {/* Summary Tab */}
          {activeTab === 'summary' && (() => {
            const enrichedBullets = notes.bullets.some(b => typeof b !== 'string');
            return (
            <div className="space-y-4">
              {/* TL;DR card */}
              {notes.tldr && (
                <div className="rounded-2xl bg-gradient-to-r from-indigo-900/40 to-violet-900/30 border border-indigo-700/40 p-4">
                  <p className="text-[10px] font-semibold text-indigo-400 uppercase tracking-widest mb-1.5">TL;DR</p>
                  <p className="text-base text-white font-medium leading-relaxed">{notes.tldr}</p>
                </div>
              )}

              {/* Overview */}
              <div className="rounded-2xl bg-gray-900/50 border border-gray-800 p-4">
                <h4 className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-widest">📝 Overview</h4>
                <p className="text-sm text-gray-200 leading-relaxed">{notes.summary}</p>
              </div>

              {/* Key Points — emoji + timestamp chips */}
              <div className="rounded-2xl bg-gray-900/50 border border-gray-800 p-4">
                <h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-widest">🔑 Key Points</h4>
                <ul className="space-y-2.5">
                  {notes.bullets.map((bullet, i) => {
                    if (typeof bullet === 'string') {
                      return (
                        <li key={i} className="flex gap-2">
                          <span className="text-indigo-400 text-sm leading-relaxed">•</span>
                          <span className="text-sm text-gray-300 leading-relaxed">{bullet}</span>
                        </li>
                      );
                    }
                    return (
                      <li key={i} className="flex items-start gap-2.5">
                        <span className="text-base leading-snug flex-shrink-0">{bullet.emoji || '•'}</span>
                        <span className="text-sm text-gray-300 leading-relaxed flex-1">
                          {bullet.text}
                          {bullet.seconds !== undefined && bullet.time && (
                            <button
                              onClick={() => seekToTime(bullet.seconds!)}
                              className="ml-2 inline-flex items-center px-1.5 py-0.5 text-[11px] font-mono bg-indigo-500/15 hover:bg-indigo-500/30 text-indigo-300 rounded border border-indigo-500/30 transition-colors align-middle"
                            >
                              {bullet.time}
                            </button>
                          )}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>

              {/* Action Items */}
              {notes.action_items && notes.action_items.length > 0 && (
                <div className="rounded-2xl bg-gray-900/50 border border-gray-800 p-4">
                  <h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-widest">🎯 Action Items</h4>
                  <ul className="space-y-2">
                    {notes.action_items.map((item, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-green-400 text-sm leading-relaxed">✓</span>
                        <span className="text-sm text-gray-300 leading-relaxed">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Key Moments — only for legacy videos without per-bullet timestamps */}
              {!enrichedBullets && notes.key_timestamps && notes.key_timestamps.length > 0 && (
                <div className="rounded-2xl bg-gray-900/50 border border-gray-800 p-4">
                  <h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-widest">⏱️ Key Moments</h4>
                  <div className="space-y-1">
                    {notes.key_timestamps.map((ts, i) => (
                      <button
                        key={i}
                        onClick={() => seekToTime(ts.seconds)}
                        className="flex items-center gap-3 w-full p-2 rounded-lg bg-gray-900/70 border border-gray-800 hover:border-indigo-500/40 transition-colors text-left"
                      >
                        <span className="text-indigo-400 font-mono text-sm">{ts.time}</span>
                        <span className="text-gray-300 text-sm">{ts.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
            );
          })()}

          {/* Study Tab — Breakdown + Flashcards (Notes coming later) */}
          {activeTab === 'study' && (
            <div className="mb-4 flex items-center justify-between gap-2 flex-wrap">
              <div className="flex gap-1.5 p-1 bg-gray-900/70 border border-gray-800 rounded-xl w-fit">
                {([
                  { id: 'chapters' as StudySection, label: '📑 Breakdown', count: notes.chapters?.length },
                  { id: 'flashcards' as StudySection, label: '🃏 Flashcards', count: notes.flashcards?.length },
                ]).map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setStudySection(s.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-all ${
                      studySection === s.id
                        ? 'bg-indigo-600/80 text-white'
                        : 'text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    {s.label}
                    {s.count !== undefined && (
                      <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                        studySection === s.id ? 'bg-white/20 text-white' : 'bg-gray-800 text-gray-400'
                      }`}>
                        {s.count}
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {/* Download Notes dropdown */}
              <div className="relative">
                <button
                  onClick={() => setShowDownloadMenu(!showDownloadMenu)}
                  disabled={downloadingPdf !== null}
                  className="flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white transition-all shadow-lg shadow-indigo-600/20 disabled:opacity-60"
                >
                  {downloadingPdf ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      {downloadingPdf === 'short' ? 'Writing revision sheet...' : 'Writing notes...'}
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Download Notes
                      <svg className={`w-3.5 h-3.5 transition-transform ${showDownloadMenu ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </>
                  )}
                </button>

                {showDownloadMenu && !downloadingPdf && (
                  <div className="absolute right-0 mt-2 w-64 bg-[#0b0d14] border border-gray-800 rounded-xl shadow-2xl z-50 overflow-hidden p-1.5">
                    <button
                      onClick={() => handleDownloadPdf('detailed')}
                      className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-gray-800/80 transition-colors"
                    >
                      <p className="text-sm font-medium text-white">📚 Detailed Notes</p>
                      <p className="text-xs text-gray-500 mt-0.5">Complete study notes with explanations &amp; flashcards</p>
                    </button>
                    <button
                      onClick={() => handleDownloadPdf('short')}
                      className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-gray-800/80 transition-colors"
                    >
                      <p className="text-sm font-medium text-white">⚡ Short Notes</p>
                      <p className="text-xs text-gray-500 mt-0.5">One-page revision sheet for quick review</p>
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Study → Breakdown */}
          {activeTab === 'study' && studySection === 'chapters' && notes.chapters && (
            <div className="space-y-3">
              {notes.chapters.map((chapter, i) => (
                <button
                  key={i}
                  onClick={() => seekToTime(chapter.start_time)}
                  className="w-full text-left p-3 rounded-xl bg-gray-900/70 border border-gray-800 hover:border-indigo-500/40 transition-colors"
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
                    <span className="text-indigo-400 font-mono text-sm whitespace-nowrap">
                      {formatTimestamp(chapter.start_time)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Study → Flashcards */}
          {activeTab === 'study' && studySection === 'flashcards' && notes.flashcards && (
            <div>
              <p className="text-gray-400 text-sm mb-4">Click a card to reveal the answer</p>
              <div className="space-y-3">
                {notes.flashcards.map((card, i) => (
                  <div
                    key={i}
                    onClick={() => toggleFlashcard(i)}
                    className="cursor-pointer"
                  >
                    <div className={`rounded-xl p-4 min-h-[100px] transition-all ${
                      flippedCards.has(i)
                        ? 'bg-green-900/25 border border-green-700/60'
                        : 'bg-gray-900/70 border border-gray-800 hover:border-indigo-500/50'
                    }`}>
                      {flippedCards.has(i) ? (
                        <>
                          <p className="text-xs text-green-400 mb-1">Answer</p>
                          <p className="text-gray-200">{card.back}</p>
                        </>
                      ) : (
                        <>
                          <p className="text-xs text-indigo-400 mb-1">Question</p>
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
            <TranscriptPanel
              segments={video.transcript.segments || []}
              currentTime={currentTime}
              onSeek={seekToTime}
              autoScroll={autoScroll}
              onToggleAutoScroll={() => setAutoScroll(!autoScroll)}
              onExplain={handleExplain}
              onTakeMeThere={handleSeekSearch}
              isSearching={isSeekSearching}
              searchResult={seekResult}
              searchError={seekError}
              onClearSearch={clearSeekSearch}
            />
          )}

          {/* Chat Tab */}
          {activeTab === 'chat' && (
            <ChatPanel
              videoId={video.id}
              videoTitle={video.title}
              suggestedPrompts={notes.suggested_prompts}
              pendingMessage={pendingChatMessage || undefined}
              onPendingMessageHandled={() => setPendingChatMessage(null)}
              onSeek={seekToTime}
              isGuest={!user}
              onSignIn={handleSignIn}
            />
          )}
        </div>

      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#07080c]">
      {/* Floating back button + processing badge (no header — video gets full height) */}
      <div className="fixed top-3 left-3 z-50 flex items-center gap-2">
        <Link
          href="/dashboard"
          className="w-9 h-9 flex items-center justify-center rounded-full bg-black/60 backdrop-blur border border-gray-700/60 text-gray-300 hover:text-white hover:border-indigo-500/60 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        {isProcessing && (
          <span className="px-2.5 py-1 text-xs bg-black/60 backdrop-blur border border-indigo-700/50 text-indigo-300 rounded-full flex items-center gap-1.5">
            <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse"></div>
            Processing
          </span>
        )}
      </div>

      {/* Main Content - Video Player + Notes Side by Side */}
      <div className="max-w-[1600px] mx-auto h-screen overflow-hidden">
        <div className="flex flex-col lg:flex-row h-full">
          {/* Left Side - Video Player (scrollable independently) */}
          <div className="lg:w-[60%] xl:w-[62%] h-full overflow-y-auto">
            {/* Video Player - Compact like reference */}
            <div className="bg-black">
              <div ref={playerContainerRef} className="relative w-full mx-auto" style={{ paddingBottom: '56.25%', maxHeight: '56vh' }}>
                <div
                  id="youtube-player"
                  className="absolute inset-0 w-full h-full"
                />
              </div>
            </div>

            {/* Video Info - Below Player (Compact) */}
            <div className="px-4 py-3 bg-[#0b0d14]">
              {video.title ? (
                <h2 className="text-lg font-bold text-white line-clamp-2">{video.title}</h2>
              ) : isProcessing ? (
                <p className="text-sm text-gray-400 flex items-center gap-2">
                  <span className="text-indigo-400">▶</span>
                  You can watch the video while we prepare your notes
                </p>
              ) : null}
              {/* Topics row with Take Me There button */}
              {isReady && (
                <div className="flex items-center justify-between gap-4 mt-2">
                  {/* Topic tags */}
                  <div className="flex flex-wrap gap-2 flex-1">
                    {video.notes?.topics && video.notes.topics.map((topic, i) => (
                      <span key={i} className="bg-gray-800/80 border border-gray-700 text-gray-300 text-xs px-2 py-1 rounded-full">
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Chapters - Quick Navigation (Only when ready) */}
            {isReady && video.notes?.chapters && video.notes.chapters.length > 0 && (
              <div className="px-4 py-2 bg-[#0b0d14] border-t border-gray-800/60">
                <h3 className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">Chapters</h3>

                {/* Discovery Tip Toast - shown on first chapter click */}
                {showBreakdownTip && (
                  <div className="flex items-center justify-between bg-indigo-900/30 border border-indigo-700/50 rounded-xl px-3 py-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-yellow-400 text-sm">💡</span>
                      <span className="text-sm text-indigo-200">
                        Want detailed summaries? Check the{' '}
                        <button
                          onClick={() => {
                            setActiveTab('study');
                            setStudySection('chapters');
                            dismissBreakdownTip();
                          }}
                          className="underline font-medium hover:text-indigo-100"
                        >
                          Study
                        </button>{' '}
                        tab
                      </span>
                    </div>
                    <button
                      onClick={dismissBreakdownTip}
                      className="text-gray-400 hover:text-white p-1 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                )}

                <div className="flex flex-wrap gap-1.5">
                  {video.notes.chapters.map((chapter, i) => (
                    <button
                      key={i}
                      onClick={() => handleChapterClick(chapter.start_time)}
                      className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-gray-800/60 border border-gray-800 hover:border-indigo-500/40 transition-colors text-left group"
                    >
                      <span className="text-indigo-400 font-mono text-xs">
                        {formatTimestamp(chapter.start_time)}
                      </span>
                      <span className="text-gray-300 text-xs group-hover:text-white">
                        {chapter.title}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

          </div>

          {/* Right Side - Processing Animation or Notes */}
          {(isProcessing || showCelebration) && (
            <ProcessingPanel
              currentStep={currentStep}
              showCelebration={showCelebration}
              progressPercent={progressPercent}
            />
          )}
          {isFailed && renderFailedState()}
          {isReady && renderNotesContent()}
        </div>
      </div>
    </div>
  );
}

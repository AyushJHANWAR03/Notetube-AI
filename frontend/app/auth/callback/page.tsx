'use client';

import { useEffect, useState, Suspense, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { videoApi } from '@/lib/videoApi';
import { identifyUser, track } from '@/lib/mixpanel';

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setUser } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState('Completing sign in...');
  const processedRef = useRef(false);

  useEffect(() => {
    // Prevent double execution in React Strict Mode - OAuth codes can only be used once!
    if (processedRef.current) return;
    processedRef.current = true;

    const handleCallback = async () => {
      const code = searchParams.get('code');

      if (!code) {
        setError('No authorization code received');
        return;
      }

      try {
        // Call backend callback endpoint
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/auth/google/callback?code=${code}`
        );

        if (!response.ok) {
          throw new Error('Authentication failed');
        }

        const data = await response.json();

        // Store token and user
        localStorage.setItem('token', data.access_token);
        setUser(data.user);

        // Mixpanel: bridge guest device_id to user_id (Simplified ID Merge)
        identifyUser(data.user.id, {
          $email: data.user.email,
          $name: data.user.name,
        });
        track('sign_in_completed', {
          sign_in_method: 'google',
          is_new_user: data.is_new_user ?? false,
        });

        // Set flag to indicate recent auth - prevents redirect race condition on video page
        sessionStorage.setItem('recentAuth', 'true');

        // Check for return URL (for returning to current page after login)
        const returnUrl = localStorage.getItem('authReturnUrl');
        if (returnUrl) {
          localStorage.removeItem('authReturnUrl');
          router.push(returnUrl);
          return;
        }

        // Check for pending video URL
        const pendingVideoUrl = localStorage.getItem('pendingVideoUrl');
        if (pendingVideoUrl) {
          setStatus('Processing your video...');
          localStorage.removeItem('pendingVideoUrl');

          try {
            // Create the video
            const videoResponse = await videoApi.createVideo(pendingVideoUrl);
            // Redirect to video page
            router.push(`/video/${videoResponse.video.id}`);
            return;
          } catch (videoErr) {
            console.error('Failed to process pending video:', videoErr);
            // If video creation fails, still go to dashboard
          }
        }

        // Redirect to dashboard if no pending video
        router.push('/dashboard');
      } catch (err) {
        console.error('Auth callback error:', err);
        setError('Authentication failed. Please try again.');
        setTimeout(() => {
          router.push('/');
        }, 3000);
      }
    };

    handleCallback();
  }, [searchParams, router, setUser]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#07080c] relative overflow-hidden">
        <div className="hero-glow" aria-hidden="true"></div>
        <div className="text-center relative z-10">
          <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-red-500/15 border border-red-500/40 flex items-center justify-center">
            <svg className="w-7 h-7 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Authentication Error</h1>
          <p className="text-gray-400">{error}</p>
          <p className="text-sm text-gray-600 mt-2">Redirecting to home...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#07080c] relative overflow-hidden">
      <div className="hero-glow" aria-hidden="true"></div>
      <div className="text-center relative z-10">
        {/* Gradient spinner ring around logo */}
        <div className="relative w-20 h-20 mx-auto mb-6">
          <div className="absolute inset-0 rounded-full bg-gradient-to-r from-indigo-500 via-violet-500 to-cyan-400 animate-spin [mask:radial-gradient(farthest-side,transparent_calc(100%-3px),#000_0)]"></div>
          <div className="absolute inset-2 rounded-full bg-[#0b0d14] flex items-center justify-center text-2xl">
            ✨
          </div>
        </div>

        <h1 className="text-2xl font-bold mb-2 bg-gradient-to-r from-indigo-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
          {status}
        </h1>
        <p className="text-gray-400 mb-8">Please wait while we set up your account</p>

        {/* What's waiting for them */}
        <div className="flex items-center justify-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-900/70 border border-gray-800">📝 AI Notes</span>
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-900/70 border border-gray-800">🃏 Flashcards</span>
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-900/70 border border-gray-800">💬 AI Chat</span>
        </div>
      </div>
    </div>
  );
}

export default function AuthCallback() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-[#07080c]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
      </div>
    }>
      <AuthCallbackContent />
    </Suspense>
  );
}

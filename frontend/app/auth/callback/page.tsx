'use client';

import { useEffect, useState, Suspense, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { videoApi } from '@/lib/videoApi';

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

        // Set flag to indicate recent auth - prevents redirect race condition on video page
        sessionStorage.setItem('recentAuth', 'true');

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
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Authentication Error</h1>
          <p className="text-gray-600">{error}</p>
          <p className="text-sm text-gray-500 mt-2">Redirecting to home...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-900">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <h1 className="text-2xl font-bold mb-2 text-white">{status}</h1>
        <p className="text-gray-400">Please wait while we set up your account</p>
      </div>
    </div>
  );
}

export default function AuthCallback() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    }>
      <AuthCallbackContent />
    </Suspense>
  );
}

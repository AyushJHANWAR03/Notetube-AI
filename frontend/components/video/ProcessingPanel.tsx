'use client';

import { useState, useEffect } from 'react';

interface ProcessingPanelProps {
  currentStep: number;
  totalSteps: number;
  showCelebration?: boolean;
  progressPercent?: number;
}

// Tips about NoteTube features - rotate every 4 seconds
const LOADING_TIPS = [
  { icon: "💬", text: "Use the Chat feature to ask questions about any part of the video!" },
  { icon: "🔍", text: "Search for any moment - just describe what you're looking for" },
  { icon: "📝", text: "Select any transcript text to save notes or get AI explanations" },
  { icon: "🎯", text: "Flashcards are auto-generated for quick review and studying" },
  { icon: "📚", text: "Chapters help you navigate to specific topics instantly" },
];

// Messages for each processing step
const STEP_MESSAGES = [
  { message: "Connecting to video...", subtext: "Fetching video metadata" },
  { message: "Extracting transcript...", subtext: "Reading video captions" },
  { message: "AI is analyzing...", subtext: "Generating insights" },
  { message: "Creating chapters...", subtext: "Organizing content" },
  { message: "Almost there!", subtext: "Building flashcards" },
];

export default function ProcessingPanel({
  currentStep,
  totalSteps,
  showCelebration = false,
  progressPercent = 0
}: ProcessingPanelProps) {
  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  const [tipFading, setTipFading] = useState(false);

  // Rotate tips every 4 seconds with fade transition
  useEffect(() => {
    if (showCelebration) return; // Don't rotate during celebration

    const interval = setInterval(() => {
      setTipFading(true);
      setTimeout(() => {
        setCurrentTipIndex((prev) => (prev + 1) % LOADING_TIPS.length);
        setTipFading(false);
      }, 300);
    }, 4000);

    return () => clearInterval(interval);
  }, [showCelebration]);

  // Get current step message (with fallback)
  const stepMessage = STEP_MESSAGES[currentStep] || STEP_MESSAGES[STEP_MESSAGES.length - 1];
  const currentTip = LOADING_TIPS[currentTipIndex];

  // Celebration view
  if (showCelebration) {
    return (
      <div className="lg:w-[40%] xl:w-[38%] lg:border-l border-gray-700 bg-gray-800 lg:h-screen flex flex-col">
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <div className="animate-bounce">
            <span className="text-6xl">🎉</span>
          </div>
          <h2 className="text-2xl font-bold text-white mt-4 mb-2">Here you go!</h2>
          <p className="text-purple-400 text-lg">Your notes are ready</p>
        </div>
      </div>
    );
  }

  return (
    <div className="lg:w-[40%] xl:w-[38%] lg:border-l border-gray-700 bg-gray-800 lg:h-screen flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <span className="text-purple-400">✨</span> NoteTube AI
        </h2>
        <p className="text-gray-400 text-sm mt-1">Preparing your learning materials...</p>
      </div>

      {/* Content area */}
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        {/* Shimmer loading blocks - Gemini style */}
        <div className="w-full max-w-sm space-y-3 mb-6">
          <div
            className="h-4 rounded-full bg-gradient-to-r from-gray-700 via-gray-600 to-gray-700 animate-pulse"
            style={{ width: '100%' }}
          />
          <div
            className="h-4 rounded-full bg-gradient-to-r from-gray-700 via-gray-600 to-gray-700 animate-pulse"
            style={{ width: '85%', animationDelay: '150ms' }}
          />
          <div
            className="h-4 rounded-full bg-gradient-to-r from-gray-700 via-gray-600 to-gray-700 animate-pulse"
            style={{ width: '70%', animationDelay: '300ms' }}
          />
        </div>

        {/* Progress bar with percentage */}
        <div className="w-full max-w-sm mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Progress</span>
            <span className="text-sm font-medium text-purple-400">{progressPercent}%</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Current step message */}
        <div className="text-center mb-10">
          <p className="text-xl text-white font-medium mb-1">
            {stepMessage.message}
          </p>
          <p className="text-gray-400 text-sm">
            {stepMessage.subtext}
          </p>
        </div>

        {/* Rotating tip card */}
        <div
          className={`bg-purple-900/20 border border-purple-700/30 rounded-xl p-5 max-w-sm transition-opacity duration-300 ${
            tipFading ? 'opacity-0' : 'opacity-100'
          }`}
        >
          <div className="flex items-start gap-4">
            <span className="text-3xl flex-shrink-0">{currentTip.icon}</span>
            <div>
              <p className="text-xs text-purple-400 font-medium uppercase tracking-wide mb-1">
                Did you know?
              </p>
              <p className="text-sm text-gray-200 leading-relaxed">
                {currentTip.text}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Progress dots at bottom */}
      <div className="p-6 border-t border-gray-700">
        <div className="flex items-center justify-center gap-2">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div
              key={i}
              className={`h-2 rounded-full transition-all duration-300 ${
                i < currentStep
                  ? 'w-2 bg-purple-500'
                  : i === currentStep
                    ? 'w-6 bg-purple-500'
                    : 'w-2 bg-gray-600'
              }`}
            />
          ))}
        </div>
        <p className="text-center text-xs text-gray-500 mt-3">
          Step {Math.min(currentStep + 1, totalSteps)} of {totalSteps}
        </p>
      </div>
    </div>
  );
}

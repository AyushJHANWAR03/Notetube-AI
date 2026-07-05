'use client';

import { useState, useEffect } from 'react';

interface ProcessingPanelProps {
  currentStep: number;
  showCelebration?: boolean;
  progressPercent?: number;
}

// Tips about NoteTube features - rotate every 4 seconds
const LOADING_TIPS = [
  { icon: "💬", text: "Use the Chat feature to ask questions about any part of the video!" },
  { icon: "🔍", text: "Search for any moment - just describe what you're looking for" },
  { icon: "✨", text: "Select any transcript text to get an AI explanation in chat" },
  { icon: "🎯", text: "Flashcards are auto-generated for quick review and studying" },
  { icon: "📚", text: "Chapters help you navigate to specific topics instantly" },
];

// Named pipeline steps shown as a checklist
const STEPS = [
  { icon: '🎬', label: 'Fetching video', sub: 'Reading metadata' },
  { icon: '📜', label: 'Extracting transcript', sub: 'Reading video captions' },
  { icon: '🧠', label: 'AI analysis', sub: 'Summary, key points & flashcards' },
  { icon: '📑', label: 'Building chapters', sub: 'Organizing content' },
  { icon: '🚀', label: 'Finishing up', sub: 'Almost there!' },
];

export default function ProcessingPanel({
  currentStep,
  showCelebration = false,
  progressPercent = 0
}: ProcessingPanelProps) {
  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  const [tipFading, setTipFading] = useState(false);

  // Rotate tips every 4 seconds with fade transition
  useEffect(() => {
    if (showCelebration) return;

    const interval = setInterval(() => {
      setTipFading(true);
      setTimeout(() => {
        setCurrentTipIndex((prev) => (prev + 1) % LOADING_TIPS.length);
        setTipFading(false);
      }, 300);
    }, 4000);

    return () => clearInterval(interval);
  }, [showCelebration]);

  const currentTip = LOADING_TIPS[currentTipIndex];

  // Celebration view
  if (showCelebration) {
    return (
      <div className="lg:w-[40%] xl:w-[38%] lg:border-l border-gray-800/60 bg-[#0b0d14] lg:h-screen flex flex-col">
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <div className="animate-bounce">
            <span className="text-6xl">🎉</span>
          </div>
          <h2 className="text-2xl font-bold text-white mt-4 mb-2">Here you go!</h2>
          <p className="text-indigo-400 text-lg">Your notes are ready</p>
        </div>
      </div>
    );
  }

  return (
    <div className="lg:w-[40%] xl:w-[38%] lg:border-l border-gray-800/60 bg-[#0b0d14] lg:h-screen flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-800/60">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">✨ NoteTube AI</span>
        </h2>
        <p className="text-gray-400 text-sm mt-1">Preparing your learning materials...</p>
      </div>

      {/* Content area */}
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        {/* Step checklist */}
        <div className="w-full max-w-sm space-y-1 mb-8">
          {STEPS.map((step, i) => {
            const isDone = i < currentStep;
            const isActive = i === currentStep;
            return (
              <div
                key={i}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-300 ${
                  isActive ? 'bg-indigo-500/10 border border-indigo-500/30' : 'border border-transparent'
                }`}
              >
                {/* Status indicator */}
                <div className="w-6 h-6 flex items-center justify-center flex-shrink-0">
                  {isDone ? (
                    <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
                      <svg className="w-3 h-3 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  ) : isActive ? (
                    <div className="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <div className="w-2 h-2 rounded-full bg-gray-700" />
                  )}
                </div>

                <span className="text-base flex-shrink-0">{step.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${isDone ? 'text-gray-500 line-through' : isActive ? 'text-white' : 'text-gray-500'}`}>
                    {step.label}
                  </p>
                  {isActive && (
                    <p className="text-xs text-indigo-300/70">{step.sub}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Progress bar with percentage */}
        <div className="w-full max-w-sm mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Progress</span>
            <span className="text-sm font-medium text-indigo-400">{progressPercent}%</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-600 to-violet-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <p className="text-center text-xs text-gray-600 mt-2">Usually ready in about a minute</p>
        </div>

        {/* Rotating tip card */}
        <div
          className={`bg-indigo-900/15 border border-indigo-700/30 rounded-2xl p-5 max-w-sm transition-opacity duration-300 ${
            tipFading ? 'opacity-0' : 'opacity-100'
          }`}
        >
          <div className="flex items-start gap-4">
            <span className="text-3xl flex-shrink-0">{currentTip.icon}</span>
            <div>
              <p className="text-xs text-indigo-400 font-medium uppercase tracking-widest mb-1">
                Did you know?
              </p>
              <p className="text-sm text-gray-200 leading-relaxed">
                {currentTip.text}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

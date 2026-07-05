'use client';

import { useEffect, useState } from 'react';

const NOTE_LINES = [
  { w: '92%', d: 0.2 },
  { w: '78%', d: 0.5 },
  { w: '85%', d: 0.8 },
  { w: '60%', d: 1.1 },
];

const CHAPTERS = [
  { t: '0:00', label: 'Introduction', d: 1.4 },
  { t: '3:16', label: 'Core Concepts', d: 1.7 },
  { t: '11:42', label: 'Deep Dive', d: 2.0 },
  { t: '24:27', label: 'Real Examples', d: 2.3 },
];

export default function HeroPreview() {
  const [cycle, setCycle] = useState(0);

  // Restart the animation loop every 8s
  useEffect(() => {
    const id = setInterval(() => setCycle((c) => c + 1), 8000);
    return () => clearInterval(id);
  }, []);

  return (
    <div key={cycle} className="grid grid-cols-1 md:grid-cols-[1fr_auto_1.2fr] items-center gap-4 max-w-4xl mx-auto">
      {/* Left: video card */}
      <div className="anim-fade-up rounded-2xl border border-gray-800 bg-gray-900/60 p-3 backdrop-blur" style={{ animationDelay: '0s' }}>
        <div className="relative aspect-video rounded-lg bg-gradient-to-br from-indigo-950 via-gray-900 to-violet-950 flex items-center justify-center overflow-hidden">
          <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_30%_30%,rgba(99,102,241,0.5),transparent_60%)]"></div>
          <div className="w-12 h-12 rounded-full bg-red-600 flex items-center justify-center shadow-lg shadow-red-600/30">
            <svg className="w-5 h-5 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
          <span className="absolute bottom-2 right-2 text-[10px] px-1.5 py-0.5 rounded bg-black/70 text-gray-200">36:56</span>
        </div>
        <p className="text-xs text-gray-400 mt-2 px-1 truncate">Complete Agentic AI Course — RAG, Embeddings &amp; More</p>
      </div>

      {/* Middle: arrow */}
      <div className="anim-fade-up hidden md:flex flex-col items-center gap-1 text-indigo-400" style={{ animationDelay: '0.3s' }}>
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 12h14" />
        </svg>
        <span className="text-[10px] text-gray-500 whitespace-nowrap">~60 sec</span>
      </div>

      {/* Right: generating output */}
      <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-4 backdrop-blur space-y-4">
        {/* Notes */}
        <div>
          <div className="anim-fade-up flex items-center gap-2 mb-2" style={{ animationDelay: '0.1s' }}>
            <span className="text-yellow-400 text-xs">✍️</span>
            <span className="text-xs font-medium text-gray-300">AI Notes</span>
            <span className="anim-cursor text-indigo-400 text-xs">▌</span>
          </div>
          <div className="space-y-1.5">
            {NOTE_LINES.map((l, i) => (
              <div key={i} className="anim-line" style={{ maxWidth: l.w, width: l.w, animationDelay: `${l.d}s`, animationFillMode: 'both' }} />
            ))}
          </div>
        </div>

        {/* Chapters */}
        <div>
          <div className="anim-fade-up flex items-center gap-2 mb-2" style={{ animationDelay: '1.3s' }}>
            <span className="text-orange-400 text-xs">📑</span>
            <span className="text-xs font-medium text-gray-300">Smart Chapters</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {CHAPTERS.map((c) => (
              <span
                key={c.t}
                className="anim-fade-up text-[10px] px-2 py-1 rounded-md bg-gray-800 border border-gray-700 text-gray-300"
                style={{ animationDelay: `${c.d}s` }}
              >
                <span className="text-indigo-400 font-mono">{c.t}</span> {c.label}
              </span>
            ))}
          </div>
        </div>

        {/* Flashcard */}
        <div className="anim-fade-up" style={{ animationDelay: '2.6s' }}>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-green-400 text-xs">🃏</span>
            <span className="text-xs font-medium text-gray-300">Flashcards</span>
          </div>
          <div className="rounded-lg bg-gradient-to-r from-indigo-900/40 to-violet-900/40 border border-indigo-700/40 px-3 py-2">
            <p className="text-[11px] text-gray-300">Q: What makes an AI agent &quot;agentic&quot;?</p>
          </div>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useEffect, useRef, useMemo, useState, useCallback } from 'react';
import { TranscriptSegment } from '@/lib/types';

interface SegmentGroup {
  id: number;
  segments: TranscriptSegment[];
  start: number;
  end: number;
  text: string;
}

interface SelectionPopup {
  visible: boolean;
  x: number;
  y: number;
  text: string;
}

interface TranscriptPanelProps {
  segments: TranscriptSegment[];
  currentTime: number;
  onSeek: (seconds: number) => void;
  autoScroll: boolean;
  onToggleAutoScroll: () => void;
  onExplain?: (text: string) => void;
  onTakeNotes?: (text: string) => void;
}

// Group segments for better readability (2-3 per group)
function groupSegments(segments: TranscriptSegment[], maxPerGroup = 3): SegmentGroup[] {
  const groups: SegmentGroup[] = [];
  let currentGroup: TranscriptSegment[] = [];
  let groupId = 0;

  for (const seg of segments) {
    currentGroup.push(seg);

    if (currentGroup.length >= maxPerGroup) {
      const firstSeg = currentGroup[0];
      const lastSeg = currentGroup[currentGroup.length - 1];
      groups.push({
        id: groupId++,
        segments: [...currentGroup],
        start: firstSeg.start,
        end: lastSeg.start + lastSeg.duration,
        text: currentGroup.map(s => s.text).join(' ')
      });
      currentGroup = [];
    }
  }

  // Handle remaining segments
  if (currentGroup.length > 0) {
    const firstSeg = currentGroup[0];
    const lastSeg = currentGroup[currentGroup.length - 1];
    groups.push({
      id: groupId++,
      segments: [...currentGroup],
      start: firstSeg.start,
      end: lastSeg.start + lastSeg.duration,
      text: currentGroup.map(s => s.text).join(' ')
    });
  }

  return groups;
}

// Format time as MM:SS
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default function TranscriptPanel({
  segments,
  currentTime,
  onSeek,
  autoScroll,
  onToggleAutoScroll,
  onExplain,
  onTakeNotes
}: TranscriptPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);
  const isAutoScrollingRef = useRef(false);
  const [selectionPopup, setSelectionPopup] = useState<SelectionPopup>({
    visible: false,
    x: 0,
    y: 0,
    text: ''
  });

  // Group segments
  const groupedSegments = useMemo(() => groupSegments(segments), [segments]);

  // Find active group based on current time
  const activeGroupId = useMemo(() => {
    for (let i = groupedSegments.length - 1; i >= 0; i--) {
      if (currentTime >= groupedSegments[i].start) {
        return groupedSegments[i].id;
      }
    }
    return groupedSegments[0]?.id ?? null;
  }, [currentTime, groupedSegments]);

  // Auto-scroll to active segment
  useEffect(() => {
    if (autoScroll && activeRef.current && containerRef.current) {
      // Don't auto-scroll if popup is visible (user is working with selection)
      if (selectionPopup.visible) return;

      // Don't auto-scroll if there's an active text selection
      const selection = window.getSelection();
      const selectedText = selection?.toString().trim();
      if (selectedText && selectedText.length > 0) return;

      // Mark that we're auto-scrolling so the scroll handler doesn't hide popup
      isAutoScrollingRef.current = true;
      activeRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
      // Reset after scroll animation completes
      setTimeout(() => {
        isAutoScrollingRef.current = false;
      }, 500);
    }
  }, [activeGroupId, autoScroll, selectionPopup.visible]);

  // Handle text selection - use setTimeout to ensure selection is stable
  const handleMouseUp = useCallback(() => {
    // Small delay to let the selection stabilize
    setTimeout(() => {
      const selection = window.getSelection();
      const selectedText = selection?.toString().trim();

      if (selectedText && selectedText.length > 0 && containerRef.current) {
        const range = selection?.getRangeAt(0);
        if (range) {
          const rect = range.getBoundingClientRect();
          const containerRect = containerRef.current.getBoundingClientRect();
          const scrollTop = containerRef.current.scrollTop;

          // Position popup above the selection, accounting for scroll
          setSelectionPopup({
            visible: true,
            x: rect.left + rect.width / 2 - containerRect.left,
            y: rect.top - containerRect.top + scrollTop - 10,
            text: selectedText
          });
        }
      }
    }, 10);
  }, []);

  // Hide popup when clicking elsewhere or when selection changes
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // Check if clicking on the popup buttons
    const target = e.target as HTMLElement;
    if (target.closest('.selection-popup')) {
      return;
    }
    setSelectionPopup(prev => ({ ...prev, visible: false }));
  }, []);

  // Hide popup on manual scroll (not auto-scroll) - but keep it if there's an active selection
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      // Don't hide popup if this scroll is from auto-scroll
      if (isAutoScrollingRef.current) return;

      // Don't hide popup if there's still an active text selection
      const selection = window.getSelection();
      const selectedText = selection?.toString().trim();
      if (selectedText && selectedText.length > 0) return;

      setSelectionPopup(prev => ({ ...prev, visible: false }));
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  const handleExplain = (text: string) => {
    setSelectionPopup(prev => ({ ...prev, visible: false }));
    window.getSelection()?.removeAllRanges();
    if (onExplain) {
      onExplain(text);
    } else {
      alert('Explain feature coming soon!');
    }
  };

  const handleTakeNotes = (text: string) => {
    setSelectionPopup(prev => ({ ...prev, visible: false }));
    window.getSelection()?.removeAllRanges();
    if (onTakeNotes) {
      onTakeNotes(text);
    } else {
      alert('Take Notes feature coming soon!');
    }
  };

  if (!segments || segments.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        No transcript available
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with Auto toggle */}
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-gray-700">
        <span className="text-gray-400 text-sm">
          {groupedSegments.length} segments
        </span>
        <button
          onClick={onToggleAutoScroll}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-colors ${
            autoScroll
              ? 'bg-blue-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          Auto
        </button>
      </div>

      {/* Transcript segments */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar relative"
        style={{ maxHeight: '600px' }}
        onMouseUp={handleMouseUp}
        onMouseDown={handleMouseDown}
      >
        {/* Selection Popup */}
        {selectionPopup.visible && (
          <div
            className="selection-popup absolute z-50 flex gap-1 bg-gray-900 border border-gray-600 rounded-lg shadow-xl p-1 transform -translate-x-1/2 -translate-y-full"
            style={{
              left: selectionPopup.x,
              top: selectionPopup.y,
            }}
          >
            <button
              onClick={() => handleExplain(selectionPopup.text)}
              className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-blue-600 text-white rounded transition-colors font-medium"
            >
              Explain
            </button>
            <button
              onClick={() => handleTakeNotes(selectionPopup.text)}
              className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-green-600 text-white rounded transition-colors font-medium"
            >
              Take Notes
            </button>
          </div>
        )}

        {groupedSegments.map((group) => {
          const isActive = group.id === activeGroupId;

          return (
            <div
              key={group.id}
              ref={isActive ? activeRef : undefined}
              className={`relative p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                isActive
                  ? 'bg-blue-900/40 border-l-2 border-blue-500'
                  : 'hover:bg-gray-700/30 border-l-2 border-transparent'
              }`}
              onClick={() => {
                // Don't seek if user has text selected (they're trying to select, not seek)
                const selection = window.getSelection();
                const selectedText = selection?.toString().trim();
                if (selectedText && selectedText.length > 0) return;
                onSeek(group.start);
              }}
            >
              {/* Active indicator dot */}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1 w-2 h-2 bg-yellow-400 rounded-full" />
              )}

              {/* Transcript text - selectable, clean without timestamps */}
              <p
                className={`text-sm leading-relaxed select-text ${
                  isActive ? 'text-white' : 'text-gray-300'
                }`}
              >
                {group.text}
              </p>
            </div>
          );
        })}
      </div>

      {/* Helper text */}
      <div className="mt-3 pt-2 border-t border-gray-700">
        <p className="text-xs text-gray-500 text-center">
          Select any text to explain or take notes
        </p>
      </div>
    </div>
  );
}

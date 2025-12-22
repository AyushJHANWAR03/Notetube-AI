'use client';

import { useEffect, useRef, useMemo, useState, useCallback } from 'react';
import { TranscriptSegment, SeekResponse } from '@/lib/types';

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
  // Take Me There (AI Search) props
  onTakeMeThere?: (query: string) => Promise<void>;
  isSearching?: boolean;
  searchResult?: SeekResponse | null;
  searchError?: string | null;
  onClearSearch?: () => void;
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
  onTakeNotes,
  onTakeMeThere,
  isSearching = false,
  searchResult,
  searchError,
  onClearSearch
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

  // AI Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [showDiscoveryTip, setShowDiscoveryTip] = useState(false);

  // Check localStorage for discovery tip on mount
  useEffect(() => {
    const dismissed = localStorage.getItem('transcriptTipDismissed');
    if (!dismissed) {
      setShowDiscoveryTip(true);
    }
  }, []);

  const dismissDiscoveryTip = useCallback(() => {
    localStorage.setItem('transcriptTipDismissed', 'true');
    setShowDiscoveryTip(false);
  }, []);

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim() || !onTakeMeThere) return;
    await onTakeMeThere(searchQuery);
  }, [searchQuery, onTakeMeThere]);

  const handleClearSearch = useCallback(() => {
    setSearchQuery('');
    onClearSearch?.();
  }, [onClearSearch]);

  // Auto-dismiss search result after 3 seconds
  useEffect(() => {
    if (searchResult && searchResult.timestamp !== null) {
      const timer = setTimeout(() => {
        onClearSearch?.();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [searchResult, onClearSearch]);

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
      {/* Header with AI Search and Auto toggle */}
      <div className="flex flex-col gap-2 mb-4 pb-3 border-b border-gray-700">
        {/* First-time discovery tip - dismissible (combined: search + text selection) */}
        {showDiscoveryTip && (
          <div className="flex items-center justify-between bg-blue-900/30 border border-blue-700/50 rounded-lg px-3 py-2">
            <div className="flex items-center gap-2">
              <span className="text-yellow-400">💡</span>
              <span className="text-sm text-blue-200">
                AI search: describe what you're looking for in any language
              </span>
            </div>
            <button
              onClick={dismissDiscoveryTip}
              className="text-gray-400 hover:text-white p-1 transition-colors"
              aria-label="Dismiss tip"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Search bar + Auto toggle row */}
        <div className="flex items-center gap-2">
          {onTakeMeThere ? (
            <div className="flex-1 relative">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSearch();
                  }
                }}
                placeholder="Describe what you're looking for..."
                disabled={isSearching}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg pl-9 pr-10 py-2 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
              />
              {isSearching ? (
                <div className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              ) : searchQuery && (
                <button
                  onClick={handleClearSearch}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          ) : (
            <span className="flex-1 text-gray-400 text-sm">
              {groupedSegments.length} segments
            </span>
          )}
          <button
            onClick={onToggleAutoScroll}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-colors flex-shrink-0 ${
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

        {/* Search result - inline below search bar */}
        {searchResult && searchResult.timestamp !== null && (
          <div
            className={`relative w-full p-3 rounded-lg border transition-all ${
              searchResult.confidence === 'high'
                ? 'bg-green-900/30 border-green-700'
                : searchResult.confidence === 'medium'
                ? 'bg-yellow-900/30 border-yellow-700'
                : 'bg-gray-700/30 border-gray-600'
            }`}
          >
            {/* Close button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleClearSearch();
              }}
              className="absolute top-2 right-2 text-gray-400 hover:text-white transition-colors p-1"
              aria-label="Dismiss result"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            <div className="flex items-center justify-between mb-1 pr-6">
              <span className="font-mono text-lg text-blue-400 font-bold">
                {formatTime(searchResult.timestamp)}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded ${
                searchResult.confidence === 'high' ? 'text-green-400 bg-green-900/50' :
                searchResult.confidence === 'medium' ? 'text-yellow-400 bg-yellow-900/50' :
                'text-gray-400 bg-gray-700/50'
              }`}>
                {searchResult.confidence === 'high' ? 'Best Match' : searchResult.confidence === 'medium' ? 'Good Match' : 'Partial'}
              </span>
            </div>
            {searchResult.matched_text && (
              <p className="text-xs text-gray-400 line-clamp-2">"{searchResult.matched_text}"</p>
            )}
          </div>
        )}

        {/* No match found */}
        {searchResult && searchResult.timestamp === null && (
          <p className="text-sm text-gray-500 text-center py-2">
            No match found. Try different keywords.
          </p>
        )}

        {/* Search error */}
        {searchError && (
          <p className="text-sm text-red-400 text-center py-2">{searchError}</p>
        )}
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

      {/* Helper text - prominent styling */}
      <div className="mt-3 pt-3 border-t border-gray-700">
        <div className="bg-purple-900/20 border border-purple-700/30 rounded-lg px-3 py-2">
          <p className="text-sm text-purple-300 text-center flex items-center justify-center gap-2">
            <span>✨</span>
            <span>Select any text above to explain or save to notes</span>
          </p>
        </div>
      </div>
    </div>
  );
}

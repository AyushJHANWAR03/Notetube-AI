'use client';

import { useState } from 'react';
import { UserNote, REWRITE_STYLES, RewriteStyle } from '@/lib/types';
import { videoApi } from '@/lib/videoApi';

interface NotesPanelProps {
  videoId: string;
  notes: UserNote[];
  onSeek: (seconds: number) => void;
  onNotesChange: (notes: UserNote[]) => void;
}

function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export default function NotesPanel({ videoId, notes, onSeek, onNotesChange }: NotesPanelProps) {
  const [rewritingNoteId, setRewritingNoteId] = useState<string | null>(null);
  const [deletingNoteId, setDeletingNoteId] = useState<string | null>(null);
  const [openDropdownId, setOpenDropdownId] = useState<string | null>(null);

  const handleDelete = async (noteId: string) => {
    setDeletingNoteId(noteId);
    try {
      await videoApi.deleteUserNote(videoId, noteId);
      onNotesChange(notes.filter(n => n.id !== noteId));
    } catch (error) {
      console.error('Failed to delete note:', error);
    } finally {
      setDeletingNoteId(null);
    }
  };

  const handleRewrite = async (noteId: string, style: RewriteStyle) => {
    setRewritingNoteId(noteId);
    setOpenDropdownId(null);
    try {
      const updatedNote = await videoApi.rewriteUserNote(videoId, noteId, style);
      onNotesChange(notes.map(n => n.id === noteId ? updatedNote : n));
    } catch (error) {
      console.error('Failed to rewrite note:', error);
    } finally {
      setRewritingNoteId(null);
    }
  };

  if (notes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center py-12">
        <div className="w-16 h-16 bg-green-900/30 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-white mb-2">
          No Notes Yet
        </h3>
        <p className="text-gray-400 text-sm max-w-sm mb-4">
          Select text from the transcript and click "Take Notes" to save important snippets here.
        </p>
        <p className="text-xs text-gray-500">
          Your saved notes will appear with timestamps for easy reference.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-gray-400 text-sm mb-4">
        {notes.length} note{notes.length !== 1 ? 's' : ''} saved
      </p>

      {notes.map((note) => (
        <div
          key={note.id}
          className="bg-gray-700/50 rounded-lg p-4 border border-gray-600 hover:border-gray-500 transition-colors"
        >
          {/* Header with timestamp */}
          <div className="flex items-center justify-between mb-2">
            <button
              onClick={() => onSeek(note.timestamp)}
              className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-mono text-sm">{formatTimestamp(note.timestamp)}</span>
            </button>
            <span className="text-xs text-gray-500">{formatDate(note.created_at)}</span>
          </div>

          {/* Original text */}
          <p className="text-gray-200 text-sm leading-relaxed mb-3">{note.text}</p>

          {/* Rewritten text (if exists) */}
          {note.rewritten_text && (
            <div className="bg-blue-900/30 border border-blue-700/50 rounded-lg p-3 mb-3">
              <p className="text-xs text-blue-400 mb-1 font-medium">AI Rewrite</p>
              <p className="text-gray-200 text-sm leading-relaxed">{note.rewritten_text}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between pt-2 border-t border-gray-600">
            {/* Rewrite dropdown */}
            <div className="relative">
              <button
                onClick={() => setOpenDropdownId(openDropdownId === note.id ? null : note.id)}
                disabled={rewritingNoteId === note.id}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gray-600 hover:bg-gray-500 text-gray-200 rounded-lg transition-colors disabled:opacity-50"
              >
                {rewritingNoteId === note.id ? (
                  <>
                    <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                    Rewriting...
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Rewrite with AI
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </>
                )}
              </button>

              {/* Dropdown menu */}
              {openDropdownId === note.id && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setOpenDropdownId(null)}
                  />
                  <div className="absolute left-0 bottom-full mb-1 w-48 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-50 py-1">
                    {REWRITE_STYLES.map((style) => (
                      <button
                        key={style.value}
                        onClick={() => handleRewrite(note.id, style.value)}
                        className="w-full text-left px-3 py-2 hover:bg-gray-700 transition-colors"
                      >
                        <div className="text-sm text-white">{style.label}</div>
                        <div className="text-xs text-gray-400">{style.description}</div>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Delete button */}
            <button
              onClick={() => handleDelete(note.id)}
              disabled={deletingNoteId === note.id}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-400 hover:text-red-300 hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50"
            >
              {deletingNoteId === note.id ? (
                <div className="w-3 h-3 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              )}
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
